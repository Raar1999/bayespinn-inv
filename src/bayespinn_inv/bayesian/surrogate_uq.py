"""MC-Dropout and SWAG uncertainty backends for the SG-supervised surrogate.

Why this module exists
----------------------
``bayesian/mc_dropout.py`` and ``bayesian/swag.py`` wrap :class:`ForwardPINN` --
the *pure-physics* forward model that ``docs/forward_model_reframe.md``
superseded. The forward model the project actually uses is
:class:`~bayespinn_inv.surrogate.iv_surrogate.IVSurrogate`, and only the deep
ensemble had a surrogate-side implementation
(:class:`~bayespinn_inv.surrogate.iv_surrogate.SurrogateEnsemble`).

That asymmetry is the whole reason ``RELEASE_READINESS.md`` Gate D recorded
"MC-dropout / SWAG compared: NOT DEMONSTRATED" -- the two backends were not
attached to the model being evaluated, so they could not be benchmarked
against the ensemble at all.

Both classes here return the *same* :class:`SurrogatePrediction` dataclass the
ensemble returns, with the same shapes, units and symlog convention, so every
downstream metric (H1 accuracy, H3 calibration, H5 uncertainty--error
correlation) applies unchanged. That is what makes the comparison fair: one
evaluation path, three uncertainty sources.

Interface contract (asserted by ``tests/test_surrogate_uq.py``)
--------------------------------------------------------------
``predict(doping_latent, biases_scaled) -> SurrogatePrediction`` with
``mean_symlog``/``std_symlog``/``mean_current`` of shape ``(B,)`` and
``samples_symlog`` of shape ``(M, B)``, for every backend.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import torch

from ..surrogate.iv_surrogate import (
    IVSurrogate,
    Normalizer,
    SurrogatePrediction,
    SymlogTransform,
    make_features,
)
from .swag import SWAGConfig, SWAGRecorder, _flatten_params, _unflatten_params

__all__ = [
    "MCDropoutSurrogate",
    "SWAGSurrogate",
    "SurrogateUQBackend",
]


class SurrogateUQBackend:
    """Common plumbing: featurise, normalise, aggregate M samples.

    Subclasses implement :meth:`_sample_symlog`, which must return an
    ``(M, B)`` array of symlog-space predictions.
    """

    def __init__(self, normalizer: Normalizer,
                 symlog: Optional[SymlogTransform] = None):
        self.normalizer = normalizer
        self.symlog = symlog or SymlogTransform()

    @property
    def M(self) -> int:  # pragma: no cover - overridden
        raise NotImplementedError

    def _features(self, doping_latent: np.ndarray,
                  biases_scaled: np.ndarray) -> torch.Tensor:
        feats = np.stack([make_features(doping_latent, b) for b in biases_scaled])
        return self.normalizer(torch.tensor(feats, dtype=torch.float32))

    def _sample_symlog(self, xb: torch.Tensor) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def predict(self, doping_latent: np.ndarray,
                biases_scaled: np.ndarray) -> SurrogatePrediction:
        """Predict an I--V curve with predictive uncertainty.

        Identical signature, return type and symlog convention as
        :meth:`SurrogateEnsemble.predict`.
        """
        xb = self._features(doping_latent, np.asarray(biases_scaled))
        S = self._sample_symlog(xb)                    # (M, B)
        mean_s = S.mean(0)
        # ddof=0 matches SurrogateEnsemble, so the three backends' sigmas are
        # directly comparable. (For M=5 the ensemble's ddof=0 sigma is biased
        # low; `ece_floor_for_ensemble` quantifies that separately.)
        std_s = S.std(0)
        return SurrogatePrediction(
            mean_symlog=mean_s,
            std_symlog=std_s,
            mean_current=self.symlog.inverse(mean_s),
            samples_symlog=S,
            mean_current_linear=self.symlog.inverse(S).mean(0),
        )


class MCDropoutSurrogate(SurrogateUQBackend):
    """MC-Dropout (Gal & Ghahramani, ICML 2016) over a single IVSurrogate.

    The model must have been *trained* with ``IVSurrogateConfig.dropout > 0``:
    dropout at test time without dropout at train time samples a different
    (and meaningless) model. This is checked in :meth:`__init__` rather than
    silently producing a zero-variance prediction.

    Only the ``nn.Dropout`` modules are put in train mode. Calling
    ``model.train()`` would also switch any normalisation layer's running
    statistics, which is not what MC-Dropout means.
    """

    def __init__(self, model: IVSurrogate, normalizer: Normalizer,
                 symlog: Optional[SymlogTransform] = None,
                 n_samples: int = 30, seed: int = 0):
        super().__init__(normalizer, symlog)
        drops = [m for m in model.modules() if isinstance(m, torch.nn.Dropout)]
        if not drops:
            raise ValueError(
                "MCDropoutSurrogate requires a model trained with dropout > 0; "
                "this IVSurrogate has no nn.Dropout modules, so every sample "
                "would be identical and sigma would be exactly zero."
            )
        if all(d.p == 0.0 for d in drops):
            raise ValueError("all Dropout layers have p=0; sigma would be zero")
        self.model = model
        self._drops = drops
        self.n_samples = int(n_samples)
        self.seed = int(seed)

    @property
    def M(self) -> int:
        return self.n_samples

    def _sample_symlog(self, xb: torch.Tensor) -> np.ndarray:
        self.model.eval()                 # deterministic everything else...
        for d in self._drops:
            d.train()                     # ...except the dropout masks
        # nn.Dropout draws from the *global* RNG, so reproducibility requires
        # seeding it -- but leaking that seed into the caller's stream is
        # exactly AUDIT_MASTER API-03. Save, seed, sample, restore.
        state = torch.random.get_rng_state()
        try:
            torch.manual_seed(self.seed)
            out = []
            with torch.no_grad():
                for _ in range(self.n_samples):
                    out.append(self.model(xb).numpy().ravel())
        finally:
            torch.random.set_rng_state(state)
            for d in self._drops:
                d.eval()
        return np.stack(out, axis=0)


class SWAGSurrogate(SurrogateUQBackend):
    """SWAG (Maddox et al., NeurIPS 2019) over a single IVSurrogate.

    Consumes a :class:`SWAGRecorder` populated during the SWA phase of
    training. Each test-time sample draws a weight vector from the fitted
    low-rank-plus-diagonal Gaussian, writes it into the network, and runs a
    forward pass; the original weights are restored afterwards.
    """

    def __init__(self, model: IVSurrogate, recorder: SWAGRecorder,
                 normalizer: Normalizer,
                 symlog: Optional[SymlogTransform] = None,
                 cfg: Optional[SWAGConfig] = None):
        super().__init__(normalizer, symlog)
        if recorder.n_collected < 2:
            raise ValueError(
                f"SWAG needs >= 2 collected snapshots to have any variance; "
                f"got {recorder.n_collected}. Call recorder.collect() during "
                f"the SWA phase of training."
            )
        self.model = model
        self.recorder = recorder
        self.cfg = cfg or recorder.cfg

    @property
    def M(self) -> int:
        return int(self.cfg.T_samples)

    def _sample_symlog(self, xb: torch.Tensor) -> np.ndarray:
        self.model.eval()
        saved = _flatten_params(self.model).clone()
        gen = torch.Generator().manual_seed(int(self.cfg.seed))
        out = []
        try:
            with torch.no_grad():
                for _ in range(self.M):
                    _unflatten_params(self.recorder.sample(generator=gen), self.model)
                    out.append(self.model(xb).numpy().ravel())
        finally:
            _unflatten_params(saved, self.model)     # never leave the model perturbed
        return np.stack(out, axis=0)
