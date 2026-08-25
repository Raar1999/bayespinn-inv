# S-1 — Global identifiability of the doping profile from terminal I–V

**Generation** 6 · **Date** 2026-08-25 · **Spec** `SPEC_g6.md` · **ADR** `ADR-0007`
**Artefacts** `outputs/global_identifiability_g6/`, `outputs/witness_falsifier_g6/`
**Arbiter** the SG oracle at every step. The surrogate was never called.

---

## 0. Headline

**Global non-identifiability is demonstrated by concrete witness, not inferred
from a rank.**

Searching 1,999,000 pairs drawn from a 2-decade prior over a 4-anchor doping
parameterisation, **13 pairs** were found whose profiles differ by at least 0.3
decades yet whose oracle I–V curves differ by **less than the 2% distinguishability
floor**. The most extreme differs by **8.18× in doping at one anchor** and produces
an I–V difference of **1.23%** — 61% of the floor.

All three pairs put through the falsifier **survived** 4× grid refinement and a
tightened solver tolerance, with all 16 bias points certified at every level. They
are consistent with physical degeneracy, not solver artefact.

This upgrades the project's central scientific claim. Before: *identifiability is
local, and global non-identifiability is unmeasured.* Now: *global
non-identifiability is measured, with exhibited witnesses that survive refinement.*

---

## 1. What was measured, and under what conditions

Per §4.2 of the ruling, no number below is meaningful without all five:

| condition | value |
|---|---|
| **Parameterisation** | `d = 4` anchors, evenly spaced; magnitude interpolated linearly in log10; sign fixed by the PN convention (PH-03/PH-04) |
| **Prior support** | log-uniform on \|doping\| over **1e21 – 1e23 m⁻³** per anchor. Every result is relative to this prior. Hash `ba11a6d5357388cb…`, fixed before sampling (`AH-14`) |
| **Noise model** | 2% relative on terminal current |
| **Observation set** | `V ∈ [0.15, 0.90]`, **16 points** |
| **Distinguishability floor** | **2.0e-02** = max(noise 2.0e-02, solver discretisation 1.5e-03) |

Both floors are reported, never subtracted (PH-13). The observation set is itself a
measured choice fixed before any search (`AH-16`): below `V = 0.15` the oracle's
grid-refinement differences stop converging, because the current is small enough
that the solver's own noise floor competes with discretisation.

**Oracle compliance (`SPEC-g6-5`):** 2,000 profiles drawn, **2,000 kept** — 0
rejected for non-convergence, 0 for untrustworthiness. Every observation carries
the solver's own `converged` and `current_is_trustworthy()` verdict.

---

## 2. `SPEC-g6-1` — Witness search

| | |
|---|---:|
| profiles sampled for the **global** search, **chart G**, **d=4** (all oracle-certified) | 2,000 |
| pairs examined | 1,999,000 |
| **witness pairs found** | **13** |
| rate | 6.5e-06 |
| observational distance, 5 recorded | 1.2255e-02 … 1.5320e-02 |
| parameter separation | 0.303 … 0.913 decades = **2.01× … 8.18×** |
| wall clock | 16.9 min |

### The closest witness

| | profile A | profile B | Δ |
|---|---|---|---|
| log10 \|C\| at 4 anchors | 22.0523, 21.9288, 21.4451, 22.5129 | 22.6129, 21.0162, 22.0673, 22.0224 | +0.56, **−0.91**, +0.62, −0.49 |
| I at 0.15 V (A/m²) | 8.450117e-03 | 8.554956e-03 | |
| I at 0.90 V (A/m²) | 9.407760e+07 | 9.370814e+07 | |

Two devices whose doping differs by a factor of **8.18** at one anchor, and by
2–4× at three others, produce terminal I–V curves agreeing to **1.23%** across 16
bias points spanning ten decades of current. At a 2% instrument they are the same
device.

### Context: this is much stronger than the existing local claim

