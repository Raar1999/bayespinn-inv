#!/usr/bin/env python
"""Quantitative results through the SG-supervised surrogate forward model.

Produces real, measured numbers for the project's core scientific claims:

  H1  Forward accuracy   : surrogate reproduces SG I-V on held-out profiles
  H2  Inverse recovery   : doping recovered from I-V; error vs measurement noise
  H3  Uncertainty (UQ)   : ensemble prediction intervals are calibrated
  H4  Active-learning gain: few well-chosen biases recover doping as well as many

All numbers are measured against the Scharfetter-Gummel oracle. Outputs:
  outputs/results/results.json
  outputs/results/results_summary.md
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import ScharfetterGummel1D, Grid1D, SGConfig
from bayespinn_inv.surrogate import (
    SymlogTransform, Normalizer, IVSurrogate, IVSurrogateConfig,
    build_sg_dataset, train_surrogate, SurrogateEnsemble,
)

torch.manual_seed(0); np.random.seed(0)
DOMAIN = (0.0, 1e-6); BIAS_MAX = 0.6; N_ANCHOR = 16; M_ENSEMBLE = 5
OUT = Path(__file__).parent.parent / "outputs" / "results"; OUT.mkdir(parents=True, exist_ok=True)

scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
VT = scaling.V_T
symlog = SymlogTransform(I0=1e-6)
sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())
biases = np.linspace(0.0, BIAS_MAX, 13)

xa = np.linspace(*DOMAIN, N_ANCHOR)
def step(L):  return np.where(xa < 0.5*DOMAIN[1], -L, L).astype(np.float64)
def graded(L, w=1.5e-7):
    xj = 0.5*DOMAIN[1]
    return (L*np.tanh((xa - xj)/w)).astype(np.float64)

# ---- Training set: step + graded over a doping range ----
train_levels = np.geomspace(5e20, 5e22, 11)
train_profiles = [step(L) for L in train_levels] + [graded(L) for L in train_levels[::2]]
print(f"Building SG dataset: {len(train_profiles)} profiles x {len(biases)} biases")
t0 = time.time()
X, Y = build_sg_dataset(train_profiles, biases, scaling, sg, symlog)
norm = Normalizer.fit(X)
print(f"  data {X.shape} in {time.time()-t0:.1f}s")

# ---- Train M-member ensemble ----
print(f"Training {M_ENSEMBLE}-member surrogate ensemble...")
members = []
for m in range(M_ENSEMBLE):
    net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, seed=m))
    # bootstrap resample for ensemble diversity
    rs = np.random.RandomState(m); idx = rs.randint(0, len(X), len(X))
    train_surrogate(net, X[idx], Y[idx], norm, epochs=2500, lr=2e-3)
    members.append(net)
ens = SurrogateEnsemble(members, norm, symlog)
print(f"  ensemble M={ens.M}, params/member={members[0].num_parameters():,}")

results = {}

# ============================================================================
# H1: Forward accuracy on held-out profiles
# ============================================================================
print("\n[H1] Forward accuracy on held-out profiles")
test_levels = np.geomspace(7e20, 4e22, 6)
def fwd_err(profiles, label):
    rels = []
    for C in profiles:
        latent = scaling.doping_to_net_input(C)
        pred = ens.predict(latent, biases / VT)
        prev=None; Isg=[]
        for V in biases:
            stt = sg.solve(C, float(V), initial_state=prev); Isg.append(stt.terminal_current); prev=stt
        Isg = np.array(Isg)
        for bi, V in enumerate(biases):
            if V < 0.1: continue  # skip V~0 where SG current is sub-noise
            rels.append(abs(pred.mean_current[bi]-Isg[bi])/max(abs(Isg[bi]),1e-9))
    rels = np.array(rels)
    return {"median_rel_err": float(np.median(rels)),
            "p90_rel_err": float(np.quantile(rels,0.9)),
            "mean_rel_err": float(np.mean(rels)), "n": len(rels)}
results["H1_forward_step"]   = fwd_err([step(L) for L in test_levels], "step")
results["H1_forward_graded"] = fwd_err([graded(L) for L in test_levels], "graded")
print(f"  step:   median rel err {results['H1_forward_step']['median_rel_err']:.3f}, "
      f"p90 {results['H1_forward_step']['p90_rel_err']:.3f}")
print(f"  graded: median rel err {results['H1_forward_graded']['median_rel_err']:.3f}, "
      f"p90 {results['H1_forward_graded']['p90_rel_err']:.3f}")

# ============================================================================
# H2: Inverse recovery vs measurement noise (step-junction family)
# ============================================================================
print("\n[H2] Inverse recovery vs measurement noise")
half = N_ANCHOR // 2
def encode_level(logL):
    C = torch.cat([-(10.0**logL).repeat(half), (10.0**logL).repeat(N_ANCHOR-half)])
    return scaling.doping_to_net_input(C)

def recover(target_symlog, member):
    logL = torch.tensor(21.5, requires_grad=True)
    opt = torch.optim.Adam([logL], lr=0.05)
    bs = torch.tensor(biases/VT, dtype=torch.float32)
    for _ in range(400):
        opt.zero_grad()
        lat = encode_level(logL)
        feats = torch.stack([torch.cat([lat, bs[i].reshape(1)]) for i in range(len(biases))])
        pred = member((feats - norm.mean)/norm.std).reshape(-1)
        loss = torch.nn.functional.mse_loss(pred, target_symlog)
        loss.backward(); opt.step(); logL.data.clamp_(20.0, 23.0)
    return float(logL)

noise_levels = [0.0, 0.02, 0.05, 0.10]
recov_truth_levels = np.geomspace(8e20, 3e22, 5)
h2 = {}
for noise in noise_levels:
    errs, covered = [], []
    for Ltrue in recov_truth_levels:
        C = step(Ltrue); prev=None; Isg=[]
        for V in biases:
            stt = sg.solve(C, float(V), initial_state=prev); Isg.append(stt.terminal_current); prev=stt
        Isg = np.array(Isg)
        # multiplicative measurement noise in current
        rng = np.random.RandomState(int(Ltrue) % 2**31)
        Inoisy = Isg * (1.0 + noise*rng.standard_normal(len(biases)))
        tgt = torch.tensor(symlog.forward(Inoisy), dtype=torch.float32)
        rec = np.array([recover(tgt, m) for m in members])
        truth = np.log10(Ltrue)
        errs.append(abs(rec.mean()-truth))
        covered.append(abs(rec.mean()-truth) <= rec.std()+1e-9)
    h2[f"noise_{noise}"] = {"median_abs_err_decades": float(np.median(errs)),
                            "mean_abs_err_decades": float(np.mean(errs)),
                            "coverage_1sigma": float(np.mean(covered))}
    print(f"  noise={noise:4.2f}: median recovery err {np.median(errs):.3f} decades, "
          f"1σ coverage {np.mean(covered):.2f}")
results["H2_inverse_vs_noise"] = h2

# ============================================================================
# H3: Calibration of ensemble prediction intervals on held-out I-V
# ============================================================================
print("\n[H3] UQ calibration: interval coverage on held-out I-V")
# For each held-out profile+bias, does the ensemble's +/-z*sigma symlog interval
# contain the SG truth at the nominal rate?
from math import erf, sqrt
def nominal(z): return erf(z/sqrt(2))   # central coverage of a Gaussian +/- z sigma
zs = [1.0, 1.64, 2.0]
cov = {z: [] for z in zs}
for C in [step(L) for L in test_levels] + [graded(L) for L in test_levels]:
    latent = scaling.doping_to_net_input(C)
    pred = ens.predict(latent, biases / VT)
    prev=None
    for bi, V in enumerate(biases):
        stt = sg.solve(C, float(V), initial_state=prev); prev=stt
        if V < 0.1: continue
        truth_s = symlog.forward(stt.terminal_current)
        for z in zs:
            lo = pred.mean_symlog[bi] - z*pred.std_symlog[bi]
            hi = pred.mean_symlog[bi] + z*pred.std_symlog[bi]
            cov[z].append(lo <= truth_s <= hi)
results["H3_calibration"] = {
    f"z_{z}": {"empirical_coverage": float(np.mean(cov[z])),
               "nominal_coverage": float(nominal(z))} for z in zs}
for z in zs:
    print(f"  ±{z}σ: empirical {np.mean(cov[z]):.2f} vs nominal {nominal(z):.2f}")

# Recalibration: fit a scalar variance-inflation T on a validation split so
# that ±1σ empirical coverage matches nominal, then re-measure on the test
# split. This is the standard fix for ensemble overconfidence.
print("  [recalibration] fitting variance-inflation temperature...")
val_profiles  = [step(L) for L in np.geomspace(6e20, 4e22, 6)]
test_profiles_c = [step(L) for L in np.geomspace(9e20, 3e22, 6)] + \
                  [graded(L) for L in np.geomspace(9e20, 3e22, 4)]
def gather_resid(profiles):
    z_scores = []
    for C in profiles:
        latent = scaling.doping_to_net_input(C); pred = ens.predict(latent, biases/VT)
        prev=None
        for bi, V in enumerate(biases):
            stt = sg.solve(C, float(V), initial_state=prev); prev=stt
            if V < 0.1: continue
            s = pred.std_symlog[bi]
            if s > 1e-9:
                z_scores.append((symlog.forward(stt.terminal_current)-pred.mean_symlog[bi])/s)
    return np.array(z_scores)
zv = gather_resid(val_profiles)
# T such that fraction(|z/T|<=1) == nominal(1): T = quantile(|z|, nominal(1))
T = float(np.quantile(np.abs(zv), nominal(1.0)))
T = max(T, 1e-3)
zt = gather_resid(test_profiles_c)
recal = {}
for z in zs:
    pre = float(np.mean(np.abs(zt) <= z))
    post = float(np.mean(np.abs(zt) <= z * T))
    recal[f"z_{z}"] = {"pre": pre, "post": post, "nominal": float(nominal(z))}
    print(f"  ±{z}σ recalibrated: {post:.2f} (was {pre:.2f}, nominal {nominal(z):.2f})")
results["H3_recalibrated"] = {"temperature": T, **recal}

# ============================================================================
# H4: Active-learning gain (few informative biases vs full sweep)
# ============================================================================
print("\n[H4] Active-learning gain: recovery from few biases")
# Compare doping recovery using (a) 3 low-bias points, (b) 3 high-bias points,
# (c) all 13. High-bias points carry more diode signal -> better recovery.
def recover_subset(Ltrue, bias_idx):
    C = step(Ltrue); prev=None; Isg=[]
    for V in biases:
        stt = sg.solve(C, float(V), initial_state=prev); Isg.append(stt.terminal_current); prev=stt
    Isg = np.array(Isg)
    bs = torch.tensor(biases[bias_idx]/VT, dtype=torch.float32)
    tgt = torch.tensor(symlog.forward(Isg[bias_idx]), dtype=torch.float32)
    recs = []
    for m in members:
        logL = torch.tensor(21.5, requires_grad=True)
        opt = torch.optim.Adam([logL], lr=0.05)
        for _ in range(400):
            opt.zero_grad()
            lat = encode_level(logL)
            feats = torch.stack([torch.cat([lat, bs[i].reshape(1)]) for i in range(len(bias_idx))])
            pred = m((feats - norm.mean)/norm.std).reshape(-1)
            loss = torch.nn.functional.mse_loss(pred, tgt)
            loss.backward(); opt.step(); logL.data.clamp_(20.0,23.0)
        recs.append(float(logL))
    return np.array(recs)
strategies = {"low_3_biases": [0,1,2], "high_3_biases": [10,11,12], "all_13": list(range(13))}
h4 = {}
for name, idx in strategies.items():
    errs = [abs(recover_subset(L, idx).mean()-np.log10(L)) for L in recov_truth_levels]
    h4[name] = {"median_abs_err_decades": float(np.median(errs)), "n_biases": len(idx)}
    print(f"  {name:14s} ({len(idx)} biases): median recovery err {np.median(errs):.3f} decades")
results["H4_active_learning"] = h4

# ---- Save ----
(OUT / "results.json").write_text(json.dumps(results, indent=2))
md = ["# BayesPINN-Inv: quantitative results (SG-supervised surrogate)\n",
      "All errors measured against the Scharfetter-Gummel oracle. "
      f"Ensemble M={M_ENSEMBLE}, {members[0].num_parameters():,} params/member.\n",
      "## H1 Forward accuracy (held-out profiles, V>=0.1V)\n",
      f"- Step junctions: median rel. I-V error **{results['H1_forward_step']['median_rel_err']:.1%}**, "
      f"p90 {results['H1_forward_step']['p90_rel_err']:.1%}",
      f"- Graded junctions: median rel. I-V error **{results['H1_forward_graded']['median_rel_err']:.1%}**, "
      f"p90 {results['H1_forward_graded']['p90_rel_err']:.1%}\n",
      "## H2 Inverse recovery vs measurement noise\n",
      "| Noise | Median recovery error (decades) | 1σ coverage |",
      "|---|---:|---:|"]
for noise in noise_levels:
    d = results["H2_inverse_vs_noise"][f"noise_{noise}"]
    md.append(f"| {noise:.0%} | {d['median_abs_err_decades']:.3f} | {d['coverage_1sigma']:.0%} |")
md += ["\n## H3 UQ calibration (interval coverage on held-out I-V)\n",
       "| Interval | Empirical (raw) | Recalibrated | Nominal |", "|---|---:|---:|---:|"]
for z in zs:
    d = results["H3_calibration"][f"z_{z}"]
    r = results["H3_recalibrated"][f"z_{z}"]
    md.append(f"| ±{z}σ | {d['empirical_coverage']:.0%} | {r['post']:.0%} | {d['nominal_coverage']:.0%} |")
md.append(f"\n*Variance-inflation temperature T={results['H3_recalibrated']['temperature']:.2f} "
          "fit on a validation split (standard fix for ensemble overconfidence).*")
md += ["\n## H4 Active-learning gain\n",
       "| Bias subset | # biases | Median recovery error (decades) |", "|---|---:|---:|"]
for name, idx in strategies.items():
    d = results["H4_active_learning"][name]
    md.append(f"| {name.replace('_',' ')} | {d['n_biases']} | {d['median_abs_err_decades']:.3f} |")
(OUT / "results_summary.md").write_text("\n".join(md))
print(f"\nSaved -> {OUT}/results.json and results_summary.md")
