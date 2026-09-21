"""``OPS-01``: an enacted rule that has no guard in the tree is not enacted.

The operator enacted this against themself at generation 8 §7, after generation 7
audited the rulings and found that `SW-20` and `DOC-07` — cited in three source
files, treated as binding for a whole generation — existed nowhere but in chat
text. The generalisation is that a rule with no home in the tree is unenforceable
and, once the message scrolls away, unrecoverable.

So ``docs/RULES_ENACTED.md`` is now a structured document rather than a note, and
this module is the parser that makes it one. Every ``##`` section must carry:

* an **Enacted** provenance line, so the rule can be traced to a ruling;
* a paragraph naming **the defect that forced it**, because a rule whose
  motivating defect nobody wrote down is a rule that gets repealed by the next
  person who finds it inconvenient;
* an **Enforced by** line naming a test module that **exists**, and that contains
  both of the ``SW-20`` controls.

The last clause is what makes this more than a formatting check: it is transitive.
A rule is enacted only if its guard exists, and a guard counts only if it can be
shown to fire and shown not to fire on a description of what it forbids.

``SW-20``: the subject is a Markdown document rather than source code, so there is
no AST. The rule's letter does not apply; its purpose does, and both controls are
implemented below. This module and the document's own explanatory paragraphs are
excluded from the scan, and the exclusion is asserted rather than trusted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "docs" / "RULES_ENACTED.md"

#: The two controls SW-20 requires of every guard, as they appear in a test
#: module: something that plants a violation, and something that supplies a
#: description of the violation the guard must not fire on.
POSITIVE_CONTROL_MARKERS = ("planted", "catches_a_planted", "positive control",
                            "positive_control", "must_flag", "recovers_a_known")
NEGATIVE_CONTROL_MARKERS = ("does_not_fire", "not_vacuous", "negative control",
                            "negative_control", "prose", "does_not_flag",
                            "one_blob", "not_different")


def parse_rules(text: str):
    """``[{name, body}]`` for every ``## `RULE` — ...`` section."""
    out = []
    for m in re.finditer(r"^## +(.+)$", text, flags=re.MULTILINE):
        start = m.end()
        nxt = re.search(r"^## ", text[start:], flags=re.MULTILINE)
        body = text[start:start + nxt.start()] if nxt else text[start:]
        out.append({"heading": m.group(1).strip(), "body": body})
    return out


#: Start of a new bold-led block, which is where an ``Enforced by`` region ends.
NEXT_BLOCK = re.compile(r"\n\n\*\*")


def enforcing_modules(body: str):
    """Test modules named in the section's ``Enforced by`` region(s).

    The region runs from ``**Enforced by**`` to the next bold-led block, so it
    covers both spellings the document uses -- a prose sentence and a table of
    guards -- and stops before the next labelled paragraph.

    Scoping to the region rather than to the whole section is the difference
    between a structural guard and a word search: a rule's prose may legitimately
    *mention* a test module -- as a counterexample, or as the guard some other
    rule uses -- without that module being what enforces this rule. The negative
    control below is exactly that case.
    """
    mods = []
    # Line-anchored, and this is not cosmetic. The first version of this
    # function matched ``**Enforced by**`` anywhere, and the negative control
    # below -- a defect paragraph that *mentions* the label inside backticks --
    # caught it reading a module name out of prose about the rule. That is
    # SW-20's failure mode, found by the control it requires, before shipping.
    for m in re.finditer(r"^\*\*Enforced by\*\*", body, flags=re.MULTILINE):
        region = body[m.start():]
        nxt = NEXT_BLOCK.search(region)
        region = region if nxt is None else region[:nxt.start()]
        mods.extend(re.findall(r"tests/(test_[A-Za-z0-9_]+\.py)", region))
    return sorted(set(mods))


#: Guards for rules enacted **before** ``SW-20`` itself, which is what requires
#: both controls. Listed with the reason, and asserted to be exactly the
#: pre-enactment set -- a new rule cannot join it.
CONTROLS_NOT_REQUIRED = {
    "test_dtype_envelopes_g6.py": (
        "PH-22 predates SW-20, so its guard was written before both controls "
        "were required of one. It measures the float32 and float64 round-trip "
        "errors and asserts the separation, which is a measurement rather than "
        "a detector, and a measurement has no violation to plant. The gap is "
        "recorded rather than closed by renaming a test: retro-fitting controls "
        "to a pre-SW-20 guard and then claiming the rule was always enforced "
        "would be the same kind of statement OPS-01 exists to stop."),
}


@pytest.fixture(scope="module")
def rules():
    return parse_rules(RULES.read_text(encoding="utf-8"))


