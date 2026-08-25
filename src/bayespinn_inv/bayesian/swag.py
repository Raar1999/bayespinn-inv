"""
SWAG (Stochastic Weight Averaging-Gaussian) for the forward PINN.

Implements Maddox et al. (NeurIPS 2019). The procedure:

1. Train the network normally to a "warm-start" point (e.g., after the
   curriculum phase completes).
2. During additional SWA-phase epochs at constant or cyclical LR, collect
   K snapshots of the parameter vector ``theta_k``.
3. Maintain running statistics:
       theta_bar         (running mean, shape D)
       theta2_bar        (running mean of squares, shape D, for diagonal var)
       D_dev             (deviation matrix, shape D x K, low-rank component)
4. At test time, sample
       theta ~ N(theta_bar, Sigma)
   with  Sigma = 0.5 * diag(theta2_bar - theta_bar^2) + 0.5/(K-1) * D_dev D_dev^T
5. Forward through the network with the sampled parameters; aggregate.

For our setting, SWAG is best used as a *complement* to ensembles when
compute budget is tight (one training run -> multiple samples). The
aggregation API matches :class:`DeepEnsemble`.

Caveats
-------
SWAG assumes the loss surface is locally Gaussian around the SWA mean —
a strong assumption that often fails for PINN losses with multiple
basins. The :class:`bayespinn_inv.calibration` metrics will reveal
whether SWAG is well-calibrated for a given problem; if not, fall back
to ensembles.
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
from .ensembles import EnsemblePrediction


def _flatten_params(model: nn.Module) -> torch.Tensor:
    """Return a single 1-D tensor concatenating all model parameters."""
    return torch.cat([p.detach().reshape(-1) for p in model.parameters()])


def _unflatten_params(flat: torch.Tensor, model: nn.Module) -> None:
    """In-place set model parameters from a flat 1-D tensor."""
    idx = 0
    for p in model.parameters():
        n = p.numel()
        p.data.copy_(flat[idx:idx + n].reshape(p.shape))
        idx += n


@dataclass
class SWAGConfig:
    """SWAG hyperparameters."""
    max_rank: int = 20            # K, deviation-matrix column count
    T_samples: int = 30           # test-time MC samples
    scale: float = 0.5            # variance scale (paper uses 0.5)
    seed: int = 0


class SWAGRecorder:
    """Collects parameter snapshots during the SWA phase of training.

    Usage::

        rec = SWAGRecorder(net, cfg=SWAGConfig(max_rank=20))
        # ... training loop ...
        for epoch in range(swa_epochs):
            # one optimizer step
            train_one_epoch(...)
            rec.collect()    # at the end of every epoch

        # ... at inference ...
        swag = SWAG(forward, recorder=rec, cfg=...)
    """

    def __init__(self, model: nn.Module, cfg: Optional[SWAGConfig] = None):
        self.model = model
        self.cfg = cfg or SWAGConfig()
        self.n_collected = 0
        flat = _flatten_params(model)
        D = flat.numel()
        self.theta_bar = torch.zeros_like(flat)
        self.theta2_bar = torch.zeros_like(flat)
        self.D_dev = torch.zeros((D, self.cfg.max_rank), dtype=flat.dtype,
                                  device=flat.device)

    def collect(self) -> None:
        flat = _flatten_params(self.model)
        n = self.n_collected
        self.theta_bar = (n * self.theta_bar + flat) / (n + 1)
        self.theta2_bar = (n * self.theta2_bar + flat ** 2) / (n + 1)
        # Roll the deviation matrix: drop the oldest column, append new
        dev = flat - self.theta_bar
        self.D_dev = torch.cat([self.D_dev[:, 1:], dev.unsqueeze(-1)], dim=1)
        self.n_collected += 1

    @property
    def diag_variance(self) -> torch.Tensor:
        return torch.clamp(self.theta2_bar - self.theta_bar ** 2, min=0.0)

    def sample(self, generator: Optional[torch.Generator] = None) -> torch.Tensor:
        """Sample one parameter vector from the SWAG posterior."""
        D = self.theta_bar.numel()
        eff_K = min(self.n_collected, self.cfg.max_rank)
        if eff_K < 2:
            # Not enough samples yet; return mean
            return self.theta_bar.clone()
        z1 = torch.randn(D, generator=generator, device=self.theta_bar.device,
                          dtype=self.theta_bar.dtype)
        z2 = torch.randn(eff_K, generator=generator,
                          device=self.theta_bar.device,
                          dtype=self.theta_bar.dtype)
        diag_term = torch.sqrt(self.cfg.scale * self.diag_variance) * z1
        # Use the most recent eff_K columns of D_dev
        D_eff = self.D_dev[:, -eff_K:]
        low_rank_term = (D_eff @ z2) * np.sqrt(self.cfg.scale / max(eff_K - 1, 1))
        return self.theta_bar + diag_term + low_rank_term


class SWAG(nn.Module):
    """Test-time SWAG predictor wrapping a ForwardPINN."""

    def __init__(
        self,
        forward_pinn: ForwardPINN,
        recorder: SWAGRecorder,
        cfg: Optional[SWAGConfig] = None,
    ):
        super().__init__()
        self.forward_pinn = forward_pinn
        self.recorder = recorder
        self.cfg = cfg or recorder.cfg

    @property
    def M(self) -> int:
        return self.cfg.T_samples

    @property
    def scaling(self) -> Scaling:
        return self.forward_pinn.scaling

    @property
    def material(self) -> Material:
        return self.forward_pinn.material

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

    def iv_curve(
        self,
        doping_si: torch.Tensor,
        biases: Sequence[float],
        with_grad: bool = False,
    ) -> Tuple[torch.Tensor, EnsemblePrediction]:
        gen = torch.Generator(device=self.recorder.theta_bar.device).manual_seed(
            self.cfg.seed
        )
        # Snapshot original params so we can restore
        orig = _flatten_params(self.forward_pinn.network)
        samples: List[torch.Tensor] = []
        try:
            for _ in range(self.cfg.T_samples):
                theta = self.recorder.sample(generator=gen)
                _unflatten_params(theta, self.forward_pinn.network)
                _, I = self.forward_pinn.iv_curve(doping_si, biases)
                samples.append(I.detach())
            stacked = torch.stack(samples, dim=0)
            mean_t = stacked.mean(dim=0)
            det_samples = stacked.detach().cpu().numpy()
            return mean_t, self._aggregate(det_samples)
        finally:
            _unflatten_params(orig, self.forward_pinn.network)

    def solve(
        self,
        doping_si: torch.Tensor,
        bias: float,
    ) -> Tuple[DeviceState, Dict[str, EnsemblePrediction]]:
        gen = torch.Generator(device=self.recorder.theta_bar.device).manual_seed(
            self.cfg.seed
        )
        orig = _flatten_params(self.forward_pinn.network)
        states: List[DeviceState] = []
        try:
            for _ in range(self.cfg.T_samples):
                theta = self.recorder.sample(generator=gen)
                _unflatten_params(theta, self.forward_pinn.network)
                states.append(self.forward_pinn.solve(doping_si, bias))
            x = states[0].x
            phi_s = np.stack([s.phi for s in states], axis=0)
            n_s   = np.stack([s.n   for s in states], axis=0)
            p_s   = np.stack([s.p   for s in states], axis=0)
            Jn_s  = np.stack([s.Jn  for s in states], axis=0)
            Jp_s  = np.stack([s.Jp  for s in states], axis=0)
            agg = {
                "phi": self._aggregate(phi_s),
                "n":   self._aggregate(np.log10(np.maximum(n_s, 1e-6))),
                "p":   self._aggregate(np.log10(np.maximum(p_s, 1e-6))),
                "Jn":  self._aggregate(Jn_s),
                "Jp":  self._aggregate(Jp_s),
            }
            mean_state = DeviceState(
                x=x,
                phi=agg["phi"].mean,
                n=np.exp(np.log(10.0) * agg["n"].mean),
                p=np.exp(np.log(10.0) * agg["p"].mean),
                Jn=agg["Jn"].mean, Jp=agg["Jp"].mean,
                doping=states[0].doping, bias=bias,
                converged=True, iterations=0, residuals=[],
            )
            return mean_state, agg
        finally:
            _unflatten_params(orig, self.forward_pinn.network)


__all__ = ["SWAG", "SWAGConfig", "SWAGRecorder"]
