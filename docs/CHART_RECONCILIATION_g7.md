# Chart reconciliation — `G7-R`

> **Amended by generation 8, 2026-08-26.** Nothing measured here is withdrawn and
> no number changes. One *summary* is narrowed: **"the dimension moves the rank
> and the chart does not"** was measured across two charts that differ along a
> single axis — geometric against arithmetic interpolation between equally spaced
> anchors in `log10|C|`, with the same fixed sign convention — and generation 8
> measured a third chart off that axis and perturbed the observation set. Both
> move the *local* spectrum by far more than the chart change does. The sentence
> is true **within that interpolant family** and says nothing outside it. See
> [`docs/G8_RESULT.md`](G8_RESULT.md) §2 and §3.
>
> Two records in this document's artefacts also predate `REP-01` and report a
> representation-shaped error without naming the projection that produced it:
> `containment.json` (4 records) and `spectra.json` (4). Under `R-4` the
> artefacts are not rewritten; the methods are named in
> `tests/test_rep01_g8.py::PRE_ENACTMENT_VIOLATIONS`, which asserts the set
> exactly so it is a guard on those files rather than an amnesty for them.
>
> **Amended by generation 10, 2026-08-26 — `WIT-01`.** Every witness count in
> this document is admissible under `WIT-01`: a pair whose qualifying separation
> the reconstruction cannot carry is not a witness. Applied to the three
> committed witness sets it removes **nothing** — 13 of the 13 in **chart G** at
> **d=4**, 37 of the 37 in **chart L** at **d=16**, 13 of the 13 in **chart J** at
> **d=16**, an admissibility ratio of **1.000** in all three — because every pair
> qualifies on a doping *magnitude*, and magnitudes reach the solver grid exactly.
> The rule is stated and applied rather than assumed, because "the rule does not
> bite here" and "the rule was never applied here" are different sentences and
> only one is checkable. It does catch one reported *quantity*: a chart-J pair
> whose junctions sit 0.425 nm apart on a 3.333 nm grid. See
> [`docs/G10_RESULT.md`](G10_RESULT.md) §3 and `outputs/g10/wit01.json`.

**What this settles.** Generation 6 published a *local* Jacobian rank at `d = 16`
— measured in what this document names **chart L** — and a *global* witness of
non-identifiability at `d = 4`, measured in **chart G**, and recorded as its
highest remaining scientific risk that "the two have never been measured on the
same parameterisation". This document measures both regimes in both charts at
both dimensions, and finds that the obstruction was never the one anybody
expected.

**Measurement conditions, once, for every number below.** Oracle-arbitrated
throughout — the float32 surrogate is never called (`SPEC-g6-5`, `PH-22`); the
NumPy Scharfetter–Gummel solver in float64 on a 301-node uniform grid decides
every question. Log-uniform **prior** on the magnitude of the doping at each
anchor over `1e21 – 1e23 m^-3`. **Noise model** independent Gaussian in relative
terminal current at a **level** of 2% (`noise_rel = 2.0e-2`). **Observation set**
16 **bias** points evenly spaced over 0.15 – 0.90 V, spanning about ten decades of
current. Two floors, reported separately and never subtracted (`PH-13`,
`ADR-0002`): a **noise floor** of `2.0e-2` and a solver **discretisation floor**
of `1.5e-3`; their maximum, `2.0e-2`, is the distinguishability floor.

Artefact: `outputs/chart_reconciliation_g7/`, manifest `manifest.json`.
Reproduce with:

```bash
PYTHONPATH=src python scripts/run_chart_reconciliation_g7.py \
  --phases containment,representation,spectra,profile,native_witness \
  --refine-evals 800 --native-samples 1200 --seed-evals 400 --profile-points 61
```

---

## 1. `SPEC-g7-1` — the two parameterisations are not nested, and neither contains the other

The answer is read from the construction, not from the name of a basis. Two
files decide it, and they never refer to each other.

