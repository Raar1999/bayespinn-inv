"""
Inverse design of semiconductor doping profiles via input-space autodiff.

This module implements the core algorithmic contribution: given a
*frozen, trained* :class:`ForwardPINN` and a target I-V curve, recover
the underlying doping profile by minimizing

    L(C) = || I_pred(C) - I_target ||^2
         + lambda_TV * TV(C)
         + lambda_pos * ReLU(-C_minority(C))^2
         + lambda_smooth * || C'' ||^2

with respect to a *parameterization* of the doping profile. We support
three parameterizations:

1. **Free pointwise** (most flexible): ``C(x_i)`` is a free vector at the
   anchor grid. Total variation regularization is essential here.
2. **Step**: ``(N_A, N_D, x_junction)`` — a single junction.
3. **Graded**: ``(N_A, N_D, x_junction, L_grade)`` — error-function junction.

The optimization is differentiable end-to-end thanks to
:meth:`ForwardPINN.iv_curve`. Adam works well for free pointwise (default
500-2000 iters); L-BFGS for low-dimensional parameterizations (50-200 iters).

References
----------
- Chen et al., "Physics-informed neural networks for inverse problems
  in nano-optics and metamaterials," Opt. Express 28, 11618 (2020).
- Rudin, Osher & Fatemi, "Nonlinear total variation based noise removal
  algorithms," Physica D 60, 259 (1992) — origin of the TV regularizer used
  here for piecewise-constant profile recovery.
- Burger, Engl, Leitao & Markowich, "Identification of doping profiles in
  semiconductor devices," Inverse Problems 17, 1765 (2001) — the canonical
  formulation of this inverse problem, its ill-posedness, and the use of
  regularization for it. See docs/NOVELTY_AUDIT.md.

Note: a previous version of this docstring cited "Beucler et al.,
'Constraining neural networks for the inverse design of semiconductor
devices' (2022)" as the source of the TV+positivity scheme. That reference
could not be verified and has been removed (docs/AUDIT_MASTER.md CITE-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

from ..pinn.forward_pinn import ForwardPINN

# ============================================================================
# Regularizers (all act on doping in SI units)
# ============================================================================

def total_variation(C_si: torch.Tensor) -> torch.Tensor:
    """1D total variation: sum_i |C[i+1] - C[i]|.

    Encourages piecewise-constant profiles (the inductive bias for
    step / LDD junctions). For graded targets, reduce lambda_TV.
    """
    return torch.sum(torch.abs(C_si[1:] - C_si[:-1]))


def smoothness_penalty(C_si: torch.Tensor) -> torch.Tensor:
    """Squared L2 norm of the discrete second derivative.

    Promotes locally smooth profiles. Effective against high-frequency
    optimization artifacts from input-space autodiff.
    """
    d2 = C_si[2:] - 2.0 * C_si[1:-1] + C_si[:-2]
    return torch.sum(d2 ** 2)


def solubility_penalty(
    C_si: torch.Tensor, C_max: float = 1.0e26,
) -> torch.Tensor:
    """Penalize doping above the solid-solubility limit (~10^20 cm^-3
    for typical dopants in Si). Quadratic outside [-C_max, C_max].
    """
    over = torch.relu(torch.abs(C_si) - C_max)
    return torch.sum(over ** 2)


# ============================================================================
# Parameterizations
# ============================================================================

class DopingParameterization(nn.Module):
    """Abstract base class. Subclasses expose ``forward()`` returning a
    1D SI doping profile on the device grid ``x_si``.
    """

    def __init__(self, x_si: torch.Tensor):
        super().__init__()
        self.register_buffer("x_si", x_si)

    def forward(self) -> torch.Tensor:                # pragma: no cover
        raise NotImplementedError

    @torch.no_grad()
    def clamp_to_range(self, abs_min: float, abs_max: float) -> None:
        """Project parameters so the doping magnitude stays in
        ``[abs_min, abs_max]`` — the range over which the (surrogate) forward
        model is valid. Base class is a no-op; subclasses override."""
        return


class FreePointwiseDoping(DopingParameterization):
    """Free pointwise parameterization: ``C[i]`` at each grid node.

    Initializes from a provided profile. Optionally clamps the
    optimization to keep the sign fixed per-node — useful if the inverse
    problem only has to recover the *magnitude* of donors/acceptors.
    """

    def __init__(self, x_si: torch.Tensor, C_init_si: torch.Tensor):
        super().__init__(x_si)
        if C_init_si.shape[0] != x_si.shape[0]:
            raise ValueError("C_init_si must match x_si shape.")
        self.C = nn.Parameter(C_init_si.detach().clone())

    def forward(self) -> torch.Tensor:
        return self.C

    @torch.no_grad()
    def clamp_to_range(self, abs_min: float, abs_max: float) -> None:
        sign = torch.sign(self.C)
        mag = self.C.abs().clamp(abs_min, abs_max)
        self.C.copy_(sign * mag)


class StepJunctionDoping(DopingParameterization):
    """Single PN step junction parameterization.

    Parameters: ``log_N_A, log_N_D, x_junction``. Working in log-space
    keeps the gradient well-conditioned across the typical 10^21 -- 10^25
    m^-3 range.

    The transition is a fixed sharp sigmoid of width ``transition_width``
    metres to keep gradients finite.
    """

    def __init__(
        self,
        x_si: torch.Tensor,
        log_N_A_init: float = np.log(1e22),
        log_N_D_init: float = np.log(1e22),
        x_junction_init: float = 5e-7,
        transition_width: float = 1e-8,
    ):
        super().__init__(x_si)
        self.log_N_A = nn.Parameter(torch.tensor(float(log_N_A_init)))
        self.log_N_D = nn.Parameter(torch.tensor(float(log_N_D_init)))
        # Junction position is parameterized in NORMALIZED units (a logit of
        # the fractional position in the domain) so its optimization scale is
        # O(1), matching log_N. Optimizing the raw position in metres (~5e-7)
        # alongside log_N (~50) under a single learning rate is unstable —
        # the position slams to the domain boundary. The fractional form is
        # also automatically bounded to the domain.
        x0 = float(x_si.min()); Lx = float(x_si.max() - x_si.min())
        self.register_buffer("_x0", torch.tensor(x0))
        self.register_buffer("_Lx", torch.tensor(Lx))
        u0 = min(max((float(x_junction_init) - x0) / Lx, 1e-3), 1 - 1e-3)
        self.u_junction = nn.Parameter(torch.tensor(float(np.log(u0 / (1 - u0)))))
        self.register_buffer("transition_width",
                              torch.tensor(float(transition_width)))

    @property
    def x_junction(self) -> torch.Tensor:
        return self._x0 + self._Lx * torch.sigmoid(self.u_junction)

    def forward(self) -> torch.Tensor:
        N_A = torch.exp(self.log_N_A)
        N_D = torch.exp(self.log_N_D)
        sigmoid = torch.sigmoid(
            (self.x_si - self.x_junction) / self.transition_width
        )
        return -N_A * (1.0 - sigmoid) + N_D * sigmoid

    @torch.no_grad()
    def clamp_to_range(self, abs_min: float, abs_max: float) -> None:
        # x_junction is auto-bounded by the sigmoid; only clamp doping levels.
        lo, hi = float(np.log(abs_min)), float(np.log(abs_max))
        self.log_N_A.clamp_(lo, hi)
        self.log_N_D.clamp_(lo, hi)


class GradedJunctionDoping(DopingParameterization):
    """Error-function-graded junction parameterization.

    Parameters: ``log_N_A, log_N_D, x_junction, log_L_grade``.
    """

    def __init__(
        self,
        x_si: torch.Tensor,
        log_N_A_init: float = float(np.log(1e22)),
        log_N_D_init: float = float(np.log(1e22)),
        x_junction_init: float = 5e-7,
        log_L_grade_init: float = float(np.log(2e-8)),
    ):
        super().__init__(x_si)
        self.log_N_A = nn.Parameter(torch.tensor(float(log_N_A_init)))
        self.log_N_D = nn.Parameter(torch.tensor(float(log_N_D_init)))
        x0 = float(x_si.min()); Lx = float(x_si.max() - x_si.min())
        self.register_buffer("_x0", torch.tensor(x0))
        self.register_buffer("_Lx", torch.tensor(Lx))
        u0 = min(max((float(x_junction_init) - x0) / Lx, 1e-3), 1 - 1e-3)
        self.u_junction = nn.Parameter(torch.tensor(float(np.log(u0 / (1 - u0)))))
        self.log_L_grade = nn.Parameter(torch.tensor(float(log_L_grade_init)))

    @property
    def x_junction(self) -> torch.Tensor:
        return self._x0 + self._Lx * torch.sigmoid(self.u_junction)

    def forward(self) -> torch.Tensor:
        N_A = torch.exp(self.log_N_A)
        N_D = torch.exp(self.log_N_D)
        L_g = torch.exp(self.log_L_grade)
        # torch.erf is differentiable
        e = torch.erf((self.x_si - self.x_junction) / L_g)
        return 0.5 * (N_D - N_A) + 0.5 * (N_D + N_A) * e

    @torch.no_grad()
    def clamp_to_range(self, abs_min: float, abs_max: float) -> None:
        lo, hi = float(np.log(abs_min)), float(np.log(abs_max))
        self.log_N_A.clamp_(lo, hi)
        self.log_N_D.clamp_(lo, hi)


# ============================================================================
# Inverse-design driver
# ============================================================================

@dataclass
class InverseConfig:
    n_iters: int = 1_000
    lr: float = 1e-2
    optimizer: str = "adam"               # "adam" or "lbfgs"
    lambda_TV: float = 0.0                # tune per-target
    lambda_smooth: float = 1.0e-6
    lambda_solubility: float = 1.0
    C_max_si: float = 1.0e26              # ~1e20 cm^-3 solid solubility
    grad_clip: float = 1.0
    log_every: int = 50
    seed: int = 0
    # Current-matching space for the data loss. "linear" is the legacy
    # relative-L2 in SI (dominated by high-bias points). "symlog" matches
    # sign(I)*log10(1+|I|/I0), which is well-conditioned across the ~13
    # orders of magnitude of diode I-V and is the right objective for the
    # SG-supervised surrogate forward model.
    match_space: str = "linear"
    symlog_I0: float = 1.0e-6
    # Constrain the doping magnitude to the forward model's valid range
    # after each optimizer step. Essential when the forward model is a
    # surrogate (only valid where it was trained); prevents the optimizer
    # from exploiting out-of-range extrapolation and diverging.
    clamp_doping: bool = False
    C_min_abs: float = 5.0e20
    C_max_abs: float = 5.0e22


@dataclass
class InverseResult:
    C_recovered_si: torch.Tensor          # final profile, SI units
    history: List[Dict[str, float]]       # per-log iteration
    converged: bool
    final_loss: float
    target_biases: torch.Tensor
    target_currents_si: torch.Tensor
    predicted_currents_si: torch.Tensor


class InverseDesigner:
    """Run inverse design against a target I-V curve.

    The forward solver is frozen (treated as a black-box differentiable
    function of doping). For ensembles, pass the *mean* ForwardPINN; for
    explicit uncertainty propagation, run the designer once per ensemble
    member and aggregate (see :mod:`active_learning`).
    """

    def __init__(
        self,
        forward: ForwardPINN,
        cfg: Optional[InverseConfig] = None,
    ):
        self.forward = forward
        self.cfg = cfg or InverseConfig()
        # Freeze the forward model
        for p in self.forward.parameters():
            p.requires_grad_(False)

    def design(
        self,
        param: DopingParameterization,
        target_biases: torch.Tensor,
        target_currents_si: torch.Tensor,
    ) -> InverseResult:
        """Optimize ``param`` to match the target I-V.

        Parameters
        ----------
        param : DopingParameterization
            A trainable parameterization. Its parameters are the
            optimization variables.
        target_biases : (B,) tensor of bias values (V)
        target_currents_si : (B,) tensor of measured currents (A/m^2)
        """
        torch.manual_seed(self.cfg.seed)
        target_biases = target_biases.to(device=self.forward.cfg.device,
                                           dtype=self.forward.cfg.dtype)
        target_currents_si = target_currents_si.to(
            device=self.forward.cfg.device, dtype=self.forward.cfg.dtype)

        if self.cfg.optimizer.lower() == "adam":
            opt = torch.optim.Adam(param.parameters(), lr=self.cfg.lr)
        elif self.cfg.optimizer.lower() == "lbfgs":
            opt = torch.optim.LBFGS(
                param.parameters(), lr=self.cfg.lr, history_size=20,
                max_iter=20, line_search_fn="strong_wolfe",
            )
        else:
            raise ValueError(f"Unknown optimizer {self.cfg.optimizer!r}")

        history: List[Dict[str, float]] = []
        last_diag = {}

        def _step_loss(do_backward: bool = True) -> torch.Tensor:
            opt.zero_grad(set_to_none=True)
            C_si = param.forward()
            biases, I_pred = self.forward.iv_curve(C_si, list(target_biases))
            # Data loss: match either in linear (relative-L2) or symlog space.
            if self.cfg.match_space.lower() == "symlog":
                I0 = self.cfg.symlog_I0
                def _sl(I):
                    return torch.sign(I) * torch.log10(1.0 + torch.abs(I) / I0)
                data = torch.mean((_sl(I_pred) - _sl(target_currents_si)) ** 2)
            else:
                # Match by log magnitude when target spans many orders of mag,
                # otherwise straight L2. Relative error, smooth and graceful.
                scale = target_currents_si.abs().max().clamp(min=1e-6)
                rel = (I_pred - target_currents_si) / scale
                data = torch.mean(rel ** 2)
            # Regularization penalties. Compute total-variation and
            # smoothness on a NORMALIZED profile (C / |C|max) so the squared
            # second difference cannot overflow float32 — raw doping ~1e22
            # gives d2^2 ~ 1e45 > 3.4e38 (float32 max) -> inf, and then
            # lambda*inf = 0*inf = NaN would poison the loss even when the
            # weight is zero. Each term is added only when its weight > 0.
            C_ref = C_si.abs().max().clamp(min=1e-6)
            C_norm = C_si / C_ref
            loss = data
            if self.cfg.lambda_TV > 0:
                tv = total_variation(C_norm)
                loss = loss + self.cfg.lambda_TV * tv
            else:
                tv = torch.zeros((), dtype=C_si.dtype, device=C_si.device)
            if self.cfg.lambda_smooth > 0:
                sm = smoothness_penalty(C_norm)
                loss = loss + self.cfg.lambda_smooth * sm
            else:
                sm = torch.zeros((), dtype=C_si.dtype, device=C_si.device)
            if self.cfg.lambda_solubility > 0:
                sol = solubility_penalty(C_si, self.cfg.C_max_si)
                loss = loss + self.cfg.lambda_solubility * sol / (self.cfg.C_max_si ** 2)
            else:
                sol = torch.zeros((), dtype=C_si.dtype, device=C_si.device)
            last_diag.clear()
            last_diag.update({
                "loss_total": float(loss.detach()),
                "loss_data":  float(data.detach()),
                "loss_TV":    float(tv.detach()),
                "loss_smooth": float(sm.detach()),
                "loss_solubility": float(sol.detach()),
                "I_max_pred":   float(I_pred.detach().abs().max()),
                "I_max_target": float(target_currents_si.abs().max()),
            })
            if do_backward:
                loss.backward()
                if self.cfg.grad_clip is not None:
                    torch.nn.utils.clip_grad_norm_(
                        param.parameters(), self.cfg.grad_clip)
            return loss

        for it in range(self.cfg.n_iters):
            if self.cfg.optimizer.lower() == "adam":
                _step_loss(do_backward=True)
                opt.step()
            else:
                opt.step(lambda: _step_loss(do_backward=True))

            if self.cfg.clamp_doping:
                param.clamp_to_range(self.cfg.C_min_abs, self.cfg.C_max_abs)

            if it % self.cfg.log_every == 0 or it == self.cfg.n_iters - 1:
                d = dict(last_diag); d["iter"] = it
                history.append(d)

        # Final eval
        with torch.no_grad():
            C_si = param.forward()
            biases, I_pred = self.forward.iv_curve(C_si, list(target_biases))
        return InverseResult(
            C_recovered_si=C_si.detach(),
            history=history,
            converged=last_diag.get("loss_data", float("inf")) < 1e-3,
            final_loss=last_diag.get("loss_total", float("nan")),
            target_biases=target_biases.detach(),
            target_currents_si=target_currents_si.detach(),
            predicted_currents_si=I_pred.detach(),
        )


__all__ = [
    "DopingParameterization",
    "FreePointwiseDoping",
    "GradedJunctionDoping",
    "InverseConfig",
    "InverseDesigner",
    "InverseResult",
    "StepJunctionDoping",
    "smoothness_penalty",
    "solubility_penalty",
    "total_variation",
]