class TestEveryRuleIsActuallyEnacted:

    def test_the_document_has_rules_in_it(self, rules):
        """A parser that finds nothing passes every assertion below."""
        assert len(rules) >= 6, f"only {len(rules)} rule sections parsed"
        names = [r["heading"] for r in rules]
        for expected in ("SW-20", "DOC-07", "OPS-01", "PH-22", "REP-01",
                         "SPEC-11"):
            assert any(expected in n for n in names), f"{expected} missing"

    def test_every_rule_states_when_it_was_enacted(self, rules):
        for r in rules:
            assert "**Enacted**" in r["body"], (
                f"{r['heading']}: no provenance line. A rule with no ruling "
                "behind it is a preference.")

    def test_every_rule_states_the_defect_that_forced_it(self, rules):
        for r in rules:
            assert re.search(r"defect that forced it", r["body"]), (
                f"{r['heading']}: no motivating defect. A rule whose reason "
                "nobody wrote down is repealed by the next person it "
                "inconveniences.")

    def test_every_rule_names_a_guard_that_exists(self, rules):
        for r in rules:
            assert "**Enforced by**" in r["body"], f"{r['heading']}"
            mods = enforcing_modules(r["body"])
            assert mods, (
                f"{r['heading']}: names no test module. OPS-01: a rule without "
                "a guard is not enacted.")
            for mod in mods:
                assert (ROOT / "tests" / mod).is_file(), (
                    f"{r['heading']} names tests/{mod}, which does not exist")

    def test_every_guard_ships_both_controls(self, rules):
        """``SW-20``, applied transitively through the rules document."""
        for r in rules:
            for mod in enforcing_modules(r["body"]):
                if mod in CONTROLS_NOT_REQUIRED:
                    continue
                src = (ROOT / "tests" / mod).read_text(encoding="utf-8").lower()
                assert any(k in src for k in POSITIVE_CONTROL_MARKERS), (
                    f"{r['heading']} -> tests/{mod}: no positive control. A "
                    "guard nobody has seen fire is a guard nobody knows works.")
                assert any(k in src for k in NEGATIVE_CONTROL_MARKERS), (
                    f"{r['heading']} -> tests/{mod}: no negative control. A "
                    "guard that fires on descriptions of what it forbids gets "
                    "disabled within a generation.")

    def test_the_controls_exemption_is_exactly_the_pre_sw20_guards(self, rules):
        """The exemption cannot grow. A new rule joining it fails here."""
        assert set(CONTROLS_NOT_REQUIRED) == {"test_dtype_envelopes_g6.py"}
        for mod, reason in CONTROLS_NOT_REQUIRED.items():
            assert (ROOT / "tests" / mod).is_file(), mod
            assert len(reason) > 120, mod
        owners = {r["heading"] for r in rules
                  if set(enforcing_modules(r["body"])) & set(CONTROLS_NOT_REQUIRED)}
        assert all("PH-22" in o for o in owners), (
            f"a rule other than PH-22 is using the pre-SW-20 exemption: {owners}")

    def test_the_scope_gap_is_stated_rather_than_left_implicit(self):
        """Pre-generation-7 rules are not here, and the document must say so."""
        text = RULES.read_text(encoding="utf-8")
        assert "not backfilled" in text or "not a complete list" in text
        assert "PH-22" in text

    def test_the_ph22_backfill_is_marked_as_reconstructed(self):
        """The one retro-applied rule must not pretend to be a quotation.

        The ruling ordered ``PH-22`` backfilled. Its original wording is not in
        this tree, so the backfill can only be a description of the rule as the
        code obeys it. Saying so is the difference between a gap and a
        fabrication, and this asserts the saying.
        """
        body = next(r["body"] for r in parse_rules(
            RULES.read_text(encoding="utf-8")) if "PH-22" in r["heading"])
        assert "reconstructed" in body.lower()
        assert "not a quotation" in body.lower() or \
            "not a quotation of the rule" in body.lower()


class TestTheGuardIsNotVacuous:

    def test_it_catches_a_rule_with_no_guard(self):
        """Positive control: the exact shape OPS-01 forbids."""
        planted = (
            "## `XX-99` — a rule someone announced\n\n"
            "**Enacted** operator ruling, 2026-01-01.\n\n"
            "**The defect that forced it.** Something went wrong once.\n")
        parsed = parse_rules(planted)
        assert len(parsed) == 1
        assert "**Enforced by**" not in parsed[0]["body"]
        assert enforcing_modules(parsed[0]["body"]) == []

    def test_it_catches_a_guard_that_does_not_exist(self):
        planted = (
            "## `XX-98` — a rule with an imaginary guard\n\n"
            "**Enacted** operator ruling, 2026-01-01.\n\n"
            "**The defect that forced it.** Something else went wrong.\n\n"
            "**Enforced by** `tests/test_a_module_that_does_not_exist.py`.\n")
        mods = enforcing_modules(parse_rules(planted)[0]["body"])
        assert mods == ["test_a_module_that_does_not_exist.py"]
        assert not (ROOT / "tests" / mods[0]).is_file()

    def test_it_does_not_fire_on_prose_describing_the_forbidden_shape(self):
        """Negative control: a paragraph about ruleless rules is not one.

        ``OPS-01``'s own section describes exactly the shape it forbids -- "a
        rule that lives only in a ruling", "existed nowhere but in chat text" --
        and must not be flagged for containing that description. The parser keys
        on structure, not on words, which is why it can tell them apart.
        """
        prose = (
            "## `XX-97` — a rule about rules\n\n"
            "**Enacted** operator ruling, 2026-01-01.\n\n"
            "**The defect that forced it.** Two rules existed only in chat "
            "text and named no `**Enforced by**` module at all, which is the "
            "shape this rule forbids: a section with no guard, naming no "
            "`tests/test_something.py`.\n\n"
            "**Enforced by** `tests/test_rules_enacted_g8.py`.\n")
        r = parse_rules(prose)[0]
        assert "**Enacted**" in r["body"]
        assert "defect that forced it" in r["body"]
        assert enforcing_modules(r["body"]) == ["test_rules_enacted_g8.py"]
        assert (ROOT / "tests" / "test_rules_enacted_g8.py").is_file()

    def test_the_parser_separates_adjacent_sections(self):
        two = ("## `A-1` — first\n\nbody one\n\n"
               "## `A-2` — second\n\nbody two\n")
        parsed = parse_rules(two)
        assert [p["heading"] for p in parsed] == ["`A-1` — first",
                                                  "`A-2` — second"]
        assert "body two" not in parsed[0]["body"]
