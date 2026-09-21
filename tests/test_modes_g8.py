"""``SPEC-g8-5``: the basin count, and the criterion that has to be fixed first.

The clause's own falsifier is *"a cluster count reported without its criterion,
or a criterion chosen after seeing the clusters"*. Both halves are mechanised:

* :class:`~bayespinn_inv.inverse.modes.ClusterCriterion` is frozen and hashes
  itself, and the run script writes that hash into the artefact **before** any
  distance is computed, exactly as ``GlobalStudyConfig.prior_hash`` does for the
  prior (``AH-14``);
* :func:`~bayespinn_inv.inverse.modes.count_basins` returns a *curve* over
  thresholds and the pre-registered count is a point on it, because a count at
  one threshold is a threshold count and ``SPEC-11`` applies to it exactly as it
  applies to a rank.

The known-answer controls below are the negative controls the clause needs: a
clusterer that always returns "many" would satisfy any count you asked of it.
"""

from __future__ import annotations

import numpy as np
import pytest

from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.inverse.modes import (
    ClusterCriterion,
    barrier_depth,
    count_basins,
    profile_distance_matrix,
    single_linkage_labels,
    witness_graph_components,
)


def _blob(centre, n, spread=0.01, seed=0, nodes=64):
    rng = np.random.default_rng(seed)
    return [10.0 ** (centre + rng.uniform(-spread, spread, size=nodes))
            for _ in range(n)]


# ===========================================================================
# The criterion is fixed before it is used
# ===========================================================================

class TestCriterion:

    def test_the_threshold_is_inherited_not_invented(self):
        """0.3 decades is the repository's own "far apart", used unchanged."""
        assert (ClusterCriterion().threshold_decades
                == GlobalStudyConfig().min_separation_decades)

    def test_the_hash_is_stable(self):
        assert ClusterCriterion().criterion_hash() == \
            ClusterCriterion().criterion_hash()

    @pytest.mark.parametrize("field,value", [
        ("threshold_decades", 0.4),
        ("linkage", "complete"),
        ("metric", "l2"),
        ("threshold_grid", (0.1, 0.2)),
    ])
    def test_the_hash_moves_when_the_criterion_moves(self, field, value):
        """A hash that does not change is a pre-registration that does not bind."""
        base = ClusterCriterion()
        assert ClusterCriterion(**{field: value}).criterion_hash() \
            != base.criterion_hash()

    def test_the_criterion_travels_with_the_result(self):
        out = count_basins(np.zeros((3, 3)), ClusterCriterion())
        assert out["criterion"]["criterion_hash"]
        assert out["criterion"]["threshold_decades"] == 0.3
        assert out["criterion"]["sign_disagreements_folded_in"] is False


# ===========================================================================
# The distance
# ===========================================================================

class TestDistance:

    def test_it_is_symmetric_with_a_zero_diagonal(self):
        D, S = profile_distance_matrix(_blob(22.0, 5))
        assert np.allclose(D, D.T, rtol=0, atol=0)
        assert np.all(np.diag(D) == 0.0)
        assert np.all(np.diag(S) == 0)

    def test_it_measures_decades(self):
        a = np.full(32, 1e21)
        b = np.full(32, 1e23)
        D, _ = profile_distance_matrix([a, b])
        assert D[0, 1] == pytest.approx(2.0, rel=1e-12)

    def test_sign_disagreements_are_counted_and_not_folded_in(self):
        """``PH-13`` in spirit: two incommensurable quantities, reported apart.

        Two profiles of identical magnitude and opposite sign are a p-n junction
        and its mirror image -- different devices -- but their log-magnitude
        distance is exactly zero. The count is what carries that, and if it were
        summed into the distance neither number would mean anything.
        """
        a = np.where(np.arange(32) < 16, -1e22, 1e22).astype(float)
        D, S = profile_distance_matrix([a, -a])
        assert D[0, 1] == 0.0
        assert S[0, 1] == 32

    def test_a_zero_node_is_refused_rather_than_patched(self):
        with pytest.raises(ValueError, match="undefined"):
            profile_distance_matrix([np.full(8, 1e22),
                                     np.array([0.0] + [1e22] * 7)])


# ===========================================================================
# The count, with known answers
# ===========================================================================

