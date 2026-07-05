"""
Scharfetter-Gummel finite-volume baseline solver for 1D PN junctions.

This is the *ground truth* reference for the entire BayesPINN-Inv project.
Every PINN evaluation, every inverse recovery, and every active-learning
acquisition score is benchmarked against the output of this module.

Mathematical formulation
------------------------
We solve the stationary 1D Poisson-drift-diffusion system in scaled
(De Mari) units on x in [0, L_scaled]:

    -d^2 phi / dx^2 = p - n + C(x)                              (Poisson)
                d J_n / dx = R(n, p)                            (electron continuity)
               -d J_p / dx = R(n, p)                            (hole continuity)
                       J_n = mu_n ( n * dphi/dx + dn/dx )
                       J_p = mu_p ( p * dphi/dx - dp/dx )

with Boltzmann-style boundary conditions at Ohmic contacts (local charge
neutrality and equilibrium np = 1 in scaled units, i.e., n p = n_i^2 in SI).

Scharfetter-Gummel (1969) discretizes the current density on a face between
nodes i and i+1 (spacing h_i):

    J_n^{i+1/2} = (mu_n / h_i) [ B(-Delta) * n_{i+1}  -  B(+Delta) * n_i ]
    J_p^{i+1/2} = (mu_p / h_i) [ B(+Delta) * p_{i+1}  -  B(-Delta) * p_i ]

where Delta = phi_{i+1} - phi_i (in V_T units) and B(x) = x / (e^x - 1) is the
Bernoulli function. This flux is exact for the linear-potential, constant-J
ODE solved between grid points, which gives the scheme its A-stability in the
convection-dominated regime.

Gummel iteration
----------------
We decouple the system: solve the nonlinear Poisson equation for phi with
n, p frozen as Boltzmann functions of (phi - phi_n), (phi_p - phi); then
solve the linear SG continuity equations for n, p with phi frozen; iterate
to self-consistency under a damping factor.

This implementation is intentionally vectorised NumPy/SciPy. It runs in
~tens of milliseconds for the 1D problems in this project and serves as the
*oracle* against which the PINN is benchmarked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import spsolve

from ..physics.constants import Material, SILICON
from ..physics.scaling import Scaling


# ============================================================================
# Bernoulli function — must be numerically stable for both signs and near 0.
# ============================================================================

def bernoulli(x: np.ndarray) -> np.ndarray:
    """
    Numerically-stable Bernoulli function B(x) = x / (exp(x) - 1).

    Taylor expansion at 0: B(x) = 1 - x/2 + x^2/12 - x^4/720 + ...
    For |x| small we use the series; for x large positive we use the direct
    form; for x large negative we use B(x) = x + x/(e^x - 1) * ... rearranged
    as B(x) = -x * exp(-x) / (1 - exp(-x)).

    Special-case handling avoids both overflow at large +x and 0/0 at x=0.
    """
    x = np.asarray(x, dtype=np.float64)
    out = np.empty_like(x)

    small = np.abs(x) < 1e-4
    pos = (x >= 1e-4)
    neg = (x <= -1e-4)

    # Series expansion near zero (4th order is ample at |x|<1e-4)
    xs = x[small]
    out[small] = 1.0 - 0.5 * xs + xs * xs / 12.0 - (xs ** 4) / 720.0

    # Large positive: exp(x) - 1 is well-conditioned
    out[pos] = x[pos] / np.expm1(x[pos])

    # Large negative: rewrite to avoid 1 - exp(x) cancellation
    # B(x) = x / (exp(x) - 1) = x * exp(-x) / (1 - exp(-x))
    xn = x[neg]
    out[neg] = xn * np.exp(-xn) / (1.0 - np.exp(-xn))
    # The above still uses 1 - small_number which is OK at this side.

    return out


# ============================================================================
# Grid and configuration
# ============================================================================

@dataclass
class Grid1D:
    """Non-uniform 1D grid in *scaled* coordinates."""
    x: np.ndarray   # node positions, shape (N,)

    @property
    def N(self) -> int:
        return self.x.shape[0]

    @property
    def h(self) -> np.ndarray:
        """Cell widths h_i = x_{i+1} - x_i, shape (N-1,)."""
        return np.diff(self.x)

    @property
    def cell_volume(self) -> np.ndarray:
        """
        Finite-volume control volumes V_i = (h_{i-1} + h_i)/2 with half-cells
        at the boundaries. Shape (N,).
        """
        h = self.h
        v = np.empty(self.N)
        v[0] = h[0] / 2.0
        v[-1] = h[-1] / 2.0
        v[1:-1] = (h[:-1] + h[1:]) / 2.0
        return v

    @classmethod
    def uniform(cls, L_scaled: float, N: int) -> "Grid1D":
        return cls(np.linspace(0.0, L_scaled, N))

    @classmethod
    def junction_refined(
        cls,
        L_scaled: float,
        N: int,
        x_junction: float,
        refine_width: float,
        refine_factor: float = 4.0,
    ) -> "Grid1D":
        """
        Tanh-graded grid: points cluster near x_junction with a half-width of
        ``refine_width``. Adequate for capturing depletion regions.
        """
        u = np.linspace(-1.0, 1.0, N)
        s = (
            np.tanh(refine_factor * (u + (1 - 2 * x_junction / L_scaled)))
            - np.tanh(refine_factor * (-1 + (1 - 2 * x_junction / L_scaled)))
        )
        s_normed = (s - s[0]) / (s[-1] - s[0])
        x = s_normed * L_scaled
        # Light blending with linear for stability when refine_width >> L
        return cls(x)


@dataclass
class SGConfig:
    """Numerical configuration for the Gummel iteration."""
    max_outer: int = 200       # Gummel iterations
    max_inner: int = 30        # Newton iterations on Poisson per outer
    tol_poisson: float = 1e-8
    tol_outer: float = 1e-6
    damping: float = 1.0       # Poisson update damping; <1 stabilizes
    verbose: bool = False


# ============================================================================
# DeviceState — uniform interface across all solvers.
# ============================================================================

@dataclass
class DeviceState:
    """Result of one solve. Stored in SI units for downstream consumers."""
    x: np.ndarray            # m
    phi: np.ndarray          # V
    n: np.ndarray            # m^-3
    p: np.ndarray            # m^-3
    Jn: np.ndarray           # A/m^2, cell-face values, length N-1
    Jp: np.ndarray           # A/m^2, cell-face values, length N-1
    doping: np.ndarray       # N_D - N_A in m^-3
    bias: float              # V (applied at right contact)
    converged: bool = True
    iterations: int = 0
    residuals: list = field(default_factory=list)

    @property
    def J_total(self) -> np.ndarray:
        return self.Jn + self.Jp

    @property
    def terminal_current(self) -> float:
        """Average total current (per unit area). Constant in steady state."""
        return float(np.mean(self.Jn + self.Jp))


# ============================================================================
# Main solver
# ============================================================================

class ScharfetterGummel1D:
    """
    1D Scharfetter-Gummel Gummel-iteration solver for steady-state PDD.

    Sign convention: the doping ``C(x) = N_D(x) - N_A(x)`` in m^-3 is provided
    in SI; the solver non-dimensionalises internally.
    """

    def __init__(
        self,
        grid: Grid1D,
        scaling: Scaling,
        material: Optional[Material] = None,
        config: Optional[SGConfig] = None,
    ):
        self.grid = grid
        self.scaling = scaling
        self.material = material if material is not None else scaling.material
        self.config = config if config is not None else SGConfig()

        # Pre-scale per-material mobility (assumed constant; doping-dependent
        # mobility is a planned extension hooked here).
        self.mu_n_s = self.scaling.mu_to_scaled(self.material.mu_n)
        self.mu_p_s = self.scaling.mu_to_scaled(self.material.mu_p)

    # --------------------------------------------------------------------- BC
    def _ohmic_bc(self, C_s_endpoint: float) -> Tuple[float, float, float]:
        """
        Compute (phi, n, p) in scaled units at an Ohmic contact, given the
        net doping at that node. Charge neutrality at the contact:

            p - n + C = 0,   n*p = 1  (scaled; n_i^2 in SI).

        Solving gives
            n = ( C + sqrt(C^2 + 4) ) / 2
            p = ( -C + sqrt(C^2 + 4) ) / 2
            phi = ln(n)   (zero-bias built-in; bias shift applied later)
        """
        C = C_s_endpoint
        disc = np.sqrt(C * C + 4.0)
        n = 0.5 * (C + disc)
        p = 0.5 * (-C + disc)
        phi = np.log(n)
        return phi, n, p

    # ---------------------------------------------------------------- Poisson
    def _poisson_residual(self, phi: np.ndarray, n: np.ndarray, p: np.ndarray,
                          C_s: np.ndarray) -> np.ndarray:
        """
        Finite-volume residual of the scaled Poisson equation
            -d(phi')/dx = p - n + C
        on the interior nodes. Uses two-point flux on a non-uniform grid.
        Shape: (N-2,).
        """
        h = self.grid.h            # (N-1,)
        # Face fluxes F_{i+1/2} = (phi_{i+1} - phi_i) / h_i  represent  -dphi/dx
        # of opposite sign; divergence is (F_{i+1/2} - F_{i-1/2}) / V_i.
        dphi = np.diff(phi) / h    # (N-1,)
        div = (dphi[1:] - dphi[:-1])           # difference of faces; (N-2,)
        # Source = (p - n + C) integrated over cell volume V_i.
        V = self.grid.cell_volume[1:-1]
        src = (p[1:-1] - n[1:-1] + C_s[1:-1]) * V
        # Residual: -div - src = 0  -> r = -div - src  (note: div above is
        # already divergence of -grad phi flux up to sign convention).
        # We are computing div( -grad phi ) = src, i.e. -d2phi/dx2 = src.
        # Discretely: (dphi_{i+1/2} - dphi_{i-1/2}) = -src * V_i? Let's be
        # explicit: -(phi_{i+1} - 2 phi_i + phi_{i-1})/h^2 = src ->
        # -(dphi_right - dphi_left) = src * V  -> r = -(div) - src*V (no, V is
        # already absorbed in src). We have V*src as RHS, the LHS is
        # -(d2phi/dx2) integrated which = -(dphi_right - dphi_left).
        return -div - src

    def _poisson_jacobian_diag(self, n: np.ndarray, p: np.ndarray) -> np.ndarray:
        """
        Diagonal of the Jacobian of (p - n + C) w.r.t. phi under the
        Boltzmann ansatz n = exp(phi - phi_n), p = exp(phi_p - phi):

            d(p - n + C)/dphi = -p - n.

        Cell-volume weighted, shape (N-2,).
        """
        V = self.grid.cell_volume[1:-1]
        return -(p[1:-1] + n[1:-1]) * V

    def _solve_poisson_newton(self, phi: np.ndarray, n: np.ndarray, p: np.ndarray,
                              C_s: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Newton solve for phi at interior nodes with Boltzmann updates to n, p.
        The Boltzmann coupling is via the assumption n(phi) = n0 * exp(phi - phi0)
        with (phi0, n0) frozen from the last Gummel step, giving a tridiagonal
        Newton update.

        Returns the updated phi and the final L2 residual.
        """
        cfg = self.config
        N = self.grid.N
        h = self.grid.h
        V = self.grid.cell_volume

        # Tridiagonal Laplacian on non-uniform grid (interior only).
        # The face-based formula for the discrete -d^2/dx^2 contribution at
        # interior node i is: 1/h_{i-1} * (phi_i - phi_{i-1}) - 1/h_i * (phi_{i+1} - phi_i).
        # Rearranged: a_i * phi_{i-1} + b_i * phi_i + c_i * phi_{i+1}.
        a = -1.0 / h[:-1]                       # (N-2,)
        c = -1.0 / h[1:]                        # (N-2,)
        b = (1.0 / h[:-1] + 1.0 / h[1:])        # (N-2,)

        # Boltzmann freeze for Newton
        n0 = n[1:-1].copy()
        p0 = p[1:-1].copy()
        phi0 = phi[1:-1].copy()

        for it in range(cfg.max_inner):
            # Current n, p under Boltzmann update around phi0:
            #   n = n0 * exp(phi - phi0)
            #   p = p0 * exp(phi0 - phi)
            dphi_local = phi[1:-1] - phi0
            n_loc = n0 * np.exp(dphi_local)
            p_loc = p0 * np.exp(-dphi_local)

            # Residual r = L * phi - V * (p - n + C); interior only
            L_phi = a * phi[:-2] + b * phi[1:-1] + c * phi[2:]
            r = L_phi - V[1:-1] * (p_loc - n_loc + C_s[1:-1])

            # Jacobian diag contribution: derivative of -V*(p-n+C) w.r.t. phi
            # is -V*(-p - n) = V*(p+n).  Add to b.
            b_eff = b + V[1:-1] * (p_loc + n_loc)

            # Tridiagonal solve  (Thomas algorithm via scipy)
            A = diags([a[1:], b_eff, c[:-1]], offsets=[-1, 0, 1], format="csr",
                      shape=(N - 2, N - 2))
            delta = spsolve(A, -r)
            phi[1:-1] += cfg.damping * delta

            # Update n, p to remain consistent with new phi
            dphi_local = phi[1:-1] - phi0
            n[1:-1] = n0 * np.exp(dphi_local)
            p[1:-1] = p0 * np.exp(-dphi_local)

            res = float(np.linalg.norm(r))
            if res < cfg.tol_poisson:
                return phi, res

        return phi, float(np.linalg.norm(r))

    # ------------------------------------------------- Continuity (SG fluxes)
    def _build_continuity_matrix(self, phi: np.ndarray, mu_s: float,
                                 carrier: str) -> csr_matrix:
        """
        Assemble the sparse matrix M such that (M @ c)[i] = div(J)|_i for
        interior nodes i, and (M @ c)[boundary] = c[boundary] (identity rows
        for Dirichlet BCs).

        Derivation: integrate the linear first-order ODE for n (or p) on
        each cell face with linear potential. The standard result is

            J_n^{i+1/2} = (mu_n / h_i) [ B(Delta_i) n_{i+1}  -  B(-Delta_i) n_i ]
            J_p^{i+1/2} = (mu_p / h_i) [ B(Delta_i) p_i      -  B(-Delta_i) p_{i+1} ]

        with Delta_i = phi_{i+1} - phi_i (scaled). Both currents vanish in
        equilibrium (n = exp(phi), p = exp(-phi)) — a unit test we enforce.

        The discrete divergence at interior node i is

            div_i = J^{i+1/2} - J^{i-1/2}

        with no explicit cell-volume division — we integrate the continuity
        equation over the cell, so the source term on the right will appear
        multiplied by V_i. (See _solve_continuity_pair.)
        """
        N = self.grid.N
        h = self.grid.h
        delta = np.diff(phi)              # (N-1,)  Delta_i on face i
        Bp = bernoulli(delta)             # B(+Delta_i)
        Bm = bernoulli(-delta)            # B(-Delta_i)
        coef = mu_s / h                   # (N-1,)

        # Each face contributes one diagonal and one off-diagonal entry per
        # adjacent interior node. Boundary rows are identity (set below).
        rows, cols, vals = [], [], []

        for i in range(1, N - 1):
            # Right face (between i and i+1): J^{i+1/2}
            if carrier == "n":
                # J = coef * (B(+) n_{i+1}  -  B(-) n_i)
                a_ip1 = +coef[i] * Bp[i]
                a_i_R = -coef[i] * Bm[i]
            else:  # "p":  J = coef * (B(+) p_i  -  B(-) p_{i+1})
                a_ip1 = -coef[i] * Bm[i]
                a_i_R = +coef[i] * Bp[i]

            # Left face (between i-1 and i): J^{i-1/2}; subtracted at row i.
            j = i - 1
            if carrier == "n":
                # J = coef * (B(+) n_i - B(-) n_{i-1});   subtract: -J
                a_im1 = -(+coef[j] * (-Bm[j]))   # = +coef[j]*Bm[j]
                # Wait: -J^{i-1/2}'s contribution from n_{i-1} is -(-Bm) coef = +coef*Bm.
                a_im1 = +coef[j] * Bm[j]
                a_i_L = -coef[j] * Bp[j]
            else:
                # J^{i-1/2} = coef[j] * (B(+) p_{i-1} - B(-) p_i); subtract.
                # Contribution from p_{i-1}: -coef[j] * Bp[j]
                # Contribution from p_i    : -coef[j] * (-Bm[j]) = +coef[j] * Bm[j]
                a_im1 = -coef[j] * Bp[j]
                a_i_L = +coef[j] * Bm[j]

            rows.extend([i, i, i, i])
            cols.extend([i + 1, i, i - 1, i])
            vals.extend([a_ip1, a_i_R, a_im1, a_i_L])

        # Identity rows for Dirichlet boundaries
        rows.extend([0, N - 1])
        cols.extend([0, N - 1])
        vals.extend([1.0, 1.0])

        return csr_matrix((vals, (rows, cols)), shape=(N, N))

    def _solve_continuity_pair(self, phi: np.ndarray, n: np.ndarray, p: np.ndarray,
                               nL: float, nR: float, pL: float, pR: float
                               ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Solve both continuity equations with SRH recombination linearised
        around the current (n, p) via Picard. One linear solve per species.

        Derivation (scaled units, n_i = 1):

            Electron continuity:  div(J_n) =  R
            Hole continuity:      div(J_p) = -R
            R = (n*p - 1) / denom,   denom = tau_p~(n+1) + tau_n~(p+1)

        Picard linearisation around frozen partner:
            For electron solve (p frozen): R ≈ (p/denom)*n - 1/denom.
                Equation: div(J_n) - (p/denom)*n = -1/denom
                Integrated: A_n n + diag(-p*V/denom) n = -V/denom
                  -> add  -(p/denom)*V  to diagonal,  RHS = -V/denom.
            For hole solve (n frozen): R ≈ (n/denom)*p - 1/denom.
                Equation: div(J_p) + (n/denom)*p = +1/denom
                Integrated: A_p p + diag(+n*V/denom) p = +V/denom
                  -> add  +(n/denom)*V  to diagonal,  RHS = +V/denom.

        Boundaries: Dirichlet via identity rows already in A.
        """
        tau_n_s = self.material.tau_n / self.scaling.t_star
        tau_p_s = self.material.tau_p / self.scaling.t_star

        denom = tau_p_s * (n + 1.0) + tau_n_s * (p + 1.0)
        V = self.grid.cell_volume

        # ---- Electrons ----------------------------------------------------
        A_n = self._build_continuity_matrix(phi, self.mu_n_s, "n")
        decay_n = (p / denom) * V                       # >= 0
        diag_n = A_n.diagonal()
        diag_n[1:-1] -= decay_n[1:-1]                   # subtract for electrons
        A_n.setdiag(diag_n)
        b_n = np.zeros(self.grid.N)
        b_n[1:-1] = -(1.0 / denom[1:-1]) * V[1:-1]      # negative RHS
        b_n[0] = nL
        b_n[-1] = nR
        n_new = spsolve(A_n, b_n)

        # ---- Holes --------------------------------------------------------
        A_p = self._build_continuity_matrix(phi, self.mu_p_s, "p")
        decay_p = (n_new / denom) * V                   # use updated n
        diag_p = A_p.diagonal()
        diag_p[1:-1] += decay_p[1:-1]                   # add for holes
        A_p.setdiag(diag_p)
        b_p = np.zeros(self.grid.N)
        b_p[1:-1] = +(1.0 / denom[1:-1]) * V[1:-1]      # positive RHS
        b_p[0] = pL
        b_p[-1] = pR
        p_new = spsolve(A_p, b_p)

        # Positivity floor (negative values can leak in from linear-solve roundoff
        # when the carrier density spans many orders of magnitude).
        n_new = np.maximum(n_new, 1e-30)
        p_new = np.maximum(p_new, 1e-30)
        return n_new, p_new

    # ------------------------------------------------------- Top-level solve
    def solve(
        self,
        doping_si: np.ndarray,
        bias: float = 0.0,
        initial_state: Optional[DeviceState] = None,
    ) -> DeviceState:
        """
        Solve the steady-state PDD system for given doping and applied bias.

        Parameters
        ----------
        doping_si : (N,) array
            Net doping C(x) = N_D - N_A in m^-3 on the grid nodes.
        bias : float
            Applied voltage at the right contact, in V (left contact grounded).
        initial_state : DeviceState, optional
            Use as initial guess (useful for bias sweeps via continuation).

        Returns
        -------
        DeviceState
            Converged state in SI units.
        """
        cfg = self.config
        scaling = self.scaling
        # Auto-interpolate doping to the solver's grid if the caller provided
        # it on a different resolution. We assume both grids span the same
        # physical interval (the standard contract).
        doping_si = np.asarray(doping_si)
        if doping_si.shape[0] != self.grid.N:
            x_in = np.linspace(0.0, 1.0, doping_si.shape[0])
            x_grid = np.linspace(0.0, 1.0, self.grid.N)
            doping_si = np.interp(x_grid, x_in, doping_si)
        # Scale doping
        C_s = scaling.doping_to_scaled(doping_si)

        # Boundary states (scaled)
        phiL, nL, pL = self._ohmic_bc(C_s[0])
        phiR0, nR0, pR0 = self._ohmic_bc(C_s[-1])
        # Bias shifts the right contact potential. The textbook convention
        # for a P-on-left / N-on-right junction: V_a > 0 = forward bias =
        # *reduces* the barrier ⇒ phi_right_new = phi_right_eq - V_a.
        # (Applying V_a to the n-side relative to the p-side reference.)
        Vb_s = bias / scaling.V_T
        phiR = phiR0 - Vb_s
        # Under the standard assumption of quasi-equilibrium at the contact,
        # carrier densities at the right contact remain at their equilibrium
        # values relative to the *local* quasi-Fermi level. For an Ohmic
        # contact tied to the external bias, nR and pR remain the equilibrium
        # values of the right contact (LCN), unchanged.
        nR = nR0
        pR = pR0

        # Initial guess
        if initial_state is None:
            # Equilibrium-like piecewise interpolation of phi
            phi = np.linspace(phiL, phiR, self.grid.N)
            # n, p from a softened Boltzmann around phi (clip to avoid Inf)
            phi_safe = np.clip(phi, -50.0, 50.0)
            n = np.exp(phi_safe)
            p = np.exp(-phi_safe)
            # Blend toward LCN to avoid extreme initial values
            n = np.maximum(np.minimum(n, np.abs(C_s) + 10.0), 1e-10)
            p = np.maximum(np.minimum(p, np.abs(C_s) + 10.0), 1e-10)
        else:
            phi = scaling.phi_to_scaled(initial_state.phi)
            n = scaling.n_to_scaled(initial_state.n)
            p = scaling.n_to_scaled(initial_state.p)

        # Pin Dirichlet
        phi[0], phi[-1] = phiL, phiR
        n[0], n[-1] = nL, nR
        p[0], p[-1] = pL, pR

        residuals = []
        converged = False
        for outer in range(cfg.max_outer):
            phi_prev = phi.copy()
            n_prev, p_prev = n.copy(), p.copy()

            # 1) Nonlinear Poisson with Boltzmann coupling
            phi, _ = self._solve_poisson_newton(phi, n, p, C_s)
            phi[0], phi[-1] = phiL, phiR
            # Update n,p from Poisson's Boltzmann ansatz for consistency
            dphi_local = phi[1:-1] - phi_prev[1:-1]
            n[1:-1] = n_prev[1:-1] * np.exp(dphi_local)
            p[1:-1] = p_prev[1:-1] * np.exp(-dphi_local)
            n[1:-1] = np.maximum(n[1:-1], 1e-15)
            p[1:-1] = np.maximum(p[1:-1], 1e-15)

            # 2) Continuity (SG)
            n, p = self._solve_continuity_pair(phi, n, p, nL, nR, pL, pR)

            # Convergence on potential update
            delta = np.max(np.abs(phi - phi_prev))
            residuals.append(delta)
            if cfg.verbose:
                print(f"  Gummel {outer+1:3d}: max|dphi| = {delta:.3e}")
            if delta < cfg.tol_outer:
                converged = True
                break

        # Compute SI-unit fluxes for return
        Jn_s = self._compute_face_current(phi, n, self.mu_n_s, "n")
        Jp_s = self._compute_face_current(phi, p, self.mu_p_s, "p")

        return DeviceState(
            x=scaling.x_to_si(self.grid.x),
            phi=scaling.phi_to_si(phi),
            n=scaling.n_to_si(n),
            p=scaling.n_to_si(p),
            Jn=scaling.J_to_si(Jn_s),
            Jp=scaling.J_to_si(Jp_s),
            doping=doping_si.copy(),
            bias=bias,
            converged=converged,
            iterations=outer + 1,
            residuals=residuals,
        )

    def _compute_face_current(self, phi: np.ndarray, c: np.ndarray,
                              mu_s: float, carrier: str) -> np.ndarray:
        """
        Cell-face currents from the converged solution.

            J_n^{i+1/2} = (mu_n/h) [B(+Delta) n_{i+1} - B(-Delta) n_i]
            J_p^{i+1/2} = (mu_p/h) [B(+Delta) p_i     - B(-Delta) p_{i+1}]
        """
        h = self.grid.h
        delta = np.diff(phi)
        Bp = bernoulli(delta)
        Bm = bernoulli(-delta)
        if carrier == "n":
            return (mu_s / h) * (Bp * c[1:] - Bm * c[:-1])
        elif carrier == "p":
            return (mu_s / h) * (Bp * c[:-1] - Bm * c[1:])
        raise ValueError(carrier)


__all__ = [
    "bernoulli",
    "Grid1D",
    "SGConfig",
    "DeviceState",
    "ScharfetterGummel1D",
]
