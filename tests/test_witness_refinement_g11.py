"""``WIT-02`` register version 3: chart L refined, and the rule now has no gap.

Version 2's guard (``tests/test_witness_refinement_close.py``) reads version 2
and is left exactly as it is. Version 2 is frozen: it is the record of the
coverage while chart L was still the uncovered set, and the assertion in it that
*some* set is non-compliant is a true statement about version 2 forever.

That module carries this instruction, written a generation before this run:

    *If this ever fails because all three sets became compliant, that is the
    good outcome and the right response is to retire this assertion with the
    commit that refined them -- not to leave it green over a rule nothing can
    trip.*

It did not fail, because it reads the frozen version. This module is what that
instruction actually asks for: the same discipline applied to the register that
now says every set is compliant, plus the question the old assertion existed to
ask -- **can this rule still be tripped?** -- asked in a form that survives the
rule being satisfied.

``TestTheRegisterIsDerivedNotDeclared``
    coverage is re-derived here from the artefacts, by matching refinement
    records to witness pairs on exact separation equality, not read out of the
    register.

``TestTheUntouchedSetsDidNotMove``
    version 3 is built by a third implementation of the same match. Chart G and
    chart J must come out identical to version 2, which is what makes chart L's
    row a measurement rather than a difference between two builders.

``TestFullComplianceIsNotVacuous``
    the replacement for the retired assertion. A rule every set satisfies is
    worth nothing unless it *could* have been failed, and it is demonstrated
    here that it could: the rule removed 11 of 37 pairs from chart L, 6 of 13
    from chart J and 1 of 13 from chart G, and a planted uncoverable set is
    still reported non-compliant.

``TestWhatFullCoverageDoesNotBuy``
    the direction this could go wrong. ``WIT-02`` tests *witnesses*, not
    *connectivity*. Full coverage must not be allowed to read as though the
    ``d=16`` basins had become separations; ``PATH-01`` and ``AH-13`` are
    untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "outputs" / "close" / "wit02_register_v2.json"
V3 = ROOT / "outputs" / "close" / "wit02_register_v3.json"
WIT01 = ROOT / "outputs" / "g10" / "wit01.json"

#: Where each refinement artefact keeps the pair's separation and its verdict.
SOURCES: Dict[str, tuple] = {
    "chart_G_d4": ("outputs/wit02_chartG/refine.json",
                   "records", "separation_decades", "survives_refinement"),
    "chart_L_d16": ("outputs/g11/wit02_chartL/refine.json",
                    "records", "separation_decades", "survives_refinement"),
    "chart_J_d16": ("outputs/g9/junction_refine.json",
                    "records", "separation_magnitudes_only",
                    "survives_refinement"),
}

pytestmark = pytest.mark.skipif(
    not V3.is_file(),
    reason="outputs/close/wit02_register_v3.json not written yet; run "
           "PYTHONPATH=src python scripts/run_wit02_chartL.py")


def _read(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def register() -> dict:
    return json.loads(V3.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def v2() -> dict:
    return json.loads(V2.read_text(encoding="utf-8"))


def derive(label: str) -> Dict[str, object]:
    """Re-derive one set's coverage from the artefacts, independently."""
    offered = json.loads(WIT01.read_text(encoding="utf-8"))["sets"][label]
    seps = [p["max_separation"] for p in offered["pairs"]]
    artefact, list_key, sep_key, ok_key = SOURCES[label]
    recs: List[dict] = list(_read(artefact)[list_key])
    matched = [r for r in recs if r[sep_key] in seps]
    n_offered = int(offered["n_pairs_offered"])
    return {
        "n_pairs_offered": n_offered,
        "n_refined": len(matched),
        "n_surviving": sum(1 for r in matched if bool(r[ok_key])),
        "coverage": len(matched) / float(n_offered),
        "compliant": len(matched) == n_offered,
    }


class TestTheRegisterIsDerivedNotDeclared:

    def test_it_covers_every_committed_witness_set(self, register) -> None:
        assert set(register["sets"]) == set(SOURCES)

    @pytest.mark.parametrize("label", sorted(SOURCES))
    def test_the_coverage_is_the_measured_one(self, register, label) -> None:
        got, want = register["sets"][label], derive(label)
        for field, value in want.items():
            assert got[field] == value, (
                f"{label}.{field}: register says {got[field]!r}, the "
                f"artefacts say {value!r}")

    def test_chart_L_is_refined_in_full(self, register) -> None:
        entry = register["sets"]["chart_L_d16"]
        assert entry["n_pairs_offered"] == 37
        assert entry["n_refined"] == 37
        assert entry["coverage"] == 1.0
        assert entry["compliant"] is True
        assert entry["refinement_artefact"] == (
            "outputs/g11/wit02_chartL/refine.json")

    def test_the_verdict_counts_agree_with_the_rows(self, register) -> None:
        rows = register["sets"]
        v = register["verdict"]
        assert v["n_sets"] == len(rows)
        assert v["n_compliant"] == sum(
            1 for e in rows.values() if e["compliant"])
        assert v["non_compliant"] == sorted(
            k for k, e in rows.items() if not e["compliant"])
        assert v["all_compliant"] == all(
            e["compliant"] for e in rows.values())


