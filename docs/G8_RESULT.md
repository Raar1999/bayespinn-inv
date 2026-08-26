# Generation 8 — a third chart, the observation set, and how many devices

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
>

**What this generation settles, in one paragraph.** Generation 7 discovered that
two identifiability results had been measured in two different
parameterisations, named them **chart G** and **chart L**, and found that at
matched `d` their *local* spectra agree to within 3%. It recorded, as its highest
remaining scientific risk, that those two charts differ along exactly one axis.
Generation 8 measured a **third chart** off that axis and perturbed the
**observation set**, and both move the spectrum by far more than the chart change
does. The chart-invariance statement survives and shrinks: it is a statement
about two interpolants, not about parameterisation. What the *local* spectrum is
actually sensitive to is **what you measure**, and after that **where the
junction is**.

**Measurement conditions, once, for every number below.** Oracle-arbitrated
throughout — the float32 surrogate is never called (`SPEC-g6-5`, `PH-22`); the
NumPy Scharfetter–Gummel solver in float64 on a 301-node uniform grid decides
every question. Log-uniform **prior** on the magnitude of the doping at each
anchor over `1e21 – 1e23 m^-3`; chart J's junction coordinate carries its own
prior, stated in §2 with its own hash. **Noise model** independent Gaussian in
relative terminal current at a **level** of 2% (`noise_rel = 2.0e-2`).
**Observation set** 16 **bias** points evenly spaced over 0.15 – 0.90 V — except
in §3, whose entire subject is changing it. Two floors, reported separately and
never subtracted (`PH-13`, `ADR-0002`): a **noise floor** of `2.0e-2` and a
solver **discretisation floor** of `1.5e-3`; their maximum, `2.0e-2`, is the
distinguishability floor.

Artefacts: `outputs/g8/`, manifest `manifest.json`, machinery commit `01f0281`.

> ## Superseded in part at generation 9
>
> Generation 8's own closing caveat -- *every cell sits at one operating point* --
> was tested at nine further operating points and was right. What moved:
>
> * **The four-way ordering does not survive.** Five distinct orderings appear
>   across the nine points under the larger-movement statistic; the ordering
>   below is recovered at 2 of 9 under that statistic and at 0 of 9 under the
>   milder one. The summary *observation set > junction > dimension >
>   interpolant* is withdrawn as a general claim. What survives is one-against-
>   three: **the observation set dominates at every operating point measured**,
>   its largest movement spanning 0.925-1.080, while the other three swing by
>   more than a factor of twenty each and trade places.
> * **The ordering was never one ordering.** Its two natural statistics disagree
>   at generation 8's own operating point -- by the largest movement each axis
>   produces the junction leads, by the mildest the observation set does -- and
>   nothing here says which was meant.
> * **section 2's chart-invariance survivor is narrower still.** The
>   chart-G-to-chart-L movement at matched `d` is 2.8% here and **101.5%** at
>   another device in a narrower bias window. It is a property of a
>   `(device, window)` cell.
> * **section 2's 13 *global* chart-J witness pairs at `d = 16` become 7** under
>   the grid refinement the *global* doping witnesses survived at generation 6. The 694 nm / 271 nm headline
>   pair survives; the count does not.
> * **section 4's licensed set is not a property of `(chart, d)`.** At a 0.10 V
>   bias window chart G at `d = 16` has a spectral gap of x230.6 at the cutoff,
>   which the inherited criterion licenses. The licence follows the gap and the
>   gap follows the cell.
> * **section 5's basin reading is corrected for chart G.** Measured on the
>   witness pairs themselves rather than an index-ordered sample, their median
>   likelihood barrier is 8.31 log-units against a floor barrier of 8.0 -- they
>   are a ridge, not two maxima. The generation-8 sentence *the number of
>   likelihood basins is larger than the number of profile-distance clusters*
>   holds for chart J and is the wrong way round here.
>
> Everything else below stands as measured. See `docs/G9_RESULT.md`.

Reproduce with:

```bash
PYTHONPATH=src python scripts/run_g8.py --out outputs/g8 \
  --phases reproduce,chart_j,obs_set,ranks,modes,negative_control
```

---

## 1. `SPEC-g8-1` — `CHART-01` closed structurally, and what the census found

The operator's bar was not documentation. It was three properties, and each is a
test rather than a sentence.

**One reconstruction operator.** `bayespinn_inv.inverse.charts._lerp` is the only
place in the package where anchor values reach the solver grid; every chart
arrives there through `Chart._to_grid`.
`tests/test_one_reconstruction_g8.py::test_every_chart_reaches_the_grid_through_to_grid`
counts the calls — exactly one per reconstruction — so a chart that grew its own
resampler would fail by calling the shared one zero times.

