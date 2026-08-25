"""
PDE residual losses for the semiconductor PINN, in scaled units.

All quantities are scaled by the :class:`Scaling` object exposed in
``bayespinn_inv.physics.scaling``. The network outputs are

    phi_s   :   scaled electrostatic potential
    log_n   :   ln(n / n_i)
    log_p   :   ln(p / n_i)

and the carrier densities are recovered as ``n_s = exp(log_n)``,
``p_s = exp(log_p)``. This log parameterization is *essential* for
numerical health: at room temperature, the carrier density spans 20+
orders of magnitude between the bulk and depletion region of a PN
junction, and a naive linear parameterization makes the loss
ill-conditioned by ~10^20.

Loss components
---------------
1. **Poisson residual**:
       r_phi = d^2 phi_s / dx_s^2 - n_s + p_s + C_s
   where C_s = (N_D - N_A) / n_i is the *signed* scaled net doping.

2. **Electron continuity (steady-state)**:
       J_n_s   = mu_n_s * exp(log_n) * d(log_n - phi_s)/dx_s
       r_n     = dJ_n_s/dx_s - R_s
   The log-current form (a.k.a. quasi-Fermi gradient times density)
   avoids the need to differentiate exp(log_n) directly inside the
   divergence — only one autograd pass per term suffices, and the
   numerical conditioning is ~6 orders of magnitude better than the
   naive form.

3. **Hole continuity (steady-state)**:
       J_p_s   = -mu_p_s * exp(log_p) * d(log_p + phi_s)/dx_s
       r_p     = dJ_p_s/dx_s + R_s

4. **Boundary loss**: enforce ohmic contact conditions (charge
   neutrality + equilibrium product) and Dirichlet potential at the
   two terminals. See :func:`ohmic_boundary_values`.

5. **Optional data loss**: supervised L2 to ground-truth fields
   (typically from the SG oracle), if provided.

References
----------
- De Mari, "An accurate numerical steady-state one-dimensional solution
  of the P-N junction," Solid-State Electron. (1968).
- Raissi, Perdikaris, Karniadakis, J. Comput. Phys. 378, 686 (2019).
- Wang, Sankaran, Perdikaris, "On the eigenvector bias of Fourier feature
  networks: from regression to solving multi-scale PDEs with PINNs,"
  CMAME 384 (2021).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn

# ============================================================================
# Autograd helpers
# ============================================================================

def _grad(y: torch.Tensor, x: torch.Tensor, create_graph: bool = True) -> torch.Tensor:
    """First derivative of ``y`` w.r.t. ``x``, shape-preserving on the last dim.

    Both ``y`` and ``x`` are expected to be (N, 1) tensors with ``x.requires_grad``.
    Returns (N, 1).
    """
    g, = torch.autograd.grad(
        y, x, grad_outputs=torch.ones_like(y),
        create_graph=create_graph, retain_graph=True,
    )
    return g


# ============================================================================
# Boundary helpers
# ============================================================================

def ohmic_boundary_values(
    C_s_left: torch.Tensor,
    C_s_right: torch.Tensor,
    V_a_s: torch.Tensor,
) -> Dict[str, torch.Tensor]:
    """Compute ohmic-contact boundary values in scaled units.

    At an ohmic contact, two conditions hold simultaneously:
        (i)  charge neutrality: n - p - C = 0
        (ii) equilibrium product: n * p = n_i^2  =>  n_s * p_s = 1

    Eliminating ``p`` gives ``n_s = (C_s + sqrt(C_s^2 + 4)) / 2``, which is
    exactly ``exp(asinh(C_s / 2))``. Since this function returns logs, the
    quadratic never has to be formed at all:

        log n_s = asinh(C_s / 2)        log p_s = -asinh(C_s / 2)

    This is branchless and exact in every dtype. The earlier form selected the
    majority carrier with ``torch.where`` over the two roots; ``torch.where``
    evaluates both branches, and for large ``|C_s|`` the discarded root
    ``0.5 * (-C_s + sqrt(C_s^2 + 4))`` underflows to exactly zero, so its
    reciprocal was ``inf`` and the backward pass produced ``0 * inf = NaN``
    in the *selected* branch. Measured onset: ``C_s ~ 1.4e8`` in float64 (the
    top 21.4% of the documented 1e21-1e25 m^-3 doping range) and ``C_s ~ 7.1e3``
    in float32 -- below the whole range, and float32 is the dtype the networks
    train in. See AUDIT_g0 GRAD-02/GRAD-03 and ``tests/test_ohmic_gradient_g0.py``.

    The derivative is ``d(log n_s)/dC_s = 1 / sqrt(4 + C_s^2)``, finite for
    every finite ``C_s``.

    The Dirichlet potential is chosen so that the *left contact's*
    electron quasi-Fermi level is the reference (phi_n_left = 0):
        phi_s_left  = ln(n_s_left)
        phi_s_right = ln(n_s_right) - V_a_s
    where V_a_s is applied at the right contact. With V_a > 0 being
    forward bias for a P-on-left / N-on-right junction, this convention
    *reduces* the barrier (phi drop across the junction) as V_a grows.
    Matches the SG solver convention in
    ``solvers/scharfetter_gummel.py``.

    Parameters
    ----------
    C_s_left, C_s_right : scalar or batched tensor
        Scaled net doping at the two contacts.
    V_a_s : scalar or batched tensor
        Scaled applied bias at the right contact.

    Returns
    -------
    dict with keys ``phi_s_left, phi_s_right, log_n_left, log_n_right,
    log_p_left, log_p_right``, broadcast to a common shape.
    """
    # AUDIT_g0 GRAD-02/GRAD-03. Charge neutrality n - p - C = 0 with n*p = 1 gives
    # n = (C + sqrt(C^2 + 4)) / 2, which is exactly exp(asinh(C / 2)). Working in
    # log space removes the quadratic entirely:
    #
    #     log n = asinh(C / 2)      log p = -asinh(C / 2)
    #
    # There is no branch, no subtraction of nearly-equal numbers, and no root to
    # discard, so nothing can overflow and no dtype has a cancellation threshold.
    # The derivative is 1 / sqrt(4 + C^2), finite for every finite C -- where the
    # previous torch.where form returned NaN above C_s ~ 1.4e8 in float64 and
    # above C_s ~ 7.1e3 in float32 (i.e. below the whole documented envelope).
    # The function already returns logs, so the exponential is never taken.
    log_n_L = torch.asinh(0.5 * C_s_left)
    log_p_L = -log_n_L
    log_n_R = torch.asinh(0.5 * C_s_right)
    log_p_R = -log_n_R
    phi_s_L = log_n_L                # reference choice (p-side grounded)
    # Same convention as SG: V_a > 0 = forward bias = barrier reduction.
    # For a P-on-left / N-on-right junction, that means phi_right is
    # *decreased* by V_a relative to its equilibrium value log(n_R).
    phi_s_R = log_n_R - V_a_s
    return dict(
        phi_s_left=phi_s_L, phi_s_right=phi_s_R,
        log_n_left=log_n_L, log_n_right=log_n_R,
        log_p_left=log_p_L, log_p_right=log_p_R,
    )


# ============================================================================
# Residual computation
# ============================================================================

@dataclass
class PhysicsParams:
    """Scaled physics parameters needed to evaluate the residuals."""
    mu_n_s: float                          # scaled electron mobility
    mu_p_s: float                          # scaled hole mobility
    tau_n_s: float                         # scaled SRH electron lifetime
    tau_p_s: float                         # scaled SRH hole lifetime
    enable_srh: bool = True
    # Normalization scales (set per-batch to make loss dimensionless).
    # Default to 1.0 (no normalization). Override e.g. with the max |C_s| on
    # the batch for the Poisson residual.
    poisson_scale: float = 1.0
    current_scale: float = 1.0


def pde_residuals(
    network: nn.Module,
    x_s: torch.Tensor,                     # (N, 1) requires_grad=True
    V_a_s: torch.Tensor,                   # (N, 1)
    doping_latent: torch.Tensor,           # (N, doping_dim)
    C_s: torch.Tensor,                     # (N, 1) scaled net doping at x_s
    params: PhysicsParams,
) -> Dict[str, torch.Tensor]:
    """Evaluate Poisson + continuity residuals at collocation points.

    The residuals are normalized by ``params.poisson_scale`` and
    ``params.current_scale`` respectively so that all loss components
    have comparable magnitudes during training — this is essential when
    doping is in the 10^22 m^-3 range (|C_s| ~ 10^6 in scaled units, so
    the unnormalized Poisson residual is ~10^12).

    Returns a dict with ``r_phi, r_n, r_p`` (already normalized) and the
    intermediate fields ``phi_s, log_n, log_p, J_n_s, J_p_s, R_s`` for
    diagnostics.
    """
    if not x_s.requires_grad:
        x_s = x_s.requires_grad_(True)
    phi_s, log_n, log_p = network(x_s, V_a_s, doping_latent)

    # First derivatives
    dphi  = _grad(phi_s, x_s)
    dlogn = _grad(log_n, x_s)
    dlogp = _grad(log_p, x_s)

    n_s = torch.exp(log_n)
    p_s = torch.exp(log_p)

    # Currents (log-density / quasi-Fermi-gradient form)
    J_n_s = params.mu_n_s * n_s * (dlogn - dphi)
    J_p_s = -params.mu_p_s * p_s * (dlogp + dphi)

    # Second derivative (Poisson) and divergences (continuity)
    d2phi  = _grad(dphi,  x_s)
    dJ_n_s = _grad(J_n_s, x_s)
    dJ_p_s = _grad(J_p_s, x_s)

    # SRH recombination
    if params.enable_srh:
        denom = params.tau_p_s * (n_s + 1.0) + params.tau_n_s * (p_s + 1.0)
        R_s = (n_s * p_s - 1.0) / denom
    else:
        R_s = torch.zeros_like(n_s)

    r_phi = (d2phi - n_s + p_s + C_s) / params.poisson_scale
    r_n   = (dJ_n_s - R_s) / params.current_scale
    r_p   = (dJ_p_s + R_s) / params.current_scale

    return dict(
        r_phi=r_phi, r_n=r_n, r_p=r_p,
        phi_s=phi_s, log_n=log_n, log_p=log_p,
        J_n_s=J_n_s, J_p_s=J_p_s, R_s=R_s,
        dphi=dphi,
    )


def boundary_residuals(
    network: nn.Module,
    x_s_bdy: torch.Tensor,                 # (2, 1) -- left and right
    V_a_s: torch.Tensor,                   # (2, 1) bias broadcast over the 2 bdy pts
    doping_latent: torch.Tensor,           # (2, doping_dim)
    C_s_bdy: torch.Tensor,                 # (2, 1) doping at the two contacts
) -> Dict[str, torch.Tensor]:
    """Evaluate Dirichlet residuals at the two ohmic contacts.

    The boundary point ordering convention is row 0 = left, row 1 = right.
    """
    phi_s, log_n, log_p = network(x_s_bdy, V_a_s, doping_latent)
    bdy = ohmic_boundary_values(
        C_s_left=C_s_bdy[0:1], C_s_right=C_s_bdy[1:2], V_a_s=V_a_s[0:1],
    )
    r_phi_L = phi_s[0:1] - bdy["phi_s_left"]
    r_phi_R = phi_s[1:2] - bdy["phi_s_right"]
    r_n_L   = log_n[0:1] - bdy["log_n_left"]
    r_n_R   = log_n[1:2] - bdy["log_n_right"]
    r_p_L   = log_p[0:1] - bdy["log_p_left"]
    r_p_R   = log_p[1:2] - bdy["log_p_right"]
    return dict(
        r_phi_L=r_phi_L, r_phi_R=r_phi_R,
        r_n_L=r_n_L, r_n_R=r_n_R,
        r_p_L=r_p_L, r_p_R=r_p_R,
    )


# ============================================================================
# Loss weights and aggregation
# ============================================================================

@dataclass
class LossWeights:
    """Component weights for the combined PINN loss.

    Defaults are calibrated to roughly balance the magnitudes of the three
    residuals at initialization for a Si PN junction. The boundary weight
    is intentionally large because boundary conditions are exact Dirichlet
    constraints whose violation propagates into the bulk.

    Use :class:`NTKAdaptiveWeights` for an adaptive alternative (Wang et al.
    2022).
    """
    w_phi: float = 1.0
    w_n: float = 1.0
    w_p: float = 1.0
    w_bdy: float = 100.0
    w_data: float = 1.0


def total_loss(
    res: Dict[str, torch.Tensor],
    bdy: Dict[str, torch.Tensor],
    weights: LossWeights,
    data_terms: Optional[Dict[str, torch.Tensor]] = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Aggregate residual dictionaries into a scalar loss.

    Returns
    -------
    loss : scalar tensor
    diag : dict of per-component MSEs (detached floats), for logging.
    """
    mse = lambda t: torch.mean(t ** 2)
    l_phi = mse(res["r_phi"])
    l_n   = mse(res["r_n"])
    l_p   = mse(res["r_p"])
    l_bdy = (
        mse(bdy["r_phi_L"]) + mse(bdy["r_phi_R"]) +
        mse(bdy["r_n_L"])   + mse(bdy["r_n_R"])   +
        mse(bdy["r_p_L"])   + mse(bdy["r_p_R"])
    )
    loss = (
        weights.w_phi * l_phi +
        weights.w_n   * l_n   +
        weights.w_p   * l_p   +
        weights.w_bdy * l_bdy
    )
    diag = {
        "loss_phi": float(l_phi.detach()),
        "loss_n":   float(l_n.detach()),
        "loss_p":   float(l_p.detach()),
        "loss_bdy": float(l_bdy.detach()),
    }
    if data_terms is not None and len(data_terms) > 0:
        l_data = sum(mse(v) for v in data_terms.values())
        loss = loss + weights.w_data * l_data
        diag["loss_data"] = float(l_data.detach())
    diag["loss_total"] = float(loss.detach())
    return loss, diag


