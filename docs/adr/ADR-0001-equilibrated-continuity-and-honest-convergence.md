# ADR-0001 — Equilibrate the SG continuity solves; make Gummel convergence honest

**Status:** Accepted · **Date:** 2026-08-19 · **Relates to:** AUDIT_MASTER BUG-03

## Context

`ScharfetterGummel1D` is the project's ground-truth oracle: every surrogate
label, every benchmark number and every inverse-design target is derived from
it. During the audit it was found to be reporting `converged=True` on states
whose electron-continuity residual equalled **100% of the current scale**.

Two independent causes:

1. The convergence test was `max|Δφ| < tol_outer` and nothing else. The
   potential is nearly insensitive to minority carriers — twelve decades below
   the majority density — so φ settled to 1e−12 by the third Gummel sweep while
   the carrier densities were still ~1% from self-consistent.
2. The continuity matrix is badly *unequilibrated*. Its row ∞-norms span
   1 → 2.5e4 (condition number only ~5.2e5), so a plain `spsolve` commits a
   large relative error on the small minority-carrier components. Instrumenting
   the iteration showed `max|np − 1|` **stagnating in a limit cycle** at ~1e−2
   and never converging; tightening `tol_outer` made the result *worse*.

## Problem

The oracle's accuracy could not be characterised, so nothing downstream could
be. Worse, the failure was invisible: `converged=True` on garbage.

## Options considered

| Option | Assessment |
|---|---|
| **A. Do nothing; document the 1% mass-action error as a limitation** | Rejected. The error is not physics, it is a linear-algebra artefact, and 1% on the minority carrier is what sets the low-bias current. |
| **B. Fix only the convergence criterion** | Rejected alone. It makes the solver honest but leaves it non-convergent — every solve would report failure. Necessary but not sufficient. |
| **C. Reformulate the continuity equations in Slotboom / quasi-Fermi variables** | Rejected *for now*. It is the textbook cure for the dynamic range, and a prototype confirmed it works (identical accuracy to option D). But it is a substantial rewrite of the solver core, changes the Dirichlet handling and the SRH linearisation, and carries real regression risk on a solver that is otherwise correct. Deferred; see ADR-0002. |
| **D. Two-sided ∞-norm equilibration of the continuity systems + fix the convergence test** | **Chosen.** |

## Decision

Apply row + column ∞-norm equilibration to both continuity systems before
`spsolve` (`solve_equilibrated`), and require the relative carrier update to
converge in addition to the potential.

Equilibration is an exact similarity transform of the linear system — it
introduces no approximation and can be applied unconditionally. It is the
standard remedy for poorly scaled systems (Higham, *Accuracy and Stability of
Numerical Algorithms*, 2nd ed., ch. 7).

A prototype confirmed that Slotboom column-scaling (option C) and generic
two-sided equilibration give **identical** accuracy here (both 7.61e−6), so the
cheaper and safer option was taken. Equilibration also cannot overflow, whereas
Slotboom scaling by `exp(φ)` would for large reverse bias.

Additionally: best-iterate tracking with stagnation detection, because past the
round-off floor further Gummel sweeps *degrade* the answer (equilibrium current
drifted −7.2e−7 → −2.2e−6 A/m² between 3 and 800 sweeps).

## Consequences

**Positive**
- Mass-action violation at equilibrium: **1.32e−2 → 7.62e−6 (1730×)**.
- Quasi-Fermi levels flat to 8.3e−10 at equilibrium (previously not flat).
- `converged` now means something. The unequilibrated path correctly reports
  `converged=False`.
- Over-iteration no longer degrades the result.

**Negative**
- 13-bias continuation sweep: **119 ms → 164 ms (+38%)**. Accepted — a 38% cost
  for a 1730× accuracy gain, on a solver that runs in milliseconds.
- `SGConfig` gained `tol_carrier`, `equilibrate`, `stall_patience`. Defaults
  preserve the old *interface*; behaviour deliberately changes.
- Numbers produced before this change are not reproducible from it. All
  committed results were regenerated.

## Validation

`tests/test_sg_numerics.py::TestGummelConvergenceIsHonest` — mass action
< 1e−4, flat quasi-Fermi levels, `equilibrate=False` demonstrably worse by
> 100×, an under-budgeted solve reports `converged=False`, over-iteration does
not degrade. `test_core_invariants.py::test_mass_action` tightened 5e−2 → 1e−4.

---

## Dated pointer — 2026-09-07 · the `1730×` in this record is withdrawn

**This ADR is not corrected.** `1730×` was true on 2026-08-19, on the solver as
it stood that day, and the decision it justifies is unchanged: equilibrate the
continuity solves. Every line above stays as written, including the two that
carry the figure.

What moved since is the solver, not the decision.
`docs/CLAIM_EVIDENCE_MATRIX.md` row `X17` withdraws the `1.32e−2 → 7.62e−6`
pair; row `S1` carries the adopted solver's measurement in its place.
Re-measured on this tree on 2026-09-07 by running the body of
`tests/test_sg_numerics.py::TestGummelConvergenceIsHonest::test_equilibration_beats_plain_spsolve`
and reading both sides rather than only the assertion:

| configuration | max \|np/n_i² − 1\| at equilibrium |
|---|---:|
| plain `spsolve` (`equilibrate=False`) | 6.7705e−3 |
| equilibrated (`equilibrate=True`) | 9.7290e−10 |

Same device in both rows: 1 µm silicon PN junction, N_A = N_D = 1e22 m⁻³,
N = 201, zero bias, `max_outer = 60`.

The two live sites that carried `1730×` onto the claim surface —
`papers/draft.md` §1 contribution 1 and `README.md`'s solver section — are
corrected under `COR-4` in `papers/CORRIGENDA_g6.md`. This pointer exists so
that a reader who arrives here first is not sent back out with a withdrawn
number.
