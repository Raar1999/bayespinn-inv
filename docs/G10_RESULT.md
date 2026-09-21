# Generation 10 — the mechanism is not localisation, and the ridge is a dimension

**What this generation settles, in one paragraph.** Generation 9 left a
mechanism-shaped hole: bias-window *width* sets the identifiable rank and spacing
does not, and nothing measured said why. `SPEC-g10-1` tested the cheapest
mechanism consistent with that split — that the window selects which transport
regimes the terminal current is sensitive to, so the observable directions should
localise in space near the junction at narrow windows and delocalise at wide ones
— under a measure hashed before the first SVD. **It is falsified.** The leading
right singular vector's spatial extent moves by under 2.5% while the rank climbs
from 1 to 4, and where it moves at all it moves the *wrong way*. `SPEC-g10-2`
removed a confound generation 9 introduced by comparing **chart G** at `d=4`
against **chart J** at `d=16`: barriers on the 37 **chart L** witness pairs at
`d=16` make the comparison matched in `d`, and **chart L is a basin, not a
ridge**. Both `d=16` charts are basins; the only ridge is `d=4`. The ridge/basin
split is a **dimension** effect, and the ruling that ordered this measurement
stated its own falsifier the wrong way round. `WIT-01` is enacted and
retro-applied, and removes nothing from any count — which is the result, not the
absence of one.

---

## 0. Measurement conditions, once, for every number below

Oracle-arbitrated throughout — the float32 surrogate is never called (`SPEC-g6-5`,
`ADR-0007`, `PH-22`). Float64 Scharfetter–Gummel on a 301-node uniform grid.
Log-uniform **prior** `1e21`–`1e23` m⁻³ per magnitude anchor. **Observation set**
16 **biases** over 0.15–0.90 V except where `SPEC-g10-1` is varying it, which is
its subject. **Noise model** independent Gaussian in relative current at a
**level** of 2%; **noise floor** `2.0e-2`, solver **discretisation floor**
`1.5e-3`, **distinguishability floor** `2.0e-2` = max of the two.

Every measurement ran against machinery commit `e05d463` with `dirty=false`;
`outputs/g10/manifest.json` records it. The barrier metric is not a
re-implementation of generation 9's — `scripts/run_g10.py` **imports**
`BarrierCriterion` and `_barrier_between` from `scripts/run_g9.py`, and the
pre-registration phase refuses to run unless the criterion hash generation 9
wrote to disk equals the one it recomputes. Three witness sets compared through
a single function are one ruler; three sets compared through three copies of a
function are not.

**`WIT-01` applies to every witness count in this document.** All are admissible:
13 of the 13 in **chart G** at `d=4`, 37 of the 37 in **chart L** at `d=16`, 13 of
the 13 in **chart J** at `d=16` — an admissibility ratio of **1.000** in all
three. See §3.

---

## 1. `SPEC-g10-1` — the localisation mechanism is falsified

### 1.1 The hypothesis, and the measure that was hashed before it was tested

> The bias window sets which transport regimes the terminal current is sensitive
> to, so it sets the rank of the sensitivity operator; the parameterisation only
> sets which subspace of profile space that operator acts on. If so, the right
> singular vectors should **localise in space** — narrow low-bias windows giving
> vectors concentrated near the junction, wider windows giving delocalised ones —
> and the rank 1 → 4 climb should track the number of distinct regimes the window
> spans.

A right singular vector `v = directions[:, k]` has one entry per chart
coordinate, and in **chart G** at `d=16` each coordinate is an anchor at a known
position, so `w_j = v_j²` is a distribution over the device. The **primary
statistic** is the participation ratio of that distribution divided by `d` —
`spread_fraction`, running from `1/16 = 0.0625` when all the weight sits on one
anchor to `1.000` when it is uniform. It uses `v_j²`, so the sign gauge a
singular vector is only defined up to cannot enter, and it does not depend on the
number of Jacobian rows, which matters because the oracle certifies 13 to 16
biases depending on the window and a statistic that moved with the row count
would be measuring the SNR gate.

