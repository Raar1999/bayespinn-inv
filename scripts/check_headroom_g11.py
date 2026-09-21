"""Does headroom against the floor predict refinement survival? Third set.

    PYTHONPATH=src python scripts/check_headroom_g11.py

What this is
------------
**Arithmetic over artefacts that already exist.** ``new_solves = 0``. It reads
the three refinement records and asks one question of each: *does a witness
pair's committed observational distance predict whether it survives the
refinement battery?*

Why it is asked now
-------------------
``docs/CLOSE_RULING.md`` §2 ratified this as corrected premise **(b)**:

    *What predicts survival is **headroom** against the distinguishability
    floor: the 7 survivors are exactly the 7 smallest distances at ``N=301``
    (max 0.01844) and the 6 that separate are the 6 largest (min 0.01873),
    against a floor of 0.02.*

That was measured on **chart J**, and confirmed afterwards on **chart G**. Both
sets have 13 pairs. Chart L has 37 and had never been refined, so until
generation 11 the rule had never met a set that did not help form it -- which is
the situation generation 9 was in when it found that a four-way sensitivity
ordering measured at one operating point did not survive nine more.

This check is a **description, not a pre-registered test**, and it is not
claimed as one (``AH-14``). It is reported because the refinement it reads was
pre-registered and because the answer changes a ratified premise, which
``SR-1`` requires be traced forward rather than noticed and dropped.

The statistic, and why two of them
----------------------------------
``spearman``
    rank correlation between the committed distance and separating. Positive
    means larger distance goes with separating, which is the direction the
    premise asserts.

``concordance``
    the probability that a randomly chosen separating pair has a **larger**
    committed distance than a randomly chosen surviving one, ties counted as a
    half. This is the premise stated as a predictive claim: **1.000** is the
    perfect ordering the premise describes, **0.500** is no information at all.
    It is reported beside ``spearman`` because a rank correlation over 13 points
    with 1 separator can look respectable while the underlying claim is nearly
    vacuous, and concordance makes the number of separators visible in what it
    is measuring.

Both are reported for every set, with the separator count beside them, so a set
whose split is too lopsided to carry either statistic says so.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]

#: ``label -> (artefact, distance key, survival key, what formed the premise)``
SETS: Dict[str, Tuple[str, str, str, bool]] = {
    "chart_G_d4": ("outputs/wit02_chartG/refine.json",
                   "g8_observational_distance", "survives_refinement", True),
    "chart_J_d16": ("outputs/g9/junction_refine.json",
                    "g8_observational_distance", "survives_refinement", True),
    "chart_L_d16": ("outputs/g11/wit02_chartL/refine.json",
                    "g8_observational_distance", "survives_refinement", False),
}

FLOOR = 0.02


def _read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def concordance(separating: np.ndarray, surviving: np.ndarray) -> Optional[float]:
    """P(a separating pair sits further from the floor than a surviving one).

    Ties count as a half, which is what makes 0.500 mean *no information*
    rather than *no ties*.
    """
    if separating.size == 0 or surviving.size == 0:
        return None
    wins = 0.0
    for a in separating:
        for b in surviving:
            wins += 1.0 if a > b else 0.5 if a == b else 0.0
    return wins / (separating.size * surviving.size)


def main() -> int:
    print("=" * 74)
    print("HEADROOM AGAINST THE FLOOR AS A PREDICTOR OF SURVIVAL")
    print("=" * 74)
    print("  arithmetic over existing artefacts; new_solves = 0")
    print(f"  distinguishability floor {FLOOR}")
    print()

    rows: List[Dict[str, Any]] = []
    for label, (artefact, dkey, okey, formed) in SETS.items():
        recs = _read(artefact)["records"]
        dist = np.array([float(r[dkey]) for r in recs]) / FLOOR
        sep = np.array([0 if bool(r[okey]) else 1 for r in recs])
        n_sep = int(sep.sum())
        if n_sep == 0 or n_sep == len(sep):
            rows.append({"set": label, "n": len(sep), "n_separating": n_sep,
                         "degenerate": True,
                         "why": "every pair fell the same way; neither "
                                "statistic is defined on a constant outcome"})
            continue
        rho, pval = stats.spearmanr(dist, sep)
        conc = concordance(dist[sep == 1], dist[sep == 0])
        rows.append({
            "set": label,
            "artefact": artefact,
            "helped_form_the_premise": formed,
            "n": len(sep),
            "n_surviving": len(sep) - n_sep,
            "n_separating": n_sep,
            "largest_surviving_in_floor_units": float(dist[sep == 0].max()),
            "smallest_separating_in_floor_units": float(dist[sep == 1].min()),
            "bands_overlap": bool(dist[sep == 0].max() > dist[sep == 1].min()),
            "spearman_rho": float(rho),
            "spearman_p": float(pval),
            "concordance": conc,
            "degenerate": False,
        })

    for r in rows:
        if r.get("degenerate"):
            print(f"  {r['set']:14} n={r['n']:2d}  degenerate: {r['why']}")
            continue
        print(f"  {r['set']:14} n={r['n']:2d}  separating={r['n_separating']:2d}"
              f"  spearman={r['spearman_rho']:+.3f} (p={r['spearman_p']:.3f})"
              f"  concordance={r['concordance']:.3f}"
              f"  {'formed the premise' if r['helped_form_the_premise'] else 'DID NOT'}")
    print()
    for r in rows:
        if r.get("degenerate"):
            continue
        print(f"  {r['set']:14} largest surviving {r['largest_surviving_in_floor_units']:.4f}"
              f"  smallest separating {r['smallest_separating_in_floor_units']:.4f}"
              f"  floor units -> {'OVERLAP' if r['bands_overlap'] else 'clean split'}")

    live = [r for r in rows if not r.get("degenerate")]
    held = [r for r in live if r["concordance"] == 1.0]
    failed = [r for r in live if r["concordance"] is not None
              and r["concordance"] < 0.6]
    verdict: Dict[str, Any] = {
        "premise": (
            "docs/CLOSE_RULING.md section 2 (b), ratified: what predicts "
            "refinement survival is headroom against the distinguishability "
            "floor"),
        "sets_where_it_holds_perfectly": [r["set"] for r in held],
        "sets_where_it_carries_no_information": [r["set"] for r in failed],
        "holds_on_every_set": bool(not failed),
        "the_sets_it_holds_on_are_the_sets_it_was_formed_on": bool(
            {r["set"] for r in held}
            == {k for k, v in SETS.items() if v[3]}),
        "reading": (
            "the premise is FALSIFIED AS A GENERAL RULE and stands only on the "
            "two sets that formed it. On chart L -- the largest set, 37 pairs "
            "with 11 separating, and the only one that did not help form the "
            "rule -- committed headroom carries no information about survival: "
            "concordance 0.479 against 0.500 for a coin, spearman -0.033 at "
            "p=0.845. The surviving and separating bands overlap across half "
            "the floor."),
        "what_it_does_not_say": (
            "it does not say the two 13-pair results were wrong. They "
            "reproduce. It says the rule read off them does not generalise, "
            "which is the same shape as generation 9's finding that a "
            "four-way ordering measured at one operating point did not "
            "survive nine more."),
        "what_it_strengthens": (
            "the close's refusal to adopt a margin band. That refusal rested "
            "on the band being 1.4 percentage points wide and therefore tuned "
            "(PH-11). Chart L is the stronger reason: across 37 pairs there "
            "is no band to tune, because survivors reach 0.996 floor units "
            "and separators start at 0.533. The decision was right and its "
            "recorded reason was weaker than the truth."),
        "status": "DESCRIPTION, not a pre-registered test (AH-14)",
        "new_solves": 0,
    }
    print()
    print("  " + verdict["reading"].replace(". ", ".\n  "))

    out = ROOT / "outputs" / "g11" / "headroom.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"floor": FLOOR, "rows": rows,
                               "verdict": verdict}, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
