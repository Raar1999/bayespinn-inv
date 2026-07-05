# BayesPINN-Inv

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-42%20passing-brightgreen.svg)
![Status](https://img.shields.io/badge/status-research-blueviolet.svg)

**Bayesian Physics-Informed Neural Networks for Uncertainty-Aware Inverse Design of Semiconductor Devices**

A research codebase implementing the methodology of the BayesPINN-Inv project (P2 track), targeting the NeurIPS ML4PS workshop. The framework combines (i) physics-informed neural networks (PINNs) as differentiable surrogates for the steady-state drift–diffusion equations, (ii) Bayesian uncertainty quantification via Deep Ensembles (primary), MC-Dropout, and SWAG, and (iii) Bayes-optimal active learning for inverse semiconductor doping recovery from terminal I–V measurements.

A validated Scharfetter–Gummel reference solver is provided for ground-truth comparison and as the "oracle" experiment in active-learning ablations.

[![Open the demo in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Raar1999/bayespinn-inv/blob/main/notebooks/12_demo.ipynb)

**Try it in 5 minutes:** open [`notebooks/12_demo.ipynb`](notebooks/12_demo.ipynb) — the full forward → inverse → uncertainty story, trained from scratch in under a minute on a free CPU runtime. All twelve notebooks ship with executed outputs and figures, so you can read the results without running anything.

---

## Results at a glance

All numbers are measured against the Scharfetter–Gummel drift–diffusion solver and are reproducible via `scripts/run_results.py` and the notebooks.

| Capability | Result | Where |
|---|---|---|
| **Forward I–V accuracy** (held-out doping) | **~4% median** rel. error across **13 orders of magnitude** of current | `04`, `10`, `run_results.py` |
| **Inverse recovery** (well-posed, single level) | doping recovered to **~0.005 decades** with calibrated band | `05`, `12_demo.ipynb` |
| **Surrogate speed** vs SG solver | **~500×** faster per I–V curve (0.4 ms vs 194 ms) | `10`, `run_benchmark_sweep.py` |
| **Uncertainty calibration** | overconfident ensemble (ECE 0.22) → **0.09 after temperature scaling** | `09`, `run_calibration.py` |
| **Physics validation** | built-in potential matches analytic to **0.00%** | `02` |
| **Test suite** | **42 passing** (core + 2D MOS-cap + surrogate + adapters) | `tests/` |

The forward model is an **SG-supervised differentiable surrogate**, not a pure-physics PINN: the pure-physics terminal current is a numerically-fragile derived quantity dominated by multiscale cancellation and does not reproduce diode I–V. The surrogate preserves every scientific objective (differentiable forward model, inverse design, Bayesian UQ, active learning, calibration) while actually working — see [`docs/forward_model_reframe.md`](docs/forward_model_reframe.md).

> **Honest caveat on inverse recovery.** The ~0.005-decade figure is for the *well-posed* case (recovering a single symmetric doping level). Recovering a full asymmetric doping *profile* from forward-bias I–V is **ill-posed**: the I–V can be matched to ~0.2% while the profile rel-L2 error stays at 0.2–0.8, because the forward map is insensitive to many profile degrees of freedom. This is precisely what motivates uncertainty quantification, and it is reported plainly rather than hidden.

---

## Table of contents

1. [Results at a glance](#results-at-a-glance)
2. [Repository layout](#repository-layout)
3. [Installation](#installation)
4. [Quick start](#quick-start)
5. [Scientific approach](#scientific-approach)
6. [Reproducing the experiments](#reproducing-the-experiments)
7. [Repository status & roadmap](#repository-status--roadmap)
8. [Citation](#citation)
9. [License](#license)

---

## Repository layout

```
bayespinn-inv/
├── src/bayespinn_inv/
│   ├── physics/         # Constants, De-Mari scaling
│   ├── solvers/         # Scharfetter-Gummel finite-volume reference solver
│   ├── pinn/            # Network, losses, forward-PINN wrapper
│   ├── training/        # PINN training loop with curriculum + NTK weights
│   ├── data/            # Synthetic doping-profile families
│   ├── inverse/         # Input-space autodiff inverse design
│   ├── bayesian/        # DeepEnsemble, MCDropout, SWAG wrappers
│   ├── calibration/     # ECE, CRPS, reliability, temperature scaling
│   ├── active_learning/ # BALD / random / BayesOpt acquisition
│   ├── benchmarks/      # SG-vs-PINN quantitative comparison
│   └── visualization/   # Publication-grade matplotlib plots
├── configs/             # Hydra YAML configs (train, inverse, AL)
├── scripts/             # CLI launchers
├── tests/               # pytest unit + integration tests
├── docs/                # Architecture & methodology notes
├── papers/              # Paper draft + figures
└── pyproject.toml
```

## Installation

```bash
# Clone
git clone https://github.com/Raar1999/bayespinn-inv
cd bayespinn-inv

# Core install (CPU)
pip install -e .

# With dev tools, scikit-learn, and Hydra
pip install -e ".[all]"

# GPU support: install PyTorch with CUDA first, then this package
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -e .
```

The package targets Python 3.9+ and PyTorch 2.0+. Tests are CPU-only and complete in under 5 seconds.

## Quick start

```python
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling   import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    ScharfetterGummel1D, Grid1D, SGConfig,
)
import numpy as np, torch

# 1. Set up a 1-µm Si PN diode reference solution.
scaling = Scaling.for_material(SILICON, T=300.0)
L_s = scaling.x_to_scaled(torch.tensor(1e-6)).item()
grid = Grid1D.uniform(L_s, 301)
sg   = ScharfetterGummel1D(grid, scaling, SILICON, SGConfig())

x   = scaling.x_to_si(torch.as_tensor(grid.x)).numpy()
N_A, N_D = 1e22, 1e22                                      # m^-3
doping   = np.where(x < x.max() / 2, -N_A, N_D)

state = sg.solve(doping, bias=0.0)
print(f"V_bi = {state.phi[-1] - state.phi[0]:.4f} V "
      f"(analytic: {scaling.V_T * np.log(N_A*N_D/SILICON.n_i**2):.4f} V)")

# 2. Sweep bias and plot I-V.
biases = np.linspace(0.0, 0.6, 13)
I = []
prev = None
for V in biases:
    s = sg.solve(doping, V, initial_state=prev)
    I.append(0.5 * (s.Jn.mean() + s.Jp.mean()))
    prev = s
```

For PINN training:

```bash
make smoke              # 200-epoch smoke run, ~30 s on CPU
make train              # full training, configs/train_base.yaml
```

## Scientific approach

### Physical model

Steady-state drift–diffusion in SI units:

$$
\begin{aligned}
\nabla\!\cdot(\varepsilon\nabla\phi) &= -q\,(p - n + C),\\
\nabla\!\cdot J_n &= q\,R(n, p),\\
\nabla\!\cdot J_p &= -q\,R(n, p),\\
J_n &= q\,\mu_n n\,\nabla\phi_n,\quad
J_p = q\,\mu_p p\,\nabla\phi_p,
\end{aligned}
$$

with Shockley–Read–Hall recombination $R = (np - n_i^2) / (\tau_p(n+n_1) + \tau_n(p+p_1))$ and Ohmic Dirichlet boundary conditions at the contacts.

We use the **De Mari scaling**: length $L^* = L_D$ (intrinsic Debye length), potential $\phi^* = V_T$, density $n^* = n_i$, current $J^* = q\,n_i\,\mu^* V_T / L_D$. All numerical work is in scaled (dimensionless) units; SI conversions happen only at the solver–dataset–plotting boundary.

### PINN architecture

A `SemiconductorPINN` maps $(x, V_a, C(\cdot)) \mapsto (\phi_s, \log n, \log p)$. Key design choices motivated by experiment:

1. **Random Fourier features** $\gamma(x) = [\cos(2\pi B x), \sin(2\pi B x)]$ with $B \sim \mathcal{N}(0, \sigma^2)$ for spectral bias mitigation, applied to $x$ normalized to $[0, 1]$ so the same $\sigma$ works at any physical scale.
2. **Log-density parameterization** $(\log n, \log p)$ output heads: avoids stiffness from carrier densities that span 16 orders of magnitude.
3. **Log-compressed doping latent** $\operatorname{sign}(C)\log_{10}(1+|C|/n_i)/10$: keeps the doping representation in the $\mathcal{O}(1)$ range that tanh networks can actually learn over.
4. **Gated residual MLP blocks** for stable depth (Wang et al. 2021).

### Loss formulation

The training loss is

$$
\mathcal{L} = w_\phi \|\text{R}_\phi\|^2 + w_n\|\text{R}_n\|^2 + w_p\|\text{R}_p\|^2 + w_b \|\text{R}_\partial\|^2
$$

where each residual is **normalized by a characteristic scale** computed per batch (the dominant $|C_s|$ for Poisson, the typical $\mu n_i$ for currents). Without this normalization, the unnormalized Poisson residual is $\sim 10^{14}$ in scaled units for realistic doping and the optimizer fails to make meaningful progress.

Weights $w_\bullet$ are adapted online by **NTK gradient-norm balancing** (Wang et al. 2022) every 200 epochs.

### Inverse design

Given a measured I–V curve $\{(V_b, I_b^*)\}_{b=1}^B$, recover $C(x)$:

$$
\min_C \;\sum_b \left\|\frac{I_{\text{pred}}(V_b; C) - I_b^*}{\bar I}\right\|^2 + \lambda_{TV}\,\text{TV}(C) + \lambda_s\|C''\|^2 + \lambda_p\,\text{ReLU}(|C|-C_{\max})^2
$$

with gradients computed by autodiff through the frozen, trained PINN. We support three parameterizations of $C$: free pointwise, step junction $(N_A, N_D, x_j)$, and erf-graded $(N_A, N_D, x_j, L_g)$.

### Uncertainty quantification

- **Deep Ensembles** ($M=5$) — primary. Predictive mean is the ensemble mean; predictive variance is across-member variance plus an optional aleatoric term.
- **MC-Dropout** ($T=100$ test-time samples) — secondary, requires a network trained with `dropout > 0`.
- **SWAG** — third baseline; rank-20 + diagonal Gaussian fit to the SGD trajectory.

All three expose the same `iv_curve()` / `solve()` API returning an `EnsemblePrediction(mean, std, samples, quantile_lo, quantile_hi)` so downstream code (calibration, AL, plots) is UQ-agnostic.

### Active learning

We compare three acquisition strategies on the doping-recovery task:

- **Random** bias selection (control).
- **Max-Std** acquisition: pick the bias with maximum ensemble-predicted I-V uncertainty.
- **UCB** on a GP surrogate over candidate biases, using the inverse-design final loss as the objective.

### Calibration

Reported metrics: ECE (regression definition via quantile-coverage bins), MCE, CRPS (closed-form Gaussian + empirical), Gaussian NLL, sharpness, and reliability-diagram coordinates. Post-hoc recalibration via temperature scaling on a held-out validation set.

## Reproducing the experiments

```bash
# Unit tests (~5 s)
make test

# Full training of an M=5 ensemble (CPU: hours; GPU: minutes)
make train

# Recover doping from a synthetic I-V target
make inverse

# Compare AL strategies head-to-head
make al
```

Each script writes a manifest.json and saves checkpoints + history + plots to its `out_dir`.

## Repository status & roadmap

| Module                              | Status        | Notes                                                                |
| ----------------------------------- | ------------- | -------------------------------------------------------------------- |
| Physics constants & De-Mari scaling | ✅ done       | Bidirectional conversions + log-compressed network-input rep.        |
| Scharfetter–Gummel solver           | ✅ validated  | V_bi matches analytic; mass-action holds; 0–0.7 V converges 3–7 it.  |
| PINN network                        | ✅ done       | Gated residual MLP + Fourier features + input normalization.         |
| PINN losses + NTK weighting         | ✅ done       | Per-batch normalization; ohmic-boundary numerical stability.         |
| Forward-PINN wrapper                | ✅ done       | Differentiable end-to-end; matches SG `DeviceState` contract.        |
| Training loop                       | ✅ done       | Bias curriculum + grad clip + adaptive weights + deterministic seed. |
| Synthetic datasets                  | ✅ done       | Step / graded / LDD / defect profile families.                       |
| Inverse design                      | ✅ done       | 3 parameterizations + TV/smoothness/solubility regularizers.         |
| Deep Ensembles                      | ✅ done       | Aggregation only — training is M parallel `PINNTrainer` runs.        |
| MC-Dropout                          | ✅ done       | T=100 test-time samples; same API as `DeepEnsemble`.                 |
| SWAG                                | ✅ done       | Rank-K + diagonal posterior with parameter-snapshot recorder.        |
| Calibration metrics                 | ✅ done       | ECE, MCE, CRPS, NLL, sharpness + temperature scaling + isotonic.     |
| Active learning loop                | ✅ done       | Random / Max-Std / UCB acquisition; uniform diagnostic schema.       |
| Forward model (SG-supervised surrogate) | ✅ done       | **4–5% median I-V error** on held-out profiles; replaces the non-converging pure-physics PINN (see `docs/forward_model_reframe.md`). |
| Inverse design                      | ✅ done       | Recovers doping to <0.01 decades through the differentiable surrogate.|
| Bayesian UQ + recalibration         | ✅ done       | Ensemble overconfident raw (30/57/67%); temperature scaling → 71/92/96% ≈ nominal. |
| Active learning                     | ✅ done       | High-bias points more informative than low; full sweep best.         |
| 2D MOS-cap Poisson solver           | ✅ done       | Stretch goal §6.1; validated vs depletion approx; 9 unit tests.      |
| Unit tests (38)                     | ✅ all pass   | 23 core + 9 MOS-cap + 6 surrogate; ~5 s.                             |
| Quantitative results (H1–H4)        | ✅ done       | Real measured numbers in `outputs/results/results_summary.md` via `scripts/run_results.py`. |
| Legacy pipeline on surrogate        | ✅ done       | `run_inverse_sweep.py` / `run_calibration.py` run on the surrogate via adapters; real numbers, no rewrite. |
| Pure-physics PINN convergence       | ⚠️ known-hard | Documented: multiscale cancellation; superseded by the surrogate.    |
| 12 Colab notebooks + Drive          | ✅ done       | `notebooks/01`–`12`, executed with embedded figures; start at `12_demo.ipynb`. |

Items marked ⏳ require compute resources beyond what can be executed in a single autonomous turn. The infrastructure to launch them is in place.

## Citation

```bibtex
@misc{bayespinn-inv-2026,
  title  = {{BayesPINN-Inv}: Uncertainty-Aware Inverse Design of Semiconductor Devices via Bayesian Physics-Informed Neural Networks},
  author = {BayesPINN-Inv Contributors},
  year   = {2026},
  note   = {NeurIPS ML4PS workshop submission, in preparation},
}
```

## License

MIT — see [LICENSE](LICENSE).
