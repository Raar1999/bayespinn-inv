# Close — the free check, three ratified corrections, `WIT-02`, and the spine

**Status** the loop is closed. `T-1` was reached at generation 6; generations
7-R, 8, 9 and 10 were bounded generations ordered post-termination, and the
ruling of 2026-08-26 (closing) ends the technical work. **No generation 11.** No
`S-5`, no `S-2`, no fourth chart, no minimum-energy path.

This document is what the closing ruling asks for and nothing beyond it: §5's
one free check, the corrections of §1 recorded as ratified, `WIT-02` enacted as
§2 defines it, §3's consequence carried all the way through the claim surface,
and §6's spine as the measurements now support it. `R-3` reserves `papers/**`,
so the spine here is the spine — not an edit to the draft.

**Measurement conditions, once, for every number below.** Nothing was solved for
this document. Every number already existed in `outputs/g9/` and `outputs/g10/`
at machinery commit `e05d463`, and the arithmetic that re-reads them is
`scripts/run_close.py` → `outputs/close/spectrum_shape.json`.

Oracle-arbitrated, 301-node grid. **Prior** log-uniform on `|doping|` over
1e21–1e23 m⁻³ per anchor, hash `ba11a6d5357388cb…`, unchanged since generation 6.
**Noise model** relative, i.i.d., at a **noise level of 2%** (`noise_rel = 0.02`),
which is also the **distinguishability floor** — two devices closer than
`2.0e-02` in the observable are the same device to this instrument. **Observation
set** 16 bias points over 0.15–0.90 V unless a narrower window is named.
**Discretisation floor** `1.5e-3` relative, measured by the convergence sweep and
never removed from a reported number (`ADR-0002`). Every witness count quoted is
admissible under `WIT-01` at an admissibility ratio of 1.000; see
`outputs/g10/wit01.json` and `docs/G10_RESULT.md` §3.

---

## 1. The one free check — `σ₂…σ₄` rise; the spectrum flattens

> §5. *Does the 1 → 4 climb come from `σ₂…σ₄` **rising** with window width, or
> from `σ₁` falling so the cutoff moves relative to a fixed spectrum shape? Plot
> the normalised spectrum against window width. Arithmetic on existing artefacts
> only. Reported either way in one paragraph.*

**The answer, in one paragraph.** It is the first branch, and not marginally.
The operational cutoff is *absolute* — `rank = #{σᵢ > log10(1 + 0.02)}` — so the
two readings separate by sign alone, with no threshold to choose. Across the
nine bias windows of `rank(observation set)` (0.10–0.75 V about a fixed 0.525 V
centre, 16 bias points, `outputs/g9/rank_obs.json`), the head `σ₁` is nearly
fixed: it moves by a factor of **1.195** at the generation-8 device and
**1.148** at `device_p50`, and it moves **downward** (`spearman` −1.000 and
−0.983), which is the wrong direction to raise a count against a cutoff that
does not scale with it. Had the spectrum been rigid, widening the window would
have *lowered* the rank. What actually happens is that the trailing values climb
toward the head: `σ₂`, `σ₃` and `σ₄` rise by factors of **47.5**, **55.4** and
**315** at the first device and **20.9**, **87.1** and **535** at the second,
measured in the *normalised* spectrum `σᵢ/σ₁`, and the identity
`Δlog σᵢ = Δlog σ₁ + Δlog(σᵢ/σ₁)` puts **95.6%–97.9%** of each one's motion in
the shape term at every device and every index. Seen as one number, the
spectrum's log-decay slope over the leading five values halves — **−1.265 →
−0.552** and **−1.261 → −0.525** — while the largest multiplicative gap behind
the head collapses from **230.6×** to **4.99×** and from **87.8×** to **5.11×**,
which is the same fact told twice: a narrow window produces one dominant
direction with two orders of magnitude of empty space behind it, and a wide
window produces a smooth decay with no population boundary in it at all. So the
rank climb is the spectrum **flattening**, not the head sliding — and the
control the measurement already contained agrees, because along the *spacing*
axis, where the rank does not move at all, the same slope moves by 2.1% and
2.8%.

