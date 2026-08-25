"""
MC-Dropout uncertainty quantification for the forward PINN.

This is the *secondary* Bayesian method in our pipeline (Deep Ensembles
remain primary). Following Gal & Ghahramani (2016), we approximate
posterior predictive uncertainty by performing T stochastic forward
passes with dropout *active at test time*. Variance across the T samples
serves as a posterior variance estimate.

Requirements
------------
The wrapped :class:`SemiconductorPINN` must have been built with
``PINNConfig.dropout > 0`` and trained with dropout active. Calling this
wrapper on a network with ``dropout=0`` yields T identical samples and
zero variance, which we detect and warn about.

Aggregation API matches :class:`DeepEnsemble`: the same
:class:`EnsemblePrediction` dataclass and the same ``iv_curve``,
``solve`` signatures are returned. This means downstream code (inverse
design, calibration, plots) is agnostic to the UQ method.
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from ..physics.constants import Material
from ..physics.scaling import Scaling
from ..pinn.forward_pinn import ForwardPINN
from ..solvers.scharfetter_gummel import DeviceState
from .ensembles import EnsemblePrediction


def _set_dropout_train_only(module: nn.Module) -> None:
    """Set all Dropout submodules to train() mode (active) while leaving
    BatchNorm and other layers in eval() mode. We don't use BatchNorm in
    the PINN, but this is the standard MC-Dropout pattern.
    """
    for m in module.modules():
        if isinstance(m, (nn.Dropout, nn.Dropout1d, nn.Dropout2d, nn.Dropout3d)):
            m.train()


class MCDropoutPINN(nn.Module):
    """MC-Dropout wrapper around a single ForwardPINN.

    Behaves like a DeepEnsemble of "size" T at inference time.
    """

    def __init__(
        self,
        forward_pinn: ForwardPINN,
        T: int = 100,
        seed: int = 0,
    ):
        super().__init__()
        self.forward_pinn = forward_pinn
        self.T = T
        self.seed = seed
        # Sanity check: warn if dropout is zero.
        dropouts = [m for m in self.forward_pinn.network.modules()
                    if isinstance(m, nn.Dropout)]
        if not dropouts:
            warnings.warn(
                "MCDropoutPINN: no Dropout layers in the wrapped network. "
                "MC-Dropout will return zero variance.",
                stacklevel=2,
            )
        elif all(getattr(d, "p", 0.0) == 0.0 for d in dropouts):
            warnings.warn(
                "MCDropoutPINN: all Dropout p=0 in the wrapped network.",
                stacklevel=2,
            )

    @property
    def scaling(self) -> Scaling:
        return self.forward_pinn.scaling

    @property
    def material(self) -> Material:
        return self.forward_pinn.material

    @property
    def M(self) -> int:
        """Match the DeepEnsemble API."""
        return self.T

    # ------------------------------------------------------------------

    def _enable_test_dropout(self) -> None:
        self.forward_pinn.network.eval()
        _set_dropout_train_only(self.forward_pinn.network)

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

    def iv_curve(
        self,
        doping_si: torch.Tensor,
        biases: Sequence[float],
        with_grad: bool = False,
    ) -> Tuple[torch.Tensor, EnsemblePrediction]:
        """T stochastic forward passes; aggregate.

        ``with_grad`` is supported but note that gradients are only correct
        if the dropout masks are *frozen* across the inverse-design loop —
        which is NOT done here. So ``with_grad=True`` should be used only
        for first-derivative diagnostic purposes, not for input-space
        inverse-design through MC-Dropout.
        """
        torch.manual_seed(self.seed)
        self._enable_test_dropout()
        samples: List[torch.Tensor] = []
        for _ in range(self.T):
            _, I = self.forward_pinn.iv_curve(doping_si, biases)
            samples.append(I if with_grad else I.detach())
        stacked = torch.stack(samples, dim=0)              # (T, B)
        mean_t = stacked.mean(dim=0)
        det_samples = stacked.detach().cpu().numpy()
        return mean_t, self._aggregate(det_samples)

    def solve(
        self,
        doping_si: torch.Tensor,
        bias: float,
    ) -> Tuple[DeviceState, Dict[str, EnsemblePrediction]]:
        torch.manual_seed(self.seed)
        self._enable_test_dropout()
        states: List[DeviceState] = []
        for _ in range(self.T):
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


__all__ = ["MCDropoutPINN"]
