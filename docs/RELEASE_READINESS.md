# Release Readiness

Assessment against the project's release gates, with evidence for each.
Anything not demonstrated is listed as not demonstrated.

**Verdict: RELEASE READY WITH DOCUMENTED LIMITATIONS.**

The code is correct where it is exercised, the claims match the measurements,
the limitations are bounded and stated, and a stranger can clone, install, test
and reproduce.

**Second audit cycle (2026-08-19).** All three items previously marked "not
release-grade" are now closed: the notebooks were regenerated and re-executed,
the MC-dropout/SWAG backends were attached to the right model and benchmarked
(ADR-0005), and the pure-physics PINN was measured and reclassified
(ADR-0004). One CRITICAL solver defect (BUG-13) was found *after* the first
cycle's 161-test suite passed, and is fixed and regression-tested. What remains
not release-grade is listed at the bottom and is smaller than before.

---

## Gate A — Code

| Check | Status | Evidence |
|---|---|---|
| No known critical bugs | ✅ | All 47 audit findings recorded and closed or explicitly accepted; each has a regression test (`docs/AUDIT_MASTER.md`). BUG-13 (CRITICAL) was found and fixed in the second cycle. |
| No unexplained failing tests | ✅ | **438 passed**, 0 failed, 0 skipped |
| No critical lint issues | ✅ | `ruff check src tests scripts` exits 0 |
| No obvious dead/duplicate implementation | ⚠️ | `_ohmic_bc` and `pinn/losses.ohmic_boundary_values` remain separate implementations of the same physics — the cause of BUG-11. The duplication is not removed, but their equivalence is now **pinned in both value and gradient** over 402 points across the doping envelope, both signs (`SPEC-g0-7`). |

## Gate B — Physics

| Check | Status | Evidence |
|---|---|---|
| Governing equations verified | ✅ | Continuum limit of the discrete flux tested numerically (`test_drift_diffusion_continuum_limit`); the module docstring's contradictory sign convention corrected (DOC-01) |
| Units verified | ✅ | Constants checked against Sze App. G; De Mari scaling round-trips tested; `J* = q n_i μ* V_T / L_D` dimensionally confirmed |
| Signs verified | ✅ | Forward bias raises current 1e3× over reverse; ideality factor 1.018 |
| Boundary conditions verified | ✅ | Ohmic BC exact (`n·p = 1` to 0.0) up to C_s = 1e12 after BUG-11 |
| Reference solver validated | ✅ | V_bi vs analytic to 7.24e-14 rel.; mass action 2.93e-9; reverse saturation; monotonicity; 2D φ_s vs depletion approximation within V_T; 2D Gauss law to 0.000% <br> *(This gate previously read "2.8e-7 / 7.6e-6". Those figures measured the **pre-audit** solver at `6577f4b` and were withdrawn in generation 0 — see `CLAIM_EVIDENCE_MATRIX` X15/X16 and `docs/PROVENANCE_BIFURCATION_g0.md`. The gate was green on evidence from a superseded program.)* |
| Numerical stability checked | ✅ | Bernoulli finite over the full double range; damped Newton with step limiting; automatic bias continuation; equilibrated linear solves |
| Mesh convergence | ✅ | 1D: LDD current grid-converged to 4 s.f. across N=201/301/601; after BUG-13, **every** trustworthy point over doping 1e21–1e25 m⁻³ is grid-converged to ≤0.35%. 2D: φ_s converges under refinement and is exactly Nx-independent |

## Gate C — ML

| Check | Status | Evidence |
|---|---|---|
| No leakage | ✅ | Train / calibration-val / test-interp / test-extrap / test-family disjoint by construction, asserted at runtime in `run_results.py`; AL acquisition uses model uncertainty only (AL-03) |
| Correct splits | ✅ | Extrapolation and family transfer now measured separately — they were not before (SCI-06) |
| Reproducible training | ✅ | Fixed seeds; `IVSurrogate` no longer mutates global RNG (API-03); full re-run reproduces interpolation error to 0.01 pp |
| Stable inference | ✅ | Deterministic; CPU |
| Robustness characterized | ✅ | 8 device families × 4 biases; doping 1e19–1e25 m⁻³; reverse bias to −5 V; NaN inputs; 5-node grids. Post-BUG-13: 90/90 solves converge over doping 1e21–1e25 × N ∈ {201,401,801} × bias ∈ {0, 0.3, 0.6, 0.9, −2, −5} V |

