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
                       J_n = mu_n ( dn/dx - n * dphi/dx )
                       J_p = -mu_p ( dp/dx + p * dphi/dx )

Sign convention (verified against the implementation, see
tests/test_sg_convergence.py::test_drift_diffusion_continuum_limit): the
electric field is E = -dphi/dx, consistent with the Poisson equation above,
so the scaled electron current is J_n = mu_n (n E + dn/dx) and the scaled
hole current is J_p = mu_p (p E - dp/dx). Both reduce to zero in
equilibrium, where n = exp(phi) and p = exp(-phi).

with Boltzmann-style boundary conditions at Ohmic contacts (local charge
neutrality and equilibrium np = 1 in scaled units, i.e., n p = n_i^2 in SI).

Scharfetter-Gummel (1969) discretizes the current density on a face between
nodes i and i+1 (spacing h_i):

    J_n^{i+1/2} = (mu_n / h_i) [ B(+Delta) * n_{i+1}  -  B(-Delta) * n_i ]
    J_p^{i+1/2} = (mu_p / h_i) [ B(+Delta) * p_i      -  B(-Delta) * p_{i+1} ]

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
from typing import Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import spsolve

from ..physics.constants import Material
from ..physics.scaling import Scaling

# ============================================================================
# Bernoulli function — must be numerically stable for both signs and near 0.
# ============================================================================

#: Below this |x| the Taylor series is used (avoids 0/0 at x = 0).
B_SMALL: float = 1e-4
#: Above this x, expm1(x) would overflow; x*exp(-x) underflows to 0 instead.
B_LARGE: float = 700.0
#: |quasi-Fermi drop| above which the direct flux difference is used instead
#: of the expm1 form (no cancellation there, and expm1 would overflow).
_U_MAX: float = 500.0
#: Hard clip on any exponent, so a pathological iterate yields a large finite
#: number rather than inf -> NaN. np.exp overflows just above 709.
_EXP_CLIP: float = 700.0

