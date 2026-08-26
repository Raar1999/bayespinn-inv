# Novelty Audit

Purpose: decide, against the literature rather than against enthusiasm, what
this repository can honestly claim as a contribution. The rule applied
throughout is that implementing something does not make it novel.

**Headline conclusion: this project's defensible contribution is a systems,
validation and reproducibility contribution, not a new method.** The prior-art
review below found established literature for every methodological idea the
project contains, including the identifiability analysis added during this
audit. Claims in the README and paper draft have been rewritten accordingly.

**Second cycle (§6) reaffirms this**, adds prior-art checks for the two new
results, and *withdraws* one previously-neutral claim: the project's
uncertainty-driven acquisition is not merely no better than random, it is
measurably worse for inverse identifiability.

---

## 1. Prior-art review

### 1.1 Inverse doping profile recovery from terminal measurements

This is a **mature, well-studied problem with a dedicated literature**, not an
open one.

| Work | What it establishes |
|---|---|
| Burger, Engl, Leitão, Markowich, *Identification of doping profiles in semiconductor devices*, **Inverse Problems 17, 1765–1795 (2001)** | The canonical formulation of doping identification in the stationary drift–diffusion system; identifiability and ill-posedness results. |
| Burger, Engl, Markowich, Pietra, *Inverse Doping Problems for Semiconductor Devices* (Springer, 2002) | Framework for inverse doping problems under different measurement types. |
| Burger, Engl, Leitão, Markowich, *On inverse problems for semiconductor equations*, **Milan J. Math. 72, 273–314 (2004)** | Voltage–current-map measurements reduce, in special cases, to a classical inverse conductivity problem; uniqueness and non-uniqueness results for regularized solutions. |
| Bayesian inversion for the identification of the doping profile in unipolar semiconductor devices, arXiv:2408.11485 (2024) | Bayesian/posterior treatment of exactly this inverse problem. |
| Data-driven solutions of ill-posed inverse problems arising from doping reconstruction in semiconductors, *Applied Mathematics in Science and Engineering* (2024) | Machine-learning surrogates applied to doping reconstruction. |
| Problem-specific inverse methods for 2D doping determination from C–V measurements, *Solid-State Electronics* (1991); inverse device modelling for 1D/2D doping profiling, *Solid-State Electronics* (1990) | Inverse device modelling for doping extraction predates the ML literature by three decades. |

**Consequence.** "Recovering doping from I–V is ill-posed" is a *known result*,
not a finding. Singular-value analysis of the doping-to-measurement map also
already appears in this literature.

### 1.2 The other components

| Component | Prior art | Verdict |
|---|---|---|
| PINNs for PDEs | Raissi, Perdikaris & Karniadakis, *JCP* 378 (2019) | Standard. |
| Fourier features / NTK loss balancing | Wang, Sankaran & Perdikaris, *CMAME* 384 (2021); *JCP* 449 (2022) | Standard; used as cited. |
| Deep ensembles for UQ | Lakshminarayanan et al., NeurIPS 2017 | Standard. |
| MC-Dropout | Gal & Ghahramani, ICML 2016 | Standard. |
| SWAG | Maddox et al., NeurIPS 2019 | Standard. |
| Regression calibration / temperature scaling | Kuleshov, Fenner & Ermon, ICML 2018; Guo et al., ICML 2017 | Standard. |
| Scharfetter–Gummel discretisation | Scharfetter & Gummel (1969); De Mari (1968) | Textbook. |
| Local identifiability via Jacobian SVD | Aster, Borchers & Thurber, *Parameter Estimation and Inverse Problems*, 3rd ed., ch. 4 | Textbook method. |
| Surrogate-based TCAD modelling | Widespread in industry and literature | Standard practice. |

**No component of this project is methodologically new.**

---

## 2. Candidate contributions, assessed

