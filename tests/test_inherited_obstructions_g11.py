"""``OBS-01``: an inherited obstruction is re-tested before it is re-asserted.

The defect, in one sentence: `HIST-01` was carried for three generations as
`UNREPAIRABLE FROM INSIDE THE TREE` while the file that repaired it sat in
`.git/`, because an impossibility once written down was never asked again.

Full text and the defect that motivated it: ``docs/RULES_ENACTED.md``,
``OBS-01``. The account of the finding: ``docs/HIST01_REPAIR_g11.md``.

What is checked
---------------
Any open finding whose ``status`` **asserts impossibility** must carry a
``last_tested`` object naming the generation, the check that was actually run,
and what it returned. A citation of the ruling that assigned the status is not a
check -- a status whose evidence is another document asserting the same status
is precisely what this rule exists to stop.

``SW-20``: the subject is a JSON document; this module's own source is not part
of the scanned document, and both controls are below.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "LOOP_STATE_v10.json"

#: Words in a `status` that assert something cannot be done.
IMPOSSIBILITY = re.compile(
    r"UNREPAIRABLE|UNRESOLVABLE|IMPOSSIBLE|CANNOT|PERMANENT|BY-CONSTRUCTION",
    re.I)

#: A `check` that is a document reference and nothing else is not a check.
_A_DOCUMENT_ONLY = re.compile(
    r"^\s*(?:see\s+)?(?:docs?/|papers/|LOOP_STATE|[A-Z]{2,}-\d+)[\w/.\-]*"
    r"(?:\s+(?:section|§)\s*\S+)?\s*\.?\s*$", re.I)

pytestmark = pytest.mark.skipif(
    not STATE.is_file(),
    reason="LOOP_STATE_v10.json is written by the generation-11 state commit")


@pytest.fixture(scope="module")
def findings() -> List[Dict]:
    return json.loads(STATE.read_text(encoding="utf-8"))["open_findings"]


def asserts_impossibility(finding: Dict) -> bool:
    return bool(IMPOSSIBILITY.search(str(finding.get("status", ""))))


def offenders(items: List[Dict]) -> List[str]:
    """Every finding that asserts impossibility without a usable check."""
    bad = []
    for f in items:
        if not asserts_impossibility(f):
            continue
        tested = f.get("last_tested")
        ident = f.get("id", "<no id>")
        if not isinstance(tested, dict):
            bad.append(f"{ident}: status asserts impossibility "
                       f"({f.get('status')!r}) and carries no last_tested")
            continue
        missing = [k for k in ("generation", "check", "result")
                   if not tested.get(k)]
        if missing:
            bad.append(f"{ident}: last_tested is missing {missing}")
            continue
        if _A_DOCUMENT_ONLY.match(str(tested["check"])):
            bad.append(
                f"{ident}: last_tested.check is a document reference "
                f"({tested['check']!r}), not a check. A status whose evidence "
                "is another document asserting the same status is what OBS-01 "
                "exists to stop")
    return bad


class TestEveryAssertedImpossibilityCarriesItsCheck:

    def test_no_finding_asserts_impossibility_without_a_check(
            self, findings) -> None:
        bad = offenders(findings)
        assert not bad, (
            "OBS-01 -- an inherited obstruction is re-tested before it is "
            "re-asserted:\n  " + "\n  ".join(bad))

    def test_the_predicate_matches_something_real(self, findings) -> None:
        """Positive control: the rule would be vacuous if it matched nothing."""
        matched = [f["id"] for f in findings if asserts_impossibility(f)]
        assert matched, (
            "no open finding asserts impossibility, so this guard is checking "
            "nothing. If that is genuinely true the rule should be retired "
            "with the commit that made it true, not left green over a "
            "predicate that matches no rows")

    def test_hist01_carries_the_check_that_repaired_it(self, findings) -> None:
        """The finding that motivated the rule, in the state it now has."""
        hist = next((f for f in findings if f.get("id") == "HIST-01"), None)
        assert hist is not None, "HIST-01 is not in open_findings"
        assert not asserts_impossibility(hist), (
            f"HIST-01 still asserts impossibility: {hist.get('status')!r}. It "
            "was repaired at generation 11; docs/HIST01_REPAIR_g11.md")


class TestTheGuardHasBothControls:
    """``IA-1``. A plausible negative, and a positive that would fail if the
    rule did nothing."""

    def test_negative_control_a_planted_bare_impossibility_is_caught(
            self) -> None:
        planted = [{
            "id": "PLANT-01",
            "severity": "MEDIUM",
            "status": "OPEN, UNREPAIRABLE FROM INSIDE THE TREE",
            "note": "reads exactly like HIST-01 did for three generations",
        }]
        bad = offenders(planted)
        assert len(bad) == 1 and "PLANT-01" in bad[0]

    def test_negative_control_a_citation_is_not_a_check(self) -> None:
        """The plausible failure, not the malformed one.

        The tempting way to satisfy this rule is to point at the ruling that
        assigned the status. That is the circularity the rule forbids.
        """
        planted = [{
            "id": "PLANT-02",
            "status": "ACCEPTED-PERMANENT",
            "last_tested": {"generation": 11,
                            "check": "docs/AUDIT_MASTER.md section CI-01",
                            "result": "status confirmed"},
        }]
        bad = offenders(planted)
        assert len(bad) == 1 and "not a check" in bad[0]

    def test_positive_control_a_real_check_passes(self) -> None:
        """Would fail if the predicate rejected everything."""
        planted = [{
            "id": "PLANT-03",
            "status": "OPEN, UNREPAIRABLE FROM INSIDE THE TREE",
            "last_tested": {
                "generation": 11,
                "check": "git fsck --lost-found; ls .git/filter-repo/; "
                         "inspected both preservation copies and the "
                         "pre-loop zip for a .git",
                "result": "two dangling stashes, neither a recorded hash",
            },
        }]
        assert offenders(planted) == []

    def test_a_finding_that_asserts_nothing_is_not_required_to_carry_one(
            self) -> None:
        planted = [{"id": "PLANT-04", "status": "OPEN", "note": "no claim"}]
        assert offenders(planted) == []


class TestTheRecordedLimitStaysVisible:
    """The rule reaches statuses, not prose, and that is measured."""

    def test_prose_impossibility_in_a_note_is_not_reached(self) -> None:
        """`docs/RULES_ENACTED.md` records this as a limit. Pin it.

        A finding whose status is a bare `OPEN` while its note argues that
        nothing can be done is not caught. Widening the predicate to note text
        was tried and rejected, and the reason is reproduced here rather than
        asserted: the widened predicate fires on notes that *describe* an
        impossibility without asserting one.
        """
        planted = [{
            "id": "PLANT-05",
            "status": "OPEN",
            "note": "nothing can be done about this from inside the tree; it "
                    "is unrepairable in practice",
        }]
        assert offenders(planted) == [], (
            "the guard now reaches note prose; if that is deliberate, the "
            "recorded limit in docs/RULES_ENACTED.md must be updated with it")

    def test_the_widened_predicate_is_measured_to_over_fire(
            self, findings) -> None:
        """The rejected widening, run rather than described.

        `docs/RULES_ENACTED.md` claims widening to note text was tried and
        rejected because it fires on notes that describe an impossibility they
        do not assert. This runs that widening over the real findings and
        requires it to produce strictly more hits than the status-only
        predicate -- which is what "over-fires" means, and what makes the
        recorded limitation a measurement rather than a story.
        """
        status_only = [f["id"] for f in findings if asserts_impossibility(f)]
        widened = [f["id"] for f in findings
                   if IMPOSSIBILITY.search(str(f.get("status", "")))
                   or IMPOSSIBILITY.search(str(f.get("note", "")))]
        assert set(status_only) <= set(widened)
        assert len(widened) > len(status_only), (
            "the widened predicate matched no more than the status-only one, "
            "so the recorded reason for rejecting it does not hold on this "
            "state file and docs/RULES_ENACTED.md must be corrected")
