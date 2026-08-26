"""The one free check the closing ruling of 2026-08-26 allows, and nothing else.

    §5. ONE FREE CHECK, THEN STOP.

    ``g10-1`` establishes that the rank climb is not the leading direction
    broadening. The obvious next question is decidable from artefacts you
    already hold: does the 1 -> 4 climb come from ``sigma_2..sigma_4`` **rising** with
    window width, or from ``sigma_1`` falling so the cutoff moves relative to a
    fixed spectrum shape? Plot the normalised spectrum against window width.

    **Arithmetic on existing artefacts only.** If it needs one new solve, it is
    future work and you stop.

Why this is a *description* and not a test
------------------------------------------
The question was put after the numbers existed. There is no pre-registration to
be had and none is claimed: the criterion below was written with the spectra on
disk, which is precisely the situation ``AH-14`` exists to keep out of the
result column. So this module reports a **description** of the rank climb, and
the word *test* does not appear in its verdict. What it can honestly offer in
place of pre-registration is three things:

* the decomposition is an **identity**, not a fit -- ``log sigma_i = log sigma_1 +
  log(sigma_i/sigma_1)`` holds term by term, so the split between "scale" and "shape" is
  arithmetic and has no free parameter to tune;
* the answer is a **sign**, not a threshold. Either the trailing values rise or
  the leading one falls. ``PH-11`` has nothing to forbid because there is no
  cutoff to choose;
* the measurement already contains its own control. The **spacing** axis moves
  the spectrum and does *not* move the rank (``SPEC-g9-2``). A statistic that
  explains the rank climb on the width axis must be quiet on the spacing axis,
  and that comparison was fixed by generation 9's design rather than by this
  module's author.

Arithmetic only, and checkable rather than asserted
---------------------------------------------------
This module imports ``json``, ``math`` and ``numpy``. It does not import
``bayespinn_inv``, it does not build a solver and it cannot reach the oracle;
``tests/test_spectrum_shape_close.py::TestThisRanNoSolver`` reads this file's
own AST and fails if that stops being true. Every number it writes is derived
from two artefacts that were on disk before the ruling was issued:

* ``outputs/g10/localisation.json`` -- 2 devices x 9 widths x 16 singular values,
  plus the spacing curve at the same 16;
* ``outputs/g9/rank_obs.json``     -- the same cells with ``rank(cutoff)`` over
  eight cutoffs and the largest multiplicative gap.

Their spectra are bit-identical, which the guard also checks: generation 10
re-measured generation 9's cells through the same imported code and the width
curves agree exactly, so "the spectrum" is one object here and not two.

Run
---
``PYTHONPATH=src python scripts/run_close.py``  (``PYTHONPATH`` is not needed and
is accepted only so the invocation matches every other one in this repository.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOCALISATION = "outputs/g10/localisation.json"
RANK_OBS = "outputs/g9/rank_obs.json"
MANIFEST = "outputs/g10/manifest.json"
OUT = "outputs/close/spectrum_shape.json"

#: How many leading singular values are WRITTEN DOWN. Five: the rank runs 1 -> 4
#: at the operational cutoff, and the fifth is the first index that never
#: crosses it, so the tail is visible without being unbounded.
K = 5

#: How many the VERDICT is allowed to rest on. Four, and the difference between
#: this and `K` is a defect this module found in its own first draft.
#:
#: `C3` compares every quoted singular value against the smallest cutoff the
#: artefact itself marks resolvable. At `K = 5` it FAILS in four of the eighteen
#: width cells -- `sigma_5` sits at or below the estimator's own spectral floor
#: at the two widest windows and at two others. Those are values read out of
#: estimator noise, and a description resting on them would be describing the
#: estimator.
#:
#: The repair is not to loosen the control. It is to stop the claim at the
#: indices the rank actually reaches: `sigma_1` through `sigma_4` clear the
#: probe in all eighteen cells, worst margin x1.51. `sigma_5` is still reported,
#: still plotted, and explicitly excluded from the verdict with its cells named.
K_CLAIM = 4


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Rank correlation with midranks for ties, as `scripts/run_g10.py` does it."""
    def rank(a: Sequence[float]) -> np.ndarray:
        arr = np.asarray(a, dtype=np.float64)
        order = np.argsort(arr, kind="mergesort")
        out = np.empty(len(arr), dtype=np.float64)
        i = 0
        while i < len(arr):
            j = i
            while j + 1 < len(arr) and arr[order[j + 1]] == arr[order[i]]:
                j += 1
            out[order[i:j + 1]] = 0.5 * (i + j)
            i = j + 1
        return out

    rx, ry = rank(x), rank(y)
    if rx.std() == 0.0 or ry.std() == 0.0:
        return float("nan")
    return float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (rx.std() * ry.std()))