**The vector carries its chart.** `ScharfetterGummel1D.solve` no longer
interpolates. It takes a grid-valued array, or a `ChartedDoping` that carries the
chart it is a vector in, and raises `DopingChartError` on anything else.

**A second path cannot be introduced silently.** An AST guard walks every module
under `src/` and `scripts/` and fails on any interpolation call not named in an
allowlist **with its count and its reason** — per call, not per file, so adding a
second interpolation to an already-listed module fails too. Both `SW-20` controls
ship with it: a planted resampler it must catch, and a module whose *text*
contains the forbidden call and whose *code* does not.

### The census, which is the finding

Before the resampler was deleted, `solve` was patched to count every call whose
doping array was not grid-valued, and the whole suite was run. The implicit
reconstruction was load-bearing at **five call sites in `src/`** and nine more in
`tests/`, across three grid resolutions:

| call site | vector length | grid | what it produced |
|---|---|---|---|
| `inverse/identifiability.py::sg_forward_jacobian` | 16, 8 | 301 | **the published local rank** |
| `inverse/charts.py::chart_forward_jacobian` | 16 | 301 | the generation-7 chart-L cells |
| `surrogate/iv_surrogate.py::simulate_iv_dataset` | 16 | 201 | **the surrogate's entire training set** |
| `data/splits.py::oracle_iv` | 16 | 201 | the supervised datasets |
| `inverse/charts.py::assert_matches_solver` | 16 | 301 | the generation-7 positive control |
| `tests/` (3 modules, 9 sites) | 9, 16 | 201, 301, 601 | fixtures and the grid-convergence check |

Two consequences, neither visible before the census.

* **Chart L is not only the local-study chart.** It is the chart the SG-labelled
  datasets and the trained surrogate were built in. Every supervised label this
  repository generates from the oracle — `data/splits.py::oracle_iv` for the
  protocol splits, `surrogate/iv_surrogate.py::simulate_iv_dataset` for the
  surrogate — came from a 16-anchor vector reconstructed by chart L's operator,
  and no file said so. The continuous operator is grid-independent — index-based
  interpolation from `d` anchors samples one piecewise-linear function whatever
  `N` is — so the three resolutions are three samplings of one chart, not three
  charts. True, and until now unwritten.
* **Chart G had three implementations, one of them inside its own falsifier.**
  `run_global_identifiability.py::make_oracle` and
  `run_witness_falsifier.py::solve_profile` each wrote the chart-G reconstruction
  out by hand, and `ChartG` was a third. The falsifier generation 6 used to check
  the witness result re-derived the chart rather than importing it, so it could
  detect a solver-level error and not a chart-level one. The independence it was
  supposed to supply was never there. The result survives — §5 re-runs both
  through one class and gets the same answer — but the *check* was weaker than it
  looked. All three now call one class.

### Nothing moved

24 profiles were captured from the **old** `solve` before deletion — three grid
resolutions × four dimensions × two profile families — and their SHA-256 digests
are frozen in `tests/data/chart_l_resampler_golden_g8.json`. The new operator
reproduces every one byte for byte.

`CHART-01` moves from `MITIGATED` to **`RESOLVED-STRUCTURALLY`**.

### One correction to the commit that made the fix

The machinery commit `01f0281` says the resampler was "load-bearing at seven
production call sites across three grid resolutions". Three grid resolutions is
right; **seven is wrong**. The census found *five* in `src/` and nine more in
`tests/`, and the message conflated the two lists. `R-4` makes a commit message
uncorrectable, so the correction is here, and `DOC-07`'s guard — which matched
digits beside "passed"/"tests" and so did not fire on a count spelled out in
words — is widened at this generation with that commit as its positive control.

---

## 2. `SPEC-g8-2` — chart J: the junction as a free coordinate

### What chart J is

Coordinates, `d` of them: `theta = [s, m_1, ..., m_{d-1}]`, where `m_i = log10|C|`
at `d-1` equally spaced anchors exactly as in chart G, and `s` places the junction
in decades of the ratio `x_j / (L - x_j)`:

```
x_j / L = 1 / (1 + 10**(-s * junction_scale))
```

`s = 0` is the device midpoint, which is where charts G and L pin it.

**Positive control.** Chart J at `s = 0` **is** chart G at `d-1`, bit for bit, at
every `d` tested and for generic magnitudes
(`tests/test_charts_g8.py::test_positive_control_J_at_s0_is_G_at_d_minus_one`),
and the magnitude columns of its Jacobian are bit-identical to chart G's at
`d-1`. Without that, "chart J moved the spectrum" would be confounded with
"chart J is a different chart in some other way too".

**Why the junction and not a spectral basis.** It is a real fabrication
parameter, it is the coordinate inverse design actually cares about, and it is
the one generation 7's own finding pointed at: chart G's junction is a
grid-level discontinuity that no continuous interpolant can produce, so a chart
in which it *moves* is off the axis the two older charts span, for a physical
reason rather than a numerical one.