**Chart G**, the global study —
`scripts/run_global_identifiability.py::make_oracle`, lines 60–62:

```python
mag = 10.0 ** np.interp(x_si, x_anchor, log10_mag)
doping = sign * mag
```

Piecewise-linear **in `log10|C|`**: geometric interpolation of the magnitude,
with the sign a hard flip at the device midpoint applied on the solver grid.
`make_oracle` returns a full 301-node array, so the solver's own resampler never
runs.

**Chart L**, the local study — `scripts/run_identifiability.py` sets
`N_ANCHOR = 16` and hands a **length-16 signed array** to a 301-node solver,
which reaches `solvers/scharfetter_gummel.py::ScharfetterGummel1D.solve`,
lines 767–774:

```python
if doping_si.shape[0] != self.grid.N:
    x_in = np.linspace(0.0, 1.0, doping_si.shape[0])
    x_grid = np.linspace(0.0, 1.0, self.grid.N)
    doping_si = np.interp(x_grid, x_in, doping_si)
```

Piecewise-linear **in `C`**: arithmetic interpolation of the signed value. This
chart appears nowhere in the analysis script. It is a side effect of a
convenience resampler in the solver, which is exactly why six generations did not
notice it was there.

### Containment

Both charts use the same *coordinates* — `theta = log10|C|` at `d` equally spaced
anchors, sign held fixed — and differ only in the reconstruction. That is enough.

Between adjacent anchors carrying magnitudes `u` and `v`, chart G traces
`t -> u^(1-t) v^t` and chart L traces `t -> (1-t)u + tv`. Geometric and
arithmetic interpolation agree **iff `u == v`**, so the two chart images meet
exactly on the piecewise-constant profiles — a measure-zero subset of each.
A second, independent obstruction sits in the sign structure: chart G places a
jump discontinuity between the two grid nodes straddling the midpoint, while
chart L is continuous and must ramp through zero across a whole anchor interval,
smearing the junction over `L/(d-1)` metres. A continuous function cannot equal a
discontinuous one.

**Neither `L ⊂ G` nor `G ⊂ L`.** Raising `d` on either side refines both
families without making either a subset of the other.

Measured, with each direction probed by an object drawn in its *own* source chart
— reusing one profile for both directions measures one thing twice. The probe
object is the *global* witness pair 0 in one direction and a *local*-study device
in the other, at `d = 4` and `d = 16`:

| probe | source | max Δ `log10\|C\|` | max rel | sign disagreements |
|---|---|---|---|---|
| chart G, `d=4` → chart G, `d=16` | witness pair 0, member a | **3.55e-15 dec** | 8.30e-15 | 0 / 301 |
| chart G, `d=4` → chart L, `d=16` | witness pair 0, member a | **1.9545 dec** | 1.11 | 2 / 301 |
| chart L, `d=16` → chart G, `d=16` | `step_asymmetric`, piecewise-constant | **0.6456 dec** | 1.78 | 9 / 301 |
| chart L, `d=16` → chart G, `d=16` | prior draw, seed 0 | **2.3264 dec** | 213.0 | 5 / 301 |

The first row is the useful positive result: **chart G nests exactly in itself**.
The `d=4` anchors land on `d=16` nodes 0, 5, 10, 15 to within `1.06e-22 m`, and
the embedding costs float64 round-off. Within chart G, a `d=4` result *is* a
`d=16` result.

The third row isolates the junction obstruction from the interpolant
obstruction: `step_asymmetric` is piecewise-constant in magnitude, which chart G
reproduces exactly, so the surviving 0.65 decades and 9 sign disagreements are
the junction alone.

`ChartL.reconstruct` is validated against the solver's own stored
`DeviceState.doping`, written *after* resampling: max relative disagreement
**0.0**, exactly. The chart is a description of the code, not a parallel
implementation of it.

---

## 2. `SPEC-g7-2` — the witness embeds into chart L, and the ruling's premise was wrong