**What this is, and is not.** It is a **description**, not a test. The question
was asked after the spectra were on disk, so there is no pre-registration and
none is claimed (`AH-14`). Three things stand in its place and none of them is
an intention: the decomposition is an **identity** with no free parameter, so
the split between scale and shape cannot be tuned; the answer is a **sign**, so
`PH-11` has no cutoff to forbid; and the control axis was fixed by `SPEC-g9-2`'s
design a generation earlier rather than chosen here. It does not say *why* the
spectrum flattens. `MECH-01` stays open, one step narrower than generation 10
left it: not "why does the window set the rank", and not "why is `v₁` fixed
while the others cross" either, but **why does widening the bias window compress
the sensitivity spectrum toward its own leading direction**.

### 1.1 The normalised spectrum against window width

Chart G at `d=16`, generation-8 operating point. `σᵢ/σ₁`, so the head is 1.000
by construction and every column is shape. Full table for both devices in
`outputs/close/spectrum_shape.json`.

| width (V) | rank at 2% | slope | `σ₂/σ₁` | `σ₃/σ₁` | `σ₄/σ₁` | `σ₅/σ₁` ‡ | largest gap |
|---|---|---|---|---|---|---|---|
| 0.10 | 1 | −1.265 | 4.34e−03 | 7.47e−04 | 3.89e−05 | 4.99e−06 | 230.6× |
| 0.15 | 1 | −1.081 | 5.84e−03 | 2.29e−03 | 1.47e−04 | 2.49e−05 | 171.3× |
| 0.20 | 2 | −0.948 | 7.06e−03 | 5.67e−03 | 4.24e−04 | 7.45e−05 | 141.7× |
| 0.30 | 3 | −0.795 | 2.26e−02 | 8.56e−03 | 2.73e−03 | 3.06e−04 | 44.3× |
| 0.40 | 4 | −0.666 | 5.11e−02 | 1.18e−02 | 8.54e−03 | 1.15e−03 | 19.6× |
| 0.50 | 4 | −0.606 | 8.96e−02 | 2.04e−02 | 1.07e−02 | 2.69e−03 | 11.2× |
| 0.60 | 4 | −0.576 | 1.33e−01 | 2.86e−02 | 1.15e−02 | 4.49e−03 | 7.54× |
| 0.70 | 4 | −0.558 | 1.85e−01 | 3.78e−02 | 1.21e−02 | 6.39e−03 | 5.41× |
| 0.75 | 4 | −0.552 | 2.06e−01 | 4.13e−02 | 1.23e−02 | 7.12e−03 | 4.99× |

‡ **reported, not claimed.** See §1.3.

### 1.2 The climb is not a property of the cutoff

`rank_cutoff_record` writes `rank(cutoff)` over eight noise levels. At three of
them — `noise_rel` 1e−3, 1e−4 and 1e−6 — the count is capped by
`resolvable_rank` in at least one cell, so the curve there reports the
estimator's own floor and not the spectrum; **which three is measured**, by
recounting `#{σ > cutoff}` and comparing against the recorded rank, rather than
chosen. At the five that survive — 0.20, 0.10, 0.05, 0.02, 0.01 — the rank is
**non-decreasing in width in all ten device-cutoff sequences and strictly higher
at 0.75 V than at 0.10 V in all ten**. The flattening is visible at every
defensible cutoff; the specific integers 1 and 4 are properties of the 2% one.

### 1.3 A defect this check found in its own first draft

The first version of `scripts/run_close.py` claimed five indices. Control `C3`
compares every quoted singular value against the smallest cutoff the artefact
itself marks resolvable, and it **failed in 4 of the 18 width cells**: `σ₅` sits
at or below the estimator's spectral floor at both 0.75 V windows, at 0.15 V for
the generation-8 device and at 0.50 V for `device_p50`. Those are values read
out of estimator noise.

The repair was not to loosen the control. The claim stops at `σ₁…σ₄` — the
indices the rank is actually made of — which clear the probe in all eighteen
cells at a worst margin of **1.51×**; `σ₅` is still reported, still in the table
above, and excluded from the verdict with its four cells named in the artefact.
`tests/test_spectrum_shape_close.py::TestTheVerdictRestsOnlyOnResolvableValues`
pins that the excluded cells stay named, so the defect cannot be tidied away by
deleting the row that recorded it.

