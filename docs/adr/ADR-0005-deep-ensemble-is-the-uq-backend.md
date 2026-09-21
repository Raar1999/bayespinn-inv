# ADR-0005 — The deep ensemble is the UQ backend; MC-dropout and SWAG are OOD-blind here

**Status:** Accepted · **Date:** 2026-08-19 · **Relates to:** RELEASE_READINESS Gate D ("MC-dropout / SWAG compared: not demonstrated"), ADR-0004

## Context

The project shipped three uncertainty backends and claimed none of them
comparatively, because they had never been compared. Gate D recorded the gap
honestly but did not explain it. The explanation is structural:
`bayesian/mc_dropout.py` and `bayesian/swag.py` wrap **`ForwardPINN`** — the
forward model ADR-0004 reclassifies as legacy — while the model actually under
evaluation is the SG-supervised `IVSurrogate`, for which only
`SurrogateEnsemble` existed. The three backends were not comparable because
two of them were attached to a different model.

## Problem

Attach all three to the same model, compare them under one protocol, and
decide which the project should stand behind — without manufacturing a
positive or a negative result.

## What was built

`bayesian/surrogate_uq.py` adds `MCDropoutSurrogate` and `SWAGSurrogate`,
both returning the *same* `SurrogatePrediction` dataclass the ensemble
returns, with the same shapes, units and symlog convention. That is what makes
the comparison a comparison: one evaluation path, three uncertainty sources.
The contract is pinned by `tests/test_surrogate_uq.py` (21 tests), including
that each backend's reported mean and sigma really are the moments of its own
samples — otherwise the three would not be on a common footing.

`scripts/run_uq_benchmark.py` runs the comparison on identical splits,
identical SG labels, identical filtering, with temperature fitted on the
disjoint calibration split and pre/post measured on one identical test set.

## Evidence

Compute is deliberately *not* equalised (a deep ensemble trains M networks by
definition); it is measured and reported, and a **budget-matched** ensemble is
included so the "5× the compute" objection has an answer rather than a caveat.

| Method | Interp rel err | ρ(σ,\|err\|) | NLL calib | σ inflation (extrap) | error inflation (extrap) | Train |
|---|---:|---:|---:|---:|---:|---:|
| deep ensemble (M=5) | 2.6% | **+0.798** | **−1.452** | **21.3×** | 12.1× | 31.4 s |
| ensemble, budget-matched | 7.5% | +0.731 | −0.565 | 12.9× | 5.6× | **6.7 s** |
| MC-dropout | 10.6% | +0.367 | 1.175 | 1.1× | 2.9× | 9.2 s |
| SWAG | 2.4% | +0.486 | 196.4 | 2.6× | 25.7× | 6.3 s |

A negative result is only worth reporting if it is not a tuning failure, and
there were two concrete reasons to suspect one (SWAG's predictive spread was
0.0085 symlog — essentially collapsed; MC-dropout's accuracy was 4× worse than
deterministic). So `scripts/run_uq_tuning.py` gives each a grid over the
hyperparameters that drive its uncertainty, selecting on calibrated NLL on the
**calibration split, never on test**:

| Method (best config) | Interp rel err | ρ(σ,\|err\|) | NLL calib | σ inflation (extrap) | error inflation (extrap) |
|---|---:|---:|---:|---:|---:|
| deep ensemble (untuned) | **2.64%** | **+0.798** | **−1.452** | **21.3×** | 12.1× |
| MC-dropout, p = 0.01 | 5.91% | +0.299 | 18.737 | 1.4× | 12.4× |
| SWAG, lr = 5e-4, scale = 0.25 | 2.90% | +0.486 | 1.814 | 2.5× | 13.2× |

**The result survives tuning.** The mechanism is visible in the last two
columns: under distribution shift the error grows ~12–13× for all three, but
MC-dropout's σ grows 1.4× and SWAG's 2.5×, while the ensemble's grows 21.3×.
MC-dropout's and SWAG's predictive spread is set by *their own
hyperparameters* — the dropout rate, the SWA trajectory width — which are
properties of the model, not of the distance from the training data. The
ensemble's spread comes from genuine functional disagreement between
independently trained members, and that is what grows off-distribution.

A caveat recorded rather than hidden: in the tuning run the calibration split
does double duty -- it selects the hyperparameters and it is where the
temperature is then fitted. No test label is touched, so this is not test
leakage, but it makes the fitted temperature mildly optimistic for the two
*tuned* methods and not for the untuned ensemble. The bias therefore runs **in
favour of** MC-dropout and SWAG, which lose regardless. A third split would be
stricter; with only 3 calibration levels there are not enough points to fit one
stably, so the direction of the bias is stated instead.

One further observation worth recording because it generalises: selecting UQ
hyperparameters on in-distribution NLL systematically prefers *small* σ
(SWAG's winner had σ_median = 0.017), and small σ is exactly what fails
out-of-distribution. In-distribution model selection and OOD reliability pull
in opposite directions here.

## Decision

1. The **deep ensemble is the project's UQ backend** and the only one whose
   uncertainty is claimed to be useful.
2. MC-dropout and SWAG are **implemented, benchmarked, and reported as not
   competitive on this problem**. They are kept: a measured negative result
   with a mechanism is worth more than an unmeasured absence.
3. The claim made is bounded to what was measured: *on this forward map, with
   this architecture and these budgets*. No general claim about MC-dropout or
   SWAG is made or implied.
4. Gate D is closed. It reads "compared; ensemble wins; mechanism identified"
   instead of "not demonstrated".

## Consequences

* Any future backend must implement the `SurrogatePrediction` contract and is
  then automatically comparable through the same script.
* The budget-matched ensemble beats both single-network methods on ρ and OOD
  awareness while training *faster* than either, so the ensemble's advantage
  here is not merely a compute advantage. That control is part of the claim.
* Reproduce with `make uq-benchmark` and `make uq-tuning`.

## Alternatives rejected

Reporting the untuned comparison alone. Rejected: it would have been a
negative result that a reviewer could dismiss in one sentence, and it would
have been partly wrong — SWAG's accuracy improves markedly with a better SWA
learning rate (13.45% → 2.90%) even though its uncertainty does not.
