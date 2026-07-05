"""
2D MOS-capacitor Poisson solver with Maxwell-Boltzmann statistics.

We solve the nonlinear Poisson equation in 2D on the MOS-cap geometry::

    grad . (eps grad phi) = -q (p - n + C)         in the semiconductor
    grad . (eps grad phi) = 0                       in the oxide
    phi(y=0, x) = V_substrate                       Dirichlet (substrate)
    phi(y=Ly, x) = V_gate - phi_ms                  Dirichlet (gate)
    d phi / dn = 0   on x = 0, Lx                   Neumann (zero flux)

with Maxwell-Boltzmann statistics inside the semiconductor::

    n = n_i exp(phi / V_T)        (under quasi-equilibrium: phi_n = 0)
    p = n_i exp(-phi / V_T)       (under quasi-equilibrium: phi_p = 0)

so the right-hand side becomes::

    rho/eps_0 = (q n_i / eps_0) (exp(-phi/V_T) - exp(phi/V_T) + C/n_i)

The solver uses Newton-Raphson on the nonlinear Poisson, with the
linearization::

    J(phi) [ d phi ] = -r(phi)
    J = -grad.(eps grad) - (q n_i / eps_0) * (exp(-phi/V_T) + exp(phi/V_T)) / V_T

(both terms positive-definite when added → SPD system, solvable with
LU or CG). We use scipy.sparse.linalg.spsolve since N typically fits.

Validation
----------
For a uniform-substrate MOS-cap, the analytical depletion approximation
predicts the surface potential as a function of V_gate. We compare
against this in :mod:`tests.test_mos_cap_2d`.

Limitations
-----------
- **No current flow**. We do NOT solve the continuity equations. This
  is the *quasi-equilibrium* regime — appropriate for accumulation,
  depletion, weak inversion at zero V_DS, and gate-leakage-free
  capacitors. Adding 2D Scharfetter-Gummel continuity (for MOSFET
  on-state currents) requires ~600 more lines and is explicitly out of
  scope for this stretch goal.
- **Boltzmann, not Fermi-Dirac**. Degenerate doping (>~5e25 m^-3) is
  out of validity range.
- **No interface traps**. Ideal MOS interface only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, diags, lil_matrix
from scipy.sparse.linalg import spsolve

from ..physics.constants import EPS_0, Q_E, Material, SILICON, thermal_voltage
from ..physics.scaling import Scaling
from .grid_2d import Grid2D, MOSCapBoundary, MOSCapGeometry


# ============================================================================
# Configuration + state
# ============================================================================

@dataclass
class MOSCap2DConfig:
    """Newton-Raphson parameters for the 2D Poisson solve."""
    max_iters: int = 50
    tol: float = 1e-8
    damping: float = 1.0       # 1.0 = full Newton step; reduce if oscillating
    phi_init: str = "linear"   # "linear" or "zero"
    clip_arg: float = 60.0     # cap |phi/V_T| in exp() to avoid overflow
    verbose: bool = False


@dataclass
class MOSCap2DState:
    """Solver output: 2D fields on the grid plus diagnostics.

    All quantities in SI units. Fields are stored as ``(Ny, Nx)`` arrays.
    Carrier densities are zero in the oxide region.
    """
    x: np.ndarray            # (Nx,) m
    y: np.ndarray            # (Ny,) m
    phi: np.ndarray          # (Ny, Nx) V
    n: np.ndarray            # (Ny, Nx) m^-3 (zero in oxide)
    p: np.ndarray            # (Ny, Nx) m^-3 (zero in oxide)
    doping: np.ndarray       # (Ny, Nx) m^-3 (zero in oxide)
    V_gate: float
    V_substrate: float
    region: np.ndarray       # (Ny, Nx) 0 = semi, 1 = oxide
    converged: bool
    iterations: int
    residuals: List[float] = field(default_factory=list)

    def surface_potential(self, gridY_interface_idx: int) -> np.ndarray:
        """Potential at the Si/SiO2 interface, as a function of x.

        Returns a (Nx,) array.
        """
        return self.phi[gridY_interface_idx, :]

    def depletion_width(self, gridY_interface_idx: int,
                         phi_threshold: float = 0.01) -> np.ndarray:
        """Estimate of the depletion width below the interface, vs x.

        Defined as the y-distance from the interface where |phi - phi_bulk|
        first drops below ``phi_threshold`` V.

        Returns a (Nx,) array; ``nan`` where no transition is found.
        """
        Ny, Nx = self.phi.shape
        phi_bulk = self.phi[0, :]                          # substrate row
        widths = np.full(Nx, np.nan)
        for i in range(Nx):
            col = self.phi[:gridY_interface_idx + 1, i]
            target = phi_bulk[i] + np.sign(col[-1] - phi_bulk[i]) * phi_threshold
            # walk from interface (top) downward
            for j_off in range(gridY_interface_idx):
                j = gridY_interface_idx - j_off
                if (col[gridY_interface_idx] > phi_bulk[i]
                        and col[j] <= target) or (
                        col[gridY_interface_idx] < phi_bulk[i]
                        and col[j] >= target):
                    widths[i] = self.y[gridY_interface_idx] - self.y[j]
                    break
        return widths


# ============================================================================
# Solver
# ============================================================================

class MOSCap2DSolver:
    """2D nonlinear Poisson on the MOS-cap geometry."""

    def __init__(
        self,
        grid: Grid2D,
        scaling: Scaling,
        material: Material = SILICON,
        config: Optional[MOSCap2DConfig] = None,
    ):
        self.grid = grid
        self.scaling = scaling
        self.material = material
        self.config = config or MOSCap2DConfig()
        self.V_T = scaling.V_T

        # Pre-build the *linear* Laplacian (the part that doesn't depend
        # on phi). The nonlinear part is added per Newton iteration.
        self._build_laplacian()

    # ------------------------------------------------------------------
    # Laplacian assembly
    # ------------------------------------------------------------------

    def _build_laplacian(self) -> None:
        """Assemble the constant-coefficient part of the system matrix.

        For a node (i, j), the discrete divergence of (eps grad phi) is::

            (1/V_ij) * [
                  eps_E * (phi[i+1,j] - phi[i,j]) / hx * hy
                - eps_W * (phi[i,j]   - phi[i-1,j]) / hx * hy
                + eps_N * (phi[i,j+1] - phi[i,j]) / hy * hx
                - eps_S * (phi[i,j]   - phi[i,j-1]) / hy * hx
            ]

        where eps_E, eps_W, eps_N, eps_S are the harmonic means at the
        east/west/north/south faces of the cell.

        We assemble the matrix L such that L @ phi.flatten() gives the
        integrated divergence of (eps grad phi) over each cell (in SI
        units, V).  The Poisson equation is then::

            L @ phi - (q / eps_0) * cell_volume * (p - n + C) = 0
        """
        Nx, Ny = self.grid.Nx, self.grid.Ny
        N = Nx * Ny
        hx, hy = self.grid.hx, self.grid.hy
        eps_x = self.grid.face_eps_x()    # (Ny, Nx-1)
        eps_y = self.grid.face_eps_y()    # (Ny-1, Nx)

        # We work in (j, i) ordering with idx(i, j) = j * Nx + i
        def idx(i, j): return j * Nx + i

        A = lil_matrix((N, N), dtype=np.float64)
        # Constant scaling: face area / distance
        ax = hy / hx       # east/west face area = hy, distance = hx
        ay = hx / hy       # north/south face area = hx, distance = hy

        for j in range(Ny):
            for i in range(Nx):
                k = idx(i, j)
                # Default: collect contributions; track boundary handling
                diag = 0.0
                # East face (between (i, j) and (i+1, j))
                if i < Nx - 1:
                    coef = ax * eps_x[j, i]
                    A[k, idx(i + 1, j)] += coef
                    diag -= coef
                # West face
                if i > 0:
                    coef = ax * eps_x[j, i - 1]
                    A[k, idx(i - 1, j)] += coef
                    diag -= coef
                # North face
                if j < Ny - 1:
                    coef = ay * eps_y[j, i]
                    A[k, idx(i, j + 1)] += coef
                    diag -= coef
                # South face
                if j > 0:
                    coef = ay * eps_y[j - 1, i]
                    A[k, idx(i, j - 1)] += coef
                    diag -= coef
                A[k, k] += diag

        # Multiply by EPS_0 to get SI fluxes (eps_r * EPS_0 = eps absolute)
        A = A.tocsr() * EPS_0
        self._L = A
        # Mark which rows correspond to Dirichlet boundaries (top, bottom)
        # We'll overwrite these rows in each Newton iter for the BC enforcement.
        self._dirichlet_idx_bottom = np.array([idx(i, 0) for i in range(Nx)])
        self._dirichlet_idx_top    = np.array([idx(i, Ny - 1) for i in range(Nx)])

    # ------------------------------------------------------------------
    # Solver
    # ------------------------------------------------------------------

    def solve(
        self,
        doping_si: np.ndarray,        # (Ny, Nx); m^-3; zero in oxide
        bc: MOSCapBoundary,
        initial_state: Optional[MOSCap2DState] = None,
    ) -> MOSCap2DState:
        """Solve the nonlinear 2D Poisson by Newton iteration.

        Parameters
        ----------
        doping_si : (Ny, Nx) array of net doping C = N_D - N_A in m^-3.
        bc : MOSCapBoundary
        initial_state : optional previously-converged state to warm-start
            from. Strongly recommended when sweeping V_gate.

        Notes on reference convention
        -----------------------------
        We use the *intrinsic Fermi level* as the zero of potential.
        Under this convention, the equilibrium bulk potential of a
        uniformly-doped P-substrate with concentration N_A is
        phi_F = -V_T * ln(N_A / n_i) < 0. The substrate Ohmic contact
        is set to this value (not to bc.V_substrate, which is the
        external applied voltage and is added on top). The gate
        Dirichlet is bc.V_gate - bc.phi_ms in the same reference frame.

        Bias continuation
        -----------------
        At large forward gate bias (deep inversion), naive Newton
        diverges because the carrier exponential is too stiff. We solve
        in a sequence of intermediate bias steps from a warm start.
        ``initial_state`` lets the caller continue from a previously
        converged solution at a nearby bias.
        """
        cfg = self.config
        Nx, Ny = self.grid.Nx, self.grid.Ny
        N = Nx * Ny
        V_T = self.V_T
        n_i = self.material.n_i
        cell_vol = self.grid.cell_volume()      # (Ny, Nx) m^2
        semi_mask = self.grid.semi_mask

        C = np.where(semi_mask, doping_si, 0.0)
        C_flat = C.flatten()
        V_flat = cell_vol.flatten()
        semi_flat = semi_mask.flatten()

        # Bulk Fermi level
        C_bulk = float(np.median(C[0, :]))
        if abs(C_bulk) < 1.0:
            phi_F = 0.0
        elif C_bulk > 0:
            phi_F = +V_T * math.asinh(C_bulk / (2.0 * n_i))
        else:
            phi_F = -V_T * math.asinh(-C_bulk / (2.0 * n_i))

        # Target Dirichlet values
        phi_bot_target = phi_F + bc.V_substrate
        phi_top_target = phi_F + (bc.V_gate - bc.phi_ms)

        # Initialize phi: from initial_state if given, else linear
        if initial_state is not None:
            phi2d = initial_state.phi.copy()
        elif cfg.phi_init == "linear":
            phi2d = np.full((Ny, Nx), phi_F)
            phi2d[0, :]  = phi_bot_target
            phi2d[-1, :] = phi_top_target
        else:
            phi2d = np.full((Ny, Nx), phi_F)
            phi2d[0, :]  = phi_bot_target
            phi2d[-1, :] = phi_top_target

        # ---------------- Bias continuation ----------------
        # We step from the current top-Dirichlet value to the target in
        # increments of at most V_step_max. For each intermediate target,
        # run damped-Newton to convergence.
        phi_top_now = float(np.mean(phi2d[-1, :]))
        phi_bot_now = float(np.mean(phi2d[0, :]))
        V_step_max = 5.0 * V_T            # ~130 mV per continuation step
        # How many steps?
        n_steps_top = int(np.ceil(abs(phi_top_target - phi_top_now) / V_step_max))
        n_steps_bot = int(np.ceil(abs(phi_bot_target - phi_bot_now) / V_step_max))
        n_steps = max(1, max(n_steps_top, n_steps_bot))
        if cfg.verbose:
            print(f"  Continuation: {n_steps} bias step(s) "
                  f"({phi_top_now:+.3f} -> {phi_top_target:+.3f} V)")

        all_residuals: List[float] = []
        total_iters = 0
        converged_all = True
        for step_idx in range(1, n_steps + 1):
            frac = step_idx / n_steps
            phi_bot = phi_bot_now + frac * (phi_bot_target - phi_bot_now)
            phi_top = phi_top_now + frac * (phi_top_target - phi_top_now)
            # Update boundary rows of phi to the new target
            phi2d[0, :]  = phi_bot
            phi2d[-1, :] = phi_top
            phi = phi2d.flatten()

            phi, step_iters, step_res, step_conv = self._newton_solve(
                phi, phi_bot, phi_top, semi_flat, C_flat, V_flat,
                V_T, n_i, cfg,
            )
            phi2d = phi.reshape(Ny, Nx)
            all_residuals.extend(step_res)
            total_iters += step_iters
            if not step_conv:
                converged_all = False
            if cfg.verbose and not step_conv:
                print(f"    step {step_idx}: stalled after {step_iters} iters")

        # Final field reconstruction
        arg = np.clip(phi2d / V_T, -cfg.clip_arg, cfg.clip_arg)
        n_field = np.where(semi_mask, n_i * np.exp( arg), 0.0)
        p_field = np.where(semi_mask, n_i * np.exp(-arg), 0.0)
        return MOSCap2DState(
            x=self.grid.x.copy(), y=self.grid.y.copy(),
            phi=phi2d, n=n_field, p=p_field,
            doping=C, V_gate=bc.V_gate, V_substrate=bc.V_substrate,
            region=self.grid.region.copy(),
            converged=converged_all, iterations=total_iters,
            residuals=all_residuals,
        )

    def _newton_solve(self, phi, phi_bot, phi_top, semi_flat, C_flat, V_flat,
                       V_T, n_i, cfg):
        """One bias-step Newton iteration.

        Returns ``(phi_final, n_iters, residuals, converged)``.
        """
        N = phi.size
        residuals: List[float] = []
        r_norm_initial: float = None
        for it in range(cfg.max_iters):
            arg = np.clip(phi / V_T, -cfg.clip_arg, cfg.clip_arg)
            n = np.where(semi_flat, n_i * np.exp( arg), 0.0)
            p = np.where(semi_flat, n_i * np.exp(-arg), 0.0)
            rhs_charge = Q_E * V_flat * np.where(semi_flat, (p - n + C_flat), 0.0)
            r = self._L @ phi + rhs_charge
            r[self._dirichlet_idx_bottom] = phi[self._dirichlet_idx_bottom] - phi_bot
            r[self._dirichlet_idx_top]    = phi[self._dirichlet_idx_top]    - phi_top
            r_norm = float(np.linalg.norm(r) / max(N ** 0.5, 1.0))
            residuals.append(r_norm)
            if r_norm_initial is None:
                r_norm_initial = max(r_norm, 1e-30)
            # Residual-decay convergence: residual dropped many orders from
            # its starting value, or stagnated near machine precision.
            if it >= 2 and (r_norm / r_norm_initial < 1e-5 or r_norm < 1e-6):
                return phi, it + 1, residuals, True

            d_charge = (Q_E * V_flat / V_T) * np.where(
                semi_flat, n + p, 0.0)
            J = self._L + diags(d_charge, 0, shape=(N, N), format="csr")
            for k in self._dirichlet_idx_bottom:
                J = self._row_to_identity(J, k)
            for k in self._dirichlet_idx_top:
                J = self._row_to_identity(J, k)

            delta = spsolve(J, -r)
            delta_natural_max = float(np.abs(delta).max())

            # When the residual is already small (near-linear regime or close
            # to the solution), Newton is reliable: take the full step. Only
            # invoke backtracking when the residual is large enough that the
            # quadratic charge nonlinearity could cause overshoot.
            if r_norm < 1e-4:
                phi = phi + delta
                if cfg.verbose:
                    print(f"    Newton {it}: |r|={r_norm:.3e} full step "
                          f"max|delta|={delta_natural_max:.3e}")
                if delta_natural_max < cfg.tol:
                    return phi, it + 1, residuals, True
                continue

            # Armijo backtracking line search for the stiff nonlinear regime.
            alpha = 1.0
            phi_trial = phi + alpha * delta
            best_alpha = 0.0
            for _ in range(20):
                arg_t = np.clip(phi_trial / V_T, -cfg.clip_arg, cfg.clip_arg)
                n_t = np.where(semi_flat, n_i * np.exp( arg_t), 0.0)
                p_t = np.where(semi_flat, n_i * np.exp(-arg_t), 0.0)
                r_t = (self._L @ phi_trial
                        + Q_E * V_flat * np.where(semi_flat, (p_t - n_t + C_flat), 0.0))
                r_t[self._dirichlet_idx_bottom] = phi_trial[self._dirichlet_idx_bottom] - phi_bot
                r_t[self._dirichlet_idx_top]    = phi_trial[self._dirichlet_idx_top]    - phi_top
                rt_norm = float(np.linalg.norm(r_t) / max(N ** 0.5, 1.0))
                if rt_norm < r_norm:
                    best_alpha = alpha
                    break
                alpha *= 0.5
                phi_trial = phi + alpha * delta
            if best_alpha == 0.0:
                best_alpha = 1.0 / 64.0
            phi = phi + cfg.damping * best_alpha * delta
            delta_max = float(np.abs(best_alpha * delta).max())
            if cfg.verbose:
                print(f"    Newton {it}: |r|={r_norm:.3e} alpha={best_alpha:.3f} "
                      f"max|step|={delta_max:.3e}")
            if delta_max < cfg.tol:
                return phi, it + 1, residuals, True
        return phi, cfg.max_iters, residuals, False

    # Helper: set a row of a CSR matrix to identity at column k.
    @staticmethod
    def _row_to_identity(A: csr_matrix, k: int) -> csr_matrix:
        A = A.tolil()
        A.rows[k] = [k]
        A.data[k] = [1.0]
        return A.tocsr()


# ============================================================================
# Convenience: 1D-equivalent MOS-cap (for analytical comparison)
# ============================================================================

def depletion_approximation_surface_potential(
    V_gate: float, N_A: float, t_ox: float, eps_si: float, eps_ox: float,
    material: Material = SILICON, T: float = 300.0,
    phi_ms: float = 0.0,
) -> Tuple[float, float, float]:
    """Closed-form depletion-approximation surface potential.

    Computes ``phi_s`` (surface potential), ``W_d`` (depletion width),
    and ``V_ox`` (oxide voltage drop) for a uniformly-doped P-substrate
    MOS capacitor in depletion/weak-inversion.

    Used as a ground-truth check on the 2D solver.

    References
    ----------
    Sze & Ng, "Physics of Semiconductor Devices" 3rd ed., Ch. 4.
    """
    V_T = thermal_voltage(T)
    n_i = material.n_i
    # Bulk Fermi potential (P-type: phi_F < 0)
    phi_F = -V_T * np.log(N_A / n_i)
    # Effective gate voltage (band-alignment corrected)
    V_GB = V_gate - phi_ms
    # Solve self-consistency: V_GB = phi_s - phi_F + V_ox
    # where V_ox = (Q_d / C_ox) and Q_d = sqrt(2 q eps_si N_A (phi_s - phi_F))
    # Newton on g(phi_s) = V_GB - (phi_s - phi_F) - sqrt(...)/C_ox = 0
    C_ox = eps_ox * EPS_0 / t_ox          # F/m^2
    coef = math.sqrt(2.0 * Q_E * eps_si * EPS_0 * N_A) / C_ox
    phi_s = V_GB                          # initial guess
    for _ in range(50):
        d = phi_s - phi_F
        if d <= 0:
            phi_s = phi_F + 1e-3; continue
        g    = V_GB - d - coef * math.sqrt(d)
        dg   = -1.0 - 0.5 * coef / math.sqrt(d)
        phi_s = phi_s - g / dg
        if abs(g) < 1e-9:
            break
    d = max(phi_s - phi_F, 0.0)
    W_d = math.sqrt(2.0 * eps_si * EPS_0 * d / (Q_E * N_A))
    V_ox = coef * math.sqrt(d)
    return phi_s, W_d, V_ox


__all__ = [
    "MOSCap2DConfig", "MOSCap2DState", "MOSCap2DSolver",
    "depletion_approximation_surface_potential",
]