Precisely how the reachable sets differ:

* chart G's sign flip is pinned between the two grid nodes straddling the
  midpoint and cannot move at any `d`;
* chart L's zero crossing is *not* pinned to the midpoint — it lands where the
  arithmetic interpolant crosses zero, which depends on the two magnitudes
  straddling it — but it cannot leave the one anchor interval of width
  `L/(d-1)` containing the midpoint;
* chart J's junction is free over the whole device and is a genuine
  discontinuity wherever it lands.

### Charts G and L cannot hold a displaced junction

Two probes, following the generation-7 containment design: one that isolates the
junction obstruction and one that carries both obstructions at once. A single
probe measures one thing and gets quoted as if it measured two.

`REP-01`: every residual below names the projection that produced it, and the
row reports the best of the two admissible projections (`collocate` and least
squares in `log10|C|`).

| probe | `x_j / L` | best chart-G stand-in | nodes doped the wrong type | best chart-L stand-in | nodes doped the wrong type |
|---|---|---|---|---|---|
| flat magnitude | 0.25 | 0.0000 dec (collocate) | **75 of 301** | 1.0000 dec (collocate) | **76 of 301** |
| flat magnitude | 0.35 | 0.0000 dec (collocate) | **45 of 301** | 1.0000 dec (collocate) | **46 of 301** |
| flat magnitude | 0.50 | 0.0000 dec (collocate) | **0 of 301** | 1.0000 dec (collocate) | **1 of 301** |
| flat magnitude | 0.65 | 0.0000 dec (collocate) | **45 of 301** | 1.0000 dec (collocate) | **45 of 301** |
| flat magnitude | 0.75 | 0.0000 dec (collocate) | **75 of 301** | 1.0000 dec (collocate) | **75 of 301** |
| witness member a magnitudes | 0.25 | 0.0282 dec (log10) | **75 of 301** | 1.2246 dec (log10) | **77 of 301** |
| witness member a magnitudes | 0.35 | 0.0282 dec (log10) | **45 of 301** | 1.2246 dec (log10) | **47 of 301** |
| witness member a magnitudes | 0.50 | 0.0282 dec (log10) | **0 of 301** | 1.2246 dec (log10) | **2 of 301** |
| witness member a magnitudes | 0.65 | 0.0282 dec (log10) | **45 of 301** | 1.2246 dec (log10) | **43 of 301** |
| witness member a magnitudes | 0.75 | 0.0282 dec (log10) | **75 of 301** | 1.2246 dec (log10) | **73 of 301** |

Both probes carry the chart-G reconstruction of the target's magnitudes; the *flat magnitude* rows isolate the junction obstruction, because a constant magnitude is something both older charts reproduce exactly, and the *witness member a* rows add the interpolant obstruction on top of it.

The chart-L residual sits at exactly 1.0000 decade in every row, which is a lattice coincidence rather than a saturation constant: chart L ramps linearly from -1e22 to +1e22 across the anchor interval containing the midpoint, and one grid node in that ramp lands where the magnitude is 1e21 - one decade below the target. The node where the ramp crosses zero has no log10 and is excluded and counted (`nodes_excluded_nonfinite` in the artefact), never patched.

The magnitude is reproduced almost exactly and the **junction is put in the wrong
place**, which shows up not as a norm but as a count of grid nodes doped the
wrong type. That is a device-level statement: charts G and L answer with a device
whose p-region and n-region boundaries are elsewhere.

### The spectrum, and the units problem that comes with it

Chart J's Jacobian has `d-1` columns in decades of doping and **one in decades of
junction ratio**. A singular spectrum of a matrix with mixed column units depends
on the relative scaling of those units, and there is no units-free choice. So the
choice is stated, its effect is measured, and the two readings are kept apart:

* the **full spectrum** is reported *with* its `junction_scale` and is **not** a
  chart-invariance measurement;
* the **magnitude sub-block** — the 15 doping columns — is unit-homogeneous, and
  it is.

| chart J cell | `junction_scale` | junction node shift per FD step | junction column norm | rank at 2% | full-spectrum move vs chart G `d=16` | magnitude-block move vs chart G `d=15` |
|---|---|---|---|---|---|---|
| `J_d16_s0_js0.1` | 0.1 | 0.86 | 4.650e-02 | 4 | 5.3% | 0.0% |
| `J_d16_s0_js1` | 1 | 8.63 | 7.971e-01 | 5 | 47.6% | 0.0% |
| `J_d16_s0_js10` | 10 | 77.92 | 1.179e+01 | 5 | 1016.9% | 0.0% |
| `J_d16_xj0.35` | 1 | 7.99 | 2.160e+00 | 5 | 297.4% | 219.2% |
| `J_d16_xj0.65` | 1 | 7.72 | 1.706e-01 | 5 | 38.2% | 9.1% |
| `J_d16_pinned` | 0 | 0.00 | 0.000e+00 | 4 | 5.3% | 0.0% |
| chart G at `d=16`, for scale | — | — | — | 4 | 0% (reference) | 5.0% |

