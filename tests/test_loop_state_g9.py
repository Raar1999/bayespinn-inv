"""``REP-01`` applied forward: every number in the state file carries its invocation.

The defect that forced it
-------------------------
``LOOP_STATE_v5.json`` recorded ``"ruff_exit": 0``. No scope, no command. The two
defensible scopes disagreed at the time it was written -- ``ruff check .`` exited
**1** with findings in ``notebooks/``, ``ruff check src tests scripts`` exited
**0** -- so one verdict was recorded and two existed, and nothing in the file
said which.

The field beside it was meant to be the good example and is not quite one either.
``"mypy_findings": 25`` came with the note *"25 over the tracked tree"*. That
scope is wrong: 25 is what ``mypy src`` reports over 44 files; over the tracked
tree, ``mypy src tests scripts`` over 112 files, it is 150. The number was right
and its description was not, which is the whole argument for recording a
**command** rather than a **characterisation** -- a command can be re-run, a
description can only be re-read.

What this guard asserts
-----------------------
1. ``baselines`` maps a name to an **object**, never to a bare scalar;
2. every object carries a non-empty ``invocation``;
3. every object carries at least one number, because a record with no number is
   not a baseline;
4. for records marked ``rerunnable``, the invocation is **actually run** and the
   recorded verdict must match what it returns today, so a baseline goes stale
   loudly rather than quietly;
5. for records that cannot be re-run inside a test -- the suite's own wall
   clock, which cannot measure itself -- ``conditions`` and
   ``measured_at_commit`` are required instead, and ``conditions`` may not be
   empty. A timing number without its conditions is the same defect wearing a
   stopwatch, and it is the specific defect the ruling of 2026-08-26 section 3
   names against the generation-8 report.

``SW-20``: the subject is a JSON document, so there is no AST of ours to walk.
Both controls are implemented -- ``test_the_guard_catches_a_planted_bare_number``
plants the exact ``"ruff_exit": 0`` shape and requires rejection, and
``test_the_guard_does_not_fire_on_a_well_formed_block`` together with
``test_prose_about_invocations_is_not_an_invocation`` are the negative controls
-- and this module's own source is not part of the scanned document.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v6.json"

pytestmark = pytest.mark.skipif(
    not STATE.is_file(),
    reason="LOOP_STATE_v6.json is written by the generation-9 state commit")


def git(*args):
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def baseline_offenders(baselines):
    """Every way a baseline record can fail to carry its own invocation."""
    offenders = []
    for name, rec in baselines.items():
        if not isinstance(rec, dict):
            offenders.append(f"{name}: bare {type(rec).__name__}, not a record "
                             "carrying an invocation")
            continue
        inv = rec.get("invocation")
        if not isinstance(inv, str) or not inv.strip():
            offenders.append(f"{name}: no invocation")
            continue
        numbers = [k for k, v in rec.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)]
        lists = [k for k, v in rec.items() if isinstance(v, list)
                 and any(isinstance(x, (int, float)) for x in v)]
        if not numbers and not lists:
            offenders.append(f"{name}: an invocation and no number")
        if not rec.get("rerunnable", False):
            for field in ("conditions", "measured_at_commit"):
                val = rec.get(field)
                if not isinstance(val, str) or not val.strip():
                    offenders.append(
                        f"{name}: not rerunnable and carries no {field}")
    return offenders


class TestTheFixedPointIsStillDefinedAway:
    """Inherited from generation 8. The invariant did not stop applying."""

    def test_champion_is_not_the_commit_that_wrote_this_file(self, state):
        writer = git("log", "-1", "--format=%H", "--", STATE.name)
        assert writer, "git could not name the commit that wrote the state file"
        assert state["champion_commit"] != writer, (
            "champion_commit names the commit that wrote this file, which is "
            "the fixed point generation 7 walked into: the file's bytes are "
            "part of the tree that commit hashes")

    def test_bookkeeping_commit_is_null_at_write_time(self, state):
        assert state["bookkeeping_commit"] is None

    def test_the_champion_is_a_real_reachable_commit(self, state):
        assert git("cat-file", "-t", state["champion_commit"]) == "commit"

    def test_the_machinery_commit_is_real_and_is_not_the_champion(self, state):
        assert git("cat-file", "-t", state["machinery_commit"]) == "commit"
        assert state["machinery_commit"] != state["champion_commit"], (
            "one tree, one commit: every measurement ran against the machinery "
            "commit and the results were written afterwards, so the two cannot "
            "be the same commit")


class TestEveryBaselineNumberCarriesItsInvocation:
    """``REP-01`` as amended by the ruling of 2026-08-26 section 3."""

    def test_the_baseline_block_is_well_formed(self, state):
        offenders = baseline_offenders(state["baselines"])
        assert not offenders, (
            "REP-01 (generation-9 amendment): a number in a state file without "
            "the command that produced it cannot be checked, only believed:\n  "
            + "\n  ".join(offenders))

    def test_the_guard_catches_a_planted_bare_number(self):
        """Positive control: the exact generation-8 shape must be rejected."""
        assert baseline_offenders({"ruff_exit": 0})

    def test_the_guard_catches_a_record_with_no_number(self):
        assert baseline_offenders(
            {"ruff": {"invocation": "ruff check .", "rerunnable": True}})

    def test_prose_about_invocations_is_not_an_invocation(self):
        """Negative control: a note *describing* the rule does not satisfy it."""
        assert baseline_offenders({"mypy": {
            "note": "measured with the usual invocation over the tracked tree",
            "findings": 25}})

    def test_a_timing_number_without_its_conditions_is_rejected(self):
        """The ruling's own example: a wall clock compared under load."""
        assert baseline_offenders({"pytest": {
            "invocation": "python -m pytest tests -q",
            "wall_clock_s": 378.11, "rerunnable": False,
            "measured_at_commit": "0f22ecc"}})

    def test_the_guard_does_not_fire_on_a_well_formed_block(self):
        """Negative control: the shape the rule asks for must pass."""
        assert not baseline_offenders({
            "ruff_whole_tree": {"invocation": "ruff check .", "exit_code": 0,
                                "findings": 0, "rerunnable": True},
            "pytest": {"invocation": "python -m pytest tests -q",
                       "collected": 709, "wall_clock_s": 300.0,
                       "rerunnable": False,
                       "conditions": "no other job on the machine",
                       "measured_at_commit": "deadbeef"},
        })