| # | Candidate | Prior work | Gap | Experimental test | Result | Novelty confidence |
|---|---|---|---|---|---|---|
| C1 | "Bayesian PINN inverse design of semiconductor devices" | Every ingredient is standard; the inverse problem is Burger et al.'s | Combination only | — | Combination of known methods | **None.** Do not claim. |
| C2 | Identifiability analysis of the I–V → doping map | Burger et al. 2001/2004 establish ill-posedness; SVD analysis exists in the literature | The specific *quantitative* spectrum for these device families is not published, but the method and the qualitative conclusion are known | `scripts/run_identifiability.py`, `run_identifiability_robustness.py` | Measured, *locally*, in **chart L** at **d=16**, at a 2% noise cutoff: 3–4 of 16 dof at the reference conditions; 1–6 (median 3) across 88 measurements; invariant to parameterisation dimension. At d=16 the cutoff does not sit in a population gap, so this is a threshold count and never a bare integer (`docs/G8_RESULT.md` §4) | **Low as method. Moderate as a measured, reproducible artefact.** |
| C3 | Solver-noise-floor-aware sensitivity analysis | Finite-difference step selection against numerical noise is classical (Gill et al., *Practical Optimization*); "don't difference below solver precision" is standard numerical-analysis advice | Making the solver *report* its own per-solve noise floor, and using that to set the differencing threshold and to reject bias points automatically, is an engineering integration not usually packaged | Documented failure and fix in `docs/AUDIT_MASTER.md` BUG-04 / this file §3 | Concrete demonstration that ignoring it manufactures a plausible but entirely fake spectrum | **Low–moderate. A methodological caution worth publishing as such, not as a new method.** |
| C4 | Uncertainty-aware active *inverse* design loop | Active learning + BO + inverse design are all standard; §1.1 shows Bayesian inversion for this exact problem exists | Would be a combination | Not implemented | The existing "active learning" result (§SCI-02) turned out not to be active learning at all | **None. Rejected** — would have been a buzzword contribution with no measurable gain. |
| C5 | The SG oracle self-reporting its trustworthy range | Error estimation for PDE solvers is a large field | Using `div(J)=0` as a free, assumption-free per-solve error bar on the terminal current is simple and, in this codebase, load-bearing | `DeviceState.current_noise_floor`; validated in §3 | Predicts the solver's actual relative precision to within a factor ~2 | **Low as novelty, high as engineering value.** |

---

## 3. What was actually validated (and one instructive failure)

The identifiability analysis is included because it is *measured and
self-checking*, not because it is new. Three validations accompany it, and the
second exists because the first version of the analysis was **wrong**:

1. **Analysis-convergence study.** The Jacobian is re-estimated across
   finite-difference steps (0.01 → 0.05 decades) and oracle SNR thresholds
   (1e4 → 1e8). The identifiable rank stabilises at 4 and the spectral shape
   (σ₁/σ₂ = 6.11–6.13) is invariant. A conclusion that moved under estimator
   refinement would be an artefact.

2. **The failure that motivated the spectral floor.** The first version used a
   1e-3-decade step and accepted any bias point with SNR > 10. It produced a
   clean-looking spectrum decaying over six orders of magnitude and an
   "identifiable rank of 6". It was **entirely noise**: an independent
   re-solve showed the measured response along the *exact null space* was the
   same size as along the most observable direction. The oracle's relative
   precision is ≈1/SNR, so a row with SNR = 10 carries 10% error, and
   differencing it yields noise rather than a derivative. The module now
   estimates its own per-entry noise from the solver's reported floor and
   refuses to report singular values below the induced spectral floor
   (Weyl bound). *This is the single most transferable lesson in this audit:
   an SVD will always hand back a plausible spectrum, including from pure
   noise.*

3. **Linear-response validation.** For each resolved direction, the predicted
   response ‖J v‖ is compared against an independent re-solve of the perturbed
   device. Measured ratios across all four device families: **0.995–1.04** for
   the leading directions.

### Measured result

Forward-bias I–V sweep (0–0.9 V), 16 profile nodes, 2% relative measurement
noise, Jacobian through the Scharfetter–Gummel solver:

| Device | Bias points used | Identifiable dof (of 16) |
|---|---|---|
| step, symmetric (1e22 / 1e22) | 10 | **4** |
| step, asymmetric (1e21 / 5e22) | 11 | **5** |
| graded (tanh, L_g = 150 nm) | 10 | **3** |
| LDD (three-segment) | 8 | **4** |

Rank versus instrument quality (symmetric step): 2 dof at 20% noise, 4 at 2%,
6 at 0.1%, 9 at 1e-4%. **Four orders of magnitude of instrument improvement
buys roughly a doubling** — the limit is the structure of the forward map, not
the noise.

**Equivalence twins.** For every family, a doping profile differing by up to
1.26× locally produces an I–V change of 0.02%–1.3% — below a 2% measurement
noise floor. Two physically distinct devices, one measurement.

