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

REPO = Path(__file__).resolve().parents[1]

#: The commit that enacts DOC-07 in this tree. Messages from here forward are
#: in scope; anything earlier is uncorrectable history.
ENACTED_AT = "3e05c9da55e152c8305838ff1da4166207051826"

#: The generation-6 message that forced the rule. Its own text is the control.
POSITIVE_CONTROL = "1a090f0"

#: Assertions of a measured count or metric. Deliberately narrow: it targets the
#: shape ``1a090f0`` used, not every digit in a message. A commit that says
#: "generation 6" or quotes a SHA must not be flagged.
_COUNT_CLAIMS = (
    re.compile(r"\b\d[\d,]*\s+(?:tests?\s+)?(?:passed|passing|failed|failing)\b", re.I),
    re.compile(r"\b\d[\d,]*\s*/\s*\d[\d,]*\s+(?:tests?|passed|passing)\b", re.I),
    re.compile(r"\b\d[\d,]*\s+of\s+\d[\d,]*\s+(?:tests?|passed|passing)\b", re.I),
    re.compile(r"\b(?:tests?|suite)\s*[:=]\s*\d[\d,]*\b", re.I),
)


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
