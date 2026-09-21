"""
Non-dimensionalization for the Poisson-drift-diffusion (PDD) system.

We use De Mari scaling, which is the standard choice for semiconductor TCAD:

    length    L*   = L_D, the intrinsic Debye length
    potential phi* = V_T = k_B T / q
    density   n*   = n_i (intrinsic carrier density)
    time      t*   = L_D^2 / (V_T * mu*)  with mu* a reference mobility
    mobility  mu*  = max(mu_n, mu_p)
    current   J*   = q * n_i * mu* * V_T / L_D

This brings the dimensionless Poisson equation to the canonical form

    - phi_{xx}^~ = ( p~ - n~ + C~ )

with C~ = (N_D - N_A) / n_i, the only doping-dependent parameter. The
dimensionless current is the Boltzmann-statistics form

    J_n~ = mu_n~ * n~ * E~ + mu_n~ * grad n~

(with the analogous form for J_p).

The scaler is a *pure data container*. All physics modules accept a Scaling
instance and decide whether to operate in SI or scaled units; never both
silently mixed. This is the project's defense against unit-bug regressions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .constants import Q_E, SILICON, Material, thermal_voltage


@dataclass(frozen=True)
class Scaling:
    """
    De Mari scaling for a given material and temperature.

    All factors map *SI value = factor * dimensionless value*. Conversions are
    therefore: SI -> scaled is division, scaled -> SI is multiplication.
    """
    material: Material
    T: float
    V_T: float                 # V, thermal voltage
    L_D: float                 # m, intrinsic Debye length (length scale)
    n_star: float              # m^-3, density scale = n_i
    mu_star: float             # m^2 / (V s), mobility scale
    t_star: float              # s, time scale
    J_star: float              # A / m^2, current density scale
    R_star: float              # m^-3 s^-1, recombination scale

    @classmethod
    def for_material(cls, material: Material = SILICON, T: float = 300.0) -> "Scaling":
        V_T = thermal_voltage(T)
        L_D = math.sqrt(material.eps * V_T / (Q_E * material.n_i))
        mu_star = max(material.mu_n, material.mu_p)
        t_star = L_D * L_D / (V_T * mu_star)
        J_star = Q_E * material.n_i * mu_star * V_T / L_D
        R_star = material.n_i / t_star
        return cls(
            material=material,
            T=T,
            V_T=V_T,
            L_D=L_D,
            n_star=material.n_i,
            mu_star=mu_star,
            t_star=t_star,
            J_star=J_star,
            R_star=R_star,
        )

    # ---- to-dimensionless (SI -> scaled) ------------------------------------
    def x_to_scaled(self, x_si):
        return x_si / self.L_D

    def phi_to_scaled(self, phi_si):
        return phi_si / self.V_T

    def n_to_scaled(self, n_si):
        return n_si / self.n_star

    def mu_to_scaled(self, mu_si):
        return mu_si / self.mu_star

    def J_to_scaled(self, J_si):
        return J_si / self.J_star

    def doping_to_scaled(self, C_si):
        return C_si / self.n_star

    # ---- from-dimensionless (scaled -> SI) ----------------------------------
    def x_to_si(self, x_s):
        return x_s * self.L_D

    def phi_to_si(self, phi_s):
        return phi_s * self.V_T

    def n_to_si(self, n_s):
        return n_s * self.n_star

    def mu_to_si(self, mu_s):
        return mu_s * self.mu_star

    def J_to_si(self, J_s):
        return J_s * self.J_star

    def doping_to_si(self, C_s):
        return C_s * self.n_star

    # ---- network-input representation ---------------------------------------
    # The raw scaled doping C_s = N/n_i has magnitudes up to ~10^9 for heavy
    # doping. Feeding values that large into a tanh network instantly
    # saturates the first hidden layer. We use a sign-preserving log
    # compression to map typical doping ranges (1e16 -- 1e25 m^-3) into
    # the ~O(1) regime the network can actually learn over.
    #
    # PH-22 (dtype). This representation is the one quantity that crosses the
    # solver/network boundary: the SG oracle works in float64, the surrogate and
    # the PINN in float32. Measured round-trip relative error of the SI <-> scaled
    # conversion over 1e16 -- 1e25 m^-3, 91 log-spaced points:
    #
    #     float64   1.678e-16   (worst at N = 1e23)
    #     float32   8.714e-08   (worst at N = 2.5e19)
    #
    # Both are at their dtype's epsilon, so the envelope transfers -- but the
    # float32 figure is a hard floor on how finely two doping profiles can be
    # *distinguished* on the network side, which matters to any study of
    # profile degeneracy. It is not a floor on the oracle.
    #
    #     latent = sign(C_si) * log10(1 + |C_si| / n_i) / 10
    #
    # This is bijective (preserves sign and magnitude information), smooth
    # through zero (log1p), and inverts cleanly via :meth:`net_input_to_si`.
    NET_DOPING_LOG_SCALE: float = 10.0

    def doping_to_net_input(self, C_si):
        """Compressed doping representation safe for tanh networks.

        Accepts numpy or torch tensors transparently.
        """
        try:
            import torch as _t
            if isinstance(C_si, _t.Tensor):
                return (_t.sign(C_si) *
                        _t.log10(1.0 + _t.abs(C_si) / self.n_star)
                        / self.NET_DOPING_LOG_SCALE)
        except ImportError:
            pass
        return (np.sign(C_si) * np.log10(1.0 + np.abs(C_si) / self.n_star)
                / self.NET_DOPING_LOG_SCALE)

    def net_input_to_doping_si(self, latent):
        """Invert :meth:`doping_to_net_input`. Returns C in m^-3."""
        try:
            import torch as _t
            if isinstance(latent, _t.Tensor):
                return (_t.sign(latent) *
                        (_t.pow(10.0, _t.abs(latent) * self.NET_DOPING_LOG_SCALE) - 1.0)
                        * self.n_star)
        except ImportError:
            pass
        return (np.sign(latent) *
                (10.0 ** (np.abs(latent) * self.NET_DOPING_LOG_SCALE) - 1.0)
                * self.n_star)

    def summary(self) -> str:
        return (
            f"Scaling[{self.material.name} @ {self.T:.1f} K]\n"
            f"  V_T   = {self.V_T:.6e} V\n"
            f"  L_D   = {self.L_D:.6e} m   ({self.L_D*1e9:.3f} nm)\n"
            f"  n*    = {self.n_star:.3e} m^-3\n"
            f"  mu*   = {self.mu_star:.3e} m^2/(V s)\n"
            f"  t*    = {self.t_star:.3e} s\n"
            f"  J*    = {self.J_star:.3e} A/m^2\n"
        )


__all__ = ["Scaling"]
