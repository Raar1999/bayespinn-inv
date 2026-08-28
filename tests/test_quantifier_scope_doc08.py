"""``DOC-08``: no bare universal quantifier over a filtered set.

**Enacted** operator ruling of 2026-08-28 §3. Rule text and the three defects
that forced it: ``docs/RULES_ENACTED.md``.

    No bare universal quantifier over a filtered set. "All tested X" is written
    "n of N X tested, all surviving". Every count carries its denominator; every
    metric carries its scope.

The family, and why it is one family rather than three slips
------------------------------------------------------------
Three findings across four generations have the same shape: **a quantifier or
metric stated without its denominator or scope, where the natural reading is the
false one.**

1. ``README.md`` said *"all tested pairs survive 4x grid refinement"* of a set in
   which 3 of 13 pairs had ever been tested. True as written; read as "all 13".
2. The generation-8 baseline recorded ``"ruff_exit": 0`` carrying neither scope
   nor command, so it said nothing about which paths were linted.
3. The same baseline recorded ``mypy_findings: 25`` with a *stated* scope that
   was the wrong one -- 25 is ``mypy src`` over 44 files, not the tracked tree,
   where it is 150.

Each was found by a different generation looking for something else. The rule
names the class so the fourth instance is caught by a guard rather than by luck.

What this guard reaches, and what it does not
---------------------------------------------
Two arms, both over prose:

``TestNoBareUniversalOverAFilteredSet``
    ``all|every|each`` applied to a set marked as **selected by having been
    subjected to something** -- *tested*, *refined*, *examined*, *sampled* and
    the rest of :data:`_SELECTED` -- in a unit that states no denominator. Both
    the adjectival form (*"all tested pairs"*) and the postmodifier form
    (*"every chart tested"*) are matched.

``TestEveryToolCountCarriesItsScope``
    a unit naming ``mypy``, ``ruff`` or ``pytest`` beside an integer must also
    carry the invocation or the scope that produced it. This is ``REP-01``'s
    rule for the state file, applied to prose. It **overlaps**
    ``tests/test_mypy_scope_g10.py``, which enforces the same thing for ``mypy``
    alone and has the better message for that case; that guard stays and this
    arm generalises it to the other two tools. The overlap was measured rather
    than assumed -- writing ``DOC-08``'s entry in the rules document tripped the
    generation-10 guard on the sentence quoting the defect.

**Out of reach, measured rather than asserted.** A count spelled as a word with
no denominator -- *"All three pairs put through the falsifier survived"*, where
the population is thirteen -- is a real instance of the family and these patterns
do not catch it. :meth:`test_a_worded_count_is_a_recorded_limit_of_this_guard`
pins that as a limit so it is visible rather than assumed absent, and the rule's
entry in ``docs/RULES_ENACTED.md`` states it. Widening ``all\\s+(?:three|four|
...)`` to catch it also catches *"admissibility ratio 1.000 in all three
charts"*, where three **is** the population, and a guard that demands "3 of 3"
there is a guard about typography.

``SW-20``: the subject is prose, so there is no AST and the rule's letter does
not apply; its purpose does. Both controls are implemented for each arm, this
module and the documents explaining the rule are out of the search scope, and
the exclusion is asserted rather than trusted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_claim_surface_g7 import _PROHIBITION, _read, _units
from test_witness_admissibility_g10 import CLAIM_SURFACE_G10

REPO = Path(__file__).resolve().parents[1]

#: Documents ``DOC-08`` is swept over. ``CLAIM_SURFACE_G10`` plus the addendum
#: that publishes the chart-G refinement, which is where the rule's flagship
#: sentence gets its denominator.
CLAIM_SURFACE_DOC08 = (*CLAIM_SURFACE_G10, "docs/CLOSE_ADDENDUM.md")

#: Participles that mark a set as *selected by having been subjected to
#: something*. Deliberately excludes ``measured``, ``reported`` and
#: ``committed``: "all measured values below", "every movement reported in §2"
#: and "every committed set" name populations, not filtered subsets, and a
#: pattern that took them would fire on four passages that state no subset at
#: all. Measured false positives, removed before shipping.
_SELECTED = (r"tested|refined|examined|sampled|checked|tried|evaluated|audited|"
             r"scanned|attempted|inspected|surveyed|probed|exercised")

#: *"all tested pairs"* -- the quantifier attaches to the participle directly.
_ADJECTIVAL = re.compile(
    r"\b(?:all|every|each)\s+(?:the\s+)?(?:\d+\s+)?(?:" + _SELECTED + r")\s+"
    r"[a-z]+s?\b", re.I)

#: *"every chart tested"* -- the participle postmodifies the noun.
#:
#: The negative lookahead is not cosmetic. ``docs/CHART_RECONCILIATION_g7.md``
#: writes *"each direction probed by an object drawn in its own source chart"*,
#: which describes a method and asserts nothing about a filtered subset. A
#: participle followed by an agent or a place is that construction, and without
#: the lookahead this guard flagged that sentence -- a false positive measured
#: on the real surface before this module was committed.
_POSTMODIFIER = re.compile(
    r"\b(?:all|every|each)\s+(?:of\s+the\s+)?(?:[a-z]+\s+){0,3}?"
    r"(?:" + _SELECTED + r")\b(?!\s+(?:by|from|against|in|with|on)\b)", re.I)

#: What makes the denominator available to the reader: "3 of 13", "13 of 13",
#: "all thirteen", "7/13", "of 37".
_DENOMINATOR = re.compile(
    r"\b\d[\d,]*\s+of\s+\d[\d,]*\b"
    r"|\b\d[\d,]*\s+of\s+(?:the\s+)?(?:three|four|ten|twelve|thirteen|"
    r"eighteen|thirty-seven)\b"
    r"|\ball\s+(?:three|four|ten|twelve|thirteen|eighteen|\d[\d,]*)\b"
    r"|\b\d+\s*/\s*\d+\b|\bof\s+\d[\d,]*\b", re.I)

#: Normative prose -- the rule being stated, not a claim being made. ``WIT-02``'s
#: own text is *"every witness is refined before it is counted"*, which is the
#: shape this guard forbids and is also the sentence enacting the forbidding.
#: Excluding it is the same move ``_PROHIBITION`` makes for a not-to-be-written
#: list.
_NORMATIVE = re.compile(
    r"\bmust\b|\bshall\b|\bnever\b|\brequire[sd]?\b|\bforbid\w*\b|"
    r"before it is counted|is written|\bwould\b|\bcannot\b|\bDOC-08\b", re.I)

#: A tool whose number is meaningless without the paths it ran over. ``\w*`` and
#: not ``\b``: the generation-8 defect was spelled ``ruff_exit``, and a trailing
#: word boundary does not match inside an identifier.
_TOOL = re.compile(r"\b(?:mypy|ruff|pytest)\w*", re.I)
_COUNT = re.compile(r"\b\d[\d,]*\b")

#: What makes the scope available. The invocation alternative requires
#: **whitespace after the tool name** inside the backticks, so a quoted key like
#: ``"ruff_exit": 0`` is not mistaken for the command ``ruff check src``. That
#: was a measured false negative on the operator's own example.
_SCOPE = re.compile(
    r"`[^`]*\b(?:mypy|ruff|pytest|make)\s+[^`]*`"
    r"|\b(?:src|tests|scripts)\b"
    r"|\btracked tree\b|\bwhole tree\b"
    r"|\b\d[\d,]*\s+files?\b|\bfiles?\s+checked\b"
    r"|\bscope\b|\binvocation\b|\bcommand\b", re.I)


def quantifier_offenders(text: str, document: str = "<text>"):
    """Units asserting a universal over a filtered set with no denominator.

    Extracted so the controls run through the *same* predicate the real
    documents are judged by. A control that re-implements the check proves
    nothing about the check.
    """
    offenders = []
    for label, unit in _units(text):
        if _PROHIBITION.search(unit) or _NORMATIVE.search(unit):
            continue
        m = _ADJECTIVAL.search(unit) or _POSTMODIFIER.search(unit)
        if m and not _DENOMINATOR.search(unit):
            offenders.append(f"{document} {label}: [{m.group(0)}] "
                             f"{unit.strip()[:150]}")
    return offenders


def tool_scope_offenders(text: str, document: str = "<text>"):
    """Units putting a tool count on the surface without its scope."""
    offenders = []
    for label, unit in _units(text):
        if _PROHIBITION.search(unit):
            continue
        if (_TOOL.search(unit) and _COUNT.search(unit)
                and not _SCOPE.search(unit)):
            offenders.append(f"{document} {label}: {unit.strip()[:150]}")
    return offenders


# ---------------------------------------------------------------------------

class TestNoBareUniversalOverAFilteredSet:
    """The first arm: *"all tested X"* without its ``n of N``."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_DOC08)
    def test_no_document_states_one(self, document: str) -> None:
        path = REPO / document
        if not path.is_file():
            pytest.skip(document + " does not exist yet")
        offenders = quantifier_offenders(_read(document), document)
        assert not offenders, (
            "DOC-08 -- a universal quantifier over a set that was filtered by "
            "having been tested, stated with no denominator. The natural "
            "reading is the false one: 'all tested pairs survive' over three "
            "of thirteen reads as 'all thirteen survive'. Write it as 'n of N "
            "tested, all surviving':\n  " + "\n  ".join(offenders))

    def test_the_guard_catches_the_sentence_that_forced_the_rule(self) -> None:
        """`SW-20`'s positive control, and it is the real defect, not a proxy."""
        planted = ("Those witnesses are degeneracies of the device: all tested "
                   "pairs survive 4x grid refinement and a tighter tolerance.")
        assert quantifier_offenders(planted), (
            "the guard does not flag the exact sentence DOC-08 was enacted "
            "against, so it would not have prevented the defect it exists for")

    def test_the_guard_catches_the_postmodifier_form(self) -> None:
        planted = ("The degeneracy is real and survives refinement in every "
                   "chart tested.")
        assert quantifier_offenders(planted)

    def test_the_repaired_sentence_passes(self) -> None:
        """The rule must be satisfiable, and this is the form that satisfies it."""
        repaired = ("Of 13 of 13 witness pairs refined, 12 survive 4x grid "
                    "refinement and a tighter tolerance and 1 separates.")
        assert not quantifier_offenders(repaired)

    def test_it_does_not_fire_on_the_statement_of_the_rule_itself(self) -> None:
        """`SW-20`'s negative control.

        ``WIT-02``'s text is *"every witness is refined before it is counted"*.
        It is the shape this guard forbids and it is also the sentence enacting
        the forbidding, so a guard that could not tell them apart would report a
        violation of itself forever -- the generation-6 self-matching defect.
        """
        for normative in (
                "Every witness is refined before it is counted.",
                "No bare universal quantifier over a filtered set; all tested "
                "X must be written with its denominator.",
                'Not to be written: "all tested pairs survive refinement".'):
            assert not quantifier_offenders(normative), normative

    def test_it_does_not_fire_on_a_method_description(self) -> None:
        """The measured false positive that shaped ``_POSTMODIFIER``."""
        benign = ("Measured, with each direction probed by an object drawn in "
                  "its own source chart.")
        assert not quantifier_offenders(benign)

    def test_it_does_not_fire_on_a_population(self) -> None:
        for benign in ("Environment for all measured values below: Python "
                       "3.11.9.",
                       "Retro-applied to every committed set it removes "
                       "nothing.",
                       "Every movement reported in section 2 would be an "
                       "artefact."):
            assert not quantifier_offenders(benign), benign

    def test_a_worded_count_is_a_recorded_limit_of_this_guard(self) -> None:
        """What ``DOC-08`` reaches and what it does not, measured.

        *"All three pairs put through the falsifier survived"* over a population
        of thirteen is an instance of the family, and these patterns do not
        catch it. Recorded rather than closed: the widening that would catch it
        also catches *"admissibility ratio 1.000 in all three charts"*, where
        three is the population, and demanding "3 of 3" there is a guard about
        typography rather than about meaning.

        If this assertion ever fails because the patterns were widened, that is
        good news and the right response is to delete it, not to narrow them
        back.
        """
        out_of_reach = ("All three pairs put through the falsifier survived 4x "
                        "grid refinement.")
        assert not quantifier_offenders(out_of_reach)

    def test_the_guard_is_not_vacuous_on_the_real_surface(self) -> None:
        """A pattern that can fire nowhere proves nothing by being green."""
        candidates = [d for d in CLAIM_SURFACE_DOC08
                      if (REPO / d).is_file()
                      and (_ADJECTIVAL.search(_read(d))
                           or _POSTMODIFIER.search(_read(d)))]
        assert candidates, (
            "no claim-surface document contains a quantifier this guard could "
            "read at all; it now proves nothing and should be retired rather "
            "than left green")


