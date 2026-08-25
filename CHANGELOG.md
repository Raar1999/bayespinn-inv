# Changelog

All notable changes to this project. Numbers here are measured, and each entry
names the command that reproduces it. Findings are tracked in
[`docs/AUDIT_MASTER.md`](docs/AUDIT_MASTER.md).

## [Unreleased] — generation 0 of the audit loop (2026-08-25)

An adversarial audit loop was run over the repository. Its first finding was that
**the repository's only commit was the pre-audit project**: both audit cycles —
6 of 40 source modules, 204 of 246 collected tests, 7 experiment launchers, the CI
workflow and the entire audit corpus — existed only as uncommitted working-tree
state. `git archive 6577f4b` and re-running the physics gives `SGConfig` with no
`equilibrate` option, a built-in-potential relative error of `2.7558e-07` against
the working tree's `7.243e-14`, and a mass-action residual of `6.1019e-03` against
`2.934e-09`. Every manifest in `outputs/` named that commit as its provenance.

### Added

- **Adoption commit `c115757`** on branch `loop/champion`, parent `6577f4b`
  (untouched). Before any git operation the tree was copied to two paths outside
  the repository and both verified 212/212 against
  `PRESERVE_MANIFEST_g0.sha256` (digest-of-digests
  `9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd`). The commit
  was then attested by extracting it and digest-comparing: **164/164 byte-identical,
  0 mismatched, 0 missing.**
- `outputs/` is now tracked — all 42 files including every `manifest.json`, so a
  clone ships the evidence with the claims (`PROV-01`).
- `git_status_counts()` and `git_tree_digest()` in `utils.provenance`
  (`ADR-0006`), and an optional `repo` argument on all four git helpers so the
  behaviour can be tested against a controlled repository.
- `docs/PROVENANCE_BIFURCATION_g0.md` — per-manifest record of which commit each
  result claims, why `6577f4b` cannot have produced it, and whether the numbers
  reproduce. Existing manifests are **not** edited.
- `docs/audit/AUDIT_g0.md`, `docs/spec/SPEC_g0.md`, `docs/gen/DECISIONS.md`.
- 34 regression tests across `tests/test_provenance_g0.py`,
  `tests/test_claim_surface_g0.py`, `tests/test_ohmic_gradient_g0.py`.

### Fixed

- **PROV-02 (CRITICAL) — dirty detection was blind to untracked files.**
  `git_is_dirty()` ran `git status --porcelain --untracked-files=no`. Measured on
  a scratch repository, a tree missing three source modules returned `False`. A
  manifest could therefore report a tree missing six source modules and 83% of the
  test suite as clean, indistinguishable from a fixed typo. Untracked files now
  count; `tracked_modified`, `untracked` and `tree_digest` are recorded as separate
  manifest fields; the flag is derived from the counts so the two cannot disagree.
  Digest cost measured at 28 ms over 166 files / 4.1 MB.
  Reproduce: `pytest tests/test_provenance_g0.py` (16 tests).

### Changed — claims corrected or withdrawn

- **Built-in potential `2.8e-7` → `7.24e-14` (withdrawn, not corrected).** The
  published figure measured the *pre-audit* solver: `git archive 6577f4b` and
  re-running reproduces `2.7558e-07` exactly. It described a program the project
  no longer ships. `CLAIM_EVIDENCE_MATRIX` X15.
- **Mass action `7.6e-6` → `2.93e-9`**, same cause. X16.
- **Equilibration gain `1.32e-2 → 7.62e-6` (1730×) → `6.77e-3 → 9.7e-10` (7.0e6×).**
  The starting point was sound (1.95× from measured); the endpoint understated the
  improvement by ~4000×. X17.
- **`RELEASE_READINESS` "Reference solver validated ✅"** cited exactly the two
  withdrawn figures. The gate was green on evidence from a superseded program.
- **Identifiability is now labelled `local` wherever it is stated** (README rows
  51, 70, 267, 340; `RELEASE_READINESS` 72, 189), with its operating point, noise
  level, parameterisation dimension and observation count (PH-21). Global,
  sampling-based non-identifiability remains **unmeasured**. X18.
  One instance in `papers/draft.md:255` is **parked**, not fixed — that path is
  operator-protected; it is pinned by a test that fails if the count moves in
  either direction.

### Verified — no change required

- A full re-run of `scripts/run_results.py` (2500 epochs, M=5, no `--quick`)
  reproduced **all 174 numeric leaves bit-identically**: C1 interpolation
  `0.027834281028660313`, C2 extrapolation `0.3818233071446869`, C3 family
  transfer `0.8423089146208244`, C4 `9.961050987243652` decades. The headline
  science is exactly reproducible; only its provenance chain was broken.
- `outputs/results/manifest.json` agrees with its `results.json` on all 102 shared
  numeric leaves — 0 mismatches. Nothing was fabricated.