---

## 4. What this project should claim

**Claim (defensible):**

> An open, tested, reproducible implementation of an SG-supervised
> differentiable forward surrogate for 1D drift–diffusion, together with a
> validated numerical oracle that reports its own trustworthy range, and a
> self-checking identifiability analysis that quantifies how many doping
> degrees of freedom terminal I–V can determine for four device families.

**Do NOT claim:**

- "First to evaluate Bayesian PINN calibration for semiconductor inverse
  problems" — unsupported; Bayesian inversion for this exact problem is
  published (arXiv:2408.11485), and no systematic search was done to establish
  first-ness. *Removed from the paper draft.*
- Novelty for the identifiability analysis as a *method* — Burger et al.
  (2001, 2004) and standard SVD inverse theory precede it.
- That the project demonstrates active learning helps — it does not currently
  demonstrate active learning at all (AUDIT_MASTER SCI-02).
- Any claim of "the first to combine X and Y" without a differentiating,
  measurable benefit.

**Honest framing for a workshop submission:** a reproducibility-and-validation
paper. Its interest is that a carefully audited pipeline overturned four of its
own published claims and two documented "physics limitations" that were
actually solver bugs (AUDIT_MASTER BUG-07, BUG-10). That is a real and
publishable message for an ML-for-science venue, and it does not require
inventing a method.

---

## 5. Citation integrity

`inverse/inverse_design.py` cited *Beucler et al., "Constraining neural networks
for the inverse design of semiconductor devices" (2022)* as the source of the
TV + positivity regularization scheme. **This citation could not be verified.**
Beucler et al.'s known work concerns enforcing analytic constraints in neural
networks emulating *physical/climate* systems, not semiconductor inverse
design, and no paper with the cited title was located. The citation has been
removed and replaced with the actual provenance of the scheme (total-variation
regularization is standard for piecewise-constant recovery — Rudin, Osher &
Fatemi 1992 — and its use in the doping context traces to the Burger et al.
line of work).

The co-cited Chen et al., *Opt. Express* **28**, 11618 (2020), is genuine and
retained.

---

---

## 6. Second-cycle reassessment (2026-08-19)

The first assessment concluded "no methodological novelty; the contribution is
systems, validation and reproducibility". That conclusion **stands**. This
section records what the second cycle measured, what prior art it was checked
against, and the one candidate whose framing is arguably differentiated.

### 6.1 Prior art searched this cycle

