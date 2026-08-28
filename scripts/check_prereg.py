"""``PRE-01``: check a pre-registration's outcome space before it is hashed.

What the rule requires
----------------------
    Before a pre-registration is hashed, its outcome space is enumerated and
    checked for two properties: **exhaustiveness** — every possible measurement
    result maps to exactly one label, with no gap and no overlap — and
    **entailment** — each label's stated meaning is implied by the branch
    condition that produces it, not merely associated with it. Any factual claim
    inside the justification (an attainable ``p``, a bound, a count) is verified
    before hashing, because it cannot be corrected after.

Why a checker and not a checklist
---------------------------------
Two generations in a row hashed a pre-registration containing a defect that a
reading would have caught, and in both cases the text could not be corrected
afterwards without destroying the thing hashing exists to protect. A checklist
is what was already being done. What was missing is a *mechanism* that consumes
the outcome space as data and reports the specific measurement result that
breaks it — because "the outcome space is exhaustive" is not a claim a person
verifies reliably by looking at prose.

So an outcome space is written down as **axes with finite levels** and each
label as a **predicate over those axes**. The product of the levels is the
enumeration the rule asks for; the predicates are evaluated over every point in
it. A gap is a point no label claims; an overlap is a point two labels claim;
an entailment failure is a point where a label fires and its own stated meaning
is false.

The predicate language is deliberately tiny and is **interpreted, never
evaluated** — no ``eval``, no ``exec``. A pre-registration is a governance
artefact, and a register that executes strings from one is a register that can
be made to say anything.

``SW-20`` and this guard
------------------------
``SW-20`` requires a guard whose subject is *source code* to work over the AST.
This guard's subject is a JSON register and the JSON artefacts it describes, so
that clause does not apply. ``SW-20``'s purpose does: both controls ship, in
``tests/test_pre01_preregistration_close.py`` — the two historical defects must
be caught, and a well-formed pre-registration must not be flagged.

Run it standalone::

    python scripts/check_prereg.py            # report on the register
    python scripts/check_prereg.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "PREREG_REGISTER.json"

Point = Dict[str, str]


# --------------------------------------------------------------------------
# The predicate language.
# --------------------------------------------------------------------------

class PredicateError(ValueError):
    """A malformed predicate. Never a measurement result -- always an author error."""


def evaluate(pred: Any, point: Point) -> bool:
    """Evaluate one predicate at one point of the outcome space.

    The whole grammar::

        {"const": true|false}
        {"var": "<axis>", "is": "<level>"}
        {"var": "<axis>", "in": ["<level>", ...]}
        {"all": [<pred>, ...]}
        {"any": [<pred>, ...]}
        {"not": <pred>}

    Anything else raises. Silently tolerating an unrecognised key is how a
    predicate comes to mean something other than what its author read.
    """
    if not isinstance(pred, dict):
        raise PredicateError(f"predicate must be an object, got {type(pred).__name__}")

    keys = set(pred)
    if keys == {"const"}:
        if not isinstance(pred["const"], bool):
            raise PredicateError("const takes a boolean")
        return pred["const"]

    if keys == {"all", }:
        return all(evaluate(p, point) for p in pred["all"])
    if keys == {"any", }:
        return any(evaluate(p, point) for p in pred["any"])
    if keys == {"not", }:
        return not evaluate(pred["not"], point)

    if keys == {"var", "is"} or keys == {"var", "in"}:
        axis = pred["var"]
        if axis not in point:
            raise PredicateError(
                f"predicate names axis {axis!r}, which the outcome space does "
                f"not declare (declared: {sorted(point)})")
        if "is" in pred:
            return point[axis] == pred["is"]
        levels = pred["in"]
        if not isinstance(levels, list):
            raise PredicateError("'in' takes a list of levels")
        return point[axis] in levels

    raise PredicateError(f"unrecognised predicate shape: {sorted(keys)}")


def axes_named_by(pred: Any, found: set) -> set:
    """Every axis a predicate mentions. Used to catch a typo'd axis name."""
    if isinstance(pred, dict):
        if "var" in pred:
            found.add(pred["var"])
        for key in ("all", "any"):
            for sub in pred.get(key, []):
                axes_named_by(sub, found)
        if "not" in pred:
            axes_named_by(pred["not"], found)
    return found


