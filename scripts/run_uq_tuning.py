#!/usr/bin/env python
"""Give MC-dropout and SWAG a fair hyperparameter search before judging them.

The headline comparison in ``run_uq_benchmark.py`` finds the deep ensemble
better than both on every uncertainty axis. A negative result is only worth
reporting if it is not simply a tuning failure, and there were two concrete
reasons to suspect one:

* SWAG's predictive spread was **0.0085 symlog** -- essentially zero. If the
  SWA phase runs at too small a learning rate the iterates barely move, the
  fitted Gaussian collapses, and SWAG degenerates to its own SWA mean. That
  is a hyperparameter artefact, not a property of SWAG.
* MC-dropout's accuracy was 4x worse than the deterministic model, which is
  what happens when the dropout rate is too high for the network capacity.

So each method gets a grid over the hyperparameters that plausibly drive its
uncertainty, and the *best* configuration of each is what gets compared. The
selection criterion is calibrated NLL on the **calibration split**, never on
the test set -- selecting on test would be exactly the leakage this project
audits for.

Usage
-----
    PYTHONPATH=src python scripts/run_uq_tuning.py [--out DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.bayesian.surrogate_uq import MCDropoutSurrogate, SWAGSurrogate
from bayespinn_inv.bayesian.swag import SWAGConfig, SWAGRecorder
from bayespinn_inv.calibration.metrics import gaussian_nll
from bayespinn_inv.data.splits import ProtocolSpec, build_level_splits, build_sg_labels
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import Grid1D, ScharfetterGummel1D, SGConfig
from bayespinn_inv.surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SymlogTransform,
    train_surrogate,
)
from bayespinn_inv.utils.provenance import RunManifest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_uq_benchmark import Evaluator

SEED = 0
T_SAMPLES = 30


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/uq_tuning")
    ap.add_argument("--epochs", type=int, default=2500)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    epochs = 300 if args.quick else args.epochs
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    spec = ProtocolSpec()
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(spec.domain_si[1])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling, SILICON, SGConfig())
    symlog = SymlogTransform()
    splits = build_level_splits(spec)
    X, Y, integrity = build_sg_labels(sg, scaling, symlog, splits["train"], spec)
    norm = Normalizer.fit(X)
    ev = Evaluator(sg, scaling, symlog, spec, splits)

    def _mk(seed, dropout=0.0):
        return IVSurrogate(IVSurrogateConfig(doping_dim=spec.n_anchor, hidden=128,
                                             n_layers=3, dropout=dropout, seed=seed))

    def selection_score(backend) -> Dict[str, float]:
        """Calibrated NLL on the CALIBRATION split. Never touches test."""
        v = ev.collect(backend, splits["calibration_val"], "step")
        ok = v["sd"] > 1e-12
        if ok.sum() < 3:
            return {"nll": float("inf"), "sigma_median": 0.0,
                    "rel_err_median": float(np.median(v["rel"]))}
        z = (v["y"][ok] - v["mu"][ok]) / v["sd"][ok]
        T = float(np.sqrt(np.mean(z ** 2)))
        return {"nll": gaussian_nll(v["mu"][ok], v["sd"][ok] * T, v["y"][ok]),
                "temperature": T,
                "sigma_median": float(np.median(v["sd"])),
                "rel_err_median": float(np.median(v["rel"]))}

    results: Dict[str, object] = {"label_integrity": integrity, "grids": {}}
    man = RunManifest.create("uq_tuning",
                             config=dict(seed=SEED, epochs=epochs,
                                         T_samples=T_SAMPLES), seed=SEED)

    # ---------------------------------------------------------- MC-dropout
    print("MC-dropout: dropout rate sweep (selected on the calibration split)")
    p_grid = [0.02, 0.05, 0.1] if args.quick else [0.01, 0.02, 0.05, 0.1, 0.2]
    mcd_rows: List[dict] = []
    best_mcd, best_mcd_score = None, float("inf")
    for p in p_grid:
        t0 = time.time()
        m = _mk(0, dropout=p)
        train_surrogate(m, X, Y, norm, epochs=epochs, lr=2e-3)
        b = MCDropoutSurrogate(m, norm, symlog, n_samples=T_SAMPLES, seed=SEED)
        sc = selection_score(b)
        sc.update(dropout_p=p, train_seconds=time.time() - t0)
        mcd_rows.append(sc)
        print(f"  p={p:<5} val NLL {sc['nll']:9.3f}  sigma_med {sc['sigma_median']:.4f}  "
              f"val rel err {sc['rel_err_median']:.2%}")
        if sc["nll"] < best_mcd_score:
            best_mcd_score, best_mcd = sc["nll"], (b, dict(dropout_p=p,
                train_seconds=sc["train_seconds"], n_networks=1,
                params=m.num_parameters(), forward_passes_per_prediction=T_SAMPLES))
    results["grids"]["mc_dropout"] = mcd_rows

    # ---------------------------------------------------------------- SWAG
    print("\nSWAG: SWA learning rate x posterior scale sweep")
    lr_grid = [2e-4, 1e-3] if args.quick else [2e-4, 5e-4, 1e-3, 2e-3]
    scale_grid = [0.5] if args.quick else [0.25, 0.5, 1.0]
    swag_rows: List[dict] = []
    best_swag, best_swag_score = None, float("inf")
    n_snap = 20
    for lr in lr_grid:
        for scale in scale_grid:
            t0 = time.time()
            net = _mk(0)
            burn = int(epochs * 0.75)
            train_surrogate(net, X, Y, norm, epochs=burn, lr=2e-3)
            rec = SWAGRecorder(net, SWAGConfig(max_rank=min(20, n_snap),
                                               T_samples=T_SAMPLES, scale=scale,
                                               seed=SEED))
            per = max(1, (epochs - burn) // n_snap)
            for _ in range(n_snap):
                train_surrogate(net, X, Y, norm, epochs=per, lr=lr)
                rec.collect()
            b = SWAGSurrogate(net, rec, norm, symlog)
            sc = selection_score(b)
            sc.update(swa_lr=lr, scale=scale, train_seconds=time.time() - t0)
            swag_rows.append(sc)
            print(f"  lr={lr:<7g} scale={scale:<5} val NLL {sc['nll']:9.3f}  "
                  f"sigma_med {sc['sigma_median']:.4f}  "
                  f"val rel err {sc['rel_err_median']:.2%}")
            if sc["nll"] < best_swag_score:
                best_swag_score, best_swag = sc["nll"], (b, dict(
                    swa_lr=lr, scale=scale, train_seconds=sc["train_seconds"],
                    n_networks=1, params=net.num_parameters(),
                    forward_passes_per_prediction=T_SAMPLES, snapshots=n_snap))
    results["grids"]["swag"] = swag_rows

    # ------------------------------------------------------ reference ensemble
    print("\nReference deep ensemble (M=5, untuned -- the incumbent)")
    t0 = time.time()
    members = []
    for m in range(5):
        net = _mk(m)
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))
        train_surrogate(net, X[idx], Y[idx], norm, epochs=epochs, lr=2e-3)
        members.append(net)
    ens = SurrogateEnsemble(members, norm, symlog)
    ens_cost = dict(train_seconds=time.time() - t0, n_networks=5,
                    params=members[0].num_parameters() * 5,
                    forward_passes_per_prediction=5)

    # --------------------------------------- final head-to-head on the test set
    print("\nBest-of-each vs the ensemble, on the held-out test sets:")
    final = {}
    for name, (backend, cost) in [("deep_ensemble", (ens, ens_cost)),
                                  ("mc_dropout_tuned", best_mcd),
                                  ("swag_tuned", best_swag)]:
        r = ev.evaluate(name, backend, cost)
        final[name] = r
        u, s = r["uncertainty_utility"], r["scores"]
        print(f"  {name:20s} interp {r['accuracy']['interpolation']['median_rel_err']['point']:6.2%}"
              f"  rho {u['spearman_rho']:+.3f}  NLL_cal {s['nll_calibrated']:8.3f}"
              f"  OOD sigma/err {r['ood']['extrapolation']['sigma_inflation_vs_interp']:5.1f}x/"
              f"{r['ood']['extrapolation']['error_inflation_vs_interp']:.1f}x")
    results["final"] = final
    results["selection"] = {
        "criterion": "calibrated Gaussian NLL on the calibration split",
        "mc_dropout_best": best_mcd[1], "swag_best": best_swag[1],
        "note": "selection never used the test set",
    }

    (out / "uq_tuning.json").write_text(json.dumps(results, indent=2, default=float),
                                        encoding="utf-8")
    man.add_result("final", final)
    man.add_artifact("uq_tuning_json", out / "uq_tuning.json")
    _write_markdown(out, results)
    man.add_artifact("uq_tuning_summary", out / "uq_tuning.md")
    man.write(out)
    print(f"\nWrote {out}/uq_tuning.json and uq_tuning.md")
    return 0


def _write_markdown(out: Path, r: dict) -> None:
    L = ["# Were MC-dropout and SWAG simply mistuned?", "",
         "Each method gets a grid over the hyperparameters that drive its "
         "uncertainty. The winner is selected by calibrated NLL on the "
         "**calibration split** -- never on the test set -- and only then "
         "evaluated against the deep ensemble on the held-out sets.", "",
         "## MC-dropout: dropout-rate grid", "",
         "| dropout p | val NLL | median sigma | val median rel err |",
         "|---:|---:|---:|---:|"]
    for row in r["grids"]["mc_dropout"]:
        L.append(f"| {row['dropout_p']} | {row['nll']:.3f} | "
                 f"{row['sigma_median']:.4f} | {row['rel_err_median']:.2%} |")
    L += ["", "## SWAG: SWA learning rate x posterior scale", "",
          "| SWA lr | scale | val NLL | median sigma | val median rel err |",
          "|---:|---:|---:|---:|---:|"]
    for row in r["grids"]["swag"]:
        L.append(f"| {row['swa_lr']:g} | {row['scale']} | {row['nll']:.3f} | "
                 f"{row['sigma_median']:.4f} | {row['rel_err_median']:.2%} |")

    L += ["", "## Best of each, against the untuned ensemble", "",
          "| Method | Interp rel err | rho(sigma,\\|err\\|) | NLL calibrated | "
          "CRPS | sigma inflation (extrap) | error inflation (extrap) | Train (s) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in r["final"].items():
        a = v["accuracy"]["interpolation"]["median_rel_err"]["point"]
        u, s, o, c = (v["uncertainty_utility"], v["scores"],
                      v["ood"]["extrapolation"], v["cost"])
        L.append(f"| `{k}` | {a:.2%} | {u['spearman_rho']:+.3f} | "
                 f"{s['nll_calibrated']:.3f} | {s['crps_empirical']:.4f} | "
                 f"{o['sigma_inflation_vs_interp']:.1f}x | "
                 f"{o['error_inflation_vs_interp']:.1f}x | {c['train_seconds']:.1f} |")
    L += ["", f"Selected: MC-dropout `{r['selection']['mc_dropout_best']}`, "
              f"SWAG `{r['selection']['swag_best']}`.", ""]
    (out / "uq_tuning.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
