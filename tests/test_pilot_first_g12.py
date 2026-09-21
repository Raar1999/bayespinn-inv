"""``PILOT-01``: a measurement is never declined on a plausibility argument.

Full text and the defect that forced it: ``docs/RULES_ENACTED.md``, ``PILOT-01``.

The defect in one line: chart L's 37 witness pairs were published as a ``WIT-02``
gap for three generations on the argument that *a basin at 212 floor units
cannot become a ridge*. The argument was right about the outcome and irrelevant
to the decision. The pilot came out at 7.5 s per pair; the run took 288 seconds.

What is checked
---------------
A state file must carry ``declined_measurements`` -- possibly empty, but
**present**, so that a generation has to say out loud that it declined nothing
rather than leaving the question unasked. Every entry must carry a ``pilot``
with the invocation that produced it and a measured number.

An entry whose justification is a prediction about the result, with no measured
cost behind it, is exactly what the rule forbids and is what the negative
control plants.

``SW-20``: the subject is a JSON document; this module's own source is not part
of the scanned document, and both controls are below.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _version(p: Path) -> int:
    m = re.search(r"v(\d+)", p.name)
    return int(m.group(1)) if m else -1


def newest_state() -> Path:
    return sorted(ROOT.glob("LOOP_STATE_v*.json"), key=_version)[-1]


STATE = newest_state()

#: Words that mark a justification as a prediction about the *result* rather
#: than a statement about the *cost*. These are the shapes the closing ruling
#: used, quoted from it.
PREDICTION = re.compile(
    r"cannot become|will not change|would not change|does not survive losing|"
    r"is not going to|no reason to think|obviously|clearly cannot", re.I)


@pytest.fixture(scope="module")
def state() -> Dict[str, Any]:
    return json.loads(STATE.read_text(encoding="utf-8"))


def offenders(entries: List[Dict[str, Any]]) -> List[str]:
    """Declines that carry no measured cost."""
    bad = []
    for e in entries:
        ident = e.get("id") or e.get("measurement") or "<unnamed>"
        pilot = e.get("pilot")
        if not isinstance(pilot, dict):
            bad.append(f"{ident}: declined with no pilot at all")
            continue
        if not pilot.get("invocation"):
            bad.append(f"{ident}: pilot carries no invocation, so its number "
                       "cannot be re-derived")
        numbers = [v for k, v in pilot.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numbers:
            bad.append(f"{ident}: pilot carries no measured number. "
                       "'A budget verdict without a pilot is void', and a "
                       "pilot without a number is not a pilot")
        why = str(e.get("why_declined", ""))
        if PREDICTION.search(why) and not numbers:
            bad.append(f"{ident}: declined on a prediction about the result "
                       f"({why[:60]!r}) with no measured cost")
    return bad


class TestTheStateFileAnswersTheQuestion:

    def test_declined_measurements_is_present(self, state) -> None:
        assert "declined_measurements" in state, (
            "PILOT-01: a state file must carry declined_measurements, even "
            "empty. Chart L was declined for two of its three generations by "
            "nobody proposing it, and a key that must be filled in is the "
            "cheapest way to make that visible")

    def test_it_is_a_list(self, state) -> None:
        assert isinstance(state["declined_measurements"], list)


class TestEveryDeclineCarriesItsPrice:

    def test_no_decline_lacks_a_measured_cost(self, state) -> None:
        bad = offenders(state.get("declined_measurements") or [])
        assert not bad, (
            "PILOT-01 -- either it is priced by pilot and declined on U-BUDGET "
            "with the number, or it is run:\n  " + "\n  ".join(bad))


class TestTheGuardHasBothControls:
    """``IA-1``. A plausible negative, and a positive that would fail if the
    rule did nothing."""

    def test_negative_control_a_plausibility_decline_is_caught(self) -> None:
        """The real shape, quoted from the closing ruling that made the error.

        Plausible, not malformed: it has an id, a reason, and a confident
        argument. It simply has no number.
        """
        planted = [{
            "id": "WITNESS-04-chart-L",
            "why_declined": (
                "a basin at 212 floor units cannot become a ridge because some "
                "of its members separate under refinement"),
        }]
        bad = offenders(planted)
        assert bad and "WITNESS-04-chart-L" in bad[0]
        assert any("no pilot" in b for b in bad)

    def test_negative_control_a_pilot_without_a_number_is_caught(self) -> None:
        planted = [{
            "id": "PLANT-02",
            "why_declined": "it will not change the answer",
            "pilot": {"invocation": "python scripts/pilot_something.py",
                      "note": "looked expensive"},
        }]
        bad = offenders(planted)
        assert bad and any("no measured number" in b for b in bad)

    def test_negative_control_a_number_without_its_invocation_is_caught(
            self) -> None:
        planted = [{"id": "PLANT-03", "pilot": {"per_unit_s": 7.5}}]
        assert any("no invocation" in b for b in offenders(planted))

    def test_positive_control_a_properly_priced_decline_passes(self) -> None:
        """Would fail if the predicate rejected everything."""
        planted = [{
            "id": "PLANT-04",
            "why_declined": "U-BUDGET: the cheapest sufficient experiment "
                            "overruns the remaining budget by 6.4x",
            "pilot": {
                "invocation": "PYTHONPATH=src python scripts/pilot_x.py --n 3",
                "per_unit_s": 940.0,
                "units_required": 74,
                "projected_total_s": 69560.0,
                "budget_s": 10800.0,
            },
        }]
        assert offenders(planted) == []

    def test_positive_control_the_predicate_reads_real_entries(
            self, state) -> None:
        """The rule must be applicable to this state file, not just to plants."""
        entries = state.get("declined_measurements") or []
        assert isinstance(entries, list)
        assert offenders(entries) == []


class TestTheRecordedLimitStaysVisible:

    def test_it_only_reaches_recorded_declines(self, state) -> None:
        """``docs/RULES_ENACTED.md`` records this limit; pin it.

        A measurement nobody proposes is invisible here, and chart L was in
        exactly that state for two of its three generations. The rule shortens
        the gap; it does not close it.
        """
        assert offenders([]) == [], (
            "an empty decline list must pass -- the rule cannot see a "
            "measurement that was never proposed, and pretending otherwise "
            "would make the guard fire on every generation that declined "
            "nothing")