`C14` reports *equivalence twins* — profiles differing by up to **1.26×**
locally, in **chart L** at **d=16**, changing I–V by 0.02–1.3%. Those were
**constructed** along locally flat directions. The witnesses here were **found by
global search** in **chart G** at **d=4** and are up to **8.18×** apart — six
times the doping difference, still indistinguishable.

---

## 3. Falsifier — the witnesses survive

`§4.6` weights this candidate heavily, and GRAD-02 is why: the previous
generation's falsifier overturned that generation's own finding.

A witness can be physical (the device cannot distinguish the pair) or an artefact
(the *solver* cannot, at the grid and tolerance used). The falsifier re-solves both
members on finer grids and with a tighter tolerance and asks whether the distance
grows through the floor.

| pair | separation | N=301 | N=601 | N=1201 | tight tol | verdict |
|---|---:|---:|---:|---:|---|---|
| 0 | 0.913 dec | 1.2255e-02 | 1.2369e-02 | **8.6089e-03** | unchanged | **survives** |
| 1 | 0.303 dec | 1.3788e-02 | 1.3557e-02 | 1.3442e-02 | unchanged | **survives** |
| 2 | 0.328 dec | 1.4224e-02 | 1.4426e-02 | 1.4521e-02 | unchanged | **survives** |

All 16 biases certified at every grid and tolerance. Pair 0's distance *falls* under
refinement — it becomes **more** degenerate, not less. Tightening `tol_carrier` to
1e-12 with `max_outer=200` changed nothing to five digits, so the pairs are not an
artefact of incomplete convergence either.

**The falsifier failed to break the result.** Recorded as a failure to falsify, not
as proof: 3 of the 13 pairs were tested, at three grids and two tolerances.

---

## 4. `SPEC-g6-2` — Contraction spectrum, and where it stops working

d = 4, n = 2,000, prior → posterior variance ratio per direction.

| tolerance (× noise) | ESS | supported | contracting (**global**, **chart G**, **d=4**) | variance ratios |
|---:|---:|:---:|---:|---|
| 1 | 1.0 | **no** | (4) | 0.000 0.000 0.000 0.000 |
| 2 | 1.7 | **no** | (4) | 0.041 0.133 0.180 0.022 |
| 5 | 13.9 | **no** | (3) | 0.269 0.268 0.766 0.367 |
| **10** | **71.0** | **yes** | **3 of 4** | 0.477 0.411 0.791 0.421 |
| 25 | 400.0 | yes | 0 of 4 | 0.633 0.645 0.841 0.623 |
| 50 | 1106.7 | yes | 0 of 4 | 0.804 0.785 0.893 0.827 |
| 100 | 1846.1 | yes | 0 of 4 | 0.936 0.918 0.963 0.947 |
| 250 | 1995.1 | yes | 0 of 4 | 0.989 0.985 0.994 0.991 |

**At the instrument's actual 2% noise, contraction is not measured.** ESS collapses
to 1.0 — the entire posterior weight lands on one draw of 2,000, the weighted
variance goes to zero, and *every* direction reports as contracting. That row is an
artefact of the estimator and is marked unsupported rather than reported. It is the
S-1 equivalent of quoting an ECE below its M=5 floor (`API-04`).

The measurable statement is narrow and is given as such: **globally, in chart G
at d=4, at 10× the instrument noise (20% relative), with ESS 71 of 2,000 usable
samples, 3 of 4 directions contract below a variance ratio of 0.5.** Above 25× the data constrains nothing;
below 10× the estimator stops estimating.

Reaching 2% would need sequential Monte Carlo or MCMC, not a larger `n` — the
required sample count grows exponentially in `d`. That is a limitation of the
method and is reported as one.

---

## 5. `SPEC-g6-3` — Dimension sweep

n = 1,000 per `d`, all figures at the tightest supported tolerance (10× noise):