Read the last two columns against each other. The full-spectrum column spans 5.3% to 1017% for the **same device** at the **same operating point**, moved only by the units of a coordinate — which is why no chart-invariance claim may be made from it. The magnitude-block column is exactly 0% wherever the junction is at the midpoint, at every `junction_scale`, because there chart J's magnitude columns are chart G's at `d=15` bit for bit.

### `SPEC-g8-2`'s falsifier fires

The clause reads: *the spectrum at matched `d` moves materially, which retires the invariance claim to its measured family and is a fine outcome.*

Measured on the unit-homogeneous block, against chart G at `d=15` — the magnitude-matched reference, because chart J spends one coordinate on the junction:

* junction displaced to `x_j/L = 0.35`: **219%**
* junction displaced to `x_j/L = 0.65`: **9.1%**
* chart-G-to-chart-L change at `d=16`, same operating point, for scale: **2.8%**
* chart G `d=15` against chart G `d=16`, i.e. the *dimension* alone: **5.0%**

**The falsifier fires.** A displaced junction moves the spectrum 79x and 3x more than the chart-G-to-chart-L change does, and the dimension alone moves it about twice as much as that change does. So the generation-7 sentence *the dimension moves the rank and the chart does not* is **retired to its measured family**: within piecewise interpolants over equally spaced anchors in `log10|C|` with a fixed sign convention, the reconstruction operator does not move the spectrum at matched `d`, while `d` does. Outside that family it says nothing, and chart J is outside it.

The asymmetry between the two displacements is a property of **this** operating point, whose magnitudes are not symmetric about the midpoint, and is reported rather than explained.

### Native witness search in chart J

**Prior**, fixed and hashed before sampling (`AH-14`): junction uniform in **physical position** over `x_j/L` in [0.2, 0.8] — junction depth is a fabrication length and a flat prior on the length is the defensible default, where a flat prior on `s` would pile mass at the contacts — and log-uniform in magnitude at 15 anchors over `1e21 – 1e23 m^-3`. Hash `236ff6576a850965...`. `GlobalStudyConfig.prior_hash` describes 16 log10 doping magnitudes and so does **not** identify this prior; both hashes are in the artefact.

**Budget** 1200 draws, 1200 oracle-certified (0 rejected for non-convergence, 0 for an untrustworthy current; `PH-19` — rejections are counted, not dropped), **719,400** pairs examined.

**Result: 13 witness pair(s)** — a *global* non-identifiability search, in chart J at `d=16`.

Closest: observational distance **1.5166e-02** (75.8% of the 2.0e-02 floor), reported separation 1.6089.

**The separation metric mixes units in chart J** and the split is reported per witness: `witness_search` uses `max|dtheta|` over coordinates, and coordinate 0 is decades of junction ratio while the rest are decades of doping. For the closest pair the magnitude-only separation is 1.6089 decades and the junction-only separation is 0.0463 decades, i.e. junctions at 484 nm and 457 nm. Under the unit-homogeneous criterion — magnitude separation alone at or above 0.3 decades — **13 of 13** survive.

**And the junction itself is not identifiable.** The witness pair whose junctions are furthest apart puts them at 694 nm and 271 nm — **423 nm apart in a 1000 nm device** — with an observational distance of 1.7551e-02, below the 2.0e-02 floor, and a magnitude separation of 1.103 decades. Terminal I–V cannot locate the metallurgical junction to better than that once the doping is free to compensate. This is the clause's physical payoff: the free coordinate was chosen because it is a fabrication parameter, and it turns out to be degenerate in the same way the magnitudes are.

**Not comparable to the other charts' counts.** Three things differ at once — the chart, the coordinate meaning, and the prior, which for chart J is not even the same *kind* of prior. Existence is a search outcome and transfers; frequency is a density estimate and does not.

---

## 3. `SPEC-g8-3` — the observation set moves the spectrum an order of magnitude more than the chart does

The generation-7 result — spectra agreeing to 3% between charts at `d = 16`
despite operating points 1.24 decades apart — is either a real invariance or a
sign that at `d = 16` the spectrum is dominated by the observation operator
rather than by the parameterisation. The ruling asked for the cheap
discriminator: perturb the observation set and compare the movement against the
movement the chart change produced.

**Metric.** The same one generation 7 used for the chart comparison: the maximum
relative movement of the leading five singular values. One ruler for both.