The `G7-R` ruling directed a headline reframe on the premise that "chart L cannot
represent either witness member to within the instrument floor — i.e. the
published local analysis was conducted in a chart blind to the degeneracy."

**That premise is false, and this measurement is what falsifies it.** It came from
a first pass that embedded by **collocation only**. Collocation is the naive
embedding, and it is not the best one.

Witness pair 0 in chart G at `d=4`: separation 0.9125 decades (8.18× in doping),
observational distance **1.225476e-02**, reproduced here digit-for-digit from the
generation-6 artefact.

Best chart-L stand-in for each member, over four projections. All four are
reported; a "best approximation" that hides its norm is unfalsifiable:

| member | projection | profile error | observational representation error | vs 2% floor |
|---|---|---|---|---|
| a | collocate | 1.9545 dec | 7.297e-03 | 36% |
| a | least squares in `C` | 1.3513 dec | 8.132e-04 | 4.1% |
| a | least squares in `log10\|C\|` | 1.2326 dec | 8.081e-03 | 40% |
| a | **observation-space refine** | 1.2387 dec | **1.392e-04** | **0.70%** |
| b | collocate | 1.3935 dec | 2.918e-02 | **146%** |
| b | least squares in `C` | 1.3523 dec | 5.177e-03 | 26% |
| b | least squares in `log10\|C\|` | 1.2094 dec | 9.697e-03 | 48% |
| b | **observation-space refine** | 1.3370 dec | **4.338e-04** | **2.2%** |

The refinement is Nelder–Mead on the oracle, budget **B = 800 sweeps per member**,
seeded from the best analytic projection; the oracle certified every evaluation
used (`converged` and `current_is_trustworthy`).

Collocation of member b lands at 146% of the floor — above it. That single number
is what the withdrawn premise rested on. The fitted stand-in reaches 2.2% of the
floor, a factor of 67 better, and member a reaches 0.70%.

**Chart L holds both witness members comfortably inside the instrument floor.**

### The pair survives the embedding, and is not collapsed

| quantity | chart G, `d=4` | best chart-L stand-ins, `d=16` |
|---|---|---|
| observational distance | 1.225476e-02 (61.3% of floor) | **1.207185e-02 (60.4% of floor)** |
| separation | 0.9125 decades (8.18×) | **0.9115 decades (8.16×)** |

Separation ratio L/G = **0.9989**. Chart L does not collapse the pair toward one
profile; it preserves it to one part in a thousand.

The pair of stand-ins is itself a **witness in chart L at `d = 16`** by the
repository's own definition — separation 0.9115 decades ≥ 0.3, observational
distance 1.207e-02 < the 2.0e-02 floor, both members oracle-certified.

There is a second reading of the same table worth stating plainly. The refined
stand-ins sit **1.24 and 1.34 decades** away from their chart-G targets in profile
space while matching the target I–V to `1.4e-04` and `4.3e-04`. Those are not
approximations that happen to be close; they are *different devices that the
instrument cannot separate*. The search for a good stand-in produced additional
degenerate profiles as a by-product.

---

## 3. `SPEC-g7-3` — the matched-`d` statement

Four cells — the *local* Jacobian spectrum in each chart at `d = 4` and
`d = 16` — all at the same operating point (the *global* witness pair 0, member
a), the same 2% noise, the same 16 **bias** observation set, the same log-uniform
**prior**, float64 throughout (`PH-22`). Chart L cells sit at member a's best chart-L
stand-in, and each cell carries its profile distance from the operating point,
because chart L cannot hold that device exactly.

**The full spectrum is the measured object. Rank is a cutoff applied to it.**

