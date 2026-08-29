"""DOC-07: a commit message never asserts a measured count or metric.

Why the rule exists
-------------------
Commit ``1a090f0`` asserts ``420 passed``. The tree it committed produced 437
passed and 1 failed. ``R-4`` makes a commit message uncorrectable, so the false
claim is permanent and ``d3b7693`` could only correct it forward.

A commit message is the one surface in this repository that no test can repair
after the fact. ``DOC-07`` removes the class of claim that would need repairing:
messages reference the manifest or artefact carrying the number instead of
restating it.

Scope
-----
Only commits created **after** the rule was enacted are in scope. Earlier history
is uncorrectable under ``R-4``, and a guard that fails on history nobody can fix
is a guard people switch off. ``1a090f0`` is therefore used as the **positive
control** rather than as a failure: the guard must flag it, and if it stops doing
so the guard has gone vacuous.

See ``docs/RULES_ENACTED.md``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from commit_map import resolve_commit

REPO = Path(__file__).resolve().parents[1]

#: The commit that enacts DOC-07 in this tree, **as recorded**. Messages from
#: here forward are in scope; anything earlier is uncorrectable history.
#:
#: ``HIST-01``: ``git filter-repo`` renamed every commit on 2026-08-28, so both
#: hashes below stopped resolving and this module's two live assertions silently
#: **skipped** -- ``_git`` turns a non-zero git exit into ``pytest.skip``. The
#: guard that polices ``DOC-07`` was therefore not running over the range it was
#: written for, and a green suite said nothing about it. The recorded hashes are
#: kept verbatim and resolved through the verified correction map at point of
#: use (``docs/COMMIT_HASH_MAP_g11.json``, ``docs/HIST01_REPAIR_g11.md``).
ENACTED_AT_AS_RECORDED = "3e05c9da55e152c8305838ff1da4166207051826"
ENACTED_AT = resolve_commit(ENACTED_AT_AS_RECORDED) or ENACTED_AT_AS_RECORDED

#: The generation-6 message that forced the rule. Its own text is the control.
POSITIVE_CONTROL_AS_RECORDED = "1a090f0"
POSITIVE_CONTROL = (resolve_commit(POSITIVE_CONTROL_AS_RECORDED)
                    or POSITIVE_CONTROL_AS_RECORDED)

#: Assertions of a measured count or metric. Deliberately narrow: it targets the
#: shape ``1a090f0`` used, not every digit in a message. A commit that says
#: "generation 6" or quotes a SHA must not be flagged.
_COUNT_CLAIMS = (
    re.compile(r"\b\d[\d,]*\s+(?:tests?\s+)?(?:passed|passing|failed|failing)\b", re.I),
    re.compile(r"\b\d[\d,]*\s*/\s*\d[\d,]*\s+(?:tests?|passed|passing)\b", re.I),
    re.compile(r"\b\d[\d,]*\s+of\s+\d[\d,]*\s+(?:tests?|passed|passing)\b", re.I),
    re.compile(r"\b(?:tests?|suite)\s*[:=]\s*\d[\d,]*\b", re.I),
)

# ---------------------------------------------------------------------------
# Generation 8: the same rule, widened, because it did not catch its own author
# ---------------------------------------------------------------------------
#
# ``01f0281`` -- the generation-8 machinery commit, whose message enacts OPS-01 --
# asserts "seven production call sites across three grid resolutions". That is a
# measured count of this tree, and it is **wrong**: the census found five call
# sites in ``src/`` and nine more in ``tests/``. Exactly the failure DOC-07 names,
# in the commit enacting the rule that rules must be guarded, and the guard above
# did not see it because it matches digits next to "passed"/"tests" and nothing
# else.
#
# The narrowness was deliberate and is recorded as such above. It was also too
# narrow. The widened patterns below catch a cardinal -- digit **or word** --
# standing in front of a noun that names something a run or a scan counts.
#
# Two design choices, both stated rather than tuned:
#
# * the vocabulary is explicit and short. A heuristic for "is this noun a
#   measurement" would fire on "three pieces of apparatus" and get disabled
#   within a generation, which is how guards die (see the g6 bernoulli guard).
# * ``generations`` is deliberately **excluded**. "six generations of results"
#   is a fact about this project's history, not a measurement this tree
#   produced; it cannot drift and it cannot be mis-transcribed from a run.
#
# Scope, following DOC-07's own design: the wide patterns apply to commits **after**
# the widening, because ``R-4`` makes earlier messages uncorrectable and a guard
# that fails on uncorrectable history is a guard people disable. ``01f0281`` is
# therefore out of scope and is instead the **positive control** -- the guard must
# flag it, exactly as ``1a090f0`` is the control for the original patterns.

#: Nouns that name something a run or a scan counts.
_MEASURED_NOUNS = (
    r"call[\s-]sites?|tests?|cells?|witnesses|witness|pairs?|findings?|"
    r"violations?|records?|modules?|files?|guards?|controls?|sweeps?|draws?|"
    r"samples?|resolutions?|basins?|clusters?|anchors|nodes?|clauses?|"
    r"call sites?"
)
_CARDINALS = (r"\d[\d,]*|one|two|three|four|five|six|seven|eight|nine|ten|"
              r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|twenty")

#: A cardinal directly in front of a measured noun, with at most one adjective
#: between them. The negative lookbehind keeps identifiers out: ``generation-6``,
#: ``DEC-g7-1`` and ``py39`` are not counts of anything.
_COUNT_CLAIMS_WIDE = (
    re.compile(rf"(?<![\w-])(?:{_CARDINALS})\s+(?:[a-z]+[\s-])?"
               rf"(?:{_MEASURED_NOUNS})\b", re.I),
)

#: The commit that widens the rule. Messages after it are in scope for the wide
#: patterns.
WIDENED_AT_SUBJECT = "g8 machinery: one reconstruction operator"

#: The message that forced the widening. Its own text is the control.
POSITIVE_CONTROL_WIDE_SUBJECT = WIDENED_AT_SUBJECT


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, cwd=str(REPO),
                         timeout=60)
    if out.returncode != 0:
        pytest.skip(f"git {' '.join(args)} unavailable: "
                    f"{out.stderr.decode('utf-8', 'replace')[:200]}")
    return out.stdout.decode("utf-8", "replace")


def offending_claims(message: str):
    """Substrings of ``message`` that assert a measured count or metric."""
    return [m.group(0) for rx in _COUNT_CLAIMS for m in rx.finditer(message)]


def offending_claims_wide(message: str):
    """As above, under the generation-8 widened patterns."""
    return [m.group(0) for rx in _COUNT_CLAIMS_WIDE for m in rx.finditer(message)]


def _sha_of_subject(subject: str):
    """Newest commit whose subject starts with ``subject``, or ``None``."""
    raw = _git("log", "--format=%H%x1f%s")
    for line in raw.splitlines():
        sha, _, subj = line.partition("\x1f")
        if subj.startswith(subject):
            return sha.strip()
    return None


def _in_scope_commits():
    """Commits from the enactment commit to HEAD, newest first."""
    raw = _git("log", "--format=%H%x1f%B%x1e", f"{ENACTED_AT}^..HEAD")
    for record in raw.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        sha, _, body = record.partition("\x1f")
        if sha.strip() == ENACTED_AT:
            # The enactment commit itself is the boundary, and in scope.
            pass
        yield sha.strip(), body


def test_no_commit_since_enactment_asserts_a_count():
    offenders = []
    for sha, body in _in_scope_commits():
        claims = offending_claims(body)
        if claims:
            offenders.append(f"{sha[:9]}: {claims}")
    assert not offenders, (
        "DOC-07 -- a commit message asserts a measured count or metric. A commit "
        "message cannot be corrected under R-4, so the claim would be permanent. "
        "Reference the manifest or artefact instead:\n  " + "\n  ".join(offenders))


def test_the_guard_catches_the_message_that_forced_the_rule():
    """Positive control. If this stops firing, the guard has gone vacuous."""
    body = _git("log", "-1", "--format=%B", POSITIVE_CONTROL)
    claims = offending_claims(body)
    assert claims, (
        f"DOC-07's guard did not flag {POSITIVE_CONTROL}, the commit whose "
        f"message asserts a test count the tree did not produce. The guard is "
        f"vacuous.\nmessage was:\n{body[:600]}")


@pytest.mark.parametrize("text", [
    "g7 machinery: three pieces of apparatus, no results yet",
    "counts are in outputs/ci_local_g7/ and the manifests, not in this message",
    "supersedes 1a090f0 and d3b7693; see generation 6",
    "fixes 4 of the 16 doping anchors in the chart definition",
    "bump numpy to 1.22 and scipy to 1.10",
])
def test_does_not_fire_on_ordinary_messages(text: str):
    """The negative control: digits are fine; asserted *test counts* are not."""
    assert not offending_claims(text), f"fired on: {text!r}"


@pytest.mark.parametrize("text", [
    "all 420 passed",
    "420 tests passed",
    "436/437 passing",
    "419 of 420 tests passing",
    "tests: 470",
])
def test_fires_on_each_forbidden_shape(text: str):
    """One planted violation per pattern, so a dead pattern cannot hide."""
    assert offending_claims(text), f"missed: {text!r}"

# ---------------------------------------------------------------------------
# The widened rule
# ---------------------------------------------------------------------------

#: `DOC-07` violations that are on the record permanently.
#:
#: `R-4` makes a commit message permanent, and the operator ruling of
#: 2026-08-28 prohibits `--amend` and history rewriting "without exception", so
#: a violation committed after the widening cannot be removed. It is parked
#: here -- named, with its exact offending phrase -- rather than erased, or
#: excluded by moving the guard's range, which is the standards drift `IA-2`
#: exists to catch.
#:
#: Each entry must STILL offend, which makes this dict a history-rewrite
#: detector as well as a record: if a parked violation stops offending, the
#: commit it names was rewritten. Both directions, exactly like
#: `test_claim_surface_g0.py::TestParkedPapersInstance`.
PARKED_DOC07_VIOLATIONS = {
    "f00b6a025": (
        '"Two findings from the suite" -- generation 12. Caught by this guard '
        "in the same generation that restored it: HIST-01 had left it skipping "
        "since the 2026-08-28 rewrite, so it had not policed a commit message "
        "for a generation. The first thing it did on being restored was catch "
        "the loop that restored it."),
    "f34edc138": (
        '"twelve tests" -- generation 13 housekeeping, the commit that updated '
        "the README badge after the commit-hook guard was added. The work order "
        "carrying that task named DOC-07 and said in as many words: no "
        "spelled-out counts. Spelling the number as a word rather than a digit "
        "is not a way around the rule -- that is precisely the shape the "
        "generation-8 widening was written to catch, and it caught it. R-4 "
        "makes the message permanent; the badge itself is the artefact the "
        "message should have pointed at."),
    "8e7983868": (
        "generation 13, and not a claim at all -- the message that parked "
        "f34edc138 above, which the guard flagged because it QUOTES the "
        "offending phrase while explaining it. The detector matches text, so "
        "it cannot separate use from mention: a message asserting a count and "
        "a message describing one that was asserted look identical to it. "
        "Parking rather than rewording, because R-4 applies to this message "
        "too. The practical consequence is recorded as OPS-03 in "
        "docs/AUDIT_MASTER.md: a message about a parked violation must not "
        "restate the phrase, or the register grows one entry per explanation."),
    "eaf7d1ad2": (
        '"three guard limitations this exposed" -- the close-out paper work of '
        "2026-08-29, in the message committing docs/PAPER_WORK_g15.md. The "
        "count is of something a scan measured, and the document's own section "
        "3 is the artefact the message should have pointed at instead of "
        "restating it. Exactly the shape the generation-8 widening was written "
        "to catch -- and caught in a message whose subject was a document about "
        "guards that check presence rather than correctness, which is the same "
        "defect class one level up. R-4 and the 2026-08-28 prohibition on "
        "--amend both apply, so it is parked rather than reworded. Per OPS-03 "
        "the message parking it does not restate the phrase."),
    "2fc81c400": (
        '"six\\nfiles" -- the message that parked eaf7d1ad2 above. It obeyed '
        "OPS-03 to the letter, restating none of the parked phrase, and then "
        "asserted a *different* count in the same breath: the figure artefacts "
        "regenerating identically. So OPS-03 is necessary and not sufficient, "
        "and the register grew anyway. The lesson the loop is recording against "
        "itself: avoiding the named phrase is not the rule, and the rule is "
        "that a message references the artefact instead of counting anything. "
        "Note also that the phrase spans a line break -- the detector matches "
        "across the wrap, so hand-wrapping a message cannot hide a count and "
        "was not trying to. R-4 applies; parked, not reworded."),
}


def test_no_commit_since_the_widening_asserts_a_spelled_out_count():
    widened_at = _sha_of_subject(WIDENED_AT_SUBJECT)
    if widened_at is None:
        pytest.skip("the widening commit is not in this history")
    raw = _git("log", "--format=%H%x1f%B%x1e", f"{widened_at}..HEAD")
    offenders = []
    for record in raw.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        sha, _, body = record.partition("\x1f")
        claims = offending_claims_wide(body)
        if claims:
            offenders.append((sha.strip(), claims))

    unparked = [f"{sha[:9]}: {claims}" for sha, claims in offenders
                if sha[:9] not in PARKED_DOC07_VIOLATIONS]
    assert not unparked, (
        "DOC-07, widened at generation 8 -- a commit message asserts a count of "
        "something a run or a scan measured. R-4 makes it permanent. Reference "
        "the manifest or the artefact:\n  " + "\n  ".join(unparked))

    still_offending = {sha[:9] for sha, _ in offenders}
    vanished = sorted(set(PARKED_DOC07_VIOLATIONS) - still_offending)
    assert not vanished, (
        f"a parked DOC-07 violation no longer offends: {vanished}. R-4 makes "
        "these permanent, so the only way one disappears is a history rewrite. "
        "If the rewrite was authorised, delete the parked entry in the same "
        "commit and say so; if it was not, this is an OPS-02 finding.")


def test_the_widened_guard_catches_the_message_that_forced_it():
    """Positive control, and it is this repository's own machinery commit.

    ``01f0281`` says "seven production call sites across three grid resolutions".
    The census found five in ``src/``. A wrong measured count, permanent under
    ``R-4``, in the commit that enacts OPS-01. If this stops firing the widening
    has gone vacuous.
    """
    sha = _sha_of_subject(POSITIVE_CONTROL_WIDE_SUBJECT)
    if sha is None:
        pytest.skip("the control commit is not in this history")
    body = _git("log", "-1", "--format=%B", sha)
    claims = offending_claims_wide(body)
    assert claims, (
        f"the widened guard did not flag {sha[:9]}, whose message asserts a "
        f"count the census contradicts. It is vacuous.\nmessage:\n{body[:600]}")
    assert any("call site" in c.lower() for c in claims), claims


@pytest.mark.parametrize("text", [
    "seven production call sites across three grid resolutions",
    "12 tests added",
    "found three findings and two violations",
    "sixteen cells measured",
])
def test_the_widened_guard_fires_on_each_forbidden_shape(text: str):
    assert offending_claims_wide(text), f"missed: {text!r}"


@pytest.mark.parametrize("text", [
    "g7 machinery: three pieces of apparatus, no results yet",
    "counts are in outputs/g8/ and the manifests, not in this message",
    "supersedes 1a090f0 and d3b7693; see generation 6",
    "six generations of results were published in an unnamed chart",
    "the generation-6 witness pair embeds into the local chart",
    "DEC-g7-1 records the CI waiver",
    "bump numpy to 1.22 and scipy to 1.10",
    "hold ruff and black at py39",
])
def test_the_widened_guard_does_not_fire_on_ordinary_messages(text: str):
    """Negative control, including the two identifier shapes that broke the
    first draft of these patterns: ``generation-6 witness`` and ``DEC-g7-1
    records`` both read as "a number followed by a measured noun" until the
    lookbehind excluded identifiers."""
    assert not offending_claims_wide(text), f"fired on: {text!r}"


def test_the_widening_does_not_weaken_the_original():
    """The narrow patterns still fire on the shape 1a090f0 used."""
    assert offending_claims("all 420 passed")
    assert offending_claims("419 of 420 tests passing")