def decay_slope(s: Sequence[float]) -> float:
    """Least-squares slope of ``log10 sigma_i`` against ``i`` over the leading `K`.

    One number for "how fast the spectrum falls away from its head". It is a
    summary of the shape and nothing turns on it: every claim in the verdict is
    carried by the normalised values themselves, which are reported in full.
    """
    v = np.asarray(s, dtype=np.float64)[:K]
    return float(np.polyfit(np.arange(1, len(v) + 1, dtype=np.float64),
                            np.log10(v), 1)[0])


def _read(rel: str) -> Dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def operational_cutoff() -> Tuple[float, float]:
    """``(noise_rel, cutoff_symlog)`` read from the manifest, never hardcoded.

    The rank every document quotes is ``rank_at_operational_cutoff``, and the
    cutoff it names is ``log10(1 + noise_rel)`` with ``noise_rel`` taken from
    the run configuration. Reading it back from ``outputs/g10/manifest.json``
    keeps this module from inventing a second 2%.
    """
    noise_rel = float(_read(MANIFEST)["config"]["noise_rel"])
    return noise_rel, float(math.log10(1.0 + noise_rel))


def _floor_probe(cell: Dict) -> float:
    """The smallest cutoff at which the record says we are still above the floor.

    ``rank_cutoff_record`` writes ``cutoff_below_spectral_floor`` per grid point.
    The smallest cutoff for which it is ``False`` is a value the estimator was
    willing to resolve, so any singular value above it is not being read out of
    estimator noise. This is a *bound* carried from the artefact, not a floor
    re-derived here -- re-deriving it would need the Jacobian, which would need
    a solve.
    """
    ok = [c["cutoff_symlog"] for c in cell["rank_cutoff_curve"]
          if not c["cutoff_below_spectral_floor"]]
    return float(min(ok)) if ok else float("inf")


# ===========================================================================
# The description, stated before the arithmetic that decides it
# ===========================================================================

#: The two readings the ruling names, written as sign conditions on an identity.
#:
#: For each trailing index ``i`` in ``2..K`` and each device, over the widths
#: ``0.10 -> 0.75`` V:
#:
#:     dlog_1₀ sigma_i  =  dlog_1₀ sigma_1  +  dlog_1₀ (sigma_i/sigma_1)
#:                   \_________/     \___________/
#:                      scale             shape
#:
#: SHAPE   the trailing values rise **relative to the head**: the shape term
#:         carries the majority of |dlog sigma_i| at every device and every i.
#: SCALE   the head moves and the shape does not: the scale term carries the
#:         majority, and its SIGN must be positive -- a falling sigma_1 with a fixed
#:         shape pushes the whole spectrum down and can only lower the rank
#:         against an absolute cutoff.
#:
#: The two are exhaustive and mutually exclusive by construction, which is why
#: no threshold appears in either.
READINGS = {
    "SHAPE": ("the spectrum flattens: sigma_2..sigma_K rise toward a nearly fixed sigma_1, and "
              "they cross the fixed absolute cutoff because the shape changed"),
    "SCALE": ("the spectrum is rigid and slides: sigma_1 moves and carries the tail "
              "with it across a fixed absolute cutoff"),
    "NEITHER": "the identity does not separate; both terms are comparable",
}


