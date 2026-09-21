# ADR-0004 — The pure-physics PINN is legacy infrastructure, not a forward model

**Status:** Accepted · **Date:** 2026-08-19 · **Relates to:** `docs/forward_model_reframe.md`, AUDIT_MASTER DOC-04, RELEASE_READINESS "not release-grade" item 2

## Context

`docs/forward_model_reframe.md` argued in 2026 that the pure-physics PINN
cannot reproduce diode I–V and replaced it with an SG-supervised surrogate.
That argument was never re-measured afterwards: its numbers came from the
*pre-audit* solver, and `RELEASE_READINESS.md` recorded the PINN pipeline as
"exercised only by a 5-epoch smoke test". The conclusion was therefore
**inherited rather than evidenced**, which is exactly the state this audit
exists to eliminate. Meanwhile the package is named `bayespinn-inv` and its
description still leads with "Physics-Informed Neural Networks", so the
terminology question is not cosmetic.

## Problem

Decide whether the pure-physics PINN should receive further scientific
development, remain a secondary baseline, or be reclassified — and make the
project's terminology match whatever is true.

## Evidence gathered

`scripts/run_pinn_vs_surrogate.py` trains both models on the identical SG
labels, on the identical device family, and scores both against the SG oracle
on the identical bias points (only those the oracle certifies as trustworthy).
The PINN is given a real budget — 8000 epochs, not the 200-epoch smoke config
— and 27× the surrogate's wall-clock:

| Model | Median rel. error | p90 | Within 50% | Train time |
|---|---:|---:|---:|---:|
| SG-supervised surrogate | **2.64%** | 6.64% | 100% | 22.5 s |
| Pure-physics PINN | **100.00%** | 100.00% | 6% | 210.6 s |

A median *and* p90 of exactly 100.00% is the signature of predicting
`I ≈ 0` everywhere: `|0 − I| / |I| = 1` regardless of `I`.

The decisive detail is that this is **not a training failure**. The PINN's own
self-consistency diagnostic — `std(J)/|mean(J)|` across the domain, which is 0
for an exact steady state — is **0.03**. It has converged to a smooth,
internally consistent solution that carries essentially no current. That is
precisely the multiscale-cancellation mechanism diagnosed in
`forward_model_reframe.md`: the continuity loss is dominated by the ~1e6-scale
bulk density, and is minimised by flattening the bulk quasi-Fermi level while
the exponentially small terminal current stays in the numerical noise.

## Options considered

| Option | Assessment |
|---|---|
| **A. Invest in the PINN** (NTK weighting, quasi-Fermi output parameterisation, current supervision) | Rejected. Adding current supervision converts it into the surrogate; the remaining pure-physics variants are a research programme in their own right, out of scope, and would duplicate a capability the project already has working. |
| **B. Delete the PINN** | Rejected. It is a genuine, reproducible negative result, and `ForwardPINN` is the interface the UQ wrappers were originally typed against. Deleting it would erase the evidence and churn the API for no scientific gain. |
| **C. Keep it, keep claiming it as a forward model** | Rejected. The evidence says it is not one. |
| **D. Reclassify as legacy/supporting infrastructure; move every forward-model claim onto the surrogate; make the terminology precise** | **Chosen.** |

## Decision

1. The **SG-supervised surrogate is the forward model.** Every forward,
   inverse, UQ, calibration and experiment-design claim rests on it.
2. The pure-physics PINN is retained as **legacy infrastructure and a
   documented negative result**. It stays smoke-tested; it gets no further
   scientific development.
3. **Terminology.** The project does not have a working "Bayesian PINN"
   forward model and must not describe itself as one. What it has is a
   *Bayesian SG-supervised differentiable surrogate*. The distribution name
   `bayespinn-inv` is retained — renaming a published package identity costs
   more than it buys — but the README, package description and paper draft
   state plainly what the forward model actually is, and the physics-informed
   component is described as what it is: a regulariser and a superseded
   baseline, not the source of predictive capability.
4. The new UQ backends are attached to the **surrogate**
   (`bayesian/surrogate_uq.py`), not to `ForwardPINN` — which is why they had
   never been benchmarked (ADR-0005).

## Consequences

* One less unvalidated claim surface. The "PINN" numbers no longer need
  defending because nothing depends on them.
* `bayesian/{ensembles,mc_dropout,swag}.py` still wrap `ForwardPINN`. That is
  now explicitly legacy; the surrogate path is `bayesian/surrogate_uq.py`. The
  duplication is documented rather than removed, because removing it would be
  an API break with no scientific benefit.
* The negative result is reproducible on demand:
  `PYTHONPATH=src python scripts/run_pinn_vs_surrogate.py`.

## Alternatives rejected

Renaming the package to match the science. Considered and rejected as
disproportionate: the honest fix is accurate prose, not a new distribution
name. The README now says so in its first section rather than burying it.
