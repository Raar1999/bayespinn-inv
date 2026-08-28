#!/usr/bin/env python
"""Generate the 01-12 Colab notebooks for BayesPINN-Inv.

Each notebook is self-contained and runnable both on Google Colab (clones +
installs the repo, optional Drive mount) and locally (adds ./src to path).
The notebooks exercise the *working* package: the SG oracle and the
SG-supervised surrogate forward model, plus inverse design, UQ, calibration,
active learning, benchmarking, and visualization.

Run from the repo root:  python scripts/build_notebooks.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

REPO = Path(__file__).parent.parent
NB_DIR = REPO / "notebooks"
NB_DIR.mkdir(exist_ok=True)

GITHUB_URL = "https://github.com/Raar1999/bayespinn-inv"  # set before pushing

# ---------------------------------------------------------------------------
# Shared cells
# ---------------------------------------------------------------------------

def badge(nb_name: str) -> str:
    colab = GITHUB_URL.replace("https://github.com/",
                               "https://colab.research.google.com/github/")
    return (f"[![Open In Colab](https://colab.research.google.com/assets/"
            f"colab-badge.svg)]({colab}/blob/main/notebooks/{nb_name})")

SETUP = f'''\
# --- Environment setup (works on Colab and locally) ---
import sys, os

IN_COLAB = "google.colab" in sys.modules

def _ensure_package():
    try:
        import bayespinn_inv  # already importable?
        return
    except ImportError:
        pass
    if IN_COLAB:
        # Optional: mount Drive for checkpoint persistence
        try:
            from google.colab import drive
            drive.mount("/content/drive")
        except Exception:
            pass
        if not os.path.isdir("bayespinn-inv"):
            os.system("git clone {GITHUB_URL} bayespinn-inv")
        os.system("pip install -q -e bayespinn-inv")
        sys.path.insert(0, os.path.abspath("bayespinn-inv/src"))
    else:
        # Local/dev: find ./src walking up from the notebook
        for cand in ["src", "../src", "../../src"]:
            if os.path.isdir(os.path.join(cand, "bayespinn_inv")):
                sys.path.insert(0, os.path.abspath(cand)); break
    import bayespinn_inv  # noqa: F401

_ensure_package()
%matplotlib inline
import numpy as np, torch, matplotlib.pyplot as plt
plt.rcParams["figure.dpi"] = 110
print("Setup OK — bayespinn_inv importable, torch", torch.__version__)
'''

# Common helpers used by several notebooks (profiles, SG oracle)
COMMON = '''\
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import ScharfetterGummel1D, Grid1D, SGConfig
from bayespinn_inv.inverse.charts import anchor_signed_to_grid

DOMAIN = (0.0, 1e-6); N_ANCHOR = 16
scaling = Scaling.for_material(SILICON, T=300.0)
L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
VT = scaling.V_T
sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())

xa = np.linspace(*DOMAIN, N_ANCHOR)
def step(L):   return np.where(xa < 0.5*DOMAIN[1], -L, L).astype(float)
def graded(L, w=1.5e-7): return (L*np.tanh((xa - 0.5*DOMAIN[1])/w)).astype(float)

def sg_iv(C, biases):
    # CHART-01: C is signed doping at N_ANCHOR anchors; the solver integrates a
    # 301-node grid. Chart L, named -- the solver no longer guesses.
    Cg = anchor_signed_to_grid(C, sg.grid.N)
    prev=None; I=[]
    for V in biases:
        s = sg.solve(Cg, float(V), initial_state=prev); I.append(s.terminal_current); prev=s
    return np.array(I)
'''


def md(text): return new_markdown_cell(text)
def code(src): return new_code_cell(src)


def make_nb(name, title, intro, cells):
    nb = new_notebook()
    nb.cells = [md(f"# {title}\n\n{badge(name)}\n\n{intro}"), md("## Setup"), code(SETUP), *cells]
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"provenance": []},
    }
    (NB_DIR / name).write_text(nbf.writes(nb), encoding="utf-8", newline="\n")
    print(f"  wrote {name} ({len(nb.cells)} cells)")


# ===========================================================================
# 01 — Setup & sanity check
# ===========================================================================
make_nb(
    "01_setup.ipynb",
    "01 · Setup & Environment Check",
    "Mount Drive (Colab), install the package, and verify the core building "
    "blocks import and run. Start here.",
    [
        md("## Sanity check: SG oracle + surrogate import"),
        code(COMMON + '''
# One SG solve as a smoke test
C = step(1e22)
I = sg_iv(C, np.array([0.0, 0.3, 0.6]))
print("SG terminal current at V=[0,0.3,0.6]:", I)
'''),
        code('''
from bayespinn_inv.surrogate import IVSurrogate, IVSurrogateConfig, SymlogTransform
net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=64, n_layers=2))
print(f"Surrogate ready: {net.num_parameters():,} params")
print("All systems go.")
'''),
        md("**Checkpoint persistence on Colab:** outputs can be written to "
           "`/content/drive/MyDrive/BayesPINN_Inv/` after mounting Drive, so "
           "trained ensembles and figures survive session timeouts."),
    ],
)

# ===========================================================================
# 02 — Physics validation
# ===========================================================================
make_nb(
    "02_physics_validation.ipynb",
    "02 · Semiconductor Physics Validation",
    "Sanity-check the scaling and the PN-junction electrostatics the whole "
    "project rests on: built-in potential, and the depletion-region fields "
    "from the Scharfetter-Gummel solver.",
    [
        code(COMMON),
        md("## Built-in potential of a PN junction\n"
           "For a step junction, $V_{bi}=V_T\\ln(N_A N_D/n_i^2)$. We compare to "
           "the potential drop the SG solver produces at equilibrium."),
        code('''
NA = ND = 1e22
Vbi_analytic = VT*np.log(NA*ND/SILICON.n_i**2)
st = sg.solve(anchor_signed_to_grid(step(1e22), sg.grid.N), 0.0)
phi = st.phi
Vbi_sg = float(phi.max() - phi.min())
print(f"V_bi analytic = {Vbi_analytic:.4f} V")
print(f"V_bi from SG  = {Vbi_sg:.4f} V")
print(f"relative diff = {abs(Vbi_sg-Vbi_analytic)/Vbi_analytic:.2%}")
'''),
        md("## Equilibrium band picture\n"
           "Potential, field, and carrier densities across the junction."),
        code('''
st = sg.solve(anchor_signed_to_grid(step(1e22), sg.grid.N), 0.0)
x_nm = np.linspace(0, 1000, len(st.phi))
fig, ax = plt.subplots(1, 3, figsize=(12, 3.2))
ax[0].plot(x_nm, st.phi); ax[0].set_title("Potential φ (V)"); ax[0].set_xlabel("x (nm)")
E = -np.gradient(st.phi, x_nm*1e-9)
ax[1].plot(x_nm, E/1e5, color="C1"); ax[1].set_title("Field (kV/cm)"); ax[1].set_xlabel("x (nm)")
ax[2].semilogy(x_nm, np.abs(st.n)+1, label="n"); ax[2].semilogy(x_nm, np.abs(st.p)+1, label="p")
ax[2].set_title("Carriers (m⁻³)"); ax[2].set_xlabel("x (nm)"); ax[2].legend()
plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 03 — SG solver
# ===========================================================================
make_nb(
    "03_sg_solver.ipynb",
    "03 · Scharfetter–Gummel Reference Solver",
    "The drift-diffusion oracle that grounds the whole project. We solve a PN "
    "junction under forward bias and extract the I–V characteristic — the "
    "ground truth the surrogate learns to reproduce.",
    [
        code(COMMON),
        md("## Forward-bias I–V (measured dynamic range, ~10 decades)"),
        code('''
biases = np.linspace(0.0, 0.6, 25)
I = sg_iv(step(1e22), biases)
plt.figure(figsize=(5,3.6))
plt.semilogy(biases, np.abs(I), "o-", ms=3)
plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)")
plt.title("PN-junction I–V from Scharfetter–Gummel")
plt.grid(alpha=0.3); plt.tight_layout(); plt.show()
print(f"|J| spans {np.abs(I).min():.2e} → {np.abs(I).max():.2e} A/m²")
'''),
        md("## Ideality factor\n"
           "From the exponential region, $n=\\frac{1}{V_T}\\,dV/d(\\ln J)$ should be ≈1 "
           "for an ideal diffusion-limited diode."),
        code('''
mask = (biases > 0.15) & (biases < 0.45)
lnJ = np.log(np.abs(I[mask]))
slope = np.polyfit(biases[mask], lnJ, 1)[0]
ideality = 1.0/(VT*slope)
print(f"Extracted ideality factor n = {ideality:.3f}")
'''),
    ],
)

# ===========================================================================
# 04 — Forward surrogate (the working forward model)
# ===========================================================================
make_nb(
    "04_forward_surrogate.ipynb",
    "04 · Forward Model — SG-Supervised Surrogate",
    "The forward model. A pure-physics PINN cannot reproduce diode I–V "
    "(the terminal current is a numerically-fragile derived quantity — see "
    "`docs/forward_model_reframe.md`). Instead we train a **differentiable "
    "surrogate** supervised by the SG oracle. Measured on disjoint splits: "
    "**2.8% median relative error interpolating, 38% extrapolating, 84% on "
    "an unseen profile family**, over a 9.96-decade label range "
    "(`outputs/results/results_summary.md`).",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (
    SymlogTransform, Normalizer, IVSurrogate, IVSurrogateConfig,
    build_sg_dataset, train_surrogate, SurrogateEnsemble)
symlog = SymlogTransform(I0=1e-6)
'''),
        md("## Build an SG-labelled dataset and train one surrogate"),
        code('''
train_levels = np.geomspace(5e20, 5e22, 11)
profiles = [step(L) for L in train_levels]
biases = np.linspace(0.0, 0.6, 13)
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog)
norm = Normalizer.fit(X)
net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, seed=0))
hist = train_surrogate(net, X, Y, norm, epochs=2500, lr=2e-3)
print(f"trained {net.num_parameters():,} params, final MSE={hist[-1]:.4f}")
'''),
        md("## Held-out forward accuracy: surrogate vs SG"),
        code('''
ens = SurrogateEnsemble([net], norm, symlog)
test_L = 1.7e21   # not in the training grid
C = step(test_L)
pred = ens.predict(scaling.doping_to_net_input(C), biases/VT)
Isg = sg_iv(C, biases)
plt.figure(figsize=(5,3.6))
plt.semilogy(biases, np.abs(Isg), "o-", label="SG (truth)", ms=4)
plt.semilogy(biases, np.abs(pred.mean_current), "x--", label="Surrogate")
plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)"); plt.legend()
plt.title(f"Held-out N=%.1e: surrogate vs SG" % test_L)
plt.grid(alpha=0.3); plt.tight_layout(); plt.show()
rel = np.abs(pred.mean_current[biases>=0.1]-Isg[biases>=0.1])/np.abs(Isg[biases>=0.1])
print(f"median relative I-V error (V≥0.1): {np.median(rel):.1%}")
'''),
    ],
)

# ===========================================================================
# 05 — Inverse design
# ===========================================================================
make_nb(
    "05_inverse_design.ipynb",
    "05 · Inverse Design — Recover Doping from I–V",
    "Given a measured I–V, recover the doping by gradient descent through the "
    "differentiable surrogate. Because the surrogate is differentiable in the "
    "doping encoding, backprop flows straight to the doping level.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate)
symlog = SymlogTransform(I0=1e-6)
biases = np.linspace(0.0, 0.6, 13)
profiles = [step(L) for L in np.geomspace(5e20, 5e22, 11)]
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog)
norm = Normalizer.fit(X)
net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, seed=0))
train_surrogate(net, X, Y, norm, epochs=2500, lr=2e-3)
'''),
        md("## Recover a held-out doping level\n"
           "Target I–V from SG at an unseen level; optimize $\\log_{10}N$ to match."),
        code('''
half = N_ANCHOR//2
def encode_level(logL):
    C = torch.cat([-(10.0**logL).repeat(half), (10.0**logL).repeat(N_ANCHOR-half)])
    return scaling.doping_to_net_input(C)

true_L = 6e21
target = torch.tensor(symlog.forward(sg_iv(step(true_L), biases)), dtype=torch.float32)
bs = torch.tensor(biases/VT, dtype=torch.float32)
logL = torch.tensor(21.5, requires_grad=True)
opt = torch.optim.Adam([logL], lr=0.05)
traj=[]
for it in range(400):
    opt.zero_grad()
    lat = encode_level(logL)
    feats = torch.stack([torch.cat([lat, bs[i].reshape(1)]) for i in range(len(biases))])
    pred = net((feats-norm.mean)/norm.std).reshape(-1)
    loss = torch.nn.functional.mse_loss(pred, target)
    loss.backward(); opt.step(); logL.data.clamp_(20,23); traj.append(float(logL))
print(f"true log10(N)={np.log10(true_L):.3f}, recovered={float(logL):.3f}, "
      f"error={abs(float(logL)-np.log10(true_L)):.3f} decades")

fig, ax = plt.subplots(1,2, figsize=(9,3.2))
ax[0].plot(traj); ax[0].axhline(np.log10(true_L), ls="--", c="k", label="truth")
ax[0].set_xlabel("iteration"); ax[0].set_ylabel("log10(N)"); ax[0].set_title("Recovery trajectory"); ax[0].legend()
Irec = sg_iv(step(10**float(logL)), biases)
Itrue = sg_iv(step(true_L), biases)
ax[1].semilogy(biases, np.abs(Itrue), "o-", label="target")
ax[1].semilogy(biases, np.abs(Irec), "x--", label="recovered")
ax[1].set_xlabel("Bias (V)"); ax[1].set_ylabel("|J|"); ax[1].set_title("I–V match"); ax[1].legend()
plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 06 — MC Dropout
# ===========================================================================
make_nb(
    "06_mc_dropout.ipynb",
    "06 · Uncertainty I — MC Dropout",
    "Cheapest UQ: train one surrogate with dropout, then sample at test time "
    "with dropout *on*. Spread across stochastic forward passes estimates "
    "predictive uncertainty.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate)
symlog = SymlogTransform(I0=1e-6)
biases = np.linspace(0.0, 0.6, 13)
profiles = [step(L) for L in np.geomspace(5e20, 5e22, 11)]
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog); norm = Normalizer.fit(X)
net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, dropout=0.1, seed=0))
train_surrogate(net, X, Y, norm, epochs=2500, lr=2e-3)
'''),
        md("## Test-time dropout sampling"),
        code('''
def mc_predict(net, latent, biases, T=50):
    net.train()  # keep dropout active
    from bayespinn_inv.surrogate import make_features
    feats = np.stack([make_features(latent, b) for b in biases/VT])
    xb = norm(torch.tensor(feats, dtype=torch.float32))
    with torch.no_grad():
        S = np.stack([net(xb).numpy().ravel() for _ in range(T)])
    return S.mean(0), S.std(0)

C = step(1.7e21); lat = scaling.doping_to_net_input(C)
m_s, sd_s = mc_predict(net, lat, biases, T=100)
mean_I = symlog.inverse(m_s)
lo = symlog.inverse(m_s-2*sd_s); hi = symlog.inverse(m_s+2*sd_s)
Isg = sg_iv(C, biases)
plt.figure(figsize=(5,3.6))
plt.semilogy(biases, np.abs(Isg), "o-", label="SG truth", ms=4)
plt.semilogy(biases, np.abs(mean_I), "--", label="MC-Dropout mean")
plt.fill_between(biases, np.abs(lo), np.abs(hi), alpha=0.25, label="±2σ")
plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)"); plt.legend(); plt.grid(alpha=0.3)
plt.title("MC-Dropout uncertainty"); plt.tight_layout(); plt.show()
print(f"mean symlog σ = {sd_s.mean():.3f}")
'''),
    ],
)

# ===========================================================================
# 07 — Deep ensemble
# ===========================================================================
make_nb(
    "07_deep_ensemble.ipynb",
    "07 · Uncertainty II — Deep Ensemble",
    "Train M surrogates from different seeds/bootstraps; their disagreement is "
    "the predictive uncertainty. Usually better-calibrated than MC-Dropout, "
    "at M× the training cost (still seconds here).",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate, SurrogateEnsemble)
symlog = SymlogTransform(I0=1e-6)
biases = np.linspace(0.0, 0.6, 13)
profiles = [step(L) for L in np.geomspace(5e20, 5e22, 11)]
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog); norm = Normalizer.fit(X)
members=[]
for m in range(5):
    net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, seed=m))
    rs = np.random.RandomState(m); idx = rs.randint(0,len(X),len(X))
    train_surrogate(net, X[idx], Y[idx], norm, epochs=2000, lr=2e-3); members.append(net)
ens = SurrogateEnsemble(members, norm, symlog)
print(f"ensemble of {ens.M}")
'''),
        md("## Ensemble uncertainty band"),
        code('''
C = step(1.7e21); pred = ens.predict(scaling.doping_to_net_input(C), biases/VT)
lo = symlog.inverse(pred.mean_symlog-2*pred.std_symlog)
hi = symlog.inverse(pred.mean_symlog+2*pred.std_symlog)
Isg = sg_iv(C, biases)
plt.figure(figsize=(5,3.6))
plt.semilogy(biases, np.abs(Isg), "o-", label="SG truth", ms=4)
plt.semilogy(biases, np.abs(pred.mean_current), "--", label="ensemble mean")
plt.fill_between(biases, np.abs(lo), np.abs(hi), alpha=0.25, label="±2σ")
plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)"); plt.legend(); plt.grid(alpha=0.3)
plt.title("Deep-ensemble uncertainty"); plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 08 — Active learning
# ===========================================================================
make_nb(
    "08_active_learning.ipynb",
    "08 · Active Learning — Which Biases to Measure",
    "Measurements cost time. Which bias points are most informative for "
    "recovering doping? High-bias points carry more diode signal, so a few "
    "well-chosen biases recover doping nearly as well as a full sweep.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate)
symlog = SymlogTransform(I0=1e-6)
biases = np.linspace(0.0, 0.6, 13)
profiles = [step(L) for L in np.geomspace(5e20, 5e22, 11)]
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog); norm = Normalizer.fit(X)
members=[]
for m in range(5):
    net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128, n_layers=3, seed=m))
    train_surrogate(net, X, Y, norm, epochs=2000, lr=2e-3); members.append(net)
half=N_ANCHOR//2
def encode_level(logL):
    C = torch.cat([-(10.0**logL).repeat(half),(10.0**logL).repeat(N_ANCHOR-half)])
    return scaling.doping_to_net_input(C)
'''),
        md("## Recover doping from bias subsets"),
        code('''
def recover(true_L, idx):
    Isg = sg_iv(step(true_L), biases)
    bs = torch.tensor(biases[idx]/VT, dtype=torch.float32)
    tgt = torch.tensor(symlog.forward(Isg[idx]), dtype=torch.float32)
    recs=[]
    for net in members:
        logL=torch.tensor(21.5, requires_grad=True); opt=torch.optim.Adam([logL],lr=0.05)
        for _ in range(400):
            opt.zero_grad(); lat=encode_level(logL)
            feats=torch.stack([torch.cat([lat,bs[i].reshape(1)]) for i in range(len(idx))])
            loss=torch.nn.functional.mse_loss(net((feats-norm.mean)/norm.std).reshape(-1), tgt)
            loss.backward(); opt.step(); logL.data.clamp_(20,23)
        recs.append(float(logL))
    return np.array(recs)

levels = np.geomspace(8e20, 3e22, 5)
strategies = {"low 3":[0,1,2], "high 3":[10,11,12], "all 13":list(range(13))}
res = {k:[abs(recover(L,idx).mean()-np.log10(L)) for L in levels] for k,idx in strategies.items()}
for k,v in res.items(): print(f"{k:8s}: median recovery error {np.median(v):.3f} decades")
plt.figure(figsize=(5,3.2))
plt.bar(range(len(res)), [np.median(v) for v in res.values()], tick_label=list(res.keys()))
plt.ylabel("median recovery error (decades)"); plt.title("Bias-subset informativeness")
plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 09 — Calibration
# ===========================================================================
make_nb(
    "09_calibration.ipynb",
    "09 · Calibration — Are the Uncertainties Honest?",
    "An uncertainty estimate is only useful if it's calibrated. We measure "
    "interval coverage of the ensemble on held-out I–V, find it **overconfident** "
    "(a known small-ensemble failure), and fix it with temperature scaling.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate, SurrogateEnsemble)
from math import erf, sqrt
symlog = SymlogTransform(I0=1e-6); biases = np.linspace(0.0, 0.6, 13)
profiles=[step(L) for L in np.geomspace(5e20,5e22,11)]
X,Y=build_sg_dataset(profiles,biases,scaling,sg,symlog); norm=Normalizer.fit(X)
members=[]
for m in range(5):
    net=IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR,hidden=128,n_layers=3,seed=m))
    rs=np.random.RandomState(m); idx=rs.randint(0,len(X),len(X))
    train_surrogate(net,X[idx],Y[idx],norm,epochs=2000,lr=2e-3); members.append(net)
ens=SurrogateEnsemble(members,norm,symlog)
def nominal(z): return erf(z/sqrt(2))
'''),
        md("## Coverage before and after recalibration"),
        code('''
def z_scores(levels):
    zs=[]
    for L in levels:
        C=step(L); pred=ens.predict(scaling.doping_to_net_input(C), biases/VT)
        Isg=sg_iv(C,biases)
        for bi,V in enumerate(biases):
            if V<0.1: continue
            s=pred.std_symlog[bi]
            if s>1e-9: zs.append((symlog.forward(Isg[bi])-pred.mean_symlog[bi])/s)
    return np.array(zs)
zv=z_scores(np.geomspace(6e20,4e22,6)); zt=z_scores(np.geomspace(9e20,3e22,6))
T=max(float(np.quantile(np.abs(zv),nominal(1.0))),1e-3)
zlist=[1.0,1.64,2.0]
print(f"temperature T={T:.2f}")
print(f"{'interval':>8} {'raw':>6} {'recal':>6} {'nominal':>8}")
raw=[]; recal=[]; nom=[]
for z in zlist:
    r=float(np.mean(np.abs(zt)<=z)); c=float(np.mean(np.abs(zt)<=z*T)); n=nominal(z)
    raw.append(r); recal.append(c); nom.append(n)
    print(f"±{z:>4}σ {r:6.0%} {c:6.0%} {n:8.0%}")
plt.figure(figsize=(4.2,4))
plt.plot(nom, raw, "o-", label="raw (overconfident)")
plt.plot(nom, recal, "s-", label="recalibrated")
plt.plot([0,1],[0,1],"k--", lw=0.8, label="ideal")
plt.xlabel("nominal coverage"); plt.ylabel("empirical coverage")
plt.legend(); plt.title("Reliability"); plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 10 — Benchmarking
# ===========================================================================
make_nb(
    "10_benchmarking.ipynb",
    "10 · Benchmarking — Accuracy & Speed vs SG",
    "How accurate and how fast is the surrogate relative to the SG oracle "
    "across many profiles? Surrogate inference is orders of magnitude faster, "
    "which is what makes gradient-based inverse design and UQ practical.",
    [
        code(COMMON + '''
import time
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate, SurrogateEnsemble)
symlog=SymlogTransform(I0=1e-6); biases=np.linspace(0.0,0.6,13)
profiles=[step(L) for L in np.geomspace(5e20,5e22,11)]
X,Y=build_sg_dataset(profiles,biases,scaling,sg,symlog); norm=Normalizer.fit(X)
net=IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR,hidden=128,n_layers=3,seed=0))
train_surrogate(net,X,Y,norm,epochs=2500,lr=2e-3); ens=SurrogateEnsemble([net],norm,symlog)
'''),
        md("## Accuracy across held-out profiles + timing"),
        code('''
test=[step(L) for L in np.geomspace(7e20,4e22,8)]
rels=[]
for C in test:
    pred=ens.predict(scaling.doping_to_net_input(C), biases/VT); Isg=sg_iv(C,biases)
    for bi,V in enumerate(biases):
        if V>=0.1: rels.append(abs(pred.mean_current[bi]-Isg[bi])/abs(Isg[bi]))
rels=np.array(rels)
print(f"median rel I-V err: {np.median(rels):.1%}, p90: {np.quantile(rels,0.9):.1%}")

# timing: full I-V curve
t=time.time()
for _ in range(20): sg_iv(step(1e22), biases)
t_sg=(time.time()-t)/20
t=time.time()
for _ in range(20): ens.predict(scaling.doping_to_net_input(step(1e22)), biases/VT)
t_sur=(time.time()-t)/20
print(f"SG: {t_sg*1e3:.1f} ms/curve   Surrogate: {t_sur*1e3:.1f} ms/curve   speedup: {t_sg/t_sur:.0f}×")
plt.figure(figsize=(4,3))
plt.bar(["SG","Surrogate"],[t_sg*1e3,t_sur*1e3]); plt.ylabel("ms / I–V curve"); plt.yscale("log")
plt.title("Forward-eval cost"); plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 11 — Visualization gallery
# ===========================================================================
make_nb(
    "11_visualization.ipynb",
    "11 · Visualization Gallery",
    "Publication-quality figures the project can produce: device-state panels, "
    "I–V with uncertainty, recovered-doping overlays. Suitable for GitHub, "
    "slides, and the paper.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate, SurrogateEnsemble)
symlog=SymlogTransform(I0=1e-6); biases=np.linspace(0.0,0.6,21)
profiles=[step(L) for L in np.geomspace(5e20,5e22,11)]
X,Y=build_sg_dataset(profiles,np.linspace(0,0.6,13),scaling,sg,symlog); norm=Normalizer.fit(X)
members=[IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR,hidden=128,n_layers=3,seed=m)) for m in range(5)]
for m,net in enumerate(members):
    rs=np.random.RandomState(m); idx=rs.randint(0,len(X),len(X)); train_surrogate(net,X[idx],Y[idx],norm,epochs=1500,lr=2e-3)
ens=SurrogateEnsemble(members,norm,symlog)
'''),
        md("## Device-state panel (SG)"),
        code('''
st=sg.solve(anchor_signed_to_grid(step(1e22), sg.grid.N),0.3); x_nm=np.linspace(0,1000,len(st.phi))
fig,ax=plt.subplots(2,2,figsize=(9,6))
ax[0,0].plot(x_nm,st.phi); ax[0,0].set_title("Potential (V)")
ax[0,1].plot(x_nm,-np.gradient(st.phi,x_nm*1e-9)/1e5,c="C1"); ax[0,1].set_title("Field (kV/cm)")
ax[1,0].semilogy(x_nm,np.abs(st.n)+1,label="n"); ax[1,0].semilogy(x_nm,np.abs(st.p)+1,label="p"); ax[1,0].legend(); ax[1,0].set_title("Carriers")
ax[1,1].plot(x_nm, st.doping if hasattr(st,'doping') else np.where(x_nm<500,-1e22,1e22)); ax[1,1].set_title("Doping")
for a in ax.ravel(): a.set_xlabel("x (nm)")
plt.tight_layout(); plt.show()
'''),
        md("## I–V with ensemble uncertainty band"),
        code('''
C=step(1.7e21); pred=ens.predict(scaling.doping_to_net_input(C), biases/VT)
lo=symlog.inverse(pred.mean_symlog-2*pred.std_symlog); hi=symlog.inverse(pred.mean_symlog+2*pred.std_symlog)
Isg=sg_iv(C,biases)
plt.figure(figsize=(5,3.6))
plt.semilogy(biases,np.abs(Isg),"o-",label="SG truth",ms=4)
plt.semilogy(biases,np.abs(pred.mean_current),"--",label="surrogate")
plt.fill_between(biases,np.abs(lo),np.abs(hi),alpha=0.25,label="±2σ")
plt.legend(); plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)"); plt.grid(alpha=0.3)
plt.title("Forward I–V with uncertainty"); plt.tight_layout(); plt.show()
'''),
    ],
)

# ===========================================================================
# 12 — End-to-end demo (the recruiter-facing one)
# ===========================================================================
make_nb(
    "12_demo.ipynb",
    "12 · End-to-End Demo — Forward → Inverse → Uncertainty",
    "**Start here for the 5-minute tour.** A complete, self-contained "
    "demonstration of uncertainty-aware inverse design of semiconductor doping:\n\n"
    "1. **Forward** — a fast SG-supervised surrogate reproduces diode I–V to "
    "2.8% median error *inside* the training band; 38% outside it.\n"
    "2. **Inverse** — recover unknown doping from a measured I–V by gradient "
    "descent through the differentiable surrogate.\n"
    "3. **Uncertainty** — a deep ensemble quantifies confidence, and temperature "
    "scaling makes it calibrated.\n\n"
    "Everything runs in well under a minute on CPU. All numbers are measured "
    "against the Scharfetter–Gummel drift-diffusion solver.",
    [
        code(COMMON + '''
from bayespinn_inv.surrogate import (SymlogTransform, Normalizer, IVSurrogate,
    IVSurrogateConfig, build_sg_dataset, train_surrogate, SurrogateEnsemble)
from math import erf, sqrt
symlog = SymlogTransform(I0=1e-6)
biases = np.linspace(0.0, 0.6, 13)
print("Building SG-labelled training set...")
profiles = [step(L) for L in np.geomspace(5e20, 5e22, 11)]
X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog)
norm = Normalizer.fit(X)
print(f"  {X.shape[0]} (doping,bias) samples")
'''),
        md("### 1 · Forward model — train a 5-member surrogate ensemble (seconds)"),
        code('''
import time; t0=time.time()
members=[]
for m in range(5):
    net=IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR,hidden=128,n_layers=3,seed=m))
    rs=np.random.RandomState(m); idx=rs.randint(0,len(X),len(X))
    train_surrogate(net,X[idx],Y[idx],norm,epochs=2500,lr=2e-3); members.append(net)
ens=SurrogateEnsemble(members,norm,symlog)
print(f"trained {ens.M}×{members[0].num_parameters():,} params in {time.time()-t0:.1f}s")

# forward accuracy on a held-out doping level
C=step(1.7e21); pred=ens.predict(scaling.doping_to_net_input(C), biases/VT); Isg=sg_iv(C,biases)
rel=np.abs(pred.mean_current[biases>=0.1]-Isg[biases>=0.1])/np.abs(Isg[biases>=0.1])
plt.figure(figsize=(5,3.6))
plt.semilogy(biases,np.abs(Isg),"o-",label="SG (ground truth)",ms=5)
plt.semilogy(biases,np.abs(pred.mean_current),"x--",label="surrogate")
plt.fill_between(biases, np.abs(symlog.inverse(pred.mean_symlog-2*pred.std_symlog)),
                 np.abs(symlog.inverse(pred.mean_symlog+2*pred.std_symlog)), alpha=0.2, label="±2σ")
plt.xlabel("Bias (V)"); plt.ylabel("|J| (A/m²)"); plt.legend(); plt.grid(alpha=0.3)
plt.title(f"Forward I–V (held-out): median error {np.median(rel):.1%}")
plt.tight_layout(); plt.show()
print(f"median relative I-V error on this held-out profile: {np.median(rel):.1%}")
'''),
        md("### 2 · Inverse design — recover unknown doping from a measured I–V"),
        code('''
half=N_ANCHOR//2
def encode_level(logL):
    C=torch.cat([-(10.0**logL).repeat(half),(10.0**logL).repeat(N_ANCHOR-half)])
    return scaling.doping_to_net_input(C)

true_L=6e21  # the "unknown" we will recover
target=torch.tensor(symlog.forward(sg_iv(step(true_L),biases)),dtype=torch.float32)
bs=torch.tensor(biases/VT,dtype=torch.float32)
recovered=[]
for net in members:
    logL=torch.tensor(21.5,requires_grad=True); opt=torch.optim.Adam([logL],lr=0.05)
    for _ in range(400):
        opt.zero_grad(); lat=encode_level(logL)
        feats=torch.stack([torch.cat([lat,bs[i].reshape(1)]) for i in range(len(biases))])
        loss=torch.nn.functional.mse_loss(net((feats-norm.mean)/norm.std).reshape(-1),target)
        loss.backward(); opt.step(); logL.data.clamp_(20,23)
    recovered.append(float(logL))
rec=np.array(recovered); truth=np.log10(true_L)
print(f"True doping:      N = {true_L:.2e}  (log10 = {truth:.3f})")
print(f"Recovered (mean): N = {10**rec.mean():.2e}  (log10 = {rec.mean():.3f} ± {rec.std():.3f})")
print(f"Absolute error:   {abs(rec.mean()-truth):.3f} decades")
print(f"Truth within ±1σ ensemble band: {abs(rec.mean()-truth) <= rec.std()+1e-9}")
'''),
        md("### 3 · Uncertainty calibration — and the fix\n"
           "The raw ensemble is *overconfident* (a known small-ensemble effect). "
           "Temperature scaling on a validation split restores calibration."),
        code('''
def nominal(z): return erf(z/sqrt(2))
def z_scores(levels):
    zs=[]
    for L in levels:
        C=step(L); pr=ens.predict(scaling.doping_to_net_input(C),biases/VT); Isg=sg_iv(C,biases)
        for bi,V in enumerate(biases):
            if V<0.1: continue
            s=pr.std_symlog[bi]
            if s>1e-9: zs.append((symlog.forward(Isg[bi])-pr.mean_symlog[bi])/s)
    return np.array(zs)
zv=z_scores(np.geomspace(6e20,4e22,6)); zt=z_scores(np.geomspace(9e20,3e22,6))
T=max(float(np.quantile(np.abs(zv),nominal(1.0))),1e-3)
zlist=[1.0,1.64,2.0]; raw=[np.mean(np.abs(zt)<=z) for z in zlist]
recal=[np.mean(np.abs(zt)<=z*T) for z in zlist]; nom=[nominal(z) for z in zlist]
print(f"temperature T = {T:.2f}")
for z,r,c,n in zip(zlist,raw,recal,nom):
    print(f"  ±{z}σ: raw {r:.0%} → recalibrated {c:.0%}  (nominal {n:.0%})")
plt.figure(figsize=(4.2,4))
plt.plot(nom,raw,"o-",label="raw (overconfident)"); plt.plot(nom,recal,"s-",label="recalibrated")
plt.plot([0,1],[0,1],"k--",lw=0.8,label="ideal")
plt.xlabel("nominal coverage"); plt.ylabel("empirical coverage"); plt.legend()
plt.title("UQ reliability"); plt.tight_layout(); plt.show()
'''),
        md("---\n### Summary\n"
           "In under a minute on CPU we trained a differentiable forward model "
           "that reproduces drift-diffusion I–V to a few percent, used it to "
           "recover unknown doping to ~0.01 decades, and quantified + calibrated "
           "the uncertainty. This is the full uncertainty-aware inverse-design "
           "loop the project set out to build.\n\n"
           "See the other notebooks (`01`–`11`) for each component in depth, and "
           "`docs/forward_model_reframe.md` for why the forward model is an "
           "SG-supervised surrogate rather than a pure-physics PINN."),
    ],
)

print("\nAll notebooks generated.")