def enumerate_space(axes: Dict[str, Sequence[str]]) -> Iterator[Point]:
    """The outcome space: the product of the axes' levels.

    This is the enumeration ``PRE-01`` asks for, made literal. If it is not
    finite and small, the outcome space has not been thought about hard enough
    to hash.
    """
    names = sorted(axes)
    for combo in itertools.product(*(axes[n] for n in names)):
        yield dict(zip(names, combo))


def describe(point: Point) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(point.items()))


# --------------------------------------------------------------------------
# Property 1 -- exhaustiveness. Property 2 -- entailment.
# --------------------------------------------------------------------------

def check_exhaustiveness(entry: dict) -> Tuple[List[str], List[str]]:
    """Every point maps to exactly one label.

    Returns ``(gaps, overlaps)`` as human-readable lines. A gap is a
    measurement result the rule does not classify; an overlap is one it
    classifies twice, which means the rule's own order of evaluation decides
    the answer and the pre-registration does not say what that order is.
    """
    axes = entry["outcome_space"]["axes"]
    gaps: List[str] = []
    overlaps: List[str] = []
    for point in enumerate_space(axes):
        firing = [lab["name"] for lab in entry["labels"]
                  if evaluate(lab["condition"], point)]
        if not firing:
            gaps.append(describe(point))
        elif len(firing) > 1:
            overlaps.append(f"{describe(point)} -> {', '.join(sorted(firing))}")
    return gaps, overlaps


def check_entailment(entry: dict) -> List[str]:
    """Each label's stated meaning holds wherever its condition fires.

    This is the property that a hash cannot supply. Hashing fixes the prose
    around a statistic; it does not make that prose correct. A label whose
    branch condition admits a measurement its stated meaning denies will, when
    that measurement occurs, put a false sentence into the record under a
    correct-looking procedure.
    """
    axes = entry["outcome_space"]["axes"]
    failures: List[str] = []
    for lab in entry["labels"]:
        holds = lab.get("meaning_holds_when")
        if holds is None:
            failures.append(
                f"{lab['name']}: no meaning_holds_when. A label whose meaning "
                f"is not stated as a predicate cannot be checked against its "
                f"own condition, which is the whole of property two")
            continue
        for point in enumerate_space(axes):
            if evaluate(lab["condition"], point) and not evaluate(holds, point):
                failures.append(
                    f"{lab['name']}: fires at [{describe(point)}] where its "
                    f"stated meaning is false")
    return failures


def check_axes_are_used(entry: dict) -> List[str]:
    """Every axis mentioned by a predicate is declared, and vice versa.

    A typo'd axis name would otherwise make a predicate raise -- caught -- but
    a *declared* axis no predicate mentions is the quieter defect: it means the
    outcome space was enumerated wider than the rule reads, and the extra
    dimension is doing nothing.
    """
    declared = set(entry["outcome_space"]["axes"])
    used: set = set()
    for lab in entry["labels"]:
        axes_named_by(lab["condition"], used)
        if lab.get("meaning_holds_when") is not None:
            axes_named_by(lab["meaning_holds_when"], used)
    problems = []
    for axis in sorted(declared - used):
        problems.append(
            f"axis {axis!r} is declared but no label's condition or meaning "
            f"mentions it")
    for axis in sorted(used - declared):
        problems.append(f"axis {axis!r} is used but not declared")
    return problems


# --------------------------------------------------------------------------
# Property 3 -- the factual claims inside the justification.
# --------------------------------------------------------------------------

def min_attainable_one_sided_p_exact_mwu(n1: int, n2: int) -> float:
    """Smallest one-sided p an exact Mann-Whitney U test can return at n1 vs n2.

    Under the null every assignment of ranks to the two samples is equally
    likely, so there are ``C(n1 + n2, n1)`` of them and the most extreme one has
    probability ``1 / C(n1 + n2, n1)``. Perfect separation attains it.

    At 3 vs 3 that is ``1/20 = 0.05`` exactly -- which is *attainable* at
    alpha = 0.05, contradicting the generation-13 pre-registration's stated
    justification for ``minimum_cells = 4``.
    """
    if n1 < 1 or n2 < 1:
        raise ValueError("both samples need at least one observation")
    return 1.0 / math.comb(n1 + n2, n1)


