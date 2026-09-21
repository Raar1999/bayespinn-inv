"""``SPEC-g9-2``: a rank on the claim surface carries the window it was measured in.

The defect that forced it
-------------------------
Generation 8 measured the identifiable count at a 2% cutoff falling from **4 to
2** in chart G at `d = 16` when the bias window narrowed from 0.15--0.90 V to
0.30--0.60 V, with the same device, the same chart and the same number of bias
points. It concluded, in its own words, that *an identifiable rank is a property
of the (device, observation set) pair and never of the device alone*.

`SPEC-11` had already made a rank carry its **cutoff**.
``tests/test_claim_surface_g7.py::TestEveryUnlicensedRankCarriesItsCutoff``
enforces that. But a rank quoted with its cutoff and without its **window** is
still a number that halves when the experimenter changes something the sentence
does not mention, and every rank in this repository is quoted at one window.

The clause, and its falsifier
-----------------------------
    ``SPEC-g9-2`` -- rank(observation set). Rank against bias-window width and
    spacing at fixed device, as a curve, alongside rank(cutoff).
    *F:* a rank appears anywhere on the claim surface at a single window
    without its curve.

So the falsifier is a statement about **prose**, and this is where it is
enforced. Two levels, because "without its curve" is two requirements:

``TestEveryRankCarriesItsObservationWindow``
    passage level -- a passage quoting a rank names the observation set that
    rank was measured over;
``TestEveryDocumentQuotingARankCitesTheCurve``
    document level -- a document that quotes a rank at all points its reader at
    the measured ``rank(observation set)`` curve, so that the single window is
    visibly one point of a curve rather than the answer.

``SW-20``. The subject is prose, so there is no AST; the rule's *purpose* is
honoured instead, exactly as ``tests/test_claim_surface_g7.py`` argues for the
same case. Both controls are implemented -- a planted bare rank the guard must
catch, and passages describing the rule which it must not fire on -- and this
module's own source is out of scope.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from test_claim_surface_g7 import (  # the same claim surface, one definition
    _PROHIBITION,
    _RANK,
    CLAIM_SURFACE_G7,
    _read,
    _units,
)

REPO = Path(__file__).resolve().parents[1]

CLAIM_SURFACE_G9 = CLAIM_SURFACE_G7

#: The observation set, however a passage spells it. A rank passage must say
#: what was measured, not merely at what noise level it was thresholded.
#:
#: Deliberately generous about *form* and strict about *presence*: "16 biases",
#: "0.15-0.90 V", "the published window" and "over the narrowed range" all name
#: an observation set, and none of them is easier to write than the truth.
_WINDOW = re.compile(
    r"\bbias(?:es|\s+point|\s+window|\s+range)?\b"
    r"|0\.15\s*[-–—]\s*0\.9\b|0\.15\s*[-–—]\s*0\.90\b"
    r"|0\.30\s*[-–—]\s*0\.60\b|0\.50\s*[-–—]\s*0\.90\b"
    r"|\bobservation set\b|\bobservation window\b|\bV window\b"
    r"|\bwindow\b",
    re.I)

#: The curve the document has to point at. Any of these makes the single window
#: visibly one point of a measured curve.
_CURVE_CITATION = re.compile(
    r"rank\s*\(\s*observation set\s*\)|rank\s*\(\s*window\s*\)"
    r"|rank\s*\(\s*cutoff\s*\)|outputs/g9/rank_obs\.json"
    r"|SPEC-g9-2|rank_obs|rank as a curve|rank-versus-window|rank vs window",
    re.I)


def window_offenders(text: str, document: str = "<text>"):
    """Passages quoting a rank fraction without naming the observation set."""
    offenders = []
    for label, unit in _units(text):
        if not _RANK.search(unit):
            continue
        if _WINDOW.search(unit) or _PROHIBITION.search(unit):
            continue
        offenders.append(f"{document} {label}: {unit.strip()[:150]}")
    return offenders


def _quotes_a_rank(text: str) -> bool:
    """A rank asserted somewhere outside a prohibition passage."""
    return any(_RANK.search(unit) and not _PROHIBITION.search(unit)
               for _, unit in _units(text))


class TestEveryRankCarriesItsObservationWindow:
    """The passage-level half of the falsifier."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G9)
    def test_no_document_quotes_a_rank_without_its_window(self, document):
        offenders = window_offenders(_read(document), document)
        assert not offenders, (
            "SPEC-g9-2 -- a rank fraction is quoted in a passage that does not "
            "say what was measured. The identifiable count at 2% falls from 4 "
            "to 2 in chart G at d=16 when the window narrows to 0.30-0.60 V "
            "with everything else held, so a rank without its observation set "
            "is a number that halves without the sentence changing:\n  "
            + "\n  ".join(offenders))

    def test_the_guard_catches_a_planted_bare_rank(self):
        planted = ("At 2% measurement noise the Jacobian determines 3 of 4 "
                   "doping degrees of freedom.")
        assert window_offenders(planted), (
            "the guard let through a rank carrying its cutoff and no window, "
            "which is exactly the shape SPEC-g9-2 forbids")

    def test_the_guard_passes_the_same_rank_with_its_window(self):
        repaired = ("At 2% measurement noise, over 16 bias points spanning "
                    "0.15-0.90 V, the Jacobian determines 3 of 4 doping "
                    "degrees of freedom.")
        assert not window_offenders(repaired)

    def test_the_guard_does_not_fire_on_prose_describing_the_rule(self):
        """`SW-20`'s negative control: the prohibition lists quote the shape."""
        prose = ('Not supported, and not to be written: a bare "3 of 4" with '
                 "no statement of what was measured.")
        assert not window_offenders(prose)

    def test_a_disclaimer_is_not_a_prohibition(self):
        """The same loophole `test_claim_surface_g7` closes, closed here too."""
        smuggled = ("The Jacobian determines 3 of 4 directions, which is not "
                    "comparable with the global result.")
        assert window_offenders(smuggled)

    def test_the_guard_is_not_vacuous_on_the_real_surface(self):
        """A guard nothing could ever trip is not evidence of anything.

        Every claim-surface document is shown to contain at least one rank
        fraction the guard *examines*; if the surface stopped quoting ranks
        entirely this test fails and says so, rather than the suite reporting a
        green guard over nothing.
        """
        seen = {d for d in CLAIM_SURFACE_G9 if _RANK.search(_read(d))}
        assert seen, ("no claim-surface document quotes a rank fraction any "
                      "more; this guard now proves nothing and should be "
                      "retired rather than left green")