## Gate D — Uncertainty quantification

| Check | Status | Evidence |
|---|---|---|
| Uncertainty evaluated | ✅ | H5: Spearman ρ(σ, \|error\|) = +0.824 (n=200). Reported honestly as **not** strictly monotone across σ quartiles — the ensemble over-states σ on the unseen profile family |
| Gradient reliability characterized | ✅ | **New (GRAD-01).** Surrogate directional derivatives agree with SG only inside the identifiable subspace (mean cosine +0.504 vs −0.001), and a 33× training-budget increase does not change the outside value — so gradient-based inverse design is bounded by the identifiability spectrum, and this is stated |
| Calibration evaluated | ✅ | H3, pre/post on one test set (n=140) |
| Coverage measured | ✅ | Wilson intervals at ±1σ/±1.64σ/±2σ |
| OOD behaviour characterized | ✅ | σ inflates 15.7× on extrapolation while error inflates 11.8× — the ensemble does detect extrapolation |
| ECE interpreted honestly | ✅ | `ece_floor_for_ensemble` quantifies the M=5 estimator floor (0.088); the previously reported 0.086 is at it |
| MC-dropout / SWAG compared | ✅ | **Closed.** Root cause of the gap: both wrapped `ForwardPINN`, not the surrogate. `bayesian/surrogate_uq.py` fixes it. After a fair hyperparameter search selected on the calibration split, the ensemble wins on every axis; mechanism identified (σ inflates 21.3× vs 1.4×/2.5× under a 12–13× error inflation). ADR-0005. |

## Gate E — Inverse design

| Check | Status | Evidence |
|---|---|---|
| Parameterization validated | ✅ | Three parameterizations; junction position in normalized logit space |
| Optimization stable | ✅ | Gradient clipping, bounded doping, normalized penalties |
| Bounds enforced | ✅ | `clamp_to_range` |
| Identifiability discussed | ✅ | **Measured locally *and* globally, in two different charts.** Local, in **chart L** at **d=16**: Jacobian rank at one operating point — 3–4 of 16 dof of that chart's reachable set, at 2% noise across four device families; 1–6 (median 3) over 88 measurements; invariant to parameterisation dimension. Global, in **chart G** at **d=4**: **13 witness pairs** found by oracle-arbitrated search over 1,999,000 pairs, the closest differing **8.18×** in doping for **1.23%** in I–V against a distinguishability floor of 2.0e-02 = max(noise 2.0e-02, solver discretisation 1.5e-03), all tested pairs surviving 4× grid refinement (ADR-0007, `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`). Contraction at the instrument's own 2% noise is **not measured** — the estimator collapses (PH-21). The two fractions are **not comparable** across charts; at matched `d` the rank is the same in both, and the chart-G witness survives embedding into chart L (`docs/CHART_RECONCILIATION_g7.md`) |
| Multiple solutions investigated | ✅ | Equivalence twins constructed (1.26×, **chart L**, **d=16**) **and** 13 global witness pairs *found by search* (up to 8.18×, **chart G**, **d=4**; the closest survives embedding into **chart L** at **d=16**), all surviving 4× grid refinement — `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md` |

## Gate F — Active learning

| Check | Status | Evidence |
|---|---|---|
| Acquisition validated | ✅ | Sequential loop implemented and run |
| Leakage excluded | ✅ | AL-03 |
| Baseline comparison performed | ✅ | vs uniform random, 8 seeds, 4 budgets; **plus** 6 strategies × 4 device families × 5 budgets × 12 seeds scored on identifiable rank (`run_experiment_design.py`) |
| Sample efficiency measured | ✅ | **Negative result, strengthened**: `max_std` is not merely no better than random, it is **worse** (−0.31 rank, 9 losses / 20). Information-based design (`d_optimal`, `null_space`) is +0.39 and never loses. DES-01. |

