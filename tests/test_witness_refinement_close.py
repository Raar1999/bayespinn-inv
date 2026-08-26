"""``WIT-02``: every witness is refined before it is counted.

**Enacted** closing operator ruling of 2026-08-26 §2. Rule text and the defect
that forced it: ``docs/RULES_ENACTED.md``.

    Every witness is refined before it is counted. Not the ones near the floor
    -- all of them.

What this guard can and cannot be
---------------------------------
It cannot refine anything. Refining a witness pair costs oracle solves across
three grids and two tolerances, the closing ruling allows *arithmetic on
existing artefacts only*, and there is no generation 11. So what ``WIT-02`` gets
at close is a **register** -- ``outputs/close/wit02_register.json``, built by
``scripts/run_close.py`` -- and this module guards the register rather than the
rule's satisfaction. That is the honest shape for a rule enacted over a corpus
it postdates: the alternative is a green suite over an unmet rule, which is the
``CI-01`` failure mode in miniature.

The register is measured, not written down
------------------------------------------
Coverage is established by matching each refinement record to a witness pair on
**exact equality** of the separation in decades against ``WIT-01``'s
``max_separation`` for the same set. Those are the same float written into two
artefacts a generation apart, not two measurements of one quantity, so equality
is the right test and inequality is a real finding.
:class:`TestTheMatchingIsNotVacuous` plants a record that must *not* match.

What it enforces
----------------
``TestTheRegisterIsDerivedNotDeclared``
    every coverage figure is re-derived here from the source artefacts and
    compared. A register that drifts from the artefacts it summarises is worse
    than no register.
``TestNoSetBecomesCompliantWithoutEvidence``
    a set may only be marked compliant if a refinement artefact exists, covers
    every offered pair, and is named. This is the direction that matters: the
    cheap way to satisfy ``WIT-02`` is to edit a boolean.
``TestTheNonComplianceIsVisibleOnTheClaimSurface``
    the prose half. A claim-surface document that quotes a witness count must
    point its reader at the refinement register, exactly as ``WIT-01`` requires
    it to point at the admissibility ratio. ``SW-20``'s two controls are below,
    and the negative one is the same shape as the one ``WIT-01``'s guard needed:
    a pattern that accepts the bare word *refined* would pass three documents
    that discuss refinement of something else.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from test_claim_surface_g7 import _PROHIBITION, CLAIM_SURFACE_G7, _read, _units
from test_witness_admissibility_g10 import _WITNESS_COUNT

REPO = Path(__file__).resolve().parents[1]
REGISTER = REPO / "outputs" / "close" / "wit02_register.json"
WIT01 = REPO / "outputs" / "g10" / "wit01.json"

#: What makes the refinement status available to the reader.
#:
#: Deliberately does NOT accept a bare "refined" or "refinement". Six
#: claim-surface passages describe *grid* refinement of the discretisation, and
#: three describe the generation-6 battery in the abstract; a pattern that took
#: those as a citation would pass documents that never state a coverage.
_REGISTER_CITATION = re.compile(
    r"WIT-02|refinement\s+register|outputs/close/wit02_register\.json"
    r"|\bsurviv\w*\s+(?:grid\s+)?refinement\b|\bof\s+13\s+separated\b"
    r"|\b\d{1,3}\s+of\s+\d{1,3}\s+refined\b",
    re.I)


@pytest.fixture(scope="module")
def register() -> dict:
    if not REGISTER.is_file():
        pytest.skip("outputs/close/wit02_register.json not written yet; "
                    "run PYTHONPATH=src python scripts/run_close.py")
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def _wit01_sets() -> dict:
    return json.loads(WIT01.read_text(encoding="utf-8"))["sets"]


class TestTheRegisterIsDerivedNotDeclared:
    """Every number re-derived from the artefacts it claims to summarise."""

    def test_it_covers_every_committed_witness_set(self, register) -> None:
        assert set(register["sets"]) == set(_wit01_sets()), (
            "the register and WIT-01 disagree about which witness sets exist; "
            "a set that is committed and unregistered is exactly the gap "
            "WIT-02 was enacted to make visible")

    def test_the_offered_counts_match_wit01(self, register) -> None:
        sets = _wit01_sets()
        for label, entry in register["sets"].items():
            assert entry["n_pairs_offered"] == sets[label]["n_pairs_offered"]

    def test_the_coverage_is_the_measured_one(self, register) -> None:
        sets = _wit01_sets()
        for label, entry in register["sets"].items():
            src = entry["refinement_artefact"]
            if src is None:
                assert entry["n_refined"] == 0
                assert entry["coverage"] == 0.0
                continue
            path = REPO / src
            assert path.is_file(), (
                label + " names " + src + " as its refinement artefact and the "
                "file is absent")
            seps = {p["max_separation"] for p in sets[label]["pairs"]}
            doc = json.loads(path.read_text(encoding="utf-8"))
            key = "pairs" if "pairs" in doc else "records"
            sep_key = ("separation_decades" if key == "pairs"
                       else "separation_magnitudes_only")
            matched = [r for r in doc[key] if r[sep_key] in seps]
            assert entry["n_refined"] == len(matched), (
                label + ": the register says " + str(entry["n_refined"])
                + " pairs refined and the artefact matches " + str(len(matched)))
            assert entry["coverage"] == pytest.approx(
                len(matched) / entry["n_pairs_offered"])

    def test_the_verdict_counts_agree_with_the_rows(self, register) -> None:
        rows = register["sets"]
        v = register["verdict"]
        assert v["n_sets"] == len(rows)
        assert v["n_compliant"] == sum(1 for e in rows.values() if e["compliant"])
        assert sorted(v["non_compliant"]) == sorted(
            k for k, e in rows.items() if not e["compliant"])
        assert v["all_compliant"] is all(e["compliant"] for e in rows.values())


class TestNoSetBecomesCompliantWithoutEvidence:
    """The direction that matters: compliance is the cheap thing to fake."""

    def test_compliance_requires_full_coverage_by_a_named_artefact(
            self, register) -> None:
        for label, entry in register["sets"].items():
            if not entry["compliant"]:
                continue
            assert entry["refinement_artefact"], (
                label + " is marked compliant with no refinement artefact")
            assert (REPO / entry["refinement_artefact"]).is_file()
            assert entry["n_refined"] == entry["n_pairs_offered"], (
                label + " is marked compliant at coverage "
                + str(entry["coverage"]))
            assert entry["coverage"] == 1.0

    def test_a_non_compliant_set_names_what_rests_on_it(self, register) -> None:
        for label, entry in register["sets"].items():
            if entry["compliant"]:
                continue
            assert entry["carries"], (
                label + " does not satisfy WIT-02 and the register does not "
                "say what rests on it, which is the half of the finding that "
                "makes it actionable")

    def test_the_rule_is_not_vacuously_satisfied(self, register) -> None:
        """A register in which everything passes proves nothing about the rule.

        If this ever fails because all three sets became compliant, that is the
        good outcome and the right response is to retire this assertion with the
        commit that refined them -- not to leave it green over a rule nothing
        can trip.
        """
        assert register["verdict"]["non_compliant"], (
            "every committed witness set now satisfies WIT-02. If a refinement "
            "run made that true, say so and retire this test; if a boolean "
            "made it true, that is the defect WIT-02 exists to catch")

    def test_the_uncovered_set_is_the_load_bearing_one_and_says_so(
            self, register) -> None:
        entry = register["sets"]["chart_L_d16"]
        if entry["compliant"]:
            pytest.skip("chart L has been refined; this record is historical")
        assert entry["n_refined"] == 0
        assert "dimension" in entry["carries"].lower(), (
            "the chart-L set carries the reading that the ridge/basin split "
            "follows the dimension; the register must say so, because the "
            "cost of the gap is the point of recording it")


class TestTheMatchingIsNotVacuous:
    """`SW-20`'s controls on the identity test that builds the register."""

    def test_a_planted_foreign_record_does_not_match(self) -> None:
        seps = {p["max_separation"]
                for p in _wit01_sets()["chart_J_d16"]["pairs"]}
        planted = {"separation_magnitudes_only": 1.6088760231687687 + 1e-9}
        assert planted["separation_magnitudes_only"] not in seps, (
            "the register matches records by exact separation equality; a value "
            "one nanodecade away matched, so the identity test is not exact "
            "and coverage could be counting another set's pairs")

    def test_the_real_records_do_match(self) -> None:
        seps = {p["max_separation"]
                for p in _wit01_sets()["chart_J_d16"]["pairs"]}
        recs = json.loads(
            (REPO / "outputs" / "g9" / "junction_refine.json").read_text(
                encoding="utf-8"))["records"]
        assert all(r["separation_magnitudes_only"] in seps for r in recs), (
            "the generation-9 refinement records no longer match the chart-J "
            "witness set, so one of the two artefacts has moved")

    def test_partial_coverage_is_reported_as_partial(self, register) -> None:
        g = register["sets"]["chart_G_d4"]
        if g["compliant"]:
            pytest.skip("chart G has been refined in full; record is historical")
        assert 0 < g["n_refined"] < g["n_pairs_offered"], (
            "chart G's coverage is neither zero nor complete and must be "
            "reported as the fraction it is; a partial coverage rounded to "
            "'refined' or 'not refined' is the sentence WIT-02 forbids")