The **decision**, registered with hash `678c272f…` before the first SVD:

> SUPPORTED iff at *every* device: `spearman(width, spread_fraction of v₁) ≥ 0.7`
> **and** the range covered over width is at least **2×** the range covered over
> spacing. FALSIFIED otherwise, and reported either way.

Both halves are required. A trend with no contrast against spacing is consistent
with any monotone artefact of window size; a contrast with no trend is not the
claim. The junction-distance is the statistic the hypothesis actually *names*,
and it is exactly why it is **not** the primary one: a statistic a hypothesis
names is the one most likely to be read generously.

The cells are the same devices, widths and spacings `SPEC-g9-2` used for
`rank(observation set)`, cell for cell, so the localisation curve and the rank
curve are one experiment rather than two.

### 1.2 The result

Widths are centred at 0.525 V; the rank column is
`rank_at_operational_cutoff` at 2% noise, reproduced from `SPEC-g9-2`.

| width (V) | 0.10 | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 | 0.60 | 0.70 | 0.75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **rank**, `g8_operating_point` | 1 | 1 | 2 | 3 | 4 | 4 | 4 | 4 | 4 |
| `spread_fraction(v₁)` | 0.5264 | 0.5258 | 0.5247 | 0.5213 | 0.5186 | 0.5184 | 0.5202 | 0.5243 | 0.5255 |
| **rank**, `device_p50` | 2 | 2 | 2 | 3 | 4 | 4 | 4 | 4 | 4 |
| `spread_fraction(v₁)` | 0.4825 | 0.4821 | 0.4814 | 0.4791 | 0.4767 | 0.4747 | 0.4729 | 0.4722 | 0.4708 |

| | `g8_operating_point` | `device_p50` |
|---|---:|---:|
| `spearman(width, spread)` | **−0.433** | **−1.000** |
| `spearman(alpha, spread)` | −0.933 | −0.733 |
| range over width | 0.0080 | 0.0117 |
| range over spacing | 0.0046 | 0.0025 |
| range ratio (width : spacing) | 1.73 | 4.73 |
| `spearman(width, junction distance)` | +0.083 | **+1.000** |
| `spearman(rank, spread)` | −0.725 | −0.894 |
| **width criterion met** | no | no |
| **contrast criterion met** | no | yes |
| **device supports the hypothesis** | **no** | **no** |

**Verdict: FALSIFIED**, at both devices, under the registered criterion. Three
separate things go wrong for the hypothesis, and they are worth separating.

**The leading direction barely moves at all.** Its spread runs over 0.0080 and
0.0117 on a scale from 0.0625 to 1.000 — under 2.5% of its own value — while the
rank climbs from 1 to 4 over exactly the same sweep. Whatever the rank climb is,
it is not the leading observable direction broadening.

**Where it moves, it moves the wrong way.** At `device_p50` the correlation with
width is `−1.000`: a perfect monotone *decrease*. The leading direction becomes
**more** localised as the window widens, which is the opposite of the prediction.
Its centroid moves **away** from the junction as the window widens
(`spearman = +1.000`), which is also the opposite of the prediction.

**And width is not even the stronger axis.** At the `g8_operating_point` the
monotone trend against *spacing* (`−0.933`) is stronger than the one against
*width* (`−0.433`) — the second clause of the clause's own falsifier, "or tracks
spacing equally", firing on its own terms. That point fails both halves of the
registered criterion; `device_p50` passes the contrast half and fails the
direction half.

### 1.3 What is reported and is not a claim

`v₂ … v₄` are recorded at every cell, with each vector stamped `reliable` only
where its index is below that cell's rank — a right singular vector below the
rank spans a near-null subspace whose orientation inside that subspace the data
does not determine, and reporting its localisation as a measurement would be
inventing a direction. Descriptively, `v₂`'s spread at the `g8_operating_point`
does rise across the reliable part of the sweep (0.306 at 0.20 V to 0.531 at
0.75 V) while `v₃` and `v₄` wander without a monotone trend, and at `device_p50`
none of the three has one.