class TestKnownAnswers:

    def test_three_separated_blobs_give_three(self):
        profiles = (_blob(21.0, 4, seed=1) + _blob(22.0, 4, seed=2)
                    + _blob(23.0, 4, seed=3))
        D, _ = profile_distance_matrix(profiles)
        out = count_basins(D, ClusterCriterion())
        assert out["count_at_threshold"] == 3
        assert out["cluster_sizes_at_threshold"] == [4, 4, 4]

    def test_one_blob_gives_one(self):
        D, _ = profile_distance_matrix(_blob(22.0, 12, seed=4))
        assert count_basins(D, ClusterCriterion())["count_at_threshold"] == 1

    def test_twelve_separated_devices_give_twelve(self):
        """The other direction: the clusterer must be able to say "many"."""
        profiles = [np.full(32, 10.0 ** (21.0 + 0.5 * k)) for k in range(12)]
        D, _ = profile_distance_matrix(profiles)
        assert count_basins(D, ClusterCriterion())["count_at_threshold"] == 12

    def test_the_count_is_reported_as_a_curve(self):
        profiles = (_blob(21.0, 3, seed=5) + _blob(22.0, 3, seed=6)
                    + _blob(23.0, 3, seed=7))
        D, _ = profile_distance_matrix(profiles)
        out = count_basins(D, ClusterCriterion())
        curve = out["curve"]
        assert len(curve) == len(ClusterCriterion().threshold_grid)
        counts = [c["n_clusters"] for c in curve]
        assert counts == sorted(counts, reverse=True), (
            "single-linkage counts must be non-increasing in the threshold; if "
            "they are not, the clusterer is not doing what it says")
        assert counts[0] == 3 and counts[-1] == 1
        assert out["plateau_containing_threshold"]["lo_decades"] <= 0.3 <= \
            out["plateau_containing_threshold"]["hi_decades"]

    def test_single_linkage_chains_and_the_module_says_so(self):
        """The documented behaviour, pinned, because it bounds the headline.

        Three devices 0.2 decades apart in a line span 0.4 decades end to end and
        are still one cluster at 0.3. That is why the count is reported as a lower
        bound on the number of distinct devices rather than as an estimate.
        """
        profiles = [np.full(16, 10.0 ** (22.0 + 0.2 * k)) for k in range(3)]
        D, _ = profile_distance_matrix(profiles)
        assert D[0, 2] == pytest.approx(0.4, rel=1e-12)
        assert count_basins(D, ClusterCriterion())["count_at_threshold"] == 1
        assert "LOWER bound" in count_basins(D, ClusterCriterion())["reading"]

    def test_labels_are_contiguous_from_zero(self):
        D, _ = profile_distance_matrix(
            _blob(21.0, 2, seed=8) + _blob(23.0, 2, seed=9))
        labels = single_linkage_labels(D, 0.3)
        assert sorted(set(labels.tolist())) == [0, 1]


# ===========================================================================
# The witness relation as a graph
# ===========================================================================

class TestWitnessGraph:

    def test_isolated_pairs_stay_pairs(self):
        g = witness_graph_components(6, [(0, 1), (2, 3), (4, 5)])
        assert g["n_components"] == 3
        assert g["component_sizes"] == [2, 2, 2]
        assert g["n_components_larger_than_a_pair"] == 0

    def test_a_chain_of_indistinguishable_devices_is_one_component(self):
        g = witness_graph_components(4, [(0, 1), (1, 2), (2, 3)])
        assert g["n_components"] == 1
        assert g["n_components_larger_than_a_pair"] == 1

    def test_members_in_no_pair_are_still_counted(self):
        g = witness_graph_components(5, [(0, 1)])
        assert g["n_components"] == 4
        assert sorted(g["component_sizes"]) == [1, 1, 1, 2]


# ===========================================================================
# The check on the proxy
# ===========================================================================

class TestBarrierDepth:

    def test_a_flat_landscape_has_no_barrier(self):
        out = barrier_depth(lambda th: 0.0, np.zeros(3), np.ones(3), n_points=11)
        assert out["certified"] is True
        assert out["barrier_depth"] == 0.0

    def test_a_bimodal_path_reports_the_dip(self):
        """The g7 measurement, in miniature: two maxima and a barrier between."""
        def ll(th):
            t = float(th[0])
            return -100.0 * (0.25 - (t - 0.5) ** 2)

        out = barrier_depth(ll, np.array([0.0]), np.array([1.0]), n_points=11)
        assert out["endpoint_max"] == pytest.approx(0.0, abs=1e-12)
        assert out["interior_min"] == pytest.approx(-25.0)
        assert out["barrier_depth"] == pytest.approx(25.0)

    def test_uncertified_points_are_counted_not_skipped(self):
        """``PH-19``: a path with a hole does not get to report a depth."""
        def ll(th):
            return None if 0.4 < float(th[0]) < 0.6 else 0.0

        out = barrier_depth(ll, np.array([0.0]), np.array([1.0]), n_points=11)
        assert out["n_uncertified"] == 1
        assert out["certified"] is False
        assert out["loglik"].count(None) == 1
