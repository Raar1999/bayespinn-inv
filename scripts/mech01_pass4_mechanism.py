"""``MECH-01`` pass 4: what the departure from the null is made of.

    PYTHONPATH=src python scripts/mech01_pass4_mechanism.py

Arithmetic over ``outputs/g14/mech01_pass4/jacobians.json``. ``new_solves = 0``.

What this is, and what it is not
--------------------------------
The verdict is in ``verdict.json`` and it is ``GENERIC_ROW_COUNT``, decided by
the pre-registered rule. **Nothing here revises it.** No threshold below is
pre-registered and nothing here is a test.

It exists because the pre-registered rule and the measurement disagree about
what happened, and that disagreement has to be resolved into a statement of fact
rather than left as an ambiguity. The rule returned ``GENERIC_ROW_COUNT``
because it required both held-out devices to clear and ``device_p10`` did not
(``p = 0.148``). But the registered *meaning* of that outcome — "the nested
windows track the null" — is contradicted: all four devices sit **above** the
chain null in the same direction, three of them at ``p <= 0.005``, and the
nested windows are consistently **less** flat than random subsets of equal size.

So the question this module answers is: less flat *because of what*?

The candidate, and why it matters
----------------------------------
The nested sequence takes the ``k`` biases nearest the window centre, so it is
**contiguous** by construction. A random ``k``-subset of the same universe is
**scattered**. Closely spaced biases sample nearly the same operating condition,
so their Jacobian rows are nearly collinear and the leading direction dominates
— a large gap behind the head. That is a property of any smooth response, not of
this device, this doping profile, or any transport regime.

If the nested sets' excess gap is fully accounted for by their **spread**, the
departure carries no mechanism: it says that adjacent measurements are redundant,
which was never in doubt. If a residual survives after spread is accounted for,
something regime-specific is left and ``MECH-01`` has somewhere to go.

The construction: at each ``k``, ordinary least squares of ``gap`` on the
subset's bias **range** over the null draws, then the nested set's **residual**
from that fit, placed as a percentile among the null residuals. A nested residual
percentile near 0.5 means "ordinary once spread is accounted for".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_mech01_pass4 import (
    CONTRAST,
    HELD_OUT,
    N_NULL,
    SEED,
    admissible_k,
    gap_behind_head,
    nested_order,
)

ROOT = Path(__file__).resolve().parents[1]
P4 = "outputs/g14/mech01_pass4"


def _read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def spread_of(biases: np.ndarray, rows: np.ndarray) -> float:
    b = biases[rows]
    return float(b.max() - b.min())


def analyse(jac: np.ndarray, biases_list: List[float]) -> Dict[str, Any]:
    biases = np.asarray(biases_list, dtype=np.float64)
    n = int(jac.shape[0])
    order = nested_order(biases_list)
    rng = np.random.default_rng(SEED)
    rows_out: List[Dict[str, Any]] = []

    for k in admissible_k(n):
        gaps, spreads = [], []
        for _ in range(N_NULL):
            sel = rng.choice(n, size=k, replace=False)
            g = gap_behind_head(np.linalg.svd(jac[sel, :], compute_uv=False))
            if g is None:
                continue
            gaps.append(g)
            spreads.append(spread_of(biases, sel))
        if len(gaps) < 50:
            continue
        g_arr, s_arr = np.asarray(gaps), np.asarray(spreads)

        nested = np.asarray(order[:k])
        g_n = gap_behind_head(np.linalg.svd(jac[nested, :], compute_uv=False))
        s_n = spread_of(biases, nested)
        if g_n is None:
            continue

        raw_pct = float(np.mean(g_arr <= g_n))
        if s_arr.std() > 0:
            slope, intercept = np.polyfit(s_arr, g_arr, 1)
            resid = g_arr - (slope * s_arr + intercept)
            resid_n = g_n - (slope * s_n + intercept)
            resid_pct = float(np.mean(resid <= resid_n))
            corr = float(np.corrcoef(s_arr, g_arr)[0, 1])
        else:
            slope = intercept = resid_pct = corr = float("nan")
            resid_n = float("nan")

        rows_out.append({
            "k": k,
            "nested_gap": g_n,
            "nested_spread_V": s_n,
            "null_spread_median_V": float(np.median(s_arr)),
            "raw_percentile": raw_pct,
            "corr_gap_spread": corr,
            "residual_percentile": resid_pct,
            "nested_residual": float(resid_n),
        })
    return {"n_rows": n, "per_k": rows_out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=f"{P4}/mechanism.json")
    args = ap.parse_args(argv)

    cap = _read(f"{P4}/jacobians.json")
    print("=" * 78)
    print("MECH-01 pass 4  what the departure is made of  (DESCRIPTION, not a test)")
    print("=" * 78)
    print("  The verdict is GENERIC_ROW_COUNT and is not revised here.")
    print("  raw pct = nested gap among null gaps.  resid pct = the same AFTER")
    print("  regressing gap on the subset's bias range. 0.5 means 'ordinary")
    print("  once spread is accounted for'.")

    devices: Dict[str, Any] = {}
    for dname, rec in cap["devices"].items():
        jac = np.asarray(rec["jacobian"], dtype=np.float64)
        res = analyse(jac, rec["biases_used"])
        devices[dname] = res
        role = "HELD OUT" if dname in HELD_OUT else "contrast"
        raw = [r["raw_percentile"] for r in res["per_k"]]
        rsd = [r["residual_percentile"] for r in res["per_k"]]
        cor = [r["corr_gap_spread"] for r in res["per_k"]]
        res["mean_raw_percentile"] = float(np.mean(raw))
        res["mean_residual_percentile"] = float(np.mean(rsd))
        res["mean_corr_gap_spread"] = float(np.mean(cor))
        print(f"\n  {dname}  ({role})")
        print(f"    {'k':>3} {'spread_V':>9} {'null_med':>9} "
              f"{'raw pct':>8} {'resid pct':>10}")
        for r in res["per_k"]:
            print(f"    {r['k']:>3} {r['nested_spread_V']:>9.3f} "
                  f"{r['null_spread_median_V']:>9.3f} "
                  f"{r['raw_percentile']:>8.3f} {r['residual_percentile']:>10.3f}")
        print(f"    mean corr(gap, spread) = {res['mean_corr_gap_spread']:+.3f}")
        print(f"    mean raw percentile    = {res['mean_raw_percentile']:.3f}")
        print(f"    mean residual pctile   = {res['mean_residual_percentile']:.3f}")

    doc = {
        "what_this_is": (
            "a description of what the nested sets' departure from the null is "
            "made of, for U-EMPIR's obligation to characterise a method's "
            "failure mechanism. Not a test, not pre-registered, and it does "
            "not revise the verdict"),
        "verdict_it_does_not_revise": _read(f"{P4}/verdict.json")["outcome"],
        "new_solves": 0,
        "devices": devices,
        "held_out": list(HELD_OUT),
        "contrast": list(CONTRAST),
    }
    p = ROOT / args.out
    p.write_text(json.dumps(doc, indent=2) + "\n",
                 encoding="utf-8", newline="\n")
    print(f"\n  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