That is where this stops. `SPEC-g10-1` says explicitly: *do not chase a second
mechanism if this one fails*. The gap generation 9 recorded stays open, it is
reported as a gap, and it is a paragraph rather than a generation.

### 1.4 What the negative is worth

It is not nothing. Before this measurement, "the window selects transport
regimes, and the regimes are spatial" was the obvious mechanism and was
unmeasured. It is now measured and wrong at two devices spanning the prior, under
a criterion fixed in advance, with the leading direction's near-invariance
quantified rather than asserted. The next candidate mechanism has to explain why
the *leading* direction is essentially fixed while the count of directions above
the noise quadruples — which is a sharper question than the one generation 9
left, and is the one thing this generation adds to it.

---

## 2. `SPEC-g10-2` — ridge or basin, at matched `d`

### 2.1 The confound, and the cell that removes it

Generation 9 measured likelihood barriers between the two members of each witness
pair, in units of the **floor barrier** `0.5 × B = 8.0` log-units — the cost of a
curve sitting one noise unit away at every certified bias, which is the only
non-arbitrary scale available. It found **chart G** at `d=4` at the floor (a
*ridge*: the likelihood is flat between the members at the resolution the
instrument has) and **chart J** at `d=16` at 59× the floor (*two basins* that
happen to produce indistinguishable current), and read that as the geometry being
chart-dependent.

Those two cells differ in **both** chart and dimension, so nothing in them
separates the two. **Chart L** at `d=16` is the cell that does: matched in `d` to
chart J, matched in interpolant family to chart G. Its 37 witness pairs have sat
in `outputs/g8/reproduce.json` since generation 8.

The classifier was registered with hash `88748b9f…` before that third set was
measured: **RIDGE** if at least a third of the witness pairs are at or below the
floor barrier, **BASIN** if none is, **MIXED** in between. On generation 9's
numbers chart G gives 6/13 → RIDGE and chart J gives 0/13 → BASIN, so the
thresholds reproduce the existing reading rather than replacing it.

### 2.2 The result

| | **chart G**, `d=4` | **chart L**, `d=16` | **chart J**, `d=16` |
|---|---:|---:|---:|
| witness pairs | 13 | 37 | 13 |
| floor barrier (log-units) | 8.0 | 8.0 | 8.0 |
| witness barrier, median | **8.315** | **1696.110** | **468.350** |
| … in floor units | **1.039** | **212.014** | **58.544** |
| witness barrier, min | 0.680 | 22.598 | 16.050 |
| witness barrier, max | 2239.21 | 15629.09 | 9397.16 |
| **at or below the floor** | **6 / 13** | **0 / 37** | **0 / 13** |
| **classification** | **RIDGE** | **BASIN** | **BASIN** |
| null control, median | 9379.17 | 2564.55 | 9478.69 |
| null control, min | 338.93 | 267.26 | 1331.58 |
| witness median ÷ null median | **8.9e-04** | **0.661** | **0.049** |
| witness path length, L2 median | 0.610 | 2.979 | 2.872 |
| max-coordinate separation, median | 0.392 | 1.475 | 1.441 |
| witness barrier ÷ path length, median | **15.35** | **568.89** | **198.85** |
| null-control path length, L2 median | 1.512 | 3.230 | 3.246 |
| null barrier ÷ path length, median | 8283 | 1083 | 2507 |

Every count above carries its null control in the same record, as `SPEC-g9-4`
requires. `outputs/g10/ridge_basin.json`.

`REP-01`, for the two rows the run does not write. Every row above is a field of
`ridge_basin.json` except two, and both are computed **at documentation time**
from that same committed record with no oracle call. *Witness median ÷ null
median* is the quotient of the two medians immediately above it. *Null barrier ÷
path length* is the median over null-control pairs of `barrier_depth` divided by
the L2 distance between the two members' coordinates, taken pair by pair rather
than as a ratio of medians — the same construction the witness row uses, which is
why the two are comparable. Neither was added to the artefact, because doing so
would have meant re-running 126 certified paths to obtain numbers the ones on
disk already imply.

