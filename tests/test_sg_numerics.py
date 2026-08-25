"""
Numerical-correctness regression tests for the Scharfetter-Gummel oracle.

Every test here corresponds to a defect found in the BUG-0x audit
(``docs/AUDIT_MASTER.md``). The pre-existing suite passed with all of these
present, which is why the tests are written as *invariants* -- properties
that must hold for any correct implementation -- rather than as golden
values captured from the current code.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
    bernoulli,
    solve_equilibrated,
)

DOMAIN_L = 1e-6


def _setup(N=201, cfg=None):
    s = Scaling.for_material(SILICON, T=300.0)
    L_s = s.x_to_scaled(torch.tensor(DOMAIN_L)).item()
    grid = Grid1D.uniform(L_s, N)
    return s, grid, ScharfetterGummel1D(grid, s, SILICON, cfg or SGConfig())


def _pn(scaling, grid, N_A=1e22, N_D=1e22):
    x = scaling.x_to_si(np.asarray(grid.x))
    return np.where(x < x.max() / 2, -N_A, N_D)


# ===========================================================================
# BUG-01 -- Bernoulli overflowed to inf/NaN for x <= -709
# ===========================================================================

class TestBernoulliExtremes:
    """B(x) = x/(exp(x)-1) must be finite and accurate for *every* input."""

    def test_finite_over_full_double_range(self):
        x = np.array([-1e300, -1e6, -2000.0, -800.0, -710.0, -709.0, -700.0,
                      -1.0, 0.0, 1.0, 700.0, 709.0, 710.0, 1e6, 1e300])
        b = bernoulli(x)
        assert np.all(np.isfinite(b)), f"non-finite Bernoulli values: {b}"

    @pytest.mark.parametrize("x", [-709.0, -710.0, -800.0, -2000.0, -1e6])
    def test_large_negative_asymptote(self, x):
        """B(x) -> -x as x -> -inf, to full relative precision."""
        got = float(bernoulli(x))
        assert got == pytest.approx(-x, rel=1e-12)

    def test_exact_reflection_identity(self):
        """B(x) - B(-x) = -x holds exactly for the true function."""
        x = np.array([1e-6, 0.5, 5.0, 50.0, 500.0, 800.0, 5000.0])
        err = np.abs(bernoulli(x) - bernoulli(-x) + x)
        assert np.max(err / np.maximum(np.abs(x), 1.0)) < 1e-13

    def test_positive_decays_to_zero_without_overflow(self):
        assert float(bernoulli(1e4)) == 0.0
        assert float(bernoulli(100.0)) == pytest.approx(100.0 / math.expm1(100.0),
                                                        rel=1e-12)

    def test_zero_dim_input_preserved(self):
        assert float(bernoulli(0.0)) == pytest.approx(1.0, abs=1e-15)


# ===========================================================================
# BUG-02 -- junction_refined coarsened the junction instead of refining it
# ===========================================================================

class TestJunctionRefinedGrid:

    def test_spacing_is_finest_at_the_junction(self):
        L, N, xj = 100.0, 81, 50.0
        g = Grid1D.junction_refined(L, N, xj, refine_width=5.0, refine_factor=6.0)
        h = g.h
        x_mid = 0.5 * (g.x[1:] + g.x[:-1])
        # the smallest cell must sit at the junction, not at the contacts
        assert abs(x_mid[np.argmin(h)] - xj) < 0.05 * L
        assert h.min() < h[0], "grid is coarser at the junction than at the contact"

    def test_refinement_ratio_matches_refine_factor(self):
        g = Grid1D.junction_refined(100.0, 201, 50.0, refine_width=5.0,
                                    refine_factor=6.0)
        h = g.h
        assert h.max() / h.min() == pytest.approx(6.0, rel=0.05)

    def test_refine_width_is_actually_used(self):
        a = Grid1D.junction_refined(100.0, 81, 50.0, refine_width=1.0)
        b = Grid1D.junction_refined(100.0, 81, 50.0, refine_width=25.0)
        assert not np.allclose(a.x, b.x), "refine_width is being ignored"

    def test_off_centre_junction_is_tracked(self):
        g = Grid1D.junction_refined(100.0, 161, 20.0, refine_width=3.0,
                                    refine_factor=6.0)
        x_mid = 0.5 * (g.x[1:] + g.x[:-1])
        assert abs(x_mid[np.argmin(g.h)] - 20.0) < 2.0

    def test_grid_is_valid(self):
        g = Grid1D.junction_refined(100.0, 64, 30.0, refine_width=4.0)
        assert g.N == 64
        assert np.all(np.diff(g.x) > 0), "grid must be strictly increasing"
        assert g.x[0] == 0.0 and g.x[-1] == pytest.approx(100.0)

    @pytest.mark.parametrize("kw", [
        dict(N=1), dict(L_scaled=-1.0), dict(refine_width=0.0),
        dict(refine_factor=0.5),
    ])
    def test_rejects_invalid_arguments(self, kw):
        args = dict(L_scaled=100.0, N=32, x_junction=50.0, refine_width=5.0)
        args.update(kw)
        with pytest.raises(ValueError):
            Grid1D.junction_refined(**args)


# ===========================================================================
# BUG-03 -- Gummel reported convergence on max|dphi| while carriers were 1% off
# ===========================================================================

class TestGummelConvergenceIsHonest:

    def test_converged_state_satisfies_mass_action_tightly(self):
        """At equilibrium n*p = n_i^2 exactly; the old code was 1.3e-2 off."""
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.0)
        assert st.converged
        ratio = (st.n / s.n_star) * (st.p / s.n_star)
        assert np.max(np.abs(ratio - 1.0)) < 1e-4

    def test_equilibrium_quasi_fermi_levels_are_flat(self):
        """Both quasi-Fermi potentials are constant at zero bias."""
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.0)
        phi = st.phi / s.V_T
        qfn = np.log(st.n / s.n_star) - phi
        qfp = -np.log(st.p / s.n_star) - phi
        assert np.ptp(qfn) < 1e-6
        assert np.ptp(qfp) < 1e-6

    def test_unconverged_solve_reports_converged_false(self):
        """A budget too small to converge must not be reported as success."""
        s, grid, sg = _setup(cfg=SGConfig(max_outer=1))
        st = sg.solve(_pn(s, grid), bias=0.0)
        assert not st.converged

    def test_equilibration_beats_plain_spsolve(self):
        """Two-sided scaling is what makes the carrier solve accurate."""
        s, grid, _ = _setup()
        doping = _pn(s, grid)
        err = {}
        for eq in (False, True):
            sg = ScharfetterGummel1D(grid, s, SILICON,
                                     SGConfig(equilibrate=eq, max_outer=60))
            st = sg.solve(doping, bias=0.0)
            r = (st.n / s.n_star) * (st.p / s.n_star)
            err[eq] = float(np.max(np.abs(r - 1.0)))
        assert err[True] < err[False] / 100.0, (
            f"equilibration gained too little: {err}")

    def test_solve_equilibrated_matches_dense_solution(self):
        rng = np.random.default_rng(0)
        from scipy.sparse import csr_matrix
        A = np.diag(rng.uniform(2, 3, 40)) + 0.1 * rng.standard_normal((40, 40))
        # impose a pathological row scaling like the continuity matrix has
        A = A * np.logspace(0, 8, 40)[:, None]
        b = rng.standard_normal(40)
        x = solve_equilibrated(csr_matrix(A), b)
        assert np.allclose(A @ x, b, rtol=1e-8, atol=1e-10)

    def test_does_not_degrade_when_over_iterated(self):
        """Extra sweeps past the noise floor must not make things worse."""
        s, grid, _ = _setup()
        doping = _pn(s, grid)
        a = ScharfetterGummel1D(grid, s, SILICON,
                                SGConfig()).solve(doping, 0.0)
        b = ScharfetterGummel1D(
            grid, s, SILICON,
            SGConfig(tol_carrier=1e-15, max_outer=500)).solve(doping, 0.0)
        # stagnation detection must stop long before max_outer
        assert b.iterations < 100
        assert abs(b.terminal_current) < 20 * abs(a.current_noise_floor)


# ===========================================================================
# BUG-04 -- terminal current lost to cancellation in the SG flux difference
# ===========================================================================

class TestFluxCancellation:

    def test_exact_equilibrium_state_gives_machine_zero_current(self):
        """With n = exp(phi), p = exp(-phi) the SG flux vanishes identically.

        The direct difference B(+D)n_{i+1} - B(-D)n_i loses ~11 digits here;
        the quasi-Fermi expm1 form does not.
        """
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.0)
        phi = st.phi / s.V_T
        n_exact = np.exp(phi)
        Jn = sg._compute_face_current(phi, n_exact, sg.mu_n_s, "n")
        # scaled units; the old direct form gave ~4e-6 here
        assert np.max(np.abs(Jn)) < 1e-10

    def test_agrees_with_direct_form_away_from_equilibrium(self):
        """The rewrite is an exact identity, not an approximation."""
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.6)
        phi = st.phi / s.V_T
        n = st.n / s.n_star
        Jn = sg._compute_face_current(phi, n, sg.mu_n_s, "n")
        d = np.diff(phi)
        direct = (sg.mu_n_s / grid.h) * (bernoulli(d) * n[1:]
                                         - bernoulli(-d) * n[:-1])
        rel = np.abs(Jn - direct) / np.maximum(np.abs(direct), 1e-300)
        assert np.max(rel) < 1e-8

    def test_hole_flux_also_agrees(self):
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.6)
        phi = st.phi / s.V_T
        p = st.p / s.n_star
        Jp = sg._compute_face_current(phi, p, sg.mu_p_s, "p")
        d = np.diff(phi)
        direct = (sg.mu_p_s / grid.h) * (bernoulli(d) * p[:-1]
                                         - bernoulli(-d) * p[1:])
        rel = np.abs(Jp - direct) / np.maximum(np.abs(direct), 1e-300)
        assert np.max(rel) < 1e-8


# ===========================================================================
# Self-reported noise floor -- the oracle must know where it stops being one
# ===========================================================================

class TestNoiseFloorDiagnostics:

    def test_total_current_is_conserved_where_trustworthy(self):
        """div(Jn+Jp)=0 exactly, so J_total is constant across the device."""
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        for V in (0.3, 0.5, 0.6):
            st = sg.solve(doping, V)
            J = st.Jn + st.Jp
            assert np.ptp(J) / abs(np.mean(J)) < 1e-4, f"J not conserved at {V} V"

    def test_equilibrium_is_flagged_untrustworthy(self):
        """The true current is exactly 0 at V=0; any nonzero value is noise."""
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.0)
        assert not st.current_is_trustworthy()

    def test_forward_bias_is_flagged_trustworthy(self):
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        prev = None
        for V in (0.1, 0.2, 0.4, 0.6):
            st = sg.solve(doping, V, initial_state=prev)
            prev = st
            assert st.current_is_trustworthy(), f"V={V} flagged untrustworthy"

    def test_noise_floor_is_positive_and_small(self):
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.5)
        assert st.current_noise_floor > 0.0
        assert st.current_noise_floor < 1e-4 * abs(st.terminal_current)


# ===========================================================================
# Sign / unit conventions -- the module docstring claimed the opposite sign
# ===========================================================================

class TestSignConventions:

    def test_drift_diffusion_continuum_limit(self):
        """The SG face flux must reduce to J_n = mu_n (dn/dx - n dphi/dx).

        This pins the sign convention E = -grad(phi), which is the one the
        Poisson equation -phi'' = p - n + C already assumes. The module
        docstring previously stated J_n = mu_n (n dphi/dx + dn/dx), the
        opposite convention, contradicting its own Poisson equation.
        """
        s, grid, sg = _setup(N=3)
        # smooth, mild fields so the continuum limit is accurate
        h = 1e-4
        phi = np.array([0.0, h * 0.3, 2 * h * 0.3])       # dphi/dx = 0.3
        n = np.array([1.0, 1.0 + h * 0.7, 1.0 + 2 * h * 0.7])  # dn/dx = 0.7
        sg.grid = Grid1D(np.array([0.0, h, 2 * h]))
        J = sg._compute_face_current(phi, n, 1.0, "n")
        expected = 0.7 - 1.0 * 0.3         # dn/dx - n dphi/dx
        assert float(J[0]) == pytest.approx(expected, rel=1e-3)

    def test_positive_bias_is_forward_for_p_left_n_right(self):
        """step_profile puts P on the left; bias>0 must raise the current."""
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        fwd = sg.solve(doping, +0.4)
        rev = sg.solve(doping, -0.4)
        assert fwd.terminal_current > 0
        assert abs(fwd.terminal_current) > 1e3 * abs(rev.terminal_current)


# ===========================================================================
# Analytical validation of the oracle itself
# ===========================================================================

class TestAnalyticalValidation:

    def test_built_in_potential_matches_analytic(self):
        s, grid, sg = _setup()
        for N_A, N_D in [(1e21, 1e21), (1e22, 5e22), (5e21, 1e23)]:
            st = sg.solve(_pn(s, grid, N_A, N_D), bias=0.0)
            expected = s.V_T * math.log(N_A * N_D / SILICON.n_i ** 2)
            got = float(st.phi[-1] - st.phi[0])
            assert got == pytest.approx(expected, rel=1e-4)

    def test_ideality_factor_near_unity(self):
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        V = np.linspace(0.25, 0.5, 8)
        prev, I = None, []
        for v in V:
            st = sg.solve(doping, float(v), initial_state=prev)
            prev = st
            assert st.current_is_trustworthy()
            I.append(st.terminal_current)
        slope = np.polyfit(V, np.log10(np.abs(I)), 1)[0]
        n_ideal = 1.0 / (slope * s.V_T * math.log(10))
        assert 0.95 < n_ideal < 1.15, f"ideality factor {n_ideal}"

    def test_current_is_monotonic_in_forward_bias(self):
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        prev, I = None, []
        for v in np.linspace(0.1, 0.6, 11):
            st = sg.solve(doping, float(v), initial_state=prev)
            prev = st
            I.append(st.terminal_current)
        assert np.all(np.diff(I) > 0), "I(V) is not monotonically increasing"

    def test_reverse_bias_saturates(self):
        """Reverse current is nearly bias-independent (saturation)."""
        s, grid, sg = _setup()
        doping = _pn(s, grid)
        I = [sg.solve(doping, v).terminal_current for v in (-0.3, -0.5, -0.7)]
        I = np.abs(np.asarray(I))
        assert I.max() / I.min() < 5.0, f"reverse current not saturating: {I}"

    def test_symmetric_device_carries_no_net_current_at_zero_bias(self):
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), bias=0.0)
        assert abs(st.terminal_current) <= 10.0 * st.current_noise_floor


# ===========================================================================
# BUG-12 -- Gummel diverges at high injection without bias continuation
# ===========================================================================

class TestAutomaticContinuation:
    """A cold solve that Gummel cannot reach directly must be ramped to."""

    @staticmethod
    def _ldd(scaling):
        xa = np.linspace(0.0, DOMAIN_L, 16)
        return np.where(xa < 0.35e-6, -1e22,
                        np.where(xa < 0.6e-6, 5e21, 5e23))

    @pytest.mark.parametrize("N", [201, 301, 601])
    def test_high_injection_converges_from_cold_start(self, N):
        s, grid, sg = _setup(N=N)
        st = sg.solve(self._ldd(s), 0.9)
        assert st.converged, f"LDD @ 0.9 V, N={N} did not converge"
        assert np.isfinite(st.terminal_current)

    def test_result_is_grid_converged(self):
        """Without continuation this gave 7e10 / 1.8e11 / -6.5e12 A/m^2."""
        vals = []
        for N in (201, 301, 601):
            s, grid, sg = _setup(N=N)
            st = sg.solve(self._ldd(s), 0.9)
            assert st.converged
            vals.append(st.terminal_current)
        vals = np.asarray(vals)
        assert np.all(vals > 0), f"sign flip across grids: {vals}"
        spread = np.ptp(vals) / np.mean(vals)
        assert spread < 1e-3, f"not grid-converged: {vals} (spread {spread:.2e})"

    def test_continuation_can_be_disabled(self):
        s, grid, sg = _setup(N=301, cfg=SGConfig(auto_continuation=False))
        st = sg.solve(self._ldd(s), 0.9)
        assert not st.converged, (
            "this case is supposed to be hard without continuation; if it now "
            "converges directly, the continuation test above is vacuous")

    def test_easy_case_does_not_pay_for_continuation(self):
        """The retry must trigger only on failure, not on every solve."""
        s, grid, sg = _setup()
        st = sg.solve(_pn(s, grid), 0.5)
        assert st.converged
        assert st.iterations < 40


# ===========================================================================
# BUG-13 -- round-off stagnation misreported as divergence, which silently
#           aborted bias continuation and returned a garbage terminal current
# ===========================================================================

class TestRoundoffStagnationIsNotDivergence:
    """`tol_carrier` is a *relative* test on an array spanning ~16 decades.

    At 1e24 m^-3 the junction electron density sits ~9 decades below max|n|,
    so its update floors at the linear-solve round-off and can never reach
    1e-8 relative. The old code called that non-convergence; the continuation
    loop then `break`-ed on its first ramp step and returned the *cold-start*
    state, whose current was wrong by 3-5 decades (and wrong in sign under
    reverse bias).
    """

    HIGH_DOPING = (1e23, 1e24, 1e25)

    def test_equilibrium_converges_at_high_doping(self):
        """The exact case that failed: the potential is at 1e-12, V_bi exact."""
        for D in self.HIGH_DOPING:
            for N in (201, 401):
                s, grid, sg = _setup(N=N)
                st = sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=0.0)
                assert st.converged, f"D={D:.0e} N={N} equilibrium must converge"
                # V_bi must still be exact -- acceptance may not hide bad physics.
                V_bi = s.V_T * math.log(D * D / SILICON.n_i ** 2)
                assert abs((st.phi[-1] - st.phi[0]) - V_bi) / V_bi < 1e-9

    def test_continuation_is_not_aborted_by_stagnation(self):
        """I(0.9 V) at 1e24/1e25 was 2.4e11 / 6.7e12 A/m^2; truth is ~1e8 / 2e7.

        The invariant that catches it without a golden value: the terminal
        current must be grid-converged. The garbage values were not -- they
        moved by orders of magnitude between N=201 and N=401.
        """
        for D in (1e24, 1e25):
            Is = []
            for N in (201, 401, 801):
                s, grid, sg = _setup(N=N)
                st = sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=0.9)
                assert st.converged, f"D={D:.0e} N={N} @0.9V must converge"
                assert st.current_is_trustworthy()
                Is.append(st.terminal_current)
            Is = np.asarray(Is)
            spread = (Is.max() - Is.min()) / abs(Is.mean())
            assert spread < 0.02, f"D={D:.0e}: current not grid-converged ({spread:.2e})"
            assert Is.mean() > 0, "forward bias must give positive current"

    def test_non_convergence_is_only_ever_genuine_divergence(self):
        """The acceptance must not swallow real failures.

        The invariant, stated so it does not depend on which knife-edge cases
        happen to diverge on a given grid: whenever a cold solve reports
        ``converged=False`` it must be because the *potential* is still far
        from settled (max|dphi| of order 1 V_T or more), never because the
        carrier update merely sat at the round-off floor. That confusion was
        BUG-13 and it is what silently aborted bias continuation.
        """
        rejected = 0
        for D in (1e21, 1e23, 1e24, 1e25):
            for N in (201, 401):
                for V in (0.0, 0.6, 0.9, -2.0):
                    s, grid, sg = _setup(N=N, cfg=SGConfig(auto_continuation=False))
                    st = sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=V)
                    if st.converged:
                        continue
                    rejected += 1
                    assert st.residuals[-1] > 1e-2, (
                        f"D={D:.0e} N={N} V={V}: rejected a state whose potential "
                        f"was converged to {st.residuals[-1]:.2e} -- this is BUG-13"
                    )
        assert rejected > 0, "the divergence detector must still fire somewhere"

    def test_ldd_high_injection_still_needs_continuation(self):
        """BUG-12's case must still be rejected on a cold start.

        If the round-off acceptance had been too permissive this would start
        reporting success on the oscillating state, and continuation -- the
        thing that makes the answer grid-independent -- would stop running.
        """
        s, grid, sg = _setup(N=401, cfg=SGConfig(auto_continuation=False))
        x = s.x_to_si(np.asarray(grid.x)); L = x.max()
        ldd = np.where(x < 0.35 * L, -1e22, np.where(x < 0.6 * L, 5e21, 5e23))
        st = sg.solve(ldd, bias=0.9)
        assert not st.converged
        assert st.residuals[-1] > 1e-2

    def test_roundoff_threshold_is_not_tuned(self):
        """Stagnation and divergence are separated by ~11 orders of magnitude.

        Any factor in [1e5, 1e13] must give an identical verdict everywhere;
        a constant that had to be tuned would change the answer somewhere.
        """
        cases = [(D, N, V) for D in (1e21, 1e23, 1e25)
                 for N in (201, 401) for V in (0.0, 0.6, 0.9, -2.0)]
        baseline = None
        for factor in (1e5, 1e7, 1e9, 1e11, 1e13):
            verdicts = []
            for D, N, V in cases:
                s, grid, sg = _setup(N=N, cfg=SGConfig(carrier_roundoff_factor=factor))
                verdicts.append(sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=V).converged)
            if baseline is None:
                baseline = verdicts
            assert verdicts == baseline, f"verdict changed at factor={factor:.0e}"
        assert all(baseline), "every case in the validated envelope must converge"

    def test_acceptance_is_reported_not_hidden(self):
        """A solve accepted at the round-off floor says so."""
        s, grid, sg = _setup(N=401)
        st = sg.solve(_pn(s, grid, N_A=1e24, N_D=1e24), bias=0.0)
        assert st.converged and st.stalled_at_roundoff
        assert st.final_carrier_update > 0.0
        # A well-scaled solve is NOT flagged.
        s, grid, sg = _setup(N=201)
        st = sg.solve(_pn(s, grid, N_A=1e22, N_D=1e22), bias=0.0)
        assert st.converged and not st.stalled_at_roundoff

    def test_untrustworthy_points_are_flagged_not_silently_wrong(self):
        """High doping + low bias is below the solver's numerical floor.

        Those points are *not* grid-converged, and the oracle must say so via
        its own noise floor rather than reporting a confident wrong number.
        """
        Is, trust = [], []
        for N in (201, 401, 801):
            s, grid, sg = _setup(N=N)
            st = sg.solve(_pn(s, grid, N_A=1e25, N_D=1e25), bias=0.3)
            Is.append(st.terminal_current); trust.append(st.current_is_trustworthy())
        spread = (max(Is) - min(Is)) / abs(np.mean(Is))
        assert spread > 0.1, "this corner is expected to be grid-sensitive"
        assert not all(trust), "and the oracle must refuse to certify it"


# ===========================================================================
# API-05 -- current_is_trustworthy() ignored the convergence flag
# ===========================================================================

class TestTrustFlagRequiresConvergence:
    """A large current with a small face-to-face spread is not evidence.

    At +100 V the solver does not converge, yet the returned current
    (3.0e10 A/m^2) has an SNR far above the threshold. Before this fix a
    caller that checked only `current_is_trustworthy()` would have accepted
    it. Every in-tree caller wrote `converged and current_is_trustworthy()`,
    so folding the check in cannot loosen any existing result -- it only
    removes the footgun.
    """

    def test_non_converged_state_is_never_trustworthy(self):
        s, grid, sg = _setup(N=101)
        st = sg.solve(_pn(s, grid), bias=100.0)
        assert not st.converged
        assert abs(st.terminal_current) > 1e6, "expected a large bogus current"
        assert not st.current_is_trustworthy()

    def test_a_good_solve_is_still_trustworthy(self):
        """The fix must not reject anything that was previously accepted."""
        s, grid, sg = _setup(N=201)
        st = sg.solve(_pn(s, grid), bias=0.6)
        assert st.converged and st.current_is_trustworthy()

    def test_equilibrium_is_still_rejected_for_the_original_reason(self):
        """At V=0 the current is genuinely below the floor (ADR-0002)."""
        s, grid, sg = _setup(N=201)
        st = sg.solve(_pn(s, grid), bias=0.0)
        assert st.converged
        assert not st.current_is_trustworthy()


# ===========================================================================
# U4 -- GaAs constants were present and correct but no device was ever solved
# ===========================================================================

class TestGaAsDeviceSolves:
    """`CLAIM_EVIDENCE_MATRIX` U4 listed GaAs as exposed-but-never-exercised.

    These tests close that gap for the *solver*: a GaAs PN junction converges
    and satisfies the same analytic invariants silicon does. They do **not**
    validate GaAs device physics against measurement -- no experimental
    comparison exists, and none is claimed.
    """

    LEVELS = (1e21, 1e22, 1e23)

    def _setup_gaas(self, N=201):
        from bayespinn_inv.physics.constants import GAAS
        s = Scaling.for_material(GAAS, T=300.0)
        L_s = s.x_to_scaled(torch.tensor(DOMAIN_L)).item()
        grid = Grid1D.uniform(L_s, N)
        return s, grid, ScharfetterGummel1D(grid, s, GAAS, SGConfig()), GAAS

    def test_builtin_potential_matches_the_analytic_value(self):
        s, grid, sg, mat = self._setup_gaas()
        for D in self.LEVELS:
            st = sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=0.0)
            assert st.converged, f"GaAs {D:.0e} did not converge"
            V_bi = s.V_T * math.log(D * D / mat.n_i ** 2)
            got = st.phi[-1] - st.phi[0]
            assert abs(got - V_bi) / V_bi < 1e-9, f"{D:.0e}: {got} vs {V_bi}"

    def test_mass_action_holds_at_equilibrium(self):
        s, grid, sg, mat = self._setup_gaas()
        for D in self.LEVELS:
            st = sg.solve(_pn(s, grid, N_A=D, N_D=D), bias=0.0)
            ratio = st.n * st.p / mat.n_i ** 2
            assert np.max(np.abs(ratio - 1.0)) < 1e-3, f"{D:.0e}"

    def test_rectifies(self):
        s, grid, sg, _ = self._setup_gaas()
        C = _pn(s, grid, N_A=1e22, N_D=1e22)
        fwd = sg.solve(C, bias=0.9)
        rev = sg.solve(C, bias=-1.0)
        assert fwd.converged and fwd.current_is_trustworthy()
        assert fwd.terminal_current > 0
        assert abs(fwd.terminal_current) > 1e3 * abs(rev.terminal_current)

    def test_gaas_and_silicon_differ(self):
        """A material parameter that is never read would pass every test above."""
        from bayespinn_inv.physics.constants import GAAS
        s_si = Scaling.for_material(SILICON, T=300.0)
        s_ga = Scaling.for_material(GAAS, T=300.0)
        assert GAAS.n_i != SILICON.n_i
        # wider gap -> far smaller n_i -> substantially larger built-in potential
        vbi_si = s_si.V_T * math.log(1e22 * 1e22 / SILICON.n_i ** 2)
        vbi_ga = s_ga.V_T * math.log(1e22 * 1e22 / GAAS.n_i ** 2)
        assert vbi_ga > vbi_si + 0.3
