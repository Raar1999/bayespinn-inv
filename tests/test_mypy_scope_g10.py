"""`REP-01` for one number in particular: a `mypy` count carries its scope.

The defect that forced it
-------------------------
`25` is what `mypy` reports over the **package**. Over the tracked tree it is
**150**. Generation 8's state file recorded the first number under the second
description — *"25 over the tracked tree"* — and generation 9 measured the
difference and corrected the state file. What generation 9 did **not** do is
reach the ten places in the documentation where "mypy 25, unchanged" had been
written across five generations with no scope at all, and the operator ruling of
2026-08-26 §4 ordered exactly that:

    Every historical "mypy unchanged at 25" — including the ones I ratified — is
    re-labelled with its scope, and the tracked-tree number becomes the carried
    baseline.

A scope carried for nine generations and stated nowhere is worse than a missing
number, because a missing number invites a check.

What this guard requires, and the two tiers it allows
------------------------------------------------------
A passage stating a `mypy` finding count must name what was scanned. Two forms
satisfy it, and the difference is deliberate:

* an **invocation** — ``mypy src``, ``python -m mypy src/bayespinn_inv``,
  ``mypy src tests scripts`` — which is what `REP-01` asks for and what the state
  file and the claim-surface documents carry;
* a **scope in words** plus the fact that it is not the tracked tree, which is
  what a *historical* gate table can honestly say. Generation-0 through
  generation-6 documents record a baseline they inherited; asserting an
  invocation into them that nobody recorded at the time would be inventing
  provenance to satisfy a guard, which is the failure this repository keeps
  finding in its own output.

``SW-20``: the subject is prose, so there is no AST; the rule's purpose is
honoured instead. Both controls are implemented, the scan's scope is derived from
the tree rather than hard-coded so it cannot silently shrink, and this module's
own source is excluded and the exclusion is asserted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_claim_surface_g7 import _units

REPO = Path(__file__).resolve().parents[1]

#: A `mypy` finding count: the word, then a bare integer within one clause.
#: Pipes are allowed because a gate table writes `| mypy | **25** |`; periods and
#: newlines are not, so the match cannot run into the next sentence. The number
#: may not touch a dot on either side, so `mypy` beside a `3.9` version claim is
#: not read as a count.
_MYPY_COUNT = re.compile(
    r"\bmypy\b[^.\n]{0,60}?(?<![\d.])\*{0,2}(\d{1,4})\*{0,2}(?![\d.])", re.I)

#: What names the scope. The first three alternatives are invocations; the rest
#: are the ways a passage can name the scanned surface without asserting a
#: command nobody recorded.
_SCOPE = re.compile(
    r"mypy\s+src|src/bayespinn_inv|src\s+tests\s+scripts"
    r"|tracked\s+tree|the\s+package\s+only"
    r"|\b\d{1,3}\s+(?:source\s+)?files\s+checked"
    r"|\(\s*\d{1,3}\s+source\s+files?\s*\)"
    r"|files_checked|mypy_package|mypy_tracked_tree|\bscope\b", re.I)

#: This guard's own source and the rule's own description. Asserted below, not
#: trusted: `SW-20`'s negative-control clause applied to the scan's own scope.
EXEMPT = {
    "tests/test_mypy_scope_g10.py": "this guard's own source",
}


def _documents():
    """Every tracked Markdown document that mentions `mypy`.

    Derived from the tree rather than listed, so a new document carrying a
    `mypy` number is in scope the moment it is written. A hard-coded list is how
    a guard's reach quietly stops matching the tree it guards.
    """
    paths = sorted(REPO.joinpath("docs").rglob("*.md"))
    paths += [REPO / "README.md", REPO / "CHANGELOG.md"]
    out = []
    for p in paths:
        rel = p.relative_to(REPO).as_posix()
        if rel in EXEMPT or not p.is_file():
            continue
        if "mypy" in p.read_text(encoding="utf-8").lower():
            out.append(rel)
    return out


def scope_offenders(text: str, document: str = "<text>"):
    """Passages stating a `mypy` count with no scope anywhere in them."""
    offenders = []
    for label, unit in _units(text):
        m = _MYPY_COUNT.search(unit)
        if not m or _SCOPE.search(unit):
            continue
        offenders.append(f"{document} {label}: [{m.group(1)}] {unit.strip()[:130]}")
    return offenders


class TestEveryMypyCountCarriesItsScope:

    @pytest.mark.parametrize("document", _documents())
    def test_no_document_states_a_mypy_count_without_its_scope(self, document):
        offenders = scope_offenders(
            (REPO / document).read_text(encoding="utf-8"), document)
        assert not offenders, (
            "REP-01, as the ruling of 2026-08-26 section 4 applied it to mypy: a "
            "finding count with no scope cannot be checked, only believed. 25 is "
            "the package; the tracked tree is 150, and one description was "
            "carried under the other for nine generations:\n  "
            + "\n  ".join(offenders))

    def test_the_guard_catches_the_exact_historical_shape(self):
        """`SW-20` positive control: the sentence this rule exists to reach."""
        assert scope_offenders("mypy **25**, unchanged from the baseline."), (
            "the guard let through the exact phrase the ruling names, which is "
            "the only phrase it was enacted to catch")

    def test_the_guard_catches_it_in_a_gate_table_too(self):
        planted = ("| gate | result |\n|---|---|\n"
                   "| mypy | **25** findings — unchanged |\n")
        assert scope_offenders(planted), (
            "a gate table row puts a pipe between the word and the number; a "
            "pattern that stopped at the pipe would miss every historical "
            "instance, which live in gate tables")

    def test_an_invocation_satisfies_it(self):
        assert not scope_offenders(
            "`mypy src` reports 25 findings, unchanged from the baseline.")

    def test_a_named_scope_satisfies_it(self):
        assert not scope_offenders(
            "mypy **25**, the package only and never the tracked tree.")

    def test_a_version_number_is_not_a_finding_count(self):
        """`SW-20` negative control: prose about the floor, not about findings."""
        assert not scope_offenders(
            "The `[tool.mypy]` comment asserted the 3.9 claim is backed by CI")

    def test_prose_describing_the_defect_does_not_fire(self):
        """The second negative control: the correction itself quotes the shape."""
        assert not scope_offenders(
            'The note "25 over the tracked tree" is wrong: 25 is `mypy src`.')

    def test_the_scan_is_not_vacuous(self):
        docs = _documents()
        assert len(docs) >= 5, (
            f"only {len(docs)} documents mention mypy; if the documentation "
            "stopped quoting mypy counts this guard proves nothing and should "
            "be retired rather than left green")

    def test_the_exemption_is_this_modules_own_source_and_nothing_else(self):
        assert set(EXEMPT) == {"tests/test_mypy_scope_g10.py"}
        assert "tests/test_mypy_scope_g10.py" not in _documents()