**The row-count confound, named rather than dropped.** `min_snr` discards bias
rows whose current does not clear the oracle's own noise floor, so the number of
rows actually differenced is not the number offered — the baseline offers 16 and
uses 15. A singular value of a taller matrix is larger for that reason alone, so
two readings are given: the raw movement, and the movement after dividing each
spectrum by `sqrt(rows used)`. The verdict is the same under either.

| observation set | biases offered | rows used | rank at 2% | move vs baseline | move, `sqrt(rows)`-normalised |
|---|---|---|---|---|---|
| **chart G, `d=16`** | | | | | |
| chart G: baseline 16 linear 0.15 0.90 | 16 | 15 | 4 | 0.0% | 0.0% |
| chart G: 16 geometric 0.15 0.90 | 16 | 14 | 4 | 19.8% | 17.0% |
| chart G: 16 linear 0.30 0.60 | 16 | 16 | 2 | 97.4% | 97.5% |
| chart G: 16 linear 0.50 0.90 | 16 | 16 | 4 | 66.3% | 67.4% |
| chart G: 8 every other | 8 | 7 | 3 | 45.8% | 20.7% |
| chart G: 8 lower half | 8 | 7 | 2 | 98.4% | 97.7% |
| **chart L, `d=16`** | | | | | |
| chart L: baseline 16 linear 0.15 0.90 | 16 | 15 | 4 | 0.0% | 0.0% |
| chart L: 16 geometric 0.15 0.90 | 16 | 13 | 4 | 19.9% | 14.0% |
| chart L: 16 linear 0.30 0.60 | 16 | 16 | 2 | 97.6% | 97.7% |
| chart L: 16 linear 0.50 0.90 | 16 | 16 | 4 | 65.9% | 67.0% |
| chart L: 8 every other | 8 | 7 | 3 | 44.8% | 19.1% |
| chart L: 8 lower half | 8 | 7 | 2 | 98.7% | 98.0% |
| **chart J, `d=16`** | | | | | |
| chart J: baseline 16 linear 0.15 0.90 | 16 | 15 | 5 | 0.0% | 0.0% |
| chart J: 16 geometric 0.15 0.90 | 16 | 13 | 5 | 20.7% | 14.8% |
| chart J: 16 linear 0.30 0.60 | 16 | 16 | 2 | 97.5% | 97.6% |
| chart J: 16 linear 0.50 0.90 | 16 | 16 | 4 | 60.5% | 61.8% |
| chart J: 8 every other | 8 | 7 | 4 | 42.0% | 15.0% |
| chart J: 8 lower half | 8 | 7 | 2 | 99.5% | 99.3% |

**The falsifier fires, and not marginally.** The chart-G-to-chart-L change at `d=16`, at this operating point, moves the leading spectrum by **2.8%**. The mildest observation-set perturbation tested — the **same 16 biases over the same 0.15–0.90 V range**, spaced geometrically instead of linearly — moves it by **19.8%**, and narrowing to 0.30–0.60 V moves it by **97.4%**. After `sqrt(rows used)` normalisation the two are 17.0% and 97.5%; the row count is not doing the work.

**Is that a fair comparison?** The obvious objection is that narrowing a bias range is a large change to the experiment while swapping one interpolant for another is a small change to the model, so the two perturbations are not commensurable. The geometric-spacing row answers it. That variant keeps the same 16 biases, the same endpoints and the same range and changes only where the intermediate points sit -- about as small a change to an experiment as one can make while changing it at all. The chart change it is compared against is not small: charts G and L interpolate differently between **every** pair of anchors, and the two cells sit at operating points **1.24 decades apart in profile space**, because chart L cannot hold the chart-G device exactly. The comparison is therefore *two rather different devices through one instrument* against *one device through two barely different instruments*, and the instrument wins by a factor of seven. The objection cuts the other way.

So the operator's second reading is the right one. *The chart does not matter* is really **at `d = 16`, little about the parameterisation matters relative to what you measure** — and that is a different and more useful sentence, because the observation set is the thing an experimenter controls.

**The rank itself moves with the bias range.** Over 0.30–0.60 V the identifiable count at a 2% cutoff falls from 4 to 2 in chart G at `d=16`, and by the same amount in chart L and in chart J at the same `d`. An identifiable rank is therefore a property of the **(device, observation set)** pair and never of the device alone; every rank this repository publishes carries its 16 biases over 0.15–0.90 V for that reason.

---

## 4. `SPEC-g8-4` — rank is a curve, and a bare integer is licensed by a gap, not by `d`

Every rank in this generation is produced by
`bayespinn_inv.inverse.identifiability.rank_cutoff_record`, which reports the
spectrum first, then the rank at every cutoff on the repository's existing
`NOISE_GRID`, then the largest multiplicative gap and whether the operational
cutoff falls inside it. The gap criterion is **generation 7's, unchanged**, which
is what keeps `AH-14` clean: it was fixed before these cells existed.