def bernoulli(x: np.ndarray) -> np.ndarray:
    """
    Numerically-stable Bernoulli function B(x) = x / (exp(x) - 1).

    Three branches, chosen so that the result is accurate *and finite* for
    every finite double-precision input:

    * ``|x| < B_SMALL``  -- Taylor series ``1 - x/2 + x^2/12 - x^4/720``.
      ``expm1`` is exact here too, but ``x/expm1(x)`` is 0/0 at x = 0.
    * ``x > B_LARGE``    -- ``B(x) = x*exp(-x)/(1-exp(-x)) ~ x*exp(-x)``.
      Using ``x/expm1(x)`` would overflow ``expm1`` to ``+inf``; the answer
      would still round to the correct 0, but with a spurious overflow
      warning. ``x*exp(-x)`` underflows gracefully to 0 instead.
    * otherwise          -- ``x/expm1(x)``.

    Note on the negative side: ``expm1`` is *designed* for the ``exp(x)-1``
    cancellation as ``x -> 0``, and for ``x -> -inf`` it saturates cleanly at
    ``-1`` so that ``B(x) -> -x``. No rewrite is needed there, and any
    rewrite involving ``exp(-x)`` overflows for ``x < -709`` (see BUG-01 in
    docs/AUDIT_MASTER.md: the previous implementation returned ``inf`` at
    ``x = -709`` and ``NaN`` below it, silently poisoning the entire
    continuity matrix whenever a single face potential drop exceeded
    ~709 V_T ~ 18.3 V at 300 K).

    Exactness check used in the test suite: B(x) - B(-x) = -x identically.
    """
    x = np.asarray(x, dtype=np.float64)
    out = np.empty_like(x)

    small = np.abs(x) < B_SMALL
    large_pos = x > B_LARGE
    rest = ~(small | large_pos)

    # Series expansion near zero (4th order is ample at |x| < 1e-4)
    xs = x[small]
    out[small] = 1.0 - 0.5 * xs + xs * xs / 12.0 - (xs ** 4) / 720.0

    # Large positive: exp(x)-1 ~ exp(x); x*exp(-x) underflows to 0 cleanly.
    xl = x[large_pos]
    out[large_pos] = xl * np.exp(-xl)

    # Everything else, both signs: expm1 is well-conditioned throughout.
    xr = x[rest]
    out[rest] = xr / np.expm1(xr)

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
        Grid whose cells are *smallest* at ``x_junction``, widening over a
        half-width of ``refine_width`` (same scaled units as ``L_scaled``).

        Construction: integrate a positive cell-density function

            rho(x) = 1 + (refine_factor - 1) * sech^2((x - x_junction)/w)

        and invert the resulting CDF on equispaced points. Because ``rho``
        is the *density of nodes*, spacing goes like ``1/rho`` and is
        therefore ``refine_factor`` times finer at the junction than in the
        bulk -- which is what "refined" means.

        BUG-02 (docs/AUDIT_MASTER.md): the previous implementation mapped
        equispaced points through ``tanh`` directly. Since spacing is
        proportional to the *derivative* of the map, and ``tanh`` is
        steepest at its centre, that construction put the **coarsest** cells
        at the junction -- 599x coarser than at the contacts for the default
        arguments -- i.e. it de-refined exactly the depletion region it was
        meant to resolve. ``refine_width`` was also never read.
        """
        if N < 2:
            raise ValueError("junction_refined needs N >= 2")
        if not (L_scaled > 0.0):
            raise ValueError("L_scaled must be positive")
        if not (refine_width > 0.0):
            raise ValueError("refine_width must be positive")
        if not (refine_factor >= 1.0):
            raise ValueError("refine_factor must be >= 1")
        # Oversampled quadrature of the node-density function.
        m = max(8 * N, 2048)
        xq = np.linspace(0.0, L_scaled, m)
        rho = 1.0 + (refine_factor - 1.0) / np.cosh(
            (xq - x_junction) / refine_width) ** 2
        cdf = np.concatenate([[0.0], np.cumsum(0.5 * (rho[1:] + rho[:-1])
                                               * np.diff(xq))])
        cdf /= cdf[-1]
        x = np.interp(np.linspace(0.0, 1.0, N), cdf, xq)
        # Pin the endpoints exactly (interp can be off by rounding).
        x[0], x[-1] = 0.0, L_scaled
        return cls(x)


@dataclass
class SGConfig:
    """Numerical configuration for the Gummel iteration.

    ``tol_outer`` alone is **not** a sufficient convergence test. The
    potential converges within 2-3 Gummel sweeps while the carrier
    densities are still far from self-consistent, because phi is almost
    insensitive to the minority carriers (they are ~12 decades below the
    majority density). Declaring convergence on max|dphi| alone reports
    success on a state whose continuity residual is 100% of the current
    scale -- see BUG-03 in docs/AUDIT_MASTER.md. We therefore additionally
    require the *relative* carrier update to fall below ``tol_carrier``.
    """
    max_outer: int = 200       # Gummel iterations
    max_inner: int = 30        # Newton iterations on Poisson per outer
    tol_poisson: float = 1e-8
    tol_outer: float = 1e-6    # on max|dphi| (scaled units)
    tol_carrier: float = 1e-8  # on max relative carrier update
    # BUG-13: `tol_carrier` is a *relative* test applied to an array whose
    # entries span up to 16 decades (majority ~1e8, minority ~1e-8 in scaled
    # units at 1e24 m^-3). Entries many decades below max|c| cannot be
    # resolved to 1e-8 relative: their update floors at the round-off of the
    # linear solve, ~O(1e4) * eps * max|c|. Requiring 1e-8 there is
    # unsatisfiable, so the iteration stalled and reported converged=False on
    # a state whose potential was converged to 1e-12 and whose V_bi was exact.
    #
    # A solve is therefore also accepted when the *absolute* carrier update
    # has reached that round-off floor:
    #     max|dc| <= carrier_roundoff_factor * eps * max|c|
    # Measured across doping 1e21-1e25 m^-3 x N in {201,401} x bias in
    # {0, 0.3, 0.6, 0.9, -2} V (scripts/../tests/test_sg_numerics.py):
    #     round-off stagnation : ratio 4.9e2 - 1.1e4,  max|dphi| <= 3.6e-12
    #     genuine divergence   : ratio 2.1e15 - 1.2e18, max|dphi| >= 6.7e-01
    # The two populations are separated by ELEVEN orders of magnitude, so the
    # threshold is not tuned: any value in [1e5, 1e13] yields an identical
    # classification (asserted in test_roundoff_threshold_is_not_tuned).
    # The default sits at the bottom of that plateau (9x above the worst
    # measured stagnation, 1e10 below the mildest measured divergence) so
    # that a BUG-03-style 1% error on a deep-minority node is still rejected.
    carrier_roundoff_factor: float = 1e5
    damping: float = 1.0       # Poisson update damping; <1 stabilizes
    equilibrate: bool = True   # two-sided scaling of the continuity systems
    stall_patience: int = 10   # stop after this many non-improving sweeps
    max_dphi: float = 5.0      # cap on |Poisson-Newton potential update|, V_T
    auto_continuation: bool = True   # retry a failed cold solve by bias ramp
    continuation_step_V: float = 0.05  # bias increment for that retry, volts
    verbose: bool = False


# ============================================================================
# Equilibrated sparse solve
# ============================================================================

def solve_equilibrated(A: csr_matrix, b: np.ndarray) -> np.ndarray:
    """Solve ``A x = b`` after two-sided (row + column) infinity-norm scaling.

    Why this matters here
    ---------------------
    The Scharfetter-Gummel continuity matrix inherits the carrier dynamic
    range: in a 1 um Si PN diode the electron density spans 12 decades
    between the n-side bulk and the p-side minority tail. That leaves the
    matrix badly *unequilibrated* -- its row infinity-norms span ~4 decades
    even though its condition number is only ~5e5 -- and a plain sparse LU
    then commits a relative error on the small (minority-carrier) components
    many orders of magnitude above machine epsilon.

    Measured on the project's reference 1 um Si diode at equilibrium
    (BUG-03, docs/AUDIT_MASTER.md): plain ``spsolve`` violates the
    mass-action law ``n p = 1`` by 1.3e-2; after equilibration the violation
    is 7.6e-6, a 1730x improvement, at negligible cost. This is the standard
    remedy for poorly scaled systems (Higham, *Accuracy and Stability of
    Numerical Algorithms*, 2nd ed., ch. 7).

    The scaling is exact -- it introduces no approximation, only a
    similarity transform of the linear system -- so it can be applied
    unconditionally.
    """
    A = A.tocsr()
    tiny = np.finfo(np.float64).tiny
    r = 1.0 / np.maximum(abs(A).max(axis=1).toarray().ravel(), tiny)
    Ar = diags(r) @ A
    c = 1.0 / np.maximum(abs(Ar).max(axis=0).toarray().ravel(), tiny)
    x = spsolve((Ar @ diags(c)).tocsc(), b * r)
    return x * c


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
    #: True when convergence was accepted because the carrier update reached
    #: the linear-solve round-off floor rather than the strict relative
    #: tolerance (BUG-13). The state is usable; this records *why* it was
    #: accepted so nothing is hidden from the consumer.
    stalled_at_roundoff: bool = False
    #: max relative carrier update on the accepted iterate.
    final_carrier_update: float = 0.0

    @property
    def J_total(self) -> np.ndarray:
        return self.Jn + self.Jp

    @property
    def terminal_current(self) -> float:
        """Average total current (per unit area). Constant in steady state."""
        return float(np.mean(self.Jn + self.Jp))

    @property
    def current_noise_floor(self) -> float:
        """Numerical noise floor on :attr:`terminal_current`, in A/m^2.

        In steady state ``div(J_n + J_p) = 0`` exactly, so the total current
        must be *constant* across every cell face. Any observed spread is
        pure numerical error (discretization + linear algebra + incomplete
        Gummel convergence). The face-to-face standard deviation is
        therefore a direct, assumption-free estimate of the uncertainty on
        the reported terminal current -- the oracle measuring its own error
        bar.

        Use :attr:`current_is_trustworthy` rather than this number alone.
        """
        return float(np.std(self.Jn + self.Jp))

    def current_is_trustworthy(self, snr: float = 10.0) -> bool:
        """True when the solve converged *and* |I| exceeds ``snr`` x the floor.

        Terminal currents that fail this test are numerical noise, not
        physics, and must not be used as supervision labels or as inverse
        design targets. Near zero bias a PN diode's true current falls below
        the floor of any finite-precision drift-diffusion solve, so this
        flag is the honest boundary of the oracle's validated range.

        The convergence check is part of the test rather than left to the
        caller. A non-converged state can carry a large current with a small
        face-to-face spread -- measured at +100 V: ``converged=False`` but
        ``I = 3.0e10`` A/m^2 with an SNR far above the threshold. Every
        in-tree caller happened to write ``st.converged and
        st.current_is_trustworthy()``, so this only removes a footgun for
        callers who did not; it cannot loosen any existing result.
        """
        if not self.converged:
            return False
        floor = self.current_noise_floor
        return bool(abs(self.terminal_current) > snr * floor)


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
        C = float(C_s_endpoint)
        disc = np.sqrt(C * C + 4.0)
        # BUG-11 (docs/AUDIT_MASTER.md): evaluating *both* roots from the
        # quadratic destroys the minority carrier by cancellation. For C > 0,
        # 0.5*(-C + sqrt(C^2+4)) subtracts two numbers that agree to machine
        # precision once C^2 >> 4: the minority density is wrong by 0.35% at
        # C_s = 1e7 (N = 1e23 m^-3, an ordinary doping level), by 25% at 1e8,
        # and is exactly 0.0 at 1e9 -- whereupon log(0) = -inf and the entire
        # solve returns NaN. The claimed doping range is 1e21-1e25 m^-3, i.e.
        # C_s up to 1e9, so this covered the top two decades of it.
        #
        # Stable form: take the majority carrier from the quadratic (no
        # cancellation there, the two terms add) and the minority from the
        # mass-action law n*p = 1, which the pair satisfies exactly.
        if C >= 0.0:
            n = 0.5 * (C + disc)
            p = 1.0 / n
        else:
            p = 0.5 * (-C + disc)
            n = 1.0 / p
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
        Damped-Newton solve for phi at interior nodes with Boltzmann updates to
        n, p. The Boltzmann coupling assumes n(phi) = n0 * exp(phi - phi0) with
        (phi0, n0) frozen from the last Gummel step, giving a tridiagonal
        Newton update.

        Globalisation (BUG-10, docs/AUDIT_MASTER.md)
        --------------------------------------------
        The nonlinear Poisson equation with Boltzmann carriers is
        exponentially stiff, and an undamped Newton step diverges violently:
        the update enters ``exp``, overflows to ``inf``, the Jacobian becomes
        *exactly singular*, ``spsolve`` returns ``NaN`` and the whole solve is
        poisoned. Measured before this fix: the LDD profile
        (-1e22 / 5e21 / 5e23 m^-3) returned ``NaN`` at every bias, and an
        asymmetric step (1e21 / 5e22) returned currents of ~1e9 A/m^2 -- four
        orders of magnitude above anything physical -- at every bias. Both are
        device families this project explicitly claims to support.

        Two standard safeguards, both required:

        * **Potential-update limiting.** Each Newton correction is capped at
          ``cfg.max_dphi`` thermal voltages. This is the classical remedy for
          the exponential Poisson nonlinearity and is what production TCAD
          does.
        * **Backtracking on the residual.** A step is accepted only if it
          reduces ``||r||``; otherwise it is halved. Combined with the cap,
          Newton can no longer walk into the overflow region.

        The exponent is additionally clipped at +-700 so that a pathological
        input yields a finite (if large) number rather than ``inf``, keeping
        the failure visible in ``converged`` instead of silently NaN-ing.

        Returns the updated phi and the final L2 residual.
        """
        cfg = self.config
        N = self.grid.N
        h = self.grid.h
        V = self.grid.cell_volume

        # Tridiagonal Laplacian on non-uniform grid (interior only).
        a = -1.0 / h[:-1]                       # (N-2,)
        c = -1.0 / h[1:]                        # (N-2,)
        b = (1.0 / h[:-1] + 1.0 / h[1:])        # (N-2,)

        # Boltzmann freeze for Newton
        n0 = n[1:-1].copy()
        p0 = p[1:-1].copy()
        phi0 = phi[1:-1].copy()

        def _carriers(dl: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
            dl = np.clip(dl, -_EXP_CLIP, _EXP_CLIP)
            return n0 * np.exp(dl), p0 * np.exp(-dl)

        def _residual(ph: np.ndarray):
            n_loc, p_loc = _carriers(ph[1:-1] - phi0)
            L_phi = a * ph[:-2] + b * ph[1:-1] + c * ph[2:]
            r = L_phi - V[1:-1] * (p_loc - n_loc + C_s[1:-1])
            return r, n_loc, p_loc

        r, n_loc, p_loc = _residual(phi)
        res = float(np.linalg.norm(r))
        for _it in range(cfg.max_inner):
            if not np.isfinite(res) or res < cfg.tol_poisson:
                break

            # Jacobian diagonal: d/dphi of -V*(p-n+C) is +V*(p+n).
            b_eff = b + V[1:-1] * (p_loc + n_loc)
            A = diags([a[1:], b_eff, c[:-1]], offsets=[-1, 0, 1], format="csr",
                      shape=(N - 2, N - 2))
            with np.errstate(all="ignore"):
                delta = spsolve(A, -r)
            if not np.all(np.isfinite(delta)):
                break

            # Cap the potential update at max_dphi thermal voltages.
            step_max = float(np.max(np.abs(delta))) if delta.size else 0.0
            if step_max > cfg.max_dphi > 0.0:
                delta = delta * (cfg.max_dphi / step_max)

            # Backtrack until the residual actually decreases.
            accepted = False
            alpha = 1.0
            for _ in range(30):
                trial = phi.copy()
                trial[1:-1] = phi[1:-1] + cfg.damping * alpha * delta
                r_t, n_t, p_t = _residual(trial)
                res_t = float(np.linalg.norm(r_t))
                if np.isfinite(res_t) and res_t < res:
                    phi, r, n_loc, p_loc, res = trial, r_t, n_t, p_t, res_t
                    accepted = True
                    break
                alpha *= 0.5
            if not accepted:
                break

        # Keep n, p consistent with the phi we are returning.
        n[1:-1], p[1:-1] = _carriers(phi[1:-1] - phi0)
        return phi, res

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
        n_new = (solve_equilibrated(A_n, b_n) if self.config.equilibrate
                 else spsolve(A_n, b_n))

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
        p_new = (solve_equilibrated(A_p, b_p) if self.config.equilibrate
                 else spsolve(A_p, b_p))

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
        _allow_continuation: bool = True,
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
        _allow_continuation : internal. Set False to suppress the automatic
            bias-ramp retry (used by the retry itself to avoid recursion).

        Returns
        -------
        DeviceState
            Converged state in SI units. Always check ``.converged``: the
            decoupled Gummel iteration is not unconditionally convergent (see
            the automatic-continuation note below).

        Automatic bias continuation
        ---------------------------
        Gummel's decoupled scheme can fail at high injection. Measured on the
        LDD profile (-1e22 / 5e21 / 5e23 m^-3) at 0.9 V from a cold start:
        max|dphi| oscillates between 2 and 87 V_T and never settles, and the
        reported current is 7e10 A/m^2 on a 201-point grid, 1.8e11 on 301 and
        **-6.5e12** on 601 -- grid-dependent nonsense.

        Ramping the bias from 0 in small steps, each warm-started from the
        last, converges at every step and gives 3.598e8 A/m^2, identical to
        four digits across all three grids. So the failure is in the
        *iteration path*, not the discretisation, and continuation is the
        standard cure.

        We therefore retry any non-converged cold solve as a bias ramp, and
        keep the retry only if it actually converges. This mirrors what
        ``MOSCap2DSolver`` does in 2D.
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
        # Best-iterate tracking. Once the carrier update reaches the
        # round-off floor, further Gummel sweeps do not improve the state --
        # they random-walk and actively *degrade* the terminal current
        # (measured: I_eq drifts from -7.2e-7 to -2.2e-6 A/m^2 between 3 and
        # 800 sweeps). We therefore keep the best iterate seen and stop once
        # progress stalls, instead of grinding to max_outer.
        best = (np.inf, None, None, None)
        best_extra = (float("inf"), float("inf"), float("inf"))
        stalled_at_roundoff = False
        delta_carrier = float("inf")
        stall = 0
        outer = -1
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

            # Convergence: the potential alone is NOT a sufficient test. phi
            # settles within 2-3 sweeps because it is insensitive to the
            # minority carriers, so a max|dphi| test reports success while
            # the carrier densities are still ~1% from self-consistent and
            # the continuity residual is 100% of the current scale (BUG-03).
            # Require the relative carrier update to converge as well.
            delta = np.max(np.abs(phi - phi_prev))
            dn = np.max(np.abs(n - n_prev) / np.maximum(np.abs(n), 1e-300))
            dp = np.max(np.abs(p - p_prev) / np.maximum(np.abs(p), 1e-300))
            delta_carrier = float(max(dn, dp))
            # Absolute carrier update measured against the round-off floor of
            # the linear solve, max|c| * eps (BUG-13). A relative test alone
            # is unsatisfiable for entries many decades below max|c|.
            _eps = np.finfo(np.float64).eps
            roundoff = float(max(
                np.max(np.abs(n - n_prev)) / max(_eps * np.max(np.abs(n)), 1e-300),
                np.max(np.abs(p - p_prev)) / max(_eps * np.max(np.abs(p)), 1e-300),
            ))
            residuals.append(delta)
            if cfg.verbose:
                print(f"  Gummel {outer+1:3d}: max|dphi| = {delta:.3e}  "
                      f"max|dc|/c = {delta_carrier:.3e}")
            score = max(delta, delta_carrier)
            if score < best[0]:
                best = (score, phi.copy(), n.copy(), p.copy())
                # (delta, delta_carrier, roundoff) *of this same iterate*.
                best_extra = (delta, delta_carrier, roundoff)
                stall = 0
            else:
                stall += 1
            # The potential test is never relaxed. The carrier test is met
            # either strictly, or by reaching the linear-solve round-off floor
            # -- which is a *converged* state, not a failure (BUG-13).
            if delta < cfg.tol_outer:
                if delta_carrier < cfg.tol_carrier:
                    converged = True
                    break
                if roundoff <= cfg.carrier_roundoff_factor:
                    converged = True
                    stalled_at_roundoff = True
                    break
            if stall >= cfg.stall_patience:
                # Stagnated at the numerical floor; keep the best iterate.
                break
        if not converged and best[1] is not None:
            phi, n, p = best[1], best[2], best[3]
            best_delta, delta_carrier, best_roundoff = best_extra
            # The loop stalled before any sweep satisfied the test, but the
            # *best* iterate may itself sit at the round-off floor with a
            # fully converged potential. Judge that iterate on its own
            # metrics -- never on a mixture of metrics from different sweeps.
            if best_delta < cfg.tol_outer and best_roundoff <= cfg.carrier_roundoff_factor:
                converged = True
                stalled_at_roundoff = True

        # Compute SI-unit fluxes for return
        Jn_s = self._compute_face_current(phi, n, self.mu_n_s, "n")
        Jp_s = self._compute_face_current(phi, p, self.mu_p_s, "p")

        state = DeviceState(
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
            stalled_at_roundoff=stalled_at_roundoff,
            final_carrier_update=float(delta_carrier),
        )

        if (state.converged or not _allow_continuation
                or not cfg.auto_continuation
                or initial_state is not None
                or abs(bias) <= cfg.continuation_step_V):
            return state

        # Retry as a bias ramp, each step warm-started from the previous one.
        n_steps = max(2, int(np.ceil(abs(bias) / cfg.continuation_step_V)))
        prev: Optional[DeviceState] = None
        ramped: Optional[DeviceState] = None
        for k in range(1, n_steps + 1):
            ramped = self.solve(doping_si, bias * k / n_steps,
                                initial_state=prev, _allow_continuation=False)
            if not ramped.converged:
                break
            prev = ramped
        if ramped is not None and ramped.converged:
            ramped.iterations += state.iterations
            return ramped
        return state

    def _compute_face_current(self, phi: np.ndarray, c: np.ndarray,
                              mu_s: float, carrier: str) -> np.ndarray:
        """
        Cell-face currents from the converged solution, in scaled units.

            J_n^{i+1/2} = (mu_n/h) [B(+Delta) n_{i+1} - B(-Delta) n_i]
            J_p^{i+1/2} = (mu_p/h) [B(+Delta) p_i     - B(-Delta) p_{i+1}]

        Evaluated in *quasi-Fermi* form to avoid catastrophic cancellation
        -----------------------------------------------------------------
        Written directly, each bracket is a difference of two large,
        nearly-equal numbers: at equilibrium the two terms cancel exactly,
        and near equilibrium they cancel to within the true (exponentially
        small) current. With scaled carrier densities reaching 1e6 and
        1/h ~ 1e4, each term is ~1e10, so double precision leaves an
        absolute error ~1e10 * 2.2e-16 ~ 2e-6 in scaled units -- a terminal
        current noise floor of ~3e-7 A/m^2 that no amount of extra Gummel
        iteration can remove (BUG-04, docs/AUDIT_MASTER.md).

        Using B(+D)/B(-D) = exp(-D) the bracket factors exactly as

            B(+D) n_{i+1} - B(-D) n_i = B(-D) n_i * expm1(u_n),
                u_n = log(n_{i+1}/n_i) - D  =  phi_n,i - phi_n,i+1
            B(+D) p_i - B(-D) p_{i+1} = -B(+D) p_i * expm1(u_p),
                u_p = log(p_{i+1}/p_i) + D  =  phi_p,i - phi_p,i+1

        i.e. the bracket is proportional to ``expm1`` of the *quasi-Fermi
        potential drop across the face*, which is identically zero in
        equilibrium. ``expm1`` is accurate to full relative precision for
        small arguments, so the cancellation disappears: the computed
        equilibrium current becomes ~1e-20 A/m^2 instead of ~1e-6, extending
        the oracle's trustworthy dynamic range by ~13 decades.

        This is an exact algebraic rewrite, not an approximation. For large
        |u| (where there is no cancellation to worry about and ``expm1``
        would overflow) we fall back to the direct difference.
        """
        h = self.grid.h
        delta = np.diff(phi)
        Bp = bernoulli(delta)
        Bm = bernoulli(-delta)
        if carrier not in ("n", "p"):
            raise ValueError(carrier)

        cl, cr = c[:-1], c[1:]
        # log ratio, guarded against zero/negative densities
        tiny = np.finfo(np.float64).tiny
        log_ratio = (np.log(np.maximum(cr, tiny))
                     - np.log(np.maximum(cl, tiny)))
        if carrier == "n":
            u = log_ratio - delta
            stable = Bm * cl * np.expm1(np.clip(u, -_U_MAX, _U_MAX))
            direct = Bp * cr - Bm * cl
        else:
            u = log_ratio + delta
            stable = -Bp * cl * np.expm1(np.clip(u, -_U_MAX, _U_MAX))
            direct = Bp * cl - Bm * cr
        bracket = np.where(np.abs(u) < _U_MAX, stable, direct)
        return (mu_s / h) * bracket


__all__ = [
    "DeviceState",
    "Grid1D",
    "SGConfig",
    "ScharfetterGummel1D",
    "bernoulli",
]
