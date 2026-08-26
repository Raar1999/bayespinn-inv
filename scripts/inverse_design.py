#!/usr/bin/env python
"""
Run inverse design against a synthetic or measured target I-V curve.

Workflow
--------
1. Load a trained ensemble (manifest.json + member checkpoints).
2. Generate or load target I-V data.
3. Optimize a doping parameterization via input-space autodiff.
4. Save: recovered profile, predicted vs target I-V, history, diagnostics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
import yaml

from bayespinn_inv.bayesian.ensembles import DeepEnsemble
from bayespinn_inv.data.datasets import sample_doping
from bayespinn_inv.inverse.charts import regrid_signed
from bayespinn_inv.inverse.inverse_design import (
    FreePointwiseDoping,
    GradedJunctionDoping,
    InverseConfig,
    InverseDesigner,
    StepJunctionDoping,
)
from bayespinn_inv.physics.constants import GAAS, SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.forward_pinn import ForwardPINN, ForwardPINNConfig
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)


def _material(name: str):
    return {"Si": SILICON, "GaAs": GAAS, "Silicon": SILICON}[name]


def _load_ensemble(manifest_path: Path, cfg: dict) -> DeepEnsemble:
    """Reconstruct a DeepEnsemble from a training-run manifest."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    train_cfg = manifest["config"]
    mat = _material(train_cfg["material"]["name"])
    scaling = Scaling.for_material(mat, T=train_cfg["material"]["T"])
    L_scaled = float(scaling.x_to_scaled(
        torch.tensor(train_cfg["domain_si"][1] - train_cfg["domain_si"][0])))
    V_a_max_s = float(train_cfg["dataset"]["bias_range"][1]) / scaling.V_T

    ens = DeepEnsemble(scaling, mat)
    for seed, ckpt_path in zip(manifest["member_seeds"],
                                manifest["checkpoints"]):
        net_cfg = PINNConfig(
            in_dim=train_cfg["network"]["in_dim"],
            hidden_dim=train_cfg["network"]["hidden_dim"],
            num_blocks=train_cfg["network"]["num_blocks"],
            fourier_features=train_cfg["network"]["fourier_features"],
            fourier_sigma=train_cfg["network"]["fourier_sigma"],
            dropout=train_cfg["network"]["dropout"],
            doping_dim=train_cfg["network"]["doping_dim"],
            output_dim=train_cfg["network"]["output_dim"],
            seed=seed,
            x_scaled_extent=L_scaled,
            V_a_scaled_extent=V_a_max_s,
        )
        net = SemiconductorPINN(net_cfg)
        ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        net.load_state_dict(ck["model_state"])
        net.eval()
        fwd_cfg = ForwardPINNConfig(
            device=cfg.get("device", "cpu"),
            n_query=401, n_anchor=train_cfg["network"]["doping_dim"],
            domain_si=tuple(train_cfg["domain_si"]),
        )
        ens.add_member(ForwardPINN(net, scaling, mat, fwd_cfg))
    return ens


def _make_target(cfg: dict, scaling: Scaling) -> Dict[str, Any]:
    """Generate or load the target I-V curve."""
    t = cfg["target"]
    domain = tuple(cfg.get("domain_si", (0.0, 1e-6)))
    if t["family"] == "synthetic":
        # Draw a profile from the requested family and run the SG oracle.
        rng = np.random.default_rng(cfg["seed"])
        sample = sample_doping(t["source_family"], n_points=128,
                                domain_si=domain, rng=rng)
        # SG forward sweep
        L_scaled = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
        grid = Grid1D.uniform(L_scaled, 301)
        sg = ScharfetterGummel1D(grid, scaling, scaling.material, SGConfig())
        bg = t["bias_grid"]
        biases = np.linspace(bg["start"], bg["stop"], int(bg["num"]))
        prev = None
        currents = []
        for V in biases:
            s = sg.solve(regrid_signed(scaling.x_to_si(
                torch.as_tensor(grid.x)).numpy(),
                                     sample.x_si, sample.doping_si),
                          float(V), initial_state=prev)
            currents.append(0.5 * (s.Jn.mean() + s.Jp.mean()))
            prev = s
        noise = t.get("noise_std_rel", 0.0)
        if noise > 0:
            rng2 = np.random.default_rng(cfg["seed"] + 1)
            currents = np.asarray(currents) * (1 + noise * rng2.standard_normal(len(currents)))
        return {
            "biases": np.asarray(biases, dtype=float),
            "currents": np.asarray(currents, dtype=float),
            "true_doping_si": sample.doping_si,
            "true_x_si": sample.x_si,
            "true_params": sample.params,
        }
    else:
        # Load from CSV
        import pandas as pd
        df = pd.read_csv(t["csv_path"])
        return {
            "biases": df["bias_V"].to_numpy(),
            "currents": df["current_A_per_m2"].to_numpy(),
            "true_doping_si": None, "true_x_si": None, "true_params": None,
        }