def describe_axis(cells: List[Dict], xkey: str, thr: float) -> Dict:
    """One axis of one device, reduced to the numbers the reading turns on."""
    xs = [float(c[xkey]) for c in cells]
    sv = np.asarray([c["singular_values"] for c in cells], dtype=np.float64)
    head = sv[:, [0]]
    norm = sv / head
    ranks = [int(c["rank_at_operational_cutoff"]) for c in cells]
    raw = [int((row > thr).sum()) for row in sv]
    lo, hi = 0, len(cells) - 1
    d_head = float(math.log10(sv[hi, 0] / sv[lo, 0]))

    per_index = []
    for i in range(1, K):
        d_abs = float(math.log10(sv[hi, i] / sv[lo, i]))
        d_shape = float(math.log10(norm[hi, i] / norm[lo, i]))
        total = abs(d_head) + abs(d_shape)
        crossings = [x for x, s in zip(xs, sv[:, i]) if s > thr]
        per_index.append({
            "index": i + 1,
            "within_claim": bool(i + 1 <= K_CLAIM),
            "delta_log10_sigma": d_abs,
            "delta_log10_scale": d_head,
            "delta_log10_shape": d_shape,
            "scale_share": (abs(d_head) / total) if total else float("nan"),
            "shape_share": (abs(d_shape) / total) if total else float("nan"),
            "shape_carries_it": bool(abs(d_shape) > abs(d_head)),
            "range_absolute": float(sv[:, i].max() / sv[:, i].min()),
            "range_normalised": float(norm[:, i].max() / norm[:, i].min()),
            "spearman_x_vs_sigma": spearman(xs, list(sv[:, i])),
            "spearman_x_vs_normalised": spearman(xs, list(norm[:, i])),
            "first_x_above_cutoff": (float(min(crossings)) if crossings else None),
        })

    return {
        "x": xs,
        "rank_at_operational_cutoff": ranks,
        "rank_equals_raw_count_above_cutoff": bool(ranks == raw),
        "raw_count_above_cutoff": raw,
        "sigma_leading": [[float(v) for v in row[:K]] for row in sv],
        "normalised_spectrum": [[float(v) for v in row[:K]] for row in norm],
        "decay_slope": [decay_slope(row) for row in sv],
        "head": {
            "sigma_1": [float(v) for v in sv[:, 0]],
            "min": float(sv[:, 0].min()),
            "max": float(sv[:, 0].max()),
            "range": float(sv[:, 0].max() / sv[:, 0].min()),
            "delta_log10": d_head,
            "spearman_x_vs_sigma_1": spearman(xs, list(sv[:, 0])),
        },
        "per_index": per_index,
        "smallest_sigma_reported": float(sv[:, :K].min()),
    }


def read_axis(reading: Dict) -> str:
    """Apply `READINGS` to one axis. No threshold, only signs and a majority."""
    live = [e for e in reading["per_index"] if e["within_claim"]]
    shape_everywhere = all(e["shape_carries_it"] for e in live)
    scale_everywhere = all(not e["shape_carries_it"] for e in live)
    if shape_everywhere:
        return "SHAPE"
    if scale_everywhere and reading["head"]["delta_log10"] > 0.0:
        return "SCALE"
    return "NEITHER"


# ===========================================================================
# Controls -- the measurement's own, not ones invented for the answer
# ===========================================================================