| cell | chart | d | σ₁ | σ₂ | σ₃ | σ₄ | σ₅ | identifiable | resolvable | profile dist |
|---|---|---|---|---|---|---|---|---|---|---|
| G, d=4 | G | 4 | 1.9234e0 | 3.2203e-1 | 6.0806e-2 | 8.2277e-3 | — | 3 | 4 | 0 dec |
| G, d=16 | G | 16 | 1.0600e0 | 2.1849e-1 | 4.3816e-2 | 1.2992e-2 | 7.5497e-3 | 4 | 5 | 0 dec |
| L, d=16 | L | 16 | 1.0694e0 | 2.2432e-1 | 4.3784e-2 | 1.2706e-2 | 7.9282e-3 | 4 | 5 | 1.2387 dec |
| L, d=4 | L | 4 | 1.9901e0 | 3.9449e-1 | 7.4245e-2 | 4.2521e-3 | — | 3 | 4 | 1.7856 dec |

Read the table down the columns, not across the rows:

* **`d` moves the rank; the chart does not.** Rank 3 at `d=4` in *both* charts,
  rank 4 at `d=16` in *both* charts.
* **At matched `d` the two charts have almost the same spectrum.** At `d=16`,
  σ₁…σ₅ agree between charts to within 3%, *despite* the two operating points
  being 1.24 decades apart in profile space. The local geometry of this problem
  is a property of the physics, not of the interpolant.

So the discrepancy generation 6 could not explain was a **dimension** effect, and
the chart was a confound that had to be removed before that could be seen.

### The cutoff, and where it is not justified

`PH-11` forbids a tuned cutoff. Two cutoffs are reported: the operational noise
threshold `log10(1 + 0.02) = 8.60e-03` the repository already uses, and the
largest multiplicative gap between consecutive resolvable singular values.

| cell | largest gap | after index | noise cutoff inside that gap? |
|---|---|---|---|
| G, d=4 | ×7.39 | 2 | **yes** |
| G, d=16 | ×4.99 | 1 | **no** |
| L, d=16 | ×5.12 | 1 | **no** |
| L, d=4 | ×17.46 | 2 | **yes** |

**At `d = 4` the rank is a population boundary. At `d = 16` it is not.** The
`d=16` spectra decay smoothly and the cutoff falls in the middle of a run of
comparable values, so "4" there is a threshold count, not a separation of
populations. That is a real weakness of every `of 16` number this repository has
ever published, including the ones it published before this generation, and it is
not repaired by the reconciliation — it is exposed by it.

Rank fractions are reported **within a chart only**. Because neither chart
contains the other, `4/16` in chart L and `3/4` in chart G are fractions over
different manifolds and are not comparable, and this document does not compare
them.

---

## 4. `SPEC-g7-3e` — native witness search in chart L at `d = 16`

The 2×2 table above is local geometry. It does not say whether **chart L** is
globally non-identifiable *on its own terms*, so that was searched for natively
rather than inferred from the embedding.

**Prior sampling**, for *global* non-identifiability. Budget **B = 1200** draws
from the same log-uniform **prior**, in chart-L coordinates at **d = 16**, giving
**719,400** pairs. All 1200 draws
were oracle-certified — 0 rejected for non-convergence, 0 for an untrustworthy
current (`PH-19`: rejections are counted, not dropped).

| | |
|---|---|
| witness pairs found | **37** (0 of 37 refined under `WIT-02`) |
| closest pair with separation ≥ 0.3 decades | **8.8137e-03** (44.1% of the 2.0e-02 floor) |
| its separation | **1.1688 decades — 14.75× in doping** |

**Seeded refinement**, also for *global* witnesses. Budget **B = 400** oracle
sweeps per seed, 3 seeds, each the best chart-L projection of one of the
generation-6 **chart G** witnesses at **d = 4**, refined against the oracle under
a separation penalty. **3 of 3** produced witnesses:

| seed | observational distance | separation | oracle certified |
|---|---|---|---|
| 0 | 2.837e-03 (14.2% of floor) | 0.6005 dec (3.99×) | yes |
| 1 | 2.199e-03 (11.0% of floor) | 0.3695 dec (2.34×) | yes |
| 2 | 2.215e-03 (11.1% of floor) | 0.4531 dec (2.84×) | yes |