| cell | chart | `d` | rank at the 2% cutoff | resolvable | largest multiplicative gap | cutoff inside it? | bare integer licensed? | profile distance from the operating point |
|---|---|---|---|---|---|---|---|---|
| `G_d4` | chart G | 4 | **3** | 4 | x7.39 after index 2 | **yes** | **yes** | 0 to round-off (exact) |
| `G_d16` | chart G | 16 | **4** | 5 | x4.99 after index 1 | no | **no** | 0 to round-off (exact) |
| `L_d4` | chart L | 4 | **3** | 4 | x17.46 after index 2 | **yes** | **yes** | 1.7856 dec (log10) |
| `L_d16` | chart L | 16 | **4** | 5 | x5.11 after index 1 | no | **no** | 1.2326 dec (log10) |
| `J_d4` | chart J | 4 | **4** | 4 | x6.21 after index 1 | no | **no** | 0.5172 dec (collocated junction at midpoint + chart-G anchors) |
| `J_d16` | chart J | 16 | **5** | 5 | x6.59 after index 1 | no | **no** | 0.0739 dec (collocated junction at midpoint + chart-G anchors) |

**A bare integer rank may be quoted in 2 of the 6 cells: `G_d4`, `L_d4`.** Everywhere else the number is a threshold count and must never appear without its cutoff.

**The ruling's parenthetical needs one correction.** §5 says a bare integer appears *"only where a gap justifies it — which today means `d=4` only"*. Measured across six cells the licence follows the **gap**, not the dimension: chart J at `d=4` has no gap at the cutoff either, so it is chart G at `d=4` and chart L at `d=4`, and `d=4` is a coincidence of those two charts rather than a property of the dimension.

**A wide plateau is not evidence when the estimator's floor is what pins it.** Every cell's record carries `plateau_containing_operational_cutoff.limited_by_resolvable_rank`, which is true when the rank has saturated at the number of singular values the finite-difference estimate can resolve at all. Reading such a plateau as *the rank is robust to the cutoff* is the trap; the flag is the exit, and it fires here: `J_d4`, `J_d16` hold their rank across the whole cutoff grid down to `noise_rel = 1e-6`, which looks like the most robust result in the table and is instead the estimator running out of resolution. The two cells whose rank a gap does license have *narrower* plateaus, which is the right way round.

---

## 5. `SPEC-g8-5` — how many basins, and the reproduction that made it answerable

### The reproduction that had to come first

The existing artefacts could not answer this clause. The two *global* searches — chart G at `d=4` and chart L at `d=16` — **found** 13 and 37 witness pairs and **kept** the first five of each, because `witness_search` rendered five. Both were therefore re-run through the post-`CHART-01` code with every witness rendered, which doubles as the regression control on the structural fix.

| search | prior draws | pairs examined | witnesses now | witnesses in the committed artefact | identical? |
|---|---|---|---|---|---|
| chart G, `d=4` (generation 6) | 2000 | 1,999,000 | 13 | 13 | **yes** |
| chart L, `d=16` (generation 7) | 1200 | 719,400 | 37 | 37 | **yes** |

Both reproduce exactly, and the distances of the five witnesses the old artefacts do carry agree to 0.0e+00 and 0.0e+00. The structural fix moved no published number.

### The criterion, fixed and hashed before any distance was computed

* **metric** `max_abs_log10_decades` — the maximum over grid nodes of `|log10|C_a| - log10|C_b||`, in decades, on reconstructed profiles so that members of different charts are compared as devices;
* **linkage** `single`;
* **threshold** 0.3 decades, **inherited** from `GlobalStudyConfig.min_separation_decades`, this repository's own pre-existing definition of *far apart*, not chosen here;
* sign disagreements counted separately and never folded into the distance (`sign_disagreements_folded_in = False`);
* **hash** `430caed50544057a15b78dd969c23811...`, written to the artefact before clustering, as `AH-14` requires.

`SPEC-11`'s rank-curve rule applies to a cluster count as much as to a rank, so the count is reported **as a curve over the threshold** and the pre-registered value is a point on it.

### The answer

| witness set | pairs | members | basins at 0.3 dec | cluster sizes | basin count across 0.05 – 3.0 dec | witness-graph components |
|---|---|---|---|---|---|---|
| chart G, `d=4` | 13 | 26 | **20** | 1x6, 1x2, 18x1 | 26 at 0.05 dec down to 1 at 3 dec | 13 (13x2) |
| chart L, `d=16` | 37 | 67 | **67** | 67x1 | 67 at 0.05 dec down to 1 at 3 dec | 31 (1x4, 3x3, 27x2) |
| chart J, `d=16` | 13 | 26 | **26** | 26x1 | 26 at 0.05 dec down to 1 at 3 dec | 13 (13x2) |

