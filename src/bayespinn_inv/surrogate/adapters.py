"""
Adapters: present the SG-supervised surrogate through the same interface the
legacy ``inverse/`` and ``calibration/`` code expects from ``ForwardPINN`` and
``DeepEnsemble``.

Why this exists
---------------
The pre-existing pipeline (``InverseDesigner``, the calibration metrics, the
inverse/calibration/defect launchers) was written against the pure-physics
``ForwardPINN`` forward model, which does not reproduce diode I-V (see
``docs/forward_model_reframe.md``). Rather than rewrite those modules, we wrap
the working surrogate so it *quacks like* the old forward model:

  - :class:`SurrogateForwardAdapter` exposes ``.cfg.{device,dtype}``,
    ``.parameters()`` and a differentiable ``.iv_curve(C_si, biases)`` — exactly
    what :class:`~bayespinn_inv.inverse.inverse_design.InverseDesigner` calls.
  - :class:`SurrogateEnsembleAdapter` exposes ``.members``, ``.scaling``,
    ``.material``, ``.M`` and ``.iv_curve(...) -> (mean_t, EnsemblePrediction)``
    — a drop-in for :class:`~bayespinn_inv.bayesian.ensembles.DeepEnsemble`.

So the legacy scripts run unchanged on top of the working forward model.

The adapter's ``iv_curve`` is differentiable in the doping, so gradient-based
inverse design flows straight through ``scaling.doping_to_net_input`` into the
surrogate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch

from ..bayesian.ensembles import EnsemblePrediction
from .iv_surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SymlogTransform,
)

# ---------------------------------------------------------------------------
# Minimal cfg object so legacy code can read .device / .dtype / anchors
# ---------------------------------------------------------------------------

@dataclass
class _AdapterCfg:
    device: str = "cpu"
    dtype: torch.dtype = torch.float32
    n_anchor: int = 16
    domain_si: Tuple[float, float] = (0.0, 1e-6)


def _to_anchor(C_si: torch.Tensor, n_anchor: int) -> torch.Tensor:
    """Resample a doping profile to ``n_anchor`` points (differentiably)."""
    C_si = C_si.reshape(-1)
    if C_si.shape[0] == n_anchor:
        return C_si
    # linear interpolation on a normalized [0,1] grid, autograd-friendly
    src = torch.linspace(0.0, 1.0, C_si.shape[0], dtype=C_si.dtype, device=C_si.device)
    dst = torch.linspace(0.0, 1.0, n_anchor, dtype=C_si.dtype, device=C_si.device)
    idx = torch.searchsorted(src, dst).clamp(1, C_si.shape[0] - 1)
    x0, x1 = src[idx - 1], src[idx]
    y0, y1 = C_si[idx - 1], C_si[idx]
    w = (dst - x0) / (x1 - x0).clamp(min=1e-12)
    return y0 + w * (y1 - y0)


# ---------------------------------------------------------------------------
# Single-member adapter (drop-in for ForwardPINN)
# ---------------------------------------------------------------------------

class SurrogateForwardAdapter:
    """Wrap one :class:`IVSurrogate` to look like a ``ForwardPINN``."""

    def __init__(
        self,
        surrogate: IVSurrogate,
        normalizer: Normalizer,
        scaling,
        material,
        symlog: Optional[SymlogTransform] = None,
        n_anchor: int = 16,
        domain_si: Tuple[float, float] = (0.0, 1e-6),
    ):
        self.surrogate = surrogate
        self.normalizer = normalizer
        self.scaling = scaling
        self.material = material
        self.symlog = symlog or SymlogTransform()
        self.cfg = _AdapterCfg(n_anchor=n_anchor, domain_si=domain_si)

    # legacy code calls .parameters() to freeze the forward model
    def parameters(self):
        return self.surrogate.parameters()

    def iv_curve(self, C_si: torch.Tensor, biases) -> Tuple[torch.Tensor, torch.Tensor]:
        """Differentiable I-V: returns ``(biases_tensor, I_si_tensor)``.

        ``C_si`` is a doping profile (any length; resampled to n_anchor).
        ``biases`` is an iterable of bias values in volts.
        """
        if not isinstance(C_si, torch.Tensor):
            C_si = torch.as_tensor(C_si, dtype=torch.float32)
        C_anchor = _to_anchor(C_si.to(torch.float32), self.cfg.n_anchor)
        latent = self.scaling.doping_to_net_input(C_anchor)      # (n_anchor,), differentiable
        VT = self.scaling.V_T
        biases_t = torch.as_tensor([float(b) for b in biases], dtype=torch.float32)
        feats = []
        for b in biases_t:
            feats.append(torch.cat([latent, (b / VT).reshape(1)]))
        F = torch.stack(feats, dim=0)                            # (B, n_anchor+1)
        Fn = (F - self.normalizer.mean) / self.normalizer.std
        s = self.surrogate(Fn).reshape(-1)                       # symlog current
        I = self.symlog.inverse(s)                               # A/m^2, differentiable
        return biases_t, I


# ---------------------------------------------------------------------------
# Ensemble adapter (drop-in for DeepEnsemble)
# ---------------------------------------------------------------------------

class SurrogateEnsembleAdapter:
    """Wrap M surrogates to look like a ``DeepEnsemble``."""

    def __init__(self, members: List[SurrogateForwardAdapter], scaling, material):
        self.members = members
        self.scaling = scaling
        self.material = material

    @property
    def M(self) -> int:
        return len(self.members)

    def iv_curve(self, C_si: torch.Tensor, biases) -> Tuple[torch.Tensor, EnsemblePrediction]:
        """Returns ``(mean_tensor, EnsemblePrediction)`` in SI current units."""
        per_member = []
        for m in self.members:
            _, I = m.iv_curve(C_si, biases)
            per_member.append(I)
        stacked = torch.stack(per_member, dim=0)                 # (M, B)
        mean_t = stacked.mean(dim=0)
        samples = stacked.detach().cpu().numpy()
        pred = EnsemblePrediction(
            mean=samples.mean(axis=0),
            std=samples.std(axis=0, ddof=0),
            samples=samples,
            quantile_lo=np.quantile(samples, 0.05, axis=0),
            quantile_hi=np.quantile(samples, 0.95, axis=0),
        )
        return mean_t, pred

    def solve(self, *args, **kwargs):
        raise NotImplementedError(
            "The surrogate models terminal I-V only, not spatial fields. "
            "Use the SG solver or the pure-physics PINN for field-level solves; "
            "the surrogate adapter supports iv_curve (forward), inverse design, "
            "UQ and calibration."
        )


# ---------------------------------------------------------------------------
# Persistence: save / load a surrogate ensemble with a manifest
# ---------------------------------------------------------------------------

def save_surrogate_ensemble(
    out_dir, members: List[IVSurrogate], normalizer: Normalizer,
    scaling_name: str, T: float, doping_dim: int,
    domain_si: Tuple[float, float], bias_range: Tuple[float, float],
    symlog_I0: float = 1e-6,
) -> Path:
    """Write member checkpoints + a manifest (``type="surrogate"``)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpts = []
    for i, net in enumerate(members):
        p = out_dir / f"surrogate_member_{i:03d}.pt"
        torch.save({"state_dict": net.state_dict(),
                    "cfg": net.cfg.__dict__}, p)
        ckpts.append(str(p.resolve()))
    manifest = {
        "type": "surrogate",
        "material": {"name": scaling_name, "T": T},
        "domain_si": list(domain_si),
        "doping_dim": doping_dim,
        "bias_range": list(bias_range),
        "symlog_I0": symlog_I0,
        "normalizer": {"mean": normalizer.mean.tolist(),
                       "std": normalizer.std.tolist()},
        "checkpoints": ckpts,
        # legacy-compatible block so pipeline scripts that read
        # manifest["config"][...] work unchanged
        "config": {
            "material": {"name": scaling_name, "T": T},
            "domain_si": list(domain_si),
            "network": {"doping_dim": doping_dim},
            "dataset": {"bias_range": list(bias_range)},
        },
    }
    mpath = out_dir / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return mpath


