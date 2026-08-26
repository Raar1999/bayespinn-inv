# Claim → Evidence Matrix

Every quantitative claim made anywhere in this repository, traced to the code,
data, seed and command that produces it. A claim without a reproducing command
is not a result.

**Environment for all measured values below:** Python 3.11.9, NumPy 2.4.4,
SciPy 1.17.1, PyTorch 2.11.0+cu128, Windows 11, CPU. Each experiment script
writes a `manifest.json` recording the git commit, tree cleanliness, versions
and configuration.

**Verdict key:** ✅ reproduced · ⚠️ corrected (old value was wrong or
mis-scoped) · ❌ withdrawn · 📄 documentation-only

---

## 1. Current claims (README, `outputs/results/`)

| # | Claim | Value | Source | Command | Seed | n | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Forward I–V error, interpolation | 2.8% median (CI 2.0–3.9%), p90 7.0% | `run_results.py` H1 | `python scripts/run_results.py` | 0 | 72 | ✅ |
| C2 | Forward I–V error, **extrapolation** | 38.2% median (23.1–89.7%), p90 861% | same | same | 0 | 68 | ✅ new |
| C3 | Forward I–V error, **family transfer** (graded, trained on steps) | 84.2% median (75.0–106.4%) | same | same | 0 | 60 | ✅ new |
| C4 | Current dynamic range of training labels | 9.96 decades (8.9e-5 → 8.1e5 A/m²) | same | same | 0 | 156 labels | ⚠️ was "13 orders of magnitude" |
| C5 | Labels dropped as numerically untrustworthy | 13 of 169 | same | same | 0 | — | ✅ new |
| C6 | Inverse recovery, 0% noise | 0.0018 decades (0.0013–0.0024) | `run_results.py` H2 | same | 0 | 40 | ⚠️ was 0.004, n=5 |
| C7 | Inverse recovery, 10% noise | 0.0072 decades (0.0047–0.0101) | same | same | 0 | 40 | ⚠️ was 0.009, n=5 |
| C8 | 1σ coverage falls with noise | 75% → 28% (0% → 10% noise) | same | same | 0 | 40/row | ✅ |
| C9 | Calibration, ±1.64σ | 46% → 90% (nominal 90%) | `run_results.py` H3 | same | 0 | 140 | ⚠️ pre/post now on the same set |
| C10 | Variance-inflation factor | T = 2.09 | same | same | 0 | 48 (val) | ⚠️ was 2.19 |
| C11 | Active learning vs random | no distinguishable advantage at any budget | `run_results.py` H4b | same | 1000–1007 | 32/cell | ✅ new (negative) |
| C12 | Identifiable dof at 2% noise, **local**, **chart L**, **d=16** | 4 (sym step), 5 (asym), 3 (graded), 4 (LDD), of 16 | `run_identifiability.py` | `python scripts/run_identifiability.py` | 0 | 8–10 biases | ✅ new |
| C13 | Rank vs instrument quality | 2 dof @20% → 9 dof @1e-4% noise | same | same | 0 | — | ✅ new |
| C14 | Equivalence twins indistinguishable (**local**, **chart L**, **d=16**) | 1.26× doping change → 0.02–1.3% I–V change | same | same | 0 | 4 families | ✅ new |
| C15 | Jacobian linear-response validation | ratios 0.995–1.04 | same | same | 0 | 4 dirs × 4 families | ✅ new |
| C16 | Surrogate speedup vs SG | 152× (0.85 ms vs 129 ms, M=5) | timing harness | see README | — | 10/200 reps | ⚠️ was "~500×" |
| C17 | Built-in potential vs analytic | rel. error 7.24e-14 | `cli.py` selftest | `bayespinn selftest` | — | 1 | ⚠️ **2.8e-7 withdrawn** (X15) — it measured the *pre-audit* solver |
| C18 | Mass action at equilibrium | max \|np−1\| = 2.93e-9 | same | same | — | 301 nodes | ⚠️ **7.6e-6 withdrawn** (X16) — same cause |
| C19 | Diode ideality factor | 1.018 | same | same | — | 8 biases | ✅ |
| C21 | Uncertainty vs error | Spearman ρ = +0.824; NOT monotone across σ quartiles | `run_results.py` H5 | same | 0 | 200 | ✅ new |
| C22 | OOD awareness | σ inflates 15.7× vs error 11.8× (interp → extrap) | same | same | 0 | 140 | ✅ new |
| C20 | Test suite | 161 passing | pytest | `make test` | — | — | ⚠️ was 42 |

## 2. Solver-improvement claims (audit)

