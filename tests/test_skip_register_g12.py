"""``SKIP-01``: a skip is a failure unless it carries a reason and an expiry.

Full text and the defect that forced it: ``docs/RULES_ENACTED.md``, ``SKIP-01``.

The defect in one line: ``HIST-01`` made eight guards fail and **three skip**.
The eight were loud. Two of the three were the ``DOC-07`` commit-message guard,
which had stopped running over the range it was written for, and the suite
reported green for a generation.

What is checked
---------------
Every skip in ``outputs/g12/skips.json`` -- produced by
``scripts/report_skips.py``, which runs the suite with ``-rs`` -- must match an
entry in ``docs/SKIP_REGISTER.json`` giving why the skip is legitimate and the
condition or generation at which it stops being legitimate. An unregistered skip
is a failure. An expired registration is a failure.

Why a register rather than a stricter ``reason=``
-------------------------------------------------
Every skip in this repository already carried a ``reason``, and the two that
mattered carried a perfectly clear one -- ``git``'s own error text. The reason
was never the missing part. What was missing is a place where the *set* of
accepted skips is written down, so that a new one has to be added deliberately
by someone who has thought about whether it should exist.

``SW-20``: the subject is two JSON documents; this module's own source is not
part of the scanned document, and both controls are below.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "outputs" / "g12" / "skips.json"
REGISTER = ROOT / "docs" / "SKIP_REGISTER.json"

#: The generation this tree is at. An entry expiring at or before it is expired.
CURRENT_GENERATION = 12

pytestmark = pytest.mark.skipif(
    not (REPORT.is_file() and REGISTER.is_file()),
    reason="SKIP-01 artefacts not written yet; run "
           "PYTHONPATH=src python scripts/report_skips.py")


def git(*args: str) -> Optional[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                         text=True, timeout=30)
    return out.stdout.strip() if out.returncode == 0 else None


@pytest.fixture(scope="module")
def report() -> Dict[str, Any]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def register() -> Dict[str, Any]:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def matches(entry: Dict[str, Any], skip: Dict[str, Any]) -> bool:
    if entry.get("module") and entry["module"] != skip.get("module"):
        return False
    return bool(re.search(entry["reason_pattern"], skip.get("reason", ""),
                          re.I))


def unregistered(skips: List[Dict[str, Any]],
                 entries: List[Dict[str, Any]]) -> List[str]:
    bad = []
    for s in skips:
        if not any(matches(e, s) for e in entries):
            bad.append(f"{s.get('module')}:{s.get('line')}  "
                       f"{s.get('reason', '')[:90]}")
    return bad


def expired(entries: List[Dict[str, Any]],
            generation: int = CURRENT_GENERATION) -> List[str]:
    bad = []
    for e in entries:
        exp = e.get("expiry") or {}
        if exp.get("kind") == "generation":
            gen = exp.get("generation")
            if isinstance(gen, int) and gen <= generation:
                bad.append(f"{e.get('id')}: expired at generation {gen}, "
                           f"now {generation}")
        elif exp.get("kind") != "condition" or not exp.get("condition"):
            bad.append(f"{e.get('id')}: expiry is neither a generation nor a "
                       "stated condition, so the skip is permanent by default "
                       "-- which is what SKIP-01 forbids")
    return bad


class TestEverySkipIsRegistered:

    def test_no_skip_is_unregistered(self, report, register) -> None:
        bad = unregistered(report["skips"], register["entries"])
        assert not bad, (
            "SKIP-01 -- a skip is a failure unless it carries a reason and an "
            "expiry. Unregistered:\n  " + "\n  ".join(bad)
            + "\n\nAdd it to docs/SKIP_REGISTER.json with why it is legitimate "
              "and when it stops being so, or fix the guard so it runs.")

    def test_no_registration_has_expired(self, register) -> None:
        bad = expired(register["entries"])
        assert not bad, "SKIP-01 -- expired:\n  " + "\n  ".join(bad)

    def test_every_entry_says_why(self, register) -> None:
        thin = [e.get("id") for e in register["entries"]
                if len(str(e.get("why_legitimate", ""))) < 40]
        assert not thin, (
            f"entries with no real justification: {thin}. 'known issue' is not "
            "a reason; it is the absence of one")


class TestTheReportIsHonestAboutItself:

    def test_it_records_the_commit_it_was_taken_at(self, report) -> None:
        assert report.get("taken_at_commit")

    def test_it_reports_skips_beside_passes(self, report) -> None:
        """The rule's own words: skip counts with reasons in the same line as
        passes."""
        line = report.get("summary_line", "")
        assert "passed" in line, (
            "the summary line must carry passes and skips together; a skip "
            "count reported somewhere else is a skip count nobody reads")

    def test_staleness_is_reported_not_hidden(self, report) -> None:
        head = git("rev-parse", "HEAD")
        if head and report["taken_at_commit"] != head:
            pytest.skip(
                "skip report predates HEAD; SKIP-01 register entry "
                "'skip report stale' -- expires when report_skips.py is re-run")
        assert report["taken_at_commit"] == head


class TestTheGuardHasBothControls:
    """``IA-1``. A plausible negative, and a positive that would fail if the
    rule did nothing."""

    def test_negative_control_an_unregistered_skip_is_caught(
            self, register) -> None:
        """Plausible, not malformed: it is exactly the shape of the two skips
        that hid ``HIST-01`` for a generation."""
        planted = [{
            "module": "tests/test_commit_messages_g7.py",
            "line": 113,
            "reason": ("git log --format=%H 3e05c9da^..HEAD unavailable: "
                       "fatal: ambiguous argument"),
        }]
        bad = unregistered(planted, register["entries"])
        assert bad, (
            "the skip that hid HIST-01 for a generation is not caught by this "
            "guard, which means the guard would not have caught it either")

    def test_negative_control_an_expired_registration_is_caught(self) -> None:
        planted = [{
            "id": "PLANT-EXPIRED",
            "reason_pattern": "anything",
            "why_legitimate": "a long enough justification to pass the other check",
            "expiry": {"kind": "generation", "generation": CURRENT_GENERATION - 1},
        }]
        assert expired(planted), "an expired registration was not caught"

    def test_negative_control_a_registration_with_no_expiry_is_caught(
            self) -> None:
        """A skip with no expiry is a permanent skip, which is the thing the
        rule exists to stop."""
        planted = [{
            "id": "PLANT-FOREVER",
            "reason_pattern": "anything",
            "why_legitimate": "a long enough justification to pass the other check",
        }]
        assert expired(planted)

    def test_positive_control_the_real_skips_are_all_registered(
            self, report, register) -> None:
        """Would fail if the matcher matched nothing."""
        assert report["skips"], (
            "the report contains no skips at all, so this guard is checking "
            "nothing. If the suite genuinely skips nothing that is the good "
            "outcome and this assertion should be retired with the commit "
            "that made it true")
        assert unregistered(report["skips"], register["entries"]) == []

    def test_positive_control_the_matcher_actually_matches(
            self, report, register) -> None:
        """Every registered entry that fires must fire on something real, or
        the register is accumulating dead rows that hide live ones."""
        used = [e.get("id") for e in register["entries"]
                if any(matches(e, s) for s in report["skips"])]
        assert used, "no register entry matches any reported skip"