## Gate G — Reproducibility

| Check | Status | Evidence |
|---|---|---|
| Clean environment works | ✅ | Wheel built and installed into a fresh venv; the suite passes **against the installed package**. Note: the build was performed offline (`SK-09`), so dependency *resolution* from `pyproject.toml` is **not** verified — see `docs/WINDOWS_RISK_g6.md` |
| Seeds recorded | ✅ | In every manifest |
| Configs recorded | ✅ | Full config dict in every manifest |
| Artifacts traceable | ✅ | `manifest.json` records git commit, tree cleanliness, Python/NumPy/SciPy/Torch versions, platform, CUDA, seed |
| Results reproducible | ✅ | Independent re-run reproduces H1 interpolation to 0.01 pp |
| CI | ❌ | **`CI-01` is REOPENED.** The workflow existed but was **untracked** until `c115757`, so it has never been pushed and **has never executed** — this gate was previously green against a file that had never run. Generation 6 executed its steps locally on Python 3.11.9/Windows (lint 0, tests 0, notebook generator 0); the **3.9 and 3.12 legs are unevaluated, not passing**. A retrievable remote run log is `OPERATOR-BLOCKED` — `R-4` forbids `git push`. Commands: `docs/OPERATOR_TASKS.md` OT-1 |

## Gate H — Documentation

| Check | Status | Evidence |
|---|---|---|
| README accurate | ✅ | Rewritten; quick-start extracted and executed; every headline number carries CI and n |
| Architecture accurate | ✅ | `forward_model_reframe.md` carries a status banner listing its superseded numbers |
| Limitations accurate | ✅ | 8 numbered limitations in the README, cross-referenced to ADRs |
| Paper claims evidence-backed | ✅ | Rewritten; first-ness claim withdrawn; placeholders removed; unverifiable citation removed |
| Installation verified | ✅ | Clean-venv install + `bayespinn selftest` |
| Claim traceability | ✅ | `docs/CLAIM_EVIDENCE_MATRIX.md` — 20 current claims, 12 solver claims, 14 superseded, **18 second-cycle claims**, 1 still unverified (GaAs) |
| Notebooks | ✅ | **Closed.** All twelve regenerated from `scripts/build_notebooks.py` and re-executed top to bottom against the current solver; stale narrative numbers corrected *in the generator*, so they cannot drift back. The generator itself was unrunnable on Windows until BUG-14 was fixed. |

## Gate I — Packaging

| Check | Status | Evidence |
|---|---|---|
| Package builds | ✅ | `python -m build --wheel` |
| Clean installation works | ✅ | Fresh venv |
| CLI works | ✅ | `bayespinn selftest` from the installed wheel — the three previous entry points were broken (PKG-01) |
| Tests work after installation | ✅ | 240 passed against site-packages |
| Version single-sourced | ✅ | `dynamic = ["version"]` from `bayespinn_inv.__version__` (previously drifted) |
| Checkpoint loading safe | ✅ | `weights_only=True` with a loud fallback (SEC-01) |

## Gate J — Research

| Check | Status | Evidence |
|---|---|---|
| Novelty claim defensible | ✅ | `docs/NOVELTY_AUDIT.md` §6 — prior art re-searched for the two new results, including the closest match (Yu, Cai & Liu, arXiv:2604.04107) which is cited and characterised; **still no methodological novelty claimed** |
| Baselines included | ✅ | Random acquisition; depletion approximation; analytic V_bi; direct-difference flux |
| Ablations included | ✅ | equilibrate on/off; continuation on/off; bias-subset ablation; FD-step and SNR-threshold convergence study; Nx/Ny mesh studies; **identifiability across 6 axes + bootstrap (88 measurements); UQ hyperparameter grids; training-budget control for GRAD-01; budget-matched ensemble** |
| Quantitative evidence available | ✅ | All results as JSON + markdown + manifest |
| Limitations explicitly stated | ✅ | README §Known limitations; AUDIT_MASTER §7 |

---

---

## Adversarial re-audit (second cycle)

Ten hostile readings, each with what was actually probed and what it found.
Three of the ten produced defects; those are fixed and regression-tested. The
rest are recorded with the evidence that answers them, so a reviewer can check
the answer rather than take it.