### Fixed — GRAD-02 / GRAD-03, promoted candidate g0c2

- **`ohmic_boundary_values` returned NaN gradients across the documented doping
  envelope.** `torch.where` evaluates both branches; for large positive `C_s`,
  `-C + sqrt(C²+4)` underflows to exactly `0.0`, the discarded branch is `inf`,
  and backward computes `0 × inf = NaN` in the *selected* branch. Bisected onset
  `C_s = 1.3922e8` (N = 1.3922e24 m⁻³) in float64 — the top **21.4%** of the
  solver's own 1e21–1e25 m⁻³ range.

  The generation-0 **falsifier** then broke that scoping: networks here train in
  float32, where cancellation arrives at `C_s = 7.079e3` — *below* the envelope.
  Sampling the envelope in float32, **41 of 41** points returned NaN. 100%, not
  21.4%. Filed as GRAD-03.

  Fixed by reformulation (`M-01`): `log n = asinh(C/2)`, `log p = −asinh(C/2)`.
  Branchless, exact in every dtype, derivative `1/sqrt(4+C²)` finite everywhere.
  Measured after the fix, over 402 envelope points in both dtypes:

  | | before | after |
  |---|---|---|
  | non-finite gradients, float64 | 44 / 402 | **0** |
  | non-finite gradients, float32 | 201 / 402 | **0** |
  | gradient rel. error, float64 | 4.393e-16 | **0.000e+00** |
  | gradient rel. error, float32 | 1.629e-07 | **8.190e-08** |
  | mass-action deviation | 3.664e-15 | **2.220e-16** |

  **No published number changes.** Measured, not inferred: `losses.boundary_residuals`
  receives boundary doping as data with no `requires_grad_` (`trainer.py:262`), so a
  float32 PINN backward at N = 1e21, 1e24 and 1e25 m⁻³ produced non-finite gradients
  in **0 of 26** weight tensors. `D1` and `ADR-0004` are **not** confounded. The
  defect fired only where doping itself carries a gradient — inverse design, and the
  Jacobian the identifiability result is built on.

  Reproduce: `pytest tests/test_ohmic_gradient_g0.py` (41 tests).
  AH-08 pre-fix outcome recorded: 17 failed / 22 passed.
  Three competing candidates were built and measured; see `docs/gen/CANDIDATES_g0.md`.

### Known open
- **CI-01 reopened** — `.github/workflows/ci.yml` had never been committed, so CI
  has never run, yet `AUDIT_MASTER` recorded the finding as VERIFIED.
- **PROV-03 (permanent)** — the adopted tree has no attestable origin. Nothing in
  git records who produced this code or against what evidence. This does not close.

## [Unreleased] — second audit cycle (2026-08-19)

The first audit cycle closed 40 findings and left the project at "release
ready with documented limitations", with three areas explicitly not
release-grade. This cycle re-ran the evidence instead of inheriting it. It
found one CRITICAL solver defect that had survived the first cycle's 161-test
suite, closed all three not-release-grade areas, and produced four new
measured results — three of them negative.

### Fixed

- **BUG-13 (CRITICAL) — round-off stagnation was reported as divergence,
  which silently aborted bias continuation.** The Gummel carrier-convergence
  test was *relative*, applied to an array spanning 16 decades; entries far
  below the array maximum can never reach a 1e-8 relative tolerance, so the
  solver reported failure on states whose potential had converged to 1e-12.
  Because `auto_continuation` breaks on the first ramp step that reports
  failure, `solve()` then returned the **cold-start** state — currents wrong
  by 3–5 orders of magnitude at 1e24–1e25 m⁻³, and **wrong in sign** under
  reverse bias. Fixed by distinguishing round-off stagnation from divergence
  using a threshold that separates the two measured populations by *eleven
  orders of magnitude* (so it is not tuned — any value in [1e5, 1e13] gives an
  identical verdict). After the fix, 90/90 solves converge across doping
  1e21–1e25 m⁻³ × N ∈ {201,401,801} × bias ∈ {0, 0.3, 0.6, 0.9, −2, −5} V, and
  every point the oracle certifies is grid-converged to ≤0.35%.
  *This did not change any published number* — the headline experiment's
  envelope (doping ≤ 8e22, bias ≤ 0.6 V) sits outside the affected band, and
  H1/H3/H5 are bit-identical before and after.
- **BUG-14 — all text I/O used the platform default encoding.**
  `scripts/build_notebooks.py` could not run at all on Windows (it died on the
  first `φ` and truncated the notebook it was writing), so "regenerate the
  notebooks" was an impossible procedure on the platform the project's own
  manifests record. Swept and fixed across 15 files: 24 `open(..., mode)`
  calls, 10 `open(path)` calls (the form the first sweep missed), 2
  `read_text()`, 1 `write_text()`.
