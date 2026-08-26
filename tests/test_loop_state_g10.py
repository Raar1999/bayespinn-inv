"""``LOOP_STATE_v7.json``: the generation-10 state file, guarded the same way.

Generation 9 built the guard; this module points it at the new file and adds the
invariants generation 10 introduces. It deliberately **imports**
``baseline_offenders`` from ``tests/test_loop_state_g9.py`` rather than restating
it: ``REP-01`` has one definition, and two copies of a rule drift into two rules.

What is new here, beyond the inherited invariants
-------------------------------------------------
``TestEveryPreRegisteredHashIsRecoverable``
    generation 10 turns on four hashed objects -- the localisation measure, the
    ridge/basin decision table, the ``WIT-01`` admissibility rule and generation
    9's barrier criterion. Each is re-derived here from the code that defines it
    and compared against what ``outputs/g10/preregister.json`` recorded. A
    pre-registration nobody can recompute is a timestamp, not a commitment.

``TestTheBarrierCriterionIsLiterallyGenerationNines``
    ``SPEC-g10-2`` compares three witness sets. That is one ruler only if the
    metric is one object, so the hash generation 9 registered and the hash
    generation 10 registered must be equal -- and the equality is asserted here
    rather than in prose.

``SW-20``: the subject is a JSON document; both controls live in the imported
module and in :class:`TestTheGuardStillHasBothControls` below, and this module's
own source is not part of the scanned document.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_loop_state_g9 import baseline_offenders

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v7.json"
G10 = ROOT / "outputs" / "g10"
G9_PRE = ROOT / "outputs" / "g9" / "preregister.json"

pytestmark = pytest.mark.skipif(
    not STATE.is_file(),
    reason="LOOP_STATE_v7.json is written by the generation-10 state commit")


def git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def _prereg():
    p = G10 / "preregister.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


class TestTheFixedPointIsStillDefinedAway:
    """Inherited. The invariant did not stop applying at generation 10."""

    def test_champion_is_not_the_commit_that_wrote_this_file(self, state):
        writer = git("log", "-1", "--format=%H", "--", STATE.name)
        assert writer, "git could not name the commit that wrote the state file"
        assert state["champion_commit"] != writer, (
            "champion_commit names the commit that wrote this file; a state "
            "file cannot name its own commit, because its bytes are part of the "
            "tree that commit hashes")

    def test_bookkeeping_commit_is_null_at_write_time(self, state):
        assert state["bookkeeping_commit"] is None

    def test_the_champion_is_a_real_reachable_commit(self, state):
        assert git("cat-file", "-t", state["champion_commit"]) == "commit"

    def test_the_machinery_commit_is_real_and_is_not_the_champion(self, state):
        assert git("cat-file", "-t", state["machinery_commit"]) == "commit"
        assert state["machinery_commit"] != state["champion_commit"], (
            "one tree, one commit: every measurement ran against the machinery "
            "commit and the results were written afterwards")


class TestEveryBaselineNumberCarriesItsInvocation:
    """``REP-01`` as amended at generation 9, applied to the new file."""

    def test_the_baseline_block_is_well_formed(self, state):
        offenders = baseline_offenders(state["baselines"])
        assert not offenders, (
            "REP-01: a number in a state file without the command that "
            "produced it cannot be checked, only believed:\n  "
            + "\n  ".join(offenders))

    def test_the_mypy_baseline_carries_its_scope(self, state):
        """The generation-9 correction, kept from silently reverting.

        ``25`` is ``mypy src`` over 44 files. The tracked tree gives 150. Nine
        generations carried the first number under the second description, so
        both scopes are recorded and both are required to stay recorded.
        """
        names = set(state["baselines"])
        assert {"mypy_package", "mypy_tracked_tree"} <= names, (
            "a mypy baseline is present without both scopes; that is the exact "
            "shape of the defect generation 9 corrected")


class TestEveryPreRegisteredHashIsRecoverable:
    """A pre-registration nobody can recompute is a timestamp."""

    @staticmethod
    def _objects():
        sys.path.insert(0, str(ROOT / "scripts"))
        sys.path.insert(0, str(ROOT / "src"))
        from run_g9 import BarrierCriterion
        from run_g10 import LocalisationMeasure, RidgeBasinDecision

        from bayespinn_inv.inverse.witness_admissibility import AdmissibilityRule
        return {
            "localisation_measure": (LocalisationMeasure(), "measure_hash"),
            "ridge_basin_decision": (RidgeBasinDecision(), "decision_hash"),
            "witness_admissibility_rule": (AdmissibilityRule(), "rule_hash"),
            "barrier_criterion": (BarrierCriterion(), "criterion_hash"),
        }

    def test_every_registered_hash_recomputes(self):
        pre = _prereg()
        if pre is None:
            pytest.skip("outputs/g10/preregister.json not written yet")
        for key, (obj, attr) in self._objects().items():
            assert pre[key][attr] == getattr(obj, attr)(), (
                f"{key} no longer hashes to the value it was registered with. "
                "AH-14: either the rule moved after the measurement, or the "
                "measurement is being read against a different rule.")

    def test_the_hashes_are_distinct(self):
        """Four rules, four hashes. Equal hashes would mean one object twice."""
        pre = _prereg()
        if pre is None:
            pytest.skip("outputs/g10/preregister.json not written yet")
        hashes = {k: pre[k][a] for k, (_, a) in self._objects().items()}
        assert len(set(hashes.values())) == len(hashes), hashes


class TestTheBarrierCriterionIsLiterallyGenerationNines:
    """Three witness sets compared through one metric, or not compared at all."""

    def test_the_two_generations_registered_the_same_criterion(self):
        pre = _prereg()
        if pre is None or not G9_PRE.is_file():
            pytest.skip("both pre-registrations are needed for this comparison")
        g9 = json.loads(G9_PRE.read_text(encoding="utf-8"))
        assert (pre["barrier_criterion"]["criterion_hash"]
                == g9["barrier_criterion"]["criterion_hash"]), (
            "SPEC-g10-2 compares chart L at d=16 against generation 9's two "
            "sets. If the barrier criterion moved between the generations, the "
            "comparison is between two rulers and the clause is void.")

    def test_the_reproduction_control_passed(self):
        p = G10 / "ridge_basin.json"
        if not p.is_file():
            pytest.skip("outputs/g10/ridge_basin.json not measured yet")
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("dropped_whole"):
            pytest.skip("SPEC-g10-2 was dropped whole by its pilot")
        rc = doc["reproduction_control"]
        assert rc["all_reproduce"], (
            "re-measuring generation 9's two witness sets through generation "
            "10's code did not return generation 9's numbers:\n"
            + json.dumps(rc["rows"], indent=2))


class TestTheStateFileIsInternallyConsistent:

    def test_this_generations_champion_matches_the_pointer(self, state):
        gen = f"g{state['generation']}"
        assert state["champion_per_generation"][gen] == state["champion_commit"]

    def test_every_open_finding_has_a_severity_and_a_status(self, state):
        for f in state["open_findings"]:
            assert f.get("severity") and f.get("status"), f

    def test_a_permanently_accepted_finding_owes_a_cost_statement(self, state):
        for f in state["open_findings"]:
            if f["status"] != "ACCEPTED-PERMANENT":
                continue
            assert f.get("cost_statement"), (
                f"{f['id']} is ACCEPTED-PERMANENT and owes a cost statement")
            assert "cost_grown_since_assignment" in f, (
                f"{f['id']}: the status requires the cost to be reviewed each "
                "generation for growth, so the review is recorded")

    def test_the_not_to_be_written_list_survives(self, state):
        assert len(state["not_supported_and_not_to_be_written"]) >= 8

    def test_every_spec_clause_of_this_generation_has_a_status(self, state):
        for clause in ("SPEC-g10-1", "SPEC-g10-2", "SPEC-g10-3",
                       "SPEC-g10-negative-control", "WIT-01"):
            assert clause in state["spec_clause_status"], (
                f"{clause} was ordered and its outcome is not recorded; a "
                "clause with no status is a clause that was quietly dropped")


class TestTheGuardStillHasBothControls:
    """``SW-20``, checked rather than asserted."""

    def test_the_imported_predicate_catches_a_planted_bare_number(self):
        assert baseline_offenders({"ruff_exit": 0})

    def test_the_imported_predicate_passes_a_well_formed_record(self):
        assert not baseline_offenders({
            "ruff_whole_tree": {"invocation": "ruff check .", "exit_code": 0,
                                "findings": 0, "rerunnable": True}})
