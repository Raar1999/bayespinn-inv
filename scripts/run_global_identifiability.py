"""S-1: global identifiability of the doping profile from terminal I-V.

Oracle-arbitrated throughout. The surrogate is never called: GRAD-01 measured its
directional derivatives as informative only *inside* the identifiable subspace,
and this study probes outside it (SPEC-g6-5).

    python scripts/run_global_identifiability.py --out outputs/global_identifiability_g6
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
    contraction_spectrum,
    witness_search,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest


def make_oracle(cfg: GlobalStudyConfig, grid_n: int = 301):
    """(log10|C| at d anchors, biases) -> (current, trustworthy, converged).

    Chart G, by name (``CHART-01``). Until generation 8 the three lines that
    define this chart were written out here, and again in
    ``scripts/run_witness_falsifier.py``, and again in
    ``bayespinn_inv.inverse.charts.ChartG`` -- three copies of one operator, one
    of them inside the falsifier that was supposed to be independent of the
    study. The chart is now constructed once and imported.

    Anchors are evenly spaced across the device; the magnitude is interpolated
    linearly in log10 between them. Sign follows the project's PN convention
    (PH-03/PH-04): acceptors (negative C) on the left half, donors on the right.
    """
    scaling = Scaling.for_material(SILICON, T=300.0)
    length = cfg.domain_si[1] - cfg.domain_si[0]
    length_scaled = float(scaling.x_to_scaled(np.float64(length)))
    sg = ScharfetterGummel1D(
        Grid1D.uniform(length_scaled, grid_n), scaling, SILICON, SGConfig()
    )
    x_si = scaling.x_to_si(np.asarray(sg.grid.x))
    chart = ChartG(cfg.n_anchor, x_si)

    def oracle(log10_mag, biases):
        doping = chart.charted(log10_mag)
        prev, current, trust, conv = None, [], [], []
        for v in biases:
            state = sg.solve(doping, float(v), initial_state=prev)
            prev = state
            current.append(state.terminal_current)
            trust.append(bool(state.current_is_trustworthy()))
            conv.append(bool(state.converged))
        return np.asarray(current), np.asarray(trust), np.asarray(conv)

    return oracle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/global_identifiability_g6")
    ap.add_argument("--n-witness", type=int, default=2000)
    ap.add_argument("--n-contract", type=int, default=2000)
    ap.add_argument("--n-sweep", type=int, default=1000)
    ap.add_argument("--dims", type=int, nargs="+", default=[2, 4, 8])
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = GlobalStudyConfig()

    man = RunManifest.create(
        "global_identifiability",
        config={**base.to_dict(), "grid_n": args.grid,
                "n_witness": args.n_witness, "n_contract": args.n_contract,
                "n_sweep": args.n_sweep, "dims": args.dims},
        seed=base.seed,
        notes="S-1. Oracle-arbitrated; the surrogate is never called (SPEC-g6-5).",
    )
    print(f"prior hash (fixed before sampling, AH-14): {base.prior_hash()}")
    print(f"floors: noise {base.noise_rel:.2e}  discretisation "
          f"{base.discretisation_floor_rel:.2e}  ->  distinguishability "
          f"{base.distinguishability_floor:.2e}")

    results = {}

    def tick(label, every=250):
        def _p(i, n):
            if i % every == 0 or i == n:
                print(f"    {label} {i}/{n}", flush=True)
        return _p

    print(f"\n[SPEC-g6-1] witness search, d={base.n_anchor}, n={args.n_witness}")
    t0 = time.perf_counter()
    results["witness_search"] = witness_search(
        base, make_oracle(base, args.grid), args.n_witness, tick("sampled"))
    results["witness_search"]["wall_clock_s"] = time.perf_counter() - t0
    print("  ->", results["witness_search"]["verdict"])

    print(f"\n[SPEC-g6-2] contraction spectrum, d={base.n_anchor}, n={args.n_contract}")
    t0 = time.perf_counter()
    results["contraction"] = contraction_spectrum(
        base, make_oracle(base, args.grid), args.n_contract, None, tick("sampled"))
    results["contraction"]["wall_clock_s"] = time.perf_counter() - t0
    print("  ->", results["contraction"]["verdict"])

    print(f"\n[SPEC-g6-3] dimension sweep, d in {args.dims}, n={args.n_sweep} each")
    sweep = {}
    for d in args.dims:
        cfg_d = GlobalStudyConfig(n_anchor=d)
        t0 = time.perf_counter()
        rec = contraction_spectrum(
            cfg_d, make_oracle(cfg_d, args.grid), args.n_sweep, None, tick(f"d={d}"))
        rec["wall_clock_s"] = time.perf_counter() - t0
        sweep[str(d)] = rec
        print(f"  d={d} ->", rec["verdict"])
    results["dimension_sweep"] = sweep

    for key, value in results.items():
        man.add_result(key, value)
    (out / "global_identifiability.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8", newline="\n")
    man.write(out)
    print(f"\nwrote {out}/global_identifiability.json and manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