def controls(loc: Dict, robs: Dict, thr: float) -> Dict:
    """Four checks that would each have made the description unquotable.

    ``C1`` the two artefacts are the same spectra. Generation 10 re-measured
        generation 9's cells through the same imported code; if the width
        curves were not bit-identical, "the spectrum" would be two objects and
        the ``rank(cutoff)`` curves could not be read beside the values.
    ``C2`` the rank is the raw count. ``rank_cutoff_record`` returns
        ``min(#{sigma > cutoff}, resolvable_rank)``. If the estimator's own floor
        were capping the count at the operational cutoff, the decomposition
        would be describing the cap rather than the spectrum. (It *does* cap at
        the two smallest cutoffs, which is reported and excluded.)
    ``C3`` nothing quoted sits in estimator noise: the smallest singular value
        this description reports is above the smallest cutoff either artefact
        was willing to call resolvable.
    ``C4`` the axis that does not move the rank. ``alpha = 0`` and ``width = 0.75``
        are the *same* observation set -- 16 linearly spaced biases over
        0.15-0.90 V -- reached by two different code paths, so their spectra
        must agree exactly; and along the whole spacing axis, where the rank
        does not move at all, the shape statistic must stay quiet.
    """
    out: Dict = {}

    same = []
    for dname, rec in loc["devices"].items():
        a = [c for c in rec["width_curve"] if "error" not in c]
        b = [c for c in robs["devices"][dname]["width_curve"] if "error" not in c]
        same.append(bool([c["singular_values"] for c in a]
                         == [c["singular_values"] for c in b]
                         and [c["width_V"] for c in a] == [c["width_V"] for c in b]))
    out["C1_two_artefacts_one_spectrum"] = {
        "passed": all(same), "per_device": same,
        "what_it_would_have_meant": (
            "generation 10 did not reproduce generation 9's cells, in which case "
            "the rank(cutoff) curves belong to different spectra than the "
            "singular values and may not be read together"),
    }

    caps = []
    for dname, rec in robs["devices"].items():
        for c in [c for c in rec["width_curve"] if "error" not in c]:
            n_above = int((np.asarray(c["singular_values"]) > thr).sum())
            caps.append({
                "device": dname, "width_V": c["width_V"],
                "rank": int(c["rank_at_operational_cutoff"]),
                "raw_count": n_above,
                "capped": bool(c["rank_at_operational_cutoff"] != n_above),
            })
    out["C2_rank_is_the_raw_count_at_the_operational_cutoff"] = {
        "passed": not any(e["capped"] for e in caps),
        "cells": caps,
        "note": ("at the two smallest cutoffs on the rank(cutoff) grid -- "
                 "noise_rel 1e-4 and 1e-6 -- the count IS capped by "
                 "resolvable_rank at the wide windows and turns over. That is "
                 "the estimator's floor, not the spectrum, and those two "
                 "columns are excluded from the monotonicity statement below."),
    }

    claim_cells, excluded = [], []
    for dname, rec in robs["devices"].items():
        for c in [c for c in rec["width_curve"] if "error" not in c]:
            probe = _floor_probe(c)
            s = c["singular_values"]
            claim_cells.append({
                "device": dname, "width_V": c["width_V"],
                "floor_probe_symlog": probe,
                "smallest_claimed_sigma": float(min(s[:K_CLAIM])),
                "margin": float(min(s[:K_CLAIM]) / probe),
                "clears": bool(min(s[:K_CLAIM]) > probe),
            })
            if float(s[K_CLAIM]) <= probe:
                excluded.append({"device": dname, "width_V": c["width_V"],
                                 "index": K_CLAIM + 1,
                                 "sigma": float(s[K_CLAIM]),
                                 "floor_probe_symlog": probe})
    out["C3_nothing_the_verdict_rests_on_is_estimator_noise"] = {
        "passed": all(e["clears"] for e in claim_cells),
        "claim_indices": list(range(1, K_CLAIM + 1)),
        "reported_indices": list(range(1, K + 1)),
        "worst_margin": min(e["margin"] for e in claim_cells),
        "cells": claim_cells,
        "reported_but_excluded_from_the_verdict": excluded,
        "note": ("the probe is the smallest cutoff the artefact itself marks "
                 "cutoff_below_spectral_floor=false; it bounds the floor from "
                 "above without re-deriving it, which would need the Jacobian "
                 "and therefore a solve. It is COARSE -- the grid steps by "
                 "factors of 2 to 100 -- so it is a bound and not a floor. "
                 "sigma_5 fails it in the cells listed above; that is why "
                 "K_CLAIM is 4 and not 5."),
    }

    identical, spacing = [], []
    for dname, rec in loc["devices"].items():
        wide = [c for c in rec["width_curve"] if c.get("width_V") == 0.75]
        lin = [c for c in rec["spacing_curve"] if c.get("alpha") == 0.0]
        identical.append(bool(wide and lin
                              and wide[0]["singular_values"] == lin[0]["singular_values"]))
        cells = [c for c in rec["spacing_curve"] if "error" not in c]
        rd = describe_axis(cells, "alpha", thr)
        spacing.append({
            "device": dname,
            "rank_moves": bool(len(set(rd["rank_at_operational_cutoff"])) > 1),
            "decay_slope_first": rd["decay_slope"][0],
            "decay_slope_last": rd["decay_slope"][-1],
            "decay_slope_change_fraction": abs(
                rd["decay_slope"][-1] / rd["decay_slope"][0] - 1.0),
            "reading": read_axis(rd),
            "axis": rd,
        })
    out["C4_the_axis_that_does_not_move_the_rank"] = {
        "passed": bool(all(identical) and not any(e["rank_moves"] for e in spacing)),
        "alpha0_equals_width075": identical,
        "spacing": spacing,
        "what_it_would_have_meant": (
            "if the spectrum flattened as much along spacing as along width, "
            "flattening would not be an account of the rank climb, because the "
            "rank does not move along spacing"),
    }
    return out



# ===========================================================================
# Provenance -- what this step can attest, and what it cannot
# ===========================================================================

