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

from ..physics.constants import EPS_0, Q_E, SILICON, Material, thermal_voltage
from ..physics.scaling import Scaling
from .grid_2d import Grid2D, MOSCapBoundary

# ============================================================================
# Configuration + state
# ============================================================================

@dataclass
class MOSCap2DConfig:
    """Newton-Raphson parameters for the 2D Poisson solve."""
    max_iters: int = 50
    tol: float = 1e-8          # absolute Newton step size (volts)
    tol_rel: float = 1e-9      # relative residual: ||r||_inf / characteristic
    damping: float = 1.0       # 1.0 = full Newton step; reduce if oscillating
    phi_init: str = "lcn"      # cold start at local charge neutrality
    clip_arg: float = 60.0     # cap |phi/V_T| in exp() to avoid overflow
    max_bias_step_VT: float = 5.0   # continuation step size, in units of V_T
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
    #: True if |phi|/V_T hit ``clip_arg`` anywhere in the semiconductor. The
    #: Boltzmann carrier model was saturated there, so the solution is
    #: outside the solver's validated range even if ``converged`` is True.
    carrier_clipping_active: bool = False

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
        # Face areas must match the half-cells used by cell_volume
        # (BUG-08, docs/AUDIT_MASTER.md). A node on the x = 0 / x = Lx
        # Neumann boundary owns a half control volume, so its charge integral
        # is halved -- but its *north/south* faces are also only hx/2 wide.
        # The old assembly used the full hx there while cell_volume
        # already used hx/2, making the scheme non-conservative at the
        # Neumann boundary: the boundary columns got twice the vertical
        # conductance they should per unit charge. On a problem that is
        # exactly 1D (uniform doping, no lateral structure) the potential
        # then bowed by ~1.5 mV toward the side walls, decaying only as
        # O(1/Nx) instead of being identically flat.
        wx = np.full(Nx, hx, dtype=np.float64)
        wx[0] = wx[-1] = 0.5 * hx
        wy = np.full(Ny, hy, dtype=np.float64)
        wy[0] = wy[-1] = 0.5 * hy

        for j in range(Ny):
            for i in range(Nx):
                k = idx(i, j)
                ax = wy[j] / hx    # east/west face area = wy_j, distance = hx
                ay = wx[i] / hy    # north/south face area = wx_i, distance = hy
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

        # Initialize phi. Cold start = local charge neutrality (phi_F
        # everywhere), which is the standard TCAD initial guess and is the
        # exact solution at flat band.
        #
        # BUG-06 (docs/AUDIT_MASTER.md): the boundary rows used to be pinned
        # to the *target* bias right here, before phi_top_now was measured
        # from them a few lines below. The continuation therefore always
        # measured a travel distance of exactly zero, computed n_steps = 1
        # and jumped straight to the full bias -- i.e. the bias continuation
        # that exists precisely to keep Newton out of the stiff exponential
        # regime never executed on a cold start. Newton then diverged for
        # every |V_gate| >~ 1 V, growing the residual by up to 16 orders of
        # magnitude. The boundary rows are now pinned inside the
        # continuation loop only, where they belong.
        if initial_state is not None:
            phi2d = initial_state.phi.copy()
        else:
            phi2d = np.full((Ny, Nx), phi_F)

        # ---------------- Bias continuation ----------------
        # We step from the current top-Dirichlet value to the target in
        # increments of at most V_step_max. For each intermediate target,
        # run damped-Newton to convergence.
        phi_top_now = float(np.mean(phi2d[-1, :]))
        phi_bot_now = float(np.mean(phi2d[0, :]))
        V_step_max = cfg.max_bias_step_VT * V_T
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
        clipped_any = False
        for step_idx in range(1, n_steps + 1):
            frac = step_idx / n_steps
            phi_bot = phi_bot_now + frac * (phi_bot_target - phi_bot_now)
            phi_top = phi_top_now + frac * (phi_top_target - phi_top_now)
            # Update boundary rows of phi to the new target
            phi2d[0, :]  = phi_bot
            phi2d[-1, :] = phi_top
            phi = phi2d.flatten()

            phi, step_iters, step_res, step_conv, step_clip = self._newton_solve(
                phi, phi_bot, phi_top, semi_flat, C_flat, V_flat,
                V_T, n_i, cfg,
            )
            clipped_any |= step_clip
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
            residuals=all_residuals, carrier_clipping_active=clipped_any,
        )

    def _newton_solve(self, phi, phi_bot, phi_top, semi_flat, C_flat, V_flat,
                      V_T, n_i, cfg):
        """Damped-Newton solve of the nonlinear Poisson at one bias step.

        Returns ``(phi, n_iters, residuals, converged, clipped)``.

        Scale-aware tolerances (BUG-05, docs/AUDIT_MASTER.md)
        ----------------------------------------------------
        The residual ``r = L phi + q V (p - n + C)`` carries the units of the
        finite-volume charge integral, so its magnitude depends on the mesh
        spacing, the doping and the permittivity -- for this project's
        default MOS-cap it sits near 1e-5, and on another mesh it moves by
        orders of magnitude. The previous implementation compared it against
        two hard-coded absolute constants: it declared convergence at
        ``r_norm < 1e-6`` and, fatally, *skipped the Armijo line search*
        whenever ``r_norm < 1e-4``. Since the residual is essentially always
        below 1e-4, the line search was dead code and every iteration took
        an unguarded full Newton step into a stiff exponential.

        We therefore normalise the residual by the characteristic size of
        the terms that build it, so ``r_rel`` is a genuine relative error,
        and we always run the line search: Armijo tries alpha = 1 first, so
        a healthy Newton step costs one extra residual evaluation.
        """
        residuals: List[float] = []
        clipped_ever = False

        # Fixed characteristic scale: the ionised dopant charge held in the
        # largest control volume. This is the natural magnitude of the
        # Poisson right-hand side and, crucially, it does NOT collapse as the
        # iteration converges -- normalising by max(|L phi|, |charge|)
        # instead makes r_rel identically 1 whenever the Laplacian term
        # vanishes (e.g. at flat band), which is precisely where the solve is
        # already exact.
        _arg0 = np.clip(phi / V_T, -cfg.clip_arg, cfg.clip_arg)
        _chg0 = Q_E * V_flat * np.where(
            semi_flat,
            n_i * np.exp(-_arg0) - n_i * np.exp(_arg0) + C_flat, 0.0)
        charge_scale = max(
            float(Q_E * np.max(V_flat) * max(float(np.max(np.abs(C_flat))), n_i)),
            float(np.max(np.abs(_chg0))),
            float(np.max(np.abs(self._L @ phi))),
            np.finfo(np.float64).tiny,
        )
        # Interior (non-Dirichlet) mask: the Dirichlet rows carry volts, not
        # charge, and must not be mixed into the same norm.
        interior = np.ones(phi.size, dtype=bool)
        interior[self._dirichlet_idx_bottom] = False
        interior[self._dirichlet_idx_top] = False

        def _residual(ph):
            raw = ph / V_T
            clipped = bool(np.any(np.abs(raw[semi_flat]) > cfg.clip_arg))
            arg = np.clip(raw, -cfg.clip_arg, cfg.clip_arg)
            nn = np.where(semi_flat, n_i * np.exp(arg), 0.0)
            pp = np.where(semi_flat, n_i * np.exp(-arg), 0.0)
            charge = Q_E * V_flat * np.where(semi_flat, (pp - nn + C_flat), 0.0)
            rr = self._L @ ph + charge
            rr[self._dirichlet_idx_bottom] = (ph[self._dirichlet_idx_bottom]
                                              - phi_bot)
            rr[self._dirichlet_idx_top] = ph[self._dirichlet_idx_top] - phi_top
            r_rel = float(np.max(np.abs(rr[interior]))) / charge_scale
            return rr, nn, pp, r_rel, clipped

        for it in range(cfg.max_iters):
            r, n, p, r_rel, clipped = _residual(phi)
            clipped_ever |= clipped
            residuals.append(r_rel)
            if r_rel < cfg.tol_rel:
                return phi, it + 1, residuals, True, clipped_ever

            # Jacobian. Where the exponential argument is clipped the model
            # is locally constant, so its derivative is zero; using the
            # unclipped derivative there would make Newton solve a
            # linearisation inconsistent with the residual it reduces.
            raw = phi / V_T
            active = np.abs(raw) <= cfg.clip_arg
            # BUG-07 (docs/AUDIT_MASTER.md): this term had the WRONG SIGN.
            #   r(phi)  = L phi + q V (p - n + C),  with L phi = +div(eps grad phi)
            #   n = n_i exp(+phi/V_T)  ->  dn/dphi = +n/V_T
            #   p = n_i exp(-phi/V_T)  ->  dp/dphi = -p/V_T
            #   => dr/dphi = L + q V (dp/dphi - dn/dphi) = L - (q V / V_T)(n + p)
            # The old code added +(q V/V_T)(n+p), so Newton was solving a
            # linearisation whose charge block pointed the wrong way. With the
            # correct sign J is a negative-definite M-matrix (negative diagonal,
            # positive off-diagonals) and Newton converges quadratically.
            d_charge = (Q_E * V_flat / V_T) * np.where(
                semi_flat & active, n + p, 0.0)
            J = self._L - diags(d_charge, 0, shape=self._L.shape, format="csr")
            J = self._apply_dirichlet_rows(J)

            delta = spsolve(J.tocsc(), -r)
            if not np.all(np.isfinite(delta)):
                return phi, it + 1, residuals, False, clipped_ever

            alpha, accepted = 1.0, False
            for _ in range(40):
                trial = phi + cfg.damping * alpha * delta
                _, _, _, rt_rel, _ = _residual(trial)
                if rt_rel < r_rel:
                    phi, accepted = trial, True
                    break
                alpha *= 0.5
            if not accepted:
                # No descent found: report honestly instead of stepping anyway.
                return phi, it + 1, residuals, False, clipped_ever
            if float(np.max(np.abs(cfg.damping * alpha * delta))) < cfg.tol:
                _, _, _, r_rel, _ = _residual(phi)
                residuals.append(r_rel)
                return (phi, it + 1, residuals,
                        bool(r_rel < cfg.tol_rel), clipped_ever)

        _, _, _, r_rel, _ = _residual(phi)
        return (phi, cfg.max_iters, residuals,
                bool(r_rel < cfg.tol_rel), clipped_ever)

    def _apply_dirichlet_rows(self, A: csr_matrix) -> csr_matrix:
        """Replace the Dirichlet rows of ``A`` with identity rows.

        Vectorised. The previous helper round-tripped the entire matrix
        through LIL format once *per boundary node per Newton iteration*,
        which dominated the solve cost.
        """
        N = A.shape[0]
        keep = np.ones(N, dtype=np.float64)
        keep[self._dirichlet_idx_bottom] = 0.0
        keep[self._dirichlet_idx_top] = 0.0
        return (diags(keep, format="csr") @ A
                + diags(1.0 - keep, format="csr")).tocsr()


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
    "MOSCap2DConfig",
    "MOSCap2DSolver",
    "MOSCap2DState",
    "depletion_approximation_surface_potential",
]