**Reproduction control.** Generation 9's two sets were re-measured here through
the same imported function against the same committed draws. Both medians
reproduce to `relative_change = 0.0` — bit for bit — and both below-floor counts
are unchanged. If they had moved, the third set would not be comparable to them
and the clause would be void.

### 2.3 The split is a dimension effect, and the ruling stated its falsifier backwards

Chart L at `d=16` is a **BASIN**: not one of its 37 pairs is within the floor
barrier, and its median is 212 floor units — deeper, in floor units, than chart J's
58.5. Under the registered table:

> both `d=16` cells are basins and the only ridge is the `d=4` one → the
> ridge/basin split is a property of the **dimension**.

The operator ruling that ordered this measurement states the falsifier as *"chart
L `d=16` sits at the floor like chart G `d=4`, which would make the ridge/basin
split a dimension effect rather than a chart effect."* **That is inverted.** If
chart L sat at the floor while chart J at the *same* `d` did not, two charts at
one dimension would disagree, and `d=4` and `d=16` would land on the same side of
the split — which is precisely what a dimension effect cannot do. The dimension
reading requires chart L to behave like chart **J**, which is what it does. The
correction is in `outputs/g10/preregister.json`, hashed before the third set was
measured, so that it cannot be read as a reading of the result.

### 2.4 Four qualifications, none of which the classifier carries

**A binary classifier over three cells is a coarse instrument, and the numbers
underneath it are not binary.** Charts L and J at `d=16` have essentially
identical path lengths (L2 median 2.979 against 2.872) and essentially identical
coordinate separations (1.475 against 1.441 decades), yet their witness barriers
differ by 3.6× and their **witness-to-null ratios by 13×** — 0.661 in chart L
against 0.049 in chart J. Their *null controls*' path lengths are matched too
(3.230 against 3.246), so the 13× is not a normalisation artefact on either side
of the ratio. So there *is* a chart effect at matched `d`; it is not a
ridge/basin one. Chart L's witness pairs are, in barrier terms, nearly as hard
to cross as ordinary prior pairs from the same chart; chart J's are twenty times
easier than its own ordinary pairs. **Both are basins. One is a much deeper basin
relative to its own null.**

Read as *connectivity relative to ordinary pairs*, the three cells order cleanly
and across both axes at once: **1/1100** in chart G at `d=4`, **1/20** in chart J
at `d=16`, **1/1.5** in chart L at `d=16`. A witness-to-null ratio near 1 says
crossing between two indistinguishable devices costs about what crossing between
two random ones does — two isolated basins that happen to look alike. A ratio far
below 1 says a preferential low-cost path exists between the members, whether or
not it dips below the instrument's floor. Chart G's is free; chart J's is cheap
and above the floor; chart L's is barely cheaper than crossing the prior.

**Chart G's pairs are closer together than the others', and part of its ridge is
that.** Its median max-coordinate separation is 0.392 decades against 1.475 and
1.441 — the witness criterion admits at 0.3, and chart G's set sits near that
edge while the `d=16` sets do not. A shorter line has less room for the
likelihood to fall. Normalising by path length leaves chart G at 15.35 log-units
per unit path against 199 and 569, so the ridge is **not merely** proximity — but
the relationship between barrier and path need not be linear, and only the
matched-`d` chart-L-against-chart-J contrast is free of this confound.

**And the deeper reading of "dimension effect" is geometric rather than
physical.** At `d = 4` the straight line between two indistinguishable devices
has fewer directions available to leave the indistinguishable set through. That
the ridge appears at the low dimension is consistent with the degeneracy being a
genuinely flat *set* whose codimension is small at `d=4` and large at `d=16`, and
this generation cannot separate that from a statement about semiconductors. What
it can say is that the split does not follow the chart.

**The direction of the bound is unchanged from generation 9 and still matters.**
Every barrier walks a *straight line* in that chart's own coordinates, so every
depth is an **upper bound** — a curved path can only be shallower. That direction
is favourable for the ridge result, which says barriers are low, and unfavourable
for both basin results. Chart J additionally spends one coordinate on a junction
ratio, which is not commensurate with a decade of doping. No search over paths
was run.

