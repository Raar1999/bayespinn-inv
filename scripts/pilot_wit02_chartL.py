"""``WITNESS-04`` pilot: what does refining chart L's 37 witness pairs cost?

    PYTHONPATH=src python scripts/pilot_wit02_chartL.py --pairs 3

What this is
------------
A **cost measurement**, not a refinement result. The operator directive section 2
``U-BUDGET`` requires *a measured pilot, not an estimate, and the factor by
which it overruns*, and states that a budget verdict without a pilot is void.
This module is that pilot and nothing else: it runs generation 6's refinement
battery -- the same one imported from :mod:`run_g9` that
:mod:`run_wit02_chartG` ran -- over a small prefix of chart L's witness pairs,
times it, and extrapolates to all 37.

It writes no register, updates no coverage, and recounts no barrier. The
refinement outcomes it happens to observe on the piloted pairs are recorded
because discarding a measurement already paid for is its own kind of waste, but
they are recorded as ``pilot_observations`` and they are **not** a ``WIT-02``
coverage claim: coverage is a property of the whole set, and ``DOC-08`` forbids
reporting a filtered subset as though it were the set.

Why a prefix and not a random sample
------------------------------------
The extrapolation is over *wall clock*, and wall clock here is dominated by the
Scharfetter-Gummel solve, whose cost depends on the grid and the tolerance --
both fixed by the battery -- and not on which pair is being solved. A prefix is
therefore as good as a sample for the quantity being extrapolated, and it is
reproducible without carrying a seed. The pilot reports the **per-pair spread**
it observed so the assumption is checkable rather than asserted: if the slowest
piloted pair is far from the fastest, the projection is quoted as a range and
the assumption is reported as failing.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_g9 import (
    REFINEMENT_GRIDS,
    REFINEMENT_TOLS,
    build_solver,
    iv,
    obs_dist,
)

from bayespinn_inv.inverse.charts import ChartL
from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
)

ROOT = Path(__file__).resolve().parents[1]
G8_REPRODUCE = "outputs/g8/reproduce.json"
SET_LABEL = "chart_L_d16"


def _battery_timed(cfg, kept, ia, ib, floor):
    """Generation 6's battery on one chart-L pair, with per-cell wall clock."""
    biases = list(cfg.biases)
    rows = []
    for grid in REFINEMENT_GRIDS:
        for tname, sg_cfg in REFINEMENT_TOLS:
            t0 = time.perf_counter()
            sg_r, x_r = build_solver(cfg, grid, sg_cfg)
            chart_r = ChartL(16, x_r)
            cur_a, tr_a, cv_a = iv(sg_r, chart_r.charted(kept[ia]), biases)
            cur_b, tr_b, cv_b = iv(sg_r, chart_r.charted(kept[ib]), biases)
            mask = tr_a & cv_a & tr_b & cv_b
            dist = obs_dist(cur_a, cur_b, mask)
            rows.append({
                "grid_n": grid,
                "tolerance": tname,
                "tol_carrier": float(sg_cfg.tol_carrier),
                "observational_distance": dist,
                "n_biases_certified": int(np.sum(mask)),
                "n_biases": len(biases),
                "below_floor": bool(dist < floor),
                "wall_clock_s": time.perf_counter() - t0,
            })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=3,
                    help="how many witness pairs to pilot")
    ap.add_argument("--out", default="outputs/g11/pilot_chartL.json")
    args = ap.parse_args(argv)

    rep = json.loads(
        (ROOT / G8_REPRODUCE).read_text(encoding="utf-8"))[SET_LABEL]
    kept = np.asarray(rep["kept_log10"], dtype=np.float64)
    pairs = [tuple(p) for p in rep["witness_pair_indices"]]
    floor = float(rep["floors"]["distinguishability"])
    cfg = GlobalStudyConfig(n_anchor=16)

    n_total = len(pairs)
    n_pilot = min(args.pairs, n_total)
    per_member = len(REFINEMENT_GRIDS) * len(REFINEMENT_TOLS)

    print("=" * 74)
    print("WITNESS-04 PILOT  chart L, d=16 -- cost of the WIT-02 battery")
    print("=" * 74)
    print(f"  witness pairs in the set  : {n_total}")
    print(f"  pairs piloted             : {n_pilot}")
    print(f"  battery                   : N={list(REFINEMENT_GRIDS)} x "
          f"{[t[0] for t in REFINEMENT_TOLS]}  "
          f"({per_member} solves per member)")
    print(f"  distinguishability floor  : {floor}")
    print()

    records, per_pair = [], []
    t_all = time.perf_counter()
    for k in range(n_pilot):
        ia, ib = pairs[k]
        t0 = time.perf_counter()
        rows = _battery_timed(cfg, kept, ia, ib, floor)
        elapsed = time.perf_counter() - t0
        per_pair.append(elapsed)
        survives = all(r["below_floor"] for r in rows)
        records.append({
            "pair_index": k,
            "member_indices": [int(ia), int(ib)],
            "separation_decades": float(rep["witness_pair_separation"][k]),
            "g8_observational_distance": float(rep["witness_pair_distance"][k]),
            "refinements": rows,
            "survives_battery": survives,
            "wall_clock_s": elapsed,
        })
        worst = max(r["observational_distance"] for r in rows)
        print(f"  pair {k:2d}  members {ia:5d},{ib:5d}   "
              f"worst d = {worst:.6f}   floor {floor}   "
              f"{'SURVIVES' if survives else 'SEPARATES'}   {elapsed:6.1f} s")

    total = time.perf_counter() - t_all
    mean = float(np.mean(per_pair))
    lo, hi = float(np.min(per_pair)), float(np.max(per_pair))
    spread = hi / lo if lo else None

    out = {
        "what_this_is": (
            "a COST MEASUREMENT for the U-BUDGET class, not a WIT-02 coverage "
            "result. Coverage is a property of the whole set and this ran a "
            "prefix of it."
        ),
        "set": SET_LABEL,
        "n_pairs_in_set": n_total,
        "n_pairs_piloted": n_pilot,
        "battery": {
            "grids": list(REFINEMENT_GRIDS),
            "tolerances": [t[0] for t in REFINEMENT_TOLS],
            "solves_per_member": per_member,
            "inherited_from": (
                "run_g9.REFINEMENT_GRIDS and run_g9.REFINEMENT_TOLS, imported "
                "rather than restated -- the same objects run_wit02_chartG.py "
                "used for chart G"
            ),
        },
        "timing": {
            "pilot_total_s": total,
            "per_pair_s": per_pair,
            "per_pair_mean_s": mean,
            "per_pair_min_s": lo,
            "per_pair_max_s": hi,
            "per_pair_spread_factor": spread,
        },
        "projection": {
            "all_pairs_s": mean * n_total,
            "all_pairs_plus_null_control_s": mean * (n_total + 1),
            "all_pairs_low_s": lo * n_total,
            "all_pairs_high_s": hi * n_total,
            "basis": (
                "mean piloted pair cost x 37. The battery's cost is set by the "
                "grid and the tolerance, both fixed, so it does not depend on "
                "which pair is solved; per_pair_spread_factor is what makes "
                "that checkable rather than asserted."
            ),
        },
        "pilot_observations": {
            "note": (
                "recorded because the solves were paid for. NOT a coverage "
                "claim and NOT a WIT-02 result for chart L: this is "
                f"{n_pilot} of {n_total} pairs, and DOC-08 forbids reporting "
                "a filtered subset as though it were the set."
            ),
            "records": records,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": sys.platform,
            "machine": platform.machine(),
        },
    }
    path = ROOT / args.out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")

    print()
    print(f"  per-pair mean             : {mean:.1f} s")
    print(f"  per-pair spread           : {lo:.1f} s .. {hi:.1f} s "
          f"(x{spread:.2f})")
    print(f"  PROJECTED, all {n_total} pairs : {mean * n_total:.0f} s "
          f"({mean * n_total / 60:.1f} min)")
    print(f"  PROJECTED, + null control : {mean * (n_total + 1):.0f} s "
          f"({mean * (n_total + 1) / 60:.1f} min)")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