def load_surrogate_ensemble(manifest_path) -> Tuple[SurrogateEnsembleAdapter, dict]:
    """Reconstruct a :class:`SurrogateEnsembleAdapter` from a manifest."""
    from ..physics.constants import GAAS, SILICON
    from ..physics.scaling import Scaling
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    material = {"Si": SILICON, "Silicon": SILICON, "GaAs": GAAS}[manifest["material"]["name"]]
    scaling = Scaling.for_material(material, T=manifest["material"]["T"])
    symlog = SymlogTransform(I0=manifest.get("symlog_I0", 1e-6))
    norm = Normalizer(
        mean=torch.tensor(manifest["normalizer"]["mean"], dtype=torch.float32),
        std=torch.tensor(manifest["normalizer"]["std"], dtype=torch.float32),
    )
    members = []
    for ck in manifest["checkpoints"]:
        # AUDIT_MASTER SEC-01: weights_only=False disables PyTorch >= 2.6's
        # safe-loading default, so a malicious checkpoint executes arbitrary
        # code on load. Our checkpoints hold only a state_dict and a plain
        # dict of config scalars, so weights_only=True is sufficient; we fall
        # back only for checkpoints written by older versions of this code,
        # and say so loudly.
        try:
            state = torch.load(ck, map_location="cpu", weights_only=True)
        except Exception:
            import warnings
            warnings.warn(
                f"Falling back to unsafe torch.load for {ck}: this executes "
                "arbitrary code from the checkpoint. Only do this for files "
                "you produced yourself.", RuntimeWarning, stacklevel=2)
            state = torch.load(ck, map_location="cpu", weights_only=False)
        cfg = IVSurrogateConfig(**state["cfg"])
        net = IVSurrogate(cfg)
        net.load_state_dict(state["state_dict"])
        net.eval()
        members.append(SurrogateForwardAdapter(
            net, norm, scaling, material, symlog,
            n_anchor=manifest["doping_dim"], domain_si=tuple(manifest["domain_si"]),
        ))
    return SurrogateEnsembleAdapter(members, scaling, material), manifest


