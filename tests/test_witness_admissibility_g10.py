"""``WIT-01``: a witness count is published with its admissibility ratio.

The defect that forced the rule
-------------------------------
Generation 9 discovered, by refining all thirteen chart-J witness pairs on the
oracle, that one of them had junctions **0.425 nm** apart on a grid whose node
spacing is **3.333 nm**. ``ChartJ.reconstruct`` places the sign flip with
``x_si < x_j``, so those two junctions build the same profile bit for bit: the
number was a property of the grid, and it had been published as a property of a
device. Refinement is the right falsifier for that and the wrong filter -- it
costs three solves per bias per pair and it fires after the count is in print.

The rule, and what it turned out to mean
----------------------------------------
    ``WIT-01``. A pair whose separation along any coordinate falls below the
    grid resolution is not a witness and is excluded before counting, not
    filtered afterwards by refinement. State the admissibility ratio and apply
    it to every existing witness count.

Applied, it removes **nothing**: every witness pair in this repository qualifies
on a magnitude coordinate, and magnitude coordinates reach the grid exactly, so
the admissibility ratio is 1.000 in all three charts. That is the result, and it
is why the ratio has to be *stated* rather than assumed -- "the rule does not
bite here" and "the rule was never applied here" are different sentences and only
one of them is checkable.

What the rule does bite on is a *reported quantity*: the 0.425 nm junction
separation itself. So this module guards two things.

``TestTheAdmissibilityPredicate``
    the predicate, over the AST-free subject it actually has -- coordinates and
    charts. Both ``SW-20`` controls: a planted sub-node pair it must reject, and
    the headline 694 nm / 271 nm pair it must admit.

``TestEveryWitnessCountCarriesItsAdmissibilityRatio``
    the prose. A claim-surface document quoting a witness count points its reader
    at the admissibility ratio, exactly as ``tests/test_claim_surface_g9.py``
    makes a rank point at its curve. Document level rather than passage level,
    for the same reason: a table row reading ``| witness pairs found | 13 |`` is
    a legitimate way to write a number, and a guard that forbade it would be a
    guard about typography.

``SW-20``: the second subject is prose, so there is no AST; the rule's *purpose*
is honoured instead. Both controls are implemented for both halves, this module's
own source is out of scope, and the exclusion is asserted rather than trusted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
from test_claim_surface_g7 import _PROHIBITION, CLAIM_SURFACE_G7, _read, _units

from bayespinn_inv.inverse.charts import ChartG, ChartJ, ChartL
from bayespinn_inv.inverse.witness_admissibility import (
    AdmissibilityRule,
    admissibility,
    apply_to_witness_set,
)

REPO = Path(__file__).resolve().parents[1]

CLAIM_SURFACE_G10 = (*CLAIM_SURFACE_G7, "docs/G10_RESULT.md")

#: A witness *count*: "13 witness pairs", "37 of 719,400", "13 witness pair(s)".
#: Restricted to a small integer immediately governing the word, so that
#: "1,999,000 pairs examined" and "witness pair 0" are not read as counts.
_WITNESS_COUNT = re.compile(
    r"\b\d{1,3}\s+(?:\*\*)?witness(?:es)?\b|\bwitness\s+pairs?\s+found\b"
    r"|\b\d{1,3}\s+witness\s+pair", re.I)

#: What makes the ratio available to the reader.
#:
#: Deliberately does NOT match a bare "admissible". Three claim-surface
#: documents contain the phrase *"the best of the two admissible projections"*,
#: which has nothing to do with witness admissibility, and a pattern that
#: accepted it would have passed those three for the wrong reason. That was a
#: measured false negative, not a hypothetical one --
#: :meth:`test_an_unrelated_use_of_the_word_admissible_does_not_satisfy_it`
#: pins the exact phrase so the loophole cannot reopen.
_ADMISSIBILITY_CITATION = re.compile(
    r"WIT-01|admissibility\s+ratio|admissible\s+under\s+WIT-01"
    r"|outputs/g10/wit01\.json|witness_admissibility", re.I)


def _x_si(n: int = 301) -> np.ndarray:
    return np.linspace(0.0, 1e-6, n)


def count_offenders(text: str, document: str = "<text>"):
    """Passages asserting a witness count, for the vacuity check."""
    return [f"{document} {label}: {unit.strip()[:150]}"
            for label, unit in _units(text)
            if _WITNESS_COUNT.search(unit) and not _PROHIBITION.search(unit)]


def _quotes_a_witness_count(text: str) -> bool:
    return any(_WITNESS_COUNT.search(unit) and not _PROHIBITION.search(unit)
               for _, unit in _units(text))


# ---------------------------------------------------------------------------

class TestTheAdmissibilityPredicate:
    """The rule itself, on charts and coordinates."""

    def test_a_planted_sub_node_junction_pair_is_rejected(self):
        """`SW-20`'s positive control: the defect, planted.

        The pair has to be rejected *for the right reason*, which constrains how
        it is built. Two devices whose junction coordinates differ by less than
        ``min_separation_decades`` are rejected by the witness criterion before
        ``WIT-01`` is reached, so such a pair tests nothing. The construction
        that does test it uses the logistic's saturated tail: at ``s ~ 4`` the
        junction sits 0.1 nm from the contact and ``dx_j/ds`` has collapsed, so
        a **0.4 decade** move in the coordinate -- comfortably qualifying --
        shifts the junction by 0.06 nm and leaves it inside the same node
        interval.
        """
        J = ChartJ(16, _x_si())
        mags = np.full(15, 22.0)
        a = np.concatenate([[4.0], mags])
        b = np.concatenate([[4.4], mags])
        assert abs(b[0] - a[0]) >= AdmissibilityRule().min_separation_decades, (
            "the planted pair does not reach the separation criterion, so it "
            "would be rejected before WIT-01 was consulted and the control "
            "would prove nothing")
        assert J.junction_node_index(a[0]) == J.junction_node_index(b[0]), (
            "the planted pair was built to sit inside one node interval and "
            "does not; the control is not testing what it claims to")
        v = admissibility(J, a, b)
        assert not v["admissible"], (
            "WIT-01 admitted two devices whose only qualifying separation is a "
            "junction move the grid does not carry -- the same profile, bit "
            f"for bit. Verdict: {v['reason']}")
        assert "unresolved" in v["reason"], (
            "the pair was rejected, but not by WIT-01: "
            f"{v['reason']}")

    def test_the_headline_junction_pair_is_admitted(self):
        """`SW-20`'s negative control: the rule must not eat the result.

        Every junction claim in this repository rests on the chart-J pair whose
        junctions sit at 694 nm and 271 nm. A rule that rejected it would be a
        rule that deleted the finding it was enacted to protect.
        """
        cj = json.loads((REPO / "outputs/g8/chart_j.json").read_text(
            encoding="utf-8"))["native_witness"]
        kept = np.asarray(cj["kept_log10"], dtype=np.float64)
        J = ChartJ(16, _x_si())
        widest, sep = None, -1.0
        for (i, j) in cj["witness_pair_indices"]:
            dx = abs(J.junction_position(kept[i][0])
                     - J.junction_position(kept[j][0]))
            if dx > sep:
                widest, sep = (i, j), dx
        assert sep > 4e-7, "the widest junction pair is not the 423 nm one"
        v = admissibility(J, kept[widest[0]], kept[widest[1]])
        assert v["admissible"], v["reason"]

    def test_the_rule_is_vacuous_for_magnitude_only_charts_and_says_so(self):
        """Charts G and L have no sub-resolution pairs, by construction."""
        x = _x_si()
        for chart in (ChartG(4, x), ChartG(16, x), ChartL(16, x)):
            res = chart.coordinate_resolution(np.full(chart.d, 22.0))
            assert np.all(res == 0.0), (
                f"{chart.label()} reports a nonzero coordinate resolution; if "
                "that is real, WIT-01 is no longer vacuous for it and every "
                "count in that chart needs re-deriving")

    def test_a_pinned_junction_has_infinite_resolution(self):
        """`junction_scale = 0` pins the junction; no `s` moves it at all."""
        J = ChartJ(16, _x_si(), junction_scale=0.0)
        res = J.coordinate_resolution(np.concatenate([[0.0], np.full(15, 22.0)]))
        assert not np.isfinite(res[0]), (
            "a pinned junction must have infinite resolution: the coordinate "
            "cannot move the profile at all, which is the positive control "
            "generations 8 and 9 rest their junction numbers on")

    def test_a_shared_junction_does_not_reject_a_magnitude_witness(self):
        """The literal reading of the rule would; this implementation must not.

        Two chart-J devices with the *same* junction have a junction separation
        of exactly zero, which is below any positive resolution. Rejecting them
        would make WIT-01 delete most of the witness set it was enacted over.
        """
        J = ChartJ(16, _x_si())
        a = np.concatenate([[0.0], np.full(15, 22.0)])
        b = np.concatenate([[0.0], np.full(15, 21.0)])
        assert admissibility(J, a, b)["admissible"]

    def test_the_ratio_is_reported_for_every_committed_witness_set(self):
        """Every set that exists is scored, so the ratio is never absent."""
        rep = json.loads((REPO / "outputs/g8/reproduce.json").read_text(
            encoding="utf-8"))
        cj = json.loads((REPO / "outputs/g8/chart_j.json").read_text(
            encoding="utf-8"))["native_witness"]
        x = _x_si()
        for chart, res, n in ((ChartG(4, x), rep["chart_G_d4"], 13),
                              (ChartL(16, x), rep["chart_L_d16"], 37),
                              (ChartJ(16, x), cj, 13)):
            out = apply_to_witness_set(chart, res["kept_log10"],
                                       res["witness_pair_indices"])
            assert out["n_pairs_offered"] == n, (
                f"{chart.label()}: {out['n_pairs_offered']} pairs on disk, "
                f"{n} expected -- a published count moved")
            assert 0.0 <= out["admissibility_ratio"] <= 1.0

    def test_the_rule_hash_is_stable(self):
        """A rule that can be edited silently is not pre-registerable."""
        assert AdmissibilityRule().rule_hash() == AdmissibilityRule().rule_hash()


class TestEveryWitnessCountCarriesItsAdmissibilityRatio:
    """The prose half of `WIT-01`."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G10)
    def test_a_document_quoting_a_witness_count_points_at_the_ratio(
            self, document: str) -> None:
        path = REPO / document
        if not path.is_file():
            pytest.skip(f"{document} does not exist yet")
        text = _read(document)
        if not _quotes_a_witness_count(text):
            pytest.skip(f"{document} quotes no witness count")
        assert _ADMISSIBILITY_CITATION.search(text), (
            f"{document} quotes a witness count and never points at its "
            "admissibility ratio. WIT-01 requires the ratio to be stated and "
            "applied to every existing count; citing WIT-01, the ratio itself "
            "or outputs/g10/wit01.json satisfies it.")

    def test_the_guard_catches_a_planted_bare_count(self):
        """`SW-20`'s positive control, on the prose half."""
        planted = "The search found 13 witness pairs among 1,999,000 examined."
        assert _WITNESS_COUNT.search(planted)
        assert not _ADMISSIBILITY_CITATION.search(planted), (
            "the citation pattern matched a bare count, so the guard cannot "
            "distinguish a repaired passage from an unrepaired one")

    def test_the_guard_passes_the_same_count_with_its_ratio(self):
        repaired = ("The search found 13 witness pairs among 1,999,000 "
                    "examined; all 13 are admissible under WIT-01 "
                    "(admissibility ratio 1.000).")
        assert _ADMISSIBILITY_CITATION.search(repaired)

    def test_the_guard_does_not_fire_on_prose_describing_the_rule(self):
        """`SW-20`'s negative control: prohibition lists quote the shape."""
        prose = ('Not supported, and not to be written: "13 witness pairs" '
                 "with no admissibility ratio beside it.")
        assert not count_offenders(prose), (
            "the guard read a prohibition list as a claim, which is the "
            "generation-6 defect SW-20 was enacted against")

    def test_an_unrelated_use_of_the_word_admissible_does_not_satisfy_it(self):
        """A measured false negative, pinned so it cannot reopen.

        Three claim-surface documents describe *"the best of the two admissible
        projections"* -- a statement about collocation, not about witnesses. The
        first version of this guard accepted them on that phrase alone.
        """
        assert not _ADMISSIBILITY_CITATION.search(
            "the row reports the best of the two admissible projections")

    def test_the_count_pattern_does_not_match_a_pair_budget(self):
        """1,999,000 pairs examined is not a witness count."""
        for benign in ("1,999,000 pairs examined",
                       "witness pair 0 member a",
                       "719,400 pairs from 1200 draws"):
            assert not _WITNESS_COUNT.search(benign), benign

    def test_the_guard_is_not_vacuous_on_the_real_surface(self):
        seen = {d for d in CLAIM_SURFACE_G10
                if (REPO / d).is_file() and _WITNESS_COUNT.search(_read(d))}
        assert seen, ("no claim-surface document quotes a witness count any "
                      "more; this guard now proves nothing and should be "
                      "retired rather than left green")

    def test_this_modules_own_source_is_out_of_scope(self):
        rel = "tests/test_witness_admissibility_g10.py"
        assert rel not in CLAIM_SURFACE_G10, (
            "this guard's own source quotes every pattern it searches for; "
            "including it would reproduce the generation-6 self-matching defect")


class TestTheMeasuredArtefactBacksTheProse:
    """If `scripts/run_g10.py` has run, the ratio the prose cites must exist."""

    @staticmethod
    def _artefact():
        p = REPO / "outputs" / "g10" / "wit01.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def test_every_committed_set_has_a_ratio(self):
        doc = self._artefact()
        if doc is None:
            pytest.skip("outputs/g10/wit01.json not measured yet")
        for tag, rec in doc["sets"].items():
            assert rec["admissibility_ratio"] == rec["admissibility_ratio"], tag
            assert rec["n_admissible"] + rec["n_rejected"] == \
                rec["n_pairs_offered"], tag

    def test_the_unresolved_junction_separation_is_recorded(self):
        doc = self._artefact()
        if doc is None:
            pytest.skip("outputs/g10/wit01.json not measured yet")
        catch = doc["what_the_rule_catches"]
        assert catch["n_pairs_with_an_unresolved_junction_separation"] >= 1, (
            "the artefact records no sub-node junction separation at all, yet "
            "generation 9 found one at 0.425 nm; either the record or the "
            "resolution is wrong")
        assert catch["node_spacing_nm"] > 0
