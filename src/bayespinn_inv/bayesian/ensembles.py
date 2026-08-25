"""
Deep Ensembles wrapper for the forward PINN.

We treat the ensemble as the *primary* Bayesian method. Each member is a
fully independent PINN with a different random seed, trained on the same
data. Predictions are aggregated as:

    mu(y)    = (1/M) sum_m  y_m
    sigma(y)^2 = (1/M) sum_m (y_m - mu)^2 + sigma_aleatoric^2

with optional aleatoric variance term (zero in our current setup, since
the PDE residual is deterministic; would be non-zero if we extended to
SDE-based modelling).

Empirical observations driving this choice (see proposal §4):

- Deep ensembles consistently outperform MFVI on regression UQ
  (Lakshminarayanan et al., 2017) for the regime of medium-sized networks
  (10^3-10^5 params) we operate in.
- Cost is M*forward; we use M=5 by default per the proposal's compute
  budget.
- Ensembles parallelize trivially.

This module intentionally does NOT provide ensemble *training* — that is
expected to happen with M independent ``PINNTrainer`` instances, run in
parallel by the experiment driver. The wrapper only handles aggregation
at inference time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from ..physics.constants import Material
from ..physics.scaling import Scaling
from ..pinn.forward_pinn import ForwardPINN
from ..solvers.scharfetter_gummel import DeviceState


@dataclass
class EnsemblePrediction:
    """Aggregated ensemble prediction.

    Each field has shape (n_query,) or (n_bias,) as appropriate. The
    ``samples`` field contains per-member raw predictions, shape
    (M, n_query/n_bias), for downstream metrics like CRPS that require
    access to the underlying distribution.
    """
    mean: np.ndarray
    std: np.ndarray
    samples: np.ndarray
    quantile_lo: np.ndarray
    quantile_hi: np.ndarray


class DeepEnsemble(nn.Module):
    """Deep ensemble of ForwardPINNs.

    Members can be added one at a time (e.g. as each ensemble training job
    completes) via :meth:`add_member`, or all at once at construction time.
    """

    def __init__(
        self,
        scaling: Scaling,
        material: Material,
        members: Optional[Sequence[ForwardPINN]] = None,
    ):
        super().__init__()
        self.scaling = scaling
        self.material = material
        self.members: nn.ModuleList = nn.ModuleList(list(members) if members else [])

    def add_member(self, fwd: ForwardPINN) -> None:
        self.members.append(fwd)

    @property
    def M(self) -> int:
        return len(self.members)

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate(
        samples: np.ndarray, q_lo: float = 0.05, q_hi: float = 0.95,
    ) -> EnsemblePrediction:
        return EnsemblePrediction(
            mean=samples.mean(axis=0),
            std=samples.std(axis=0, ddof=0),
            samples=samples,
            quantile_lo=np.quantile(samples, q_lo, axis=0),
            quantile_hi=np.quantile(samples, q_hi, axis=0),
        )

    # ------------------------------------------------------------------
    # IV curves
    # ------------------------------------------------------------------

    def iv_curve(
        self,
        doping_si: torch.Tensor,
        biases: Sequence[float],
        with_grad: bool = False,
    ) -> Tuple[torch.Tensor, EnsemblePrediction]:
        """Run every ensemble member and aggregate I(V).

        Parameters
        ----------
        with_grad : bool
            If True, keep autograd connected (used by inverse design).
            The returned ``EnsemblePrediction.samples`` is then derived
            from a detached numpy snapshot, but the *aggregated mean* is
            available as a torch tensor via the first return value.
        """
        if self.M == 0:
            raise RuntimeError("Empty ensemble.")
        member_currents: List[torch.Tensor] = []
        for fwd in self.members:
            _, I = fwd.iv_curve(doping_si, biases)
            member_currents.append(I)
        stacked = torch.stack(member_currents, dim=0)        # (M, B)
        mean_t = stacked.mean(dim=0)                          # (B,)
        det_samples = stacked.detach().cpu().numpy()
        return mean_t, self._aggregate(det_samples)

    # ------------------------------------------------------------------
    # Field predictions (phi, n, p) across the device
    # ------------------------------------------------------------------

    def solve(
        self,
        doping_si: torch.Tensor,
        bias: float,
    ) -> Tuple[DeviceState, Dict[str, EnsemblePrediction]]:
        """Aggregated forward solve. Returns the ensemble-mean
        :class:`DeviceState` *plus* per-field uncertainty predictions.
        """
        states: List[DeviceState] = []
        for fwd in self.members:
            states.append(fwd.solve(doping_si, bias))
        # All members share the same query grid (ForwardPINNConfig)
        x = states[0].x
        phi_s = np.stack([s.phi for s in states], axis=0)
        n_s   = np.stack([s.n   for s in states], axis=0)
        p_s   = np.stack([s.p   for s in states], axis=0)
        # Currents on face grid (slightly larger). Average per-member.
        Jn_s  = np.stack([s.Jn  for s in states], axis=0)
        Jp_s  = np.stack([s.Jp  for s in states], axis=0)
        agg = {
            "phi": self._aggregate(phi_s),
            "n":   self._aggregate(np.log10(np.maximum(n_s, 1e-6))),  # log10
            "p":   self._aggregate(np.log10(np.maximum(p_s, 1e-6))),
            "Jn":  self._aggregate(Jn_s),
            "Jp":  self._aggregate(Jp_s),
        }
        mean_state = DeviceState(
            x=x,
            phi=agg["phi"].mean,
            n=np.exp(np.log(10.0) * agg["n"].mean),
            p=np.exp(np.log(10.0) * agg["p"].mean),
            Jn=agg["Jn"].mean,
            Jp=agg["Jp"].mean,
            doping=states[0].doping,
            bias=bias,
            converged=True, iterations=0, residuals=[],
        )
        return mean_state, agg


def load_deep_ensemble(manifest_path) -> Tuple["DeepEnsemble", Dict]:
    """Reconstruct a :class:`DeepEnsemble` from a pure-physics PINN manifest.

    AUDIT_g0 PKG-04 / SW-17. This function previously lived in the repository's
    ``scripts/run_benchmark_sweep.py``, and ``surrogate/adapters.py`` reached it
    by ``exec_module``-ing that file from the source checkout at runtime -- a
    path that does not exist in an installed wheel. It depends on nothing
    repo-only, so it belongs in the package; the script now delegates here, which
    also gives the project one definition instead of two (SW-02).

    The ensemble it rebuilds is the **legacy** pure-physics PINN
    (``ADR-0004``: 100% median relative error as a forward model). It is
    reconstructible because a shipped artefact still exercises this path --
    ``outputs/smoke/manifest.json`` carries checkpoints and no ``type`` key.

    Parameters
    ----------
    manifest_path : str or Path
        A ``manifest.json`` written by the legacy training pipeline, carrying
        ``config``, ``member_seeds`` and ``checkpoints``.

    Returns
    -------
    (ensemble, manifest)
        The rebuilt ensemble and the parsed manifest dict.
    """
    import json
    from pathlib import Path as _Path

    from ..physics.constants import GAAS, SILICON
    from ..pinn.forward_pinn import ForwardPINNConfig
    from ..pinn.network import PINNConfig, SemiconductorPINN

    manifest = json.loads(_Path(manifest_path).read_text(encoding="utf-8"))
    cfg = manifest["config"]
    material = {"Si": SILICON, "Silicon": SILICON, "GaAs": GAAS}[cfg["material"]["name"]]
    scaling = Scaling.for_material(material, T=cfg["material"]["T"])
    L_scaled = float(scaling.x_to_scaled(
        torch.tensor(cfg["domain_si"][1] - cfg["domain_si"][0])))
    V_a_max_s = float(cfg["dataset"]["bias_range"][1]) / scaling.V_T

    ens = DeepEnsemble(scaling, material)
    for seed, ck_path in zip(manifest["member_seeds"], manifest["checkpoints"]):
        net_cfg = PINNConfig(
            in_dim=cfg["network"]["in_dim"],
            hidden_dim=cfg["network"]["hidden_dim"],
            num_blocks=cfg["network"]["num_blocks"],
            fourier_features=cfg["network"]["fourier_features"],
            fourier_sigma=cfg["network"]["fourier_sigma"],
            dropout=cfg["network"]["dropout"],
            doping_dim=cfg["network"]["doping_dim"],
            output_dim=cfg["network"]["output_dim"],
            seed=seed,
            x_scaled_extent=L_scaled,
            V_a_scaled_extent=V_a_max_s,
        )
        net = SemiconductorPINN(net_cfg)
        # SEC-02 / SW-16: never execute code from a checkpoint. These hold only
        # tensors and plain scalars, so weights_only=True is always sufficient.
        ck = torch.load(ck_path, map_location="cpu", weights_only=True)
        net.load_state_dict(ck["model_state"])
        net.eval()
        ens.add_member(ForwardPINN(
            net, scaling, material,
            ForwardPINNConfig(
                n_query=cfg["network"].get("n_query", 201),
                n_anchor=cfg["network"]["doping_dim"],
                domain_si=tuple(cfg["domain_si"]),
            ),
        ))
    return ens, manifest


__all__ = ["DeepEnsemble", "EnsemblePrediction", "load_deep_ensemble"]
