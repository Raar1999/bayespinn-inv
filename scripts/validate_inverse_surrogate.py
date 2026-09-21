#!/usr/bin/env python
"""Closing the loop: inverse design + uncertainty through the surrogate.

1. Train a 3-member ensemble of current-head surrogates on SG data.
2. Forward check on a held-out doping level.
3. Inverse design: given a target I-V (from SG at a held-out level),
   recover the doping level by gradient descent through each surrogate.
4. Report the recovered doping with an ensemble uncertainty band.

This demonstrates the full scientific pipeline works with the reframe:
forward (doping->I-V) accurate, inverse (I-V->doping) recovers truth,
uncertainty quantified.
"""
from __future__ import annotations

import sys
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

np.random.seed(0)
DOMAIN = (0.0, 1e-6); BIAS_MAX = 0.6; N_ANCHOR = 16; I0 = 1e-6
scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
VT = scaling.V_T

def symlog_np(I): return np.sign(I) * np.log10(1.0 + np.abs(I) / I0)
def step_profile(L, n=N_ANCHOR):
    x = np.linspace(*DOMAIN, n); return np.where(x < 0.5 * DOMAIN[1], -L, L)

# doping level -> latent (log-compressed), as a torch-differentiable map
def level_to_latent_torch(log10_level):
    """Differentiable encoding of a uniform step-junction at 10**log10_level.

    Mirrors scaling.doping_to_net_input for a symmetric step (|C| constant,
    sign flips at the junction). doping_to_net_input applies a signed-log
    compression; we replicate it so gradients flow to log10_level.
    """
    # signed log compression used by the scaling: sign * log10(1+|C|/C0)
    # Recover C0 by probing the numpy encoder on a known value.
    return log10_level  # placeholder; real encoding probed numerically below

sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())
biases = np.linspace(0.0, BIAS_MAX, 13)

# Probe the encoder to get its functional form: encode |C| over a sweep,
# fit so we can build a differentiable torch version.
probe_levels = np.geomspace(1e20, 1e23, 40)
enc_left = []   # encoded value of the left (p, negative) anchor
enc_right = []  # encoded value of the right (n, positive) anchor
for L in probe_levels:
    lat = scaling.doping_to_net_input(step_profile(L))
    enc_left.append(lat[0]); enc_right.append(lat[-1])
enc_left = np.array(enc_left); enc_right = np.array(enc_right)
# The encoding is monotonic in log10(L); fit cubic for a smooth diff map.
lg = np.log10(probe_levels)
cl = np.polyfit(lg, enc_left, 3)
cr = np.polyfit(lg, enc_right, 3)
def encode_level_torch(log10L):
    powers_l = sum(cl[i] * log10L ** (3 - i) for i in range(4))
    powers_r = sum(cr[i] * log10L ** (3 - i) for i in range(4))
    # full latent: left half = p-side value, right half = n-side value
    half = N_ANCHOR // 2
    return torch.cat([powers_l.repeat(half), powers_r.repeat(N_ANCHOR - half)])

# --- Data ---
all_levels = np.geomspace(5e20, 5e22, 14)
test_level = all_levels[7]          # held out for inverse design
train_levels = np.delete(all_levels, 7)

def build_xy(levels):
    X, Y = [], []
    for L in levels:
        lat = scaling.doping_to_net_input(step_profile(L)); prev = None
        for V in biases:
            st = sg.solve(step_profile(L), float(V), initial_state=prev); prev = st
            X.append(np.concatenate([lat, [V / VT]])); Y.append(symlog_np(st.terminal_current))
    return np.array(X, np.float32), np.array(Y, np.float32)

print("Generating SG training data...")
Xtr, Ytr = build_xy(train_levels)
mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-8
Xtr_n = torch.tensor((Xtr - mu) / sd); Ytr_t = torch.tensor(Ytr).reshape(-1, 1)
mu_t, sd_t = torch.tensor(mu), torch.tensor(sd)