| # | Claim | Value | Evidence | Verdict |
|---|---|---|---|---|
| S1 | Equilibration improves mass action | 6.77e-3 → 9.7e-10 (7.0e6×) | `test_sg_numerics.py::test_equilibration_beats_plain_spsolve` | ⚠️ **"1.32e-2 → 7.62e-6 (1730×)" withdrawn** (X17) |
| S2 | expm1 flux removes cancellation | 5.86e-7 → 1.39e-13 A/m² on an exact state (4.2e6×) | `::test_exact_equilibrium_state_gives_machine_zero_current` | ✅ |
| S3 | expm1 form is an exact identity | agrees with direct form to 1.9e-11 relative away from equilibrium | `::test_agrees_with_direct_form_away_from_equilibrium` | ✅ |
| S4 | Noise floor is predictive | current precision tracks 1/SNR over 5 decades | measured; ADR-0002 | ✅ |
| S5 | 2D MOS-cap converges over full range | −2 V → +5 V, rel. residual ~1e-12 | `test_mos_cap_physics.py::TestConvergenceAcrossBias` | ✅ |
| S6 | 2D lateral invariance exact | ~1e-15 (was ~1.5e-3, O(1/Nx)) | `::TestLateralInvariance` | ✅ |
| S7 | 2D Gauss law | Q_semi = D_ox to 0.000% | `::test_gauss_law_total_charge_balances_gate_field` | ✅ |
| S8 | φ_s vs depletion approximation | within 15–26 mV (≈V_T) over 0.2–0.8 V | `::test_surface_potential_matches_depletion_approximation` | ✅ |
| S9 | Ohmic BC exact at extreme doping | \|np−1\| = 0 exactly up to C_s = 1e12 | `test_robustness.py::test_doping_magnitude_sweep` | ✅ |
| S10 | LDD high-injection grid convergence | I = 3.5976e8–3.5986e8 A/m² across N=201/301/601 | `test_sg_numerics.py::TestAutomaticContinuation` | ✅ |
| S11 | Bernoulli finite over full double range | exact identity to 8e-17 | `::TestBernoulliExtremes` | ✅ |
| S12 | ECE floor for M=5 | 0.088 (Monte-Carlo, matches analytic 0.091) | `test_robustness.py::test_perfect_ensemble_scores_at_its_floor` | ✅ |

## 3. Superseded claims

| # | Old claim | Where | Why it changed | Now |
|---|---|---|---|---|
| X1 | "~4% median rel. error across **13 orders of magnitude**" | README | Measured span of the reference I–V is 10.0 decades, and the evaluated points span less. The "13" was never measured. | C1, C4 |
| X2 | "Graded junctions: median 4.6%" | `results_summary.md` | The old script **trained on graded profiles too**, so this was in-distribution error reported as generalization. Retested as true family transfer. | C3 (84%) |
| X3 | Calibration "30% → 71%" | `results_summary.md` | The two columns came from **different test sets**. | C9 |
| X4 | "1σ coverage 100 / 80 / 60 / 40%" | `results_summary.md` | n = 5, no interval, and one RNG seed reused across all noise rows. | C8 (n=40, Wilson CIs) |
| X5 | "H4 Active-learning gain" | `results_summary.md` | Contained no active learning — three fixed bias subsets. Its own numbers also contradicted its stated hypothesis. | H4a (renamed), C11 (real AL) |
| X6 | "~500× faster (0.4 ms vs 194 ms)" | README | Compared a single surrogate against SG; the ensemble is what is used, and SG is now slower but correct. | C16 (152×) |
| X7 | "SG solver ✅ validated … 0–0.7 V converges 3–7 it" | README roadmap | The 3-iteration "convergence" was the false-convergence bug (BUG-03). | S1, C18 |
| X8 | "Unit tests (38) … 23 core + 9 MOS-cap + 6 surrogate" | README roadmap | Contradicted the badge (42) in the same file and omitted `test_adapters.py`. | C20 |
| X9 | "ECE 0.224 → 0.086 after temperature scaling" | README, reframe doc | 0.086 is *at* the M=5 estimator floor (0.088); it cannot be read as a calibration quality. | S12 |
| X10 | "Strong-inversion stiffness" limitation | README, `grid_2d.py` | Was BUG-07, a wrong-sign Jacobian, not physics. | S5 |
| X11 | "First to evaluate Bayesian PINN calibration quantitatively for semiconductor inverse problems" | `papers/draft.md` | No prior-art search supported it; Bayesian inversion for this problem is published (arXiv:2408.11485). | ❌ withdrawn (ADR-0003) |
| X12 | "The forward PINN converges on realistic doping ranges" | `papers/draft.md` | Directly contradicted `docs/forward_model_reframe.md` in the same repository. | ❌ withdrawn |
| X13 | Beucler et al. (2022) as the source of the TV+positivity scheme | `inverse_design.py` | Citation could not be verified; no paper with that title located. | ❌ removed (CITE-01) |
| X14 | README quick-start `0.5*(Jn.mean()+Jp.mean())` | README | Off by a factor of 2 vs `terminal_current = mean(Jn+Jp)`. | 📄 fixed and executed |
| X15 | "Built-in potential vs analytic: rel. error **2.8e-7**" | README headline table, C17, `RELEASE_READINESS` | Measured on the **pre-audit** solver. `git archive 6577f4b` and re-run: `2.7558e-07` — the published figure, reproduced exactly on the *superseded* code. The adopted solver measures `7.243e-14`, grid-independent over N=101…601. The claim described a program the project no longer ships. | ❌ withdrawn → C17 (AUDIT_g0 SCI-08 / PROV-06) |
| X16 | "Mass action at equilibrium: max \|np−1\| = **7.6e-6**" | C17/C18, `RELEASE_READINESS` | Same cause. Adopted solver: `2.93e-9` at the selftest configuration (`1.37e-9 … 8.42e-9` over grids 101–601). | ❌ withdrawn → C18 |
| X17 | "Equilibration improves mass action **1.32e-2 → 7.62e-6 (1730×)**" | S1 | The `1.32e-2` starting point is sound (measured `6.77e-3`, 1.95× — within tolerance). The `7.62e-6` endpoint is not: the adopted solver reaches `9.7e-10`, so the real gain is ~**7.0e6×**, not 1730×. The published figure understated the improvement by ~4000×. | ❌ withdrawn → S1 |
| X18 | Identifiability stated without a local/global label (the **chart L** / **chart G** label was added later still, see G8) | README rows 51, 70, 267, 340; `RELEASE_READINESS` 72, 189 | `inverse/identifiability.py` computes a **local** Jacobian rank at one operating point and says so; `papers/draft.md` labels it three times. The README and release gates dropped the qualifier, inviting the number to be read as global non-identifiability. PH-21 forbids this. | ⚠️ qualified, not withdrawn (AUDIT_g0 SCI-11) |

