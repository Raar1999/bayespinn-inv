"""``LOOP_STATE_v8.json``: the closing state file, guarded the same way.

Generation 9 built the guard, generation 10 pointed it at its own file, and this
module points it at the closing one. It **imports** ``baseline_offenders`` from
``tests/test_loop_state_g9.py`` rather than restating it: ``REP-01`` has one
definition, and two copies of a rule drift into two rules.

What is new here, beyond the inherited invariants
-------------------------------------------------
``TestTheCloseIsRecordedAsAClose``
    a closing state file has obligations a generation's does not. It must say
    that no generation follows it, it must not open a specification clause, and
    the free check it does record must be marked as arithmetic over existing
    artefacts rather than as a measurement.

``TestWhatTheCloseChangedIsInTheFile``
    ``WIT-02`` and the search-form rewrite each removed something from the
    supportable set. A state file that carries the new rule but not the
    prohibitions it implies would leave the claim surface freer than the ruling
    left it, which is the direction that matters.

``TestTheProhibitionListStillBites``
    ``not_supported_and_not_to_be_written`` is only worth anything if the
    documents obey it. The two entries this close adds are checked against the
    claim surface through the same predicates the other guards use.

``SW-20``: the subject is a JSON document; this module's own source is not part
of the scanned document, and both controls live in the imported module and in
:class:`TestTheGuardStillHasBothControls`.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest
from test_loop_state_g9 import baseline_offenders

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v8.json"
PREVIOUS = ROOT / "LOOP_STATE_v7.json"
CLOSE = ROOT / "outputs" / "close"

pytestmark = pytest.mark.skipif(
    not STATE.is_file(),
    reason="LOOP_STATE_v8.json is written by the closing state commit")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


class TestTheFixedPointIsStillDefinedAway:
    """Inherited. The invariant did not stop applying because the loop closed."""

    def test_champion_is_not_the_commit_that_wrote_this_file(self, state) -> None:
        writer = git("log", "-1", "--format=%H", "--", STATE.name)
        assert writer, "git could not name the commit that wrote the state file"
        assert state["champion_commit"] != writer, (
            "champion_commit names the commit that wrote this file; a state "
            "file cannot name its own commit, because its bytes are part of "
            "the tree that commit hashes")

    def test_bookkeeping_commit_is_null_at_write_time(self, state) -> None:
        assert state["bookkeeping_commit"] is None

    def test_the_champion_is_a_real_reachable_commit(self, state) -> None:
        assert git("cat-file", "-t", state["champion_commit"]) == "commit"

    def test_the_machinery_commit_is_real(self, state) -> None:
        assert git("cat-file", "-t", state["machinery_commit"]) == "commit"


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
        assert now["invocation"] == before["invocation"], (
            "the carried mypy baseline changed scope between the two files; a "
            "count is only comparable against the same invocation")
        assert now["files_checked"] >= before["files_checked"], (
            "the tracked-tree scan shrank, so the finding count is not "
            "comparable with generation 10's")
        assert now["findings"] <= before["findings"], (
            "the carried mypy baseline grew; the ruling of 2026-08-26 section 4 "
            "made this the baseline precisely so it could not")


class TestTheCloseIsRecordedAsAClose:

    def test_it_says_no_generation_follows(self, state) -> None:
        assert state["terminated"] is True
        assert state.get("closed") is True, (
            "the closing state file must record that the loop is closed, not "
            "only that T-1 was reached; every file since generation 6 says the "
            "second thing and four bounded generations followed anyway")
        assert re.search(r"no generation 11|generation 11", state["designation"],
                         re.I)

    def test_it_opens_no_specification_clause(self, state) -> None:
        opened = [k for k in state["spec_clause_status"]
                  if k.lower().startswith(("spec-g11", "spec-close"))]
        assert not opened, (
            "the closing ruling permits one arithmetic check and no new "
            "scope; these clauses open scope: " + ", ".join(opened))

    def test_the_free_check_is_recorded_as_arithmetic(self, state) -> None:
        fc = state["free_check"]
        assert fc["new_solves"] == 0
        assert fc["status"].startswith("DESCRIPTION"), (
            "the free check was ordered after the data existed; recording it "
            "as a test would claim a pre-registration that does not exist")
        for rel in fc["artefacts"]:
            assert (ROOT / rel).is_file(), rel + " is named and absent"
        assert fc["verdict"] in ("SHAPE", "SCALE", "NEITHER")

    def test_the_free_check_agrees_with_its_artefact(self, state) -> None:
        doc = json.loads((CLOSE / "spectrum_shape.json").read_text(
            encoding="utf-8"))
        assert state["free_check"]["verdict"] == doc["verdict"]["agreed"]
        assert doc["verdict"]["all_controls_pass"] is True

    def test_the_operator_tasks_are_carried_not_closed(self, state) -> None:
        joined = " ".join(state["operator_tasks"])
        for task in ("OT-1", "OT-2", "OT-3"):
            assert task in joined, (
                task + " is not carried in the closing state file. The loop may "
                "not close an operator task by closing itself")


class TestWhatTheCloseChangedIsInTheFile:

    def test_wit02_is_recorded_with_its_register(self, state) -> None:
        entry = state["spec_clause_status"].get("WIT-02")
        assert entry, "WIT-02 was enacted and the state file does not record it"
        assert "ENACTED" in entry.upper()
        reg = json.loads((CLOSE / "wit02_register.json").read_text(
            encoding="utf-8"))
        assert reg["verdict"]["non_compliant"], (
            "the register reports full compliance; either a refinement run "
            "happened, in which case the state file should say so, or the "
            "register is wrong")
        for label in reg["verdict"]["non_compliant"]:
            assert label.split("_")[1] in entry or label in entry, (
                "WIT-02's record does not name the non-compliant set " + label)

    def test_the_finding_for_the_unrefined_set_is_open(self, state) -> None:
        ids = {f["id"]: f for f in state["open_findings"]}
        assert "WITNESS-04" in ids
        assert "RESOLVED" not in ids["WITNESS-04"]["status"].upper(), (
            "WITNESS-04 is the finding that the chart-L witness set has never "
            "been refined. WIT-02 does not resolve it -- it registers it")

    def test_the_bound_direction_produced_a_prohibition(self, state) -> None:
        joined = " ".join(state["not_supported_and_not_to_be_written"]).lower()
        assert "separation" in joined and "upper" in joined, (
            "the closing ruling section 3 weakened both basin results to search "
            "statements. The state file must forbid the separation reading, or "
            "the weakening exists only in prose")
        assert "minimum-energy" in joined or "minimum energy" in joined, (
            "the test that was not run must be named in the prohibition, "
            "because AH-13 is about what a failed search does not show")


class TestTheProhibitionListStillBites:
    """A prohibition nothing obeys is decoration."""

    #: Documents the two new prohibitions are checked against.
    SURFACE = ("README.md", "docs/CLAIM_EVIDENCE_MATRIX.md",
               "docs/G10_RESULT.md", "docs/CLOSE_RULING.md")

    def test_no_document_calls_a_d16_result_a_separation(self) -> None:
        offenders: List[str] = []
        for rel in self.SURFACE:
            path = ROOT / rel
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not re.search(r"basin", line, re.I):
                    continue
                if re.search(r"separat(?:ed|ion|es)\b", line, re.I) and not \
                        re.search(r"not a separation|search statement|"
                                  r"not separation|rather than a separation|"
                                  r"separation proofs?|junction separation|"
                                  r"never a separation", line, re.I):
                    offenders.append(rel + ": " + line.strip()[:120])
        assert not offenders, (
            "a basin passage asserts separation without the search-form "
            "qualifier the closing ruling section 3 requires:\n  "
            + "\n  ".join(offenders))

    def test_the_guard_catches_a_planted_separation_claim(self) -> None:
        """`SW-20`'s positive control."""
        planted = ("Chart L at d=16 is a basin: its 37 witness pairs are "
                   "separated by a barrier 212x the floor.")
        assert re.search(r"basin", planted, re.I)
        assert re.search(r"separat(?:ed|ion|es)\b", planted, re.I)
        assert not re.search(r"not a separation|search statement", planted, re.I)

    def test_the_guard_passes_the_repaired_sentence(self) -> None:
        repaired = ("Chart L at d=16 is a basin: no connecting path below the "
                    "floor was found, which is a search statement and not a "
                    "separation proof.")
        assert re.search(r"search statement", repaired, re.I)

    def test_the_close_document_is_on_the_claim_surface(self) -> None:
        from test_claim_surface_g7 import CLAIM_SURFACE_G7
        assert "docs/CLOSE_RULING.md" in CLAIM_SURFACE_G7, (
            "the closing document publishes the spine and the free check; a "
            "document that states the result and is not guarded is unguarded")


class TestTheGuardStillHasBothControls:
    """`SW-20`: a guard over a document carries a positive and a negative case."""

    def test_the_baseline_predicate_rejects_a_bare_scalar(self) -> None:
        assert baseline_offenders({"pytest": 812}), (
            "REP-01's predicate accepted a bare integer, so it no longer "
            "distinguishes a record from a number")

    def test_the_baseline_predicate_accepts_a_full_record(self) -> None:
        good = {"pytest": {"invocation": "python -m pytest tests -q",
                           "collected": 870, "rerunnable": True}}
        assert not baseline_offenders(good)
