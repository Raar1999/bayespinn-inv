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
#:
#: Generation 8 adds ``docs/G8_RESULT.md`` and a third chart. Both are widenings
#: of this guard's reach, not of its strictness: a document that publishes the
#: result and is not on this list is unguarded, and a chart the regexes cannot
#: name is a chart whose rank fractions travel unlabelled.
CLAIM_SURFACE_G7 = (
    "README.md",
    "docs/RELEASE_READINESS.md",
    "docs/CLAIM_EVIDENCE_MATRIX.md",
    "docs/S1_GLOBAL_IDENTIFIABILITY_g6.md",
    "docs/CHART_RECONCILIATION_g7.md",
    "docs/G8_RESULT.md",
    "docs/G9_RESULT.md",
    "docs/NOVELTY_AUDIT.md",
    # The closing ruling's document. It publishes the free check, the spine and
    # the search-form rewrite, so it belongs here and not in EXEMPT: a document
    # that states the result and is not on this list is unguarded, which is the
    # defect this tuple exists to prevent.
    "docs/CLOSE_RULING.md",
    # The one bounded refinement authorised after the close. It publishes the
    # chart-G witness coverage and the recounted ridge, so it publishes the
    # result and joins the list on the same reasoning as the line above.
    "docs/CLOSE_ADDENDUM.md",
    # The paper, joined at the close. It publishes the local rank, the
    # observation-set result and the witness sets, so by this tuple's own stated
    # rule -- a document that states the result and is not on this list is
    # unguarded -- it belongs here. It was absent only because ``R-3`` reserved
    # ``papers/**``; the close ruling released it.
    "papers/draft.md",
    # Added at the close-out audit of 2026-08-29, which asked which documents
    # publish a result and are not on this list. These two do and were not.
    #
    # ``docs/G11_RESULT.md`` is the same class as the G8, G9 and G10 result
    # documents already here -- the tuple simply stopped growing at G10 while the
    # loop ran to G14.
    #
    # ``ADR-0007`` is Accepted, superseded by nothing, and its Context paragraph
    # publishes the local rank. A live decision record a reader consults is a
    # claim surface whatever its directory is called.
    "docs/G11_RESULT.md",
    "docs/adr/ADR-0007-the-oracle-arbitrates-global-identifiability.md",
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
    # --- Added by the close-out audit of 2026-08-29, under ``AGE-01``. --------
    # Each states a result somewhere and none publishes one: they are dated
    # records of what was measured, ruled or corrected at a moment. Listing them
    # is what makes this dict and CLAIM_SURFACE_G7 *exhaustive* over the tree, so
    # a document can no longer state a result and be on neither list -- which is
    # how ``papers/draft.md``, ``docs/G11_RESULT.md`` and ``ADR-0007`` came to sit
    # off-surface for several generations each.
    "CHANGELOG.md": "dated history; entries state what was true at their date, "
                    "including claims later withdrawn",
    "RULINGS.md": "self-ruling record; ratifies and quotes",
    "docs/AUDIT_MASTER.md": "the findings ledger; records and quotes findings",
    "docs/RULES_ENACTED.md": "states the rules, and quotes the shapes they forbid",
    "docs/G12_RESULT.md": "generation record. Its rank-shaped text is reproduction "
                          "controls -- '8 of 8' -- not an identifiability result",
    "docs/G13_RESULT.md": "generation record; same, '8 of 8 identical'",
    "docs/G14_RESULT.md": "generation record; same, '8 of 8' singular values",
    "docs/HIST01_REPAIR_g11.md": "repair record; quotes a commit subject",
    "docs/REPRO01_LEAF_AUDIT_g6.md": "artefact-leaf audit; quotes published "
                                     "numbers to check them against artefacts",
    "docs/audit/AUDIT_g0.md": "audit record; quotes the defective rows verbatim",
    "docs/audit/AUDIT_g6.md": "audit record; re-measurement table",
    "docs/audit/AUDIT_g10.md": "audit record; quotes the ruling's clause",
    "docs/gen/FINAL_REPORT_v1.md": "superseded by FINAL_REPORT_v2",
    "docs/gen/FINAL_REPORT_v2.md": "dated report of generations 0-6, TERMINATED. "
                                   "Adding chart labels invented at generation 7 "
                                   "to a generation-6 report would be overwriting "
                                   "a historical record, not scoping a live claim",
    "docs/gen/GEN_g6.md": "generation record, superseded by the result documents",
    "papers/CORRIGENDA_g6.md": "corrigenda record; quotes the defective text in "
                              "order to correct it",
    # --- Added by the close-out order of 2026-08-29 T3-T6, under ``AGE-01``. --
    # The order asked for two new documents and did not name this obligation,
    # because it was written against the rules of its own date and the rule it
    # needed was enacted in the commit it was written against. Deciding is the
    # cheap half; noticing the decision was needed is the rule.
    #
    # Verified load-bearing, 2026-08-29: with these two entries removed,
    # ``tests/test_age01_surface_coverage_close.py`` fails and names both files
    # with the claim kinds it found in them --- ``ordering,rank,spectral`` and
    # ``ordering,spectral``. The guard that makes this dict load-bearing is that
    # file, not this one; ``test_claim_surface_g7.py`` alone stays green either
    # way. Checked rather than assumed, which is the only reason to trust it.
    "docs/PAPER_AUDIT_g15.md": "editorial audit; quotes the paper's claims in "
                               "order to assess how they read, and publishes "
                               "none of its own",
    "docs/PAPER_RECOMMENDATIONS_g15.md": "proposal record; quotes current and "
                                         "proposed claim text side by side. "
                                         "Nothing in it is applied, so a "
                                         "sentence in it is a proposal rather "
                                         "than a statement",
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
#: Naming a chart. Chart J joined at generation 8; a chart the guard cannot name
#: is a chart whose rank fractions travel unlabelled past it.
_CHART = re.compile(r"chart[\s-]*[GLJ]\b", re.I)
_CHART_G = re.compile(r"chart[\s-]*G\b", re.I)
_CHART_L = re.compile(r"chart[\s-]*L\b", re.I)
_CHART_J = re.compile(r"chart[\s-]*J\b", re.I)
_CHARTS = (("G", _CHART_G), ("L", _CHART_L), ("J", _CHART_J))
#: A regime word. "locally" was not matched until generation 8 found the
#: asymmetry -- "globally" was accepted and "locally" was not, which forced
#: awkward prose to satisfy a guard rather than a reader.
_REGIME = re.compile(r"\blocal(?:ly)?\b|\bglobal(?:ly)?\b", re.I)
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
        named = [name for name, rx in _CHARTS if rx.search(unit)]
        spans_both = len(named) >= 2
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


#: A witness-search budget: the pair count a search examined. These are the three
#: denominators this repository has, and quoting two of them in one breath is the
#: frequency comparison every ruling since generation 6 has forbidden.
_PAIR_COUNTS = re.compile(r"\b1,999,000\b|\b719,400\b")


def frequency_offenders(text: str, document: str = "<text>"):
    """Units that put two searches' budgets side by side without a disclaimer.

    ``SPEC-g8`` carries forward: *frequencies stay uncompared across charts*.
    Existence is a search outcome and transfers; frequency is a density estimate
    and does not, and three searches at three budgets over three priors are
    existence proofs.

    Deliberately narrow. It matches the literal pair counts rather than trying to
    recognise "a frequency", because a guard that tries to parse the concept
    fires on the sentences that forbid it and gets disabled. Its scope is the one
    comparison the rulings name; the rest is enforced by review, and
    ``docs/audit/AUDIT_g8.md`` says so rather than implying this guard is
    complete.
    """
    offenders = []
    for label, unit in _units(text):
        if len(_PAIR_COUNTS.findall(unit)) < 2:
            continue
        if re.search(r"not comparable|do not compare|uncompared|different "
                     r"priors?|existence proof", unit, re.I):
            continue
        offenders.append(f"{document} {label}: {unit.strip()[:150]}")
    return offenders


#: Denominators for which generation 8 measured a population gap at the
#: operational cutoff, so a bare integer rank is licensed. Read from the
#: measurement rather than written down, so the guard tracks the artefact instead
#: of a remembered sentence; the fallback is the measured answer at the time this
#: was written, for a checkout without the artefact.
def _licensed_denominators():
    path = REPO / "outputs" / "g8" / "ranks.json"
    if not path.is_file():
        return {4}
    import json
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    return {c["n_parameters"] for c in cells.values()
            if c["bare_integer_rank_justified"]}


#: A cutoff, however the passage spells it.
_CUTOFF = re.compile(r"\d\s*%|noise|cutoff|floor|threshold", re.I)

#: A unit that *forbids* a shape rather than asserting it. Deliberately narrow:
#: it is the vocabulary of a prohibition, and it excludes "not comparable",
#: which is a disclaimer attached to a claim rather than a prohibition of one.
#: Without this the guard fires on the passages that state the rule -- the
#: SW-20 failure mode -- and with anything wider it becomes a way to smuggle a
#: bare rank past it behind a disclaimer.
_PROHIBITION = re.compile(
    r"not to be written|must not|may not|never (?:appear|be quoted|quote)|"
    r"forbidden|do not quote|not supported", re.I)


def bare_rank_offenders(text: str, document: str = "<text>",
                        licensed=None):
    """Rank fractions at an unlicensed denominator, quoted without a cutoff.

    ``SPEC-11``, enacted at generation 8 §5: *a bare integer rank appears only
    where a gap justifies it*. Generation 7 measured where that is -- the
    operational cutoff falls inside the spectrum's largest multiplicative gap at
    ``d = 4`` in both older charts and at no other cell -- so at every other
    denominator the number is a threshold count and may not travel without its
    threshold.

    The licensed set is read from ``outputs/g8/ranks.json`` rather than written
    here, so that re-measuring the cells moves the guard with them.
    """
    lic = _licensed_denominators() if licensed is None else licensed
    offenders = []
    for label, unit in _units(text):
        for m in _RANK.finditer(unit):
            if int(m.group(1)) in lic:
                continue
            if _CUTOFF.search(unit) or _PROHIBITION.search(unit):
                continue
            offenders.append(f"{document} {label}: {unit.strip()[:150]}")
            break
    return offenders


class TestEveryUnlicensedRankCarriesItsCutoff:
    """``SPEC-11``: at a denominator with no population gap, the rank is a count."""

    def test_the_licensed_set_is_read_from_the_measurement(self) -> None:
        lic = _licensed_denominators()
        assert lic, "no denominator is licensed; the guard would flag everything"
        assert 16 not in lic, (
            "d=16 became licensed, which contradicts the measured spectra; if "
            "that is real, re-measure and say so, do not let it pass silently")

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_no_document_quotes_a_bare_unlicensed_rank(self, document: str) -> None:
        offenders = bare_rank_offenders(_read(document), document)
        assert not offenders, (
            "SPEC-11 -- a rank fraction at a denominator with no population gap "
            "at the cutoff is quoted with no cutoff in its own passage. It is a "
            "threshold count, not a boundary between populations, and must "
            "carry the threshold:\n  " + "\n  ".join(offenders))

    def test_the_guard_catches_a_planted_bare_rank(self) -> None:
        planted = ("In chart L the Jacobian determines only 3-4 of 16 doping "
                   "degrees of freedom.")
        assert bare_rank_offenders(planted, licensed={4})

    def test_the_guard_passes_the_same_rank_with_its_cutoff(self) -> None:
        repaired = ("In chart L at 2% measurement noise the Jacobian determines "
                    "only 3-4 of 16 doping degrees of freedom.")
        assert not bare_rank_offenders(repaired, licensed={4})

    def test_the_guard_does_not_fire_on_a_licensed_denominator(self) -> None:
        """Negative control: `d = 4` is where the gap is, so it needs nothing."""
        licensed = "In chart G at d=4, 3 of 4 directions are identifiable."
        assert not bare_rank_offenders(licensed, licensed={4})

    def test_the_guard_does_not_fire_on_prose_describing_the_rule(self) -> None:
        """The SW-20 control, and the one that actually bites here.

        ``docs/CHART_RECONCILIATION_g7.md``'s *not to be written* list quotes
        "3-4 of 16" as an example of the forbidden shape. A word-matching guard
        cannot tell that from the shape itself, so the prohibition vocabulary is
        what separates them -- and it is kept narrow for the reason the next test
        checks.
        """
        prose = ('Not supported, and not to be written: the local "3-4 of 16" '
                 "of chart L at d=16 beside chart G's result.")
        assert not bare_rank_offenders(prose, licensed={4})

    def test_a_disclaimer_is_not_a_prohibition(self) -> None:
        """The loophole the narrow vocabulary exists to close.

        "not comparable" is something a *claim* carries, not something a
        prohibition says, so it must not buy an exemption from the cutoff
        requirement. If it did, every bare rank could be smuggled past this
        guard by appending three words.
        """
        smuggled = ("Chart L determines 3-4 of 16 doping directions, which is "
                    "not comparable with chart G's fraction.")
        assert bare_rank_offenders(smuggled, licensed={4})


class TestNoFrequencyComparison:
    """Two searches' budgets may not stand side by side without a disclaimer."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G7)
    def test_no_document_compares_two_search_budgets(self, document: str) -> None:
        offenders = frequency_offenders(_read(document), document)
        assert not offenders, (
            "frequencies stay uncompared across charts -- two search budgets "
            "are quoted in one unit with nothing saying they are not "
            "comparable:\n  " + "\n  ".join(offenders))

    def test_the_guard_catches_a_planted_comparison(self) -> None:
        planted = ("Chart G found 13 witnesses in 1,999,000 pairs and chart L "
                   "found 37 in 719,400, so chart L is denser.")
        assert frequency_offenders(planted)

    def test_the_guard_does_not_fire_on_the_disclaimer(self) -> None:
        """Negative control: the sentence that states the rule states the numbers.

        Both budgets have to appear together somewhere, precisely so a reader can
        see that neither can be quoted without the other. The disclaimer is what
        distinguishes stating them from comparing them.
        """
        allowed = ("Chart G examined 1,999,000 pairs and chart L 719,400; the "
                   "two rates are not comparable, because the chart, the "
                   "dimension and the sampling density all differ.")
        assert not frequency_offenders(allowed)

    def test_the_guard_does_not_fire_on_one_budget_alone(self) -> None:
        assert not frequency_offenders("13 witness pairs among 1,999,000 examined")


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

        # Generation 8: the regime matcher is symmetric. It accepted "globally"
        # and rejected "locally", which is a guard shaping prose rather than
        # checking it.
        assert _REGIME.search("measured locally, in chart L")
        assert _REGIME.search("measured globally, in chart G")
        assert _REGIME.search("a local Jacobian rank")
        assert not _REGIME.search("a locale-dependent format string")
        assert list(_statement_lines(unlabelled))

        # Generation 8: the third chart must be caught by the same battery, and
        # a fraction naming chart J alongside chart G must need the same licence.
        j_only = "In chart J at d=16 the local rank is 5 of 16 at a 2% cutoff."
        assert _CHART.search(j_only), "the chart matcher cannot see chart J"
        assert _RANK.search(j_only)
        assert not reconciliation_offenders(j_only), (
            "a single-chart statement must not need a reconciliation licence")

        j_and_g = ("Chart J gives 5 of 16 at d=16 and chart G gives 3 of 4 at "
                   "d=4.")
        assert reconciliation_offenders(j_and_g), (
            "a fraction spanning chart J and chart G must be rejected without a "
            "licence, exactly as one spanning G and L is")

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
