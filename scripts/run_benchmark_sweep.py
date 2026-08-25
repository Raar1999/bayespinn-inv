#!/usr/bin/env python
"""Benchmark sweep: SG vs PINN across many held-out doping profiles.

Produces the data behind paper Table 1 (forward-model accuracy).

For each profile family and each bias point, this script measures:
  - phi RMS error (V)
  - log10(n) RMS error
  - log10(p) RMS error
  - |dI|/I relative error
  - wall-clock per solve

Output structure::

    outputs/benchmarks/
      raw_results.csv        # one row per (profile_id, bias)
      summary.json           # per-family aggregate statistics
      figures/
        boxplot_phi_rms.png
        boxplot_I_relative.png
        scatter_I_pinn_vs_sg.png

Usage::

    python scripts/run_benchmark_sweep.py \\
        --ensemble outputs/ensemble/manifest.json \\
        --n_test_profiles 50 \\
        --families step,graded,ldd,defect \\
        --bias_grid 0.0,0.7,15 \\
        --out outputs/benchmarks/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.bayesian.ensembles import DeepEnsemble
from bayespinn_inv.benchmarks.sg_vs_pinn import compare_solvers
from bayespinn_inv.data.datasets import sample_doping
from bayespinn_inv.physics.constants import GAAS, SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.forward_pinn import ForwardPINN, ForwardPINNConfig
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)


def _material_from_name(name: str):
    return {"Si": SILICON, "Silicon": SILICON, "GaAs": GAAS}[name]


def load_ensemble(manifest_path: Path) -> DeepEnsemble:
    """Reconstruct a DeepEnsemble from a manifest.json."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    cfg = manifest["config"]
    material = _material_from_name(cfg["material"]["name"])
    scaling = Scaling.for_material(material, T=cfg["material"]["T"])
    L_scaled = float(scaling.x_to_scaled(
        torch.tensor(cfg["domain_si"][1] - cfg["domain_si"][0])))
    V_a_max_s = float(cfg["dataset"]["bias_range"][1]) / scaling.V_T
    ens = DeepEnsemble(scaling, material)
    for seed, ck_path in zip(manifest["member_seeds"], manifest["checkpoints"]):
        net_cfg = PINNConfig(
            in_dim=cfg["network"]["in_dim"],
            hidden_dim=cfg["network"]["hidden_dim"],
            num_blocks=cfg["network"]["num_blocks"],
            fourier_features=cfg["network"]["fourier_features"],
            fourier_sigma=cfg["network"]["fourier_sigma"],
            dropout=cfg["network"]["dropout"],
            doping_dim=cfg["network"]["doping_dim"],
            output_dim=cfg["network"]["output_dim"],
            seed=seed,
            x_scaled_extent=L_scaled,
            V_a_scaled_extent=V_a_max_s,
        )
        net = SemiconductorPINN(net_cfg)
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        net.load_state_dict(ck["model_state"])
        net.eval()
        fwd = ForwardPINN(net, scaling, material,
                          ForwardPINNConfig(
                              n_query=cfg["network"].get("n_query", 201),
                              n_anchor=cfg["network"]["doping_dim"],
                              domain_si=tuple(cfg["domain_si"]),
                          ))
        ens.add_member(fwd)
    return ens, manifest