| Work | Bearing on this project |
|---|---|
| Yu, Cai & Liu (2026), *Physical Sensitivity Kernels Can Emerge in Data-Driven Forward Models: Evidence From Surface-Wave Dispersion*, [arXiv:2604.04107](https://arxiv.org/abs/2604.04107) | **Closest prior art to C6 below.** Compares autodiff gradients of a neural surrogate against theoretical sensitivity kernels and finds the surrogate *does* recover the main depth-dependent structure, with the caveat that structure in the training data injects systematic artefacts into the inferred sensitivities. It does **not** relate gradient fidelity to the identifiable subspace or the singular-value spectrum, and does not run an undertraining control. |
| *Sequential design for surrogate modeling in Bayesian inverse problems*, [arXiv:2402.16520](https://arxiv.org/html/2402.16520) | Goal-oriented sequential design (IP-SUR, CSQ) for GP surrogates in Bayesian inverse problems. Also notes that plain D-optimal design ignores the posterior and can spend budget in low-posterior regions. |
| *Efficient D-optimal design of experiments for infinite-dimensional Bayesian linear inverse problems*, [arXiv:1711.05878](https://arxiv.org/pdf/1711.05878); *Goal-Oriented OED for Large-Scale Bayesian Linear Inverse Problems*, [arXiv:1802.06517](https://arxiv.org/pdf/1802.06517) | D-/A-optimal design for exactly this class of problem is established and scaled. |
| Fedorov, *Theory of Optimal Experiments* (1972); Atkinson & Donev, *Optimum Experimental Designs* (1992) | The design criteria used in `active_learning/design.py` are textbook. |

### 6.2 Candidates assessed

| # | Candidate | Prior work | Gap | Experimental test | Result | Novelty confidence |
|---|---|---|---|---|---|---|
| C6 | **Gradient fidelity is bounded by the identifiable subspace** — a surrogate that fits I–V to 2.6% has directional derivatives that agree with the true Jacobian *only* inside the identifiable subspace, and no amount of training changes that | arXiv:2604.04107 compares surrogate gradients to true kernels in a different domain and reaches a more optimistic conclusion; ill-posedness and null spaces are classical | Using the **identifiability spectrum as a predictor of where a learned surrogate's gradients are trustworthy**, direction by direction, with a control that excludes undertraining | `scripts/run_gradient_fidelity.py` | mean cosine **+0.504 inside** vs **−0.001 outside** over 4 device families; outside-agreement flat (+0.003 → −0.001) across a 33× training-budget increase while value error fell 4.5× | **Low as method; moderate as a diagnostic framing and a measured result.** The mechanism is not surprising once stated — that is a point in its favour, not against it, but it is not a new method. |
| C7 | Identifiability-aware experiment design for this inverse problem | Extensive: Fedorov; Atkinson & Donev; arXiv:1711.05878, 1802.06517, 2402.16520 | None methodologically | `scripts/run_experiment_design.py` | `d_optimal`/`null_space` **+0.39** mean rank vs random (5 wins, 0 losses / 20); the project's own `max_std` is **−0.31** (2 wins, 9 losses) | **None as method.** The value is the *negative* result about uncertainty acquisition, not the positive one about D-optimality. |
| C8 | Three UQ backends compared under one protocol on an SG-supervised surrogate | Deep ensembles, MC-dropout, SWAG all standard; comparisons of them are a genre | None methodologically | `run_uq_benchmark.py` + `run_uq_tuning.py` | Ensemble wins on every uncertainty axis after a fair hyperparameter search; mechanism identified (σ inflates 21.3× vs 1.4×/2.5× under a 12–13× error inflation) | **None as method; a clean, mechanistically explained benchmark result.** |

### 6.3 What changed in the claim

The first cycle's headline claim is extended by one clause, and one prior
claim is **withdrawn**:

**Claim (defensible), revised:**

> An open, tested, reproducible implementation of an SG-supervised
> differentiable forward surrogate for 1D drift–diffusion, together with a
> validated numerical oracle that reports its own trustworthy range; a
> self-checking identifiability analysis that quantifies how many doping
> degrees of freedom terminal I–V can determine, shown to be a property of the
> measurement rather than of the parameterisation; and the accompanying
> observation that the surrogate's *gradients* inherit that limit — they are
> accurate inside the identifiable subspace and uninformative outside it,
> irrespective of training budget.

**Withdrawn:** the framing that the project's active learning is a neutral
result. It is not neutral. `max_std` acquisition is **worse than random** for
inverse identifiability (DES-01). The README and paper draft say so.

### 6.4 The rule applied

Both C7 and C8 were implemented and both produced usable results, and neither
is claimed as novel — implementing something does not make it new. C6 is
reported as a *finding with a mechanism and a control*, and its closest prior
art is cited and characterised, including the fact that it reaches a more
optimistic conclusion in a different domain. If a reviewer judges C6 a
restatement of known ill-posedness theory, that judgement is compatible with
everything claimed here: the value is that it is measured, on a real device
problem, with the alternative explanation excluded.

## Sources

- [Identification of doping profiles in semiconductor devices — Inverse Problems 17, 1765 (2001)](https://iopscience.iop.org/article/10.1088/0266-5611/17/6/315)
- [On inverse problems for semiconductor equations — Milan J. Math. 72, 273 (2004)](https://link.springer.com/article/10.1007/s00032-004-0025-6)
- [Inverse Doping Problems for Semiconductor Devices (Springer)](https://link.springer.com/chapter/10.1007/978-1-4615-0113-8_3)
- [Inverse problems for semiconductors: models and methods](https://link.springer.com/chapter/10.1007/978-0-8176-4554-0_6)
- [Bayesian inversion for the identification of the doping profile in unipolar semiconductor devices (arXiv:2408.11485)](https://arxiv.org/html/2408.11485)
- [Data-driven solutions of ill-posed inverse problems arising from doping reconstruction in semiconductors](https://www.tandfonline.com/doi/full/10.1080/27690911.2024.2323626)
- [A problem-specific inverse method for two-dimensional doping profile determination from C–V measurements](https://www.sciencedirect.com/science/article/abs/pii/003811019190090L)
- [Physical parameter extraction by inverse device modelling: 1D and 2D doping profiling](https://www.sciencedirect.com/science/article/abs/pii/003811019090190P)
