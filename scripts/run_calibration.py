#!/usr/bin/env python
"""Calibration sweep across DeepEnsemble / MC-Dropout / SWAG.

For each available UQ method:
  1. Run forward inference on a held-out test set of (profile, bias) pairs
  2. Use the SG oracle as ground truth
  3. Compute ECE, MCE, CRPS, NLL, sharpness
  4. Apply temperature-scaling and isotonic recalibration on a val split
  5. Recompute metrics on the test split
  6. Plot reliability diagrams before and after recalibration

Output structure::

    outputs/calibration/
      summary.json
      figures/
        reliability_<method>_uncal.png
        reliability_<method>_temperature.png
        reliability_<method>_isotonic.png

Usage::

    python scripts/run_calibration.py \\
        --ensemble outputs/ensemble/manifest.json \\
        --mc_dropout outputs/mc_dropout/manifest.json \\
        --swag      outputs/swag/recorder.pt \\
        --n_val_profiles 30 --n_test_profiles 50 \\
        --out outputs/calibration/

Any of ``--ensemble``, ``--mc_dropout``, ``--swag`` may be omitted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.bayesian.ensembles import EnsemblePrediction
from bayespinn_inv.bayesian.mc_dropout import MCDropoutPINN
from bayespinn_inv.bayesian.swag import SWAG, SWAGConfig, SWAGRecorder
from bayespinn_inv.calibration.metrics import (
    fit_isotonic_recalibrator,
    fit_temperature_regression,
    report_calibration,
)
from bayespinn_inv.data.datasets import sample_doping
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.surrogate import load_forward_ensemble as load_ensemble


def _collect_predictions(uq_model, scaling, sg, sg_grid, profiles, biases):
    """Run uq_model on every (profile, bias) pair; collect samples + truth."""
    M = uq_model.M
    n_pts = len(profiles) * len(biases)
    samples_all = np.zeros((M, n_pts))
    truth_all   = np.zeros(n_pts)
    idx = 0
    for prof in profiles:
        dop_t = torch.as_tensor(prof.doping_si, dtype=torch.float32)
        _, pred = uq_model.iv_curve(dop_t, list(biases))
        # ensure ndarray
        samples = np.asarray(pred.samples)
        if samples.shape != (M, len(biases)):
            samples = samples.reshape(M, len(biases))
        # SG oracle for this profile
        prev = None
        for b_idx, V in enumerate(biases):
            s = sg.solve(prof.doping_si, float(V), initial_state=prev)
            truth_all[idx] = s.terminal_current
            samples_all[:, idx] = samples[:, b_idx]
            prev = s
            idx += 1
    return samples_all, truth_all


def _predict_to_ensemble_prediction(samples: np.ndarray) -> EnsemblePrediction:
    return EnsemblePrediction(
        mean=samples.mean(axis=0),
        std=samples.std(axis=0),
        samples=samples,
        quantile_lo=np.quantile(samples, 0.05, axis=0),
        quantile_hi=np.quantile(samples, 0.95, axis=0),
    )


def _apply_temperature(pred: EnsemblePrediction, T: float) -> EnsemblePrediction:
    """Scale predictive std by T (samples shifted symmetrically about mean)."""
    centered = pred.samples - pred.mean[None, :]
    new_samples = pred.mean[None, :] + T * centered
    return _predict_to_ensemble_prediction(new_samples)


def _save_reliability_plot(report, path: Path, title: str):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="Ideal")
    ax.plot(report.predicted_q, report.empirical_q, "o-",
             color="#0173B2", ms=4, label="Observed")
    ax.fill_between(report.predicted_q, report.predicted_q,
                      report.empirical_q, color="#949494", alpha=0.15)
    ax.text(0.05, 0.92, f"ECE = {report.ece:.3f}",
             transform=ax.transAxes, fontsize=9,
             bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))
    ax.set_xlabel("Predicted quantile")
    ax.set_ylabel("Empirical quantile")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_title(title); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(path, dpi=200)
    import matplotlib.pyplot as plt
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensemble",   help="Manifest of DeepEnsemble")
    ap.add_argument("--mc_dropout", help="Manifest of a single-network "
                                          "PINN trained with dropout>0")
    ap.add_argument("--mc_T", type=int, default=50,
                    help="Number of MC-Dropout test-time samples")
    ap.add_argument("--swag",       help="Path to a saved SWAGRecorder")
    ap.add_argument("--swag_T", type=int, default=30)
    ap.add_argument("--n_val_profiles", type=int, default=20)
    ap.add_argument("--n_test_profiles", type=int, default=40)
    ap.add_argument("--bias_grid", default="0.0,0.5,8")
    ap.add_argument("--target_family", default="step")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    if not (args.ensemble or args.mc_dropout or args.swag):
        raise SystemExit("Must provide at least one UQ method "
                          "(--ensemble / --mc_dropout / --swag)")

    bs, be, bn = args.bias_grid.split(",")
    biases = np.linspace(float(bs), float(be), int(bn))
    rng = np.random.default_rng(args.seed)

    # Use the first available manifest to set up scaling + domain
    primary_manifest_path = args.ensemble or args.mc_dropout
    primary_ens, primary_manifest = load_ensemble(Path(primary_manifest_path))
    scaling = primary_ens.scaling
    material = primary_ens.material
    domain = tuple(primary_manifest["config"]["domain_si"])

    L_s = float(scaling.x_to_scaled(torch.tensor(domain[1] - domain[0])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 301), scaling, material, SGConfig())

    # Restrict target doping to the forward model's validated range when it is
    # a surrogate (it extrapolates poorly outside, and SG can go singular at
    # very high doping). Interior of the [5e20, 5e22] training range.
    dop_range = (6e20, 4e22) if primary_manifest.get("type") == "surrogate" else None

    val_profiles = [sample_doping(args.target_family, n_points=128,
                                     domain_si=domain, rng=rng,
                                     doping_range=dop_range)
                    for _ in range(args.n_val_profiles)]
    test_profiles = [sample_doping(args.target_family, n_points=128,
                                       domain_si=domain, rng=rng,
                                       doping_range=dop_range)
                     for _ in range(args.n_test_profiles)]

    # Build the list of UQ methods to evaluate
    methods: Dict[str, object] = {}
    if args.ensemble:
        methods["deep_ensemble"] = primary_ens
    if args.mc_dropout:
        # Load a single-member "ensemble" then wrap in MC-Dropout
        mc_ens, _ = load_ensemble(Path(args.mc_dropout))
        methods["mc_dropout"] = MCDropoutPINN(mc_ens.members[0], T=args.mc_T,
                                                seed=args.seed)
    if args.swag:
        # Build SWAG: need a recorder + a ForwardPINN
        recorder_state = torch.load(args.swag, map_location="cpu",
                                      weights_only=False)
        if isinstance(recorder_state, SWAGRecorder):
            recorder = recorder_state
            # We need a ForwardPINN compatible with the saved recorder.
            # Use member 0 of the ensemble if provided, else error out.
            if args.ensemble:
                swag_fwd = primary_ens.members[0]
            else:
                raise SystemExit(
                    "SWAG requires --ensemble to provide a network to load into; "
                    "see docs/architecture.md for the standalone-SWAG layout."
                )
            methods["swag"] = SWAG(swag_fwd, recorder,
                                     SWAGConfig(T_samples=args.swag_T))
        else:
            raise SystemExit(f"Unrecognized SWAG file format: {args.swag}")

    # Current spans ~13 orders of magnitude; calibration metrics other than
    # ECE (CRPS, NLL, sharpness) overflow / are meaningless in linear current
    # units. For the surrogate forward model, compute calibration in symlog
    # space, where the predictive distribution is well-conditioned. ECE is
    # rank-based and essentially unaffected; CRPS/NLL/sharpness become finite
    # and interpretable (in symlog / decade units).
    use_symlog_metrics = (primary_manifest.get("type") == "surrogate")
    _I0 = 1e-6
    def _to_metric_space(arr):
        if not use_symlog_metrics:
            return arr
        a = np.asarray(arr, dtype=np.float64)
        return np.sign(a) * np.log10(1.0 + np.abs(a) / _I0)

    summary: Dict[str, Dict] = {}
    for name, model in methods.items():
        print(f"\n=== {name} ===")
        # Validation set: collect predictions, fit recalibrators
        v_samples, v_truth = _collect_predictions(
            model, scaling, sg, None, val_profiles, biases)
        v_samples, v_truth = _to_metric_space(v_samples), _to_metric_space(v_truth)
        v_pred = _predict_to_ensemble_prediction(v_samples)
        # Test set
        t_samples, t_truth = _collect_predictions(
            model, scaling, sg, None, test_profiles, biases)
        t_samples, t_truth = _to_metric_space(t_samples), _to_metric_space(t_truth)
        t_pred = _predict_to_ensemble_prediction(t_samples)

        # Uncalibrated
        rep_uncal = report_calibration(t_pred, t_truth, n_bins=10)
        print("  uncalibrated:", rep_uncal.summary().strip().replace("\n", " | "))

        # Temperature scaling fit on val
        T = fit_temperature_regression(v_pred.mean, v_pred.std, v_truth)
        t_pred_temp = _apply_temperature(t_pred, T)
        rep_temp = report_calibration(t_pred_temp, t_truth, n_bins=10)
        print(f"  T fit on val = {T:.3f}")
        print("  temperature: ", rep_temp.summary().strip().replace("\n", " | "))

        # Isotonic recalibration of the CDF (optional / softer)
        try:
            fit_isotonic_recalibrator(v_samples, v_truth)
            iso_status = "fit"
        except Exception as e:
            iso_status = f"skipped ({e})"
        print(f"  isotonic: {iso_status}")

        # Save reliability plots
        _save_reliability_plot(rep_uncal,
            fig_dir / f"reliability_{name}_uncal.png",
            f"{name} (uncalibrated)")
        _save_reliability_plot(rep_temp,
            fig_dir / f"reliability_{name}_temperature.png",
            f"{name} (T={T:.2f})")

        summary[name] = {
            "uncalibrated": {
                "ECE": rep_uncal.ece, "MCE": rep_uncal.mce,
                "CRPS": rep_uncal.crps, "NLL": rep_uncal.nll,
                "sharpness": rep_uncal.sharpness,
            },
            "temperature_scaled": {
                "T": T,
                "ECE": rep_temp.ece, "MCE": rep_temp.mce,
                "CRPS": rep_temp.crps, "NLL": rep_temp.nll,
                "sharpness": rep_temp.sharpness,
            },
            "n_val": len(v_truth), "n_test": len(t_truth),
            "M_or_T": model.M,
        }

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=float)
    print(f"\nDone -> {out_dir}/summary.json")

    # Pretty headline table
    print(f"\n{'method':16s}  {'ECE_uncal':>10s}  {'ECE_cal':>10s}  "
          f"{'CRPS_cal':>10s}  {'NLL_cal':>10s}")
    for name, s in summary.items():
        print(f"{name:16s}  "
              f"{s['uncalibrated']['ECE']:10.4f}  "
              f"{s['temperature_scaled']['ECE']:10.4f}  "
              f"{s['temperature_scaled']['CRPS']:10.4e}  "
              f"{s['temperature_scaled']['NLL']:10.4f}")


if __name__ == "__main__":
    main()