## 4. Claims that remain unverified *(as of the first cycle; see §5 for resolutions)*

| # | Claim | Where | Status |
|---|---|---|---|
| U1 | Notebook outputs `01`–`12` | `notebooks/` | **Stale.** Executed against the pre-audit solver, so their numbers predate BUG-01…BUG-12. Not re-executed in this cycle; they should be regenerated or marked historical before release. |
| U2 | MC-dropout and SWAG UQ quality | `bayesian/` | Implemented and interface-tested, but never compared against the deep ensemble under a common protocol. No claim is made about them. |
| U3 | `pinn/` training pipeline results | `training/`, `configs/` | The pure-physics PINN is superseded as a forward model; its training loop is exercised only by a 5-epoch smoke test. |
| U4 | GaAs material parameters | `physics/constants.py` | Constants check out against Sze, but no GaAs device has been solved or validated. |

---

## 5. Second-cycle claims (2026-08-19)

| # | Claim | Value | Command | Seed | n | Verdict |
|---|---|---|---|---|---|---|
| D1 | Pure-physics PINN, forward I–V error | **100.00% median, 100.00% p90**, 6% of points within 50% | `python scripts/run_pinn_vs_surrogate.py` | 0 | 72 | ✅ new |
| D2 | Surrogate, same protocol as D1 | 2.64% median, 6.64% p90, 100% within 50% | same | 0 | 72 | ✅ new |
| D3 | PINN self-consistency `std(J)/\|mean(J)\|` | 0.03 (0 = exact steady state) — converged, and wrong | same | 0 | 6 profiles | ✅ new |
| D4 | Deep ensemble ρ(σ,\|err\|) vs tuned MC-dropout / tuned SWAG | **+0.798** vs +0.299 / +0.486 | `python scripts/run_uq_tuning.py` | 0 | 200 | ✅ new |
| D5 | σ inflation off-distribution, ensemble vs MC-dropout vs SWAG | **21.3×** vs 1.4× vs 2.5×, against a 12–13× error inflation | same | 0 | 140 | ✅ new |
| D6 | Budget-matched ensemble still beats both single-network methods | ρ +0.731, 6.7 s train (vs 9.2 s / 6.3 s) | `python scripts/run_uq_benchmark.py` | 0 | 200 | ✅ new |
| D7 | Surrogate gradient fidelity inside identifiable subspace | mean cosine **+0.504** | `python scripts/run_gradient_fidelity.py` | 0 | 4 devices | ✅ new |
| D8 | Surrogate gradient fidelity **outside** identifiable subspace | mean cosine **−0.001** | same | 0 | 4 devices | ✅ new |
| D9 | D7/D8 are not undertraining | 300→10000 epochs: value error 1.133→0.252 symlog while outside-cosine +0.003→−0.001 | same | 0 | 4 devices × 4 budgets | ✅ new |
| D10 | `max_std` acquisition vs random, on identifiable rank | **−0.31** (2 wins / 9 ties / 9 losses) | `python scripts/run_experiment_design.py` | 0 | 20 device×budget, 12 seeds | ✅ new |
| D11 | `d_optimal` / `null_space` vs random | **+0.39** (5 wins / 15 ties / **0 losses**) | same | 0 | same | ✅ new |
| D12 | Surrogate-vs-SG Jacobian correlation (bounds D10/D11) | +0.01 … +0.40 by device | same | 0 | 4 devices | ✅ new |
| D13 | Identifiable rank vs parameterisation dimension | does **not** grow: P = 8→32 gives rank 2–4 | `python scripts/run_identifiability_robustness.py` | 0 | see manifest | ✅ new |
| D14 | Identifiable rank across all robustness axes | **1–6, median 3** over 88 measurements; **3–4** at the reference conditions | same | 0 | 88 | ⚠️ headline "3–5" corrected to 3–4 (reference) / 1–6 (all conditions) |
| D14a | Where the extremes come from | rank 1 only at a reduced bias range (v_max=0.6, graded); rank 5–6 only at larger finite-difference steps (0.02–0.05), which lower the *analysis* noise floor rather than revealing more physics | same | 0 | 88 | ✅ new |
| D15 | SG converges across the claimed doping envelope after BUG-13 | 90/90 solves; every trustworthy point grid-converged to ≤0.35% | `pytest tests/test_sg_numerics.py -k Roundoff` | — | 90 | ✅ new |
| D16 | Headline results unchanged by the BUG-13 fix | H1/H3/H5 bit-identical before and after | `python scripts/run_results.py` | 0 | — | ✅ verified |
| D17 | Test suite | **240 passing** (was 161) | `make test` | — | — | ✅ |
| D18 | GaAs PN junction solves | V_bi exact to <1e-9 rel.; mass action ≤6e-5; rectifies >1e3× | `pytest -k GaAs` | — | 3 levels | ✅ new |
| D19 | `current_is_trustworthy()` now requires convergence | at +100 V: was `trust=True` on a non-converged state carrying I=3.0e10 A/m²; now `False` | `pytest -k TrustFlag` | — | — | ⚠️ API footgun closed |
| D20 | README quick-start runs verbatim | V_bi 0.7143 V = analytic; 12/13 bias points trustworthy, V=0 correctly flagged | copy-paste from README | — | 13 | ✅ |

