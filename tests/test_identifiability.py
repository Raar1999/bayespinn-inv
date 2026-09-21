"""
Tests for the identifiability analysis.

The scientific claim being protected is: *an I--V sweep determines only a
handful of the doping degrees of freedom, and the analysis knows which of its
own numbers it is entitled to trust.* Both halves are tested -- including the
failure mode that made the first version of this analysis wrong (differencing
oracle outputs that were below the solver's own noise floor produced a
plausible-looking spectrum that was entirely noise).
"""

from __future__ import annotations

import numpy as np
import pytest

from bayespinn_inv.inverse.charts import ChartL
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    equivalence_perturbation,
    sg_forward_jacobian,
    symlog,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)


@pytest.fixture(scope="module")
def oracle():
    sc = Scaling.for_material(SILICON, T=300.0)
    L_s = float(sc.x_to_scaled(np.float64(1e-6)))
    return ScharfetterGummel1D(Grid1D.uniform(L_s, 301), sc, SILICON, SGConfig())


@pytest.fixture(scope="module")
def chart(oracle):
    """CHART-01: 16 coordinates, a 301-node solver, and the chart said out loud.

    These numbers used to be produced by handing the solver a length-16 array
    and letting it resample. Same operator, same values -- named.
    """
    sc = Scaling.for_material(SILICON, T=300.0)
    return ChartL(16, sc.x_to_si(np.asarray(oracle.grid.x)))


@pytest.fixture(scope="module")
def chart8(oracle):
    """The same chart at d = 8, for the estimator-honesty tests."""
    sc = Scaling.for_material(SILICON, T=300.0)
    return ChartL(8, sc.x_to_si(np.asarray(oracle.grid.x)))


@pytest.fixture(scope="module")
def reference(oracle, chart):
    xa = np.linspace(0.0, 1e-6, 16)
    C = np.where(xa < 0.5e-6, -1e22, 1e22)
    biases = np.linspace(0.0, 0.9, 19)
    J, I_ref, kept, eta = sg_forward_jacobian(oracle, C, biases,
                                              rel_step=0.05, min_snr=1e8,
                                              chart=chart)
    rep = analyse_identifiability(J, noise_rel=0.02, jacobian_noise=eta)
    return C, biases, J, kept, eta, rep


# ===========================================================================
# The analysis must not trust numbers it cannot resolve
# ===========================================================================

class TestSelfHonesty:

    def test_exact_null_space_is_exposed(self, reference):
        """With P > B the map has a null space; the SVD must show it.

        Using full_matrices=False truncates V to B columns and hides exactly
        the directions no experiment can constrain.
        """
        _, _, J, _, _, rep = reference
        B, P = J.shape
        assert rep.directions.shape == (P, P)
        assert rep.singular_values.size == P
        n_zero = int(np.sum(rep.singular_values == 0.0))
        assert n_zero >= P - B

    def test_identifiable_rank_capped_by_resolvable_rank(self, reference):
        _, _, _, _, _, rep = reference
        assert rep.identifiable_rank <= rep.resolvable_rank

    def test_noisy_jacobian_yields_no_claimed_resolution(self, reference):
        """A Jacobian we admit is noise must not produce an identifiable rank."""
        _, _, J, _, _, _ = reference
        huge = analyse_identifiability(J, noise_rel=0.02, jacobian_noise=1e3)
        assert huge.resolvable_rank == 0
        assert huge.identifiable_rank == 0

    def test_refuses_to_difference_below_the_oracle_noise_floor(self, oracle,
                                                                chart8):
        """Requesting an impossible SNR must raise, not return noise."""
        xa = np.linspace(0.0, 1e-6, 8)
        C = np.where(xa < 0.5e-6, -1e22, 1e22)
        with pytest.raises(ValueError, match=r"noise floor|SNR"):
            sg_forward_jacobian(oracle, C, [0.0, 0.05], min_snr=1e12,
                                chart=chart8)

    def test_only_trustworthy_biases_are_kept(self, oracle, chart8):
        xa = np.linspace(0.0, 1e-6, 8)
        C = np.where(xa < 0.5e-6, -1e22, 1e22)
        biases = np.linspace(0.0, 0.6, 13)
        _, _, kept, _ = sg_forward_jacobian(oracle, C, biases, min_snr=1e6,
                                            chart=chart8)
        # V = 0 has zero true current; it can never clear the floor
        assert 0 not in kept
        assert len(kept) < len(biases)


