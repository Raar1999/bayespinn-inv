#!/usr/bin/env python
"""
Run active learning ablation: random vs max-std vs UCB on a single
synthetic ground-truth doping profile.

Outputs a CSV per strategy with per-round metrics plus a combined
JSON summary suitable for the convergence plot.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
import yaml

# Reuse the ensemble-loader from the inverse-design launcher
from inverse_design import _load_ensemble

from bayespinn_inv.active_learning.loop import (
    ActiveLearningConfig,
    active_learning_loop,
)
from bayespinn_inv.inverse.inverse_design import InverseConfig
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)


def build_oracle(scaling, n_anchor=301, domain=(0., 1e-6)):
    """Build an SG solver that acts as the lab oracle."""
    L_scaled = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
    grid = Grid1D.uniform(L_scaled, n_anchor)
    return ScharfetterGummel1D(grid, scaling, scaling.material, SGConfig())


def build_target_doping(cfg, n_points=128, domain=(0., 1e-6)):
    """Construct the ground-truth doping profile from config."""
    from bayespinn_inv.data.datasets import (
        defect_profile,
        graded_profile,
        ldd_profile,
        step_profile,
    )
    x = np.linspace(domain[0], domain[1], n_points)
    t = cfg["target"]
    family = t["family"]
    if family == "step":
        C = step_profile(x, t["N_A"], t["N_D"], t["x_junction"])
    elif family == "graded":
        C = graded_profile(x, t["N_A"], t["N_D"],
                           t["x_junction"], t["L_grade"])
    elif family == "ldd":
        C = ldd_profile(x, t["N_A_body"], t["N_D_ldd"], t["N_D_sd"],
                         t["x_ldd_start"], t["x_ldd_end"])
    elif family == "defect":
        C = defect_profile(x, t["N_A"], t["N_D"], t["x_junction"],
                            t["defect_amplitude"], t["defect_center"],
                            t["defect_width"])
    else:
        raise ValueError(f"Unknown target family: {family!r}")
    return x, C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/al_base.yaml")
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    ens = _load_ensemble(Path(cfg["forward_ckpt"]) / "manifest.json", cfg)
    scaling = ens.scaling

    domain = tuple(ens.members[0].cfg.domain_si)
    x_true, C_true = build_target_doping(cfg, n_points=128, domain=domain)
    true_doping_t = torch.as_tensor(C_true, dtype=torch.float32)
    oracle = build_oracle(scaling, n_anchor=301, domain=domain)

    cb = cfg["active_learning"]["candidate_biases"]
    cands = np.linspace(cb["start"], cb["stop"], int(cb["num"]))

    all_results = {}
    for strategy in cfg["strategies"]:
        al_cfg = ActiveLearningConfig(
            n_rounds=cfg["active_learning"]["n_rounds"],
            candidate_biases=cands,
            initial_biases=tuple(cfg["active_learning"]["initial_biases"]),
            strategy=strategy,
            inverse_cfg=InverseConfig(
                lr=cfg["inverse"].get("lr", 5e-3),
                lambda_TV=cfg["inverse"].get("lambda_TV", 1.0),
                lambda_smooth=cfg["inverse"].get("lambda_smooth", 1e-6),
            ),
            n_inverse_iters=cfg["active_learning"]["n_inverse_iters"],
            measurement_noise_rel=cfg["active_learning"]["measurement_noise_rel"],
            seed=cfg["seed"],
        )
        print(f"\n=== Strategy: {strategy} ===")
        initial = torch.zeros_like(true_doping_t)
        res = active_learning_loop(
            uq_model=ens, oracle=oracle,
            true_doping_si=true_doping_t,
            forward_for_inverse=ens.members[0],
            initial_doping_si=initial, cfg=al_cfg,
        )
        # Serialize
        sdir = out_dir / strategy
        sdir.mkdir(parents=True, exist_ok=True)
        np.savez(sdir / "trajectory.npz",
                  biases_acquired=res["biases_acquired"],
                  measurements=res["measurements"],
                  final_doping=res["final_doping"],
                  true_doping=C_true, true_x=x_true)
        with open(sdir / "log.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump([asdict(l) for l in res["log"]], f, indent=2)
        all_results[strategy] = [asdict(l) for l in res["log"]]
        print(f"  final relative L2 error: {res['log'][-1].doping_error_relative:.4f}")

    with open(out_dir / "summary.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(all_results, f, indent=2)
    with open(out_dir / "config_used.yaml", "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(cfg, f)
    print(f"\nAll strategies complete. Outputs -> {out_dir}/")


if __name__ == "__main__":
    main()
