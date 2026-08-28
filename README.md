# BayesPINN-Inv

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests](https://img.shields.io/badge/tests-1051%20collected-brightgreen.svg)
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
| **Identifiability** (***local***, **chart L**) | **Local** identifiability in **chart L** at **d=16** — the rank of the Jacobian at one operating point, over the reachable set of that chart (`log10\|C\|` at 16 anchors, arithmetic interpolation of the signed doping; `bayespinn_inv.inverse.charts`). At the reference point (1 µm Si PN junction, N_A=N_D=1e22 m⁻³, 19 bias points over 0–0.9 V, 2% noise, P=16), I–V determines only **3–4 of 16** doping dof; **1–6 across every tested variation**, median 3, over 88 measurements; **the rank does not grow with the parameterisation** (P=8→32 leaves it at 3–4) | `run_identifiability.py`, `run_identifiability_robustness.py` |
| **Identifiability** (***global***, **chart G**) | **Demonstrated by witness, not inferred.** In **chart G** at **d=4** (geometric interpolation of the magnitude; `bayespinn_inv.inverse.charts`), log-uniform prior 1e21–1e23 m⁻³, 16 biases over 0.15–0.90 V, distinguishability floor **2.0e-02** = max(noise 2.0e-02, solver 1.5e-03): **13 witness pairs** among 1,999,000 examined. Closest differs by **8.18× in doping** yet only **1.23%** in I–V. **13 of 13 refined** under `WIT-02` (`outputs/close/wit02_register_v2.json`); **12 of 13 survive** 4× grid refinement and a tighter tolerance and **1 separates** at the finest grid and is withdrawn. Oracle-arbitrated; the surrogate is never used (ADR-0007) | `run_global_identifiability.py`, `run_wit02_chartG.py` |
| **Surrogate speed** vs SG | **152×** faster per I–V curve (0.85 ms vs 129 ms, M=5 ensemble) | `run_results.py` |
| **Surrogate *gradient* fidelity** | directional derivatives agree with SG **only inside** the identifiable subspace: mean cosine **+0.50 inside vs −0.00 outside**, unchanged by a 33× training-budget increase | `run_gradient_fidelity.py` |
| **UQ backend comparison** | deep ensemble beats tuned MC-dropout and tuned SWAG on every uncertainty axis; σ inflates **21.3×** off-distribution vs 1.4×/2.5× | `run_uq_benchmark.py`, `run_uq_tuning.py` |
| **Bias selection** | information-based design **+0.39** identifiable rank vs random (5 wins/0 losses); the incumbent uncertainty acquisition is **−0.31**, i.e. *worse than random* | `run_experiment_design.py` |
| **Built-in potential** vs analytic | rel. error **7.24e-14** (grid-independent over N=101…601) | `bayespinn selftest` |
| **Test suite** | see the badge at the top, which `tests/test_notebooks.py::TestDocumentedTestCountIsHonest` checks against live collection on every run; incl. 58 solver-numerics, 27 MOS-cap physics and 41 ohmic-gradient tests. The row used to restate the total by hand and had drifted by more than a hundred tests, so it now points at the one number a guard maintains | `make test` |

### Read these caveats before quoting any number above

1. **Extrapolation and family transfer are poor.** The surrogate is accurate
   *inside* the doping band and profile family it was trained on and degrades
   sharply outside both. This is stated because it was measured; earlier
   versions of this table reported only interpolation and called it
   "held-out".
2. **Inverse recovery of a single doping level is the well-posed
   sub-problem.** It is a one-parameter identification against 13 observations,
   not profile recovery.
3. **Profile recovery is ill-posed — locally *and* globally.** The *local*
   result is the numerical rank of the forward Jacobian at one operating point
   in **chart L** at **d=16** (1 µm Si PN junction, N_A=N_D=1e22 m⁻³); the
   *global* result is in **chart G** at **d=4**. The *global* question — whether
   distant parameter sets fit equally well — is no longer open: at d=4 over a
   1e21–1e23 m⁻³ log-uniform prior, a search over 1,999,000 pairs found **13**
   whose I–V curves differ by less than the 2% distinguishability floor, the
   closest differing by **8.18× in doping** for a **1.23%** change in I–V. Of
   those 13, **13 of 13** have been through the refinement battery under
   `WIT-02` and **12 survive** 4× grid refinement and a tighter solver
   tolerance, so those twelve are degeneracies of the device rather than of the
   solver; the thirteenth separates at `N = 1201` and is withdrawn
   ([`docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`](docs/S1_GLOBAL_IDENTIFIABILITY_g6.md),
   [`docs/CLOSE_ADDENDUM.md`](docs/CLOSE_ADDENDUM.md)).
   The two numbers were measured in different **charts** — the local rank in
   **chart L** at d=16, the global contraction in **chart G** at d=4 — and
   neither chart contains the other, so their fractions are over different
   manifolds and are not comparable. Generation 7 measured both charts at both
   dimensions at one operating point and found the spectra agreeing to within 3%
   at matched d (`docs/CHART_RECONCILIATION_g7.md`), which it summarised as *the
   dimension moves the rank and the chart does not*.

   **Generation 8 confined that summary to what it measured and then beat it in
   two directions** ([`docs/G8_RESULT.md`](docs/G8_RESULT.md)). Charts G and L
   differ only in whether the interpolation between anchors is geometric or
   arithmetic; a **third chart** with the junction position as a free continuous
   coordinate — **chart J** — moves the unit-homogeneous part of the spectrum by
   **219%** at one displaced junction and **9.1%** at another, against the 2.8%
   the chart-G-to-chart-L change produces at the same operating point. And
   perturbing the **observation set** alone, in **chart G** at **d=16**, moves it
   by **19.8%** merely by spacing the same 16 biases geometrically instead of
   linearly, and by **97.4%** over a narrowed 0.30–0.60 V range — where the
   *local* rank itself falls from 4 to 2. So the honest statement is that within
   one interpolant family the chart hardly matters, the dimension matters a
   little more, **what you measure matters an order of magnitude more than
   either**, and a genuinely different parameterisation matters most of all. A
   19-point forward-bias I–V sweep at 2% measurement noise determines only 3–4
   of 16 doping degrees of freedom of **chart L** at **d=16** at the reference
   conditions, and 1–6 (median 3)
   across 88 measurements spanning parameterisation dimension, bias count,
   bias range, solver grid, doping level and finite-difference step. **The
   rank does not grow with the parameterisation dimension** — quadrupling the
   number of profile parameters from P=8 to P=32 leaves it at 3–4 — so this is
   a property of the measurement, not of the discretisation. Two devices differing
   by up to 1.26× in local doping, in **chart L** at **d=16**, produce I–V curves
   differing by 0.02–1.3% — indistinguishable at realistic noise. Improving the instrument by four orders of magnitude
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
├── tests/               # 678 tests
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

The forward map is rank-deficient **locally**, and degenerate **globally**.
Locally, in **chart L** at **d=16**, at 2% measurement noise over the reference
observation set of 16 bias points spanning 0.15–0.90 V: at a given operating
point the Jacobian of a terminal I–V sweep determines only 3–4 of 16 of that
chart's doping degrees of freedom, and that number **does not grow when you add
parameters**. It does, however, move with what you measure: the count is
reported as `rank(cutoff)` in `outputs/g8/ranks.json`, and narrowing the same 16
biases to 0.30–0.60 V halves it, from 4 to 2. Globally, in
**chart G** at **d=4**: two profiles differing by **8.18× in doping** produce I–V
curves differing by **1.23%**, below a 2% floor — and that pair survives 4× grid
refinement, so it is the device that cannot tell them apart, not the solver.

The degeneracy is not an artefact of either chart. Generation 7 embedded that
witness pair into **chart L** at **d=16** and it survives: observational distance
1.207e-02 against 1.225e-02 in **chart G**, with the 8.18× separation preserved to
one part in a thousand. Generation 9 walked the likelihood between the two
members of each *global* **chart G** **d=4** witness pair and found a median
barrier of 8.31 log-units against a floor barrier of 8.0, where ordinary prior
pairs sit at 339 or deeper: the witness pairs are a **ridge the instrument
cannot resolve**, not two isolated points.
Generation 10 added the matched-dimension cell that comparison was missing.
**Chart L** at **d=16** is a *basin*, not a ridge — no connecting path below
the floor barrier was found along the straight line for any of its 37 witness
pairs, and the median is 212× the floor — and the same is true of **chart J** at
**d=16**. Both are **search statements against an upper-bound barrier**, not
separation proofs: a curved path can only be shallower, and the minimum-energy
path was not computed (`docs/CLOSE_RULING.md` §4). Neither set satisfies
`WIT-02`: chart L is refined 0 of 37. The ridge is a property of the **dimension**: only
`d = 4` puts witness pairs at the instrument's own floor, and it stays there
after normalising by path length. What the chart moves at matched `d` is the
*depth*: charts L and J have the same path lengths for their witness pairs and
for their null controls, and differ 13× in the ratio between them
([`docs/G10_RESULT.md`](docs/G10_RESULT.md) §2).

**What the local number is most sensitive to is what you measure.** Across
twelve operating points -- four devices crossed with three bias windows --
perturbing the observation set moves the leading spectrum by 92%-108% every
time, while changing the chart, the dimension or the junction position each
swings by more than a factor of twenty and the three trade places depending on
the device and the window. The ranking generation 8 published is
operating-point dependent and is withdrawn as a general claim;
`docs/G9_RESULT.md` has the measurement.

**And it is not a flat direction.** The likelihood along the path between the two
devices, in **chart G** at **d=4**, is **bimodal** — two isolated maxima at the
endpoints, separated by a barrier **242 log-units** deep, with only 5 of 61 path
points inside the 2% floor, against a control along the most observable direction
that is 43.7× deeper and has no second mode. Three things follow, and they are
what this project is actually about.

1. **The degeneracy is a discrete set of isolated equivalent devices, not a
   continuum.** A flat direction is a manifold of indistinguishable devices; this
   is several distinct devices, each locally well determined, that produce the
   same measurement.
2. **The *local* and *global* results never disagreed.** A local Jacobian
   spectrum is *structurally incapable* of detecting a second mode 8–15× away in
   doping — it is a derivative at a point. The two analyses measure different
   things and one of them cannot see the phenomenon in principle. That, not the
   chart and not the dimension, is the reconciliation; the chart work
   (`docs/CHART_RECONCILIATION_g7.md`, [`docs/G8_RESULT.md`](docs/G8_RESULT.md))
   is what had to happen before it could be seen.
3. **Gradient-based inversion cannot cross a 242-log-unit barrier.** It converges
   to whichever basin it was initialised in and reports a well-conditioned local
   spectrum while doing so — high apparent confidence, wrong device. Every
   inverse-design method that reports a *local* uncertainty inherits this.

And it is not only the doping magnitudes. Generation 8 added a **chart J** whose
extra coordinate is the junction position, searched it *globally* at **d=16**, and
found **13 witness pairs** among 719,400
examined, **13 of 13 refined** under `WIT-02` with 7 surviving `N = 301 → 1201`. The widest puts the metallurgical junction at **694 nm** in one
device and **271 nm** in the other — **423 nm apart in a 1000 nm
device** — with an I–V difference below the 2% floor. Terminal I–V cannot locate
the junction either, once the doping is free to compensate
([`docs/G8_RESULT.md`](docs/G8_RESULT.md) §2).

**Every witness count on this page is admissible under `WIT-01`.** A pair whose
qualifying separation the reconstruction cannot carry is not a witness, and
generation 10 applies that to the counts rather than assuming it of them: 13 of
the 13 in **chart G** at **d=4**, 37 of the 37 in **chart L** at **d=16**, and 13
of the 13 in **chart J** at **d=16** are admissible — an admissibility ratio of
**1.000** in all three, because every pair qualifies on a doping *magnitude* and
magnitudes reach the solver grid exactly. The rule removes nothing here, and that
is a measurement rather than an assumption. What it does catch is one reported
*quantity*: a chart-J pair whose junctions sit **0.425 nm** apart on a **3.333 nm**
grid, a difference the representation does not resolve, withdrawn as a junction
separation ([`docs/G10_RESULT.md`](docs/G10_RESULT.md) §3,
`outputs/g10/wit01.json`).

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
make test                          # 678 tests; timings in LOOP_STATE_v5.json
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
| 3 | Profile recovery from terminal I–V is ill-posed **locally and globally**. Locally, in **chart L** at **d=16**: 3–4 of 16 dof identifiable at 2% noise at the reference point. Globally, in **chart G** at **d=4**: 13 witness pairs (up to **8.18×** apart in doping, **1.23%** apart in I–V) found by search. The two fractions are over different charts and are not comparable; at matched d the rank is the same in both charts (`docs/CHART_RECONCILIATION_g7.md`), but that invariance holds only within the one interpolant family those two charts span — a third chart with a free junction, and the observation set, both move the spectrum far more ([`docs/G8_RESULT.md`](docs/G8_RESULT.md)). | Local Jacobian rank stress-tested across six axes plus a bootstrap; global witnesses found by oracle-arbitrated search over 1,999,000 pairs, of which **13 of 13 refined** under `WIT-02` and **12 of 13 survive** 4× grid refinement. ADR-0007. |
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