### Resolution of the previously-unverified claims

| # | Was | Now |
|---|---|---|
| U1 | Notebook outputs stale | ✅ **Resolved.** All twelve regenerated from `scripts/build_notebooks.py` and re-executed top to bottom against the current solver; the stale narrative numbers ("13 orders", "~4%", "~500×") corrected *in the generator*. |
| U2 | MC-dropout / SWAG never compared | ✅ **Resolved.** Root cause was that both wrapped `ForwardPINN` rather than the surrogate. `bayesian/surrogate_uq.py` fixes it; D4–D6 are the comparison. ADR-0005. |
| U3 | PINN pipeline unvalidated | ✅ **Resolved as a negative result.** D1–D3; reclassified as legacy (ADR-0004). |
| U4 | GaAs never solved | ✅ **Resolved for the solver.** A GaAs PN junction now converges at 1e21/1e22/1e23 m⁻³ with V_bi exact to <1e-9 relative and mass action to 6e-5, and rectifies (`tests/test_sg_numerics.py::TestGaAsDeviceSolves`, 4 tests). GaAs *device physics* is still not validated against measurement, and none is claimed. |

---

## 6. Loop re-verification, generations 0–5 (2026-08-25)

Every experiment launcher re-run from the champion commit and compared
leaf-by-leaf against its recorded artefact. This is the evidence for `SPEC-g0-1`
("one commit reproduces the entire claim surface"), which generation 0 could
assert for only one of seven experiments.

**Timing fields are excluded from the comparison and reported separately.**
Wall-clock is not a scientific claim and the machine was under load throughout —
`train_seconds` roughly doubled on several runs. Counting that as a
non-reproduction would be dishonest in the other direction.

| experiment | numeric leaves | non-timing diff | timing diff | integer leaves changed | claims | verdict |
|---|---|---|---|---|---|---|
| `run_results.py` | 174 | **0** | 0 | 0 | C1–C11, C21, C22 | ✅ bit-identical |
| `run_uq_benchmark.py` | 471 | **0** | 10 | 0 / 136 | D4, D5, D6 | ✅ |
| `run_uq_tuning.py` | 424 | **0** | 22 | 0 / 98 | D4, D5 | ✅ |
| `run_pinn_vs_surrogate.py` | 21 | **0** | 2 | 0 / 9 | D1, D2, D3 | ✅ |
| `run_experiment_design.py` | 5066 | **0** | 4 | 0 / 2102 | D10, D11, D12 | ✅ |
| `run_gradient_fidelity.py` | 1639 | **0** | 4 | 0 / 283 | D7, D8, D9 | ✅ |
| `run_identifiability_robustness.py` | 3287 | **0** | 0 | 0 / 1847 | D13, D14, D14a | ✅ |
| `run_identifiability.py` | 375 | 41 | 0 | **0 / 79** | C12–C15 | ⚠️ `REPRO-01` |