class TestTheRecordedInvocationsStillReturnWhatIsRecorded:
    """A baseline that is never re-run is a claim. These are re-run."""

    @staticmethod
    def _run(invocation: str) -> subprocess.CompletedProcess:
        args = invocation.split()
        if args[0] in ("ruff", "mypy", "pytest"):
            args = [sys.executable, "-m", *args]
        return subprocess.run(args, capture_output=True, text=True,
                              cwd=str(ROOT), timeout=600)

    def test_every_rerunnable_baseline_still_holds(self, state):
        stale = []
        for name, rec in state["baselines"].items():
            if not rec.get("rerunnable", False):
                continue
            proc = self._run(rec["invocation"])
            if "exit_code" in rec and proc.returncode != rec["exit_code"]:
                stale.append(f"{name}: {rec['invocation']!r} recorded exit "
                             f"{rec['exit_code']}, returned {proc.returncode}")
        assert not stale, (
            "a recorded baseline no longer describes this tree:\n  "
            + "\n  ".join(stale))

    def test_the_mypy_counts_hold_for_the_recorded_version(self, state):
        """Version-gated on purpose.

        A finding count moves with the analyser, and a guard that fails when
        somebody upgrades mypy is a guard that gets deleted. So the comparison
        runs only when the installed version is the one the baseline names, and
        says so out loud when it does not, rather than passing silently.
        """
        import re
        for name, rec in state["baselines"].items():
            if not name.startswith("mypy"):
                continue
            got = self._run("mypy --version").stdout.strip()
            if rec.get("tool_version") not in got:
                pytest.skip(f"{name}: baseline recorded for "
                            f"{rec.get('tool_version')!r}, installed {got!r}")
            out = self._run(rec["invocation"]).stdout
            m = re.search(r"Found (\d+) errors? in \d+ files? "
                          r"\(checked (\d+) source files?\)", out)
            assert m, f"{name}: could not parse mypy output\n{out[-400:]}"
            assert int(m.group(1)) == rec["findings"], (
                f"{name}: recorded {rec['findings']} findings, "
                f"{rec['invocation']!r} now reports {m.group(1)}. A new module "
                "that is not clean under this invocation is a finding, not a "
                "baseline drift.")
            # The file count is scope, and scope legitimately GROWS: adding a
            # module adds a file. It must never shrink unnoticed, though --
            # a scan that quietly stopped covering part of the tree is how an
            # advertised guarantee becomes an unmeasured one, which is CI-01's
            # whole shape. So the direction is asserted and the equality is not.
            assert int(m.group(2)) >= rec["files_checked"], (
                f"{name}: recorded {rec['files_checked']} files at "
                f"{rec['measured_at_commit'][:7]}, {rec['invocation']!r} now "
                f"checks only {m.group(2)}. The scope shrank.")


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
                f"{f['id']} is ACCEPTED-PERMANENT and owes a cost statement; "
                "the status is what keeps the cost visible, and without one it "
                "is a closed finding under another name")
            assert "cost_grown_since_assignment" in f, (
                f"{f['id']}: the status requires the cost to be reviewed each "
                "generation for growth, so the review is recorded rather than "
                "remembered")

    def test_ci01_is_the_reclassification_the_ruling_defaulted_to(self, state):
        ci = next(f for f in state["open_findings"] if f["id"] == "CI-01")
        assert ci["status"] == "ACCEPTED-PERMANENT", (
            "the generation-8 decision went unanswered for three cycles and "
            "the ruling's stated default fired at generation 9 section 4")

    def test_the_not_to_be_written_list_survives(self, state):
        assert len(state["not_supported_and_not_to_be_written"]) >= 8