The floor probe is **coarse**: it is the smallest grid cutoff marked
`cutoff_below_spectral_floor = false`, and that grid steps by factors of 2 to
100. It bounds the floor from above without re-deriving it, which would need the
Jacobian and therefore a solve. A tighter bound is not available under §5's
constraint and is not claimed.

### 1.4 Controls

| | control | result |
|---|---|---|
| `C1` | generation 9's and generation 10's width curves are the same spectra | **PASS**, bit-identical at both devices |
| `C2` | the rank at the operational cutoff is the raw count, not the `resolvable_rank` cap | **PASS**, 18 of 18 cells |
| `C3` | nothing the verdict rests on is estimator noise | **PASS** at `σ₁…σ₄`, worst margin 1.51×; **fails at `σ₅`**, which is why the claim stops at four |
| `C4` | the axis that does **not** move the rank | **PASS** — `α = 0` and `width = 0.75` are one observation set reached by two code paths and their spectra agree exactly; along the whole spacing axis the rank is fixed and the slope moves 2.1% and 2.8% against width's 56% and 58% |

`arithmetic_only`: `new_solves = 0`, and it is checkable rather than asserted —
`tests/test_spectrum_shape_close.py::TestThisRanNoSolver` parses
`scripts/run_close.py`'s AST and fails if it imports or calls anything that can
reach the oracle. The guard is written over the AST and not over the text
because the module's own docstring names the package in the sentence saying it
does not import it, and a text search would read that sentence as the violation
it describes.

---

## 2. Three ruling premises, corrected before the fact and now ratified

All three corrections were made and hashed in generation 10 and are carried in
`LOOP_STATE_v7.json` under `ruling_premises_corrected`. The closing ruling §1
ratifies all three. They are listed here only so the ratification has a home.

| | premise | status |
|---|---|---|
| a | `SPEC-g10-2`'s falsifier, as the generation-10 ruling stated it, was **inverted** | ratified as inverted. The outcome indicating a dimension effect is the one measured: both `d=16` cells basins, only `d=4` a ridge |
| b | the pairs that separate under refinement are **not** the nearly-coincident ones | ratified. What predicts survival is **headroom** against the distinguishability floor: the 7 survivors are exactly the 7 smallest distances at `N=301` (max 0.01844) and the 6 that separate are the 6 largest (min 0.01873), against a floor of 0.02 |
| c | `WIT-01` read literally rejects almost every real witness | ratified; the implemented reading applies the rule to the separation that *qualifies* the pair |

**(a) is the one that mattered procedurally.** It was registered with its hash
*before* the third barrier set was measured, which is what makes it a correction
rather than a reading of the result — the correction predates the number it
would otherwise be accused of explaining.

**No margin band was adopted for (b), and the reason is recorded rather than
left implicit.** The observed split sits between 92.2% and 93.65% of the floor:
1.4 percentage points. A threshold chosen inside a band that narrow is tuned,
and `PH-11` forbids it. `WIT-02` below is what replaces it.

---

## 3. `WIT-02` enacted — refine, do not threshold

**Enacted** closing operator ruling of 2026-08-26 §2. Full text and enforcement
in `docs/RULES_ENACTED.md`.

> Every witness is refined before it is counted. Not the ones near the floor —
> all of them.

`WIT-01` stays for the sub-grid case it does catch. It is not withdrawn and it
is not sufficient: retro-applied to every committed set it removes **nothing**
(admissibility ratio 1.000 in all three charts), because every pair qualifies on
a doping magnitude and magnitudes reach the grid exactly.

**One committed count does not satisfy `WIT-02`, and it is load-bearing.**
Globally, in chart L at `d = 16`, the 37 witness pairs have never been through
the refinement battery (`WITNESS-04`, open since generation 7). Generation 10
used them for barriers, and those barriers are what reclassified the ridge/basin
split as a dimension effect. Generation 9 put chart J's 13 witness pairs at
`d = 16` through that battery and **6 of 13 separated**. So the chart-L set is a
count whose refinement result does not exist, standing under a structural
conclusion.

