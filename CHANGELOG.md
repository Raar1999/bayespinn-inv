# Changelog

All notable changes to this project. Numbers here are measured, and each entry
names the command that reproduces it. Findings are tracked in
[`docs/AUDIT_MASTER.md`](docs/AUDIT_MASTER.md).

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