class TestEveryToolCountCarriesItsScope:
    """The second arm: ``REP-01``'s rule for the state file, applied to prose."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_DOC08)
    def test_no_document_states_a_bare_tool_count(self, document: str) -> None:
        path = REPO / document
        if not path.is_file():
            pytest.skip(document + " does not exist yet")
        offenders = tool_scope_offenders(_read(document), document)
        assert not offenders, (
            "DOC-08 -- a lint or type-check count on the claim surface with "
            "neither its invocation nor its scope. 25 findings is `mypy src` "
            "over 44 files and 150 is the tracked tree; the bare number reads "
            "as whichever the reader assumes:\n  " + "\n  ".join(offenders))

    def test_the_guard_catches_both_of_the_operators_examples(self) -> None:
        """`SW-20`'s positive control, on the two real defects."""
        for planted in ('The baseline records `"ruff_exit": 0`.',
                        "mypy reports 25 findings."):
            assert tool_scope_offenders(planted), planted

    def test_the_scoped_forms_pass(self) -> None:
        for repaired in (
                "Over the tracked tree -- `mypy src tests scripts`, 123 files "
                "-- it is 150.",
                "894 collected, 889 passed under "
                "`PYTHONPATH=src python -m pytest tests -q`.",
                "`ruff check src tests scripts` exits 0."):
            assert not tool_scope_offenders(repaired), repaired

    def test_it_does_not_fire_on_prose_describing_the_defect(self) -> None:
        """`SW-20`'s negative control, taken from the surface it guards.

        ``docs/G9_RESULT.md`` narrates the defect: *"the generation-8 baseline
        recorded `"ruff_exit": 0`, carrying neither scope nor command"*. The
        sentence contains the violation as its subject and states the scope
        words, which is what keeps it out of the offender list.
        """
        prose = ('The generation-8 baseline recorded `"ruff_exit": 0`, '
                 "carrying neither scope nor command.")
        assert not tool_scope_offenders(prose)

    def test_the_guard_is_not_vacuous_on_the_real_surface(self) -> None:
        n = sum(1 for d in CLAIM_SURFACE_DOC08 if (REPO / d).is_file()
                for _, unit in _units(_read(d))
                if _TOOL.search(unit) and _COUNT.search(unit))
        assert n, ("no claim-surface unit names a lint or type-check tool "
                   "beside a number; this arm proves nothing and should be "
                   "retired rather than left green")


class TestTheScopeIsAssertedNotTrusted:
    """`SW-20`: the guard's own source and the rule's documents stay out."""

    def test_this_modules_own_source_is_out_of_scope(self) -> None:
        assert "tests/test_quantifier_scope_doc08.py" not in CLAIM_SURFACE_DOC08

    def test_the_rules_document_is_out_of_scope(self) -> None:
        """``docs/RULES_ENACTED.md`` quotes every forbidden shape by design."""
        assert "docs/RULES_ENACTED.md" not in CLAIM_SURFACE_DOC08

    def test_the_addendum_is_in_scope(self) -> None:
        """A document that publishes the result and is unguarded is the gap."""
        assert "docs/CLOSE_ADDENDUM.md" in CLAIM_SURFACE_DOC08
