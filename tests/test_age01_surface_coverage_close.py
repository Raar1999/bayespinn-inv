"""``AGE-01``: the claim surface is exhaustive over the tree, and stays so.

The defect that forced it
-------------------------
Two artefacts in this repository encoded the rule set of their own date and were
then trusted years of generations later, unchecked:

* **``papers/CORRIGENDA_g6.md`` COR-1.** Written at generation 6 against
  ``PH-21`` -- *a local Jacobian rank is never reported without the word
  local* -- and applied at the close, nine cycles later. It repaired the regime
  label and nothing else, because nothing else was nameable when it was written.
  By the time it was applied, ``SPEC-g9-2`` also required the observation window,
  and the repaired sentence was **still** unguarded in that dimension. A
  correction is complete only against the rules of its own date.
* **``CLAIM_SURFACE_G7`` itself.** The tuple grew to ``docs/G10_RESULT.md`` and
  stopped, while the loop ran to generation 14. ``docs/G11_RESULT.md`` and
  ``ADR-0007`` published results off-surface for several generations each, and
  ``papers/draft.md`` was off it from generation 0. Nothing was wrong with any
  entry in the list; the list simply stopped being asked whether it was complete.

What this guard adds
--------------------
It makes the pair (``CLAIM_SURFACE_G7`` + cascade, ``EXEMPT``) **exhaustive**: a
tracked document may state a result only if it is on one list or the other. A new
document that publishes a rank, a witness count, or a spectral or ordering claim
now fails the suite until someone decides which it is. That decision is cheap;
noticing it was needed is what was not happening.

It cannot guard the other half of ``AGE-01`` -- whether a *correction* is stale
by later rules -- because that needs a reading of what the correction repairs
against what the rules now require, and there is no artefact carrying the first.
That half is procedural and is stated as such in ``docs/RULES_ENACTED.md``.

``SW-20``: the subject is prose and a pair of Python lists, so there is no AST.
Both controls ship -- a planted result-bearing document is caught, and a process
record and a document with no result are not.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, rel
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_g7 = _load("_age01_g7", "tests/test_claim_surface_g7.py")

#: The surface and the cascade, read from the modules that define them rather
#: than restated. A restatement here would be a third enumeration to go stale,
#: which is the defect this module exists to prevent.
SURFACE = set(_g7.CLAIM_SURFACE_G7) | {"docs/G10_RESULT.md",
                                       "docs/CLOSE_ADDENDUM.md"}
EXEMPT = set(_g7.EXEMPT)

#: A rank fraction, from the guard that defines it.
RANK = _g7._RANK
PROHIBITION = _g7._PROHIBITION

#: A witness count, as ``WIT-01``'s guard spells it.
WITNESS_COUNT = re.compile(
    r"\b\d{1,3}\s+(?:\*\*)?witness(?:es)?\b|\bwitness\s+pairs?\s+found\b"
    r"|\b\d{1,3}\s+witness\s+pair", re.I)

#: A spectral claim: the shape of the singular spectrum, asserted.
#:
#: No earlier guard has one, because the spectrum-shape result arrived at the
#: close of generation 10 and no claim-surface rule was written for it. That is
#: itself an instance of the class: the detectors grew to cover generation 9's
#: vocabulary and stopped.
SPECTRAL = re.compile(
    r"(?:spectrum|spectra)\s+(?:flatten|moves?|is\s+rigid)"
    r"|flatten\w*\s+(?:the\s+)?spectrum"
    r"|\bsigma_1\b|σ₁|\bσ_1\b"
    r"|decay[\s-]slope|normalised\s+spectrum|shape\s+(?:term|share)"
    r"|leading\s+singular\s+(?:value|direction)", re.I)

#: An ordering claim over the four sensitivities.
ORDERING = re.compile(
    r"observation\s+set\s*>|>\s*observation\s+set"
    r"|junction\s*>\s*|interpolant\s*>\s*|dimension\s*>\s*"
    r"|one-against-three"
    r"|dominat\w+\s+(?:the\s+)?(?:local\s+)?spectrum"
    r"|ordering\s+of\s+the\s+four", re.I)

DETECTORS = (("rank", RANK), ("witness", WITNESS_COUNT),
             ("spectral", SPECTRAL), ("ordering", ORDERING))


def states_a_result(text: str):
    """Which detectors fire outside a prohibition passage."""
    kinds = []
    for name, rx in DETECTORS:
        for _label, unit in _g7._units(text):
            if rx.search(unit) and not PROHIBITION.search(unit):
                kinds.append(name)
                break
    return kinds


def _in_a_checkout() -> bool:
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(ROOT),
                       capture_output=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def tracked_markdown():
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, "git ls-files failed"
    return sorted(p for p in out.stdout.splitlines() if p.strip())


@pytest.mark.skipif(not _in_a_checkout(), reason="not run from a git checkout")
class TestTheSurfaceIsExhaustive:

    def test_every_document_stating_a_result_is_on_one_list_or_the_other(self):
        """The rule. A document may state a result; it may not do so unlisted."""
        unlisted = []
        for rel in tracked_markdown():
            if rel in SURFACE or rel in EXEMPT:
                continue
            kinds = states_a_result(
                (ROOT / rel).read_text(encoding="utf-8", errors="replace"))
            if kinds:
                unlisted.append(f"{rel}: {','.join(sorted(set(kinds)))}")
        assert not unlisted, (
            "AGE-01 -- these documents state a result and are on neither "
            "CLAIM_SURFACE_G7 (nor its cascade) nor EXEMPT. Decide which, and "
            "say why in the EXEMPT reason if it is a process record:\n  "
            + "\n  ".join(unlisted))

    def test_the_scan_actually_reaches_the_tree(self):
        """A guard that walked an empty list would also pass the test above."""
        docs = tracked_markdown()
        assert len(docs) > 20, f"only {len(docs)} markdown files found"
        assert any(states_a_result((ROOT / d).read_text(encoding="utf-8",
                                                        errors="replace"))
                   for d in docs), "no document states a result; scan is vacuous"

    def test_every_listed_document_still_exists(self):
        """A list that names absent files has stopped describing the tree."""
        missing = [r for r in (SURFACE | EXEMPT)
                   if r.endswith(".md") and not (ROOT / r).is_file()]
        assert not missing, f"listed but absent: {missing}"

    def test_no_document_is_on_both_lists(self):
        both = SURFACE & EXEMPT
        assert not both, f"on the surface and exempt at once: {sorted(both)}"


class TestTheDetectorControls:
    """``SW-20``'s purpose: shown to fire, and shown not to fire on a record."""

    @pytest.mark.parametrize("planted,kind", [
        ("In chart L at d=16 the Jacobian determines 3-4 of 16 doping "
         "directions at 2% noise.", "rank"),
        ("The search returned 13 witness pairs among 1,999,000 examined.",
         "witness"),
        ("The rank climb is the spectrum flattening, not the head sliding.",
         "spectral"),
        ("What you measure dominates the local spectrum at every point.",
         "ordering"),
    ])
    def test_it_catches_a_planted_result(self, planted: str, kind: str):
        assert kind in states_a_result(planted)

    def test_it_does_not_fire_on_a_document_with_no_result(self):
        """Negative control: a detector that fired on everything would also
        make the exhaustiveness test pass, by putting every document on a list."""
        ordinary = ("This module builds the notebooks. It takes a directory and "
                    "writes one file per chapter, with 4 of 7 chapters needing a "
                    "data download first.")
        assert not states_a_result(ordinary)

    def test_a_prohibition_passage_is_not_a_claim(self):
        """The shape a not-to-be-written list has. Forbidding a sentence is not
        asserting it, and a guard that cannot tell them apart gets switched off."""
        forbidding = ("Not to be written: any rank fraction such as 3-4 of 16 "
                      "quoted without its chart. This must never appear.")
        assert not states_a_result(forbidding)

    def test_the_two_documents_this_audit_added_would_have_been_caught(self):
        """The positive control from history, and the reason this module exists.

        ``docs/G11_RESULT.md`` and ``ADR-0007`` published results off-surface for
        several generations. They are on the surface now, so the control is that
        the *detector* still recognises them -- if it stops, this guard has gone
        vacuous and the next such document will pass unnoticed.
        """
        for rel in ("docs/G11_RESULT.md",
                    "docs/adr/ADR-0007-the-oracle-arbitrates-global-"
                    "identifiability.md"):
            text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            assert states_a_result(text), f"{rel} no longer reads as a result"
            assert rel in SURFACE, f"{rel} left the surface"