Refining 37 pairs across three grids is new solving, which §5 forbids and no
generation 11 will do. The rule is therefore enacted with the non-compliance
**registered and visible on the claim surface** rather than enacted and quietly
violated:

| global witness set | witness pairs | refined under `WIT-02` | what rests on it |
|---|---|---|---|
| **chart G**, `d = 4` | 13 witness pairs | **3 of 13** (23.1%) — generation 6's battery; all 3 survive | the ridge result |
| **chart L**, `d = 16` | 37 witness pairs | **0 of 37** (0.0%) — no refinement of this set has ever been run | the chart-L basin search statement, and the dimension reading |
| **chart J**, `d = 16` | 13 witness pairs | **13 of 13** — `N = 301/601/1201`, `tol_carrier = 1e-12`; 7 survive | the junction degeneracy, the chart-J basin search statement |

The register is **measured, not asserted**: `outputs/close/wit02_register.json`
matches each refinement record to its witness pair by exact equality of the
separation in decades against `WIT-01`'s `max_separation` for the same set, so
"three of the thirteen" is a coverage figure and not a recollection. Coverage is
0.231, 0.000 and 1.000; **one set of three is compliant**.

`tests/test_witness_refinement_close.py` guards the register: it re-derives the
coverage from the artefacts, fails if a set silently becomes compliant without a
refinement artefact behind it, and requires every claim-surface document quoting
a witness count to point at the register. A rule whose only live consequence is
a paragraph admitting it is unmet is still a rule doing its job: before
`WIT-02`, "not refined" and "refined, fine" were the same sentence on the claim
surface.

---

## 4. The barrier is an **upper** bound, and the basin results are search statements

`BOUND-01`: `docs/CLAIM_EVIDENCE_MATRIX.md` said *lower* while
`LOOP_STATE_v6.json` said *upper*, with the same justification clause on both.
**Upper is correct.** Every barrier walks a straight line in one chart's own
coordinates, and a better path between the same two points can only be
*shallower*.

The closing ruling §3 follows that direction all the way, and it is asymmetric:

**The ridge result is safe and slightly strengthened.** Globally, in chart G at
`d = 4`, the median barrier between the two members of a witness pair is 8.31
log-units against a floor barrier of 8.0, with 6 of 13 witness pairs at or below
it. If that is an upper bound, the true barrier is *at most* at the floor.
Nothing to weaken.

**Both basin results are weakened to search statements.** Globally, in chart J
at `d = 16` (median 468 log-units, 59× the floor, 0 of 13 witness pairs within
it) and in chart L at `d = 16` (median 1696, 212× the floor, 0 of 37 witness
pairs within it), the measurement establishes that **no connecting path below the
floor was found along the straight line in that chart's coordinates**. It does
**not** establish that the members are separated. A shallower path may exist and
was not searched for.

`AH-13` applies in its usual direction: this is a search that did not find
something, not a demonstration that nothing is there.

**The test that would settle it, named rather than gestured at.** A
minimum-energy path between the two members — string method or nudged elastic
band against the same oracle, converged in the same chart's coordinates, with
the same floor barrier as the criterion. It was **not run**, it is out of budget
for this paper, and it is the single measurement that would convert either basin
statement from a search into a separation.

**What survives unchanged.** The *dimension* reading does not depend on the
basins being separations. It is a comparison of three sets under one metric: only
`d=4` puts pairs at the floor, and it survives path-length normalisation at 15.35
log-units per unit path against 199 and 569. Both sides of that comparison are
upper bounds, so the ordering between them is not disturbed by the bound
direction — it is disturbed by the possibility that the *slack* in the bound
differs between charts, which is exactly what a minimum-energy path would
measure and what `PATH-01` records as open.

**Every basin sentence on the claim surface is rewritten to the search form.**
`docs/CLAIM_EVIDENCE_MATRIX.md` rows I6a, J2 and J2a; `docs/G10_RESULT.md` §6;
the spine below. The word "basin" is retained as the *name of the observed
shape* and no longer as a claim about connectivity.

---

## 5. The spine, as the measurements now support it

`R-3` reserves `papers/**`. This is the spine, not an edit to the draft.