**Totals: 11,457 numeric leaves across eight experiments. 41 non-timing
differences, all in one experiment, all diagnostics. Zero integer-valued leaves
changed anywhere** — and the integers are where the ranks live, so every
identifiability claim in the repository reproduces exactly.

### The load-bearing one

`run_pinn_vs_surrogate.py` re-ran **with the GRAD-02/GRAD-03 fix applied**:

| | recorded | re-run |
|---|---|---|
| PINN median rel. error | `0.9999970197631748` | `0.9999970197631748` |
| PINN p90 rel. error | `1.0000456802107016` | `1.0000456802107016` |
| PINN fraction within 50% | `0.05555555555555555` | `0.05555555555555555` |
| Surrogate median rel. error | `0.026436009151515727` | `0.026436009151515727` |

Generation 0 argued, from 0 NaN in 26 weight-gradient tensors, that the ohmic fix
could not disturb `D1`/`ADR-0004`. This is that argument tested end-to-end:
**it holds bit-for-bit.** `ADR-0004` stands unchanged.

### REPRO-01 — resolved as a provenance artefact, not a numerics defect

41 of 375 leaves in `run_identifiability.py` differ from the 2026-08-19 artefact.
Median relative drift `1.906e-08`; maximum `5.840e-02`, at
`/devices/ldd/spectral_floor` and `/devices/ldd/entry_noise` (the same quantity
propagated).

**No claim is affected.** All four **local** identifiable ranks in **chart L**
at **d=16** — the Jacobian rank at the reference operating point, over 16 bias
points spanning 0.15–0.90 V and reported as `rank(cutoff)`, 4, 5, 3, 4
of 16 — every
`resolvable_rank`, and all four complete `rank_vs_noise` tables are identical.

Three measurements, in order, and the first hypothesis was wrong:

1. **BLAS threading — ruled out.** The forward Jacobian is bit-identical twice
   within one process, across three separate processes at default thread counts,
   and across three more with `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1`.
   Six runs, one SHA-256.
2. **The script as a whole — ruled out.** `run_identifiability.py` run twice on
   the current tree: **375 leaves, 0 differing.** Bit-identical to itself.
3. **Therefore the difference is in the producing tree, not the runtime.** The
   2026-08-19 artefact's manifest says `6577f4b`, dirty — which `PROV-04`
   establishes is not enough to reconstruct anything.

`run_identifiability_robustness.py`, which exercises the same solver 88 times,
reproduced bit-identically across 3287 leaves. That is consistent with the
conclusion and inconsistent with a live nondeterminism in the solver.

This is the first **quantified** cost of `PROV-03`: 41 numbers that can never be
explained, because the tree that produced them was never committed. The
explanation cannot be confirmed either — confirming it would require the very
thing that was lost. Recorded as unresolvable rather than closed.

---

## 7. S-1 — global identifiability (generation 6, 2026-08-25)

Oracle-arbitrated throughout; the surrogate is never called (`ADR-0007`,
`SPEC-g6-5`). Every row carries the five conditions §4.2 requires: parameterisation
`d`, prior support, noise model, observation set, and both floors.

**Common regime for G1-G5:** d as stated; log-uniform prior 1e21-1e23 m^-3 per
anchor (hash `ba11a6d5357388cb...`, fixed before sampling); 16 biases over
0.15-0.90 V; noise floor 2.0e-02; solver discretisation floor 1.5e-03;
distinguishability floor **2.0e-02** = max of the two. Manifest:
`outputs/global_identifiability_g6/manifest.json`.