**Chart L is globally non-identifiable at `d = 16`.** The published local rank in
that chart is therefore misleading in exactly the way a **chart G** rank would
have been: it reports how many directions are flat *at a point*, in a chart that
also contains distant, observationally indistinguishable devices.

The closest native chart-L witness is a **stronger** witness than the
generation-6 headline — 14.75× apart at 44% of the floor, against 8.18× at 61%.

### What must not be read off these two searches

The witness *frequencies* are not comparable. Chart G found 13 in 1,999,000 pairs
and chart L found 37 in 719,400, and those two rates are not comparable. Three
things differ at once — the chart, the
dimension (4 against 16), and the sampling density per dimension — so the ratio of
those rates measures the confound, not the physics. Existence is a **search
outcome** and transfers; frequency is a **density estimate** and does not. Both
budgets are stated above so that neither number can be quoted without its
denominator.

---

## 5. `SPEC-g7-4` — profile likelihood along the witness path

This is a *global* measurement — it walks between two distant devices — read
against the *local* geometry of §3.

**Parameterisation** chart G, `d = 4`, `theta = log10|C|` at 4 equally spaced
anchors. **Path** the straight line in `theta` between witness pair 0's two
members, extended to `t ∈ [-0.25, 1.25]`, 61 points.
**Endpoint a** `[22.0523, 21.9288, 21.4451, 22.5129]`.
**Endpoint b** `[22.6129, 21.0162, 22.0673, 22.0224]`.
**Reference observation** the oracle I–V of endpoint a, noise-free, at the 16-bias
observation set; **noise model** independent Gaussian in relative current at a
level of 2%.

| `t` | log-likelihood | observational distance from a |
|---|---|---|
| 0.000 | **0.000** | 0 |
| 0.475 | **−242.44** | 1.2574e-01 |
| 1.000 | **−0.591** | 1.2255e-02 |

**The profile is not flat. It is bimodal.** Exactly two local maxima on `[0, 1]`,
at the two endpoints, separated by a barrier 242 log-units deep. Only **5 of 61**
points on the path sit inside the 2% distinguishability floor, and **58 of 61**
fall below a log-likelihood of −2.

### Control

Without a control a flat profile is not evidence — it could be a flat solver. The
same excursion length in `theta` along the **most observable** right singular
direction of the chart-G `d=4` Jacobian at endpoint a (σ₁ = 1.9234) reaches a
log-likelihood of **−10584.5** at `t = 1`, **43.7×** deeper than the witness
path's barrier, and has **no** second maximum. The flatness is directional and
real.

### What bimodality changes

This corrects the geometry assumed in the generation-6 ruling §3.3, which
attributed the 2%-noise ESS collapse to a posterior "diffuse along the degenerate
manifold". There is no manifold here to be diffuse along. There are two isolated
modes with a 242-log-unit barrier between them, and prior importance sampling
collapses because it must land inside a narrow mode, not because it is spread
along a ridge. The remedy follows the diagnosis: a mode-hopping or tempered
sampler, not more samples.

It also sharpens the operational consequence. Gradient-based inversion cannot
travel between these two devices — the barrier is 43.7× shallower than the
steepest direction but still 242 log-units — so an optimiser returns whichever
mode it started nearest, with no indication that the other exists.

---

## 6. What may be said, and what may not

### Supported

* **Chart G, `d = 4`.** 13 witness pairs among 1,999,000 examined; the closest
  differs by 8.18× in doping and 1.23% in I–V, at 61.3% of the 2.0e-02
  distinguishability floor, and survives 4× grid refinement and a tighter solver
  tolerance. **3 of 13 refined** under `WIT-02`; the other 10 have never been.
