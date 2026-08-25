"""
Physical constants and reference material parameters.

All values in SI units unless explicitly noted. Sources are cited inline so
that any future deviation from CODATA / Sze can be audited.

Conventions
-----------
* Charge of the electron is the positive elementary charge `q`. Electron charge
  is `-q`. We never carry a separate sign convention for electrons.
* Carrier densities `n, p` are *number densities* in m^-3.
* Dopant densities `N_D, N_A` are *ionized* donor / acceptor densities in m^-3.
  Full ionization is assumed throughout unless explicitly stated.
* Electric potential `phi` in volts. Electric field `E = -grad phi` in V/m.
* Mobility `mu` in m^2 / (V s). Diffusivity `D` in m^2 / s. Einstein: D = mu * V_T.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---- Universal constants (CODATA 2018) --------------------------------------
Q_E: Final[float] = 1.602176634e-19      # C (exact, SI redefinition)
K_B: Final[float] = 1.380649e-23         # J / K (exact, SI redefinition)
EPS_0: Final[float] = 8.8541878128e-12   # F / m
H_PLANCK: Final[float] = 6.62607015e-34  # J s (exact)

# ---- Reference temperature --------------------------------------------------
T_REF: Final[float] = 300.0  # K, used as default ambient temperature


def thermal_voltage(T: float = T_REF) -> float:
    """Thermal voltage V_T = k_B T / q."""
    return K_B * T / Q_E


@dataclass(frozen=True)
class Material:
    """
    Static material parameters at a reference temperature.

    These are *low-field, undoped* baseline values. Field-dependent mobility
    and doping-dependent mobility are implemented separately in
    ``physics.mobility``; SRH lifetimes in ``physics.recombination``.
    """
    name: str
    eps_r: float            # relative permittivity, dimensionless
    n_i: float              # intrinsic carrier density at T_REF, m^-3
    mu_n: float             # low-field electron mobility, m^2/(V s)
    mu_p: float             # low-field hole mobility, m^2/(V s)
    E_g: float              # bandgap at T_REF, eV
    N_c: float              # conduction-band effective density of states, m^-3
    N_v: float              # valence-band effective density of states, m^-3
    tau_n: float = 1e-6     # SRH electron lifetime, s (defaults: clean Si)
    tau_p: float = 1e-6     # SRH hole lifetime, s

    @property
    def eps(self) -> float:
        """Absolute permittivity epsilon = eps_r * eps_0 in F/m."""
        return self.eps_r * EPS_0


# Silicon at 300 K. Values from Sze & Ng 'Physics of Semiconductor Devices'
# 3rd ed., Wiley 2007, Appendix G. n_i = 1.0e16 m^-3 = 1.0e10 cm^-3 is the
# canonical room-temperature figure used by Sentaurus and Atlas.
SILICON = Material(
    name="Si",
    eps_r=11.7,
    n_i=1.0e16,           # m^-3  (= 1e10 cm^-3)
    mu_n=0.1350,          # m^2/(V s) = 1350 cm^2/(V s)
    mu_p=0.0480,          # m^2/(V s) = 480 cm^2/(V s)
    E_g=1.12,             # eV
    N_c=2.8e25,           # m^-3 = 2.8e19 cm^-3
    N_v=1.04e25,          # m^-3 = 1.04e19 cm^-3
    tau_n=1.0e-6,         # 1 µs
    tau_p=1.0e-6,
)

# GaAs sketch parameters (forward compatibility; not exercised in M1-M2).
GAAS = Material(
    name="GaAs",
    eps_r=12.9,
    n_i=2.1e12,           # m^-3
    mu_n=0.85,            # m^2/(V s) at low field
    mu_p=0.04,
    E_g=1.424,
    N_c=4.7e23,
    N_v=9.0e24,
    tau_n=1.0e-9,
    tau_p=1.0e-9,
)


__all__ = [
    "EPS_0",
    "GAAS",
    "H_PLANCK",
    "K_B",
    "Q_E",
    "SILICON",
    "T_REF",
    "Material",
    "thermal_voltage",
]