def _aggregate(rows: List[Dict], by: str) -> Dict[str, Dict]:
    """Aggregate per-row metrics by a grouping key (e.g. 'family')."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[r[by]].append(r)
    summary = {}
    metric_keys = ["phi_rms_V", "phi_max_V", "log_n_rms", "log_p_rms",
                   "I_relative", "sg_time_ms", "pinn_time_ms"]
    for k, rs in groups.items():
        s = {"n": len(rs)}
        for m in metric_keys:
            vals = np.asarray([r[m] for r in rs if np.isfinite(r[m])])
            if vals.size == 0:
                continue
            s[m] = {
                "median": float(np.median(vals)),
                "mean":   float(np.mean(vals)),
                "p10":    float(np.quantile(vals, 0.10)),
                "p90":    float(np.quantile(vals, 0.90)),
                "max":    float(np.max(vals)),
                "n_finite": int(vals.size),
            }
        summary[k] = s
    return summary


def _maybe_save_figures(rows: List[Dict], fig_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib unavailable; skipping figures)")
        return
    fig_dir.mkdir(parents=True, exist_ok=True)
    families = sorted({r["family"] for r in rows})
    # Boxplot of phi RMS by family
    fig, ax = plt.subplots(figsize=(5, 3.5))
    data = [[r["phi_rms_V"] for r in rows if r["family"] == f and np.isfinite(r["phi_rms_V"])]
            for f in families]
    ax.boxplot(data, labels=families)
    ax.set_ylabel(r"$\phi$ RMS error (V)")
    ax.set_yscale("log")
    ax.set_title("Forward model accuracy by family")
    fig.tight_layout(); fig.savefig(fig_dir / "boxplot_phi_rms.png", dpi=200)
    # Boxplot of I relative error by family
    fig, ax = plt.subplots(figsize=(5, 3.5))
    data = [[r["I_relative"] for r in rows if r["family"] == f and np.isfinite(r["I_relative"])]
            for f in families]
    ax.boxplot(data, labels=families)
    ax.set_ylabel(r"$|I_{\rm PINN} - I_{\rm SG}| / |I_{\rm SG}|$")
    ax.set_yscale("log")
    ax.set_title("Terminal current relative error by family")
    fig.tight_layout(); fig.savefig(fig_dir / "boxplot_I_relative.png", dpi=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble", required=True,
                    help="Path to ensemble manifest.json")
    ap.add_argument("--n_test_profiles", type=int, default=50,
                    help="Number of profiles per family")
    ap.add_argument("--families", default="step,graded,ldd,defect")
    ap.add_argument("--bias_grid", default="0.0,0.7,15",
                    help="Format: start,stop,num")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load ensemble (we benchmark only against member 0; ensemble mean is for
    # downstream calibration, not point-accuracy)
    ens, manifest = load_ensemble(Path(args.ensemble))
    pinn = ens.members[0]
    scaling = ens.scaling
    material = ens.material
    domain = tuple(manifest["config"]["domain_si"])

    # Build SG oracle on a fine grid
    L_s = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
    sg_grid = Grid1D.uniform(L_s, 301)
    sg = ScharfetterGummel1D(sg_grid, scaling, material, SGConfig())

    # Parse bias grid
    bs, be, bn = args.bias_grid.split(",")
    biases = np.linspace(float(bs), float(be), int(bn))
    families = args.families.split(",")

    rng = np.random.default_rng(args.seed)
    rows: List[Dict] = []
    print(f"Benchmark sweep: {len(families)} families x "
          f"{args.n_test_profiles} profiles x {len(biases)} biases")
    t_start = time.perf_counter()

    for family in families:
        print(f"\n--- family: {family} ---")
        for k in range(args.n_test_profiles):
            sample = sample_doping(family, n_points=128, domain_si=domain, rng=rng)
            dop_t = torch.as_tensor(sample.doping_si, dtype=torch.float32)
            try:
                res = compare_solvers(sg, pinn, dop_t, biases, warmup=0)
            except Exception as e:
                print(f"  skipped profile {k}: {e}")
                continue
            for i, V in enumerate(res.biases):
                rows.append({
                    "family": family,
                    "profile_id": k,
                    "bias_V": float(V),
                    "phi_rms_V":  float(res.phi_rms_error[i]),
                    "phi_max_V":  float(res.phi_max_error[i]),
                    "log_n_rms":  float(res.n_log_rms_error[i]),
                    "log_p_rms":  float(res.p_log_rms_error[i]),
                    "I_relative": float(res.I_relative_error[i]),
                    "sg_time_ms":   1e3 * res.time_per_solve_sg,
                    "pinn_time_ms": 1e3 * res.time_per_solve_pinn,
                })
            if (k + 1) % 10 == 0:
                print(f"  done {k + 1} / {args.n_test_profiles}")

    elapsed = time.perf_counter() - t_start
    print(f"\nTotal wall-clock: {elapsed:.1f}s, "
          f"{len(rows)} (profile, bias) rows")

    # Write raw CSV
    csv_path = out_dir / "raw_results.csv"
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"  raw -> {csv_path}")

    # Aggregate
    summary = {
        "by_family": _aggregate(rows, by="family"),
        "overall":   _aggregate(rows, by="bias_V"),
        "n_rows":    len(rows),
        "elapsed_s": elapsed,
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  summary -> {out_dir / 'summary.json'}")

    # Print headline numbers
    print("\nHeadline metrics by family (median across all biases):")
    print(f"  {'family':10s} {'phi_rms (V)':>14s} {'log_n_rms':>12s} "
          f"{'|dI|/I':>12s}")
    for fam, s in summary["by_family"].items():
        print(f"  {fam:10s} "
              f"{s['phi_rms_V']['median']:14.3e} "
              f"{s['log_n_rms']['median']:12.3f} "
              f"{s['I_relative']['median']:12.3e}")

    # Figures
    fig_dir = out_dir / "figures"
    _maybe_save_figures(rows, fig_dir)
    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
