"""Correctness of the optimal-experiment-design acquisition strategies.

These strategies decide which measurements get taken, so a silent bug here
would bias every downstream comparison in ``scripts/run_experiment_design.py``
in a way that looks like a scientific result. The tests are written against
analytically-known designs where the right answer can be derived by hand,
rather than against values captured from the current implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from bayespinn_inv.active_learning.design import (
    DESIGN_STRATEGIES,
    design_information_matrix,
    design_scores,
    design_summary,
    greedy_design,
    select_next_bias,
)

DETERMINISTIC = [s for s in DESIGN_STRATEGIES if s != "random"]


@pytest.fixture
def orthogonal_case():
    """A Jacobian whose rows are orthogonal with known, distinct gains.

    Row j excites parameter direction j alone, with gain 2**-j. The unique
    information-maximising design of size k is therefore rows 0..k-1, and the
    unique design that best improves the *worst* direction is the row with the
    smallest gain still unmeasured. Both answers are known without running
    the code.
    """
    P = 4
    J = np.zeros((P, P))
    for j in range(P):
        J[j, j] = 2.0 ** (-j)
    return J


class TestInformationMatrix:

    def test_empty_design_has_zero_information(self, orthogonal_case):
        M = design_information_matrix(orthogonal_case, [])
        assert M.shape == (4, 4)
        assert np.allclose(M, 0.0)

    def test_information_is_additive_over_measurements(self, orthogonal_case):
        J = orthogonal_case
        a = design_information_matrix(J, [0])
        b = design_information_matrix(J, [1])
        ab = design_information_matrix(J, [0, 1])
        assert np.allclose(ab, a + b)

    def test_information_is_symmetric_psd(self, orthogonal_case):
        M = design_information_matrix(orthogonal_case, [0, 2])
        assert np.allclose(M, M.T)
        assert np.all(np.linalg.eigvalsh(M) >= -1e-12)

    def test_scales_as_one_over_noise_squared(self, orthogonal_case):
        m1 = design_information_matrix(orthogonal_case, [0, 1], noise_symlog=1.0)
        m2 = design_information_matrix(orthogonal_case, [0, 1], noise_symlog=2.0)
        assert np.allclose(m2 * 4.0, m1)


class TestStrategiesPickTheKnownAnswer:

    def test_d_optimal_takes_the_highest_gain_row_first(self, orthogonal_case):
        """With orthogonal rows, log det is maximised by the largest gain."""
        assert select_next_bias(orthogonal_case, [], [0, 1, 2, 3], "d_optimal") == 0

    def test_null_space_prefers_an_unmeasured_direction(self, orthogonal_case):
        """After measuring row 0, rows 1-3 all add new directions; row 0 adds none.

        The invariant that matters is that a row already fully inside the
        measured subspace scores *lowest*.
        """
        J = orthogonal_case
        scores = design_scores(J, [0], [0, 1, 2, 3], "null_space")
        assert scores[0] == pytest.approx(0.0, abs=1e-12)
        assert np.all(scores[1:] > 0.0)

    def test_greedy_design_never_repeats_a_measurement(self, orthogonal_case):
        for strat in DETERMINISTIC:
            sel = greedy_design(orthogonal_case, [0, 1, 2, 3], 3, strat,
                                sigma=np.array([1.0, 2.0, 3.0, 4.0]))
            assert len(sel) == len(set(sel)) == 3

    def test_greedy_design_respects_the_candidate_pool(self, orthogonal_case):
        sel = greedy_design(orthogonal_case, [1, 3], 2, "d_optimal")
        assert set(sel) <= {1, 3}

    def test_budget_larger_than_pool_is_truncated_not_an_error(self, orthogonal_case):
        sel = greedy_design(orthogonal_case, [0, 1], 5, "d_optimal")
        assert len(sel) == 2

    def test_max_std_picks_the_largest_sigma(self, orthogonal_case):
        sigma = np.array([0.1, 0.9, 0.3, 0.2])
        assert select_next_bias(orthogonal_case, [], [0, 1, 2, 3], "max_std",
                                sigma=sigma) == 1

    def test_uncertainty_strategies_require_sigma(self, orthogonal_case):
        for strat in ("max_std", "std_x_nullspace"):
            with pytest.raises(ValueError, match="sigma"):
                design_scores(orthogonal_case, [], [0, 1], strat)

    def test_unknown_strategy_is_rejected(self, orthogonal_case):
        with pytest.raises(ValueError, match="unknown strategy"):
            design_scores(orthogonal_case, [], [0, 1], "not_a_strategy")

    def test_no_candidates_is_an_error_not_a_silent_none(self, orthogonal_case):
        with pytest.raises(ValueError, match="no candidate"):
            select_next_bias(orthogonal_case, [0], [], "d_optimal")


class TestStrategiesAreActuallyDifferent:
    """If two strategies always agreed, the comparison would be vacuous."""

    def test_information_and_uncertainty_can_disagree(self):
        # Row 1 carries the most information; row 0 has the largest sigma.
        J = np.array([[0.1, 0.0], [0.0, 5.0]])
        sigma = np.array([10.0, 0.1])
        assert select_next_bias(J, [], [0, 1], "max_std", sigma=sigma) == 0
        assert select_next_bias(J, [], [0, 1], "d_optimal") == 1

    def test_random_is_seed_reproducible(self):
        J = np.eye(6)
        cand = list(range(6))
        a = greedy_design(J, cand, 3, "random", rng=np.random.default_rng(1))
        b = greedy_design(J, cand, 3, "random", rng=np.random.default_rng(1))
        assert a == b

    def test_random_actually_explores_different_designs(self):
        """A "random" strategy that returned one fixed design would make the
        baseline a single arbitrary choice rather than an average."""
        J = np.eye(8)
        cand = list(range(8))
        designs = {tuple(greedy_design(J, cand, 3, "random",
                                       rng=np.random.default_rng(s)))
                   for s in range(20)}
        assert len(designs) > 1


class TestDesignSummary:

    def test_more_measurements_never_reduce_resolvable_rank(self):
        rng = np.random.default_rng(0)
        J = rng.normal(size=(10, 6))
        prev = -1
        for k in (1, 2, 4, 6, 8, 10):
            s = design_summary(J, list(range(k)), noise_rel=0.02)
            assert s["resolvable_rank"] >= prev or k == 1
            prev = s["resolvable_rank"]

    def test_rank_cannot_exceed_the_number_of_measurements(self):
        rng = np.random.default_rng(1)
        J = rng.normal(size=(12, 8))
        for k in (1, 2, 3):
            s = design_summary(J, list(range(k)), noise_rel=0.02)
            assert s["identifiable_rank"] <= k
            assert s["resolvable_rank"] <= k

    def test_reports_the_design_size(self):
        J = np.eye(5)
        assert design_summary(J, [0, 2, 4])["n_biases"] == 3