| # | Claim | Value | Command | n | Verdict |
|---|---|---|---|---|---|
| G1 | Global non-identifiability, witness search (**chart G**, **d=4**) | **13 witness pairs** of 1,999,000 examined; separations **2.01x - 8.18x** in doping; observational distances 1.23e-02 - 1.53e-02, all below the 2.0e-02 floor | `python scripts/run_global_identifiability.py` | 2000 profiles, all oracle-certified | :white_check_mark: new |
| G2 | The closest witness | doping differs **8.18x** at one anchor; I-V differs **1.23%** across 16 biases spanning ten decades of current | same | 1 pair | :white_check_mark: new |
| G3 | Witnesses survive refinement | 3 of 3 tested pairs stay below the floor at N=301/601/1201 and at `tol_carrier=1e-12`; pair 0's distance *falls* 1.23e-02 -> 8.61e-03 | `python scripts/run_witness_falsifier.py` | 3 pairs x 3 grids x 2 tolerances | :white_check_mark: new |
| G4 | Contraction spectrum (**chart G**, **d=4**) | **3 of 4** directions contract below variance ratio 0.5, at **10x** the instrument noise, over 16 biases spanning 0.15-0.90 V, ESS 71.0 | `run_global_identifiability.py` | 2000 | :warning: measurable only in a narrow band, see G5 |
| G5 | Contraction at the instrument's own 2% noise (**global**, **chart G**, **d=4**, 16 biases 0.15-0.90 V) | **NOT MEASURED.** Prior importance sampling collapses: ESS 1.0, all variance ratios 0.000. The apparent "4 of 4 contracting" is an estimator artefact and is reported as unsupported | same | 2000 | :white_check_mark: negative result |
| G6 | Contracting directions vs parameterisation (**global**, **chart G**) | does **not** grow with d: **2 of 2** (d=2), **3 of 4** (d=4), **1 of 8** (d=8), all at 10x noise over 16 biases spanning 0.15-0.90 V | same | 1000 per d | :warning: d=8 confounded -- samples/dimension fall 500 -> 250 -> 125 |
| G7 | Local vs global relationship | **superseded by G8**. The two numbers were measured in different charts (**chart L** at d=16; **chart G** at d=4) and their fractions are over different manifolds, so "not comparable in magnitude" was right for the wrong reason | `CHART_RECONCILIATION_g7.md` | - | :warning: superseded |
| G8 | Local and global at matched chart and d | **the dimension moves the rank; the chart does not.** Rank 3 at d=4 and 4 at d=16 in **chart G** *and* in **chart L**, one operating point, 2% noise, 16 biases; spectra agree to within 3% at matched d. Witness pair 0 embeds into **chart L** at **d=16** with observational distance 1.207e-02 vs 1.225e-02, separation preserved to 0.999 | `python scripts/run_chart_reconciliation_g7.py` | 4 cells, oracle float64 | :white_check_mark: new |
| G9 | Shape of the degeneracy | **bimodal, not a flat manifold**: two isolated likelihood maxima at the witness endpoints, barrier 242 log-units deep, 5 of 61 path points inside the 2.0e-02 floor; a control along the most observable direction is 43.7x deeper with no second mode (**chart G**, **d=4**) | same | 61 points + 61 control | :white_check_mark: new |

### What G1-G7 do not establish

Nothing at d=16, the parameterisation the local result uses; nothing outside the
stated prior (a narrower physical prior could exclude these witnesses entirely);
no contraction spectrum at 2% noise; and 13 is the number found at this budget,
not the true number. The d=8 decline is confounded with sampling density and is
not evidence of less information at higher d.

## 8. Generation 8 — the third chart, the observation set, the basin count (2026-08-26)

