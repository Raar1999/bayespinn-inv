#!/usr/bin/env python
"""Inverse-design sweep over targets x noise x parameterizations.

Produces the data behind paper Table 2 / Figure 3 (inverse recovery
accuracy under measurement noise).

For each (target_profile, noise_level, parameterization):
  1. Generate synthetic I-V from SG with multiplicative noise
  2. Run inverse design once per ensemble member (M runs)
  3. Aggregate per-anchor mean + 90% quantile band of recovered C
  4. Compute relative L2 doping error and band coverage of true profile

Output structure::

    outputs/inverse_sweep/
      raw_results.json         # full per-run details
      summary.csv              # one row per (target, noise, param)
      figures/
        error_vs_noise.png
        coverage_vs_noise.png

Usage::

    python scripts/run_inverse_sweep.py \\
        --ensemble outputs/ensemble/manifest.json \\
        --n_targets 30 \\
        --noise_levels 0.0,0.01,0.05,0.10 \\
        --parameterizations free,step,graded \\
        --out outputs/inverse_sweep/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.data.datasets import sample_doping
from bayespinn_inv.inverse.inverse_design import (
    FreePointwiseDoping,
    GradedJunctionDoping,
    InverseConfig,
    InverseDesigner,
    StepJunctionDoping,
)
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

# Reuse loader from benchmark script
from bayespinn_inv.surrogate import load_forward_ensemble as load_ensemble


def _make_param(kind: str, x_si: torch.Tensor, init_C: torch.Tensor = None):
    if kind == "free":
        if init_C is None:
            init_C = torch.zeros_like(x_si)
        return FreePointwiseDoping(x_si, init_C)
    if kind == "step":
        return StepJunctionDoping(x_si)
    if kind == "graded":
        return GradedJunctionDoping(x_si)
    raise ValueError(f"Unknown parameterization: {kind!r}")


def _sg_iv(sg, sg_grid, scaling, doping_si: np.ndarray,
            biases: np.ndarray) -> np.ndarray:
    """Compute the SG-oracle I-V curve."""
    # SG.solve auto-interpolates to its own grid as of the latest fix
    currents = []
    prev = None
    for V in biases:
        s = sg.solve(doping_si, float(V), initial_state=prev)
        currents.append(s.terminal_current)
        prev = s
    return np.asarray(currents)


def _coverage_fraction(
    C_lo: np.ndarray, C_hi: np.ndarray, C_true: np.ndarray,
) -> float:
    """Fraction of true-profile points inside the predicted band."""
    return float(np.mean((C_true >= C_lo) & (C_true <= C_hi)))


def _relative_l2(C_pred: np.ndarray, C_true: np.ndarray) -> float:
    err = np.linalg.norm(C_pred - C_true)
    return float(err / max(np.linalg.norm(C_true), 1e-30))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble", required=True)
    ap.add_argument("--n_targets", type=int, default=30)
    ap.add_argument("--target_families", default="step,graded")
    ap.add_argument("--noise_levels", default="0.0,0.01,0.05,0.10")
    ap.add_argument("--parameterizations", default="free,step,graded")
    ap.add_argument("--bias_grid", default="0.05,0.6,10")
    ap.add_argument("--n_inverse_iters", type=int, default=600)
    ap.add_argument("--lr", type=float, default=5e-3)
    ap.add_argument("--lambda_TV", type=float, default=0.0)
    ap.add_argument("--lambda_smooth", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--match_space", default="auto",
                    help="'linear', 'symlog', or 'auto' (symlog for surrogate "
                         "manifests, linear for pure-physics PINN).")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ens, manifest = load_ensemble(Path(args.ensemble))
    scaling = ens.scaling
    material = ens.material
    domain = tuple(manifest["config"]["domain_si"])

    L_s = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
    sg_grid = Grid1D.uniform(L_s, 301)
    sg = ScharfetterGummel1D(sg_grid, scaling, material, SGConfig())

    families = args.target_families.split(",")
    noise_levels = [float(x) for x in args.noise_levels.split(",")]
    parameterizations = args.parameterizations.split(",")
    bs, be, bn = args.bias_grid.split(",")
    biases = np.linspace(float(bs), float(be), int(bn))

    rng = np.random.default_rng(args.seed)
    n_anchor = manifest["config"]["network"]["doping_dim"]
    x_anchor = torch.linspace(domain[0], domain[1], n_anchor)

    match_space = args.match_space
    if match_space == "auto":
        match_space = "symlog" if manifest.get("type") == "surrogate" else "linear"
    print(f"  inverse current-matching space: {match_space}")

    icfg_base = InverseConfig(
        n_iters=args.n_inverse_iters, lr=args.lr, optimizer="adam",
        lambda_TV=args.lambda_TV, lambda_smooth=args.lambda_smooth,
        lambda_solubility=1.0, log_every=10**9, seed=args.seed,
        match_space=match_space,
        clamp_doping=(manifest.get("type") == "surrogate"),
        C_min_abs=5.0e20, C_max_abs=5.0e22,
    )

    rows: List[Dict[str, Any]] = []
    raw: List[Dict[str, Any]] = []

    print(f"Sweep: {len(families)}F x {args.n_targets}T x {len(noise_levels)}N "
          f"x {len(parameterizations)}P x {ens.M}M ensemble members")
    t_start = time.perf_counter()

    # Restrict target doping to the forward model's validated range when it's
    # a surrogate (it extrapolates poorly outside, and SG can go singular at
    # very high doping). Interior of the [5e20, 5e22] training range.
    target_doping_range = (6e20, 4e22) if manifest.get("type") == "surrogate" else None

    for family in families:
        print(f"\n=== target family: {family} ===")
        for t in range(args.n_targets):
            target = sample_doping(family, n_points=128, domain_si=domain, rng=rng,
                                   doping_range=target_doping_range)
            sg_iv_clean = _sg_iv(sg, sg_grid, scaling, target.doping_si, biases)
            # Sample C_true onto the anchor grid for L2 comparison
            x_a_np = x_anchor.numpy()
            C_true_anchor = np.interp(x_a_np, target.x_si, target.doping_si)
            for noise in noise_levels:
                # Add multiplicative + small additive noise (consistent w/ AL)
                noisy = sg_iv_clean * (1.0 + noise * rng.standard_normal(len(biases))) \
                        + noise * 1e-3 * rng.standard_normal(len(biases))
                target_b_t = torch.as_tensor(biases, dtype=torch.float32)
                target_I_t = torch.as_tensor(noisy, dtype=torch.float32)
                for param_kind in parameterizations:
                    # Per-member recoveries -> uncertainty band on C
                    per_member_C = []
                    per_member_loss = []
                    for _m_idx, fwd in enumerate(ens.members):
                        param = _make_param(param_kind, x_anchor)
                        designer = InverseDesigner(fwd, icfg_base)
                        result = designer.design(param, target_b_t, target_I_t)
                        C_rec = result.C_recovered_si.detach().cpu().numpy()
                        # If parameterization gives a profile on x_anchor
                        # (StepJunctionDoping / GradedJunctionDoping), it has the
                        # same shape already; FreePointwiseDoping likewise.
                        if C_rec.shape[0] != n_anchor:
                            C_rec = np.interp(x_a_np,
                                np.linspace(domain[0], domain[1], C_rec.shape[0]),
                                C_rec)
                        per_member_C.append(C_rec)
                        per_member_loss.append(result.final_loss)
                    C_stack = np.stack(per_member_C, axis=0)  # (M, n_anchor)
                    C_mean = C_stack.mean(axis=0)
                    C_lo = np.quantile(C_stack, 0.05, axis=0)
                    C_hi = np.quantile(C_stack, 0.95, axis=0)
                    # Metrics
                    rel_l2 = _relative_l2(C_mean, C_true_anchor)
                    coverage = _coverage_fraction(C_lo, C_hi, C_true_anchor)
                    rows.append({
                        "family":         family,
                        "target_id":      t,
                        "noise":          noise,
                        "parameterization": param_kind,
                        "rel_L2_C":       rel_l2,
                        "coverage_90":    coverage,
                        "mean_final_loss": float(np.mean(per_member_loss)),
                        "max_final_loss":  float(np.max(per_member_loss)),
                    })
                    raw.append({
                        **rows[-1],
                        "x_anchor":       x_a_np.tolist(),
                        "C_true":         C_true_anchor.tolist(),
                        "C_mean":         C_mean.tolist(),
                        "C_lo":           C_lo.tolist(),
                        "C_hi":           C_hi.tolist(),
                    })
            if (t + 1) % 5 == 0:
                print(f"  done {t + 1}/{args.n_targets} targets, "
                      f"{time.perf_counter() - t_start:.0f}s elapsed")

    elapsed = time.perf_counter() - t_start
    print(f"\nTotal: {len(rows)} (target, noise, param) rows in {elapsed:.0f}s")

    # CSV
    if rows:
        with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"  summary -> {out_dir / 'summary.csv'}")
    with open(out_dir / "raw_results.json", "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, default=str)

    # Aggregate by (parameterization, noise)
    from collections import defaultdict
    agg = defaultdict(list)
    for r in rows:
        agg[(r["parameterization"], r["noise"])].append(r)
    summary = {}
    for (p, n), rs in agg.items():
        l2 = np.asarray([r["rel_L2_C"] for r in rs])
        cov = np.asarray([r["coverage_90"] for r in rs])
        key = f"{p}/noise={n}"
        summary[key] = {
            "n": len(rs),
            "rel_L2_C_median": float(np.median(l2)),
            "rel_L2_C_mean":   float(np.mean(l2)),
            "rel_L2_C_p10":    float(np.quantile(l2, 0.10)),
            "rel_L2_C_p90":    float(np.quantile(l2, 0.90)),
            "coverage_90_mean":  float(np.mean(cov)),
            "coverage_90_median": float(np.median(cov)),
        }
    with open(out_dir / "aggregate.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    # Headline print
    print("\nHeadline (median rel-L2 doping error, target coverage = 0.90):")
    print(f"  {'param':12s} {'noise':>8s} {'rel-L2':>10s} {'coverage':>10s}")
    for k, s in sorted(summary.items()):
        p_name, n_name = k.split("/")
        n_val = n_name.split("=")[1]
        print(f"  {p_name:12s} {n_val:>8s} {s['rel_L2_C_median']:10.4f} "
              f"{s['coverage_90_median']:10.4f}")

    # Figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig_dir = out_dir / "figures"
        fig_dir.mkdir(exist_ok=True)
        # Error vs noise, one line per parameterization
        params_unique = sorted({r["parameterization"] for r in rows})
        noises_unique = sorted({r["noise"] for r in rows})
        fig, ax = plt.subplots(figsize=(5, 3.4))
        for p in params_unique:
            xs, ys, ylo, yhi = [], [], [], []
            for n in noises_unique:
                rs = [r["rel_L2_C"] for r in rows
                      if r["parameterization"] == p and r["noise"] == n]
                if not rs:
                    continue
                xs.append(n); ys.append(np.median(rs))
                ylo.append(np.quantile(rs, 0.25))
                yhi.append(np.quantile(rs, 0.75))
            ax.errorbar(xs, ys, yerr=[np.array(ys)-np.array(ylo),
                                       np.array(yhi)-np.array(ys)],
                        label=p, marker="o", capsize=3)
        ax.set_xlabel("Measurement noise (relative)")
        ax.set_ylabel("Median relative L2 doping error")
        ax.set_yscale("log")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(fig_dir / "error_vs_noise.png", dpi=200)
        # Coverage vs noise
        fig, ax = plt.subplots(figsize=(5, 3.4))
        for p in params_unique:
            xs, ys = [], []
            for n in noises_unique:
                rs = [r["coverage_90"] for r in rows
                      if r["parameterization"] == p and r["noise"] == n]
                if not rs:
                    continue
                xs.append(n); ys.append(np.median(rs))
            ax.plot(xs, ys, "o-", label=p)
        ax.axhline(0.90, color="k", lw=0.7, ls="--", label="Target 0.90")
        ax.set_xlabel("Measurement noise (relative)")
        ax.set_ylabel("Empirical coverage of 90% band")
        ax.set_ylim(0, 1)
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(fig_dir / "coverage_vs_noise.png", dpi=200)
        print(f"  figures -> {fig_dir}")
    except ImportError:
        pass

    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