---

## 3. `WIT-01` — enacted, retro-applied, and it removes nothing

### 3.1 The rule, and what "along any coordinate" has to mean

> A pair whose separation along any coordinate falls below the grid resolution is
> not a witness and is excluded **before** counting, not filtered afterwards by
> refinement. State the admissibility ratio and apply it to every existing
> witness count.

Read literally the rule rejects almost every real witness. Two chart-J devices
sharing a junction are separated by exactly **zero** in that coordinate, which is
below any positive resolution, and they are a perfectly good witness. So it is
implemented on the separation that **qualifies** the pair: admissible iff some
coordinate is separated by at least `min_separation_decades` **and** that
separation is resolved by the reconstruction. Coordinates separated by a nonzero
but *unresolved* amount are counted and reported separately rather than treated
as either.

The resolution lives on the **chart**, not inside a search.
`Chart.coordinate_resolution` returns zero for every magnitude coordinate,
because anchor magnitudes reach the grid through `charts._lerp` exactly;
`ChartJ` overrides the junction with an exact node-index test, because
`ChartJ.reconstruct` depends on that coordinate *only* through the mask
`x_si < x_j`, so the node index is the whole of what the representation carries
about it. A pinned junction (`junction_scale = 0`) has **infinite** resolution,
which is the positive control every junction number in this repository rests on.

### 3.2 Applied to every committed witness count

| set | pairs offered | admissible | ratio | rule vacuous for this chart? |
|---|---:|---:|---:|---|
| **chart G**, `d=4` | 13 | 13 | **1.000** | yes |
| **chart L**, `d=16` | 37 | 37 | **1.000** | yes |
| **chart J**, `d=16` | 13 | 13 | **1.000** | no |

**The rule removes nothing.** Every witness pair in this repository qualifies on
a doping *magnitude*, and magnitude coordinates are exact, so for charts G and L
the ratio is 1.000 by construction. Chart J is the one chart where the rule
*could* bite and does not: all 13 of its pairs qualify on magnitude coordinates
too.

That is a result, and it is why the ratio has to be stated rather than assumed.
"The rule does not bite here" and "the rule was never applied here" are different
sentences, and only the first is checkable. `WIT-01` is, on today's chart
inventory, **a chart-J rule with no live instance** — and a rule whose scope is
stated can be checked against the next chart, while a rule whose scope is assumed
cannot.

### 3.3 What it does catch: a reported quantity, not a count

One chart-J pair has junctions **0.425 nm** apart on a grid whose node spacing is
**3.333 nm**. Those two devices build the same profile bit for bit. The pair is a
legitimate witness — it qualifies on magnitudes, 1.326 decades apart — but *"its
junctions are 0.425 nm apart"* is a statement about the grid, and it is withdrawn.
It is the only such quantity in the three sets.

### 3.4 The premise the rule was ordered on does not hold

The ruling states that the chart-J pairs which separate under refinement *"are
those whose junctions were nearly coincident — 0.4 nm apart, rising 195% — which
is sub-grid and was never a witness."* Measured against
`outputs/g9/junction_refine.json`, with the node spacing beside it:

| junction separation of the pairs that **survive** refinement | 26.6, 41.7, 63.2, 177.1, 178.4, 249.5, 422.9 nm |
|---|---|
| junction separation of the pairs that **separate** under refinement | 0.4, 3.4, 9.0, 196.2, 246.2, 412.2 nm |
| grid node spacing | 3.333 nm |

Of the six pairs that separate, **one** has a sub-node junction separation. The
other five separate with junctions 9 to 412 nm apart — up to 124 nodes — and the
surviving set includes separations of 26.6 and 41.7 nm. **Junction separation
does not predict refinement survival**, and `WIT-01` would not have prevented the
generation-9 finding: it admits all thirteen pairs, including the 0.425 nm one.