class Head(nn.Module):
    def __init__(self, d, h=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, h), nn.SiLU(), nn.Linear(h, h),
                                 nn.SiLU(), nn.Linear(h, h), nn.SiLU(), nn.Linear(h, 1))
    def forward(self, x): return self.net(x)

# --- Train 3-member ensemble ---
print("Training 3-member surrogate ensemble...")
members = []
for m in range(3):
    torch.manual_seed(m)
    head = Head(Xtr.shape[1]); opt = torch.optim.Adam(head.parameters(), lr=2e-3, weight_decay=1e-5)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=2500)
    idx = np.random.RandomState(m).permutation(len(Xtr_n))  # bootstrap-ish order
    for _ep in range(2500):
        opt.zero_grad()
        loss = nn.functional.mse_loss(head(Xtr_n[idx]), Ytr_t[idx])
        loss.backward(); opt.step(); sch.step()
    members.append(head); print(f"  member {m}: final train mse={float(loss):.4f}")

def predict_symlog(head, latent, bias_scaled):
    x = torch.cat([latent, bias_scaled.reshape(1)])
    xn = (x - mu_t) / sd_t
    return head(xn.float())

# --- Forward check on held-out level ---
print(f"\nForward check, held-out N_A=N_D={test_level:.2e}:")
lat_true = torch.tensor(scaling.doping_to_net_input(step_profile(test_level)), dtype=torch.float32)
prev = None; I_sg_target = []
for V in biases:
    st = sg.solve(step_profile(test_level), float(V), initial_state=prev); prev = st
    I_sg_target.append(st.terminal_current)
I_sg_target = np.array(I_sg_target)
print(f"  {'V':>5} {'I_SG':>12} {'I_surrogate':>12}")
for bi in range(0, len(biases), 3):
    with torch.no_grad():
        s = np.mean([float(predict_symlog(h, lat_true, torch.tensor(biases[bi]/VT))) for h in members])
    I_pred = np.sign(s) * I0 * (10 ** abs(s) - 1)
    print(f"  {biases[bi]:5.2f} {I_sg_target[bi]:12.3e} {I_pred:12.3e}")

# --- Inverse design: recover doping level from the SG target I-V ---
print(f"\nInverse design: recovering doping from target I-V (truth={np.log10(test_level):.3f} in log10)")
target_symlog = torch.tensor(symlog_np(I_sg_target), dtype=torch.float32)
bias_scaled_all = torch.tensor(biases / VT, dtype=torch.float32)

recovered = []
for m, head in enumerate(members):
    log10L = torch.tensor(21.5, requires_grad=True)  # initial guess (wrong)
    opt = torch.optim.Adam([log10L], lr=0.05)
    for _it in range(400):
        opt.zero_grad()
        lat = encode_level_torch(log10L)
        preds = []
        for bi in range(len(biases)):
            x = torch.cat([lat, bias_scaled_all[bi].reshape(1)])
            xn = (x - mu_t) / sd_t
            preds.append(head(xn.float()))
        pred = torch.cat(preds).reshape(-1)
        loss = nn.functional.mse_loss(pred, target_symlog)
        loss.backward(); opt.step()
        log10L.data.clamp_(20.0, 23.0)
    recovered.append(float(log10L))
    print(f"  member {m}: recovered log10(N)={float(log10L):.3f} "
          f"(N={10**float(log10L):.2e}), final loss={float(loss):.4f}")

rec = np.array(recovered)
truth = np.log10(test_level)
print("\n=== Inverse recovery result ===")
print(f"  True doping:      log10(N) = {truth:.3f}  (N = {test_level:.2e})")
print(f"  Recovered (mean): log10(N) = {rec.mean():.3f} +/- {rec.std():.3f}")
print(f"  Recovered (N):    {10**rec.mean():.2e}  [band: {10**(rec.mean()-rec.std()):.2e}, {10**(rec.mean()+rec.std()):.2e}]")
print(f"  Absolute error:   {abs(rec.mean()-truth):.3f} decades")
print(f"  Truth inside +/-1sigma band: {abs(rec.mean()-truth) <= rec.std() + 1e-9}")