# ============================================================================
# NTK-style adaptive weighting (Wang, Sankaran, Perdikaris 2022)
# ============================================================================

class NTKAdaptiveWeights:
    """Online adaptive PINN loss weighting via gradient-norm balancing.

    At each adaptive step, each loss component's weight is multiplied by
    a factor that equalizes its gradient L2 norm w.r.t. network parameters.
    This is the lightweight variant of the NTK eigenvalue method that
    avoids the cost of explicit Hessian estimation.

    Algorithm (per update):
        g_i = || ∇_θ L_i ||_2
        w_i := alpha * w_i + (1 - alpha) * (sum_j g_j) / (g_i * num_terms)

    where ``alpha`` is an EMA smoothing factor (default 0.9). Weights are
    clipped to ``[1e-3, 1e+3]`` to prevent runaway.

    Usage
    -----
    >>> aw = NTKAdaptiveWeights(["phi", "n", "p", "bdy"])
    >>> # ... build the per-component loss tensors ...
    >>> aw.update(losses={"phi": l_phi, "n": l_n, "p": l_p, "bdy": l_bdy},
    ...           params=model.parameters())
    >>> w = aw.weights  # dict of floats
    """

    def __init__(self, names, alpha: float = 0.9, clip: Tuple[float, float] = (1e-3, 1e3)):
        self.names = list(names)
        self.alpha = float(alpha)
        self.clip_lo, self.clip_hi = clip
        self.weights = dict.fromkeys(self.names, 1.0)

    @staticmethod
    def _grad_norm(loss: torch.Tensor, params) -> float:
        params = [p for p in params if p.requires_grad]
        grads = torch.autograd.grad(
            loss, params, retain_graph=True, create_graph=False,
            allow_unused=True,
        )
        norm_sq = 0.0
        for g in grads:
            if g is not None:
                norm_sq = norm_sq + float((g ** 2).sum())
        return norm_sq ** 0.5

    def update(self, losses: Dict[str, torch.Tensor], params) -> Dict[str, float]:
        """Recompute weights from current per-term loss gradients."""
        params = list(params)
        norms = {}
        for name in self.names:
            if name not in losses:
                continue
            norms[name] = self._grad_norm(losses[name], params)
        s = sum(norms.values())
        if s <= 0:
            return self.weights
        n_terms = len(norms)
        for name, g in norms.items():
            if g <= 0:
                continue
            target = s / (g * n_terms)
            new = self.alpha * self.weights[name] + (1.0 - self.alpha) * target
            new = max(self.clip_lo, min(self.clip_hi, new))
            self.weights[name] = float(new)
        return self.weights


__all__ = [
    "LossWeights",
    "NTKAdaptiveWeights",
    "PhysicsParams",
    "boundary_residuals",
    "ohmic_boundary_values",
    "pde_residuals",
    "total_loss",
]