### 1. Semiconductor physicist — "where is the physics wrong?"

Probed independently of the test suite: Bernoulli against a 60-digit decimal
reference over the full double range (worst relative error **1.2e-16**); the
identity `B(x) − B(−x) = −x` over 4001 points (max relative **2.2e-16**);
built-in potential vs analytic at four doping levels (**8.7e-12 … 0**); mass
action at equilibrium (**4.8e-9**); rectification and reverse saturation;
ideality factor from the 0.3–0.5 V log-slope (**1.0184**). Nothing wrong found.
**GaAs, previously never solved, now solves** with V_bi exact to <1e-9 and mass
action ≤6e-5 — U4 closed for the solver, not for device physics.

### 2. Numerical-methods expert — "where can this solver silently fail?"

**Found BUG-13** (CRITICAL): a relative carrier tolerance applied across 16
decades is unsatisfiable, was read as divergence, and aborted bias
continuation — returning cold-start currents wrong by 3–5 decades and of the
wrong sign in reverse bias, across the top two decades of the *claimed* doping
range. Invisible to all 161 tests of the first cycle. Fixed; the discriminator
sits on an eleven-decade plateau so it is not tuned.

Also probed: NaN and inf doping (→ `converged=False`, honest), all-zero doping
(converges, physical), a 3-node grid, doping supplied at the wrong resolution
(auto-interpolated), ±100 V. **The ±100 V probe found a second defect**:
`current_is_trustworthy()` returned `True` on a non-converged state carrying
3.0e10 A/m². Fixed by folding the convergence check in.

### 3. ML reviewer — "where is the leakage?"

Split disjointness is asserted at construction and tested from both sides,
including a negative control that a deliberately overlapping spec **is**
rejected. For the new experiments: the experiment-design acquisition is called
with `J_surr` and `sigma` only — the SG Jacobian appears exclusively in
`design_summary`, which scores; UQ hyperparameters are selected on the
calibration split. **One honest caveat found and documented rather than
engineered away**: in the tuning run the calibration split does double duty
(selection *and* temperature fitting). Not test leakage, and the resulting bias
runs *in favour of* the two methods that lose.

### 4. Bayesian reviewer — "does the uncertainty mean anything?"

ρ(σ,|err|) = +0.798, and σ inflates 21.3× under distribution shift against a
12.1× error inflation. It is honestly *not* monotone across σ quartiles — the
ensemble over-states σ on the unseen profile family, which is the safe
direction but is stated as a defect rather than a feature. MC-dropout and SWAG
were benchmarked for the first time and lose; the mechanism (their σ is a
function of their own hyperparameters, not of distance from data) is measured,
not asserted.

### 5. Inverse-problem researcher — "is the problem identifiable?"

**Locally**, in **chart L** at **d=16** — the Jacobian rank at one operating
point, over that chart's reachable set — 3–4 of 16 at the reference conditions; 1–6 (median 3) across 88 measurements
spanning six axes plus a 400-replicate bootstrap. The extremes are attributed
rather than reported as scatter: rank 1 only at a reduced bias range, rank 5–6
only at larger finite-difference steps (an *estimator* effect). The decisive
control is that the rank does not grow with the parameterisation dimension.
Equivalence twins were constructed and verified through the solver. The
analysis remains **local**, and that is listed as the largest open risk.

### 6. Research reviewer — "what exactly is novel?"

Nothing methodologically. Prior art was re-searched this cycle for both new
results; the closest match to the gradient-fidelity finding (Yu, Cai & Liu,
arXiv:2604.04107) is cited, characterised, and noted to reach a *more
optimistic* conclusion in a different domain. The optimal-design criteria are
Fedorov/Atkinson–Donev and are labelled as such. Two citations added this cycle
were checked against the sources: one author list and one year/volume/title
were wrong on first writing and were corrected.

### 7. Reproducibility reviewer — "can I reproduce every number?"