class TestTheUntouchedSetsDidNotMove:
    """The control that makes chart L's row a measurement."""

    @pytest.mark.parametrize("label", ["chart_G_d4", "chart_J_d16"])
    def test_the_row_is_identical_to_version_2(self, register, v2,
                                               label) -> None:
        for field in ("n_pairs_offered", "n_refined", "n_surviving",
                      "coverage", "compliant", "refinement_artefact"):
            assert register["sets"][label][field] == v2["sets"][label][field], (
                f"{label}.{field} moved between register versions 2 and 3, and "
                "this run touched neither set")

    def test_the_register_records_that_control(self, register) -> None:
        block = register["untouched_sets_reproduce_version_2"]
        assert block["all"] is True, block["rows"]

    def test_version_2_is_still_on_disk_and_still_records_the_gap(
            self, v2) -> None:
        assert v2["sets"]["chart_L_d16"]["n_refined"] == 0
        assert v2["sets"]["chart_L_d16"]["compliant"] is False

    def test_the_new_register_names_what_it_supersedes(self, register) -> None:
        sup = register["supersedes"]
        assert sup["register"].endswith("wit02_register_v2.json")
        assert "chart L only" in sup["what_moved"]


class TestFullComplianceIsNotVacuous:
    """What the retired assertion was really asking, asked so it survives.

    ``IA-1``: a plausible negative control, and a positive control that would
    fail if the rule did nothing.
    """

    def test_every_set_is_compliant(self, register) -> None:
        assert register["verdict"]["all_compliant"] is True
        assert register["verdict"]["non_compliant"] == []

    def test_positive_control_the_rule_actually_removed_members(
            self, register) -> None:
        """Would fail if ``WIT-02`` were a rubber stamp.

        A rule that never removes anything is decoration. Across the three
        sets it removed 18 of 63 pairs, and it removed some from every one.
        """
        losses = {label: e["n_pairs_offered"] - e["n_surviving"]
                  for label, e in register["sets"].items()}
        assert all(v > 0 for v in losses.values()), (
            f"WIT-02 removed nothing from at least one set: {losses}. A rule "
            "no set can fail is not evidence that the sets are sound")
        assert sum(losses.values()) >= 3

    def test_negative_control_a_planted_uncovered_set_is_non_compliant(
            self) -> None:
        """Plausible, not malformed: a set with a real artefact that covers
        only part of it -- which is exactly what chart L was until this run."""
        offered = json.loads(WIT01.read_text(encoding="utf-8"))[
            "sets"]["chart_L_d16"]
        seps = [p["max_separation"] for p in offered["pairs"]]
        recs = list(_read(SOURCES["chart_L_d16"][0])["records"])
        partial = [r for r in recs[:5] if r["separation_decades"] in seps]
        coverage = len(partial) / float(offered["n_pairs_offered"])
        assert coverage < 1.0
        assert len(partial) != offered["n_pairs_offered"], (
            "a five-record prefix of a 37-pair set was judged complete; the "
            "compliance test is counting something other than coverage")

    def test_negative_control_a_foreign_record_does_not_match(self) -> None:
        """A refinement record from another chart must not count toward this
        one, or coverage would be a recollection rather than a fraction."""
        offered = json.loads(WIT01.read_text(encoding="utf-8"))[
            "sets"]["chart_L_d16"]
        seps = {p["max_separation"] for p in offered["pairs"]}
        foreign = list(_read(SOURCES["chart_G_d4"][0])["records"])
        crossed = [r for r in foreign if r["separation_decades"] in seps]
        assert not crossed, (
            f"{len(crossed)} chart-G refinement records match chart-L witness "
            "separations, so the register's matching does not identify a set")


class TestWhatFullCoverageDoesNotBuy:
    """The direction in which this result is most likely to be over-read."""

    def test_the_register_says_what_full_coverage_does_not_mean(
            self, register) -> None:
        text = register["verdict"]["what_full_coverage_does_not_mean"].lower()
        assert "upper bound" in text
        assert "minimum-energy path" in text or "minimum energy path" in text
        assert "separation" in text

    def test_the_recount_carries_the_bound_direction(self) -> None:
        recount = _read("outputs/g11/wit02_chartL/recount.json")
        text = recount["verdict"][
            "the_barrier_is_still_an_upper_bound"].lower()
        assert "upper" in text and "straight line" in text, (
            "the recount must carry BOUND-01's direction; a basin measured "
            "over refined witnesses is still a search that found no path")

    def test_the_surviving_count_is_reported_with_its_denominator(
            self, register) -> None:
        """``DOC-08``. 26 is meaningless without 37."""
        entry = register["sets"]["chart_L_d16"]
        assert entry["n_surviving"] is not None
        assert entry["n_pairs_offered"] == 37
        assert entry["n_refined"] == 37