* **Chart L, `d = 16`.** 37 witness pairs among 719,400 examined at a stated
  budget of 1200 prior draws; the closest differs by 14.75× in doping and 0.88%
  in I–V, at 44.1% of the same floor. Chart L is globally non-identifiable on its
  own terms. **0 of 37 refined** under `WIT-02` — no refinement of this set has
  ever been run, and generation 9 separated 6 of 13 in the one set that was.
* **The chart-G witness transfers into chart L.** Best chart-L stand-ins for
  witness pair 0 reach 0.70% and 2.2% of the floor in observation space; their
  pair distance is 1.207e-02 against 1.225e-02 in chart G, with separation
  preserved at a ratio of 0.9989.
* **Matched-`d` local geometry.** At one operating point, 2% noise, 16 biases:
  identifiable rank 3 at `d=4` and 4 at `d=16`, **in each chart separately**, with
  σ₁…σ₅ agreeing between charts to within 3% at `d=16`. The dimension moves the
  rank; the chart does not — **within the family these two charts span**, which is
  piecewise interpolation over equally spaced anchors in `log10|C|` with a fixed
  sign convention. Generation 8 measured a third chart outside that family and
  found the spectrum moves materially, so this sentence must not be generalised
  past its measured family ([`docs/G8_RESULT.md`](G8_RESULT.md) §2).
* **The degeneracy is bimodal, not a flat manifold** — two isolated likelihood
  maxima separated by a 242-log-unit barrier, against a control direction 43.7×
  steeper with no second mode.
* **Neither chart contains the other**, from the constructions, at every finite `d`.

### Not supported, and not to be written

* **Any rank fraction compared across charts** — the *local* "3–4 of 16" of
  chart L at `d=16` against the *global* "3 of 4" of chart G at `d=4` are **not
  comparable**, being different denominators over different manifolds, and the
  matched-`d` table of §3 exists precisely so that comparison never has to be
  made that way.
* **Any frequency or probability of degeneracy**, in either chart. Two searches at
  two budgets are existence proofs. Neither is a density estimate, and the
  measure-zero point stands: an embedded lower-`d` family has measure zero under a
  higher-`d` prior, so *existence at `d=16`* — which is now established natively,
  not only by embedding — must still not be read as a *frequency* at `d=16`.
* **Any contraction number at the instrument's own 2% noise.** Unchanged from
  generation 6: the estimator collapses (ESS 1.0) and the result is withheld. §5
  now explains *why* — the posterior is multimodal, not diffuse — which makes more
  samples the wrong remedy.
* **"4 of 16 is a population boundary"** — withdrawn, and it was measured over
  16 biases spanning 0.15–0.90 V: in **chart L** at `d = 16` the *local* rank is
  a threshold count, not a population count, because the spectrum has no clean
  gap at the cutoff (§3), and it is reported as `rank(cutoff)` for that reason.
  The same caveat applies to **chart G** at `d = 16`.

---

## 7. Corrections this generation makes to its own instructions

Recorded because a ruling that is silently reinterpreted is worse than one that
is contradicted in writing.

1. **The headline reframe is withdrawn.** "Chart L cannot represent either
   witness member to within the instrument floor" is false: the best chart-L
   stand-ins reach 0.70% and 2.2% of the floor. The claim came from a
   collocation-only embedding in the pre-`G7-R` scouting report, and the fitted
   embedding overturns it. `tests/test_charts_g7.py::test_projection_is_at_least_as_good_as_collocation`
   pins the ordering so the mistake cannot recur silently.

2. **`SPEC-g7-2`'s falsifier does not fire.** It was written as "the embedded
   pair's distance exceeds the distinguishability floor". Under collocation it
   does (2.446e-02); under the best embedding it does not (1.207e-02). The
   falsifier is only meaningful against a *best* embedding, and the ruling's own
   correction — that a failed embedding means the witnesses are outside chart L,
   not that the degeneracy is an artefact of `d=4` — is the right reading and is
   now moot for this pair.

3. **The `§3.3` posterior geometry is corrected** from a flat degenerate manifold
   to isolated modes, on the profile-likelihood evidence in §5.