def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                             text=True, timeout=30)
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _sha256(rel: str) -> Optional[str]:
    path = ROOT / rel
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance(inputs: Sequence[str]) -> Dict:
    """The inputs, by digest, plus the tree that read them.

    Every other run script in this repository writes a ``Manifest`` from
    ``bayespinn_inv``. This one cannot: importing the package is exactly what
    ``tests/test_spectrum_shape_close.py::TestThisRanNoSolver`` forbids, because
    a script that can reach the oracle cannot evidence that it did not. So the
    provenance is written here, and it attests a narrower and more relevant
    thing.

    A solving run's manifest answers *what code produced this number*. This step
    produced no number that was not already on disk, so the question that
    matters is *which bytes did it read* -- and the answer is a digest per input
    file, which pins the inputs independently of git state, of what else was in
    the tree, and of whether anything was dirty. ``git_dirty`` is recorded
    beside it and is deliberately **not** required to be false: a dirty tree
    cannot change an input whose digest is pinned.

    What it does not attest: that the inputs are correct, that the code that
    produced them was clean, or that this platform is the only one the
    arithmetic holds on. The first two are the inputs' own manifests' job --
    ``outputs/g10/manifest.json`` and ``outputs/g9/manifest.json`` -- and the
    third is ``PROV-07``, open and unchanged.
    """
    return {
        "inputs_sha256": {rel: _sha256(rel) for rel in inputs},
        "input_manifests": ["outputs/g10/manifest.json",
                            "outputs/g9/manifest.json"],
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "git_dirty_is_not_a_gate": (
            "the inputs are pinned by digest, so a dirty tree cannot have "
            "changed what was read; this differs from a solving run, where the "
            "working tree IS the measurement"),
        "python": sys.version.split()[0],
        "platform": platform.system().lower(),
        "validated_platforms": ["win32"],
        "unvalidated": "linux and darwin -- PROV-07, open and unchanged",
    }

# ===========================================================================
# WIT-02 -- the refinement register
# ===========================================================================

WIT01 = "outputs/g10/wit01.json"
REGISTER = "outputs/close/wit02_register.json"

#: Where a refinement result for each committed witness set would live, and how
#: the pairs it covers are identified.
#:
#: The identification is not by position and not by trust. Each refinement
#: artefact carries the pair's separation in decades; `WIT-01`'s per-pair record
#: carries the same quantity as ``max_separation``. Two records describe the
#: same pair iff those agree EXACTLY -- they are the same float written twice,
#: not two measurements of one thing -- so coverage is measured rather than
#: assumed. That matters most where it is partial: generation 6's battery
#: refined three pairs, and "three of the thirteen" and "three pairs from
#: somewhere" are different sentences.
#: ``(artefact, list key, separation key, survival key)``; ``None`` where no
#: refinement of that set has ever been run.
REFINEMENT_SOURCES: Dict[str, Optional[Tuple[str, str, str, str]]] = {
    "chart_G_d4": ("outputs/witness_falsifier_g6/witness_falsifier.json",
                   "pairs", "separation_decades", "survives_refinement"),
    "chart_L_d16": None,
    "chart_J_d16": ("outputs/g9/junction_refine.json",
                    "records", "separation_magnitudes_only",
                    "survives_refinement"),
}

#: What each set is load-bearing for, so a reader sees the cost of the gap
#: rather than only its size.
CARRIES = {
    "chart_G_d4": "the ridge result",
    "chart_L_d16": ("the chart-L basin search statement, and through it the "
                    "reading that the ridge/basin split follows the dimension"),
    "chart_J_d16": ("the junction degeneracy, and the chart-J basin search "
                    "statement"),
}


