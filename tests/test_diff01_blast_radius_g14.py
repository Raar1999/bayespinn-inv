"""``DIFF-01``: a mechanical edit states its blast radius before it runs.

The defect that forced it
-------------------------
The ``EOL-02`` enactment's first pass changed **9,832 lines to fix 68** — 145x
its own intent — by adding the keyword correctly at every site and then writing
every file back through Python's text mode, normalising 25 CRLF files to LF.
``.gitattributes`` is ``* -text``, so that mixture is the committed truth.

**The suite was green before the sweep and green after it.** Every file was
individually correct; the damage existed only in aggregate. A reviewer reading
the diffstat caught it, which is a person, not a mechanism.

What the rule requires
----------------------
    Any mechanical or sweep edit states its expected changed-line count before
    it runs. A result exceeding the expectation by more than 2x halts the edit
    and is reported, regardless of whether the suite is green. Applies to
    normalisations, codemods, and rule enactments — the three places where
    correct-per-file and catastrophic-in-aggregate are the same operation.

How this guard makes that self-enforcing rather than declarative
----------------------------------------------------------------
A register nobody updates guards nothing. ``SKIP-01`` avoids that by comparing
its register against the skips the suite actually emits; there is no equivalent
signal for "a sweep happened", so this guard manufactures one from git: a commit
touching at least ``sweep_shaped_files_changed`` files **is** sweep-shaped, and
must appear in the register by subject. Hand edits are deep and narrow; codemods
are shallow and wide, and the file count is that signature.

Scope follows ``DOC-07``'s own design: commits before the enactment commit are
out of scope, because ``R-4`` makes history uncorrectable and a guard that fails
on history nobody can fix is a guard people switch off. The generation-13
``EOL-02`` sweep is registered as the founding entry and is used here as the
**positive control from history** — the guard must identify it as sweep-shaped,
and if it stops doing so the detector has gone vacuous.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "SWEEP_REGISTER.json"

#: The generation-13 sweep. Its subject is stable across a filter-repo rename,
#: which its SHA would not be -- ``HIST-01``'s lesson.
POSITIVE_CONTROL_SUBJECT = (
    "g13: EOL-02 -- every text-mode write states its line ending")

REQUIRED_FIELDS = (
    "id", "generation", "kind", "description",
    "expected_changed_lines", "expected_stated_before_running",
    "actual_changed_lines", "ratio", "outcome",
)


def register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def _in_a_checkout() -> bool:
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(ROOT),
                       capture_output=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=str(ROOT),
                         capture_output=True, timeout=120)
    assert out.returncode == 0, f"git {' '.join(args)} failed"
    return out.stdout.decode("utf-8", "replace")


def files_changed(sha: str) -> int:
    txt = _git("show", "--name-only", "--pretty=format:", sha)
    return len({ln for ln in txt.splitlines() if ln.strip()})


def sha_of_subject(subject: str):
    out = _git("log", "--all", "--format=%H%x00%s")
    for line in out.splitlines():
        if "\x00" not in line:
            continue
        sha, subj = line.split("\x00", 1)
        if subj.strip() == subject:
            return sha
    return None


def over_threshold(entry: dict, halt_ratio: float) -> bool:
    """A sweep whose result exceeded its stated expectation by more than 2x."""
    exp = entry["expected_changed_lines"]
    act = entry["actual_changed_lines"]
    return exp > 0 and (act / exp) > halt_ratio


class TestTheRegisterIsWellFormed:

    def test_every_entry_carries_the_fields_its_kind_needs(self):
        for e in register()["entries"]:
            assert e["kind"] in register()["kinds"], (
                f"{e.get('id')}: unknown kind {e['kind']!r}")
            if e["kind"] == "mechanical":
                missing = [f for f in REQUIRED_FIELDS if f not in e]
                assert not missing, f"{e.get('id')}: missing {missing}"
            else:
                assert e.get("why_not_mechanical"), (
                    f"{e['id']}: a non-mechanical entry must say why it is "
                    f"here, or the trigger becomes a rubber stamp")
                assert e.get("commit_subject"), f"{e['id']}: no commit_subject"

    def test_a_non_mechanical_entry_cannot_smuggle_a_sweep_through(self):
        """The obvious way to defeat the rule is to relabel a codemod.

        The kind is a declaration, so nothing can verify it directly. What is
        verified is that a non-mechanical entry claiming changed-line counts
        must still satisfy the ratio -- so relabelling a sweep buys nothing
        unless its accounting is also withheld, which the field requirement
        above makes visible.
        """
        halt = register()["thresholds"]["halt_ratio"]
        for e in register()["entries"]:
            if e["kind"] == "mechanical":
                continue
            if "expected_changed_lines" in e and "actual_changed_lines" in e:
                assert not over_threshold(e, halt), (
                    f"{e['id']}: declared non-mechanical but overran its own "
                    f"stated expectation")

    def test_every_expectation_was_stated_before_the_edit_ran(self):
        """The whole rule. An expectation written afterwards is a description."""
        for e in register()["entries"]:
            if e["kind"] != "mechanical":
                continue
            assert e["expected_stated_before_running"] is True, (
                f"{e['id']}: an expectation recorded after the fact is not an "
                f"expectation")
            assert e.get("expected_basis"), (
                f"{e['id']}: an expectation with no stated basis is a guess")

    def test_the_recorded_ratio_matches_the_recorded_counts(self):
        for e in register()["entries"]:
            if e["kind"] != "mechanical":
                continue
            got = e["actual_changed_lines"] / e["expected_changed_lines"]
            assert abs(got - e["ratio"]) <= 0.05 * max(1.0, e["ratio"]), (
                f"{e['id']}: ratio {e['ratio']} does not match "
                f"{e['actual_changed_lines']}/{e['expected_changed_lines']}")

    def test_an_overrun_halted_and_was_reported(self):
        reg = register()
        halt = reg["thresholds"]["halt_ratio"]
        for e in reg["entries"]:
            if e["kind"] != "mechanical" or not over_threshold(e, halt):
                continue
            assert e["outcome"] == "HALTED", (
                f"{e['id']}: exceeded the expectation by "
                f"{e['ratio']}x and did not halt")
            assert e.get("committed") is False, (
                f"{e['id']}: a halted edit must not have been committed")
            assert e.get("reported_in"), (
                f"{e['id']}: a halted edit must name where it was reported")

    def test_a_completed_entry_is_within_the_threshold(self):
        reg = register()
        halt = reg["thresholds"]["halt_ratio"]
        for e in reg["entries"]:
            if e.get("outcome") != "COMPLETED":
                continue
            assert not over_threshold(e, halt), (
                f"{e['id']}: completed at {e['ratio']}x, above the threshold")


class TestTheGuardControls:
    """``SW-20``'s purpose: shown to fire, and shown not to fire on a description."""

    def test_it_catches_a_planted_overrun(self):
        """Positive control: an overrun that did not halt."""
        planted = {
            "id": "planted", "generation": 99, "kind": "mechanical",
            "description": "a codemod that ran away",
            "expected_changed_lines": 50, "expected_stated_before_running": True,
            "expected_basis": "50 sites", "actual_changed_lines": 5000,
            "ratio": 100.0, "outcome": "COMPLETED", "committed": True,
        }
        assert over_threshold(planted, 2.0), "the detector did not fire"
        with pytest.raises(AssertionError):
            _assert_entry_ok(planted, 2.0)

    def test_it_does_not_fire_on_an_edit_that_stayed_within_its_estimate(self):
        """Negative control: a sweep that behaved is not an incident.

        Without this the guard could reject everything and still look correct.
        """
        ok = {
            "id": "well-behaved", "generation": 99, "kind": "mechanical",
            "description": "a codemod that did what it said",
            "expected_changed_lines": 68, "expected_stated_before_running": True,
            "expected_basis": "68 sites", "actual_changed_lines": 71,
            "ratio": 1.04, "outcome": "COMPLETED", "committed": True,
        }
        assert not over_threshold(ok, 2.0)
        _assert_entry_ok(ok, 2.0)

    def test_the_threshold_is_a_ratio_and_not_a_line_count(self):
        """A small edit that doubles is an incident; a large one that does not is not.

        The rule is about blast radius relative to intent, so a guard keyed to an
        absolute line count would miss the small-but-runaway case entirely.
        """
        small_runaway = {"expected_changed_lines": 3, "actual_changed_lines": 40}
        large_behaved = {"expected_changed_lines": 4000,
                         "actual_changed_lines": 4200}
        assert over_threshold(small_runaway, 2.0)
        assert not over_threshold(large_behaved, 2.0)