#: Named computations a register entry may cite. A claim that cannot be checked
#: by one of these is not a checkable claim, and the register must say so rather
#: than let it through unverified.
CLAIM_CHECKS = {
    "min_attainable_one_sided_p_exact_mwu": min_attainable_one_sided_p_exact_mwu,
}

_COMPARE = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
}


def check_factual_claims(entry: dict) -> List[str]:
    """Recompute every factual claim and compare against the recorded verdict.

    The register records what the pre-registration asserted, what the assertion
    computes to, and whether it is true. This recomputes the value and re-derives
    the verdict. If the register and the arithmetic disagree, the register is
    wrong -- which is the failure mode a register of verified claims has.
    """
    problems: List[str] = []
    for claim in entry.get("factual_claims", []):
        name = claim.get("check")
        if name is None:
            if claim.get("verdict") != "NOT-MECHANICALLY-CHECKABLE":
                problems.append(
                    f"{claim.get('id')}: no check named, and the verdict is not "
                    f"NOT-MECHANICALLY-CHECKABLE. A claim is either verified or "
                    f"declared unverifiable; it is never merely present")
            continue
        if name not in CLAIM_CHECKS:
            problems.append(f"{claim.get('id')}: unknown check {name!r}")
            continue

        value = CLAIM_CHECKS[name](**claim.get("args", {}))
        recorded = claim.get("computed_value")
        if recorded is None or abs(value - recorded) > 1e-12:
            problems.append(
                f"{claim.get('id')}: check recomputes to {value!r}, register "
                f"records {recorded!r}")
            continue

        asserts = claim.get("claim_asserts")
        if not isinstance(asserts, dict) or asserts.get("op") not in _COMPARE:
            problems.append(
                f"{claim.get('id')}: claim_asserts must be "
                f"{{'op': one of {sorted(_COMPARE)}, 'value': <number>}}")
            continue

        derived = "TRUE" if _COMPARE[asserts["op"]](value, asserts["value"]) else "FALSE"
        if derived != claim.get("verdict"):
            problems.append(
                f"{claim.get('id')}: recorded verdict {claim.get('verdict')!r}, "
                f"but {value!r} {asserts['op']} {asserts['value']!r} is {derived}")
    return problems


# --------------------------------------------------------------------------
# One entry, all properties.
# --------------------------------------------------------------------------

def check_entry(entry: dict) -> Dict[str, List[str]]:
    """Run every property over one register entry.

    Returns a dict of property name -> findings. Empty everywhere means the
    pre-registration is checkable and clean; it does not mean the science is
    right, and nothing here should be read as saying so.
    """
    gaps, overlaps = check_exhaustiveness(entry)
    return {
        "gaps": gaps,
        "overlaps": overlaps,
        "entailment": check_entailment(entry),
        "axes": check_axes_are_used(entry),
        "factual_claims": check_factual_claims(entry),
    }


#: Properties whose findings say the PRE-REGISTRATION is defective.
DEFECT_PROPERTIES = ("gaps", "overlaps", "entailment", "axes")


def is_defective(findings: Dict[str, List[str]]) -> bool:
    """Is the pre-registration itself defective?

    ``factual_claims`` is deliberately excluded. A finding there does not say
    the pre-registration is defective -- it says the *register's record of it*
    disagrees with the arithmetic, which is a different and worse thing, and it
    is always a failure regardless of the expected verdict.
    """
    return any(findings[k] for k in DEFECT_PROPERTIES)


def load_register(path: Path = REGISTER) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] = ()) -> int:
    ap = argparse.ArgumentParser(description="PRE-01 pre-registration checker")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(list(argv) or None)

    reg = load_register()
    report = {}
    exit_code = 0
    for entry in reg["entries"]:
        if entry.get("outcome_space") is None:
            continue
        findings = check_entry(entry)
        report[entry["id"]] = findings
        expected = entry.get("expected_verdict", "CLEAN")
        got = "DEFECTIVE" if is_defective(findings) else "CLEAN"
        if got != expected:
            exit_code = 1
        if findings["factual_claims"]:
            # The register disagrees with the arithmetic. Never expected, never
            # excused by the entry's expected_verdict.
            exit_code = 1
        if not args.json:
            print(f"{entry['id']}: {got} (expected {expected})")
            for prop, lines in findings.items():
                for line in lines:
                    print(f"    {prop}: {line}")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