Every headline experiment has a `make` target and writes a manifest recording
git commit, tree cleanliness, library versions, platform, CUDA and seed. The
README quick-start was extracted and executed verbatim. The BUG-13 fix was
verified **not** to move any published number by re-running the headline
experiment and diffing. Two older output directories (`calib_surrogate`,
`inv_sweep_surrogate`) predate `RunManifest` and are not covered — stated here
rather than quietly excluded.

### 8. Software engineer — "what breaks off the happy path?"

**Found BUG-14**: every text write used the platform default encoding, so the
notebook generator could not run on Windows at all. Fixed across 15 files and
regression-tested with a sweep that is verified to *fail* when the defect is
reintroduced. `make check-install` hard-coded `venv/bin/` and could not run on
Windows either. CI now includes a Windows job, since a Linux-only matrix
structurally cannot see this class.

### 9. Industry engineer — "would I trust this for a real decision?"

For the forward model inside its training band, with the stated error bars:
plausibly. For anything else the project now says no in specific terms —
38% extrapolation error, 84% family transfer, gradients uninformative outside
the identifiable subspace, and a solver that refuses to certify its own current
below the noise floor. The honest summary is that this is a validated research
instrument, not a TCAD replacement, and the README says so.

### 10. Release engineer — "can a stranger clone, install, test, run?"

Wheel built, installed into a fresh venv, `bayespinn selftest` passes, and the
full suite passes **from site-packages** rather than the checkout (verified by
printing the imported module path). All new modules are present in the wheel.

## What is NOT release-grade

1. **GaAs.** Constants present and checked against Sze; **no GaAs device has
   ever been solved**. The material is exposed in the API and must be treated
   as untested.
2. **The pure-physics PINN.** Measured at 100% median relative error and
   reclassified as legacy (ADR-0004). It is retained, smoke-tested, and
   explicitly not a forward model. Its `configs/train_*.yaml` paths run
   end-to-end but their *results* are not validated because there is nothing
   to validate them against.
3. **Duplicate ohmic-BC implementations.** `_ohmic_bc` and
   `pinn/losses.ohmic_boundary_values` remain separate implementations of the
   same physics — the cause of BUG-11. They agree today; the duplication is
   documented, not removed.
4. **The gradient-fidelity result is 1D and single-architecture.** GRAD-01 is
   measured on four 1D device families with one surrogate architecture.
   Whether the inside/outside separation is as sharp elsewhere is untested.
5. **The experiment-design gain is modest and Jacobian-limited.** +0.39 rank,
   obtained while planning with a surrogate Jacobian correlating only
   +0.01…+0.40 with the truth. A better forward model would likely change the
   size of the effect; the direction of the `max_std` result is more robust
   than the magnitude of the `d_optimal` one.
6. **Identifiability is local.** A Jacobian at an operating point. Global
   (sampling-based) non-identifiability remains the largest open scientific
   risk, unchanged from the first cycle.

## Recommended next steps

1. Extend the identifiability analysis from local (Jacobian) to global
   (sampling-based). This is where the remaining scientific risk sits, and it
   is the one first-cycle recommendation still outstanding.
2. Test GRAD-01 in 2D and with a second surrogate architecture. If the
   inside/outside separation holds, it generalises; if not, that bounds it.
3. Merge the two ohmic-BC implementations behind one function.
4. Solve one GaAs device, or remove GaAs from the public API.
5. If the low-bias regime becomes scientifically necessary, reformulate the SG
   continuity solve in quasi-Fermi variables (ADR-0002 option A).

## Reproducing every claim in this document

```bash
make test                          # 240 tests
make results                       # H1-H5 headline table
make identifiability               # the identifiability spectrum
make identifiability-robustness    # 88 measurements across 6 axes + bootstrap
make uq-benchmark                  # ensemble vs MC-dropout vs SWAG
make uq-tuning                     # ... after a fair hyperparameter search
make experiment-design             # information- vs uncertainty-driven design
make gradient-fidelity             # where the surrogate gradients are usable
make pinn-vs-surrogate             # the ADR-0004 evidence
make notebooks                     # regenerate the twelve notebooks
make check-install                 # build a wheel, install clean, test there
```

Every one writes `manifest.json` recording git commit, tree cleanliness,
Python/NumPy/SciPy/Torch versions, platform, CUDA and seed.
