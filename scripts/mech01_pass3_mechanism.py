"""``MECH-01`` pass 3: why the row-side statistic failed, quantified.

    PYTHONPATH=src python scripts/mech01_pass3_mechanism.py

Arithmetic over ``outputs/g13/mech01_pass3/`` and ``outputs/g12/mech01_rows/``.
``new_solves = 0``.

What this is, and what it is not
--------------------------------
The verdict is in ``verdict.json`` and it is ``DOES_NOT_SEPARATE``, decided by
the pre-registered rule on the pre-registered statistic. **Nothing here revises
it.** This module does not test anything and no threshold in it is
pre-registered.

It exists because ``U-EMPIR`` does not accept a bare failure. Its obligation is
to "name each method, why it was expected to work, and **the mechanism of its
failure**", and a mechanism is a measurement, not an adjective. So: four devices,
two axes, the statistic the pre-registration fixed, and the question of what
``dz`` is actually varying with.

The three candidates
--------------------
``dz`` could vary with the **axis** (the hypothesis: it is larger where the rank
climbs), with the **split ratio** ``b = n_out/n_rows`` (the confound named in the
pre-registration before the held-out devices were touched), or with the
**device** (a per-device offset that has nothing to do with either).

All three are measured here on the same footing.

The b-matched comparison
------------------------
The pre-registered test pools every admissible cell, and on the width axis those
run over ``b`` in 0.375--0.875 while the spacing axis only ever reaches
0.818--0.875. Restricting both axes to the ``b`` range they share is the
comparison the pre-registered test could not make, and it is reported here as a
**post-hoc diagnostic**. It is the honest read of what the axes do when the
confound is held still; it is not a second verdict and may not be quoted as one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_mech01_pass3 import DISCOVERY, HELD_OUT, SHARED_ALPHA, axis_dz

ROOT = Path(__file__).resolve().parents[1]
PASS3 = "outputs/g13/mech01_pass3"
PASS2 = "outputs/g12/mech01_rows/rows.json"


def _read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _cells() -> List[Dict[str, Any]]:
    """Every admissible cell from all four devices, tagged."""
    out: List[Dict[str, Any]] = []
    sources = [(_read(PASS2)["devices"], "discovery"),
               (_read(f"{PASS3}/heldout.json")["devices"], "held_out")]
    for devices, role in sources:
        for dname, rec in devices.items():
            for axis, key, drop in (("width", "width_V", None),
                                    ("spacing", "alpha", SHARED_ALPHA)):
                for r in axis_dz(rec[f"{axis}_curve"], key, drop=drop):
                    if not r["admissible"]:
                        continue
                    out.append({"device": dname, "role": role, "axis": axis,
                                "param": r["param"], "b": r["b"],
                                "dz": r["dz"]})
    return out


def _corr(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=f"{PASS3}/mechanism.json")
    args = ap.parse_args(argv)

    cells = _cells()
    devices = list(DISCOVERY) + list(HELD_OUT)

    print("=" * 74)
    print("MECH-01 pass 3  the mechanism of the failure  (DESCRIPTION, not a test)")
    print("=" * 74)
    print("  The verdict is DOES_NOT_SEPARATE and is not revised here.")
    print()

    # --- 1. what dz varies with -------------------------------------------
    by_device = {d: [c for c in cells if c["device"] == d] for d in devices}
    print("  per-device offset: dz has a device-level level, on BOTH axes")
    print("  %-20s %-9s %-9s %-9s %s" % ("device", "median dz", "width", "spacing", "corr(dz,b)"))
    offsets = {}
    for d in devices:
        cs = by_device[d]
        w = [c["dz"] for c in cs if c["axis"] == "width"]
        s = [c["dz"] for c in cs if c["axis"] == "spacing"]
        offsets[d] = {
            "median_dz": float(np.median([c["dz"] for c in cs])),
            "median_width": float(np.median(w)),
            "median_spacing": float(np.median(s)),
            "corr_dz_b_width": _corr([c["b"] for c in cs if c["axis"] == "width"], w),
        }
        o = offsets[d]
        print("  %-20s %+9.3f %+9.3f %+9.3f %+9.3f"
              % (d, o["median_dz"], o["median_width"], o["median_spacing"],
                 o["corr_dz_b_width"]))

    spread = (max(o["median_dz"] for o in offsets.values())
              - min(o["median_dz"] for o in offsets.values()))
    print(f"\n  device-to-device spread in median dz: {spread:.3f}")

    # --- 2. the b-matched comparison ---------------------------------------
    lo = max(min(c["b"] for c in cells if c["axis"] == a) for a in ("width", "spacing"))
    hi = min(max(c["b"] for c in cells if c["axis"] == a) for a in ("width", "spacing"))
    print(f"\n  b range shared by both axes: [{lo:.3f}, {hi:.3f}]")
    print("  %-20s %-6s %-6s %-10s %-10s %s"
          % ("device", "n_w", "n_s", "med width", "med spacing", "width>spacing?"))
    matched: Dict[str, Any] = {}
    for d in devices:
        cs = [c for c in by_device[d] if lo - 1e-12 <= c["b"] <= hi + 1e-12]
        w = [c["dz"] for c in cs if c["axis"] == "width"]
        s = [c["dz"] for c in cs if c["axis"] == "spacing"]
        med_w = float(np.median(w)) if w else None
        med_s = float(np.median(s)) if s else None
        exceeds = med_w is not None and med_s is not None and med_w > med_s
        rec = {"n_width": len(w), "n_spacing": len(s),
               "median_width": med_w, "median_spacing": med_s,
               "width_exceeds": exceeds}
        matched[d] = rec
        print("  %-20s %-6d %-6d %-10s %-10s %s"
              % (d, len(w), len(s),
                 "%+.3f" % med_w if med_w is not None else "-",
                 "%+.3f" % med_s if med_s is not None else "-",
                 exceeds if med_w is not None and med_s is not None else "-"))

    # --- 3. dz against b, pooled -------------------------------------------
    pooled_b = _corr([c["b"] for c in cells], [c["dz"] for c in cells])
    within = {}
    for d in devices:
        cs = by_device[d]
        within[d] = _corr([c["b"] for c in cs], [c["dz"] for c in cs])
    print(f"\n  corr(dz, b) pooled over all four devices: {pooled_b:+.3f}")
    print("  within device: " + "  ".join(f"{d}={within[d]:+.3f}" for d in devices))

    doc = {
        "what_this_is": (
            "a description of how the row-side method failed, for U-EMPIR's "
            "obligation to name the mechanism. Not a test, not "
            "pre-registered, and it does not revise the verdict"),
        "verdict_it_does_not_revise": _read(f"{PASS3}/verdict.json")["outcome"],
        "new_solves": 0,
        "per_device": offsets,
        "device_median_spread": spread,
        "b_matched": {
            "shared_b_range": [lo, hi],
            "per_device": matched,
            "why_post_hoc": (
                "the pre-registered test pools every admissible cell, and the "
                "axes do not span the same b. This restricts both to the b "
                "range they share. It is the comparison the pre-registered "
                "test could not make and it is NOT a second verdict"),
        },
        "corr_dz_b": {"pooled": pooled_b, "within_device": within},
        "n_cells": len(cells),
    }
    p = ROOT / args.out
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
