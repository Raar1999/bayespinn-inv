"""``LOOP_STATE_v9.json``: the addendum state file, guarded the same way.

The loop closed at ``LOOP_STATE_v8.json``. One bounded refinement was authorised
afterwards -- operator ruling of 2026-08-28 §2, chart G only -- and this file
records what it measured. It **imports** ``baseline_offenders`` from
``tests/test_loop_state_g9.py`` rather than restating it: ``REP-01`` has one
definition, and two copies of a rule drift into two rules.

What is new here, beyond the inherited invariants
-------------------------------------------------
``TestTheAddendumIsRecordedAsAnAddendum``
    it must still say the loop is closed, it must open no specification clause,
    and it must record the refinement as a **measurement with a
    pre-registration** rather than as arithmetic -- which is the opposite of what
    the closing state file had to say about its free check, and for the same
    reason: the record must match what actually happened.

``TestTheRefinementAgreesWithItsArtefacts``
    every number the state file quotes about the refinement is re-read from
    ``outputs/wit02_chartG/`` and ``outputs/close/wit02_register_v2.json`` and
    compared. A state file that summarises artefacts it disagrees with is worse
    than one that summarises nothing.

``TestWhatIsNotClosedStaysOpen``
    ``WITNESS-04`` narrowed to chart L is not ``WITNESS-04`` resolved, and
    ``PATH-01`` is untouched by a refinement. The direction that matters is the
    one where a bounded run is recorded as having settled more than it did.

``TestTheBaselineIsHonestAboutItsFailures``
    the recorded pytest baseline must state the failures the suite actually has
    in this tree. Eight guards fail here because the commit hashes every state
    file since generation 8 records are absent from this clone's object graph;
    a baseline claiming zero failures would be the ``CI-01`` shape exactly.

``SW-20``: the subject is a JSON document; this module's own source is not part
of the scanned document, and both controls are in
:class:`TestTheGuardStillHasBothControls`.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import pytest
from test_loop_state_g9 import baseline_offenders

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v9.json"
PREVIOUS = ROOT / "LOOP_STATE_v8.json"
RUN = ROOT / "outputs" / "wit02_chartG"
REGISTER_V2 = ROOT / "outputs" / "close" / "wit02_register_v2.json"

pytestmark = pytest.mark.skipif(
    not STATE.is_file(),
    reason="LOOP_STATE_v9.json is written by the addendum state commit")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def refine() -> dict:
    return json.loads((RUN / "refine.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def recount() -> dict:
    return json.loads((RUN / "recount.json").read_text(encoding="utf-8"))


class TestTheFixedPointIsStillDefinedAway:
    """Inherited. A state file cannot name the commit that wrote it."""

    def test_champion_is_not_the_commit_that_wrote_this_file(self, state) -> None:
        writer = git("log", "-1", "--format=%H", "--", STATE.name)
        assert writer, "git could not name the commit that wrote the state file"
        assert state["champion_commit"] != writer

    def test_bookkeeping_commit_is_null_at_write_time(self, state) -> None:
        assert state["bookkeeping_commit"] is None

    def test_the_champion_is_a_real_reachable_commit(self, state) -> None:
        assert git("cat-file", "-t", state["champion_commit"]) == "commit", (
            "champion_commit names a commit this clone cannot reach. That is "
            "the HIST-01 condition the earlier state files are in, and this "
            "file was written in this object graph, so it has no excuse")


class TestEveryBaselineCarriesItsInvocation:
    """`REP-01` as amended at generation 9, through the imported predicate."""

    def test_no_baseline_is_a_bare_scalar(self, state) -> None:
        offenders = baseline_offenders(state["baselines"])
        assert not offenders, (
            "REP-01 -- a baseline that does not carry the invocation that "
            "produced it is a number nobody can re-derive:\n  "
            + "\n  ".join(offenders))

    def test_the_carried_mypy_scope_did_not_shrink(self, state) -> None:
        now = state["baselines"]["mypy_tracked_tree"]
        before = json.loads(PREVIOUS.read_text(encoding="utf-8"))[
            "baselines"]["mypy_tracked_tree"]
        assert now["invocation"] == before["invocation"]
        assert now["files_checked"] >= before["files_checked"]
        assert now["findings"] <= before["findings"], (
            "the carried mypy baseline grew; the ruling of 2026-08-26 §4 made "
            "this the baseline precisely so it could not")


class TestTheAddendumIsRecordedAsAnAddendum:

    def test_the_loop_is_still_closed(self, state) -> None:
        assert state["terminated"] is True
        assert state["closed"] is True
        assert re.search(r"no generation 11|generation 11", state["designation"],
                         re.I)

    def test_it_opens_no_specification_clause(self, state) -> None:
        opened = [k for k in state["spec_clause_status"]
                  if k.lower().startswith(("spec-g11", "spec-close",
                                           "spec-addendum"))]
        assert not opened, (
            "the ruling authorised one refinement and no new scope; these "
            "clauses open scope: " + ", ".join(opened))

    def test_the_refinement_is_recorded_as_a_measurement(self, state) -> None:
        """The mirror image of the closing file's free-check assertion.

        The close had to record its check as arithmetic because it solved
        nothing. This one solved, so recording it as arithmetic would understate
        what was done and would make the pre-registration pointless.
        """
        rec = state["addendum"]
        assert rec["new_solves"] > 0
        assert rec["status"].startswith("MEASUREMENT")
        assert rec["preregistered"] is True
        for rel in rec["artefacts"]:
            assert (ROOT / rel).is_file(), rel + " is named and absent"

    def test_the_authorisation_is_named(self, state) -> None:
        text = json.dumps(state["addendum"])
        assert "2026-08-28" in text, (
            "a solving run after a close must name the ruling that authorised "
            "it, or the close means nothing")

    def test_the_operator_tasks_are_carried_not_closed(self, state) -> None:
        joined = " ".join(state["operator_tasks"])
        for task in ("OT-1", "OT-2", "OT-3"):
            assert task in joined


class TestTheRefinementAgreesWithItsArtefacts:
    """Every quoted number re-read from the run that produced it."""

    def test_the_survival_counts_match(self, state, refine) -> None:
        rec, v = state["addendum"], refine["verdict"]
        assert rec["n_pairs_offered"] == v["n_pairs"]
        assert rec["n_refined"] == v["n_refined_here"]
        assert rec["n_surviving"] == v["n_surviving"]
        assert rec["n_separated"] == v["n_separated_by_refinement"]

    def test_the_classification_matches(self, state, recount) -> None:
        rec, v = state["addendum"], recount["verdict"]
        assert rec["classification"] == v["classification_over_the_surviving_set"]
        assert rec["flipped"] == v["flipped"]
        assert rec["fraction_below_the_floor_barrier"] == pytest.approx(
            v["fraction_below_floor_here"])
        assert rec["median_in_floor_units"] == pytest.approx(
            v["median_in_floor_units"])

    def test_the_controls_are_recorded_and_passed(self, refine, recount) -> None:
        assert refine["reproduction_control"]["all_identical"] is True, (
            "the three pairs generation 6 refined did not reproduce through "
            "this code path, so the ten new ones are not commensurate with them")
        assert refine["reproduction_control"]["all_verdicts_agree"] is True
        assert refine["negative_control"]["passes"] is True, (
            "the null-control pair was reported as surviving refinement; a "
            "battery that cannot separate two distinguishable devices cannot "
            "evidence that a witness pair is inseparable")
        assert recount["reproduction_control"]["all_identical"] is True, (
            "the thirteen barrier depths did not reproduce generation 10's, so "
            "the recount is a new measurement rather than a recount")
        assert recount["self_consistency"]["all_identical"] is True

    def test_the_recount_used_the_registered_criterion(self, recount) -> None:
        g10 = json.loads((ROOT / "outputs" / "g10" / "preregister.json").read_text(
            encoding="utf-8"))
        assert (recount["criterion"]["criterion_hash"]
                == g10["barrier_criterion"]["criterion_hash"])
        assert (recount["decision"]["decision_hash"]
                == g10["ridge_basin_decision"]["decision_hash"])

    def test_the_reading_was_registered_before_the_run(self, recount) -> None:
        prereg = json.loads((RUN / "preregister.json").read_text(
            encoding="utf-8"))
        v = recount["verdict"]
        assert v["outcomes_hash"] == prereg["outcomes"]["outcomes_hash"], (
            "the outcome table moved between pre-registration and reporting, "
            "so the reading is post-hoc whatever it says")
        assert v["reading"] == prereg["outcomes"]["table"][
            v["classification_over_the_surviving_set"]]

    def test_the_register_reports_what_the_state_file_says(self, state) -> None:
        reg = json.loads(REGISTER_V2.read_text(encoding="utf-8"))
        g = reg["sets"]["chart_G_d4"]
        assert g["compliant"] is True
        assert g["n_refined"] == state["addendum"]["n_refined"]
        assert g["n_surviving"] == state["addendum"]["n_surviving"]
        assert reg["verdict"]["non_compliant"] == ["chart_L_d16"]


class TestWhatIsNotClosedStaysOpen:
    """A bounded run must not be recorded as having settled more than it did."""

    def test_witness_04_is_narrowed_not_resolved(self, state) -> None:
        ids = {f["id"]: f for f in state["open_findings"]}
        assert "WITNESS-04" in ids
        status = ids["WITNESS-04"]["status"].upper()
        assert "RESOLVED" not in status, (
            "WITNESS-04 is that a committed witness set has never been "
            "refined. Chart L, at 0 of 37, still has not been")
        assert "chart L" in ids["WITNESS-04"]["note"] or \
            "chart_L" in ids["WITNESS-04"]["note"]

    def test_path_01_is_untouched(self, state) -> None:
        ids = {f["id"]: f for f in state["open_findings"]}
        assert "PATH-01" in ids
        assert "RESOLVED" not in ids["PATH-01"]["status"].upper(), (
            "refining witnesses does not compute a minimum-energy path; the "
            "barrier is still an upper bound")

    def test_mech_01_is_untouched(self, state) -> None:
        ids = {f["id"]: f for f in state["open_findings"]}
        assert "MECH-01" in ids
        assert "RESOLVED" not in ids["MECH-01"]["status"].upper()

    def test_the_prohibitions_are_carried_forward(self, state) -> None:
        joined = " ".join(state["not_supported_and_not_to_be_written"]).lower()
        assert "separation" in joined and "upper" in joined
        assert "minimum-energy" in joined or "minimum energy" in joined


class TestTheBaselineIsHonestAboutItsFailures:
    """`CI-01` in miniature: a green number over a suite that is not green."""

    def test_the_pytest_baseline_records_its_failures(self, state) -> None:
        p = state["baselines"]["pytest"]
        assert "failed" in p, "the pytest baseline does not record a failure count"
        if p["failed"]:
            assert p.get("failures_are"), (
                "the baseline records failures and does not say which they are "
                "or why they are not this run's doing")

    def test_the_pre_existing_failures_are_attributed(self, state) -> None:
        ids = {f["id"] for f in state["open_findings"]}
        assert "HIST-01" in ids, (
            "eight guards fail in this clone because the commit hashes the "
            "state files record are not in its object graph. A baseline that "
            "carries the failures and no finding explaining them leaves the "
            "next reader to rediscover it")

    def test_the_counts_add_up(self, state) -> None:
        p = state["baselines"]["pytest"]
        assert (p["passed"] + p["skipped"] + p["failed"]) == p["collected"], (
            "passed + skipped + failed does not equal collected, so at least "
            "one of the four numbers was not read off the same run")


class TestTheGuardStillHasBothControls:
    """`SW-20`: a positive case the guard must catch, and a negative it must not."""

    def test_the_baseline_predicate_rejects_a_bare_scalar(self) -> None:
        assert baseline_offenders({"pytest": 812}), (
            "REP-01's predicate accepted a bare integer, so it no longer "
            "distinguishes a record from a number")

    def test_the_baseline_predicate_accepts_a_full_record(self) -> None:
        good = {"pytest": {"invocation": "python -m pytest tests -q",
                           "collected": 870, "rerunnable": True}}
        assert not baseline_offenders(good)

    def test_the_addendum_document_is_on_the_claim_surface(self) -> None:
        from test_claim_surface_g7 import CLAIM_SURFACE_G7
        assert "docs/CLOSE_ADDENDUM.md" in CLAIM_SURFACE_G7, (
            "the addendum publishes the coverage and the recounted ridge; a "
            "document that states the result and is not guarded is unguarded")
