"""
Forward-solver wrapper around :class:`SemiconductorPINN`.

This module exposes a single class, :class:`ForwardPINN`, whose
``solve(doping_si, bias) -> DeviceState`` interface is *intentionally
identical* to that of :class:`ScharfetterGummel1D`. Downstream code
(inverse design, active learning, plotting, benchmark harness) is
therefore solver-agnostic and can swap one for the other.

Design notes
------------
1. **Fixed-dimension doping latent.** The PINN takes a fixed-length
   doping vector as input. We sample the user-provided ``doping_si``
   profile at a fixed grid of ``cfg.doping_dim`` anchor points spanning
   the device. The same anchor grid is used at training time, so the
   network learns a parameterized family.

2. **Differentiable end-to-end.** The wrapper preserves gradients from
   the input ``doping_si`` tensor through to the returned currents,
   which is what makes input-space autodiff inverse design possible.

3. **Numerical current.** The terminal current is the device-averaged
   total current density J = J_n + J_p, evaluated at all collocation
   points on a fine query grid. For a converged steady-state solution
   this is constant in x (current continuity); the per-point variance
   serves as a diagnostic for solution quality.

4. **Units.** ``doping_si`` is in m^-3 (SI). ``bias`` is in volts.
   The returned :class:`DeviceState` is in SI units.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn

from ..physics.scaling import Scaling
from ..physics.constants import Material
from ..solvers.scharfetter_gummel import DeviceState, Grid1D
from .network import SemiconductorPINN, PINNConfig


@dataclass
class ForwardPINNConfig:
    """Runtime config for ForwardPINN evaluation.

    Most knobs are inherited from PINNConfig (architecture); this struct
    governs only the inference-time behavior.
    """
    device: str = "cpu"
    dtype: torch.dtype = torch.float32
    n_query: int = 401          # collocation points along x for inference
    n_anchor: int = 32          # doping-latent anchor count (must match net.cfg.doping_dim)
    domain_si: Tuple[float, float] = (0.0, 1e-6)  # device length in metres


class ForwardPINN(nn.Module):
    """A PINN packaged as a forward semiconductor solver.

    Parameters
    ----------
    network : SemiconductorPINN
        A (trained or untrained) PINN. The wrapper itself does no training;
        use :mod:`bayespinn_inv.training` for that.
    scaling : Scaling
        The De-Mari scaling used at training time. This MUST match the
        scaling under which the network was trained.
    material : Material
        Material used to derive physical mobilities and lifetimes for
        post-hoc current evaluation. Should match training-time material.
    cfg : ForwardPINNConfig
    """

    def __init__(
        self,
        network: SemiconductorPINN,
        scaling: Scaling,
        material: Material,
        cfg: Optional[ForwardPINNConfig] = None,
    ):
        super().__init__()
        self.network = network
        self.scaling = scaling
        self.material = material
        self.cfg = cfg or ForwardPINNConfig()
        # Sanity: the network's doping_dim must match our anchor count.
        net_doping_dim = network.cfg.doping_dim
        if net_doping_dim != self.cfg.n_anchor:
            raise ValueError(
                f"PINNConfig.doping_dim ({net_doping_dim}) must equal "
                f"ForwardPINNConfig.n_anchor ({self.cfg.n_anchor})."
            )

    # ------------------------------------------------------------------
    # Doping latent representation
    # ------------------------------------------------------------------

    def anchor_grid_si(self) -> torch.Tensor:
        """Uniform anchor grid spanning the device, in metres."""
        xL, xR = self.cfg.domain_si
        return torch.linspace(xL, xR, self.cfg.n_anchor,
                              device=self.cfg.device, dtype=self.cfg.dtype)

    def doping_to_latent(
        self,
        doping_si: torch.Tensor,
        x_si: torch.Tensor,
    ) -> torch.Tensor:
        """Resample a user-provided doping profile to the anchor grid.

        Parameters
        ----------
        doping_si : (M,) tensor in m^-3, on the grid ``x_si``.
        x_si      : (M,) tensor in metres.

        Returns
        -------
        latent : (n_anchor,) tensor in *scaled* units.
        """
        # 1D linear interpolation (torch does not yet have a 1D interp1d,
        # so we do it by hand — fully differentiable in doping_si).
        x_anchor = self.anchor_grid_si()
        # Clamp to grid range to avoid extrapolation.
        x_clamped = torch.clamp(x_anchor, x_si.min(), x_si.max())
        # searchsorted gives the *right* index of each anchor in x_si.
        right = torch.searchsorted(x_si.contiguous(), x_clamped.contiguous())
        right = torch.clamp(right, 1, len(x_si) - 1)
        left = right - 1
        xl, xr = x_si[left], x_si[right]
        yl, yr = doping_si[left], doping_si[right]
        # Avoid 0/0 at coincident anchor.
        w = torch.where(xr > xl, (x_clamped - xl) / (xr - xl + 1e-30),
                        torch.zeros_like(xr))
        anchor_si = yl + w * (yr - yl)
        # Use the log-compressed network-input representation, matching
        # data/datasets.py.
        anchor_latent = self.scaling.doping_to_net_input(anchor_si)
        return anchor_latent

    # ------------------------------------------------------------------
    # Forward solve
    # ------------------------------------------------------------------

    def solve(
        self,
        doping_si: torch.Tensor,
        bias: float | torch.Tensor,
        grid: Optional[Grid1D] = None,
    ) -> DeviceState:
        """Evaluate the PINN as a forward solver.

        Parameters
        ----------
        doping_si : (M,) tensor, m^-3, on a grid spanning the device.
            The grid is taken to be uniform over ``cfg.domain_si``.
        bias : float or scalar tensor, in volts.
            Applied at the right contact (left grounded).
        grid : Grid1D, optional
            Inference grid. If None, a uniform grid of ``cfg.n_query`` points
            is built.

        Returns
        -------
        DeviceState in SI units.

        Notes
        -----
        Wrapped in ``torch.enable_grad()`` so spatial derivatives can be
        computed regardless of outer ``torch.no_grad()`` context.
        """
        with torch.enable_grad():
            return self._solve_impl(doping_si, bias, grid)

    def _solve_impl(
        self,
        doping_si: torch.Tensor,
        bias: float | torch.Tensor,
        grid: Optional[Grid1D] = None,
    ) -> DeviceState:
        # 1) Build inference grid (Grid1D stores *scaled* coordinates)
        if grid is None:
            xL_si, xR_si = self.cfg.domain_si
            assert xL_si == 0.0, "Forward grid must start at x=0; shift before solving."
            L_scaled = float(self.scaling.x_to_scaled(torch.as_tensor(xR_si - xL_si)))
            grid = Grid1D.uniform(L_scaled, self.cfg.n_query)
        # grid.x is scaled coords; convert to SI for the DeviceState record
        x_s_grid = torch.as_tensor(grid.x, device=self.cfg.device,
                                    dtype=self.cfg.dtype)
        x_si_query = self.scaling.x_to_si(x_s_grid)
        N = x_si_query.shape[0]

        # 2) Reduce doping_si to fixed-length latent
        x_si_doping = torch.linspace(
            self.cfg.domain_si[0], self.cfg.domain_si[1],
            doping_si.shape[0], device=self.cfg.device, dtype=self.cfg.dtype,
        )
        doping_latent = self.doping_to_latent(doping_si, x_si_doping)  # (n_anchor,)
        latent_broadcast = doping_latent[None, :].expand(N, -1)        # (N, n_anchor)

        # 3) Build network inputs in *scaled* units (already have scaled grid)
        x_s = x_s_grid.reshape(-1, 1).detach().clone().requires_grad_(True)
        V_a_s_scalar = self.scaling.phi_to_scaled(torch.as_tensor(
            bias, device=self.cfg.device, dtype=self.cfg.dtype))
        V_a_s = V_a_s_scalar * torch.ones((N, 1), device=self.cfg.device,
                                           dtype=self.cfg.dtype)

        # 4) Forward pass
        phi_s, log_n, log_p = self.network(x_s, V_a_s, latent_broadcast)

        # 5) Compute currents in scaled units via log-density formula
        dphi  = torch.autograd.grad(phi_s, x_s,
                                    grad_outputs=torch.ones_like(phi_s),
                                    create_graph=False, retain_graph=True)[0]
        dlogn = torch.autograd.grad(log_n, x_s,
                                    grad_outputs=torch.ones_like(log_n),
                                    create_graph=False, retain_graph=True)[0]
        dlogp = torch.autograd.grad(log_p, x_s,
                                    grad_outputs=torch.ones_like(log_p),
                                    create_graph=False, retain_graph=False)[0]
        n_s = torch.exp(log_n)
        p_s = torch.exp(log_p)
        mu_n_s = self.scaling.mu_to_scaled(self.material.mu_n)
        mu_p_s = self.scaling.mu_to_scaled(self.material.mu_p)
        J_n_s =  mu_n_s * n_s * (dlogn - dphi)
        J_p_s = -mu_p_s * p_s * (dlogp + dphi)

        # 6) Convert back to SI units. Currents are face-centered in the SG
        #    convention; for the PINN they are node-centered. We pad by
        #    repeating the boundary value so the array shapes match the
        #    DeviceState contract (one extra entry on the right).
        x_si  = x_si_query.detach().cpu().numpy()
        phi_si = self.scaling.phi_to_si(phi_s.detach().squeeze(-1)).cpu().numpy()
        n_si  = self.material.n_i * np.exp(log_n.detach().squeeze(-1).cpu().numpy())
        p_si  = self.material.n_i * np.exp(log_p.detach().squeeze(-1).cpu().numpy())
        # Stack on the face grid: take node-centered values, then pad.
        Jn_si = self.scaling.J_to_si(J_n_s.detach().squeeze(-1)).cpu().numpy()
        Jp_si = self.scaling.J_to_si(J_p_s.detach().squeeze(-1)).cpu().numpy()
        Jn_face = np.concatenate([Jn_si, Jn_si[-1:]])
        Jp_face = np.concatenate([Jp_si, Jp_si[-1:]])

        doping_arr = doping_si.detach().cpu().numpy()
        # Resample doping to the inference grid for the DeviceState record
        doping_on_query = np.interp(x_si, x_si_doping.detach().cpu().numpy(),
                                    doping_arr)

        return DeviceState(
            x=x_si, phi=phi_si, n=n_si, p=p_si,
            Jn=Jn_face, Jp=Jp_face,
            doping=doping_on_query, bias=float(bias),
            converged=True, iterations=0,
            residuals=[],
        )

    # ------------------------------------------------------------------
    # Differentiable I-V curve generator (no detach inside!)
    # ------------------------------------------------------------------

    def iv_curve(
        self,
        doping_si: torch.Tensor,
        biases: Sequence[float],
        x_si_query: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Differentiable I-V evaluation.

        Returns
        -------
        bias_tensor : (B,) tensor of bias values
        I_terminal  : (B,) tensor of terminal current densities (A/m^2),
                      with gradients connected to ``doping_si``.

        Notes
        -----
        Wrapped in ``torch.enable_grad()`` because we need autograd to
        compute spatial derivatives of the network output internally,
        regardless of any outer ``torch.no_grad()`` context (e.g. when
        called from a final-evaluation block in inverse design).
        """
        with torch.enable_grad():
            return self._iv_curve_impl(doping_si, biases, x_si_query)

    def _iv_curve_impl(
        self,
        doping_si: torch.Tensor,
        biases: Sequence[float],
        x_si_query: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if x_si_query is None:
            xL, xR = self.cfg.domain_si
            x_si_query = torch.linspace(xL, xR, self.cfg.n_query,
                                         device=self.cfg.device,
                                         dtype=self.cfg.dtype)
        N = x_si_query.shape[0]
        x_s = self.scaling.x_to_scaled(x_si_query).reshape(-1, 1)
        x_s = x_s.detach().clone().requires_grad_(True)

        # Anchor latent (same for all biases)
        x_si_doping = torch.linspace(
            self.cfg.domain_si[0], self.cfg.domain_si[1],
            doping_si.shape[0], device=self.cfg.device, dtype=self.cfg.dtype,
        )
        doping_latent = self.doping_to_latent(doping_si, x_si_doping)

        mu_n_s = self.scaling.mu_to_scaled(self.material.mu_n)
        mu_p_s = self.scaling.mu_to_scaled(self.material.mu_p)

        currents = []
        bias_tensor = torch.as_tensor(list(biases), device=self.cfg.device,
                                       dtype=self.cfg.dtype)
        for V in bias_tensor:
            V_s = self.scaling.phi_to_scaled(V)
            V_a_s = V_s * torch.ones((N, 1), device=self.cfg.device,
                                     dtype=self.cfg.dtype)
            latent_broadcast = doping_latent[None, :].expand(N, -1)

            phi_s, log_n, log_p = self.network(x_s, V_a_s, latent_broadcast)
            dphi  = torch.autograd.grad(phi_s, x_s,
                                        grad_outputs=torch.ones_like(phi_s),
                                        create_graph=True, retain_graph=True)[0]
            dlogn = torch.autograd.grad(log_n, x_s,
                                        grad_outputs=torch.ones_like(log_n),
                                        create_graph=True, retain_graph=True)[0]
            dlogp = torch.autograd.grad(log_p, x_s,
                                        grad_outputs=torch.ones_like(log_p),
                                        create_graph=True, retain_graph=True)[0]
            n_s = torch.exp(log_n)
            p_s = torch.exp(log_p)
            J_n_s =  mu_n_s * n_s * (dlogn - dphi)
            J_p_s = -mu_p_s * p_s * (dlogp + dphi)
            J_tot_s = J_n_s + J_p_s
            # Mean over x as the terminal current (current continuity gives
            # constant J for a converged solution; mean is best-estimate).
            J_terminal_s = J_tot_s.mean()
            J_terminal_si = self.scaling.J_to_si(J_terminal_s)
            currents.append(J_terminal_si)

        I_terminal = torch.stack(currents)
        return bias_tensor, I_terminal


__all__ = ["ForwardPINN", "ForwardPINNConfig"]
