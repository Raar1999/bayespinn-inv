"""``PRE-01``: a pre-registration's outcome space is checked before it is hashed.

The defect that forced it
-------------------------
Two generations in a row hashed a pre-registration containing a defect a reading
would have caught, and in both cases the text could not be corrected afterwards
without destroying the thing hashing exists to protect.

* **Generation 13** justified ``minimum_cells = 4`` with the sentence *"below
  four admissible cells on either axis the exact test cannot reach p = 0.05
  one-sided"*. At 3 against 3 the minimum attainable one-sided ``p`` is exactly
  ``1/C(6,3) = 0.05``, which clears ``alpha = 0.05``. The sentence reads like a
  derivation and is not one.
* **Generation 14** registered ``GENERIC_ROW_COUNT`` to mean *"the nested windows
  track the null"* while its branch condition was *everything that is not
  ``IDENTITY_MATTERS``*. The measurement landed exactly in the gap: all four
  devices departed from the null in the same direction, three at ``p <= 0.005``,
  and the rule returned the label whose meaning that refutes.

The operator's sentence is the rule's justification: **hashing fixes the prose
around a statistic; it does not make that prose correct.**

What this guard adds over a checklist
-------------------------------------
A checklist is what was already being done. This consumes the outcome space as
data -- axes with finite levels, labels as predicates -- enumerates the product,
and names the specific measurement result that breaks it.

``SW-20`` and this guard
------------------------
``SW-20``'s AST clause governs guards whose subject is *source code*. This
guard's subject is a JSON register, so that clause does not apply; its purpose
does, and both controls ship below. The positive controls are the two historical
defects, which the checker must continue to identify -- if it stops, the
detector has gone vacuous, which is ``DIFF-01``'s design. The negative control is
a well-formed pre-registration that must come back clean, because a checker that
rejects everything also looks correct.

Named ``_close`` and not ``_g15``: no generation 15 ran. The loop terminated at
``L1`` and this is the closing ruling being enacted.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_checker():
    """Load the checker by path, as ``tests/test_loaded_code_g7.py`` does.

    Importing it as ``scripts.check_prereg`` would put the same file under two
    module names -- ``mypy src tests scripts`` checks it directly as
    ``check_prereg`` as well -- and mypy refuses that. Loading by path also
    makes the guard independent of whether the invocation put the repository
    root on ``sys.path``, which ``python -m pytest`` does and a bare ``pytest``
    does not.
    """
    path = ROOT / "scripts" / "check_prereg.py"
    spec = importlib.util.spec_from_file_location("_pre01_checker", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_checker = _load_checker()

CLAIM_CHECKS = _checker.CLAIM_CHECKS
PredicateError = _checker.PredicateError
check_entailment = _checker.check_entailment
check_entry = _checker.check_entry
check_exhaustiveness = _checker.check_exhaustiveness
check_factual_claims = _checker.check_factual_claims
enumerate_space = _checker.enumerate_space
evaluate = _checker.evaluate
is_defective = _checker.is_defective
load_register = _checker.load_register
min_attainable_one_sided_p_exact_mwu = _checker.min_attainable_one_sided_p_exact_mwu
REGISTER = ROOT / "docs" / "PREREG_REGISTER.json"

PASS4 = "mech01-pass4-g14"
PASS3 = "mech01-pass3-g13"


def register() -> dict:
    return load_register(REGISTER)


def entry(entry_id: str) -> dict:
    for e in register()["entries"]:
        if e["id"] == entry_id:
            return e
    raise AssertionError(f"{entry_id} is not in the register")


def checkable_entries():
    return [e for e in register()["entries"] if e.get("outcome_space")]


#: A pre-registration that satisfies both properties. Used as the negative
#: control. Its GENERIC label's meaning is stated as what its branch condition
#: actually admits -- "not established at both devices" -- rather than as the
#: stronger "tracks the null", which is the whole of the difference.
WELL_FORMED = {
    "id": "negative-control",
    "expected_verdict": "CLEAN",
    "outcome_space": {
        "axes": {
            "p10_clears": ["clears", "does_not_clear"],
            "p90_clears": ["clears", "does_not_clear"],
        }
    },
    "labels": [
        {
            "name": "ESTABLISHED",
            "condition": {"all": [{"var": "p10_clears", "is": "clears"},
                                  {"var": "p90_clears", "is": "clears"}]},
            "meaning": "the effect is present at both held-out devices.",
            "meaning_holds_when": {"all": [{"var": "p10_clears", "is": "clears"},
                                           {"var": "p90_clears", "is": "clears"}]},
        },
        {
            "name": "NOT_ESTABLISHED",
            "condition": {"not": {"all": [{"var": "p10_clears", "is": "clears"},
                                          {"var": "p90_clears", "is": "clears"}]}},
            "meaning": "the effect is not established at both devices. This says "
                       "nothing about whether it is present at one.",
            "meaning_holds_when": {"not": {"all": [{"var": "p10_clears", "is": "clears"},
                                                   {"var": "p90_clears", "is": "clears"}]}},
        },
    ],
    "factual_claims": [],
}


class TestThePredicateLanguage:
    """It is interpreted, never evaluated. A malformed predicate is an author error."""

    def test_it_evaluates_the_whole_grammar(self):
        point = {"a": "x", "b": "y"}
        assert evaluate({"const": True}, point)
        assert evaluate({"var": "a", "is": "x"}, point)
        assert not evaluate({"var": "a", "is": "z"}, point)
        assert evaluate({"var": "a", "in": ["x", "z"]}, point)
        assert evaluate({"all": [{"var": "a", "is": "x"}, {"var": "b", "is": "y"}]}, point)
        assert evaluate({"any": [{"var": "a", "is": "z"}, {"var": "b", "is": "y"}]}, point)
        assert evaluate({"not": {"var": "a", "is": "z"}}, point)

    @pytest.mark.parametrize("bad", [
        {"var": "missing_axis", "is": "x"},
        {"unknown_key": 1},
        {"const": "yes"},
        {"var": "a", "in": "x"},
        "not even an object",
    ])
    def test_it_refuses_what_it_does_not_understand(self, bad):
        """Silently tolerating an unrecognised key is how a predicate comes to
        mean something other than what its author read."""
        with pytest.raises((PredicateError, ValueError)):
            evaluate(bad, {"a": "x"})

    def test_the_register_contains_no_executable_strings(self):
        """No ``eval``, no ``exec``, and nothing in the register that would need one.

        Every condition is a nested object. A register that executed strings
        from a governance artefact could be made to say anything.
        """
        for e in checkable_entries():
            for lab in e["labels"]:
                assert isinstance(lab["condition"], dict)
                assert isinstance(lab["meaning_holds_when"], dict)

    def test_the_enumeration_is_the_product_of_the_levels(self):
        axes = {"a": ["1", "2"], "b": ["x", "y", "z"]}
        points = list(enumerate_space(axes))
        assert len(points) == 6
        assert len({tuple(sorted(p.items())) for p in points}) == 6


class TestTheRegisterIsWellFormed:

    def test_every_checkable_entry_states_both_a_meaning_and_its_predicate(self):
        """Property two is unavailable without both. A label carrying prose and
        no predicate is exactly the artefact this rule exists to reject."""
        for e in checkable_entries():
            assert e.get("expected_verdict") in {"CLEAN", "DEFECTIVE"}, e["id"]
            assert e["labels"], f"{e['id']}: no labels"
            for lab in e["labels"]:
                assert lab.get("meaning"), f"{e['id']}/{lab.get('name')}: no meaning"
                assert lab.get("meaning_holds_when") is not None, (
                    f"{e['id']}/{lab['name']}: meaning stated as prose only")

    def test_every_entry_verdict_matches_what_the_checker_finds(self):
        for e in checkable_entries():
            findings = check_entry(e)
            got = "DEFECTIVE" if is_defective(findings) else "CLEAN"
            assert got == e["expected_verdict"], (
                f"{e['id']}: register says {e['expected_verdict']}, checker says "
                f"{got}\n" + json.dumps(findings, indent=2))

    def test_every_preregistration_in_the_tree_is_registered(self):
        """The self-enforcing hook. A register nobody updates guards nothing.

        There is no natural signal for "a pre-registration was written", so the
        guard manufactures one from the filesystem: every ``preregister*.json``
        under ``outputs/`` must be named by an entry, either as one that is
        checked or as one explicitly declared historical.
        """
        known = set()
        for e in register()["entries"]:
            if e.get("artefact"):
                known.add(e["artefact"])
            known.update(e.get("artefacts", []))

        found = {p.relative_to(ROOT).as_posix()
                 for p in ROOT.glob("outputs/**/preregister*.json")}
        unregistered = sorted(found - known)
        assert not unregistered, (
            "PRE-01: pre-registration artefacts with no register entry:\n  "
            + "\n  ".join(unregistered))

    def test_the_registered_artefacts_still_exist(self):
        """A register pointing at files that are gone is a register nobody reads."""
        missing = []
        for e in register()["entries"]:
            paths = ([e["artefact"]] if e.get("artefact") else []) + e.get("artefacts", [])
            missing += [p for p in paths if not (ROOT / p).exists()]
        assert not missing, f"registered but absent: {missing}"


class TestThePositiveControlsFromHistory:
    """The two defects the rule was enacted for. If these stop being caught,
    the detector has gone vacuous."""

    def test_pass4_entailment_failure_is_caught_and_names_the_label(self):
        failures = check_entailment(entry(PASS4))
        assert failures, "the generation-14 defect is no longer detected"
        assert all("GENERIC_ROW_COUNT" in f for f in failures)
        # Every point at which exactly one device departs -- 8 of the 16.
        assert len(failures) == 8, failures

    def test_pass4_declares_an_axis_its_decision_rule_never_reads(self):
        """The operator's diagnosis, made mechanical: the outcome space is
        three-way -- more flat, indistinguishable, less flat -- and the rule is
        two-way."""
        problems = check_entry(entry(PASS4))["axes"]
        assert any("direction" in p for p in problems), problems

    def test_pass4_result_that_actually_occurred_is_one_of_the_failing_points(self):
        """Not a hypothetical. ``device_p90`` cleared and ``device_p10`` did not."""
        e = entry(PASS4)
        observed = {"p10_clears": "does_not_clear", "p90_clears": "clears",
                    "direction": "less_flat_than_null", "controls": "passed"}
        generic = next(lab for lab in e["labels"]
                       if lab["name"] == "GENERIC_ROW_COUNT")
        assert evaluate(generic["condition"], observed), (
            "the pre-registered rule did return GENERIC_ROW_COUNT")
        assert not evaluate(generic["meaning_holds_when"], observed), (
            "and its registered meaning is false at that same point")

    def test_the_observed_pass4_result_matches_the_committed_artefact(self):
        """The point above is read off the artefact, not asserted about it."""
        verdict = json.loads(
            (ROOT / "outputs/g14/mech01_pass4/verdict.json").read_text(encoding="utf-8"))
        assert verdict["outcome"] == "GENERIC_ROW_COUNT"
        assert verdict["held_out"]["device_p10"]["clears_alpha"] is False
        assert verdict["held_out"]["device_p90"]["clears_alpha"] is True
        assert verdict["held_out"]["device_p10"]["direction"] == "less flat than the null"
        assert verdict["held_out"]["device_p90"]["direction"] == "less flat than the null"

    def test_pass3_factual_claim_is_false_and_the_register_says_so(self):
        e = entry(PASS3)
        claim = next(c for c in e["factual_claims"]
                     if c["id"] == "pass3-minimum-cells")
        assert claim["verdict"] == "FALSE"
        # Recomputed here rather than trusted: 1 / C(6,3).
        assert min_attainable_one_sided_p_exact_mwu(3, 3) == pytest.approx(0.05)
        assert min_attainable_one_sided_p_exact_mwu(2, 5) == pytest.approx(1 / 21)
        assert not check_factual_claims(e), "the register disagrees with the arithmetic"

    def test_the_claim_is_confirmed_by_a_second_code_path(self):
        """Two code paths, one measurement -- this loop's own discipline.

        The combinatorial identity and ``scipy``'s exact test must agree, or the
        finding rests on one implementation.
        """
        scipy_stats = pytest.importorskip("scipy.stats")
        got = scipy_stats.mannwhitneyu([4, 5, 6], [1, 2, 3],
                                       alternative="greater", method="exact").pvalue
        assert got == pytest.approx(min_attainable_one_sided_p_exact_mwu(3, 3))
        assert got == pytest.approx(1.0 / math.comb(6, 3))

    def test_pass3_has_the_same_entailment_defect_one_generation_earlier(self):
        """Found by applying this checker to generation 13, not previously recorded.

        Unlike pass 4's, this one **fired**: ``device_p10`` cleared at
        ``p = 0.00062`` while ``device_p90`` did not at ``p = 0.30629``, and the
        label was written with the sentence *"not a property of the system"* in
        its meaning.
        """
        failures = check_entailment(entry(PASS3))
        assert any("DOES_NOT_SEPARATE" in f for f in failures), failures

        verdict = json.loads(
            (ROOT / "outputs/g13/mech01_pass3/verdict.json").read_text(encoding="utf-8"))
        assert verdict["outcome"] == "DOES_NOT_SEPARATE"
        devices = verdict["devices"]
        assert devices["device_p10"]["test"]["clears_alpha"] is True
        assert devices["device_p90"]["test"]["clears_alpha"] is False
        assert devices["device_p10"]["test"]["p_value"] < 0.001

        observed = {"p10_clears": "clears", "p90_clears": "does_not_clear",
                    "admissible_cells": "at_least_four",
                    "reproduction_control": "passed"}
        label = next(lab for lab in entry(PASS3)["labels"]
                     if lab["name"] == "DOES_NOT_SEPARATE")
        assert evaluate(label["condition"], observed)
        assert not evaluate(label["meaning_holds_when"], observed)

    def test_that_finding_did_not_reach_the_descent(self):
        """Scope, stated rather than left open.

        The ``U-EMPIR`` verdict rests method 2's falsification on the measured
        ``b`` confound and quotes both p-values, so the ``L0 -> L1`` descent does
        not lean on the sentence that fails.
        """
        text = (ROOT / "docs" / "UEMPIR_MECH01_g14.md").read_text(encoding="utf-8")
        assert "0.00062" in text and "0.30629" in text, (
            "the verdict must state both p-values, not the label's prose")
        assert "not a property of the system" not in text


class TestTheNegativeControl:
    """A checker that rejects everything also looks correct."""

    def test_a_well_formed_preregistration_is_not_flagged(self):
        findings = check_entry(WELL_FORMED)
        assert not is_defective(findings), findings

    def test_the_difference_is_the_meaning_and_nothing_else(self):
        """The discriminating control.

        Take the generation-14 entry and change **only** ``GENERIC_ROW_COUNT``'s
        ``meaning_holds_when`` to what its branch condition actually admits. The
        entailment finding must disappear. If it does not, the checker is
        reporting on something other than the property it claims to measure.
        """
        repaired = copy.deepcopy(entry(PASS4))
        for lab in repaired["labels"]:
            if lab["name"] == "GENERIC_ROW_COUNT":
                lab["meaning_holds_when"] = lab["condition"]
        assert not check_entailment(repaired), (
            "the entailment finding survived a repair of the meaning, so it is "
            "not the meaning that produced it")
        # And the original still fails, so the repair is what changed it.
        assert check_entailment(entry(PASS4))

    def test_a_gap_is_caught(self):
        """Positive control for the other half of property one."""
        gappy = copy.deepcopy(WELL_FORMED)
        gappy["labels"] = [gappy["labels"][0]]  # drop the catch-all
        gaps, overlaps = check_exhaustiveness(gappy)
        assert gaps and not overlaps

    def test_an_overlap_is_caught(self):
        overlapping = copy.deepcopy(WELL_FORMED)
        overlapping["labels"].append({
            "name": "ALWAYS", "condition": {"const": True},
            "meaning": "fires everywhere",
            "meaning_holds_when": {"const": True},
        })
        gaps, overlaps = check_exhaustiveness(overlapping)
        assert overlaps and not gaps

    def test_a_register_that_lies_about_a_claim_is_caught(self):
        """The third clause's own control: the arithmetic outranks the record."""
        lying = copy.deepcopy(entry(PASS3))
        for claim in lying["factual_claims"]:
            if claim["id"] == "pass3-minimum-cells":
                claim["verdict"] = "TRUE"
        problems = check_factual_claims(lying)
        assert problems, "a wrong recorded verdict went undetected"

        wrong_value = copy.deepcopy(entry(PASS3))
        for claim in wrong_value["factual_claims"]:
            if claim["id"] == "pass3-minimum-cells":
                claim["computed_value"] = 0.5
        assert check_factual_claims(wrong_value)

    def test_an_unchecked_claim_must_declare_itself_unverifiable(self):
        """A claim is either verified or declared unverifiable, never merely present."""
        smuggled = {"factual_claims": [{"id": "vague", "quoted": "it is well known"}]}
        assert check_factual_claims(smuggled)

        declared = {"factual_claims": [{"id": "vague", "quoted": "it is well known",
                                        "verdict": "NOT-MECHANICALLY-CHECKABLE"}]}
        assert not check_factual_claims(declared)

    def test_every_named_check_is_reachable_from_the_register(self):
        """A check nobody cites is a check nobody runs."""
        cited = set()
        for e in register()["entries"]:
            for claim in e.get("factual_claims", []) or []:
                if claim.get("check"):
                    cited.add(claim["check"])
        assert cited <= set(CLAIM_CHECKS), f"register cites unknown checks: {cited - set(CLAIM_CHECKS)}"
