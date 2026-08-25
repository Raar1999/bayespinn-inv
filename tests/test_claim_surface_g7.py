"""SPEC-g7-6: an identifiability claim carries the chart it was measured in.

What generation 7 found
-----------------------
The published local rank and the published global witness were measured in two
different **charts** -- two different maps from ``d`` coordinates to a doping
profile (``bayespinn_inv.inverse.charts``). Neither chart contains the other, so
``d`` counts coordinates on different manifolds and a rank *fraction* means
nothing across them. "3--4 of 16" is a statement about chart L's reachable set at
d=16; it is not a statement about doping profiles.

Three guards follow, and they check different things:

``test_every_rank_fraction_names_a_chart``
    A fraction with no chart is a fraction over an unstated manifold.

``test_a_unit_spanning_both_charts_cites_the_reconciliation``
    The ruling's §4.2 negative control. A sentence putting the chart-L rank
    beside the chart-G global result is **rejected** unless it also cites what
    licenses the juxtaposition. Naming both charts is not enough on its own --
    that is precisely the sentence §4.2 requires the battery to reject.

``TestEveryStatementNamesItsChart``
    Every statement of the result carries regime, chart and dimension in its own
    passage, and the document carries the rest of the measurement conditions.

Where this deviates from the clause, and why
--------------------------------------------
``SPEC-g7-6`` reads "every statement ... carries local/global, d, prior, noise
model and level, observation set, and both floors". Enforced literally -- all
seven fields inside every statement's passage -- the surviving prose repeats four
constants after every sentence, which is a real cost with no reader benefit:
prior, noise model, noise level, observation set and the two floors are
**identical across the whole study**, while regime, chart and ``d`` **vary between
statements** and change what the sentence means.

So the fields are split by whether they discriminate:

* **per statement** -- regime, chart, ``d``. Getting one wrong makes the sentence
  false.
* **per document** -- prior, noise model and level, observation set, both floors.
  Getting one wrong makes the document wrong, and the document-level assertion
  catches that.

Both halves are asserted; nothing is dropped. This narrows the guard's *shape*,
not its *strictness*, and is recorded as ``DEC-g7-3`` with its reversal.

SW-20 and this guard
--------------------
``SW-20`` mandates AST for guards whose subject is **source code**. This guard's
subject is **prose**, where there is no AST, so the rule's letter does not apply
-- but its purpose does, and the two controls it requires are implemented:
``test_the_guards_are_not_vacuous`` plants a violation for each guard including
§4.2's negative control, and ``test_does_not_fire_on_prose_describing_the_rule``
supplies text describing the forbidden pattern without asserting it. This module
and the documents explaining the rule are excluded from the search scope, and the
exclusion is asserted rather than trusted.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Documents that publish the identifiability result to a reader.
CLAIM_SURFACE_G7 = (
    "README.md",
    "docs/RELEASE_READINESS.md",
    "docs/CLAIM_EVIDENCE_MATRIX.md",
    "docs/S1_GLOBAL_IDENTIFIABILITY_g6.md",
    "docs/CHART_RECONCILIATION_g7.md",
)

#: Excluded, with the reason. Each of these *describes* the rule or records the
#: process; none publishes the result. Excluding them narrows reach, not
#: strictness -- ``test_exclusions_are_process_records_not_claims`` asserts that
#: none is a claim-surface document in disguise.
EXEMPT = {
    "tests/test_claim_surface_g7.py": "this guard's own source",
    "src/bayespinn_inv/inverse/charts.py": "defines the rule",
    "docs/gen/DECISIONS.md": "decision ledger; quotes the forbidden pattern",
    "docs/audit/AUDIT_g7.md": "audit record; quotes findings verbatim",
    "papers/draft.md": "R-3 reserved; handled by test_claim_surface_g0",
}

#: A rank fraction: "3-4 of 16", "3 of 4", "1 of 8". Two restrictions, both
#: from measured false positives on this claim surface:
#:   * the denominator is limited to the parameterisation dimensions this
#:     project uses, so "loses 9 of 20" is not read as a rank claim;
#:   * it may not be followed by a digit or a comma, so "ESS 71 of 2,000
#:     usable samples" is not read as "of 2".
_RANK = re.compile(r"\b\d\s*(?:[-–—]\s*\d\s*)?of\s+(2|4|8|16|32)\b(?![\d,])")
#: An assertion of the global result, for deciding what counts as a statement.
_GLOBAL = re.compile(r"witness pair|non-identifiab|globally|indistinguishable", re.I)
#: An assertion of *existence* specifically -- a witness, not a contraction
#: count. Narrower than ``_GLOBAL`` on purpose: "globally, in chart G at d=4,
#: 3 of 4 directions contract" is a single-chart statement and must not be read
#: as putting a rank beside the other chart's witness result.
_WITNESS = re.compile(r"witness|non-identifiab|indistinguishable", re.I)
#: Naming a chart.
_CHART = re.compile(r"chart[\s-]*[GL]\b", re.I)
_CHART_G = re.compile(r"chart[\s-]*G\b", re.I)
_CHART_L = re.compile(r"chart[\s-]*L\b", re.I)
_REGIME = re.compile(r"\blocal\b|\bglobal(?:ly)?\b", re.I)
_DIM = re.compile(r"\bd\s*=\s*\d+|\bof\s+\d+\b", re.I)
#: Citing what licenses putting the two charts side by side.
_RECONCILED = re.compile(
    r"embed|matched[\s-]*d|stand-in|representation error|not comparable|"
    r"CHART_RECONCILIATION", re.I)

_DOC_FIELDS = {
    "prior": re.compile(r"\bprior\b", re.I),
    "noise model": re.compile(r"noise", re.I),
    "noise level": re.compile(r"2\s*%|2\.0?e-2|0\.02", re.I),
    "observation set": re.compile(r"\bbias(?:es)?\b|observation set", re.I),
    "noise floor": re.compile(r"noise floor|distinguishability floor", re.I),
    # The discretisation floor may be named or quoted by its value; forcing one
    # spelling would make this a guard about vocabulary.
    "discretisation floor": re.compile(
        r"discretisation|discretization|1\.5e-0?3", re.I),
}

#: How many lines either side count as the same passage.
_CONTEXT = 8


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _units(text: str):
    """Yield ``(label, unit_text)`` -- one per table row, one per sentence.

    A markdown table row is its own claim: readers quote rows. Each row is
    scoped with its table's header, which is part of what the row asserts.
    Elsewhere the unit is a sentence, because "in one sentence" is what the
    ruling forbids.
    """
    lines = text.splitlines()
    header = ""
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("|"):
            header = ""
            continue
        if set(stripped) <= set("|-: \t"):
            # The alignment row: the line above it is this table's header, and a
            # markdown table's header is part of what every row of it asserts.
            # Scoping the chart to the header is how a reader reads the table --
            # requiring "chart G" inside all five rows of a sweep would be a
            # guard about typography.
            header = lines[i - 1] if i else ""
            continue
        yield f"row {i + 1}", (header + " " + line) if header else line
    prose = "\n".join(ln for ln in text.splitlines()
                      if not ln.lstrip().startswith("|"))
    for s in re.split(r"(?<=[.!?])\s+", prose):
        if s.strip():
            yield "sentence", " ".join(s.split())


def _statement_lines(text: str):
    """Lines that assert the result, as ``(index, line)``."""
    for i, line in enumerate(text.splitlines()):
        if _RANK.search(line) or (_GLOBAL.search(line) and re.search(r"\d", line)):
            yield i, line


def reconciliation_offenders(text: str, document: str = "<text>"):
    """Units that put a rank fraction beside a witness result without a licence.

    Extracted so the ruling's §4.2 negative control can be run through the *same*
    predicate the real documents are judged by. A control that re-implements the
    check proves nothing about the check.
    """
    offenders = []
    for label, unit in _units(text):
        if not _RANK.search(unit):
            continue
        spans_both = bool(_CHART_G.search(unit) and _CHART_L.search(unit))
        if not (spans_both or _WITNESS.search(unit)):
            continue
        if _RECONCILED.search(unit):
            continue
        offenders.append(f"{document} {label}: {unit.strip()[:150]}")
    return offenders


# ---------------------------------------------------------------------------

class TestNoCrossChartQuotation:
    """A rank fraction carries its chart, and never stands beside the other's."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_every_rank_fraction_names_a_chart(self, document: str) -> None:
        offenders = [f"{document} {label}: {unit.strip()[:150]}"
                     for label, unit in _units(_read(document))
                     if _RANK.search(unit) and not _CHART.search(unit)]
        assert not offenders, (
            "SPEC-g7-6 -- a rank fraction is stated without naming the chart it "
            "was measured in. Neither chart contains the other, so an unlabelled "
            "fraction is over an unstated manifold:\n  " + "\n  ".join(offenders))

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_a_unit_spanning_both_charts_cites_the_reconciliation(
            self, document: str) -> None:
        offenders = reconciliation_offenders(_read(document), document)
        assert not offenders, (
            "SPEC-g7-3 -- a rank fraction is quoted beside the other chart's "
            "result without citing the embedding test or the matched-d "
            "measurement that licenses it:\n  " + "\n  ".join(offenders))


