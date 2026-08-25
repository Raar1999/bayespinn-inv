# ADR-0007 — The oracle arbitrates global identifiability; the surrogate may only propose

- **Status** Accepted
- **Date** 2026-08-25
- **Generation** 6
- **Supersedes** nothing. **Superseded by** nothing.
- **Findings** seed item `S-1` · **Spec** `SPEC-g6-1` … `SPEC-g6-5`
- **Rules** `PH-21`, `PH-22`, `PH-13`, `PH-19`, `AH-13` … `AH-16`

## Context

Every identifiability number this project publishes is **local**: the numerical
rank of the forward Jacobian at one operating point. 3–4 of 16 doping degrees of
freedom at 2% noise; 1–6 (median 3) across 88 measurements spanning six axes; and
the rank does not grow with the parameterisation (P = 8 → 32 leaves it at 3–4).

A local rank says which directions are flat *here*. It says nothing about whether
a distant profile fits the same I–V equally well. Nothing in the repository has
ever ruled that out, and generation 0 made the gap explicit rather than closing
it — every statement of the result now carries the word *local* and its regime.

Generation 6 is the first attempt to measure the global question. Doing so
requires choosing an instrument, and that choice is the whole decision.

## Decision

**The SG oracle arbitrates every global claim. The surrogate may propose and may
never arbitrate.**

Two independent measurements force this, and either would be sufficient:

1. **`GRAD-01`.** Surrogate directional derivatives agree with the oracle *only
   inside the identifiable subspace*: mean cosine **+0.504 inside, −0.001
   outside**, unchanged by a 33× training-budget increase. A global study probes
   precisely outside that subspace. Using an instrument that is measurably
   uninformative there, to measure what is there, would not be a shortcut — it
   would manufacture the conclusion.

2. **`PH-22`, measured this generation.** The surrogate path is float32 and cannot
   represent doping differences below **~1e-7 relative**; the float64 oracle
   round-trips to **1.678e-16**. A float32 instrument cannot resolve the
   degeneracies the study exists to find, independently of what it was trained on.

The temptation is real and quantified: the surrogate is **152× faster**, which
would turn a 45-minute study into 18 seconds. That is exactly why the rule is
structural rather than advisory —
`tests/test_global_identifiability_g6.py::TestArbiterCompliance` fails if
`inverse/global_identifiability.py` acquires any import path to the surrogate
package, checked at the AST level so the module's own docstring explaining the
exclusion cannot satisfy it.

### What the module provides

Three new public symbols, the whole `E-4` budget for this generation:

- **`GlobalStudyConfig`** — frozen. Carries the parameterisation dimension `d`,
  the prior support, the observation set, both floors, and the seed. Its
  `prior_hash()` is recorded **before sampling** (`AH-14`).
- **`witness_search`** — hunts for two profiles far apart in parameter space whose
  oracle observations differ by less than the distinguishability floor. A found
  pair is a concrete, checkable example, reported with both profiles and both I–V
  curves — not a rank.
- **`contraction_spectrum`** — prior → posterior variance ratio per direction.

### Floors are reported, never subtracted

The **distinguishability floor** is `max(noise floor, solver discretisation
floor)`, and both components are reported separately (`PH-13`, ADR-0002). Measured
for the adopted observation set `V ∈ [0.15, 0.90]`:

| floor | value |
|---|---:|
| solver discretisation | 1.5e-03 |
| measurement noise | 2.0e-02 |
| **distinguishability** | **2.0e-02** |

Two profiles closer than this are indistinguishable *by this instrument and this
solver*. Calling them identifiable would be a statement about arithmetic, not
about the device.

The observation set itself is a measured choice, fixed before any search
(`AH-16`): below `V = 0.15` the oracle's grid-refinement differences stop
converging, because the current is small enough that the solver's own noise floor
competes with discretisation.

### Contraction is reported against a tolerance sweep, not a single number

The first implementation weighted prior samples by a Gaussian likelihood at the
instrument's 2% noise and reported one variance ratio per direction. On a smoke
run it returned **"4 of 4 directions contract"** with an **effective sample size
of 1.0** — the weight had collapsed onto a single draw, the weighted variance had
gone to zero, and every direction trivially "contracted".

That number was an artefact of the estimator, not a property of the device, and it
is the S-1 equivalent of quoting an ECE below its M=5 floor (`API-04`). It was
discarded rather than reported.

The design that replaced it sweeps the tolerance, reports the effective sample
size at each, and marks any row below an ESS floor of 20 as **unsupported**. The
collapse becomes visible instead of becoming a result. This is deliberately
analogous to the existing rank-vs-instrument-quality result (`C13`), which reports
rank as a function of noise rather than at one noise level.

## Consequences

**Global studies are ~150× more expensive than the surrogate would make them.**
Measured budget unit: one oracle I–V curve over 16 biases at N=301 costs **0.36 s**,
so ≈ 10,000 curves per hour. The pre-registered `n` for generation 6 (7,000 curves,
≈ 42 min) is set from that measurement and fixed in `SPEC_g6.md` before the first
production sample. If a future study cannot afford its `n`, **the scope of the
claim is reduced, never the `n` behind it** (`SCI-03` precedent).

**Sampling once and comparing pairwise is what makes it affordable.** `n` oracle
solves yield `n(n−1)/2` candidate pairs, so 2,000 curves examine ~2 million pairs.

**A failed search is not a result about the world.** `AH-13`: "no witness found at
budget B" and "identifiable" are different sentences, and only the first is
measured. The verdict string carries the budget so the distinction cannot be lost
in quotation.

**Prior importance sampling may simply not reach the instrument's noise level.**
That is a limitation of the method, and reporting it as one is the honest outcome.
A future generation wanting contraction at 2% noise needs sequential Monte Carlo
or MCMC, not a larger `n` — the required sample count grows exponentially in `d`.

## Alternatives rejected

- **Arbitrate with the surrogate and validate a sample on the oracle.** The
  sampling would still be steered by an instrument that is measurably
  uninformative in the region being sampled; oracle-checking the survivors cannot
  recover what was never proposed.
- **Use the local Jacobian to define the search directions.** Circular: it would
  find degeneracies only where the local analysis already says they are, which is
  the question rather than the answer.
- **Report contraction at 2% noise regardless of ESS.** This is what the first
  implementation did, and it produced a confident, clean, wrong answer.
- **Widen the noise until the sampler behaves and quote that as the result.**
  `AH-02` in a new costume. The tolerance sweep reports every level with its ESS,
  so the reader sees what was supported and what was not.