**Do the witness pairs join two different basins?** Each pair is a *global* result — chart G at `d=4`, chart L at `d=16` — and each basin is a parameter-space cluster, so the two need not agree. Computed from the committed artefacts rather than in the run: chart G, `d=4` **11 of 13** do; chart L, `d=16` **37 of 37** do; chart J, `d=16` **13 of 13** do. **2 do not**, and they are the chaining caveat made concrete. Single linkage merges a group whenever *any* two of its members are closer than the threshold, so two devices that the witness predicate calls far apart — at least 0.3 decades apart in *coordinates* — can end up in one basin by being chained through intermediate members that are close to each of them in *profile distance*. The two criteria measure different things and are not required to agree; where they disagree, single linkage is the one that merges, which is why the count is reported as a lower bound and never as an estimate.

**What single linkage means here, and what the count is a bound on.** A cluster is *connected by a chain of steps each shorter than 0.3 decades*, not *all within 0.3 decades of each other*. Chaining can only **merge** clusters, so the count is a **lower bound** on the number of distinct devices at the stated threshold and is reported as one.

**The control the count needs, and what it costs the headline.** Run the same criterion over the same number of *ordinary* prior draws from the same chart — devices that form no witness pair at all — and it returns: chart G, `d=4` **23 of 26**; chart L, `d=16` **67 of 67**; chart J, `d=16` **26 of 26**. Computed at documentation time from the same committed draws, with no oracle calls. Read it before reading the table above.

For **chart L** at `d=16` the control is as high as the measurement, and that is not a coincidence: two independent draws from a log-uniform box spanning two decades in each of sixteen coordinates are almost certain to differ by more than 0.3 decades *somewhere*, so at this threshold in this chart the metric separates almost any two draws and the basin count is close to the member count **by construction**. The chart-L number is therefore weak evidence about the landscape and is not quoted as anything else. The informative object there is the **witness graph**, which is not trivial: its components are not all pairs.

For **chart G** at `d=4` the control is informative, because four coordinates leave far less room to be far apart. The measurement sits *slightly* below it — 20 against 23 of 26 — so the witness members are somewhat more clustered than ordinary draws, and only somewhat. That gap is too small to carry any weight on its own and is reported because a control that flatters the measurement would have been worth even less.

**What survives either reading.** The witness set is not two devices. Chart G's 13 pairs are 13 *disjoint* pairs, and chart L's witness graph has more than two components with some larger than a pair. Whatever the right basin count is, it is not two, and the practical consequence in §7 rests on that and not on the exact number.

### The check on the proxy

Parameter-space clustering is a proxy for the likelihood landscape, so a stated sample of within-cluster and between-cluster pairs was walked in a straight line and the deepest point of the profile likelihood recorded — the same measurement `SPEC-g7-4` made for one pair. The sample rule is index order, which is draw order, fixed by the seed before clustering, so the sample is not chosen by outcome.

| witness set | within-cluster pairs walked | median barrier | between-cluster pairs walked | median barrier |
|---|---|---|---|---|
| chart G, `d=4` | 10 | 630.5 | 10 | 1393.2 |
| chart L, `d=16` | 0 | — | 10 | 1187.9 |
| chart J, `d=16` | 0 | — | 10 | 874.0 |

**What the check actually says, which is not what it was hoping to say.** Only chart G, `d=4` has both arms, because everywhere else every member is its own basin and there are no within-cluster pairs to walk. There, between-cluster barriers are deeper than within-cluster ones — median 1393 against 630 log-units, a factor of 2.2 — so the ordering is the right way round. But **630 log-units is not a shallow barrier**. Devices the profile metric puts in one cluster are still separated by a likelihood barrier hundreds of log-units deep, which means a single-linkage cluster at 0.3 decades is **not** a likelihood basin: it is a set of devices that happen to be close in profile space, several of which the sampler could not travel between either.

That cuts against the count and for the conclusion. The number of *likelihood* basins is larger than the number of profile-distance clusters, not smaller, so the reported counts are a lower bound in a second and stronger sense than the chaining one. And it makes the qualitative answer — the witness set is not two devices — harder to escape rather than easier.

**What this check covers and what it does not.** It is a *global* measurement in each set's own chart — chart G at `d=4`, chart L at `d=16` — walking between two devices rather than differentiating at one. The sample is drawn from the within-cluster and between-cluster pair lists in index order, so where every member is its own basin the within-cluster arm is empty and the contrast cannot be made; that is reported as a dash rather than as a number. The stronger version - walking the witness pairs themselves rather than an index-ordered sample - is what `SPEC-g7-4` did for one pair, and doing it for all of them was outside this generation's budget. It is the obvious next measurement and is recorded as such rather than quietly skipped.

---

## 6. Negative control (mandatory)