def _make_parameterization(cfg: dict, domain_si, x_anchor_si,
                             initial_C_si=None):
    p = cfg["parameterization"]
    x_t = torch.as_tensor(x_anchor_si, dtype=torch.float32)
    if p["kind"] == "free_pointwise":
        if initial_C_si is None:
            initial_C_si = torch.zeros_like(x_t)
        else:
            initial_C_si = torch.as_tensor(initial_C_si, dtype=torch.float32)
        return FreePointwiseDoping(x_t, initial_C_si)
    elif p["kind"] == "step_junction":
        return StepJunctionDoping(x_t)
    elif p["kind"] == "graded_junction":
        return GradedJunctionDoping(x_t)
    else:
        raise ValueError(f"Unknown parameterization: {p['kind']!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/inverse_base.yaml")
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load the ensemble
    manifest_dir = Path(cfg["forward_ckpt"])
    manifest_path = manifest_dir / "manifest.json"
    ens = _load_ensemble(manifest_path, cfg)
    print(f"Loaded ensemble with M={ens.M} members from {manifest_path}")

    # 2) Build/load target
    scaling = ens.scaling
    target = _make_target(cfg, scaling)
    print(f"Target: {len(target['biases'])} bias points, |I|_max={np.abs(target['currents']).max():.3e}")

    # 3) Parameterization + designer
    p_cfg = cfg["parameterization"]
    x_anchor = np.linspace(*cfg.get("domain_si", (0.0, 1e-6)), p_cfg["n_points"])
    param = _make_parameterization(cfg, (x_anchor[0], x_anchor[-1]), x_anchor)
    icfg = InverseConfig(
        n_iters=cfg["inverse"]["n_iters"],
        lr=cfg["inverse"]["lr"],
        optimizer=cfg["inverse"]["optimizer"],
        lambda_TV=cfg["inverse"]["lambda_TV"],
        lambda_smooth=cfg["inverse"]["lambda_smooth"],
        lambda_solubility=cfg["inverse"]["lambda_solubility"],
        C_max_si=cfg["inverse"]["C_max_si"],
        grad_clip=cfg["inverse"]["grad_clip"],
        log_every=cfg["inverse"]["log_every"],
        seed=cfg["seed"],
    )
    # Use mean ensemble member for inverse design optimization.
    # For per-member uncertainty propagation, loop over members instead.
    designer = InverseDesigner(ens.members[0], icfg)
    target_b = torch.as_tensor(target["biases"], dtype=torch.float32)
    target_I = torch.as_tensor(target["currents"], dtype=torch.float32)
    result = designer.design(param, target_b, target_I)

    # 4) Save
    np.savez(out_dir / "result.npz",
              x_si=x_anchor,
              C_recovered_si=result.C_recovered_si.detach().cpu().numpy(),
              target_biases=result.target_biases.detach().cpu().numpy(),
              target_currents=result.target_currents_si.detach().cpu().numpy(),
              predicted_currents=result.predicted_currents_si.detach().cpu().numpy(),
              true_doping_si=target["true_doping_si"]
                if target["true_doping_si"] is not None else np.array([]),
              true_x_si=target["true_x_si"]
                if target["true_x_si"] is not None else np.array([]))
    with open(out_dir / "history.json", "w", encoding="utf-8") as f:
        json.dump(result.history, f, indent=2)
    with open(out_dir / "config_used.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    print(f"Final loss: {result.final_loss:.3e}")
    print(f"Outputs -> {out_dir}/")


if __name__ == "__main__":
    main()