# ===========================================================================
# The Jacobian must actually predict the forward map
# ===========================================================================

class TestLinearResponseValidation:

    @pytest.mark.parametrize("k", [0, 1, 2])
    def test_predicted_response_matches_independent_resolve(self, oracle,
                                                            reference,
                                                            chart, k):
        """||J v|| must match a fresh SG solve of the perturbed device."""
        C, biases, J, kept, _, rep = reference
        Bk = biases[kept]

        def iv(Cp):
            prev, o = None, []
            for V in Bk:
                st = oracle.solve(chart.on_grid_signed(Cp), float(V),
                                  initial_state=prev)
                prev = st
                o.append(st.terminal_current)
            return np.asarray(o)

        v = rep.directions[:, k]
        step = 0.01 * v / np.linalg.norm(v)
        predicted = float(np.linalg.norm(J @ step))
        Cp = np.sign(C) * np.abs(C) * 10.0 ** step
        actual = float(np.linalg.norm(symlog(iv(Cp)) - symlog(iv(C))))
        assert actual == pytest.approx(predicted, rel=0.10)

    def test_response_is_ordered_by_singular_value(self, reference):
        """Directions with larger gain must move the I--V more."""
        _, _, J, _, _, rep = reference
        resp = [float(np.linalg.norm(J @ rep.directions[:, k]))
                for k in range(4)]
        assert resp == sorted(resp, reverse=True)


# ===========================================================================
# The scientific conclusion
# ===========================================================================

class TestIllPosedness:

    def test_most_profile_degrees_of_freedom_are_unidentifiable(self, reference):
        """The headline result: I--V pins down only a handful of the 16 dof."""
        _, _, _, _, _, rep = reference
        assert rep.n_parameters == 16
        assert 2 <= rep.identifiable_rank <= 7, (
            f"identifiable rank {rep.identifiable_rank} outside the validated "
            "range; the ill-posedness claim needs re-measuring")

    def test_better_instrument_gives_diminishing_returns(self, reference):
        """Rank grows sub-linearly in log-noise -- an experimental-design result."""
        _, _, _, _, _, rep = reference
        curve = dict(rep.rank_vs_noise([0.10, 0.02, 1e-4]))
        assert curve[0.10] <= curve[0.02] <= curve[1e-4]
        # four orders of magnitude of instrument improvement must not recover
        # anything close to all 16 degrees of freedom
        assert curve[1e-4] < rep.n_parameters

    def test_equivalence_twin_is_physically_distinct_but_iv_indistinguishable(
            self, oracle, reference, chart):
        """The operational statement of ill-posedness, verified through SG."""
        C, biases, _, kept, _, rep = reference
        twin = equivalence_perturbation(rep, C, decades=0.1, mode="least")

        # physically distinct: at least 25% doping change somewhere
        decades = np.abs(np.log10(np.abs(twin) / np.abs(C)))
        assert np.max(decades) > 0.09
        # junction structure preserved (signs unchanged)
        assert np.array_equal(np.sign(twin), np.sign(C))

        def iv(Cp):
            prev, o = None, []
            for V in biases[kept]:
                st = oracle.solve(chart.on_grid_signed(Cp), float(V),
                                  initial_state=prev)
                prev = st
                o.append(st.terminal_current)
            return np.asarray(o)

        rel = np.max(np.abs(iv(twin) - iv(C)) / np.abs(iv(C)))
        assert rel < 0.02, (
            f"twin is distinguishable at 2% noise ({rel:.3%}); the "
            "equivalence-class construction no longer holds")


class TestReportMechanics:

    def test_detectable_amplitude_is_inverse_gain(self, reference):
        _, _, _, _, _, rep = reference
        k = 0
        assert rep.detectable_amplitude(k) == pytest.approx(
            rep.noise_symlog / rep.singular_values[k])

    def test_parameter_sensitivity_shape(self, reference):
        _, _, J, _, _, rep = reference
        assert rep.parameter_sensitivity().shape == (J.shape[1],)

    def test_summary_is_renderable(self, reference):
        _, _, _, _, _, rep = reference
        text = rep.summary()
        assert "identifiable rank" in text
        assert "spectral floor" in text

    def test_equivalence_perturbation_rejects_fully_identifiable_case(self):
        J = np.eye(4) * 10.0
        rep = analyse_identifiability(J, noise_rel=0.02)
        with pytest.raises(ValueError):
            equivalence_perturbation(rep, np.ones(4) * 1e22)
