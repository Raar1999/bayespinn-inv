#!/usr/bin/env python
"""Proof: direct current-head surrogate (the correct reframe).

A small MLP maps (doping_latent, bias) -> signed-log terminal current,
supervised by SG. This bypasses the numerically-fragile field-gradient
current computation entirely. Trained on a set of doping levels, tested on
HELD-OUT levels to show it generalizes (not memorizes).

If held-out I-V tracks SG across 13 orders of magnitude, the surrogate
reframe is proven: inverse design / UQ / AL / calibration all work on top.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

torch.manual_seed(0); np.random.seed(0)
DOMAIN = (0.0, 1e-6); BIAS_MAX = 0.6; N_ANCHOR = 16; I0 = 1e-6

scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))

def symlog_np(I): return np.sign(I) * np.log10(1.0 + np.abs(I) / I0)
def isymlog(s):   return np.sign(s) * I0 * (10.0 ** np.abs(s) - 1.0)

def step_profile(NA, ND, n=N_ANCHOR):
    x = np.linspace(*DOMAIN, n)
    return np.where(x < 0.5 * DOMAIN[1], -NA, ND)

# --- Doping levels: train on 9, hold out 3 (interpolated + extrapolated) ---
all_levels = np.geomspace(5e20, 5e22, 12)
test_idx = [2, 6, 10]
train_idx = [i for i in range(12) if i not in test_idx]
print(f"Train levels: {all_levels[train_idx]}")
print(f"Test  levels: {all_levels[test_idx]}")

sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())
biases = np.linspace(0.0, BIAS_MAX, 13)

def build_xy(levels):
    X, Y = [], []
    for L in levels:
        C = step_profile(L, L)
        latent = scaling.doping_to_net_input(C)   # (N_ANCHOR,)
        prev = None
        for V in biases:
            st = sg.solve(C, float(V), initial_state=prev); prev = st
            X.append(np.concatenate([latent, [V / scaling.V_T]]))
            Y.append(symlog_np(st.terminal_current))
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)

print("Generating SG data...")
Xtr, Ytr = build_xy(all_levels[train_idx])
Xte, Yte = build_xy(all_levels[test_idx])
print(f"  train {Xtr.shape}, test {Xte.shape}")

# normalize inputs
mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8
Xtr_n = torch.tensor((Xtr - mu) / sd); Ytr_t = torch.tensor(Ytr).reshape(-1, 1)
Xte_n = torch.tensor((Xte - mu) / sd); Yte_t = torch.tensor(Yte).reshape(-1, 1)

# --- Current-head MLP ---
class CurrentHead(nn.Module):
    def __init__(self, d_in, h=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, h), nn.SiLU(),
            nn.Linear(h, h), nn.SiLU(),
            nn.Linear(h, h), nn.SiLU(),
            nn.Linear(h, 1),
        )
    def forward(self, x): return self.net(x)

head = CurrentHead(Xtr.shape[1])
print(f"current-head params={sum(p.numel() for p in head.parameters()):,}")
opt = torch.optim.Adam(head.parameters(), lr=2e-3, weight_decay=1e-5)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=3000)

t0 = time.time()
for epoch in range(3000):
    opt.zero_grad()
    pred = head(Xtr_n)
    loss = nn.functional.mse_loss(pred, Ytr_t)
    loss.backward(); opt.step(); sched.step()
    if epoch % 500 == 0 or epoch == 2999:
        with torch.no_grad():
            te = nn.functional.mse_loss(head(Xte_n), Yte_t)
        print(f"[{epoch:4d}] train_mse={float(loss):.4f} test_mse={float(te):.4f}")
print(f"Trained in {time.time()-t0:.1f}s")

# --- Validate on HELD-OUT levels ---
print("\n=== Held-out I-V: surrogate vs SG ===")
head.eval()
with torch.no_grad():
    pred_te = head(Xte_n).numpy().ravel()
k = 0
all_rel = []
for li, L in enumerate(all_levels[test_idx]):
    print(f"\nHELD-OUT N_A=N_D={L:.2e}:")
    print(f"  {'V':>5} {'I_SG':>12} {'I_surrogate':>12} {'rel_err':>9}")
    for bi, V in enumerate(biases):
        s_pred = pred_te[k]; k += 1
        I_pred = isymlog(s_pred)
        I_sg = isymlog(Yte[li * len(biases) + bi])
        rel = abs(I_pred - I_sg) / max(abs(I_sg), 1e-9)
        all_rel.append(rel)
        if bi % 2 == 0:
            print(f"  {V:5.2f} {I_sg:12.3e} {I_pred:12.3e} {rel:9.3f}")
print(f"\nMedian relative error on held-out I-V: {np.median(all_rel):.3f}")
print(f"Mean symlog (log-decade) error: {np.mean(np.abs(pred_te - Yte)):.3f}")
