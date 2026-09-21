"""``scripts/run_close.py``: the closing ruling's one free check, guarded.

The ruling of 2026-08-26 (closing) §5 allows exactly one further measurement and
constrains it twice over: *"arithmetic on existing artefacts only"* and *"if it
needs one new solve, it is future work and you stop"*. Both halves are checkable
and both are checked here rather than promised in prose.

``TestThisRanNoSolver``
    reads ``scripts/run_close.py``'s own AST and fails if it imports
    ``bayespinn_inv``, or names any of the solver entry points the other run
    scripts use. A script that *says* it did no solving and a script that
    *cannot* solve are different objects, and only the second one is evidence.
    ``SW-20``: the subject is source code, so the guard is written over the AST
    and not over the text; both controls are below.

``TestTheDecompositionIsAnIdentity``
    the split between "scale" and "shape" has no free parameter. It is checked
    numerically against the artefact -- ``dlog sigma_i`` must equal
    ``dlog sigma_1 + dlog(sigma_i/sigma_1)`` to floating-point -- because an
    identity that has quietly become a fit is the failure mode that would make
    the shares meaningless while leaving them plausible.

``TestTheVerdictRestsOnlyOnResolvableValues``
    the module's own first draft claimed five indices and control ``C3`` failed
    in four of eighteen cells: ``sigma_5`` sits at or below the estimator's
    spectral floor at the widest windows. The repair was to narrow the claim to
    ``sigma_1..sigma_4`` -- the indices the rank is actually made of -- and keep
    reporting the fifth. This class pins that: the excluded cells must still be
    named in the artefact, so the defect cannot be tidied away by deleting the
    row that recorded it.

``TestTheControlAxisIsNotVacuous``
    ``C4`` is only a control if the spacing axis really does leave the rank
    alone while the width axis moves it. Both halves are asserted from the
    artefact.

``TestTheProseMatchesTheArtefact``
    ``docs/CLOSE_RULING.md`` §1 states the answer in one paragraph, as the
    ruling requires. The numbers in that paragraph are re-read from
    ``outputs/close/spectrum_shape.json`` here, so the paragraph cannot drift
    from the measurement it reports (``DOC-07``'s discipline, applied to a
    document instead of a commit message).
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path
from typing import Set

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_close.py"
ARTEFACT = REPO / "outputs" / "close" / "spectrum_shape.json"
PROSE = REPO / "docs" / "CLOSE_RULING.md"

#: Names that would mean a solve happened. The package itself, and the three
#: entry points every other run script reaches the oracle through.
SOLVER_NAMES = ("bayespinn_inv", "build_solver", "chart_forward_jacobian",
                "analyse_identifiability", "cell_spectrum", "run_g9", "run_g10")


def _tree() -> ast.Module:
    return ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))


def _imported_names(tree: ast.Module) -> Set[str]:
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module.split(".")[0])
            out.update(a.name for a in node.names)
    return out


def _called_names(tree: ast.Module) -> Set[str]:
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


@pytest.fixture(scope="module")
def doc() -> dict:
    if not ARTEFACT.is_file():
        pytest.skip("outputs/close/spectrum_shape.json not written yet; "
                    "run PYTHONPATH=src python scripts/run_close.py")
    return json.loads(ARTEFACT.read_text(encoding="utf-8"))


class TestThisRanNoSolver:
    """`SW-20`: the constraint is on source, so the guard reads the AST."""

    def test_the_script_exists(self) -> None:
        assert SCRIPT.is_file(), "the closing ruling's check has no script"

    def test_it_imports_nothing_that_can_solve(self) -> None:
        names = _imported_names(_tree())
        offenders = sorted(names & set(SOLVER_NAMES))
        assert not offenders, (
            "scripts/run_close.py imports " + ", ".join(offenders) + ". The "
            "closing ruling allows arithmetic on existing artefacts only; a "
            "script that can reach the oracle cannot evidence that it did not.")

    def test_it_calls_nothing_that_can_solve(self) -> None:
        offenders = sorted(_called_names(_tree()) & set(SOLVER_NAMES))
        assert not offenders, (
            "scripts/run_close.py calls " + ", ".join(offenders))

    def test_it_reads_only_artefacts_that_predate_the_ruling(self, doc) -> None:
        for rel in doc["arithmetic_only"]["inputs"]:
            assert (REPO / rel).is_file(), rel + " is named as an input and is absent"
        assert doc["arithmetic_only"]["new_solves"] == 0

    def test_the_guard_catches_a_planted_solver_import(self) -> None:
        """`SW-20`'s positive control."""
        planted = ast.parse(
            "from bayespinn_inv.inverse.charts import ChartG\nChartG(4, None)\n")
        assert _imported_names(planted) & set(SOLVER_NAMES), (
            "the AST guard cannot see a solver import, so it proves nothing")

    def test_the_guard_does_not_fire_on_a_mention_in_a_docstring(self) -> None:
        """`SW-20`'s negative control, and the reason it is written over the AST.

        ``scripts/run_close.py``'s docstring *names* ``bayespinn_inv`` in the
        sentence that says it does not import it. A text search would read that
        sentence as the violation it describes -- the generation-6 self-matching
        defect exactly.
        """
        assert "bayespinn_inv" in SCRIPT.read_text(encoding="utf-8"), (
            "the docstring no longer mentions the package, so this control no "
            "longer controls for anything")
        benign = ast.parse('"""This module does not import bayespinn_inv."""\n')
        assert not (_imported_names(benign) & set(SOLVER_NAMES))