def wit02_register() -> Dict:
    """Which committed witness sets have been refined, measured from artefacts.

    ``WIT-02``, enacted by the closing ruling of 2026-08-26 section 2:

        Every witness is refined before it is counted. Not the ones near the
        floor -- all of them.

    The rule needs no threshold, which is the point of it: the operator declined
    a margin band because the observed split sits between 92.2% and 93.65% of
    the floor, 1.4 percentage points, and a threshold chosen inside a band that
    narrow is tuned (``PH-11``).

    This function does not refine anything. Refining the two uncovered sets is
    new solving, which the closing ruling section 5 forbids, so what the rule
    gets at close is a **register**: every committed set, its coverage, and what
    rests on it. A rule whose live consequence is a recorded non-compliance is
    still doing its job -- before it, "not refined" and "refined, fine" were the
    same sentence on the claim surface.
    """
    wit01 = _read(WIT01)
    out: Dict = {
        "rule": {
            "id": "WIT-02",
            "text": ("every witness is refined before it is counted -- not the "
                     "ones near the floor, all of them"),
            "enacted": "closing operator ruling of 2026-08-26 section 2",
            "supersedes": None,
            "relationship_to_WIT01": (
                "WIT-01 is not withdrawn. It stays for the sub-grid case it "
                "does catch. Retro-applied it removes nothing -- admissibility "
                "ratio 1.000 in all three charts -- because every pair "
                "qualifies on a doping magnitude and magnitudes reach the grid "
                "exactly, so it is not sufficient either."),
            "why_no_threshold": (
                "the observed refinement split sits between 92.2% and 93.65% "
                "of the distinguishability floor, 1.4 percentage points. A "
                "threshold inside a band that narrow is tuned; PH-11 forbids "
                "it. Refining every witness needs no threshold to defend."),
        },
        "provenance": provenance(
            [WIT01] + [s[0] for s in REFINEMENT_SOURCES.values() if s]),
        "sets": {},
    }

    for label, src in REFINEMENT_SOURCES.items():
        offered = wit01["sets"][label]
        n_offered = int(offered["n_pairs_offered"])
        seps = [p["max_separation"] for p in offered["pairs"]]
        entry: Dict = {
            "chart": offered["chart"],
            "d": offered["d"],
            "n_pairs_offered": n_offered,
            "admissibility_ratio_WIT01": offered["admissibility_ratio"],
            "refinement_artefact": (src[0] if src else None),
            "n_refined": 0,
            "n_surviving": None,
            "coverage": 0.0,
            "compliant": False,
            "carries": CARRIES[label],
            "matched_by": ("exact equality of the separation in decades against "
                           "WIT-01's max_separation for the same set"),
        }
        if src is not None and (ROOT / src[0]).is_file():
            artefact, list_key, sep_key, ok_key = src
            recs = list(_read(artefact)[list_key])
            matched = [r for r in recs if r[sep_key] in seps]
            entry["n_refined"] = len(matched)
            entry["n_surviving"] = sum(1 for r in matched if bool(r[ok_key]))
            entry["n_records_in_artefact"] = len(recs)
            entry["n_records_not_matched_to_this_set"] = len(recs) - len(matched)
            entry["coverage"] = len(matched) / float(n_offered)
            entry["compliant"] = bool(len(matched) == n_offered)
        out["sets"][label] = entry

    out["verdict"] = {
        "n_sets": len(out["sets"]),
        "n_compliant": sum(1 for e in out["sets"].values() if e["compliant"]),
        "non_compliant": sorted(k for k, e in out["sets"].items()
                                if not e["compliant"]),
        "all_compliant": all(e["compliant"] for e in out["sets"].values()),
        "why_not_repaired_here": (
            "refining the uncovered pairs is new solving. The closing ruling "
            "section 5 allows arithmetic on existing artefacts only and orders "
            "a stop; there is no generation 11. The gap is registered rather "
            "than closed, and WITNESS-04 carries it as load-bearing."),
        "reading": (
            "chart J is the only committed witness set that satisfies WIT-02. "
            "Chart G is partially covered -- generation 6's battery refined "
            "three of its thirteen pairs and all three survived. Chart L is "
            "uncovered, and it is the set the dimension reading rests on."),
    }
    return out


# ===========================================================================
# Main
# ===========================================================================