Oracle-arbitrated throughout; the surrogate is never called (`ADR-0007`, `SPEC-g6-5`, `PH-22`). **Common regime for H1-H8:** float64 Scharfetter-Gummel on a 301-node uniform grid; log-uniform **prior** 1e21-1e23 m^-3 per magnitude anchor (chart J's junction coordinate carries its own prior and its own hash); **noise model** independent Gaussian in relative current at a **level** of 2%; **observation set** 16 **biases** over 0.15-0.90 V except in H4, whose subject is changing it; noise floor 2.0e-02, solver discretisation floor 1.5e-03, distinguishability floor **2.0e-02** = max of the two. Manifest: `outputs/g8/manifest.json`. Row `G8` of section 7 is **qualified by H3 and H4** and should not be read without them.

| # | Claim | Value | Command | n | Verdict |
|---|---|---|---|---|---|
| H1 | `CHART-01` closed structurally | one reconstruction operator; the solver raises rather than interpolating; an AST guard fails per call when a second path appears. 24 profiles frozen from the deleted code path reproduce byte for byte | `pytest tests/test_one_reconstruction_g8.py` | 24 golden profiles, 3 grids | :white_check_mark: new |
| H2 | The fix moved no published number | **chart G**, **d=4**: 13 witness pairs of 1,999,000, identical to the generation-6 artefact. **chart L**, **d=16**: 37 of 719,400, identical to the generation-7 artefact. Distances of the five rendered witnesses agree to 0.0 in both. The two budgets are **not comparable** and are quoted only to show each search reproduced itself | `python scripts/run_g8.py --phases reproduce` | 2000 + 1200 draws | :white_check_mark: new |
| H3 | A third chart moves the *local* spectrum (**chart J**, **d=16**) | **chart J at `s=0` IS chart G at `d=15`, bit for bit** -- chart J *contains* chart G rather than sitting beside it, re-verified at 12 operating points at generation 9, so what follows is measured within one family. Displacing the junction moves the unit-homogeneous magnitude-block spectrum by **219%** (`x_j/L = 0.35`) and **9.1%** (0.65) against **chart G** at **d=15**, versus **2.8%** for the chart-G-to-chart-L change at matched d. The generation-7 invariance is retired to the interpolant family it was measured in | `python scripts/run_g8.py --phases chart_j` | 7 cells, one operating point | :white_check_mark: new |
| H4 | The observation set moves it far more (**chart G**, **d=16**) | the same 16 biases over the same range, spaced geometrically instead of linearly: **19.8%**. Narrowed to 0.30-0.60 V: **97.4%**, and the *local* identifiable count falls from 4 to 2. Unchanged after `sqrt(rows-used)` normalisation | `python scripts/run_g8.py --phases obs_set` | 6 observation sets x 3 charts | :white_check_mark: new |
| H5 | A *local* rank is a curve over cutoffs | a bare integer is licensed by a population gap at the cutoff in 2 of 6 cells: `G_d4`, `L_d4`. Chart J at **d=4** has no gap either, so the licence follows the gap and not the dimension | `python scripts/run_g8.py --phases ranks` | 6 cells x 8 cutoffs | :white_check_mark: new |
| H6 | How many basins the witness set is | **many, not two**: **chart G**, **d=4**: 20 basins from 26 members of 13 pairs; **chart L**, **d=16**: 67 basins from 67 members of 37 pairs; **chart J**, **d=16**: 26 basins from 26 members of 13 pairs, single-linkage at a threshold of 0.3 decades fixed and hashed before clustering. Reported as a **lower bound** and as a curve over 0.05-3.0 decades. **Qualified by its own null control**: the same criterion over the same number of ordinary prior draws returns almost the member count in **chart L** at **d=16**, so the count there is close to trivial and only the qualitative answer survives | `python scripts/run_g8.py --phases modes` | see manifest | :white_check_mark: new |
| H7 | Native witness search (**chart J**, **d=16**), *global* | **13 witness pair(s)** among 719,400 pairs from 1200 draws under the junction prior (hash `236ff6576a85...`), 13 of them still witnesses under a magnitude-only separation criterion. **Not comparable** to the other charts' counts: the chart, the coordinate meaning and the kind of prior all differ | `python scripts/run_g8.py --phases chart_j` | 1200 draws | :white_check_mark: new |
| H7a | The junction position is *globally* non-identifiable too (**chart J**, **d=16**; chart J at `s=0` is chart G at `d=15` bit for bit, so the free junction is one coordinate added to a contained chart) | the widest witness pair puts the junction at 694 nm and 271 nm — **423 nm apart in a 1000 nm device** — with an observational distance of 1.7551e-02, below the 2.0e-02 floor. Terminal I-V cannot locate the metallurgical junction to better than that once the doping is free to compensate | same | 1 pair of 1200 draws | :white_check_mark: new |
| H8 | Charts G and L cannot place a junction | best **chart G** stand-in for a chart-J device at `x_j/L = 0.25` reproduces the magnitude to 0.0282 decades (log10) and dopes **75 of 301** grid nodes the wrong type; best **chart L** stand-in, 1.2246 decades (log10) and 77 of 301 | same | 2 probes x 5 junctions | :white_check_mark: new |

### What H1-H8 do not establish

> **Measured at generation 9, and the caveat was right.** The ordering named below was repeated at nine further operating points and does not survive: five distinct orderings appear, the generation-8 order is reproduced at 2 of 9 under the larger-movement statistic and at 0 of 9 under the milder one, and the interpolant reaches 101%. See the I-series in section 9 and `docs/G9_RESULT.md` section 2. The rows above are what was measured at the generation-8 operating point and stand as that.

Every cell above sits at **one operating point** - witness pair 0 member a, or a projection of it into the chart in question. The ordering the generation found (observation set > junction > dimension > interpolant) is measured there and nowhere else, and the one axis generation 8 did not perturb is the one every cell shares. The basin counts are single-linkage lower bounds over members the search happened to find, at one prior and one budget; they are not estimates of how many basins exist. No frequency is comparable across charts, and the chart-J prior is not the same kind of prior as the other two.

### Negative control

Four predicates each returned the negative answer on a case constructed to deserve it, through the same code the rows above ran through: the witness search on a distinguishable pair, the chart discriminator on a pinned junction, the cluster criterion on known-answer sets, and the solver on a chartless parameter vector. `all_controls_pass = True`; `outputs/g8/negative_control.json`.

---

## 9. Generation 9 - the ordering at further operating points (2026-08-26)

Oracle-arbitrated; 301-node grid except in I4, where the grid is the
subject; 16 bias points per window; 2% noise; finite differences at a
relative step of 0.05 with rows below `min_snr = 1e4` discarded -- all
inherited unchanged from generation 8, because one ruler is what makes a
replication one. Selection rule, ordering statistic and cluster criterion
hashed before the first draw: `outputs/g9/preregister.json`. Machinery
commit `a6728fe`, `dirty = false`. Artefacts `outputs/g9/`, manifest
`manifest.json`.

| # | Claim | Value | Command | n | Verdict |
|---|---|---|---|---|---|
| I0 | The generation-8 cells reproduce through this generation's code | interpolant 2.76% (g8: 2.8%), dimension 5.01% (5.0%), junction `x_j/L=0.35` 219.2% (219%), `0.65` 9.13% (9.1%), observation set geometric 19.80% (19.8%) | `python scripts/run_g9.py --phases op_points` | 1 control point, 12 cells | :white_check_mark: reproduction control |
| I1 | The four-way ordering is **operating-point dependent** | five distinct orderings across nine further operating points under the larger-movement statistic, four under the milder one; the generation-8 order recovered at **2 of 9** and **0 of 9** respectively; the two statistics agree at only 2 of the 12 points measured | same | 3 devices x 3 bias windows | :white_check_mark: **falsifies the generation-8 ordering** |
| I2 | What survives: the observation set dominates everywhere | its largest movement spans **0.925 - 1.080** across all 12 operating points, a factor of 1.17 end to end, while junction spans 0.173-4.560 (x26), dimension 0.026-0.558 (x21) and interpolant 0.026-1.015 (x39) | same | 12 points | :white_check_mark: new |
| I3 | Chart-invariance is a property of a cell, not of the charts | the chart-G-to-chart-L movement at matched `d` is **2.6%** at best and **101.5%** at `device_p50` in the 0.15-0.50 V window; at the generation-8 device alone, narrowing the window takes it from 2.8% to **30.7%** | same | 12 points | :white_check_mark: **narrows the generation-7 result** |
| I3a | The two charts in the observable, which is the denominator the invariance result needed | **at most 2.67%** apart in terminal current over the window their spectra are compared in, while sitting **more than 1.2 decades** apart in profile space (least-squares projection in `log10|C|`, the best admissible method). 0.82% at the generation-8 operating point | same | 12 points | :white_check_mark: new; supersedes an unreproducible 44% |
| I4 | The chart-J witness **count** does not survive refinement | **7 of 13** pairs stay below the 2.0e-02 floor at `N = 301/601/1201` and `tol_carrier = 1e-12`. The pairs that separate are concentrated among those whose junctions were nearly coincident: the pair 0.4 nm apart rises **195%** | `python scripts/run_g9.py --phases junction_refine` | 13 pairs x 3 grids x 2 tolerances | :warning: **falsifies the count of 13** |
| I4a | The junction *headline* pair survives it | 694 nm / 271 nm: observational distance **falls** 1.7551e-02 -> 1.7247e-02, below the floor at all six configurations | same | 1 pair | :white_check_mark: survives |
| I5 | A *local* rank is a curve in the observation set as well as in the cutoff (**chart G**, **d=16**) | at the generation-8 device the identifiable count at a 2% cutoff runs **1 -> 4** as the bias window widens from 0.10 V to 0.75 V about a fixed 0.525 V centre, and does **not move at all** as spacing runs from linear to geometric over a fixed 0.15-0.90 V window | `python scripts/run_g9.py --phases rank_obs` | 2 devices x (9 widths + 9 spacings) | :white_check_mark: new |
| I5a | A bare integer becomes licensed at **d=16** in a narrow bias window | at 0.10 V and 0.15 V the 2% cutoff falls inside a spectral gap of **x230.6** and **x171.3**, so the inherited gap criterion licenses a bare integer there. The licence follows the gap, and the gap is a property of the `(chart, d, device, bias window)` cell | same | 18 cells | :white_check_mark: extends `SPEC-11` |
| I6 | The chart-G witness pairs are a **ridge**, not two isolated points (**global**, **chart G**, **d=4**) | median likelihood barrier between the two members of a witness pair **8.31 log-units** against a floor barrier of 8.0, with **6 of 13** pairs at or below it. Null control - the same criterion over the same number of ordinary prior draws forming no witness pair - has a **minimum** of 339 and a median of 9379 | `python scripts/run_g9.py --phases basins` | 13 witness + 13 null paths | :white_check_mark: new, strengthens S-1 |
| I6a | Chart J's witness pairs are the other shape (**global**, **chart J**, **d=16**) | no pair within the floor barrier; median **468 log-units**, 59x the floor. Null control minimum 1332, median 9479. Both are global non-identifiability; they are different shapes of it | same | 13 witness + 13 null paths | :white_check_mark: new |

### What I1-I6a do not establish

Nine further operating points are nine, drawn under one rule from one prior
at one `d`; they establish that the ordering is not invariant, not what it
depends on. The observation-set dominance is measured over three windows
inside one converged bias range and says nothing about ranges outside it.
I5's curves are at two devices, named in `docs/G9_RESULT.md` section 3
before they were chosen. I6's barrier metric covers the *global* witness pairs of **chart G** at
**d=4** and of **chart J** at **d=16**, with an equal-sized null control,
and not every pair among the members; a straight line in chart coordinates
is a lower bound on the barrier, since a curved path can only be shallower.

### Negative control

Four predicates each returned the negative answer on a case constructed to
deserve it, through the same code the rows above ran through. The one the
clause names: the generation-8 evidence -- the four-way ordering at a single
operating point -- offered as a general claim, **rejected** by the same
predicate that judges I1, on the stated ground that generality is a claim
about the operating points that were not measured. That same predicate
accepts three synthetic points carrying one order under both statistics, so
it is not a predicate that only ever rejects. `all_controls_pass = True`;
`outputs/g9/negative_control.json`.
