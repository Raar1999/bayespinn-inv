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
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from ..pinn.forward_pinn import ForwardPINN
from ..pinn.network import SemiconductorPINN, PINNConfig
from ..physics.constants import Material
from ..physics.scaling import Scaling
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


__all__ = ["DeepEnsemble", "EnsemblePrediction"]