def build() -> Dict:
    loc, robs = _read(LOCALISATION), _read(RANK_OBS)
    noise_rel, thr = operational_cutoff()

    doc: Dict = {
        "question": (
            "does the rank climb 1 -> 4 over bias-window width come from "
            "sigma_2..sigma_4 RISING with width, or from sigma_1 FALLING so "
            "that a fixed absolute cutoff moves relative to a fixed spectrum "
            "shape?"),
        "ordered_by": "closing operator ruling of 2026-08-26 section 5",
        "status": (
            "DESCRIPTION, not a test. The question was asked after the spectra "
            "were on disk, so there is no pre-registration and none is claimed "
            "(AH-14). What stands in its place: the decomposition is an "
            "identity with no free parameter, the answer is a sign rather than "
            "a threshold (PH-11 has nothing to forbid), and the control axis "
            "was fixed by SPEC-g9-2's design a generation earlier."),
        "arithmetic_only": {
            "inputs": [LOCALISATION, RANK_OBS, MANIFEST],
            "new_solves": 0,
            "enforced_by": ("tests/test_spectrum_shape_close.py::"
                            "TestThisRanNoSolver reads this module's AST"),
        },
        "cutoff": {
            "noise_rel": noise_rel,
            "cutoff_symlog": thr,
            "kind": "ABSOLUTE",
            "why_it_matters": (
                "rank = #{sigma_i > log10(1+noise_rel)}. The cutoff does not "
                "scale with sigma_1, so a rigid spectrum whose head FALLS can "
                "only lose directions. That is what makes the two readings "
                "separable by sign alone."),
            "source": MANIFEST + " config.noise_rel",
        },
        "provenance": provenance([LOCALISATION, RANK_OBS, MANIFEST]),
        "readings": READINGS,
        "claim_scope": {
            "indices_reported": list(range(1, K + 1)),
            "indices_the_verdict_rests_on": list(range(1, K_CLAIM + 1)),
            "why": ("the rank runs 1 -> 4, so sigma_1..sigma_4 are the indices "
                    "the count is made of. sigma_5 is reported because the tail "
                    "should be visible, and excluded because it sits at or "
                    "below the estimator's own spectral floor in four of the "
                    "eighteen width cells -- see control C3."),
        },
        "devices": {},
    }

    verdicts = {}
    for dname, rec in loc["devices"].items():
        cells = [c for c in rec["width_curve"] if "error" not in c]
        axis = describe_axis(cells, "width_V", thr)
        gaps = [{"width_V": c["width_V"],
                 "largest_gap_ratio": c["largest_gap_ratio"],
                 "operational_cutoff_falls_in_largest_gap":
                     c["operational_cutoff_falls_in_largest_gap"],
                 "bare_integer_rank_justified": c["bare_integer_rank_justified"]}
                for c in robs["devices"][dname]["width_curve"] if "error" not in c]
        curves = [{"width_V": c["width_V"],
                   "rank_by_noise_rel": {str(e["noise_rel"]): e["rank"]
                                         for e in c["rank_cutoff_curve"]}}
                  for c in robs["devices"][dname]["width_curve"] if "error" not in c]
        verdicts[dname] = read_axis(axis)
        doc["devices"][dname] = {
            "width_axis": axis,
            "reading": verdicts[dname],
            "gap_structure": gaps,
            "rank_over_every_cutoff": curves,
        }

    doc["controls"] = controls(loc, robs, thr)

    # Which cutoffs are usable is MEASURED, not chosen. `rank_cutoff_record`
    # returns min(#{sigma > cutoff}, resolvable_rank); at a cutoff where that
    # minimum bites in any cell, the curve is reporting the estimator's own
    # floor rather than the spectrum. Those cutoffs are named and dropped, and
    # the rule that drops them is the same one `C2` applies at the operational
    # cutoff -- not a second criterion invented for this paragraph.
    grid = sorted({float(k) for d in doc["devices"].values()
                   for c in d["rank_over_every_cutoff"]
                   for k in c["rank_by_noise_rel"]}, reverse=True)
    capped_at = set()
    for rec in robs["devices"].values():
        for c in [c for c in rec["width_curve"] if "error" not in c]:
            s = np.asarray(c["singular_values"], dtype=np.float64)
            for e in c["rank_cutoff_curve"]:
                if e["rank"] != int((s > e["cutoff_symlog"]).sum()):
                    capped_at.add(float(e["noise_rel"]))
    clean = [g for g in grid if g not in capped_at]
    climbs = {}
    for dname, d in doc["devices"].items():
        for g in clean:
            key = next(k for k in d["rank_over_every_cutoff"][0]["rank_by_noise_rel"]
                       if float(k) == g)
            seq = [c["rank_by_noise_rel"][key] for c in d["rank_over_every_cutoff"]]
            climbs[dname + "@" + format(g, "g")] = {
                "first": seq[0], "last": seq[-1],
                "non_decreasing": all(b >= a for a, b in zip(seq, seq[1:])),
                "climbs": bool(seq[-1] > seq[0]),
                "sequence": seq,
            }
    doc["climb_is_not_a_property_of_the_cutoff"] = {
        "cutoffs_examined": clean,
        "excluded": sorted(capped_at, reverse=True),
        "why_excluded": (
            "at these cutoffs rank_at_operational_cutoff is capped by "
            "resolvable_rank in at least one cell, so the curve reports the "
            "estimator's floor and not the spectrum. Which cutoffs those are "
            "is measured here by recounting #{sigma > cutoff} and comparing, "
            "not chosen: the cap first bites at the wide windows and never at "
            "noise_rel >= 0.01."),
        "climbs_everywhere": all(e["climbs"] for e in climbs.values()),
        "non_decreasing_everywhere": all(e["non_decreasing"] for e in climbs.values()),
        "per_cutoff": climbs,
    }

    agreed = set(verdicts.values())
    doc["verdict"] = {
        "per_device": verdicts,
        "agreed": (agreed.pop() if len(agreed) == 1 else "SPLIT"),
        "all_controls_pass": all(v["passed"] for v in doc["controls"].values()),
        "statement": None,
    }
    v = doc["verdict"]["agreed"]
    if v == "SHAPE":
        heads = [d["width_axis"]["head"] for d in doc["devices"].values()]
        shares = [e["shape_share"] for d in doc["devices"].values()
                  for e in d["width_axis"]["per_index"] if e["within_claim"]]
        doc["verdict"]["statement"] = (
            "SHAPE. sigma_1 is nearly fixed -- it moves by a factor of "
            + format(min(h["range"] for h in heads), ".3f") + " to "
            + format(max(h["range"] for h in heads), ".3f")
            + " across the widths -- and it moves DOWNWARD, which is the wrong "
            "direction to raise a count against an absolute cutoff. The "
            "trailing values rise, and " + format(min(shares), ".1%") + " to "
            + format(max(shares), ".1%") + " of each one's motion is in the "
            "normalised spectrum. The rank climb is the spectrum FLATTENING, "
            "not the head sliding.")
    else:
        doc["verdict"]["statement"] = v + ": " + READINGS.get(v, "unclassified")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="the closing ruling's free check")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--register", default=REGISTER)
    args = ap.parse_args(argv)

    doc = build()
    path = ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    reg = wit02_register()
    reg_path = ROOT / args.register
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")

    bar = "=" * 74
    print(bar)
    print("CLOSING RULING section 5 -- the one free check")
    print(bar)
    print("  cutoff  " + format(doc["cutoff"]["cutoff_symlog"], ".6e")
          + " symlog (noise_rel=" + format(doc["cutoff"]["noise_rel"], "g")
          + "), ABSOLUTE")
    for dname, d in doc["devices"].items():
        a = d["width_axis"]
        print()
        print("  " + dname + "  ->  " + d["reading"])
        header = "    width rank   slope |"
        for i in range(1, K):
            header += format("s" + str(i + 1) + "/s1", ">12")
        print(header)
        for j, w in enumerate(a["x"]):
            row = ("    " + format(w, "6.2f")
                   + format(a["rank_at_operational_cutoff"][j], "4d") + " "
                   + format(a["decay_slope"][j], "7.4f") + " |")
            for i in range(1, K):
                row += format(a["normalised_spectrum"][j][i], "12.4e")
            print(row)
        h = a["head"]
        print("    sigma_1 x" + format(h["range"], ".4f") + " over the axis, "
              "spearman " + format(h["spearman_x_vs_sigma_1"], "+.3f")
              + " (delta log10 = " + format(h["delta_log10"], "+.5f") + ")")
        for e in a["per_index"]:
            print("    sigma_" + str(e["index"])
                  + ("" if e["within_claim"] else " (REPORTED, NOT CLAIMED)")
                  + ": shape carries "
                  + format(e["shape_share"], "5.1%") + ", scale "
                  + format(e["scale_share"], "4.1%") + "; normalised range x"
                  + format(e["range_normalised"], ".4g"))
    print()
    for name, c in doc["controls"].items():
        print("  " + ("PASS" if c["passed"] else "FAIL") + "  " + name)
    print()
    print("  climbs at every defensible cutoff: "
          + str(doc["climb_is_not_a_property_of_the_cutoff"]["climbs_everywhere"]))
    print("  VERDICT  " + doc["verdict"]["agreed"])
    print("  " + doc["verdict"]["statement"])
    print()
    print("-" * 74)
    print("WIT-02 refinement register")
    print("-" * 74)
    for label, e in reg["sets"].items():
        print("  " + format(label, "<14")
              + " " + format(e["n_refined"], "2d") + " of "
              + format(e["n_pairs_offered"], "2d") + " refined "
              + "(" + format(e["coverage"], "6.1%") + ")  "
              + ("COMPLIANT" if e["compliant"] else "NOT COMPLIANT")
              + ("" if e["n_surviving"] is None
                 else "  " + str(e["n_surviving"]) + " survive"))
    print("  " + reg["verdict"]["reading"])
    print()
    print("  written  " + args.out)
    print("  written  " + args.register)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
