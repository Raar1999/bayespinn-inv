"""``SPEC-11``'s rank-curve rule: a rank is a curve over cutoffs, not an integer.

Generation 7 measured, in four ``(chart, d)`` cells, where the operational cutoff
sits relative to the spectrum's largest multiplicative gap. At ``d = 4`` it sits
inside it (x7.39 in chart G, x17.46 in chart L). At ``d = 16`` it does not (x4.99
and x5.12, cutoff outside). So "3 of 4" is a boundary between two populations of
singular values and "4 of 16" is a threshold applied to a smooth decay -- two
different kinds of object, quoted for six generations in the same voice.

``rank_cutoff_record`` is the only way generation-8 machinery reports a rank, and
this module is its guard. The two controls are the two directions:

* a spectrum with a clean decade-wide gap at the cutoff **must** be flagged
  ``bare_integer_rank_justified``;
* a smoothly decaying spectrum **must not** be.

A flag that fired on both, or on neither, would be worth nothing, so both are
asserted rather than one.

The criterion is inherited, not chosen here
--------------------------------------------
"the operational cutoff falls strictly inside the largest multiplicative gap of
the resolvable spectrum" is generation 7's criterion, unchanged. That is what
keeps ``AH-14`` clean: it was fixed before the generation-8 cells existed, so it
cannot have been picked to suit them. This module pins the criterion so that
changing it later is a visible act.
"""

from __future__ import annotations

import numpy as np
import pytest

from bayespinn_inv.inverse.identifiability import (
    IdentifiabilityReport,
    rank_cutoff_record,
)

NOISE = 0.02
CUTOFF = float(np.log10(1.0 + NOISE))          # 8.600e-03 symlog


def _report(singular_values, jacobian_noise=1e-6, B=16):
    """A report with a chosen spectrum. Only the SVD-derived fields matter here."""
    s = np.asarray(singular_values, dtype=np.float64)
    P = s.size
    return IdentifiabilityReport(
        jacobian=np.zeros((B, P)),
        singular_values=s,
        directions=np.eye(P),
        bias_modes=np.zeros((B, min(B, P))),
        noise_symlog=CUTOFF,
        jacobian_noise=jacobian_noise,
    )


class TestTheRecordIsACurve:

    def test_it_reports_a_rank_at_every_defensible_cutoff(self):
        rec = rank_cutoff_record(_report([1.0, 0.3, 0.05, 2e-3, 1e-4]), NOISE)
        assert len(rec["rank_curve"]) == 8
        noises = [c["noise_rel"] for c in rec["rank_curve"]]
        assert noises == sorted(noises, reverse=True)
        ranks = [c["rank"] for c in rec["rank_curve"]]
        assert ranks == sorted(ranks), (
            "rank must be non-decreasing as the cutoff falls; if it is not, the "
            "curve is not a curve")

    def test_the_spectrum_comes_before_the_rank(self):
        """`PH-11`: the measured object is the spectrum, the rank is a reading."""
        rec = rank_cutoff_record(_report([1.0, 0.3, 0.05]), NOISE)
        keys = list(rec)
        assert keys.index("singular_values") < keys.index("rank_curve")
        assert rec["singular_values"] == [1.0, 0.3, 0.05]

    def test_it_carries_the_cutoff_with_the_rank(self):
        rec = rank_cutoff_record(_report([1.0, 0.3, 0.05, 1e-4]), NOISE)
        assert rec["operational_noise_rel"] == NOISE
        assert rec["operational_cutoff_symlog"] == pytest.approx(CUTOFF)
        assert str(rec["rank_at_operational_cutoff"]) in rec["how_to_quote"]
        assert "cutoff" in rec["how_to_quote"]

    def test_a_cutoff_below_the_spectral_floor_is_flagged(self):
        """Below the estimator's own floor a rank counts estimator noise."""
        rec = rank_cutoff_record(_report([1.0, 0.3, 0.05], jacobian_noise=1e-2),
                                 NOISE)
        assert any(c["cutoff_below_spectral_floor"] for c in rec["rank_curve"])