- **`current_is_trustworthy()` ignored the convergence flag.** At +100 V a
  non-converged state carrying `I = 3.0e10 A/m²` had a high SNR and was
  reported trustworthy. Every in-tree caller already wrote
  `converged and current_is_trustworthy()`, so folding the check in cannot
  loosen any result — it removes a footgun for callers who did not.
- `make check-install` hard-coded the POSIX `venv/bin/` path and could not run
  on Windows.

### Added

- `bayespinn_inv.bayesian.surrogate_uq` — `MCDropoutSurrogate` and
  `SWAGSurrogate` over the **surrogate**. The reason MC-dropout and SWAG had
  never been benchmarked is that both wrapped `ForwardPINN`, the superseded
  forward model. All three backends now return the same `SurrogatePrediction`.
- `bayespinn_inv.data.splits` — the single definition of the experimental
  protocol (five disjoint level splits, SG label generation, trust filtering),
  so `run_results.py` and every new experiment build data one way.
- `bayespinn_inv.active_learning.design` — D-optimal, E-optimal and
  null-space experiment design. Textbook criteria (Fedorov 1972; Atkinson &
  Donev 1992); **no novelty claimed**.
- Six new experiments, each writing a provenance manifest:
  `run_uq_benchmark.py`, `run_uq_tuning.py`, `run_experiment_design.py`,
  `run_gradient_fidelity.py`, `run_identifiability_robustness.py`,
  `run_pinn_vs_surrogate.py`. All wired into the `Makefile`.
- **79 new tests** (161 → 240), including regression coverage for BUG-13,
  BUG-14, the trust-flag fix, the UQ backend interface contract, split
  leakage invariants, the design criteria against analytically-known answers,
  and a GaAs PN junction.
- CI now runs a **Windows** job (BUG-14 was Windows-only and a Linux-only
  matrix could not see it), lints `scripts/`, and smoke-runs the notebook
  generator.
- `ADR-0004` (the PINN is legacy), `ADR-0005` (the ensemble is the UQ
  backend).

### Measured — new results

- **GRAD-01: surrogate accuracy does not imply surrogate gradients.** A
  surrogate that fits I–V to 2.6% median relative error has directional
  derivatives agreeing with the SG Jacobian **only inside the identifiable
  subspace**: mean cosine **+0.504 inside vs −0.001 outside**, across four
  device families. A 33× increase in training budget cuts the value error 4.5×
  and leaves the outside-subspace agreement at zero — so this is ill-posedness,
  not undertraining. `make gradient-fidelity`
- **DES-01: uncertainty-driven acquisition is *worse* than random.** Over 4
  device families × 5 budgets × 12 seeds, scored on identifiable rank:
  `max_std` **−0.31** (2 wins / 9 losses), `d_optimal` and `null_space`
  **+0.39** (5 wins / **0 losses**). Supersedes the earlier "no
  distinguishable advantage" framing. `make experiment-design`
- **UQ-01: the deep ensemble wins after a fair hyperparameter search.** σ
  inflates **21.3×** off-distribution against a 12.1× error inflation; tuned
  MC-dropout manages 1.4× and tuned SWAG 2.5× against ~12–13×. A
  budget-matched ensemble, trained *faster* than either, still beats both.
  `make uq-benchmark`, `make uq-tuning`
- **PINN-01: the pure-physics PINN predicts essentially zero current** —
  100.00% median *and* p90 relative error at 27× the surrogate's training
  cost, while its own self-consistency diagnostic reads 0.03. Converged, and
  wrong. `make pinn-vs-surrogate`
- **IDENT-02: the identifiability result survives, and the rank does not grow
  with the parameterisation.** 88 measurements across six axes plus a
  bootstrap: rank 1–6, median 3; **3–4** at the reference conditions.
  P = 8 → 32 leaves it at 3–4, so it is a property of the measurement rather
  than of the discretisation. `make identifiability-robustness`

### Changed

- **The headline identifiability claim is corrected from "3–5 of 16" to "3–4
  of 16" (reference conditions), with the full range 1–6 (median 3) reported.**
  The previous value came from a single run against the pre-BUG-13 solver.
- All twelve notebooks regenerated and **re-executed**; the stale narrative
  numbers ("13 orders of magnitude", "~4% error", "~500× speed") corrected *in
  the generator*, so they cannot drift back.
- The project no longer describes its forward model as a PINN. See ADR-0004.
- `docs/architecture.md` carries a banner saying which packages are legacy.

### Known limitations

See [`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md). The largest open
scientific risk is unchanged: the identifiability analysis is **local** (a
Jacobian at an operating point); global, sampling-based non-identifiability is
not addressed.

---

## [0.1.0-dev] — first audit cycle

40 findings; 12 numbered solver defects, six CRITICAL, all present while the
pre-existing 42-test suite passed. Two documented "physics limitations" turned
out to be solver bugs. See `docs/AUDIT_MASTER.md` §1–6c.