**What does predict it is headroom below the floor.** Sorted by observational
distance at `N=301`, the seven pairs that survive are exactly the seven smallest
and the six that separate are exactly the six largest; the largest surviving
distance is `0.01844` and the smallest separating one is `0.01873`, against a
floor of `0.02`. Four of the six cross it on a relative move of 1.2% to 7.9%,
which is the same size as moves seen in pairs that survive (`+4.8%`, `+5.6%`).
Only two show a rise that is large on its own terms — `+195%` at a 0.4 nm junction
separation and `+29%` at 9.0 nm, both within three nodes — and those two are the
genuine discretisation artefacts.

So the generation-9 headline stands with a sharper reading than it had: the
junction degeneracy survives refinement, six pairs cross the floor, and **most of
those six cross it because they started within 6% of it**, not because they were
sub-grid.

---

## 4. `SPEC-g10-3` — the validity boundary, stated and not tested

The adopted observation set is `V ∈ [0.15, 0.90]`, 16 points, from
`docs/spec/SPEC_g6.md` §1b. Every witness search, every barrier and every
spectrum in this repository uses it, so the boundary is common to the whole claim
surface and is not a property of any one result. The claim it bounds is the one
generation 9 left standing: *the observation set dominates the other three axes at
every operating point measured — 0.925 to 1.080 across twelve points, against ×21
to ×39 for junction, dimension and interpolant.* That stability was measured over
three bias windows — `0.15–0.90`, `0.15–0.50`, `0.50–0.90` V — and **all three sit
inside the converged range**.

**The two boundaries do not have the same epistemic status, and nine generations
have written them as if they did.**

| boundary | status | evidence |
|---|---|---|
| **lower, 0.15 V** | **MEASURED AND REJECTED BELOW** | the convergence sweep ran 19 biases over 0–0.9 V. For `V ≥ 0.15` the `N=301/601/1201` differences halve under refinement (`1.47e-3 → 1.20e-3` at 0.15 V). The non-monotone maximum comes entirely from `V = 0.10`, where `I ≈ 1.3e-3` A/m² and the solver's own current noise floor competes with discretisation |
| **upper, 0.90 V** | **UNTESTED — `PH-15`** | the convergence sweep's own upper end *is* 0.9 V. Above it there is no evidence in either direction, because nothing was ever solved there in this line of work |

Below 0.15 V the oracle was tested and found unconverged; that is a measurement.
Above 0.90 V the oracle was never tested; that is not. *"The solver is unvalidated
there"* must never be written as *"the solver fails there"*.

**Checked rather than asserted.** Every bias list in every artefact under
`outputs/` was read — **74** JSON files, this generation's own artefacts included —
and the largest bias any artefact was ever evaluated at is **0.9 V**. Reading files is not extending the range.

**`PH-15` labels, carried forward:**

* the observation-set dominance is bounded to `V ∈ [0.15, 0.90]`; outside that
  range it is **untested**, not weaker;
* `rank(window width)` climbing 1 → 4 is measured over widths 0.10–0.75 V centred
  at 0.525 V, all inside the converged range; the rank outside it is **untested**
  — the curve is `rank(observation set)` in `outputs/g9/rank_obs.json`, and every
  point on it carries its own `rank(cutoff)` curve;
* `SPEC-g10-1`'s falsification of the localisation mechanism is bounded the same
  way. It says nothing about windows outside `[0.15, 0.90]` V.

**Not tested here, and why.** The clause says state the range, not extend it.
Extending it is a different study with a different convergence burden: a bias
above 0.90 V would require the discretisation floor to be re-measured there before
any identifiability number taken there meant anything, and running one without
the other would produce a number with no floor beneath it.

---

## 5. Negative controls (mandatory)

`outputs/g10/negative_control.json`. All five behave as required.