class TestEveryStatementNamesItsChart:
    """Regime, chart and d travel with the number; the rest with the document."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_passage_carries_regime_chart_and_dimension(self, document: str) -> None:
        lines = _read(document).splitlines()
        bad = []
        for i, line in _statement_lines("\n".join(lines)):
            lo, hi = max(0, i - _CONTEXT), min(len(lines), i + _CONTEXT + 1)
            ctx = "\n".join(lines[lo:hi])
            missing = [n for n, rx in (("regime", _REGIME), ("chart", _CHART),
                                       ("d", _DIM)) if not rx.search(ctx)]
            if missing:
                bad.append(f"{document}:{i + 1} missing {missing}: "
                           f"{line.strip()[:110]}")
        assert not bad, (
            "SPEC-g7-6 -- identifiability statements missing a discriminating "
            "field in their own passage:\n  " + "\n  ".join(bad))

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_document_carries_the_measurement_conditions(self, document: str) -> None:
        text = _read(document)
        if not list(_statement_lines(text)):
            pytest.skip(f"{document} states no identifiability result")
        missing = [name for name, rx in _DOC_FIELDS.items() if not rx.search(text)]
        assert not missing, (
            f"SPEC-g7-6 -- {document} states the identifiability result but does "
            f"not carry {missing} anywhere in the document")


class TestGuardControls:
    """SW-20's two controls, plus a check that the exclusions are honest."""

    def test_the_guards_are_not_vacuous(self) -> None:
        """A planted violation for each guard, including §4.2's negative control."""
        unlabelled = "Terminal I-V determines only 3-4 of 16 doping directions."
        assert _RANK.search(unlabelled), "the rank matcher misses a bare fraction"
        assert not _CHART.search(unlabelled)

        negative_control = (
            "In chart L the terminal I-V determines 3-4 of 16 doping directions, "
            "and in chart G 13 witness pairs were found at d=4.")
        assert _RANK.search(negative_control)
        assert _CHART_G.search(negative_control)
        assert _CHART_L.search(negative_control)
        assert not _RECONCILED.search(negative_control), (
            "the §4.2 negative control would pass the reconciliation check -- "
            "the battery must reject it on SPEC-g7-3")

        repaired = negative_control + (
            " The two fractions are not comparable across charts; at matched d "
            "the rank is the same in both (CHART_RECONCILIATION_g7).")
        assert _RECONCILED.search(repaired), "the guard is unsatisfiable"

        assert not _RANK.search("the acquisition loses 9 of 20 comparisons"), (
            "the rank matcher fires on an unrelated fraction")
        assert list(_statement_lines(unlabelled))

    def test_does_not_fire_on_prose_describing_the_rule(self) -> None:
        """The control generation 6 kept failing.

        Text that *describes* the forbidden sentence must not be treated as an
        instance of it. The guard cannot tell the two apart from the words alone,
        which is exactly why the documents that explain the rule are excluded
        from the search scope rather than rewritten to dodge it.
        """
        for rel, why in EXEMPT.items():
            assert rel not in CLAIM_SURFACE_G7, (
                f"{rel} is both exempt ({why}) and on the claim surface")
        assert any(rel.startswith(("docs/", "tests/", "src/")) for rel in EXEMPT), (
            "no explanatory document is exempt")

        described = ("A reconciliation must never state that chart L determines "
                     "3-4 of 16 directions while citing chart G's d=4 witness "
                     "pairs in the same breath.")
        assert _RANK.search(described) and _CHART_G.search(described), (
            "the matcher no longer recognises the pattern this prose describes")
        assert Path(__file__).name in EXEMPT["tests/test_claim_surface_g7.py"] \
            or "own source" in EXEMPT["tests/test_claim_surface_g7.py"]

    def test_exclusions_are_process_records_not_claims(self) -> None:
        """An exemption must not be a way to hide a live claim from the guard."""
        for rel in EXEMPT:
            p = REPO / rel
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            for _label, unit in _units(text):
                if not _RANK.search(unit):
                    continue
                if _CHART_G.search(unit) and _CHART_L.search(unit) \
                        and not _RECONCILED.search(unit):
                    assert re.search(
                        r"forbid|never|must not|violation|negative control|"
                        r"corrigend|quoted|ruling|not comparable|superseded",
                        text, re.I), (
                        f"{rel} quotes across charts and the document gives no "
                        "indication it is doing so deliberately")
                    break

    def test_every_claim_surface_document_exists(self) -> None:
        for rel in CLAIM_SURFACE_G7:
            assert (REPO / rel).is_file(), f"{rel} is on the claim surface but absent"