class TestTheDecompositionIsAnIdentity:
    """No free parameter, checked rather than asserted."""

    def test_the_terms_sum(self, doc) -> None:
        for dname, d in doc["devices"].items():
            for e in d["width_axis"]["per_index"]:
                assert e["delta_log10_sigma"] == pytest.approx(
                    e["delta_log10_scale"] + e["delta_log10_shape"], abs=1e-12), (
                    dname + " index " + str(e["index"]) + ": the scale and "
                    "shape terms no longer sum to the movement they decompose, "
                    "so the shares are a fit and not an identity")

    def test_the_shares_sum_to_one(self, doc) -> None:
        for d in doc["devices"].values():
            for e in d["width_axis"]["per_index"]:
                assert e["scale_share"] + e["shape_share"] == pytest.approx(1.0)

    def test_the_cutoff_is_read_from_the_run_configuration(self, doc) -> None:
        cfg = json.loads((REPO / "outputs" / "g10" / "manifest.json").read_text(
            encoding="utf-8"))["config"]
        assert doc["cutoff"]["noise_rel"] == cfg["noise_rel"]
        assert doc["cutoff"]["cutoff_symlog"] == pytest.approx(
            math.log10(1.0 + cfg["noise_rel"]))
        assert doc["cutoff"]["kind"] == "ABSOLUTE", (
            "the two readings are separable by sign only because the cutoff "
            "does not scale with sigma_1")


class TestTheVerdictRestsOnlyOnResolvableValues:
    """The defect this module found in its own first draft, pinned open."""

    def test_the_claim_is_narrower_than_the_report(self, doc) -> None:
        scope = doc["claim_scope"]
        assert scope["indices_the_verdict_rests_on"] == [1, 2, 3, 4]
        assert scope["indices_reported"] == [1, 2, 3, 4, 5]

    def test_the_excluded_cells_are_still_named(self, doc) -> None:
        c3 = doc["controls"]["C3_nothing_the_verdict_rests_on_is_estimator_noise"]
        assert c3["passed"] is True
        assert c3["reported_but_excluded_from_the_verdict"], (
            "no cell is recorded as excluded. Either sigma_5 became resolvable "
            "everywhere -- in which case say so -- or the record of why the "
            "claim stops at four indices has been deleted")
        for e in c3["reported_but_excluded_from_the_verdict"]:
            assert e["sigma"] <= e["floor_probe_symlog"]

    def test_every_claimed_value_clears_the_floor_probe(self, doc) -> None:
        c3 = doc["controls"]["C3_nothing_the_verdict_rests_on_is_estimator_noise"]
        assert all(e["clears"] for e in c3["cells"])
        assert c3["worst_margin"] > 1.0

    def test_the_verdict_quotes_no_excluded_index(self, doc) -> None:
        for d in doc["devices"].values():
            live = [e for e in d["width_axis"]["per_index"] if e["within_claim"]]
            assert [e["index"] for e in live] == [2, 3, 4]


class TestTheControlAxisIsNotVacuous:
    """`C4` controls for something only if the two axes actually differ."""

    def test_the_rank_moves_along_width_and_not_along_spacing(self, doc) -> None:
        for dname, d in doc["devices"].items():
            ranks = d["width_axis"]["rank_at_operational_cutoff"]
            assert len(set(ranks)) > 1, dname + ": the rank does not move along width"
        for e in doc["controls"]["C4_the_axis_that_does_not_move_the_rank"]["spacing"]:
            assert e["rank_moves"] is False, (
                e["device"] + ": the rank moves along spacing too, so spacing "
                "is no longer the control SPEC-g9-2 made it")

    def test_the_shape_statistic_separates_the_two_axes(self, doc) -> None:
        """The flattening must be large on width and small on spacing."""
        for dname, d in doc["devices"].items():
            s = d["width_axis"]["decay_slope"]
            width_change = abs(s[-1] / s[0] - 1.0)
            spacing = next(
                e for e in doc["controls"][
                    "C4_the_axis_that_does_not_move_the_rank"]["spacing"]
                if e["device"] == dname)
            assert width_change > 10.0 * spacing["decay_slope_change_fraction"], (
                dname + ": the spectrum flattens as much along spacing as "
                "along width, so flattening is not an account of a climb that "
                "happens on one axis only")

    def test_the_two_code_paths_agree_where_they_describe_one_observation_set(
            self, doc) -> None:
        c4 = doc["controls"]["C4_the_axis_that_does_not_move_the_rank"]
        assert all(c4["alpha0_equals_width075"]), (
            "alpha=0 and width=0.75 are 16 linearly spaced biases over "
            "0.15-0.90 V built by two different functions; their spectra "
            "disagree, so one of the two axes is not the observation set it "
            "claims to be")