Four predicates, each shown to return the **negative** answer on a case constructed to deserve it, end to end through the same code the positive results ran through.

| # | predicate | case | result |
|---|---|---|---|
| 1 | `witness_search`, unmodified | two chart-J devices, identical doping magnitudes, junctions at 0.25 L and 0.75 L — separation 0.954, observational distance 5.3473e-01 against a 2.0e-02 floor | **REJECTED**, 0 witnesses |
| 2 | the chart discriminator of §2 | chart J with `junction_scale = 0`, which pins the junction where charts G and L pin it | junction column norm 0.0e+00, magnitude columns agree with chart G at `d=15` to 0.0e+00 → **NOT DIFFERENT** |
| 3 | `count_basins`, unmodified | three well-separated synthetic blobs, and one blob | 3 and 1 → **PASSES** |
| 4 | `ScharfetterGummel1D.solve` | a bare length-16 doping array on a 301-node grid — exactly what six generations of results were produced by | **RAISED**; the same call with a chart attached still solves: True |

All four behave as required: `True`.

Control 2 is the one that matters most for §2. A discriminator that cannot return *not different* for a chart whose extra coordinate is dead is not measuring anything, and every movement reported in §2 would be an artefact of the comparison rather than a property of the chart.

---

## 7. What may be said, and what may not

### Supported

* **`CHART-01` is closed structurally.** One reconstruction operator, a parameter vector that carries its chart across every API boundary, and an AST guard that fails when a second path appears. The 24 frozen profiles show no published number moved, and the two witness searches reproduce exactly.
* **Charts G and L cannot place a junction.** A chart-J device with its junction at `x_j/L = 0.25` is answered by the best chart-G stand-in with a device whose magnitude is right to a few hundredths of a decade and whose doping type is wrong at 75 of 301 grid nodes. Chart J's reachable set is not a refinement of either older chart's.
* **The junction position is *globally* non-identifiable too.** Chart J at `s = 0` *is* chart G at `d-1` bit for bit, so chart J **contains** chart G rather than sitting beside it and the search below runs inside one family. Chart J at `d=16` yields 13 witness pairs -- **7 of which survive grid refinement**, measured at generation 9; the widest, which does survive, puts the metallurgical junction at 694 nm in one device and 271 nm in the other — 423 nm apart in a 1000 nm device — with an I–V difference below the 2% floor. The free coordinate was chosen because it is a fabrication parameter, and it turns out to be degenerate in the same way the doping magnitudes are.
* **The chart-invariance statement is retired to its measured family.** Within piecewise interpolants over equally spaced anchors in `log10|C|` with a fixed sign convention, the reconstruction operator does not move the *local* spectrum at matched `d`, while `d` does. Chart J moves it by far more, and so does the observation set.
* **At `d = 16`, what you measure dominates how you parameterise.** Spacing the same 16 biases geometrically rather than linearly over the same range moves the leading *local* spectrum 7x more than changing the chart does; narrowing the range to 0.30–0.60 V drops the identifiable count from 4 to 2 in chart G at `d=16`.
* **Rank is a curve.** A bare integer is licensed by a population gap at the cutoff, which holds in `G_d4`, `L_d4` and nowhere else among the six cells measured.
* **The witness set is not two devices.** Chart G's 13 pairs at `d=4` are 13 *disjoint* pairs, and chart L's witness graph at `d=16` has more than two components, some of them larger than a pair. The basin counts themselves are single-linkage lower bounds at a threshold fixed and hashed before clustering, reported as a curve, and — for chart L — against a null control that says the count there is close to trivial. See §5.

### Not supported, and not to be written

* **Any rank fraction compared across charts.** Unchanged, and now three charts rather than two. Neither of the older charts contains the other, and chart J's coordinate count includes one coordinate that is not a doping magnitude at all.
* **Any frequency or probability of degeneracy, in any chart.** Three searches at three budgets are existence proofs. The chart-J search is further apart than the other two: its prior is not the same *kind* of prior, because one coordinate is a position.
* **Any contraction number at the instrument's own 2% noise.** Unchanged and still withheld: the estimator collapses (ESS 1.0). Generation 7 explained why — the posterior is multimodal, not diffuse — which makes more samples the wrong remedy.
* **Any bare integer rank outside the licensed cells**, which now explicitly includes chart J at `d=4`. The licence follows the gap, not the dimension.
* **Any full-spectrum comparison involving chart J without its `junction_scale`.** The spectrum of a mixed-unit Jacobian is not units-free; the same device at the same operating point moves by 5% or by a factor of ten depending on a choice with no canonical answer.
* **Any statement that an identifiable rank is a property of the device.** It is a property of the (device, observation set) pair, and the bias range alone halves it.
* **"The chart does not move the rank"** as an unqualified sentence. It is true within one interpolant family and false outside it.
