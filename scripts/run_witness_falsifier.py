"""Falsifier for S-1: is the witness pair a solver artefact or a real degeneracy?

Generation-6 ruling section 4.6 weights this candidate heavily, and GRAD-02 is the
reason: that generation's falsifier overturned the generation's own finding within
the same generation.

A witness pair is two profiles, far apart in parameter space, whose oracle I-V
curves differ by less than the distinguishability floor. There are two ways that
can happen:

  PHYSICAL   the device genuinely cannot distinguish them -- the information is
             not in the terminal current at all
  ARTEFACT   the *solver* cannot distinguish them at the grid and tolerance used,
             and a better-resolved solve separates them

Only the first is a statement about semiconductors. This script tries to destroy
the pair: it re-solves both members on progressively finer grids and with tighter
convergence tolerances, and reports whether the observational distance stays below
the floor or grows through it.

A pair that survives refinement is evidence of physical degeneracy. A pair that
separates was an artefact, and the S-1 conclusion must be withdrawn to whatever
survives.

    python scripts/run_witness_falsifier.py --out outputs/witness_falsifier_g6
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest


def solve_profile(log10_mag, biases, grid_n, sg_cfg, domain_si=(0.0, 1e-6)):
    """One I-V curve, with the solver's own verdict on every point."""
    scaling = Scaling.for_material(SILICON, T=300.0)
    length_scaled = float(scaling.x_to_scaled(np.float64(domain_si[1] - domain_si[0])))
    sg = ScharfetterGummel1D(Grid1D.uniform(length_scaled, grid_n), scaling, SILICON, sg_cfg)
    x_si = scaling.x_to_si(np.asarray(sg.grid.x))
    # CHART-01: this used to be a third hand-written copy of chart G, inside the
    # falsifier meant to be independent of the study that has the other two.
    # Two copies agreeing proves nothing about either; one definition does.
    doping = ChartG(len(log10_mag), x_si).charted(log10_mag)
    prev, current, trust = None, [], []
    for v in biases:
        st = sg.solve(doping, float(v), initial_state=prev)
        prev = st
        current.append(st.terminal_current)
        trust.append(bool(st.current_is_trustworthy() and st.converged))
    return np.asarray(current), np.asarray(trust)


def distance(a, b, mask):
    """Max relative difference over the points both solves certify."""
    if not mask.any():
        return float("nan")
    denom = np.maximum(np.abs(a[mask]), np.abs(b[mask]))
    return float(np.max(np.abs(a[mask] - b[mask]) / denom))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--study", default="outputs/global_identifiability_g6/global_identifiability.json")
    ap.add_argument("--out", default="outputs/witness_falsifier_g6")
    ap.add_argument("--grids", type=int, nargs="+", default=[301, 601, 1201])
    # DOC-08. This used to be a bare ``pairs[:3]`` in the loop below: the run
    # tested three of thirteen pairs and reported "all tested pairs survive",
    # which is true and reads as its opposite. The cap is now an argument, it
    # defaults to testing every offered pair, and the payload records how many
    # of how many were tested so the verdict cannot be quoted without them.
    ap.add_argument("--max-pairs", type=int, default=None,
                    help="test only the first N pairs. The generation-6 run "
                         "used 3 and its artefact records that; the default "
                         "here is every offered pair.")
    args = ap.parse_args()

    study = json.loads(Path(args.study).read_text(encoding="utf-8"))
    ws = study["witness_search"]
    cfg = GlobalStudyConfig()
    biases = list(cfg.biases)
    floor = cfg.distinguishability_floor

    pairs = ws.get("witnesses") or []
    label = "witness"
    if not pairs:
        # No witness: falsify the *other* way -- take the closest far-apart pair
        # found and ask whether refinement brings it BELOW the floor, which would
        # mean the search missed a real degeneracy at the production grid.
        closest = ws.get("closest_far_pair")
        if closest is None:
            print("no pairs to test"); return 1
        pairs, label = [closest], "closest-far-pair (no witness was found)"

    n_offered = len(pairs)
    tested = pairs if args.max_pairs is None else pairs[:args.max_pairs]

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    man = RunManifest.create(
        "witness_falsifier",
        config={"grids": args.grids, "floor": floor, "source_study": args.study,
                "n_pairs": n_offered, "n_pairs_tested": len(tested),
                "max_pairs": args.max_pairs, "label": label},
        seed=cfg.seed,
        notes="Section 4.6 falsifier: does the pair survive grid refinement and a "
              "tighter tolerance, or was it a solver artefact?",
    )

    print(f"testing {len(tested)} of {n_offered} {label} pair(s) against "
          f"floor {floor:.3e}\n")
    records = []
    for k, pair in enumerate(tested):
        a = np.asarray(pair["profile_a_log10"], dtype=float)
        b = np.asarray(pair["profile_b_log10"], dtype=float)
        print(f"--- pair {k}: separation {pair['separation_decades']:.3f} decades, "
              f"reported distance {pair['observational_distance']:.4e}")
        rows = []
        for grid_n in args.grids:
            for tag, sg_cfg in (("default", SGConfig()),
                                ("tight", SGConfig(tol_carrier=1e-12, max_outer=200))):
                ia, ta = solve_profile(a, biases, grid_n, sg_cfg)
                ib, tb = solve_profile(b, biases, grid_n, sg_cfg)
                mask = ta & tb
                d = distance(ia, ib, mask)
                rows.append({"grid_n": grid_n, "tolerance": tag,
                             "n_trustworthy": int(mask.sum()), "n_biases": len(biases),
                             "observational_distance": d,
                             "below_floor": bool(d < floor)})
                print(f"      N={grid_n:<5} tol={tag:<8} certified {int(mask.sum())}/{len(biases)}"
                      f"  distance {d:.4e}  {'BELOW floor' if d < floor else 'ABOVE floor'}")
        survived = all(r["below_floor"] for r in rows if np.isfinite(r["observational_distance"]))
        records.append({"pair_index": k, "separation_decades": pair["separation_decades"],
                        "reported_distance": pair["observational_distance"],
                        "refinements": rows, "survives_refinement": survived})
        print(f"      -> {'SURVIVES: consistent with a physical degeneracy' if survived else 'SEPARATES: was a solver artefact'}\n")

    # DOC-08: the verdict carries its denominator. The generation-6 wording,
    # "all tested pairs survive grid refinement and a tighter tolerance", was
    # true over three of thirteen and read as a statement about thirteen.
    n_survive = sum(1 for r in records if r["survives_refinement"])
    verdict = (
        f"{len(records)} of {n_offered} pairs tested; "
        + (f"all {n_survive} survive grid refinement and a tighter tolerance"
           if records and n_survive == len(records)
           else f"{n_survive} survive and {len(records) - n_survive} separated "
                f"under refinement")
        + (f"; the remaining {n_offered - len(records)} were not tested"
           if len(records) < n_offered else ""))
    payload = {"label": label, "floor": floor, "grids": args.grids,
               "n_pairs_offered": n_offered, "n_pairs_tested": len(records),
               "n_surviving": n_survive,
               "pairs": records, "verdict": verdict}
    man.add_result("falsifier", payload)
    (out / "witness_falsifier.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    man.write(out)
    print("VERDICT:", verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