class TestTheClimbIsNotAnArtefactOfTheCutoff:

    def test_it_climbs_at_every_uncapped_cutoff(self, doc) -> None:
        c = doc["climb_is_not_a_property_of_the_cutoff"]
        assert c["climbs_everywhere"] is True
        assert c["non_decreasing_everywhere"] is True
        assert len(c["cutoffs_examined"]) >= 5

    def test_the_dropped_cutoffs_are_dropped_for_a_measured_reason(self, doc) -> None:
        c = doc["climb_is_not_a_property_of_the_cutoff"]
        assert c["excluded"], (
            "no cutoff was excluded; if resolvable_rank never caps the count "
            "then say so, because the exclusion rule below is describing "
            "nothing")
        assert set(c["excluded"]).isdisjoint(set(c["cutoffs_examined"]))
        assert "resolvable_rank" in c["why_excluded"]


class TestTheProvenanceIsWhatItClaims:
    """A pure-arithmetic step attests its inputs, not its tree.

    Every other run script writes a ``Manifest`` from ``bayespinn_inv``, which
    this one may not import. What it writes instead is a digest per input file,
    and that is the stronger attestation for this step: a solving run's answer
    depends on the working tree, and this one's depends only on the bytes it
    read. ``git_dirty`` is therefore recorded and deliberately not gated.
    """

    def test_every_input_digest_is_the_real_one(self, doc) -> None:
        import hashlib
        for rel, digest in doc["provenance"]["inputs_sha256"].items():
            path = REPO / rel
            assert path.is_file(), rel + " is digested and absent"
            assert digest == hashlib.sha256(path.read_bytes()).hexdigest(), (
                rel + " has changed since the artefact was written; re-run "
                "PYTHONPATH=src python scripts/run_close.py")

    def test_it_digests_every_input_it_names(self, doc) -> None:
        assert (set(doc["provenance"]["inputs_sha256"])
                == set(doc["arithmetic_only"]["inputs"])), (
            "the inputs the artefact names and the inputs it digests differ, so "
            "one of the two lists is describing a different run")

    def test_the_register_carries_its_own_provenance(self) -> None:
        import hashlib
        path = REPO / "outputs" / "close" / "wit02_register.json"
        if not path.is_file():
            pytest.skip("outputs/close/wit02_register.json not written yet")
        prov = json.loads(path.read_text(encoding="utf-8"))["provenance"]
        for rel, digest in prov["inputs_sha256"].items():
            src = REPO / rel
            assert src.is_file(), rel
            assert digest == hashlib.sha256(src.read_bytes()).hexdigest(), rel

    def test_the_unvalidated_platforms_are_still_named(self, doc) -> None:
        """`PROV-07` is open; a close does not close it by being a close."""
        prov = doc["provenance"]
        assert prov["validated_platforms"] == ["win32"]
        assert "PROV-07" in prov["unvalidated"]


class TestTheProseMatchesTheArtefact:
    """`DOC-07`'s discipline, applied to the closing document."""

    @staticmethod
    def _text() -> str:
        return PROSE.read_text(encoding="utf-8")

    def test_the_document_exists(self) -> None:
        assert PROSE.is_file(), "docs/CLOSE_RULING.md is missing"

    def test_it_states_the_verdict_the_artefact_reached(self, doc) -> None:
        assert doc["verdict"]["agreed"] in ("SHAPE", "SCALE", "NEITHER")
        text = self._text().lower()
        assert doc["verdict"]["agreed"].lower() in text, (
            "the closing document does not state the verdict "
            + doc["verdict"]["agreed"])

    def test_the_sigma_1_range_in_the_prose_is_the_measured_one(self, doc) -> None:
        ranges = sorted(d["width_axis"]["head"]["range"]
                        for d in doc["devices"].values())
        text = self._text()
        for r in ranges:
            token = format(r, ".3f")
            assert token in text, (
                "the closing document does not quote the measured sigma_1 "
                "range " + token + "; a paragraph that reports a measurement "
                "must carry that measurement's numbers")

    def test_it_records_that_sigma_1_moves_the_wrong_way(self, doc) -> None:
        for d in doc["devices"].values():
            assert d["width_axis"]["head"]["delta_log10"] < 0.0, (
                "sigma_1 no longer falls, so the sentence in the closing "
                "document about it moving the wrong way is now false")
        assert re.search(r"wrong (?:way|direction)|falls|downward|receding",
                         self._text(), re.I)

    def test_it_names_the_status_as_a_description(self, doc) -> None:
        assert doc["status"].startswith("DESCRIPTION")
        assert re.search(r"description(?!\s+of\s+the\s+file)", self._text(), re.I), (
            "the closing document must say the free check is a description "
            "and not a test; the question was asked after the data existed")