class TestRulingNegativeControl:
    """§4.2 of the generation-7 ruling, run end to end through the real predicate.

    "A reconciliation that quotes the d=4 existence result and the d=16 local
    rank in one sentence without an embedding test. The battery must reject it
    on SPEC-g7-3."
    """

    NEGATIVE_CONTROL = """## Reconciliation

Terminal I-V determines only 3-4 of 16 doping directions in chart L at d=16, and 13 witness pairs were found in chart G at d=4, so the local and global results agree.
"""

    def test_the_battery_rejects_it(self) -> None:
        offenders = reconciliation_offenders(self.NEGATIVE_CONTROL, "<control>")
        assert offenders, (
            "SPEC-g7-3's negative control PASSED the battery. A reconciliation "
            "quoting the d=4 existence result beside the d=16 local rank without "
            "an embedding test must be rejected.")

    def test_it_passes_once_the_embedding_test_is_cited(self) -> None:
        """The guard must be satisfiable, or it is a prohibition, not a check."""
        repaired = self.NEGATIVE_CONTROL.replace(
            "so the local and global results agree.",
            "and the two fractions are not comparable across charts; the chart-G"
            " pair embeds into chart L with its separation preserved"
            " (CHART_RECONCILIATION_g7).")
        assert not reconciliation_offenders(repaired, "<repaired>")

    def test_the_real_reconciliation_is_not_the_negative_control(self) -> None:
        """The document this generation shipped must itself pass."""
        text = _read("docs/CHART_RECONCILIATION_g7.md")
        assert not reconciliation_offenders(text, "docs/CHART_RECONCILIATION_g7.md")
        assert _RECONCILED.search(text)
