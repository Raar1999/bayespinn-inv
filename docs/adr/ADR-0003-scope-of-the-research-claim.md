# ADR-0003 — Scope of the research claim: systems contribution, not a new method

**Status:** Accepted · **Date:** 2026-08-19 · **Relates to:** docs/NOVELTY_AUDIT.md, AUDIT_MASTER DOC-04, CITE-01

## Context

The paper draft claimed the project is *"the first to evaluate Bayesian PINN
calibration quantitatively for semiconductor inverse problems"*, and the README
framed the work as a novel methodological combination. Neither claim had a
prior-art review behind it.

The audit charter requires that novelty be established against the literature
before it is asserted, and prefers a defensible systems contribution over a
fabricated methodological one.

## Findings from the prior-art review

Inverse doping recovery from terminal measurements is a **mature field with a
dedicated literature**, not an open problem:

- Burger, Engl, Leitão & Markowich, *Identification of doping profiles in
  semiconductor devices*, Inverse Problems **17**, 1765 (2001) — the canonical
  formulation, with identifiability and ill-posedness results.
- Burger, Engl, Leitão & Markowich, *On inverse problems for semiconductor
  equations*, Milan J. Math. **72**, 273 (2004) — voltage–current-map
  measurements; uniqueness and non-uniqueness for regularized solutions.
- Bayesian inversion for doping profile identification, arXiv:2408.11485 (2024).
- Data-driven / ML solutions for doping reconstruction (2024).
- Inverse device modelling for doping profiling dates to *Solid-State
  Electronics* (1990, 1991).

Every ML component (PINNs, Fourier features, NTK weighting, deep ensembles,
MC-dropout, SWAG, temperature scaling) is standard and cited as such.
Jacobian-SVD local identifiability is a textbook method (Aster, Borchers &
Thurber, ch. 4).

**No component of this project is methodologically new.**

## Options considered

| Option | Assessment |
|---|---|
| **A. Keep the "first to…" framing** | Rejected. Unsupported, and contradicted by arXiv:2408.11485. |
| **B. Invent a new method to justify a novelty claim** (e.g. an uncertainty-aware active inverse-design loop) | Rejected. It would be a combination of standard parts with no demonstrated benefit — and the project's *existing* active-learning result turned out on inspection not to be active learning at all. Adding a second unvalidated mechanism to fix an unvalidated claim is the wrong move. |
| **C. Drop all research framing and present a code release** | Rejected. It undersells genuinely useful measured results. |
| **D. Reframe as a validation / reproducibility contribution and back it with measurements** | **Chosen.** |

## Decision

The project claims:

> An open, tested, reproducible implementation of an SG-supervised
> differentiable forward surrogate for 1D drift–diffusion, together with a
> validated numerical oracle that reports its own trustworthy range, and a
> self-checking identifiability analysis quantifying how many doping degrees of
> freedom terminal I–V can determine for four device families.

It explicitly does **not** claim first-ness, methodological novelty for the
identifiability analysis, or that active learning helps.

The identifiability analysis is included because it converts an assertion the
repository was already making ("profile recovery is ill-posed") into a measured,
validated, reproducible number — not because it is new.

## Consequences

- Paper draft abstract and contributions rewritten; the "first to" sentence and
  the `X`/`Y`/`Z` placeholders removed.
- README results table reframed around measured quantities with intervals.
- The unverifiable *Beucler et al. (2022)* citation removed and replaced with
  the actual provenance (Rudin–Osher–Fatemi for TV; Burger et al. for the
  inverse doping formulation).
- The honest headline for a workshop submission becomes: a carefully audited
  pipeline overturned four of its own published claims and two documented
  "physics limitations" that were in fact solver bugs. That is publishable, and
  it does not require inventing a method.

## Validation

`docs/NOVELTY_AUDIT.md` carries the prior-art table, the candidate-contribution
assessment (including the rejected candidates and why), and the measured
identifiability results with their three validation checks.
