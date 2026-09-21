"""``MECH-01``: what the row-side measurement's control axis says about it.

    PYTHONPATH=src python scripts/mech01_discriminator.py

Arithmetic over ``outputs/g12/mech01_rows/rows.json``. ``new_solves = 0``.

Why this exists
---------------
``scripts/run_mech01_rows.py`` pre-registered a **sign** as its discriminator:
``NEW_ROWS`` iff ``mean(excess(2..4)) > excess(1)`` at every width beyond the
narrowest. That test returned ``NEW_ROWS``, 8 of 8 widths at both devices.

Its control axis says the sign is not diagnostic. ``C1`` computes the same
statistic along ``SPEC-g9-2``'s **spacing** axis, where the rank does not move
at all, and the sign comes out the same way in 16 of 18 cells. A discriminator
that fires just as readily on the axis where nothing happens is not
discriminating; it is describing a property these Jacobians have generally.

**So the pre-registered verdict is void as a verdict**, and this module is what
replaces it -- explicitly as a *description*, not a test. The statistic below
was chosen **after** seeing that the sign failed, and ``AH-14`` applies in full:
there is no pre-registration for it and none is claimed.

What it measures
----------------
The **magnitude** of the gap ``mean(excess(2..4)) - excess(1)``, compared
between the two axes. The sign asks *does the concentration exist*; the
magnitude asks *is it larger where the rank moves than where it does not*, which
is the question the control was really posing.

Two things make the comparison fair rather than convenient, and both were fixed
by ``SPEC-g9-2``'s design a generation before this question was asked:

* the axes share a cell. ``alpha = 0`` and ``width = 0.75`` are **one
  observation set reached by two code paths** -- generation 9's ``C4`` control.
  It is excluded from the spacing side of the comparison, because counting one
  cell on both sides would inflate the overlap between the axes rather than the
  difference.
* both axes hold the bias **count** fixed at 16 offered, so neither is
  advantaged by having more rows.

What it cannot establish
------------------------
That the width effect is real *as a test*. It is a magnitude comparison over
nine points per axis with no pre-registered threshold, and a threshold chosen
now would be tuned (``PH-11``). It reports the ratio and the shape and stops
there. A pre-registered version of this statistic is what a third pass would
need, and that would be the **same** method with a sharper statistic -- not a
third distinct method for ``U-EMPIR``'s purposes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROWS = "outputs/g12/mech01_rows/rows.json"
SHARED_ALPHA = 0.0          # the cell the two axes share (g9's C4 control)


def gaps(cells: List[Dict[str, Any]], key: str) -> List[Dict[str, float]]:
    out = []
    for c in cells:
        if c.get("mean_excess_trailing") is None or c.get("excess_head") is None:
            continue
        out.append({
            "param": float(c[key]),
            "gap": float(c["mean_excess_trailing"] - c["excess_head"]),
            "n_rows": c["n_rows"],
            "n_outside_core": c["n_outside_core"],
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g12/mech01_discriminator.json")
    args = ap.parse_args(argv)

    doc_in = json.loads((ROOT / ROWS).read_text(encoding="utf-8"))
    print("=" * 74)
    print("MECH-01  the sign did not discriminate; what the magnitude says")
    print("=" * 74)
    print("  DESCRIPTION, not a test. The statistic was chosen after the")
    print("  pre-registered sign failed its control axis (AH-14).")
    print()

    devices: Dict[str, Any] = {}
    for dname, rec in doc_in["devices"].items():
        w = gaps(rec["width_curve"], "width_V")
        s_all = gaps(rec["spacing_curve"], "alpha")
        s = [r for r in s_all if r["param"] != SHARED_ALPHA]

        shared_w = next((r for r in w if r["param"] == 0.75), None)
        shared_s = next((r for r in s_all if r["param"] == SHARED_ALPHA), None)
        shared_agrees = bool(
            shared_w and shared_s
            and abs(shared_w["gap"] - shared_s["gap"]) < 1e-12)

        wv = np.array([r["gap"] for r in w])
        sv = np.array([r["gap"] for r in s])
        peak = w[int(np.argmax(wv))]
        devices[dname] = {
            "width": {"n": len(w), "max_gap": float(wv.max()),
                      "min_gap": float(wv.min()),
                      "at_max_width_V": peak["param"],
                      "range": float(wv.max() - wv.min())},
            "spacing_excluding_the_shared_cell": {
                "n": len(s), "max_gap": float(sv.max()),
                "min_gap": float(sv.min()),
                "range": float(sv.max() - sv.min())},
            "max_ratio_width_over_spacing": float(wv.max() / sv.max())
            if sv.max() > 0 else None,
            "width_max_exceeds_every_spacing_cell": bool(wv.max() > sv.max()),
            "shared_cell_control": {
                "alpha_0_equals_width_0_75": shared_agrees,
                "width_0_75_gap": shared_w["gap"] if shared_w else None,
                "alpha_0_gap": shared_s["gap"] if shared_s else None,
                "why": ("generation 9's C4: alpha=0 and width=0.75 are one "
                        "observation set reached by two code paths. They must "
                        "agree exactly, and it is a free reproduction control "
                        "on this statistic"),
            },
            "width_curve": w,
            "spacing_curve": s_all,
        }
        d = devices[dname]
        print(f"  {dname}")
        print(f"    width   : max gap {d['width']['max_gap']:+.4f} at "
              f"width {d['width']['at_max_width_V']:.2f} V, "
              f"range {d['width']['range']:.4f} over {d['width']['n']} cells")
        print(f"    spacing : max gap "
              f"{d['spacing_excluding_the_shared_cell']['max_gap']:+.4f}, "
              f"range {d['spacing_excluding_the_shared_cell']['range']:.4f} "
              f"over {d['spacing_excluding_the_shared_cell']['n']} cells "
              f"(shared cell excluded)")
        print(f"    ratio   : {d['max_ratio_width_over_spacing']:.2f}x"
              f"   width max exceeds every spacing cell: "
              f"{d['width_max_exceeds_every_spacing_cell']}")
        print(f"    C4 shared cell agrees exactly: {shared_agrees}")

    both = all(v["width_max_exceeds_every_spacing_cell"]
               for v in devices.values())
    ratios = [v["max_ratio_width_over_spacing"] for v in devices.values()
              if v["max_ratio_width_over_spacing"]]
    peaks = [v["width"]["at_max_width_V"] for v in devices.values()]

    doc: Dict[str, Any] = {
        "what_this_is": (
            "a DESCRIPTION of what separates the width axis from the control "
            "axis, written after the pre-registered SIGN test failed to "
            "separate them. Not pre-registered, and AH-14 applies in full"),
        "why_the_sign_verdict_is_void": (
            "run_mech01_rows.py pre-registered NEW_ROWS iff the trailing "
            "directions sit further outside the core window than the head, at "
            "every width. That is true at 16 of 16 width cells -- and also at "
            "16 of 18 cells of the SPACING axis, where SPEC-g9-2 measured the "
            "rank as fixed. A discriminator that fires on the axis where "
            "nothing happens is not discriminating"),
        "new_solves": 0,
        "devices": devices,
        "reading": {
            "width_max_exceeds_every_spacing_cell_at_both_devices": both,
            "ratio_range": [min(ratios), max(ratios)] if ratios else None,
            "peak_width_V": sorted(set(peaks)),
            "what_it_suggests": (
                "the concentration of the trailing directions on rows outside "
                "the core is a general property of these Jacobians -- it is "
                "present on both axes -- but it is LARGER on the width axis, "
                "and largest at the narrow-to-mid windows where the rank is "
                "actually climbing rather than at the widest windows where it "
                "has saturated at four"),
            "what_it_does_not_establish": (
                "that the width effect is real as a TEST. Nine points per "
                "axis, no pre-registered threshold, and a threshold chosen now "
                "would be tuned (PH-11). MECH-01 stays open"),
        },
        "consequence_for_U_EMPIR": (
            "the row-side method is INCONCLUSIVE as pre-registered, which is "
            "not the same as failed: the hypothesis was not falsified, the "
            "discriminator was too blunt. A sharpened version -- the magnitude "
            "statistic, pre-registered, with the spacing axis as the null -- "
            "is the SAME method with a better statistic, not a third distinct "
            "one. U-EMPIR still stands at one falsified method (generation "
            "10's column side)"),
    }
    p = ROOT / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    print()
    print("  " + doc["reading"]["what_it_suggests"].replace(" -- ", "\n  -- "))
    print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