| d | samples per dimension | ESS | contracting (**global**, **chart G**) |
|---:|---:|---:|---|
| 2 | 500 | 31.6 | **2 of 2** |
| 4 | 250 | 38.8 | **3 of 4** |
| 8 | 125 | 50.5 | **1 of 8** |

The count of contracting directions **does not grow with the parameterisation**:
2, 3, 1 for d = 2, 4, 8. This is the global analogue of `D13`, which found the
*local* rank invariant to parameterisation (P = 8 → 32 leaves it at 3–4).

**The d=8 figure is confounded and must not be read as "less information at higher
d".** `n` was held at 1,000 while `d` grew, so samples per dimension fall 500 → 250
→ 125. A sparser sample in a larger space finds less contraction whether or not the
physics changed. Separating the two requires `n` scaled with `d`, which the
pre-registered budget did not cover. Stated rather than glossed (`SPEC-g6-3` RISK).

---

## 6. `SPEC-g6-4` — The local/global relationship

| | local (**chart L**, **d=16**) | global (**chart G**, **d=4**) |
|---|---|---|
| method | Jacobian rank at one operating point | prior→posterior contraction + witness search |
| result | **3–4 of 16**, **chart L**, **d=16**, at 2% noise — **not comparable** with the next column, see `CHART_RECONCILIATION_g7.md` | **3 of 4**, **chart G**, **d=4**, at 10× noise |
| what it says | which directions are flat *here* | which directions the data constrains *at all*, and which distant profiles collide |

**They agree in direction and cannot be compared in magnitude.** Both say only a
handful of directions are constrained. Generation 7 found the deeper reason: the
local number was measured in **chart L** and the global one in **chart G**, and
neither chart contains the other, so the two fractions are **not comparable**
across charts — they are over different manifolds, not merely different
denominators (`CHART_RECONCILIATION_g7.md`). The denominators differ (16 vs 4) and
the noise levels differ (2% vs 20%) as well.

Measured at matched chart and matched `d`, the **dimension** moves the rank and
the **chart** does not: identifiable rank 3 at `d=4` and 4 at `d=16` in **chart G**
*and* in **chart L**, with the spectra agreeing to within 3% at `d=16`.

**Where the local analysis is insufficient, precisely:** a local rank cannot
exhibit a witness. It says a direction is flat *at a point*; it cannot say that a
profile 8× away produces the same measurement. Only the global search can, and it
did. The local framing was not wrong — it was incomplete in exactly the way
generation 0 said it might be.

---

## 7. What this does and does not establish

**Establishes.** Globally, in **chart G** at **d=4**, over a 1e21–1e23 m⁻³
log-uniform prior, with 16 bias points over 0.15–0.90 V and a 2% distinguishability
floor — the maximum of a 2.0e-02 noise floor and a 1.5e-03 solver discretisation
floor — terminal I–V does **not** determine the doping profile: pairs differing by
up to 8.18× produce indistinguishable measurements, and they survive 4× grid
refinement and a tighter solver tolerance. Generation 7 showed the same pair
survives embedding into **chart L** at **d=16**, and found 37 further witnesses
natively in **chart L** (`CHART_RECONCILIATION_g7.md`).

**Does not establish.**

- Anything at d = 16, the parameterisation the published local result uses. This
  study is d ∈ {2, 4, 8}.
- Anything outside the stated prior. A narrower physical prior could exclude these
  witnesses entirely — the result is *relative to the prior*, as §4.2 requires.
- A contraction spectrum at the instrument's own 2% noise. Not measured; the
  estimator collapses there.
- That 13 is the true number of witnesses. It is the number found in 1,999,000
  pairs at this budget. A larger search would find more.
- That the d=8 decline is physical. It is confounded with sampling density.

**`AH-13` applies in reverse here.** The witness search *succeeded*, so this is a
positive claim rather than an absence-of-evidence one. Had it found nothing, the
sentence would have been "no witness found at this budget" — not "identifiable".