| # | control | construction | required | got |
|---|---|---|---|---|
| 1 | the localisation measure separates the extremes | a Jacobian whose leading direction is a single anchor, against one whose leading direction is uniform | `1/16` and `1.000` | **0.0625** and **1.000** |
| 2 | the measure is not fooled by the width axis itself | one Haar-random unit vector per width, scored by the same statistic; the axis carries no information about them | `spearman < 0.7` | **+0.067** |
| 3 | `WIT-01` rejects a sub-node pair and admits a real one | a planted chart-J pair 0.4 decades apart in the junction coordinate, placed in the logistic's saturated tail so the junctions stay inside a single node interval; and the 694 nm / 271 nm headline pair | REJECTED, for the stated reason; ADMITTED | **rejected as unresolved**; **admitted** |
| 4 | the ridge/basin classifier returns both answers | one chart-L device against itself; two chart-L devices 1.6 decades apart at every anchor | RIDGE; BASIN, on a certified path | **RIDGE** (barrier 0.0); **BASIN** (barrier 1.315e+05, certified) |
| 5 | a pinned junction is still not different | chart J with `junction_scale = 0` against **chart G** at `d=15`, retained from generation 9 and extended with the `WIT-01` resolution | identical magnitude columns, zero junction column, **infinite** resolution | **not different**; resolution `inf` |

Control 3 is the one that needed care. The obvious construction — two devices
whose junction coordinates differ by a fraction of a node — is thrown out by the
**separation criterion** before `WIT-01` is consulted, so it would report
"rejected" whatever the rule did and prove nothing. The construction that
actually tests the rule uses the logistic's saturated tail, where `dx_j/ds` has
collapsed: a 0.4-decade move in the coordinate, comfortably past the criterion,
shifts the junction by 0.06 nm. The control asserts the rejection *reason*, not
just the rejection.

---

## 6. What this generation withdraws, and what replaces it

**Withdrawn.** *"The geometry of the degeneracy is chart-dependent — a ridge at
the instrument floor in one chart, isolated basins in another."* The comparison
that produced it was confounded in chart and dimension together. At matched
`d=16` both charts are basins.

**What replaces it, and it is two statements rather than one.**

1. **The ridge is a property of the dimension.** Only `d=4` puts witness pairs at
   the instrument's own floor — 6 of 13 there, 0 of 37 and 0 of 13 at `d=16` —
   and it survives normalisation by path length (15.35 log-units per unit path
   against 199 and 569). The likely reading is geometric: at `d=4` the straight
   line between two indistinguishable devices has fewer directions available to
   leave the indistinguishable set through.

   **Amended at close (ruling of 2026-08-26 §3).** Every barrier here is an
   *upper* bound, so the two `d=16` statements are **searches that found no
   connecting path below the floor along the straight line**, not demonstrations
   that the members are separated. The dimension ordering itself is undisturbed —
   both sides of the comparison are upper bounds — but what is untested is
   whether the slack in the bound differs between cells, which is what a
   minimum-energy path would measure and what `PATH-01` records as open. `AH-13`.
2. **What the chart moves at matched `d` is the depth, not the kind.** Charts L
   and J at `d=16` have the same path lengths and the same coordinate separations
   and differ by 13× in witness-to-null ratio (0.661 against 0.049). Chart L's
   witness pairs are nearly as hard to cross as its own ordinary prior pairs;
   chart J's are twenty times easier than its own.

**Unchanged.** Generation 9's two cells reproduce bit for bit. The chart-G ridge
stands — it is strengthened by the bound direction, since an upper bound at the
floor means the true barrier is at most at the floor — the junction degeneracy
survives refinement, and every witness count is admissible under `WIT-01`. The
chart-J basin stands as a **search statement**, amended at close with the
chart-L one; see `docs/CLOSE_RULING.md` §4.

**Added at close, and it is not in this generation's measurements.** `WIT-02`
requires every witness to be refined before it is counted. Two of the three
committed sets do not satisfy it — **chart G 3 of 13** and **chart L 0 of 37** —
and the chart-L one is the set item 1 above rests on. Register:
`outputs/close/wit02_register.json`.

### 6.1 The paper's spine, with item 4 rewritten and item 6 added

The ruling of 2026-08-26 §6 proposed five items. Four survive as written; the
fourth does not, and a fifth measured statement joins them. `R-3` reserves
`papers/**`, so this is the spine as the measurements now support it, not an edit
to the draft.

1. Identifiability verdicts in device inverse problems are dominated by the
   measurement protocol, and the domination is one-against-three rather than an
   ordering: ×1.17 against ×21–×39 across twelve operating points. *Unchanged.*
