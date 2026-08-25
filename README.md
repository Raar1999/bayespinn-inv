# BayesPINN-Inv

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-400%20passing-brightgreen.svg)
![Status](https://img.shields.io/badge/status-research-blueviolet.svg)

**Uncertainty-aware inverse design of semiconductor devices from terminal I–V,
built on a validated drift–diffusion reference solver.**

A research codebase combining (i) a Scharfetter–Gummel finite-volume solver for
the steady-state drift–diffusion system that **reports its own numerical
trustworthy range**, (ii) an SG-supervised differentiable forward surrogate for
terminal current, (iii) Bayesian UQ via deep ensembles (MC-dropout and SWAG are
implemented and benchmarked, and lose — ADR-0005), and (iv) a measured
identifiability analysis of the inverse problem.

> **On the name.** Despite `bayespinn`, the working forward model is **not** a
> pure-physics PINN. That model was measured at **100% median relative error** —
> it converges to a smooth, self-consistent, current-free solution — and is
> retained only as legacy infrastructure and a documented negative result
> ([ADR-0004](docs/adr/ADR-0004-pure-physics-pinn-is-legacy.md)). The forward
> model is a Scharfetter–Gummel-supervised differentiable surrogate.

> **What this project claims — and does not.** Every methodological component
> here is standard, and inverse doping recovery is a mature field
> (Burger, Engl, Leitão & Markowich, *Inverse Problems* **17**, 1765, 2001). The
> contribution is a validated, reproducible implementation plus a quantitative
> identifiability result — not a new method. See
> [`docs/NOVELTY_AUDIT.md`](docs/NOVELTY_AUDIT.md).

---

## Results at a glance

All numbers are measured against the Scharfetter–Gummel oracle and regenerated
by `scripts/run_results.py`, which writes a `manifest.json` recording the git
commit, environment and configuration. Every statistic carries `n` and a 95%
interval.

| Capability | Result | Reproduce with |
|---|---|---|
| **Forward I–V, interpolation** | **2.8% median** rel. error (95% CI 2.0–3.9%, n=72), p90 7.0% | `run_results.py` |
| **Forward I–V, extrapolation** | **38% median** (23–90%, n=68), p90 **860%** — outside the training doping band | `run_results.py` |
| **Forward I–V, family transfer** | **84% median** (75–106%, n=60) — graded profiles, trained on steps only | `run_results.py` |
| **Current dynamic range** | **9.96 decades** measured (8.9e-5 → 8.1e5 A/m²) | `run_results.py` |
| **Inverse recovery** (single level, well-posed) | **0.0018 decades** at 0% noise → 0.0072 at 10% noise (n=40 each) | `run_results.py` |
| **UQ calibration** | ±1.64σ coverage 46% → **90%** after variance inflation T=2.09 (nominal 90%, n=140, same test set) | `run_results.py` |
| **Is the uncertainty useful?** | Spearman ρ(σ, \|error\|) = **+0.82** (n=200); σ inflates **15.7×** on extrapolation while error inflates 11.8× | `run_results.py` |
| **Identifiability** (***local***) | **Local** identifiability — the rank of the Jacobian at one operating point, *not* a global result. At the reference point (1 µm Si PN junction, N_A=N_D=1e22 m⁻³, 19 bias points over 0–0.9 V, 2% noise, P=16), I–V determines only **3–4 of 16** doping dof; **1–6 across every tested variation**, median 3, over 88 measurements; **the rank does not grow with the parameterisation** (P=8→32 leaves it at 3–4). Global, sampling-based non-identifiability is **unmeasured** | `run_identifiability.py`, `run_identifiability_robustness.py` |
| **Surrogate speed** vs SG | **152×** faster per I–V curve (0.85 ms vs 129 ms, M=5 ensemble) | `run_results.py` |
| **Surrogate *gradient* fidelity** | directional derivatives agree with SG **only inside** the identifiable subspace: mean cosine **+0.50 inside vs −0.00 outside**, unchanged by a 33× training-budget increase | `run_gradient_fidelity.py` |
| **UQ backend comparison** | deep ensemble beats tuned MC-dropout and tuned SWAG on every uncertainty axis; σ inflates **21.3×** off-distribution vs 1.4×/2.5× | `run_uq_benchmark.py`, `run_uq_tuning.py` |
| **Bias selection** | information-based design **+0.39** identifiable rank vs random (5 wins/0 losses); the incumbent uncertainty acquisition is **−0.31**, i.e. *worse than random* | `run_experiment_design.py` |
| **Built-in potential** vs analytic | rel. error **7.24e-14** (grid-independent over N=101…601) | `bayespinn selftest` |
| **Test suite** | **400 passing**, incl. 58 solver-numerics, 27 MOS-cap physics and 41 ohmic-gradient tests | `make test` |

### Read these caveats before quoting any number above

1. **Extrapolation and family transfer are poor.** The surrogate is accurate
   *inside* the doping band and profile family it was trained on and degrades
   sharply outside both. This is stated because it was measured; earlier
   versions of this table reported only interpolation and called it
   "held-out".
2. **Inverse recovery of a single doping level is the well-posed
   sub-problem.** It is a one-parameter identification against 13 observations,
   not profile recovery.
3. **Profile recovery is ill-posed, and now quantified — *locally*.** This is a
   **local** identifiability result: the numerical rank of the forward
   Jacobian at one operating point (1 µm Si PN junction, N_A=N_D=1e22 m⁻³).
   Global, sampling-based non-identifiability has **not** been measured, and
   nothing here rules out distant parameter sets that fit equally well. A
   19-point forward-bias I–V sweep at 2% measurement noise determines only 3–4
   of 16 doping degrees of freedom at the reference conditions, and 1–6 (median 3)
   across 88 measurements spanning parameterisation dimension, bias count,
   bias range, solver grid, doping level and finite-difference step. **The
   rank does not grow with the parameterisation dimension** — quadrupling the
   number of profile parameters from P=8 to P=32 leaves it at 3–4 — so this is
   a property of the measurement, not of the discretisation. Two devices differing by up to 1.26× in local
   doping produce I–V curves differing by 0.02–1.3% — indistinguishable at
   realistic noise. Improving the instrument by four orders of magnitude
   roughly doubles the identifiable rank; the limit is the *structure* of the
   forward map, not the noise.
4. **Uncertainty-driven acquisition is *worse* than random bias selection.**
   Earlier versions of this README said "no distinguishable advantage". Measured
   properly (4 device families × 5 budgets × 12 seeds, scored on identifiable
   rank), `max_std` scores **−0.31** rank versus random and loses 9 of 20
   comparisons. Information-based design (`d_optimal`, `null_space`) scores
   **+0.39** and never loses. Predictive uncertainty asks "where is the forward
   model unsure?"; the inverse problem needs "which measurement constrains a
   direction I cannot see?" — different questions.
5. **The uncertainty is informative but over-conservative out of
   distribution.** ρ(σ, |error|) = +0.82, but the error is *not* strictly
   monotone across σ quartiles (medians 0.008, 0.031, 0.373, 0.254): on the
   unseen graded family the ensemble reports σ = 0.67 against an actual error
   of 0.27. It errs toward caution, which is the safe direction, but σ should
   not be read as a calibrated error estimate outside the training
   distribution.
6. **ECE from a small ensemble has a floor.** A *perfectly* calibrated 5-member
   ensemble scores ECE ≈ 0.088 under this estimator
   (`calibration.metrics.ece_floor_for_ensemble`). Do not read small ECE
   differences at M=5 as calibration quality.

### Audit

This repository underwent a full adversarial engineering, physics, ML and
reproducibility audit. It recorded **40 findings**, including **12 numerical
defects** in the solvers — three of which silently produced wrong physics while
the 42-test suite passed — and it retired two documented "physics limitations"
that turned out to be solver bugs. Fourteen previously published claims were
corrected or withdrawn. The complete ledger, with evidence and a regression
test for each finding, is [`docs/AUDIT_MASTER.md`](docs/AUDIT_MASTER.md); the
claim-by-claim trace is
[`docs/CLAIM_EVIDENCE_MATRIX.md`](docs/CLAIM_EVIDENCE_MATRIX.md).

---

## Table of contents

1. [Results at a glance](#results-at-a-glance)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [Repository layout](#repository-layout)
5. [Scientific approach](#scientific-approach)
6. [Reproducing the experiments](#reproducing-the-experiments)
7. [Known limitations](#known-limitations)
8. [Citation](#citation)
9. [License](#license)

---

## Installation

```bash
git clone https://github.com/Raar1999/bayespinn-inv
cd bayespinn-inv

pip install -e .              # core (CPU)
pip install -e ".[all]"       # + dev tools, scikit-learn, Hydra
```

Python 3.9+, PyTorch 2.0+. Verify the install reproduces known physics:

```bash
bayespinn selftest
```

```
[PASS] built-in potential  0.714317 V vs analytic 0.714317 V  (rel 2.76e-07)
[PASS] mass action n p = n_i^2  max deviation 7.61e-06
[PASS] equilibrium solve converged
[PASS] equilibrium current correctly flagged as below the noise floor
[PASS] diode ideality factor  1.0184  (expected ~1)
[PASS] I(V) monotonically increasing
SELF-TEST: PASS
```

Other subcommands: `bayespinn info` (version, git commit, environment — put
this in bug reports), `bayespinn iv`, `bayespinn identifiability`.

## Quick start

```python
import numpy as np, torch
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    ScharfetterGummel1D, Grid1D, SGConfig,
)

scaling = Scaling.for_material(SILICON, T=300.0)
L_s  = scaling.x_to_scaled(torch.tensor(1e-6)).item()
grid = Grid1D.uniform(L_s, 301)
sg   = ScharfetterGummel1D(grid, scaling, SILICON, SGConfig())

x = scaling.x_to_si(np.asarray(grid.x))
N_A = N_D = 1e22                                  # m^-3
doping = np.where(x < x.max() / 2, -N_A, N_D)     # P on the left

state = sg.solve(doping, bias=0.0)
print(f"V_bi = {state.phi[-1] - state.phi[0]:.4f} V "
      f"(analytic {scaling.V_T * np.log(N_A*N_D/SILICON.n_i**2):.4f} V)")

# Bias sweep. `bias > 0` is FORWARD bias for this P-left/N-right junction.
prev = None
for V in np.linspace(0.0, 0.6, 13):
    s = sg.solve(doping, float(V), initial_state=prev)
    prev = s
    # ALWAYS check these two before using a current:
    #   .converged                -- did the Gummel iteration actually converge?
    #   .current_is_trustworthy() -- is |I| above the solver's own noise floor?
    flag = "ok" if (s.converged and s.current_is_trustworthy()) else "UNTRUSTED"
    print(f"V={V:.2f}  I={s.terminal_current: .6e} A/m^2  "
          f"floor={s.current_noise_floor:.2e}  {flag}")
```

`terminal_current` is `mean(Jn + Jp)`. Near zero bias the true current falls
below any finite-precision drift–diffusion solve; `current_is_trustworthy()`
is the honest boundary and returns `False` there.

## Repository layout

```
bayespinn-inv/
├── src/bayespinn_inv/
│   ├── physics/         # constants (CODATA/Sze), De Mari scaling
│   ├── solvers/         # Scharfetter-Gummel 1D; 2D MOS-cap Poisson
│   ├── surrogate/       # SG-supervised current head + ensemble + adapters
│   ├── inverse/         # input-space autodiff design; identifiability analysis
│   ├── bayesian/        # DeepEnsemble, MC-Dropout, SWAG
│   ├── calibration/     # ECE, CRPS, reliability, temperature scaling
│   ├── active_learning/ # random / max-std / GP-UCB acquisition
│   ├── pinn/            # network, physics losses, forward-PINN wrapper
│   ├── utils/           # run provenance / manifests
│   └── cli.py           # `bayespinn` console entry point
├── scripts/             # experiment launchers (repo tools, need configs/)
├── tests/               # 400 tests
├── docs/                # audit ledger, novelty audit, ADRs, release readiness
└── outputs/             # generated results + manifests
```

## Scientific approach

### Physical model

Steady-state drift–diffusion in SI units, with `E = -∇φ`:

$$
\nabla\!\cdot(\varepsilon\nabla\phi) = -q\,(p - n + C),\qquad
\nabla\!\cdot J_n = q R,\qquad \nabla\!\cdot J_p = -q R
$$

$$
J_n = q\mu_n\!\left(nE + \tfrac{k_BT}{q}\nabla n\right),\qquad
J_p = q\mu_p\!\left(pE - \tfrac{k_BT}{q}\nabla p\right)
$$

with SRH recombination $R=(np-n_i^2)/[\tau_p(n+n_1)+\tau_n(p+p_1)]$ and ohmic
Dirichlet contacts. **De Mari scaling** throughout: $L^*=L_D$, $\phi^*=V_T$,
$n^*=n_i$, $J^*=qn_i\mu^*V_T/L_D$.

### The reference solver, and how far to trust it

Scharfetter–Gummel exponential fitting on a finite-volume mesh, Gummel-decoupled
with a damped Newton solve of the nonlinear Poisson equation. Three properties
matter for everything downstream:

- **The continuity systems are equilibrated before solution.** The matrix
  inherits the 12-decade carrier dynamic range; without two-sided ∞-norm
  scaling the minority carrier is wrong by ~1%. Equilibration improves the
  equilibrium mass-action law by **1730×** (ADR-0001).
- **Convergence is tested on carriers, not just the potential.** φ settles
  within three sweeps while the carriers are still 1% off, so a `max|Δφ|` test
  reports success on a state whose continuity residual equals the entire
  current scale.
- **The solver reports its own error bar.** In steady state `div(Jn+Jp)=0`
  exactly, so `J_total` must be constant across the device; the observed spread
  is `current_noise_floor`, an assumption-free estimate of the numerical error
  on the terminal current. It is *predictive*: the current's relative precision
  tracks `1/SNR` across five decades (ADR-0002).
- **Round-off stagnation is distinguished from divergence.** A *relative*
  carrier tolerance is unsatisfiable for entries many decades below the array
  maximum; treating that as failure aborted bias continuation and returned
  cold-start currents wrong by 3–5 decades above 1e24 m⁻³ (BUG-13). The two
  populations are separated by eleven orders of magnitude in the measured
  data, so the discriminator is not a tuned constant.

### The result that ties the project together

The forward map is **locally** rank-deficient: at a given operating point, the
Jacobian of a terminal I–V sweep determines only 3–4 of 16 doping degrees of
freedom, and that number **does not grow when you add parameters** — it is a
property of the measurement. "Locally" is not a hedge: the rank is measured at
one operating point, and global non-identifiability is unmeasured.

A surrogate trained only on that measurement is therefore constrained only in
that subspace. Its *values* can be excellent while its *derivatives* along the
other 12–13 directions are unconstrained. Measured: mean cosine between the
surrogate's and the solver's directional derivatives is **+0.50 inside** the
identifiable subspace and **−0.00 outside**, and a 33× larger training budget
cuts the value error 4.5× without moving the outside number at all.

That has teeth, because the surrogate's whole purpose is to be differentiable.
Gradient-based inverse design and Jacobian-based experiment design consume
exactly those derivatives — which is also why picking the next measurement by
*predictive uncertainty* is worse than random here, while picking it by
*information* is better.

### Forward model

The terminal current is a **directly SG-supervised head**
`(doping_latent, scaled_bias) → symlog(I)`, not a quantity derived from PINN
field gradients — the derived route is dominated by multiscale cancellation and
does not reproduce diode I–V. See
[`docs/forward_model_reframe.md`](docs/forward_model_reframe.md). Physics
residuals remain available as regularizers on the field outputs.

Because the current head is what the inverse problem actually uses, calling the
whole system a "PINN" would overstate the role of physics in it. The forward
model is a physics-supervised surrogate.

### Inverse design and identifiability

Doping is recovered by autodiff through the frozen differentiable surrogate,
under TV / smoothness / solubility regularization, with three
parameterizations (free pointwise, step junction, erf-graded).

`inverse/identifiability.py` measures *how much of the profile the data can
determine at all*, by taking the SVD of the forward Jacobian
$\partial\,\mathrm{symlog}\,I(V)/\partial \log_{10}|C|$ computed through the SG
solver. The analysis is self-limiting in three ways: it estimates its own
finite-difference noise and refuses to report singular values below the induced
spectral floor; it re-derives the conclusion across finite-difference steps and
oracle SNR thresholds; and it validates the predicted response `‖Jv‖` against an
independent re-solve (measured ratios 0.995–1.04).

## Reproducing the experiments

```bash
make test                          # 400 tests, ~1 min 15 s
make selftest                      # physics self-check of the installed package
make check-install                 # build a wheel, install clean, test there

make results                       # H1-H5 headline table            (~25 min)
make identifiability               # the identifiability spectrum     (~6 min)
make identifiability-robustness    # 88 measurements, 6 axes + bootstrap (~35 min)
make uq-benchmark                  # ensemble vs MC-dropout vs SWAG   (~3 min)
make uq-tuning                     # ... after a fair hyperparam search (~10 min)
make experiment-design             # information- vs uncertainty-driven design
make gradient-fidelity             # where the surrogate gradients are usable
make pinn-vs-surrogate             # the ADR-0004 evidence            (~4 min)
make notebooks                     # regenerate the twelve notebooks
```

Each writes `manifest.json` alongside its results recording the git commit,
whether the working tree was dirty, library versions, hardware, seed and full
configuration — so any number can be traced to what produced it.

## Known limitations

| # | Limitation | Status |
|---|---|---|
| 1 | Terminal-current noise floor ~2e-6 A/m² near equilibrium; the true current there is zero and the oracle cannot resolve it. | Measured and reported per solve. Removing it needs a quasi-Fermi reformulation (ADR-0002). |
| 2 | The surrogate extrapolates poorly outside its training doping band (38% median error) and does not transfer to unseen profile families (84%). | Measured; the honest operating envelope. |
| 3 | Profile recovery from terminal I–V is ***locally*** ill-posed: 3–4 of 16 dof identifiable at 2% noise at the reference operating point (1–6, median 3, across all tested conditions). | **Local** Jacobian rank, quantified and stress-tested across six axes plus a bootstrap; invariant to parameterisation dimension. Global identifiability is unmeasured. |
| 4 | Uncertainty-driven bias acquisition is **worse** than random for inverse identifiability (−0.31 rank, 9 losses / 20). | Measured negative result; information-based design (+0.39) is the working alternative. AUDIT_MASTER DES-01. |
| 4b | The surrogate's **gradients** are usable only inside the identifiable subspace (mean cosine +0.50 inside, −0.00 outside) — and more training does not fix it. | Measured; this bounds gradient-based inverse design and any Jacobian-based experiment design. AUDIT_MASTER GRAD-01. |
| 4c | The pure-physics PINN does not work as a forward model (100% median relative error). | Retained as legacy + a documented negative result. ADR-0004. |
| 4d | MC-dropout and SWAG are implemented but not competitive here; their σ barely responds to distribution shift. | Benchmarked after a fair hyperparameter search. ADR-0005. |
| 5 | 2D MOS-cap solves Poisson only — no continuity equations, hence no current. | Scoped out. |
| 6 | Boltzmann statistics; degenerate doping (>~5e25 m⁻³) out of range. | `carrier_clipping_active` flags saturation per solve. |
| 7 | No interface traps, no quantum confinement, constant mobility. | Documented; mobility hook exists, unimplemented. |
| 8 | Gummel is not unconditionally convergent at high injection. | Automatic bias continuation added; `converged` is honest when it still fails. |
| 9 | Above ~1e24 m⁻³ at low forward bias the terminal current falls below the solver's own numerical floor and is *not* grid-converged. | Flagged automatically by `current_is_trustworthy()`; never used as a label. Found while fixing BUG-13. |

## Citation

```bibtex
@misc{bayespinn-inv-2026,
  title  = {{BayesPINN-Inv}: A Validated Drift--Diffusion Reference Solver and
            Identifiability Analysis for Inverse Semiconductor Design},
  author = {BayesPINN-Inv Contributors},
  year   = {2026},
  note   = {Research code; see docs/NOVELTY_AUDIT.md for scope of claims},
}
```

## License

MIT — see [LICENSE](LICENSE).