class TestEveryDocumentQuotingARankCitesTheCurve:
    """The document-level half: one window must be visibly one point."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE_G9)
    def test_a_document_that_quotes_a_rank_points_at_the_curve(self, document):
        text = _read(document)
        if not _quotes_a_rank(text):
            pytest.skip(f"{document} quotes no rank")
        assert _CURVE_CITATION.search(text), (
            f"{document} quotes a rank and never points at a rank curve. "
            "SPEC-g9-2's falsifier is 'a rank at a single window without its "
            "curve'; citing rank(cutoff), rank(observation set) or "
            "outputs/g9/rank_obs.json satisfies it.")

    def test_the_citation_pattern_catches_the_documented_forms(self):
        for good in ("see rank(observation set) in outputs/g9/rank_obs.json",
                     "reported as rank(cutoff) over the inherited grid",
                     "SPEC-g9-2 measures it as a curve"):
            assert _CURVE_CITATION.search(good), good

    def test_the_citation_pattern_does_not_match_an_unrelated_sentence(self):
        assert not _CURVE_CITATION.search(
            "The rank is 3 of 4 and the spectrum decays smoothly.")


class TestTheMeasuredCurveIsWhatTheGuardPointsAt:
    """If the artefact exists, the prose requirement must be satisfiable.

    Skipped before ``scripts/run_g9.py`` has run, because a guard that fails on
    a missing measurement is a guard that blocks the measurement.
    """

    @staticmethod
    def _artefact():
        p = REPO / "outputs" / "g9" / "rank_obs.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def test_the_curve_has_more_than_one_window(self):
        doc = self._artefact()
        if doc is None:
            pytest.skip("outputs/g9/rank_obs.json not measured yet")
        for name, dev in doc["devices"].items():
            widths = [c for c in dev["width_curve"] if "error" not in c]
            assert len(widths) >= 3, (
                f"{name}: a 'curve' over {len(widths)} windows is not a curve")

    def test_every_point_on_the_curve_carries_its_own_rank_cutoff_curve(self):
        doc = self._artefact()
        if doc is None:
            pytest.skip("outputs/g9/rank_obs.json not measured yet")
        for name, dev in doc["devices"].items():
            for axis in ("width_curve", "spacing_curve"):
                for cell in dev[axis]:
                    if "error" in cell:
                        continue
                    assert cell.get("rank_cutoff_curve"), (
                        f"{name} {axis}: a point on the window curve reports a "
                        "rank without its cutoff curve, which is SPEC-11's "
                        "defect inside SPEC-g9-2's fix")