2. Bias-window **width** sets the rank (1 → 4); spacing moves the spectrum
   (19.8%) and not the rank. The two are separable and had been fused.
   *Unchanged.*
3. The degeneracy is real and survives refinement in each of the committed
   witness sets that had been through the battery at this generation — globally,
   in **chart G** at `d=4`, 3 of 13 pairs refined and all 3 surviving; in
   **chart J** at `d=16`, 13 of 13 refined and 7 surviving; **chart L** at
   `d=16` stood at 0 of 37 and had never been tested. 8.18× and 14.75× in
   doping, 694 nm against 271 nm in junction depth, the last falling 1.7% under
   `N = 301 → 1201`. *Unchanged, with the account of which pairs do **not**
   survive corrected: it is proximity to the floor, not sub-grid junctions.
   Denominators added after the fact under `DOC-08`; the sentence read "in every
   chart tested", which was true over two sets and read as three. The chart-G
   figures were superseded at the close addendum — `docs/CLOSE_ADDENDUM.md`,
   13 of 13 refined and 12 surviving — and are left here as what this generation
   measured.*
4. ~~Its geometry is not universal: a ridge in one chart, isolated basins in
   another.~~ **Its geometry follows the dimension, not the chart.** Only `d=4`
   puts witness pairs at the instrument's own floor; at both charts tested at
   `d=16` no connecting path below the floor was found. What the chart moves at
   matched `d` is the *depth* relative to that chart's own null — 13× between two
   charts with matched path lengths. *Amended at close:* the `d=16` results are
   **search statements against an upper-bound barrier**, not separation proofs,
   and the minimum-energy path was not computed.
5. Local analysis is structurally incapable of detecting any of (3) or (4).
   *Unchanged.*
6. **The obvious mechanism for (2) is wrong.** The window does not set the rank by
   selecting spatial regions: the leading observable direction's spatial extent is
   invariant to the window to within 2.5% while the rank quadruples, and what
   movement it has runs opposite to the prediction. A negative, measured against a
   criterion fixed in advance, and the sharpest open question the project has.

   *At close, this item folds into item 2 and item 6 becomes the `0.9 V` validity
   bound; see `docs/CLOSE_RULING.md` §5 for the spine as the closing ruling states
   it. The free check §5 allowed adds a description: the rank climb is the
   spectrum **flattening** — `σ₁` nearly fixed and falling while `σ₂…σ₄` rise by
   ×21–×535 in the normalised spectrum, 95.6%–97.9% of the motion in shape.*

---

## 7. Highest remaining scientific risk

**The mechanism question is still open, and this generation narrowed it rather
than answering it.** `SPEC-g10-1` shows the rank climb is not the leading
observable direction broadening: `v₁`'s spatial extent moves by under 2.5% while
the count of directions above the noise quadruples, and where it moves it moves
the wrong way. What replaces "the window selects spatial regimes" is not another
mechanism but a sharper question — why is the leading direction essentially fixed
while the ones behind it cross the noise floor? Nothing here answers it, and the
clause forbade chasing it.

**Second.** The ridge/basin classification rests on a barrier metric that walks a
straight line in each chart's own coordinates. Every depth is an upper bound; the
three sets walk lines through three different coordinate systems, one of which
spends a coordinate on a quantity that is not a decade of doping; and the `d=4`
set's members sit 3.7× closer together than the `d=16` sets'. Path-length
normalisation and the matched-`d` contrast each address part of this and neither
addresses all of it. A search over paths, rather than the straight line, is the
measurement that would settle it and was not run.

**Third.** `WIT-01` was enacted against a defect it turns out not to reach. The
sub-grid junction separation was real and is withdrawn, but the rule that was
supposed to have caught the generation-9 finding admits every pair involved in it.
The rule is correct and worth keeping — it is the only thing standing between a
future chart with a quantised coordinate and a published count of its own grid —
but this generation records that it was ordered on a premise that does not hold,
and that the thing which actually predicts refinement survival is proximity to
the distinguishability floor, which no rule in this repository currently guards.