class TestTheGapCriterion:

    def test_a_clean_gap_at_the_cutoff_justifies_a_bare_integer(self):
        """Positive control. Three big values, then a decade-wide fall past the
        cutoff -- the ``d = 4`` shape, idealised."""
        rec = rank_cutoff_record(_report([1.9, 0.32, 0.061, 8.2e-4]), NOISE)
        assert rec["rank_at_operational_cutoff"] == 3
        assert rec["operational_cutoff_falls_in_largest_gap"] is True
        assert rec["bare_integer_rank_justified"] is True
        assert "population boundary" in rec["how_to_quote"]

    def test_a_smooth_decay_does_not(self):
        """Negative control. Geometric decay: every gap is the same, so the
        cutoff cannot be inside *the largest* one in any meaningful sense --
        the ``d = 16`` shape."""
        s = 1.0 * (0.55 ** np.arange(12))
        rec = rank_cutoff_record(_report(s), NOISE)
        assert rec["bare_integer_rank_justified"] is False
        assert "threshold count" in rec["how_to_quote"]
        assert "must never be quoted without its cutoff" in rec["how_to_quote"]

    def test_the_two_controls_disagree(self):
        """The check that makes the pair a control rather than two assertions."""
        gapped = rank_cutoff_record(_report([1.9, 0.32, 0.061, 8.2e-4]), NOISE)
        smooth = rank_cutoff_record(_report(0.55 ** np.arange(12)), NOISE)
        assert gapped["bare_integer_rank_justified"] != \
            smooth["bare_integer_rank_justified"]

    def test_the_gap_is_reported_even_when_the_cutoff_misses_it(self):
        rec = rank_cutoff_record(_report(0.55 ** np.arange(12)), NOISE)
        assert rec["largest_gap_ratio"] is not None
        assert rec["largest_gap_after_index"] is not None


class TestThePlateau:

    def test_a_plateau_pinned_by_the_estimator_floor_says_so(self):
        """A wide plateau is not evidence when ``resolvable_rank`` is the cap.

        With a coarse Jacobian estimate the rank saturates at the number of
        singular values the estimator can resolve, and then it stops moving with
        the cutoff for a reason that has nothing to do with the spectrum's
        structure. Reading that as "the rank is robust" is the trap; the flag is
        the exit.
        """
        rec = rank_cutoff_record(_report([1.0, 0.5, 0.25, 1e-9, 1e-10],
                                         jacobian_noise=3e-3), NOISE)
        p = rec["plateau_containing_operational_cutoff"]
        assert rec["rank_at_operational_cutoff"] == rec["resolvable_rank"]
        assert p["limited_by_resolvable_rank"] is True

    def test_a_plateau_not_pinned_by_the_floor_says_that_too(self):
        rec = rank_cutoff_record(_report([1.9, 0.32, 0.061, 8.2e-4],
                                         jacobian_noise=1e-9), NOISE)
        p = rec["plateau_containing_operational_cutoff"]
        assert rec["rank_at_operational_cutoff"] < rec["resolvable_rank"]
        assert p["limited_by_resolvable_rank"] is False

    def test_the_plateau_brackets_the_operational_cutoff(self):
        rec = rank_cutoff_record(_report([1.9, 0.32, 0.061, 8.2e-4]), NOISE)
        p = rec["plateau_containing_operational_cutoff"]
        assert p["noise_rel_lo"] <= NOISE <= p["noise_rel_hi"]


class TestItGeneralisesPastRanks:

    def test_a_basin_count_is_reported_the_same_way(self):
        """The rule is about threshold counts, not about ranks specifically."""
        from bayespinn_inv.inverse.modes import ClusterCriterion, count_basins
        D = np.array([[0.0, 0.1, 2.0],
                      [0.1, 0.0, 2.0],
                      [2.0, 2.0, 0.0]])
        out = count_basins(D, ClusterCriterion())
        assert "curve" in out and len(out["curve"]) > 1
        assert out["count_at_threshold"] == 2
        assert "plateau_containing_threshold" in out
