#!/usr/bin/env python
"""Defect detection case study (paper Figure 5).

A clean self-contained demonstration of the full BayesPINN-Inv pipeline:

  1. Construct a synthetic device with a known buried defect cluster on
     top of a baseline PN step junction.
  2. Generate a synthetic I-V measurement set from the SG oracle with
     realistic multiplicative noise.
  3. Run inverse design *once per ensemble member* to obtain a per-
     member recovered profile.
  4. Aggregate to a posterior mean + 90% credible band on C(x).
  5. Check whether the 90% band contains the true defect amplitude and
     location. Report coverage and recovered defect parameters.
  6. Plot the hero figure: recovered profile with shaded band against
     true profile, plus a side panel showing measured vs predicted I-V.

Usage::

    python scripts/defect_case_study.py \\
        --ensemble outputs/ensemble/manifest.json \\
        --defect_position 700e-9 --defect_amplitude 5e22 --defect_width 50e-9 \\
        --n_iv_points 10 --measurement_noise 0.02 \\
        --out outputs/defect_study/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.data.datasets import defect_profile
from bayespinn_inv.inverse.charts import regrid_signed
from bayespinn_inv.inverse.inverse_design import (
    FreePointwiseDoping,
    InverseConfig,
    InverseDesigner,
)
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.surrogate import load_forward_ensemble as load_ensemble
from bayespinn_inv.visualization.plots import (
    PALETTE,
    apply_style,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble", required=True)
    ap.add_argument("--N_A", type=float, default=1e22)
    ap.add_argument("--N_D", type=float, default=1e22)
    ap.add_argument("--x_junction", type=float, default=5e-7)
    ap.add_argument("--defect_position", type=float, default=7e-7)
    ap.add_argument("--defect_amplitude", type=float, default=5e22)
    ap.add_argument("--defect_width", type=float, default=5e-8)
    ap.add_argument("--n_iv_points", type=int, default=10)
    ap.add_argument("--measurement_noise", type=float, default=0.02)
    ap.add_argument("--n_inverse_iters", type=int, default=800)
    ap.add_argument("--lambda_TV", type=float, default=0.5)
    ap.add_argument("--lambda_smooth", type=float, default=1e-4)
    ap.add_argument("--lr", type=float, default=5e-3)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load ensemble
    ens, manifest = load_ensemble(Path(args.ensemble))
    scaling = ens.scaling
    material = ens.material
    domain = tuple(manifest["config"]["domain_si"])
    n_anchor = manifest["config"]["network"]["doping_dim"]
    print(f"Loaded ensemble of M={ens.M}, domain={domain}, n_anchor={n_anchor}")

    # 2) Construct the true profile (defect on top of baseline step)
    x_true = np.linspace(domain[0], domain[1], 256)
    C_true = defect_profile(
        x_true, N_A=args.N_A, N_D=args.N_D,
        x_junction=args.x_junction,
        defect_amplitude=args.defect_amplitude,
        defect_center=args.defect_position,
        defect_width=args.defect_width,
    )
    print(f"True profile: N_A=N_D={args.N_A:.1e}, x_j={args.x_junction*1e9:.0f} nm")
    print(f"  defect: amp={args.defect_amplitude:+.1e}, "
          f"center={args.defect_position*1e9:.0f} nm, "
          f"width={args.defect_width*1e9:.0f} nm")

    # 3) Generate the synthetic measurement set
    L_s = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 301), scaling, material, SGConfig())
    biases = np.linspace(0.05, manifest["config"]["dataset"]["bias_range"][1],
                         args.n_iv_points)
    rng = np.random.default_rng(args.seed)
    I_clean = []
    prev = None
    # CHART-01: C_true lives on `x_true` (256 points), the solver on 301 nodes.
    # A physical-abscissa regrid, said out loud.
    C_true_grid = regrid_signed(
        scaling.x_to_si(np.asarray(sg.grid.x)), x_true, C_true)
    for V in biases:
        s = sg.solve(C_true_grid, float(V), initial_state=prev)
        I_clean.append(s.terminal_current)
        prev = s
    I_clean = np.asarray(I_clean)
    I_noisy = I_clean * (1.0 + args.measurement_noise *
                          rng.standard_normal(len(biases)))
    print(f"Measurements: {len(biases)} biases in [{biases[0]:.2f}, {biases[-1]:.2f}] V")
    print(f"  |I| range = [{np.abs(I_clean).min():.3e}, {np.abs(I_clean).max():.3e}] A/m^2")

    # 4) Run inverse design once per ensemble member
    x_anchor = torch.linspace(domain[0], domain[1], n_anchor)
    icfg = InverseConfig(
        n_iters=args.n_inverse_iters, lr=args.lr, optimizer="adam",
        lambda_TV=args.lambda_TV, lambda_smooth=args.lambda_smooth,
        lambda_solubility=1.0, log_every=10**9, seed=args.seed,
    )
    target_b_t = torch.as_tensor(biases, dtype=torch.float32)
    target_I_t = torch.as_tensor(I_noisy, dtype=torch.float32)

    per_member_C = []
    per_member_pred_I = []
    per_member_loss = []
    for m_idx, fwd in enumerate(ens.members):
        param = FreePointwiseDoping(x_anchor, torch.zeros_like(x_anchor))
        designer = InverseDesigner(fwd, icfg)
        result = designer.design(param, target_b_t, target_I_t)
        per_member_C.append(result.C_recovered_si.detach().cpu().numpy())
        per_member_pred_I.append(result.predicted_currents_si.detach().cpu().numpy())
        per_member_loss.append(result.final_loss)
        print(f"  member {m_idx}: final loss = {result.final_loss:.3e}")

    # 5) Aggregate to posterior over C
    C_stack = np.stack(per_member_C, axis=0)          # (M, n_anchor)
    I_stack = np.stack(per_member_pred_I, axis=0)     # (M, n_biases)
    C_mean = C_stack.mean(axis=0)
    C_lo   = np.quantile(C_stack, 0.05, axis=0)
    C_hi   = np.quantile(C_stack, 0.95, axis=0)
    # Coverage of the true profile by the 90% band (on anchor grid)
    C_true_anchor = np.interp(x_anchor.numpy(), x_true, C_true)
    coverage = float(np.mean((C_true_anchor >= C_lo) &
                              (C_true_anchor <= C_hi)))
    rel_l2 = float(np.linalg.norm(C_mean - C_true_anchor) /
                   max(np.linalg.norm(C_true_anchor), 1e-30))
    # Recover defect parameters from the posterior mean
    baseline = (-args.N_A * (x_anchor.numpy() < args.x_junction)
                + args.N_D * (x_anchor.numpy() >= args.x_junction))
    bump = C_mean - baseline
    recovered_amp = float(bump.max() if abs(bump.max()) > abs(bump.min()) else bump.min())
    recovered_center = float(x_anchor.numpy()[np.argmax(np.abs(bump))])

    print("\n=== Recovery results ===")
    print(f"  relative L2 doping error: {rel_l2:.4f}")
    print(f"  coverage of 90% band:     {coverage:.4f} (target 0.90)")
    print(f"  recovered defect:         amp={recovered_amp:+.2e}, "
          f"center={recovered_center*1e9:.0f} nm")
    print(f"  true defect:              amp={args.defect_amplitude:+.2e}, "
          f"center={args.defect_position*1e9:.0f} nm")

    # 6) Save
    np.savez(out_dir / "result.npz",
              x_anchor=x_anchor.numpy(), C_mean=C_mean, C_lo=C_lo, C_hi=C_hi,
              C_stack=C_stack, x_true=x_true, C_true=C_true,
              biases=biases, I_clean=I_clean, I_noisy=I_noisy,
              I_stack=I_stack)
    metrics = {
        "rel_L2_C":         rel_l2,
        "coverage_90":      coverage,
        "recovered_amp":    recovered_amp,
        "recovered_center": recovered_center,
        "true_amp":         args.defect_amplitude,
        "true_center":      args.defect_position,
        "per_member_loss":  per_member_loss,
        "mean_loss":        float(np.mean(per_member_loss)),
        "M":                ens.M,
    }
    with open(out_dir / "metrics.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(metrics, f, indent=2)

    # 7) Hero figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        apply_style()
        fig, (ax_C, ax_I) = plt.subplots(1, 2, figsize=(9.5, 3.6))

        # Doping panel
        ax_C.plot(x_true * 1e9, C_true, "--", color=PALETTE["red"],
                  label="Ground truth", lw=1.5)
        ax_C.plot(x_anchor.numpy() * 1e9, C_mean,
                  color=PALETTE["blue"], lw=1.6, label="Recovered (mean)")
        ax_C.fill_between(x_anchor.numpy() * 1e9, C_lo, C_hi,
                           color=PALETTE["blue"], alpha=0.25,
                           label="90% credible band")
        ax_C.axvline(args.defect_position * 1e9, color=PALETTE["grey"],
                     lw=0.7, ls=":", label=f"True defect @ {args.defect_position*1e9:.0f} nm")
        ax_C.axhline(0, color="k", lw=0.5)
        ax_C.set_xlabel("x (nm)")
        ax_C.set_ylabel(r"$C(x) = N_D - N_A$  (m$^{-3}$)")
        ax_C.set_title(f"Defect recovery (rel L2 = {rel_l2:.3f}, cov = {coverage:.2f})")
        ax_C.legend(loc="best", fontsize=8)

        # I-V panel
        ax_I.errorbar(biases, np.abs(I_noisy), yerr=args.measurement_noise * np.abs(I_clean),
                      fmt="o", color=PALETTE["red"], mfc="white", ms=4,
                      capsize=2, label="Noisy measurement")
        I_mean = I_stack.mean(axis=0); I_lo = np.quantile(I_stack, 0.05, axis=0)
        I_hi  = np.quantile(I_stack, 0.95, axis=0)
        ax_I.fill_between(biases, np.abs(I_lo), np.abs(I_hi),
                           color=PALETTE["blue"], alpha=0.2,
                           label="PINN posterior")
        ax_I.plot(biases, np.abs(I_mean), color=PALETTE["blue"], lw=1.3)
        ax_I.set_yscale("log")
        ax_I.set_xlabel("Bias (V)")
        ax_I.set_ylabel(r"$|I|$ (A/m$^2$)")
        ax_I.set_title("I-V fit")
        ax_I.legend(loc="best", fontsize=8)

        fig.tight_layout()
        fig.savefig(fig_dir / "defect_recovery_hero.png", dpi=300)
        print(f"\nHero figure -> {fig_dir / 'defect_recovery_hero.png'}")
    except ImportError:
        print("\n(matplotlib unavailable; skipping hero figure)")

    print(f"\nDone -> {out_dir}")


if __name__ == "__main__":
    main()