class TestTheNonComplianceIsVisibleOnTheClaimSurface:
    """The prose half of `WIT-02`."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_a_document_quoting_a_witness_count_points_at_the_register(
            self, document: str) -> None:
        path = REPO / document
        if not path.is_file():
            pytest.skip(document + " does not exist yet")
        text = _read(document)
        quotes = [u for _, u in _units(text)
                  if _WITNESS_COUNT.search(u) and not _PROHIBITION.search(u)]
        if not quotes:
            pytest.skip(document + " quotes no witness count")
        assert _REGISTER_CITATION.search(text), (
            document + " quotes a witness count and never points at the "
            "refinement register. WIT-02 requires every witness to be refined "
            "before it is counted; where that has not happened the count may "
            "still be quoted, but not without the coverage beside it. Citing "
            "WIT-02, the register, or a survival figure satisfies this.")

    def test_the_guard_catches_a_planted_bare_count(self) -> None:
        """`SW-20`'s positive control."""
        planted = "The search found 13 witness pairs among 1,999,000 examined."
        assert _WITNESS_COUNT.search(planted)
        assert not _REGISTER_CITATION.search(planted)

    def test_the_guard_passes_the_same_count_with_its_coverage(self) -> None:
        repaired = ("The search found 13 witness pairs among 1,999,000 "
                    "examined; 3 of 13 refined under WIT-02.")
        assert _REGISTER_CITATION.search(repaired)

    def test_a_bare_mention_of_refinement_does_not_satisfy_it(self) -> None:
        """`SW-20`'s negative control, and the reason the pattern is narrow.

        Grid refinement of the discretisation is discussed all over this
        repository and has nothing to do with witness coverage. A pattern that
        accepted the word would pass documents that state no coverage at all --
        the same false negative ``WIT-01``'s guard measured on the phrase *"the
        best of the two admissible projections"*.
        """
        for benign in ("the differences halve under refinement",
                       "refinement of the grid from N=301 to N=1201",
                       "a refined estimate of the discretisation floor"):
            assert not _REGISTER_CITATION.search(benign), benign
        # ...and the form the real prose uses for witness refinement, which the
        # first version of this pattern rejected: `docs/G8_RESULT.md` writes
        # "7 of which survive grid refinement", where "grid" sits between the
        # two words. A measured false positive on this guard's own surface.
        assert _REGISTER_CITATION.search("7 of which survive grid refinement")

    def test_the_guard_does_not_fire_on_prose_describing_the_rule(self) -> None:
        prose = ('Not supported, and not to be written: "13 witness pairs" '
                 "with no refinement coverage beside it.")
        assert all(_PROHIBITION.search(u) or not _WITNESS_COUNT.search(u)
                   for _, u in _units(prose)), (
            "the guard read a prohibition list as a claim, which is the "
            "generation-6 defect SW-20 was enacted against")

    def test_the_guard_is_not_vacuous_on_the_real_surface(self) -> None:
        seen = {d for d in CLAIM_SURFACE_G7
                if (REPO / d).is_file() and _WITNESS_COUNT.search(_read(d))}
        assert seen, ("no claim-surface document quotes a witness count any "
                      "more; this guard now proves nothing and should be "
                      "retired rather than left green")

    def test_this_modules_own_source_is_out_of_scope(self) -> None:
        assert "tests/test_witness_refinement_close.py" not in CLAIM_SURFACE_G7