1. **Identifiability verdicts are dominated by the measurement protocol** —
   one-against-three rather than an ordering: **×1.17 against ×21–×39** across
   twelve operating points, with junction, dimension and interpolant permuting
   freely between them.

2. **Bias-window *width* sets the rank; spacing moves the spectrum and not the
   rank.** Over 16 bias points at 2% noise the identifiable count runs 1 → 4 as
   the window widens from 0.10 V to 0.75 V about a fixed 0.525 V centre, while
   running linear-to-geometric spacing over a fixed 0.15–0.90 V window moves the
   spectrum by 19.8% and the rank not at all (`rank(observation set)`,
   `outputs/g9/rank_obs.json`). The climb is **not** the leading singular
   direction broadening — `v₁`'s spatial extent moves under 2.5% on a
   0.0625–1.000 scale and recedes from the junction where it moves — it is the
   **spectrum flattening**: `σ₁` nearly fixed and falling, `σ₂…σ₄` rising by
   ×21–×535 in the normalised spectrum, 95.6%–97.9% of the motion in shape.

3. **The degeneracy is real and survives refinement in every chart tested** —
   8.18× and 14.75× in doping, 694 nm against 271 nm in junction depth falling
   1.7% under `N = 301 → 1201`. Survival is predicted by **headroom against the
   floor**, not by geometry.

4. **Its geometry is dimension-dependent, not chart-dependent**: pairs sit at the
   instrument floor at `d=4` and do not at `d=16` in either chart tested. What
   the chart moves at matched `d` is the **depth** — 13× in witness-to-null ratio
   between two charts with matched path lengths. **The `d=16` results are search
   statements against an upper-bound barrier, not separation proofs**: no
   connecting path below the floor was found along the straight line, and the
   minimum-energy path was not computed.

5. **Local analysis is structurally incapable of detecting any of (3) or (4).**

6. **Everything above is bounded above by 0.9 V**, which is the top of the
   convergence sweep and has never been validated as a limit (`PH-15`). The
   largest bias any artefact under `outputs/` was ever evaluated at is 0.9 V,
   across 74 JSON files read. *"Unvalidated above"* is not *"fails above"*.

---

## 6. Limitations — stated, not buried

* **The mechanism is unexplained.** §1 converts "the rank climb is unexplained"
  into a description of *what* moves. It does not say why widening the bias
  window compresses the spectrum. `MECH-01` open.
* **The barrier is an upper bound and the minimum-energy path was not
  computed.** Both `d=16` results are searches that found nothing, not
  separations. `PATH-01` open.
* **Two of the three committed witness sets do not satisfy `WIT-02`** — chart G
  at 3 of 13 and chart L at 0 of 37, the latter being the set the dimension
  reading rests on. In the one set that was refined in full, 6 of 13 pairs
  separated. `WIT-02` §3, `WITNESS-04` open and load-bearing.
* **The upper bias boundary is untested.** Not tested and found sound — never
  tested. `PH-15`.
* **No claim in this repository has been evidenced on any interpreter but
  CPython 3.11 or any operating system but the development one.** `.github/workflows/ci.yml`
  has never executed; the 3.9 floor is a static scan, and `linux` and `darwin`
  are unvalidated and say so in every manifest. `CI-01` `ACCEPTED-PERMANENT`,
  `PROV-07` open, `OT-1` stands.
* **The basin/ridge classifier is binary over three cells.** The numbers beneath
  it are not, and only the chart-L-against-chart-J contrast is matched in both
  path length and dimension.

---

## 7. What closes, and what does not

**Closed.** The technical work. Ten generations. No generation 11.

**Not closed, and not the loop's to close.** `OT-1` (push and run CI, reversion
condition unchanged), `OT-2` (apply `papers/CORRIGENDA_g6.md`; five cycles
unapplied, `papers/draft.md` line 255 unchanged), `OT-3` (preservation: two
copies on one disk is one failure from losing ten generations). `R-3` reserves
the writing.

The open findings are carried forward as they stand in `LOOP_STATE_v8.json`.
None of them is downgraded by this document, and `WIT-02` and the search-form
rewrite each add one that was previously invisible.