def _assert_entry_ok(entry: dict, halt_ratio: float) -> None:
    if over_threshold(entry, halt_ratio):
        assert entry["outcome"] == "HALTED", (
            f"{entry['id']}: exceeded the expectation and did not halt")
        assert entry.get("committed") is False


@pytest.mark.skipif(not _in_a_checkout(), reason="not run from a git checkout")
class TestSweepShapedCommitsAreRegistered:

    def test_the_positive_control_is_still_detected_as_sweep_shaped(self):
        """The generation-13 sweep. If this stops firing, the detector is vacuous."""
        sha = sha_of_subject(POSITIVE_CONTROL_SUBJECT)
        assert sha, "the EOL-02 sweep commit is not reachable; control lost"
        n = files_changed(sha)
        thr = register()["thresholds"]["sweep_shaped_files_changed"]
        assert n >= thr, (
            f"the EOL-02 sweep touched {n} files, below the sweep-shaped "
            f"threshold of {thr}; the detector would not have seen it")

    def test_it_is_in_the_register(self):
        subjects = {e.get("commit_subject") for e in register()["entries"]}
        assert POSITIVE_CONTROL_SUBJECT in subjects

    def test_every_sweep_shaped_commit_since_enactment_is_registered(self):
        """The rule, made self-enforcing.

        Scope is the enactment commit forward. Before it, ``R-4`` applies and a
        guard that fails on uncorrectable history gets switched off.
        """
        reg = register()
        thr = reg["thresholds"]["sweep_shaped_files_changed"]
        enacted = sha_of_subject(reg["enacted_at_subject"])
        if enacted is None:
            pytest.skip("DIFF-01 enactment commit not yet in history")
        known = {e.get("commit_subject") for e in reg["entries"]}
        unregistered = []
        for line in _git("log", "--format=%H%x00%s",
                         f"{enacted}~1..HEAD").splitlines():
            if "\x00" not in line:
                continue
            sha, subj = line.split("\x00", 1)
            subj = subj.strip()
            if subj in known:
                continue
            if files_changed(sha) >= thr:
                unregistered.append(f"{sha[:12]} {subj}")
        assert not unregistered, (
            "DIFF-01: sweep-shaped commits with no register entry:\n  "
            + "\n  ".join(unregistered))