def load_forward_ensemble(manifest_path):
    """Auto-detect manifest type and return the matching forward ensemble.

    - ``type == "surrogate"``  -> :class:`SurrogateEnsembleAdapter`
    - otherwise (pure-physics PINN manifest) -> ``DeepEnsemble`` via the
      legacy loader in ``scripts/run_benchmark_sweep.py``.

    This lets every pipeline script consume either forward model transparently.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("type") == "surrogate":
        return load_surrogate_ensemble(manifest_path)

    # Legacy pure-physics PINN path. This branch execs a file from the *source
    # checkout*: parents[3] is the repository root in a dev install, but in
    # site-packages it points somewhere arbitrary and scripts/ does not exist
    # (AUDIT_MASTER PKG-02). Fail with an actionable message instead of an
    # opaque AttributeError on a None spec.
    import importlib.util
    import sys

    scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
    legacy = scripts_dir / "run_benchmark_sweep.py"
    if not legacy.is_file():
        raise FileNotFoundError(
            f"Manifest {manifest_path} is not a surrogate manifest "
            f"(type={manifest.get('type')!r}), so the legacy pure-physics PINN "
            f"loader is required -- but it lives in the repository's scripts/ "
            f"directory, which is not packaged, and was not found at {legacy}. "
            "Run from a source checkout, or regenerate the ensemble with "
            "scripts/train_surrogate_ensemble.py to get a type='surrogate' "
            "manifest.")
    spec = importlib.util.spec_from_file_location("_rbs", legacy)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_rbs"] = mod
    spec.loader.exec_module(mod)
    return mod.load_ensemble(Path(manifest_path))


__all__ = [
    "SurrogateEnsembleAdapter",
    "SurrogateForwardAdapter",
    "load_forward_ensemble",
    "load_surrogate_ensemble",
    "save_surrogate_ensemble",
]
