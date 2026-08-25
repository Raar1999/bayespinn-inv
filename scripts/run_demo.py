#!/usr/bin/env python
"""End-to-end demonstration of the BayesPINN-Inv pipeline.

Runs in five stages:

  1. Train a 3-member PINN ensemble on a synthetic doping dataset.
  2. Benchmark trained PINN against the SG oracle (pointwise + I-V).
  3. Inverse design: recover a held-out doping profile from synthetic I-V.
  4. Active learning ablation on a defect-recovery task.
  5. Generate all publication figures.

Outputs go to ``outputs/demo/``. The script is designed to run on CPU
in roughly 15-30 minutes (depending on the requested epoch count below).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.active_learning.loop import (
    ActiveLearningConfig,
    active_learning_loop,
)
from bayespinn_inv.bayesian.ensembles import DeepEnsemble
from bayespinn_inv.benchmarks.sg_vs_pinn import (
    compare_solvers,
)
from bayespinn_inv.calibration.metrics import (
    fit_temperature_regression,
    report_calibration,
)
from bayespinn_inv.data.datasets import (
    build_dataset,
    defect_profile,
)
from bayespinn_inv.inverse.inverse_design import (
    FreePointwiseDoping,
    InverseConfig,
    InverseDesigner,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.forward_pinn import ForwardPINN, ForwardPINNConfig
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.training.trainer import PINNTrainer, TrainConfig
from bayespinn_inv.visualization.plots import (
    plot_active_learning_convergence,
    plot_device_state,
    plot_doping_recovery,
    plot_iv_with_uncertainty,
    plot_reliability_diagram,
    plot_training_history,
)

# ---------------------------------------------------------------------------
# Config knobs
# ---------------------------------------------------------------------------

N_EPOCHS = 5_000             # training epochs per member
N_ENSEMBLE = 3               # M for DeepEnsemble
DOMAIN = (0.0, 1e-6)         # 1 um device
HIDDEN = 48
N_BLOCKS = 3
DOPING_DIM = 16
BATCH_SIZE = 192
LR = 1.5e-3
CURRICULUM = 1_000
BIAS_MAX = 0.4
OUT_DIR = Path(__file__).parent.parent / "outputs" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("BayesPINN-Inv: end-to-end demonstration")
print("=" * 70)
print(f"Output directory:  {OUT_DIR}")
print(f"Ensemble M:        {N_ENSEMBLE}")
print(f"Epochs/member:     {N_EPOCHS}")
print(f"Architecture:      hidden={HIDDEN}, blocks={N_BLOCKS}, doping_dim={DOPING_DIM}")
print()

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

torch.manual_seed(0)
np.random.seed(0)
scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
V_a_scaled = BIAS_MAX / scaling.V_T

print(scaling.summary())
print()

# ---------------------------------------------------------------------------
# Stage 1: Train ensemble
# ---------------------------------------------------------------------------

print("=" * 70)
print(f"Stage 1: training {N_ENSEMBLE}-member ensemble")
print("=" * 70)

# Build training dataset (shared across members so the comparison is fair)
examples, samples = build_dataset(
    n_per_family={"step": 6, "graded": 2},
    n_points=96, domain_si=DOMAIN,
    scaling=scaling, n_anchor=DOPING_DIM, seed=0,
    bias_range=(0.0, BIAS_MAX),
)
print(f"Dataset: {len(examples)} profiles, families = "
      f"{ {s.family for s in samples} }")

ensemble = DeepEnsemble(scaling, SILICON)
all_histories = []
training_times = []
for member_idx in range(N_ENSEMBLE):
    seed = member_idx
    print(f"\n--- Member {member_idx+1}/{N_ENSEMBLE} (seed={seed}) ---")
    cfg_net = PINNConfig(
        in_dim=2, hidden_dim=HIDDEN, num_blocks=N_BLOCKS,
        fourier_features=24, fourier_sigma=2.0,
        doping_dim=DOPING_DIM, seed=seed,
        x_scaled_extent=L_scaled, V_a_scaled_extent=V_a_scaled,
    )
    net = SemiconductorPINN(cfg_net)
    if member_idx == 0:
        print(f"  network params: {net.num_parameters():,}")
    member_dir = OUT_DIR / f"member_{member_idx:03d}"
    final_ckpt = member_dir / "ckpt_final.pt"
    if final_ckpt.exists():
        print(f"  found existing checkpoint at {final_ckpt}; loading")
        ck = torch.load(final_ckpt, map_location="cpu", weights_only=False)
        net.load_state_dict(ck["model_state"])
        hist = ck.get("history", [{"loss_total": float("nan")}])
        training_times.append(0.0)
        print(f"  loaded checkpoint (final loss in history = "
              f"{hist[-1]['loss_total']:.3e})")
    else:
        tcfg = TrainConfig(
            lr=LR, n_epochs=N_EPOCHS, batch_size=BATCH_SIZE,
            curriculum_epochs=CURRICULUM, bias_max=BIAS_MAX,
            use_ntk_weights=True, adaptive_weight_every=250,
            ntk_alpha=0.9, log_every=1000, ckpt_every=N_EPOCHS - 1,
            seed=seed, domain_si=DOMAIN,
            out_dir=str(member_dir),
        )
        t0 = time.time()
        trainer = PINNTrainer(net, scaling, SILICON, examples, tcfg)
        hist = trainer.train()
        dt = time.time() - t0
        training_times.append(dt)
        print(f"  trained in {dt:.1f}s ({N_EPOCHS/dt:.1f} ep/s); "
              f"final loss = {hist[-1]['loss_total']:.3e}")
    all_histories.append(hist)
    # Wrap into ForwardPINN and add to ensemble
    fcfg = ForwardPINNConfig(device="cpu", n_query=201, n_anchor=DOPING_DIM,
                              domain_si=DOMAIN)
    fwd = ForwardPINN(net, scaling, SILICON, fcfg)
    ensemble.add_member(fwd)

total_train = sum(training_times)
print(f"\nTotal training time: {total_train:.1f}s "
      f"({total_train/N_ENSEMBLE:.1f}s/member avg)")

# Training history plot
fig = plot_training_history(all_histories[0], title="Training history (member 0)")
fig.savefig(FIG_DIR / "01_training_history.png")
print("  -> figures/01_training_history.png")

# ---------------------------------------------------------------------------
# Stage 2: Benchmark vs SG
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("Stage 2: SG vs PINN benchmark")
print("=" * 70)

# Build held-out test profiles
test_doping_list = []
test_doping_list.append(("test_step_1e22",
                          np.where(np.linspace(*DOMAIN, 128) < 5e-7, -1e22, 1e22)))
test_doping_list.append(("test_step_5e22",
                          np.where(np.linspace(*DOMAIN, 128) < 5e-7, -5e22, 5e22)))

biases = np.linspace(0.0, BIAS_MAX, 7)
benchmark_results = {}
L_scaled_grid = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1])))
sg_grid = Grid1D.uniform(L_scaled_grid, 301)
sg_solver = ScharfetterGummel1D(sg_grid, scaling, SILICON, SGConfig())

for name, dop in test_doping_list:
    print(f"\nProfile: {name}")
    dop_t = torch.as_tensor(dop, dtype=torch.float32)
    res = compare_solvers(sg_solver, ensemble.members[0],
                           dop_t, biases, warmup=1)
    benchmark_results[name] = {
        "biases": res.biases.tolist(),
        "phi_rms_error_V": res.phi_rms_error.tolist(),
        "phi_max_error_V": res.phi_max_error.tolist(),
        "n_log_rms_error": res.n_log_rms_error.tolist(),
        "p_log_rms_error": res.p_log_rms_error.tolist(),
        "I_relative_error": res.I_relative_error.tolist(),
        "time_per_solve_sg":   res.time_per_solve_sg,
        "time_per_solve_pinn": res.time_per_solve_pinn,
    }
    # Print summary
    mid = len(biases) // 2
    print(f"  V_a=0.0:  phi_rms={res.phi_rms_error[0]:.3e} V,  "
          f"|dI|/I={res.I_relative_error[0]:.3e}")
    print(f"  V_a={biases[mid]:.2f}:  phi_rms={res.phi_rms_error[mid]:.3e} V,  "
          f"|dI|/I={res.I_relative_error[mid]:.3e}")
    print(f"  V_a={biases[-1]:.2f}:  phi_rms={res.phi_rms_error[-1]:.3e} V,  "
          f"|dI|/I={res.I_relative_error[-1]:.3e}")
    print(f"  time_per_solve: SG={res.time_per_solve_sg*1e3:.1f} ms, "
          f"PINN={res.time_per_solve_pinn*1e3:.1f} ms")

with open(OUT_DIR / "benchmark.json", "w", encoding="utf-8") as f:
    json.dump(benchmark_results, f, indent=2)

# Device-state plot for one test bias
test_dop = test_doping_list[0][1]
test_dop_t = torch.as_tensor(test_dop, dtype=torch.float32)
sg_state = sg_solver.solve(np.interp(scaling.x_to_si(
    torch.as_tensor(sg_grid.x)).numpy(),
    np.linspace(*DOMAIN, 128), test_dop), 0.3)
pinn_state = ensemble.members[0].solve(test_dop_t, 0.3)
fig = plot_device_state(sg_state, title="SG (oracle), test_step_1e22, V=0.3V")
fig.savefig(FIG_DIR / "02_sg_state.png")
fig = plot_device_state(pinn_state, title="Trained PINN, test_step_1e22, V=0.3V")
fig.savefig(FIG_DIR / "02_pinn_state.png")
print("\nField-comparison plots -> figures/02_sg_state.png, 02_pinn_state.png")

# I-V uncertainty plot
target_biases_np = np.linspace(0.0, BIAS_MAX, 13)
mean_t, pred = ensemble.iv_curve(test_dop_t, target_biases_np.tolist())
# Ground truth from SG
sg_biases = []
sg_currents = []
prev = None
for V in target_biases_np:
    s = sg_solver.solve(np.interp(scaling.x_to_si(
        torch.as_tensor(sg_grid.x)).numpy(),
        np.linspace(*DOMAIN, 128), test_dop),
        float(V), initial_state=prev)
    sg_biases.append(V); sg_currents.append(s.terminal_current)
    prev = s
fig = plot_iv_with_uncertainty(
    target_biases_np, pred.mean, pred.quantile_lo, pred.quantile_hi,
    ground_truth=np.asarray(sg_currents), title="Ensemble I-V vs SG (test profile)",
    log_y=True,
)
fig.savefig(FIG_DIR / "03_iv_uncertainty.png")
print("I-V plot -> figures/03_iv_uncertainty.png")

# ---------------------------------------------------------------------------
# Stage 3: Inverse design
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("Stage 3: Inverse design")
print("=" * 70)

# Use the same test profile as the unknown "true" doping.
true_doping_si = test_dop_t.clone()
true_x_si = np.linspace(*DOMAIN, 128)

# Synthetic target I-V from the SG oracle
target_biases = torch.linspace(0.05, BIAS_MAX, 7)
target_currents = []
prev = None
sg_dop_on_grid = np.interp(scaling.x_to_si(
    torch.as_tensor(sg_grid.x)).numpy(), true_x_si,
                            true_doping_si.numpy())
for V in target_biases:
    s = sg_solver.solve(sg_dop_on_grid, float(V), initial_state=prev)
    target_currents.append(s.terminal_current)
    prev = s
target_currents = torch.as_tensor(target_currents, dtype=torch.float32)
print(f"Target I-V: {len(target_biases)} points, "
      f"|I|_max = {target_currents.abs().max().item():.3e} A/m^2")

# Inverse: free pointwise on a 64-point grid initialized from a "wrong" guess
inv_x = torch.linspace(*DOMAIN, 64)
# Initial guess: opposite-signed weak junction (intentionally wrong)
init_C = torch.where(inv_x < 5e-7,
                      torch.tensor(1e21), torch.tensor(-1e21))
param = FreePointwiseDoping(inv_x, init_C)
print("Inverse design starting from wrong-sign N_A=N_D=1e21 m^-3 guess")

icfg = InverseConfig(
    n_iters=200, lr=5e-3, optimizer="adam",
    lambda_TV=0.0, lambda_smooth=1e-4, lambda_solubility=1.0,
    C_max_si=1e26, log_every=50, seed=0,
)
designer = InverseDesigner(ensemble.members[0], icfg)
result = designer.design(param, target_biases, target_currents)
print(f"  inverse done: final loss = {result.final_loss:.3e}")

# Plot the recovered profile vs ground truth
fig = plot_doping_recovery(
    inv_x.numpy(),
    result.C_recovered_si.numpy(),
    C_true=np.interp(inv_x.numpy(), true_x_si, true_doping_si.numpy()),
    title=f"Inverse design (final loss = {result.final_loss:.2e})",
)
fig.savefig(FIG_DIR / "04_doping_recovery.png")
print("Recovery plot -> figures/04_doping_recovery.png")

# Save the recovered profile + history
np.savez(OUT_DIR / "inverse_result.npz",
          x_si=inv_x.numpy(),
          C_recovered_si=result.C_recovered_si.numpy(),
          target_biases=result.target_biases.numpy(),
          target_currents=result.target_currents_si.numpy(),
          predicted_currents=result.predicted_currents_si.numpy(),
          C_true=np.interp(inv_x.numpy(), true_x_si, true_doping_si.numpy()))
with open(OUT_DIR / "inverse_history.json", "w", encoding="utf-8") as f:
    json.dump(result.history, f, indent=2)

# ---------------------------------------------------------------------------
# Stage 4: Active learning ablation
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("Stage 4: Active learning ablation (small budget for demo)")
print("=" * 70)

# Target: a defect profile (different from training distribution)
x_target = np.linspace(*DOMAIN, 64)
C_target = defect_profile(x_target, N_A=1e22, N_D=1e22,
                           x_junction=5e-7,
                           defect_amplitude=2e22,
                           defect_center=7e-7,
                           defect_width=5e-8)
target_doping_t = torch.as_tensor(C_target, dtype=torch.float32)

al_results = {}
for strategy in ["random", "max_std", "ucb"]:
    print(f"\n  AL strategy: {strategy}")
    al_cfg = ActiveLearningConfig(
        n_rounds=4,
        candidate_biases=np.linspace(0.0, BIAS_MAX, 17),
        initial_biases=(0.0, 0.2),
        strategy=strategy,
        n_inverse_iters=80,
        inverse_cfg=InverseConfig(
            lr=5e-3, lambda_TV=0.0,
            lambda_smooth=1e-4, lambda_solubility=1.0,
        ),
        seed=0,
    )
    initial_doping = -1e21 * torch.ones_like(target_doping_t)
    # weak uniform p-type init: doesn't match truth, but is in-distribution
    # so the PINN gradient through the doping is well-conditioned.
    res = active_learning_loop(
        uq_model=ensemble, oracle=sg_solver,
        true_doping_si=target_doping_t,
        forward_for_inverse=ensemble.members[0],
        initial_doping_si=initial_doping, cfg=al_cfg,
    )
    al_results[strategy] = res
    print(f"  biases chosen: {[round(l.chosen_bias, 3) for l in res['log']]}")
    print(f"  final relative L2 doping error: "
          f"{res['log'][-1].doping_error_relative:.3f}")

# Convergence plot (per-round relative L2 error)
al_logs_serializable = {
    s: [dict(round_idx=l.round_idx, chosen_bias=l.chosen_bias,
              inverse_loss=l.inverse_loss,
              doping_error_l2=l.doping_error_l2,
              doping_error_relative=l.doping_error_relative)
        for l in res["log"]]
    for s, res in al_results.items()
}
fig = plot_active_learning_convergence(
    al_logs_serializable, metric="doping_error_relative",
    title="Active learning convergence",
)
fig.savefig(FIG_DIR / "05_al_convergence.png")
print("\nAL convergence plot -> figures/05_al_convergence.png")
with open(OUT_DIR / "al_results.json", "w", encoding="utf-8") as f:
    json.dump(al_logs_serializable, f, indent=2)

# ---------------------------------------------------------------------------
# Stage 5: Calibration on held-out I-V
# ---------------------------------------------------------------------------

print()
print("=" * 70)
print("Stage 5: Calibration on a sweep of held-out profiles")
print("=" * 70)

# Generate 16 held-out test profiles + their SG-oracle I-V curves
rng = np.random.default_rng(101)
from bayespinn_inv.data.datasets import sample_doping

held_out = [sample_doping("step", n_points=128, domain_si=DOMAIN, rng=rng)
            for _ in range(4)]
cal_biases = np.linspace(0.0, BIAS_MAX, 6)

# For each held-out profile + bias, get ensemble samples and SG ground truth
sample_currents = []   # (n_profiles*n_biases, M)
truth_currents = []    # (n_profiles*n_biases,)
for prof in held_out:
    dop = torch.as_tensor(prof.doping_si, dtype=torch.float32)
    _, pred = ensemble.iv_curve(dop, cal_biases.tolist())
    # samples shape: (M, B)
    for b_idx in range(len(cal_biases)):
        sample_currents.append(pred.samples[:, b_idx])
    # SG ground truth
    sg_dop = np.interp(scaling.x_to_si(torch.as_tensor(sg_grid.x)).numpy(),
                        prof.x_si, prof.doping_si)
    prev = None
    for V in cal_biases:
        s = sg_solver.solve(sg_dop, float(V), initial_state=prev)
        truth_currents.append(s.terminal_current)
        prev = s
sample_currents = np.asarray(sample_currents).T   # (M, n_total)
truth_currents = np.asarray(truth_currents)        # (n_total,)
print(f"Calibration set: {sample_currents.shape[1]} (profile, bias) points, "
      f"M={sample_currents.shape[0]} samples each")

# Reliability + ECE
from bayespinn_inv.bayesian.ensembles import EnsemblePrediction

pred = EnsemblePrediction(
    mean=sample_currents.mean(axis=0),
    std=sample_currents.std(axis=0),
    samples=sample_currents,
    quantile_lo=np.quantile(sample_currents, 0.05, axis=0),
    quantile_hi=np.quantile(sample_currents, 0.95, axis=0),
)
report = report_calibration(pred, truth_currents, n_bins=10)
print(f"\nUncalibrated:\n{report.summary()}")

T = fit_temperature_regression(pred.mean, pred.std, truth_currents)
print(f"Fitted temperature: T = {T:.3f}")
pred_T = EnsemblePrediction(
    mean=pred.mean, std=T * pred.std,
    samples=pred.mean[None, :] + T * (pred.samples - pred.mean[None, :]),
    quantile_lo=pred.mean - T * (pred.mean - pred.quantile_lo),
    quantile_hi=pred.mean + T * (pred.quantile_hi - pred.mean),
)
report_T = report_calibration(pred_T, truth_currents, n_bins=10)
print(f"Temperature-scaled:\n{report_T.summary()}")

fig = plot_reliability_diagram(report.predicted_q, report.empirical_q,
                                 ece=report.ece, title="Uncalibrated")
fig.savefig(FIG_DIR / "06_reliability_uncal.png")
fig = plot_reliability_diagram(report_T.predicted_q, report_T.empirical_q,
                                 ece=report_T.ece,
                                 title=f"Temperature-scaled (T={T:.2f})")
fig.savefig(FIG_DIR / "06_reliability_cal.png")
print("Reliability plots -> figures/06_reliability_uncal.png, _cal.png")

# Save aggregated metrics
metrics_summary = {
    "training": {
        "n_epochs":           N_EPOCHS,
        "n_ensemble":         N_ENSEMBLE,
        "total_train_s":      total_train,
        "final_losses": [h[-1]["loss_total"] for h in all_histories],
    },
    "benchmark": benchmark_results,
    "inverse": {
        "final_loss": result.final_loss,
    },
    "active_learning_final_rel_L2": {
        s: res["log"][-1].doping_error_relative
        for s, res in al_results.items()
    },
    "calibration_uncalibrated": {
        "ECE": report.ece, "MCE": report.mce,
        "CRPS": report.crps, "NLL": report.nll,
        "sharpness": report.sharpness,
    },
    "calibration_temperature_scaled": {
        "T": T,
        "ECE": report_T.ece, "MCE": report_T.mce,
        "CRPS": report_T.crps, "NLL": report_T.nll,
        "sharpness": report_T.sharpness,
    },
}
with open(OUT_DIR / "metrics_summary.json", "w", encoding="utf-8") as f:
    json.dump(metrics_summary, f, indent=2)

print()
print("=" * 70)
print("Demo complete.")
print(f"  Outputs:  {OUT_DIR}/")
print(f"  Figures:  {FIG_DIR}/")
print(f"  Summary:  {OUT_DIR}/metrics_summary.json")
print("=" * 70)
