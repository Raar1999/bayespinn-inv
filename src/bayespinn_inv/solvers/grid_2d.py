"""
2D rectangular grid for MOS-capacitor simulation.

A MOS capacitor has two stacked materials (silicon body + gate oxide)
with different dielectric constants, and Dirichlet boundary conditions
on (i) the substrate contact at the bottom and (ii) the gate contact at
the top. The semiconductor-oxide interface has a continuity condition
on the electric flux that we handle implicitly via the permittivity
mapping.

The grid spans ``[0, Lx] x [0, Ly]`` where ``y=0`` is the substrate
contact and ``y=Ly`` is the gate contact. The oxide occupies the top
slab ``[0, Lx] x [Ly - t_ox, Ly]`` (region tag 1); the semiconductor
fills the rest (region tag 0).

This module is intentionally minimal: it builds the geometry, the
permittivity map, and the per-cell volume integrals needed by the
Poisson and continuity finite-volume solvers. It does NOT carry any
solver logic — that lives in :mod:`solvers.mos_cap_2d`.

Coordinate convention
---------------------
- ``x`` is the lateral coordinate (along the channel direction)
- ``y`` is the vertical coordinate (from substrate to gate)
- 2D fields are stored as ``(Ny, Nx)`` arrays so that ``arr[j, i]``
  corresponds to ``(x_i, y_j)``. This is the standard convention for
  ``imshow``-friendly plotting.

Limitations vs full 2D TCAD
---------------------------
- We treat only the Poisson + quasi-equilibrium-Maxwell-Boltzmann
  regime, valid for MOS capacitors in accumulation, depletion, and weak
  inversion. Full strong-inversion current flow under non-equilibrium
  conditions (e.g. MOSFET on-state) requires the 2D Scharfetter-Gummel
  continuity solver, which is out of scope for this stretch goal.
- The interface roughness and quantum confinement effects relevant
  below ~5 nm SiO2 are not modelled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class MOSCapGeometry:
    """Geometry of a 1D MOS capacitor extended to 2D.

    Even though a MOS capacitor is essentially 1D in the depletion
    direction, we use a 2D grid for two reasons:
      (1) It exercises the 2D infrastructure (the whole point of this
          stretch goal: confirm the PINN scales to 2D).
      (2) It supports asymmetric (e.g. non-uniformly doped body) cases.

    The 1D-equivalent solution corresponds to ``Lx`` small enough that
    no lateral variations build up.

    All lengths in metres.
    """
    Lx: float                # lateral extent
    Ly_semi: float           # vertical extent of the semiconductor body
    t_ox: float              # gate oxide thickness
    eps_r_semi: float        # semiconductor dielectric constant
    eps_r_ox: float = 3.9    # SiO2 default

    @property
    def Ly(self) -> float:
        """Total vertical extent (semiconductor + oxide)."""
        return self.Ly_semi + self.t_ox

    @property
    def y_interface(self) -> float:
        """y-coordinate of the Si/SiO2 interface."""
        return self.Ly_semi


@dataclass
class Grid2D:
    """Uniform 2D rectangular grid covering the MOS-cap geometry.

    Coordinates are stored in SI units (metres) on this struct, but the
    scaled-coordinate versions are computed on demand via the same
    :class:`Scaling` machinery used elsewhere.
    """
    geometry: MOSCapGeometry
    Nx: int
    Ny: int
    x: np.ndarray            # (Nx,) lateral node positions, in metres
    y: np.ndarray            # (Ny,) vertical node positions, in metres
    hx: float                # uniform x spacing, in metres
    hy: float                # uniform y spacing, in metres
    eps_r_field: np.ndarray  # (Ny, Nx) relative permittivity at each node
    region: np.ndarray       # (Ny, Nx) int; 0 = semiconductor, 1 = oxide
    semi_mask: np.ndarray    # (Ny, Nx) bool; True iff node is in semiconductor

    @classmethod
    def uniform(cls, geometry: MOSCapGeometry, Nx: int, Ny: int) -> "Grid2D":
        """Build a uniform 2D grid covering the MOS-cap."""
        if Nx < 4 or Ny < 4:
            raise ValueError("Need at least 4 nodes per axis for finite volumes.")
        x = np.linspace(0.0, geometry.Lx, Nx)
        y = np.linspace(0.0, geometry.Ly, Ny)
        hx = float(x[1] - x[0])
        hy = float(y[1] - y[0])
        eps_r = np.full((Ny, Nx), geometry.eps_r_semi, dtype=np.float64)
        region = np.zeros((Ny, Nx), dtype=np.int8)
        oxide_mask = y >= geometry.y_interface - 0.5 * hy  # interface cell shared
        region[oxide_mask, :] = 1
        eps_r[oxide_mask, :] = geometry.eps_r_ox
        semi_mask = region == 0
        return cls(geometry=geometry, Nx=Nx, Ny=Ny,
                   x=x, y=y, hx=hx, hy=hy,
                   eps_r_field=eps_r, region=region, semi_mask=semi_mask)

    @property
    def shape(self) -> Tuple[int, int]:
        return (self.Ny, self.Nx)

    @property
    def n_nodes(self) -> int:
        return self.Nx * self.Ny

    def node_index(self, i: int, j: int) -> int:
        """Map (x-index i, y-index j) to a flat node index. Row-major (j-major)."""
        return j * self.Nx + i

    def cell_volume(self) -> np.ndarray:
        """Per-node control-volume "areas" (m^2) for 2D finite volumes.

        For interior nodes this is ``hx * hy``. Boundary nodes get half
        in the perpendicular direction; corners get a quarter.
        """
        wx = np.full(self.Nx, self.hx, dtype=np.float64)
        wx[0]  = 0.5 * self.hx
        wx[-1] = 0.5 * self.hx
        wy = np.full(self.Ny, self.hy, dtype=np.float64)
        wy[0]  = 0.5 * self.hy
        wy[-1] = 0.5 * self.hy
        return np.outer(wy, wx)   # (Ny, Nx)

    def face_eps_x(self) -> np.ndarray:
        """Harmonic mean of eps_r across vertical faces (between i and i+1).

        Returns shape (Ny, Nx-1). Harmonic averaging is the standard
        finite-volume treatment of conductive coefficients across
        material interfaces.
        """
        a = self.eps_r_field[:, :-1]
        b = self.eps_r_field[:, 1:]
        return 2.0 * a * b / (a + b)

    def face_eps_y(self) -> np.ndarray:
        """Harmonic mean of eps_r across horizontal faces (between j and j+1).

        Returns shape (Ny-1, Nx). This is the term that matters at the
        Si/SiO2 interface and ensures flux continuity is enforced
        correctly without any special interface treatment.
        """
        a = self.eps_r_field[:-1, :]
        b = self.eps_r_field[1:, :]
        return 2.0 * a * b / (a + b)


@dataclass
class MOSCapBoundary:
    """Boundary-condition specification.

    - ``V_gate``: applied gate voltage (V)
    - ``V_substrate``: substrate contact voltage (V), conventionally 0
    - ``phi_ms``: metal-semiconductor work-function difference (V).
      Subtracted from V_gate when computing the gate Dirichlet value;
      models the band-alignment offset between the gate metal and the
      semiconductor reference.
    - Sides (``x=0`` and ``x=Lx``) get zero-flux (Neumann) by default,
      modelling a laterally-uniform MOS capacitor.
    """
    V_gate: float = 0.0
    V_substrate: float = 0.0
    phi_ms: float = 0.0


__all__ = ["Grid2D", "MOSCapBoundary", "MOSCapGeometry"]
