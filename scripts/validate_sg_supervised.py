#!/usr/bin/env python
"""Proof-of-concept: SG-supervised physics-informed surrogate.

Trains the existing SemiconductorPINN with:
  - direct supervision of the terminal current against the SG oracle
    (in a symlog scale to span the ~13 orders of magnitude of diode I-V),
  - Poisson + boundary residuals as physics regularizers.

Then compares the trained surrogate's I-V to SG. If this tracks SG across
the bias range (real relative error, not ~1.0), the reframe works and the
whole downstream pipeline (inverse design, UQ, AL, calibration) produces
honest numbers on top of it.

This is intentionally small (free-Colab budget): one network, a handful of
profiles, a few thousand epochs, a few minutes on CPU.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.inverse.charts import anchor_signed_to_grid
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.losses import (
    PhysicsParams,
    boundary_residuals,
    pde_residuals,
)
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

torch.manual_seed(0)
np.random.seed(0)

DOMAIN = (0.0, 1e-6)
BIAS_MAX = 0.6
N_ANCHOR = 16
N_COLLOC = 96
HIDDEN = 64
N_BLOCKS = 3
FOURIER = 16
N_EPOCHS = 4000
I0 = 1e-6        # symlog reference current (A/m^2)

scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
Va_scaled_max = BIAS_MAX / scaling.V_T

# scaled mobilities via the scaling's mu_to_scaled
mu_n_s = float(scaling.mu_to_scaled(SILICON.mu_n))
mu_p_s = float(scaling.mu_to_scaled(SILICON.mu_p))

print(f"L_scaled={L_scaled:.3f}, Va_scaled_max={Va_scaled_max:.1f}, "
      f"mu_n_s={mu_n_s:.3f}, mu_p_s={mu_p_s:.3f}")


def symlog(I):
    if isinstance(I, torch.Tensor):
        return torch.sign(I) * torch.log10(1.0 + torch.abs(I) / I0)
    return np.sign(I) * np.log10(1.0 + np.abs(I) / I0)


# --- Build training profiles (step junctions at several doping levels) ---
def step_profile(NA, ND, n=N_ANCHOR):
    x = np.linspace(*DOMAIN, n)
    return np.where(x < 0.5 * DOMAIN[1], -NA, ND)

doping_levels = [1e21, 3e21, 1e22, 3e22]
profiles = [step_profile(L, L) for L in doping_levels]

# --- Precompute SG terminal currents across bias for each profile ---
sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())
biases = np.linspace(0.0, BIAS_MAX, 13)
print("Precomputing SG terminal currents...")
sg_currents = np.zeros((len(profiles), len(biases)))
for pi, C in enumerate(profiles):
    C_grid = anchor_signed_to_grid(C, sg.grid.N)       # CHART-01: chart L
    prev = None
    for bi, V in enumerate(biases):
        st = sg.solve(C_grid, float(V), initial_state=prev)
        sg_currents[pi, bi] = st.terminal_current
        prev = st
print(f"  SG |I| range: [{np.abs(sg_currents).min():.2e}, {np.abs(sg_currents).max():.2e}] A/m^2")

# --- Network ---
cfg = PINNConfig(in_dim=2, hidden_dim=HIDDEN, num_blocks=N_BLOCKS,
                 fourier_features=FOURIER, fourier_sigma=2.0,
                 doping_dim=N_ANCHOR, seed=0,
                 x_scaled_extent=L_scaled, V_a_scaled_extent=Va_scaled_max)
net = SemiconductorPINN(cfg)
print(f"params={net.num_parameters():,}")

# Precompute doping latents + boundary scaled doping
latents = []
C_bdy_list = []
for C in profiles:
    latent = torch.as_tensor(scaling.doping_to_net_input(C), dtype=torch.float32)
    latents.append(latent)
    Cs = scaling.doping_to_scaled(C)
    C_bdy_list.append(torch.tensor([[float(Cs[0])], [float(Cs[-1])]], dtype=torch.float32))

opt = torch.optim.Adam(net.parameters(), lr=2e-3)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=N_EPOCHS)

W_CURR = 1.0
W_POISSON = 0.1
W_BDY = 1.0

t0 = time.time()
for epoch in range(N_EPOCHS):
    pi = np.random.randint(len(profiles))
    bi = np.random.randint(len(biases))
    C = profiles[pi]
    latent = latents[pi]
    V = float(biases[bi])
    V_a_s = V / scaling.V_T

    # Collocation points
    x_s = torch.rand(N_COLLOC, 1) * L_scaled
    x_s.requires_grad_(True)
    Va_col = torch.full((N_COLLOC, 1), V_a_s)
    lat_col = latent[None, :].expand(N_COLLOC, -1)

    # Scaled net doping at collocation points
    x_anchor = np.linspace(*DOMAIN, N_ANCHOR)
    x_col_si = scaling.x_to_scaled(torch.tensor(DOMAIN[1])).item()  # not used
    # interpolate C at the collocation x (in SI)
    x_col_phys = (x_s.detach().numpy().ravel() / L_scaled) * DOMAIN[1]
    C_col_si = np.interp(x_col_phys, x_anchor, C)
    C_s_col = torch.as_tensor(scaling.doping_to_scaled(C_col_si),
                              dtype=torch.float32).reshape(-1, 1)

    phys = PhysicsParams(mu_n_s=mu_n_s, mu_p_s=mu_p_s,
                         tau_n_s=1e6, tau_p_s=1e6, enable_srh=False,
                         poisson_scale=float(np.abs(scaling.doping_to_scaled(C)).max()),
                         current_scale=max(mu_n_s, mu_p_s))
    res = pde_residuals(net, x_s, Va_col, lat_col, C_s_col, phys)

    # Terminal current = mean of J_tot (the exact quantity iv_curve returns)
    J_tot_s = res["J_n_s"] + res["J_p_s"]
    J_term_s = J_tot_s.mean()
    I_pinn = scaling.J_to_si(J_term_s)
    I_sg = sg_currents[pi, bi]

    # Current supervision in symlog space
    l_curr = (symlog(I_pinn) - symlog(torch.tensor(I_sg, dtype=torch.float32))) ** 2

    # Physics regularizers
    l_poisson = torch.mean(res["r_phi"] ** 2)

    # Boundary
    xb = torch.tensor([[0.0], [L_scaled]], requires_grad=False)
    Vb = torch.full((2, 1), V_a_s)
    latb = latent[None, :].expand(2, -1)
    Cb = C_bdy_list[pi]
    bdy = boundary_residuals(net, xb, Vb, latb, Cb)
    l_bdy = sum(torch.mean(bdy[k] ** 2) for k in bdy)

    loss = W_CURR * l_curr + W_POISSON * l_poisson + W_BDY * l_bdy
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
    opt.step()
    sched.step()

    if epoch % 500 == 0 or epoch == N_EPOCHS - 1:
        print(f"[{epoch:5d}] loss={float(loss):.3e} "
              f"curr={float(l_curr):.3e} poisson={float(l_poisson):.3e} "
              f"bdy={float(l_bdy):.3e}")

print(f"Trained in {time.time()-t0:.1f}s")

# --- Validate: PINN I-V vs SG on the training profiles ---
print("\n=== PINN I-V vs SG (symlog-supervised surrogate) ===")
net.eval()
for pi, _C in enumerate(profiles):
    latent = latents[pi]
    print(f"\nProfile N_A=N_D={doping_levels[pi]:.0e}:")
    print(f"  {'V':>5} {'I_SG':>11} {'I_PINN':>11} {'symlog_err':>10}")
    errs = []
    for bi, V in enumerate(biases):
        V_a_s = float(V) / scaling.V_T
        x_s = torch.linspace(0, L_scaled, 201).reshape(-1, 1).requires_grad_(True)
        Va = torch.full((201, 1), V_a_s)
        lat = latent[None, :].expand(201, -1)
        phi_s, log_n, log_p = net(x_s, Va, lat)
        dphi = torch.autograd.grad(phi_s, x_s, torch.ones_like(phi_s), create_graph=False, retain_graph=True)[0]
        dlogn = torch.autograd.grad(log_n, x_s, torch.ones_like(log_n), create_graph=False, retain_graph=True)[0]
        dlogp = torch.autograd.grad(log_p, x_s, torch.ones_like(log_p), create_graph=False, retain_graph=True)[0]
        n_s, p_s = torch.exp(log_n), torch.exp(log_p)
        J = mu_n_s * n_s * (dlogn - dphi) - mu_p_s * p_s * (dlogp + dphi)
        I_pinn = float(scaling.J_to_si(J.mean()))
        I_sg = sg_currents[pi, bi]
        se = abs(float(symlog(I_pinn)) - float(symlog(I_sg)))
        errs.append(se)
        if bi % 3 == 0:
            print(f"  {V:5.2f} {I_sg:11.3e} {I_pinn:11.3e} {se:10.3f}")
    print(f"  mean symlog error across bias: {np.mean(errs):.3f}")
