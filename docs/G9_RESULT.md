# Generation 9 — the ordering was a property of one operating point

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

**What this generation settles, in one paragraph.** Generation 8 measured four
things that move the local identifiability spectrum — the observation set, the
junction, the dimension, the interpolant — ranked them, and recorded as its own
highest remaining scientific risk that every cell in that ranking sat at **one
operating point**. Generation 9 repeated the whole measurement at **nine further
operating points**, three devices spanning the doping prior crossed with three
bias windows spanning the observation range, under a selection rule hashed
before the first device was drawn. The ranking does not survive. Five different
orderings appear across the nine points; the generation-8 order is reproduced at
**two** of nine under one statistic and at **none** under the other. What does
survive is narrower and more useful: **the observation set moves the spectrum by
92%–108% at every operating point measured, and the relative order of the other
three axes is not a property of this problem at all.** The interpolant — the
axis generation 7 called invariant at 2.8% — moves it by **101%** at one of the
nine.

**Measurement conditions, once, for every number below.** Oracle-arbitrated
throughout: the float32 surrogate is never called (`SPEC-g6-5`, `PH-22`); the
NumPy Scharfetter–Gummel solver in float64 on a 301-node uniform grid decides
every question, except in §4 where refining the grid *is* the question.
Log-uniform **prior** on the magnitude of the doping at each anchor over
`1e21 – 1e23 m^-3`. **Noise model** independent Gaussian in relative terminal
current at a **level** of 2% (`noise_rel = 2.0e-2`). Finite differences in
decades of doping at a **relative step** of 0.05, bias rows below `min_snr =
1e4` against the oracle's own noise floor discarded rather than differenced —
both inherited unchanged from generation 8, because "same metrics, same
normalisation" is a clause of `SPEC-g9-1` and it starts with the estimator. Two
floors, reported separately and never subtracted (`PH-13`, `ADR-0002`): a
**noise floor** of `2.0e-2` and a solver **discretisation floor** of `1.5e-3`;
their maximum, `2.0e-2`, is the distinguishability floor.

Artefacts: `outputs/g9/`, manifest `manifest.json`, machinery commit `a6728fe`
with `dirty = false`. Reproduce with:

```bash
PYTHONPATH=src python scripts/run_g9.py --out outputs/g9 \
  --phases preregister,op_points,rank_obs,junction_refine,basins,negative_control
```

**A note on method, because one piece of it is the best process this loop has
produced.** `tests/test_claim_surface_g0.py::TestParkedPapersInstance` pins the
count of unqualified passages in `papers/draft.md` at one and fails in **both**
directions. `papers/**` is reserved by `R-3`, so the loop cannot apply
`papers/CORRIGENDA_g6.md`; when the operator does, that test fails *by design*,
and the failure is the signal to promote `draft.md` onto the guarded claim
surface and delete the parked-instance test. A trip-wire that breaks when the
thing it guards is fixed, and whose breakage is the instruction, is how a
reserved file stays under measurement without being touched. `SPEC-g9-2`'s prose
guard, `tests/test_claim_surface_g9.py`, is built the same way: it fails when
the surface it guards stops quoting ranks at all, rather than passing silently
over nothing.

---

## 1. Phase A — the bookkeeping the ruling ordered

### 1.1 One lint verdict, by elimination

The generation-8 baseline recorded `"ruff_exit": 0`, carrying neither scope nor
command, and the two defensible scopes disagreed: `ruff check .` exited **1**
with 107 findings, every one of them in `notebooks/`; `ruff check src tests
scripts` exited **0**. One verdict was recorded and two existed.

Annotating that would have preserved it. `pyproject.toml` now grants
`notebooks/*.ipynb` exactly the codes their generator produces, each named with
its reason and `scripts/build_notebooks.py` named as the generator. **Both
invocations now exit 0 over the tracked tree.**

The block is not a blanket amnesty and `tests/test_lint_scope_g9.py` proves it
in four directions: the two scopes agree; a planted undefined name in a notebook
cell still fails; the generator's own cell layout is quiet; and the findings
that are real untidiness rather than layout — one unused re-export, one
`f"…%.1e…" % x`, one unused loop counter, all in the generator's source strings
— are pinned **exactly**, so repairing the generator fails that test by design.
A fifth test checks the scopes do not agree by exclusion: `ruff check .` is
shown to still reach `notebooks/`.

Regenerating to fix those three was considered and rejected: the notebooks ship
executed outputs (`NB-01`), the generator emits clean cells, and running it
discards 3,097 lines of stored output. Three lint findings are not worth
deleting the evidence that the notebooks ran.

### 1.2 `REP-01` applied forward, and what it caught in its own author

Every entry in `LOOP_STATE_v6.json`'s `baselines` block is now an object
carrying the **command** that produced it. `tests/test_loop_state_g9.py`
re-runs the rerunnable ones and compares.

Applying it caught the field the ruling held up as the good example.
`"mypy_findings": 25` came with the note *"25 over the tracked tree"*. That
scope is wrong: **25** is `mypy src`, **44** files. Over the tracked tree —
`mypy src tests scripts`, **112** files — it is **150**. The number was right
and the sentence describing it was not, which is a slightly worse failure than
`ruff_exit`'s missing scope, because a wrong description reads as authoritative
while a missing one at least announces itself. It is the whole argument for
recording a command rather than a characterisation: a command can be re-run, a
description can only be re-read.

### 1.3 The suite's wall clock, re-measured rather than annotated

The generation-8 report compared 378.11 s against a declared band while
spot-check scripts shared the cores. Re-run on a quiet machine at the machinery
commit: **169.00 / 163.80 / 171.43 s**, 709 collected, 706 passed, 3 skipped, 0
failed. That sits inside generation 7's 171–181 s band. The generation-8 figures
of 370–374 s were the load, not the suite, and are superseded by measurement
rather than by a note.

### 1.4 `CI-01` — `ACCEPTED-PERMANENT`, and what it costs

The generation-8 decision — remote or no remote — went unanswered for three
cycles and outlived its own deadline, so the stated default fires.

> **Cost statement.** No claim in this repository has ever been evidenced on any
> interpreter other than CPython 3.11, or on any operating system other than the
> `win32` host it was developed on. The declared support floor rests on **static
> analysis of 110 files** by `scripts/check_python_support_floor.py`, which can
> only falsify a floor and never confirm one, and which cannot see dependency
> resolution at all — the single thing a clean-install leg exists to test. The
> `.github/workflows/ci.yml` matrix has never executed, on any leg, in nine
> generations. Concretely: `numpy>=1.22`, `scipy>=1.10`, `torch>=2.0`,
> `matplotlib>=3.7`, `PyYAML>=6.0` and `tqdm>=4.65` name lower bounds that have
> never been resolved together by a package manager, and the wheel this project
> builds has never been installed anywhere except the machine that built it.

**The cost has grown since the finding was assigned.** The support-floor scan
covered **96** files at generation 7 and covers **110** now. A larger clean scan
is a larger *unevidenced* surface, not a stronger claim, so `cost_grown_since_assignment`
is recorded as `true` and `pyproject.toml`'s comment now carries 110 with the 96
beside it. If a remote is added the status reverts and this statement is
superseded forward, not deleted.

---

## 2. `SPEC-g9-1` — the ordering at nine further operating points

### 2.1 The rule, written down before it was applied

`AH-14` is not satisfied by intending to be fair. `outputs/g9/preregister.json`
was written before the first draw and carries three SHA-256 hashes; every later
phase recomputes them and refuses to run on a mismatch.

| object | hash | what it fixes |
|---|---|---|
| `operating_point_rule` | `f4d51bc566b86f48…` | how the devices and windows are chosen |
| `ordering_statistic` | `1c69e254d4b12b18…` | what "the ordering" means, and which perturbation belongs to which axis |
| `barrier_criterion` | `9631b4711f99a631…` | §5's cluster criterion |

**The device axis.** 400 candidates drawn from the study's own log-uniform
doping prior in chart G at `d = 4`, under seed 9 rather than the study seed, so
these are new devices and not the generation-6 draws re-served. Candidates are
ranked by mean `log10|C|` and the draws nearest the 10th, 50th and 90th
percentiles are taken. A candidate is admitted only if the oracle certifies
every bias in the widest window and only if it is at least 0.3 decades — the
study's own `min_separation_decades` — from the generation-8 operating point in
profile space. Otherwise the next candidate in rank order is taken and the
substitution is recorded.

**The bias axis.** Three windows over the range the oracle's discretisation
error was measured to converge on: the published `0.15–0.90 V`, its lower part
`0.15–0.50 V`, its upper part `0.50–0.90 V`. Every operating point is a
`(device, window)` pair, because generation 8's own conclusion is that an
identifiable rank belongs to that pair and never to the device alone.

**What the rule produced**, with zero substitutions and zero rejections:

| device | percentile | mean `log10|C|` | decades from the g8 operating point |
|---|---|---|---|
| `device_p10` | 10 | 21.632 | **1.218** |
| `device_p50` | 50 | 22.021 | **0.640** |
| `device_p90` | 90 | 22.349 | **1.413** |

These are genuinely distinct devices, not projections of the *global*
generation-6 witness pair 0 member a (**chart G**, `d = 4`): the nearest sits
0.64 decades away in profile space, twice the study's own separation criterion.

### 2.2 What "the ordering" means, since it did not previously mean anything

The generation-8 state file summarises four families of movement as
`observation set > junction > dimension > interpolant`. That summary has no
statistic attached, and the two obvious ones **disagree on generation 8's own
numbers**. So both are computed at every point:

* **`by_max`** — the largest movement each axis produces over its pre-registered
  perturbation set;
* **`by_mildest`** — the smallest, i.e. the mildest perturbation that axis
  admits.

The ordering is called **stable** at a point only when both agree there. At the
generation-8 operating point they do not:

| statistic | order at the generation-8 operating point |
|---|---|
| `by_max` | **junction** (219%) > observation set (98.4%) > dimension (5.0%) > interpolant (2.8%) |
| `by_mildest` | **observation set** (19.8%) > junction (9.1%) > dimension (5.0%) > interpolant (2.8%) |

The published summary picks neither and says which nowhere.

### 2.3 The reproduction control

Before anything new is claimed, the generation-8 operating point is re-measured
through this generation's code. Every number reproduces:

| contrast | generation 8 | generation 9 |
|---|---|---|
| interpolant, chart G → chart L at `d = 16` | 2.8% | **2.76%** |
| dimension, chart G `d = 15` → `d = 16` | 5.0% | **5.01%** |
| junction to `x_j/L = 0.35`, magnitude block | 219% | **219.2%** |
| junction to `x_j/L = 0.65`, magnitude block | 9.1% | **9.13%** |
| observation set, geometric spacing, same window | 19.8% | **19.80%** |

So what follows is one ruler applied to more points, not a second ruler.

### 2.4 The ordering, at every point measured

`by_max` per axis. The generation-8 point is the control row and is not one of
the nine.

| operating point | observation set | junction | dimension | interpolant | `by_max` order |
|---|---|---|---|---|---|
| **g8 control**, wide | 0.984 | **2.192** | 0.050 | 0.028 | jun > obs > dim > int |
| **g8 control**, low | 0.987 | **2.297** | 0.558 | 0.307 | jun > obs > dim > int |
| **g8 control**, high | 0.925 | **2.079** | 0.030 | 0.026 | jun > obs > dim > int |
| `device_p10`, wide | **0.987** | 0.384 | 0.037 | 0.032 | obs > jun > dim > int |
| `device_p10`, low | **0.944** | 0.413 | 0.030 | 0.062 | obs > jun > int > dim |
| `device_p10`, high | **0.925** | 0.173 | 0.039 | 0.041 | obs > jun > int > dim |
| `device_p50`, wide | **0.988** | 0.426 | 0.026 | 0.077 | obs > jun > int > dim |
| `device_p50`, low | **1.080** | 0.469 | 0.543 | **1.015** | obs > int > dim > jun |
| `device_p50`, high | **0.978** | 0.371 | 0.029 | 0.153 | obs > jun > int > dim |
| `device_p90`, wide | 0.998 | **2.786** | 0.158 | 0.074 | jun > obs > dim > int |
| `device_p90`, low | 1.000 | **4.560** | 0.266 | 0.220 | jun > obs > dim > int |
| `device_p90`, high | 0.989 | **1.259** | 0.033 | 0.051 | jun > obs > int > dim |

**Five distinct orderings under `by_max`, four under `by_mildest`.** Of the nine
further points, **2 of 9** reproduce the generation-8 `by_max` order and **0 of
9** reproduce its `by_mildest` order. The two statistics agree at only 2 of the
12 points measured.

**`SPEC-g9-1`'s falsifier fires under both statistics.** This outcome was
pre-registered as reportable (`AH-04`, `AH-13`), and the headline converts to
the weaker form the clause names: **the ordering is itself operating-point
dependent.**

### 2.5 What survives, which is not nothing

Read the columns rather than the rows.

* **The observation set is the only axis that is large everywhere.** Its `by_max`
  spans **0.925 – 1.080** across all twelve points — a factor of 1.17 from end to
  end. Every other axis swings by more than an order of magnitude: junction
  0.173 – 4.560 (×26), dimension 0.026 – 0.558 (×21), interpolant 0.026 – 1.015
  (×39).
* **So the ordering is not four-way. It is one-against-three.** *What you measure
  dominates the local spectrum at every operating point tested; how you
  parameterise, at what dimension, and where the junction sits trade places among
  themselves depending on the device and the window.* That is a claim the nine
  points support and the one point could not have.
* **The chart-invariance statement does not survive a change of operating point
  either.** The interpolant contrast — chart G against chart L at matched `d`,
  the same comparison generation 7 published as agreeing to 3% — measures
  **2.6%** at its best and **101.5%** at `device_p50` in the `0.15–0.50 V`
  window. At the *same device* as generation 8's, merely narrowing the window
  takes it from 2.8% to **30.7%**. "The charts agree at matched `d`" is a
  statement about one `(device, window)` cell.

### 2.6 The denominator the invariance result was missing — measured, and it is not 44%

The ruling asked that the observable-space distance between the two compared
chart cells be promoted into the same table as the 2.8%, on the strength of a
figure of **44%** (`1.790241e-04` against `2.576097e-04`) reported during
verification.

**That figure could not be re-derived, and the number that replaces it points the
other way.** Its invocation was never recorded — the exact defect §3 of the
ruling is about — and no construction found here reproduces those digits. What
*is* measurable, on exactly the two cells whose spectra are compared, over
exactly the window they are compared in, is now in the artefact at every
operating point:

| operating point | profile distance, chart G to chart L | **distance in the observable** | spectral movement |
|---|---|---|---|
| g8 control, wide | 1.233 decades (least squares in `log10|C|`) | **0.82%** | 2.76% |
| g8 control, high | 1.233 decades | **0.70%** | 2.56% |
| `device_p10`, wide | 1.239 decades | **1.37%** | 3.16% |
| `device_p50`, wide | 1.288 decades | **2.67%** | 7.66% |
| `device_p90`, wide | 1.277 decades | **2.53%** | 7.44% |

`REP-01`: every profile distance in that column is the residual left by
least-squares projection in `log10|C|`, the best of the two admissible
projections, and the method travels in the same artefact record as the value.

So the two charts are **more than 1.2 decades apart in profile space and at most
2.7% apart in the observable**, at every operating point measured. The
invariance result is therefore *less* surprising than it looked, not more: the
two cells' spectra agree because the two devices are very nearly the same device
*as seen through this instrument in this window*, and the observable is what the
Jacobian differentiates. That is the same finding as §2.5's, arrived at from the
other side — it is the observation set that decides.

The nearest constructions that do reach ≈43% are same-coordinate-vector
comparisons at `d = 4` **below** the published bias window, around 0.01–0.08 V.
Those are not the cells whose spectra agree to 2.8%, and quoting the two
together would compare different objects.

### 2.7 Chart J contains chart G, at every point

`ChartJ(16)` at `s = 0` reproduces `ChartG(15)` bit for bit, and the magnitude
columns of its Jacobian are bit-identical to chart G's at `d = 15`. Generation 8
established that at one operating point; it is asserted here at **all twelve**,
and holds at all twelve.

That is what makes §2.4's junction column interpretable: the 17%–456% movements
are measured **within one family**, between a chart and the chart it contains,
not across two incomparable parameterisations. Wherever the junction result
appears, that containment appears with it.

---

## 3. `SPEC-g9-2` — `rank(observation set)`, as a curve

`SPEC-11` made a rank carry its **cutoff**. It does not yet carry its
**window**, and generation 8 showed the window halving it. So the rank is
measured against the observation set the way it is measured against the cutoff:
as a curve.

Two axes, at two fixed devices — the generation-8 operating point, because that
is where every published rank sits, and the median-doping device, because that
is where the selection rule puts the centre of the prior. Which two, and why, is
stated rather than chosen by outcome.

**Width.** The window is widened about a fixed centre of 0.525 V, 16 linear bias
points throughout, so width is the only thing that moves.

| window width | window | rows used | rank at a 2% cutoff | largest gap | cutoff in the gap? |
|---|---|---|---|---|---|
| 0.10 V | 0.475–0.575 | 16 | **1** | ×230.6 | **yes** |
| 0.15 V | 0.450–0.600 | 16 | **1** | ×171.3 | **yes** |
| 0.20 V | 0.425–0.625 | 16 | 2 | ×141.7 | no |
| 0.30 V | 0.375–0.675 | 16 | 3 | ×44.3 | no |
| 0.40 V | 0.325–0.725 | 16 | 4 | ×19.6 | no |
| 0.50 V | 0.275–0.775 | 16 | 4 | ×11.2 | no |
| 0.60 V | 0.225–0.825 | 16 | 4 | ×7.5 | no |
| 0.70 V | 0.175–0.875 | 15 | 4 | ×5.4 | no |
| 0.75 V | 0.150–0.900 | 15 | 4 | ×5.0 | no |

Chart G at `d = 16`, generation-8 device. At `device_p50` the same sweep runs
2, 2, 2, 3, 4, 4, 4, 4, 4.

**Spacing.** One window, `0.15–0.90 V`, 16 bias points, spacing interpolated
continuously from linear (`α = 0`) to geometric (`α = 1`) — a two-valued knob
cannot produce a curve, so this is the one-parameter family joining them.

| `α` | 0 | 0.125 | 0.25 | 0.375 | 0.5 | 0.625 | 0.75 | 0.875 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| rank at a 2% cutoff, 16 biases over 0.15–0.90 V | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |

**Three things follow.**

1. **The rank is a function of window width, and not of spacing.** Width takes it
   from 1 to 4 at the generation-8 device; spacing does not move it at all,
   across the entire family — even though generation 8 measured the same spacing
   change moving the *spectrum* by 19.8%. Moving the spectrum and moving the rank
   are different things, and this is the first measurement in the repository that
   separates them.
2. **The published count is the plateau, reached only at width ≥ 0.40 V.** Every
   rank this repository quotes sits at 0.75 V, on the flat part of a curve whose
   other end is 1.
3. **A bare integer becomes licensed at `d = 16` in a narrow window.** At 0.10 V
   and 0.15 V the operational cutoff falls inside a gap of ×230.6 and ×171.3 —
   an enormous population separation — so `rank(cutoff)`'s own criterion licenses
   a bare integer there. Generation 8 concluded the licence was `G_d4` and `L_d4`
   and that "the licence follows the gap, not the dimension". That is right, and
   it cuts further than generation 8 saw: the licence follows the gap, and the
   gap is a property of the `(chart, d, device, window)` cell. Section 2.4's
   twelve points make the same point from the other direction — chart G at `d = 4`
   is in-gap at only 4 of them, and chart J at `d = 16` is in-gap at one.

`SPEC-g9-2`'s falsifier is about prose, and is enforced on prose:
`tests/test_claim_surface_g9.py` fails when a rank fraction appears in a passage
that does not say what was measured, or when a document quoting a rank never
points at a rank curve. It found live instances across six claim-surface
documents on its first run; each now carries its observation set.

---

## 4. `SPEC-g9-3` — the chart-J witnesses through the refinement falsifier

The doping witnesses faced this battery at generation 6 and survived it: re-solve
both members at `N = 301 → 601 → 1201` and at `tol_carrier = 1e-12`, and ask
whether the observational distance stays below the floor or grows through it.
The chart-J witnesses — the junction result, published at generation 8 — had
never faced it. All thirteen pairs, six configurations each:

| pair | junctions apart | `N=301`, default | `N=1201`, tight | change | survives |
|---|---|---|---|---|---|
| 0 | 26.6 nm | 1.5166e-02 | 1.4039e-02 | −7.4% | **yes** |
| 1 | 41.7 nm | 1.5714e-02 | 1.4440e-02 | −8.1% | **yes** |
| 2 | 178.4 nm | 1.6144e-02 | 1.6380e-02 | +1.5% | **yes** |
| **3** | **422.9 nm** | **1.7551e-02** | **1.7247e-02** | **−1.7%** | **yes** |
| 4 | 63.2 nm | 1.7619e-02 | 1.7471e-02 | −0.8% | **yes** |
| 5 | 249.5 nm | 1.7874e-02 | 1.8725e-02 | +4.8% | **yes** |
| 6 | 177.1 nm | 1.8436e-02 | 1.9469e-02 | +5.6% | **yes** |
| 7 | 412.2 nm | 1.8733e-02 | 1.9307e-02 | +3.1% | no |
| 8 | 0.4 nm | 1.8785e-02 | 5.5498e-02 | **+195.4%** | no |
| 9 | 9.0 nm | 1.9120e-02 | 2.4631e-02 | +28.8% | no |
| 10 | 3.4 nm | 1.9544e-02 | 2.1090e-02 | +7.9% | no |
| 11 | 196.2 nm | 1.9615e-02 | 1.9843e-02 | +1.2% | no |
| 12 | 246.2 nm | 1.9705e-02 | 2.0204e-02 | +2.5% | no |

**The falsifier fires. Six of thirteen pairs separate above the 2.0e-02 floor
under refinement, so the count of thirteen is a property of the 301-node grid
and not of the device family.**

**The headline pair survives.** Pair 3 is the one the claim surface quotes —
junctions at 694 nm and 271 nm, 423 nm apart in a 1000 nm device — and its
distance *falls* 1.7% under refinement, staying below the floor at all six
configurations. The result *the junction position is globally non-identifiable*
stands. The result *there are thirteen such pairs* does not.

**The pattern is legible and worth stating.** The pairs that separate are
concentrated among those whose junctions were nearly coincident to begin with —
0.4 nm, 3.4 nm and 9.0 nm apart, which are the three largest rises in the table
— and pair 8, whose junctions differ by less than a grid spacing at `N = 301`,
separates by 195%. Those pairs were never junction degeneracies; they were pairs
whose *magnitudes* compensated, resolved at a resolution too coarse to tell.
Refinement removes them and leaves the pairs whose junctions genuinely differ,
which is the falsifier doing exactly what it is for.

Chart J had to be rebuilt at each grid, because a junction lands at a physical
position and which nodes straddle it is a function of `N`. That is the mechanism
by which a coarse grid can manufacture a degeneracy, and it is why this battery
was the right one to run.

---

## 5. `SPEC-g9-4` — basins by barrier depth, with the null control the clause requires

Generation 8 clustered witness members by **profile distance** and said in the
same breath that the proxy was not the landscape. This replaces the proxy with
the thing itself: two members are in one basin when the profile likelihood along
the straight line between them does not fall by more than a threshold, and the
threshold is stated in units of the **floor barrier** — the log-likelihood cost
of a curve sitting exactly one noise unit away at every certified bias, which is
`0.5 × B = 8.0` log-units here. That is the only non-arbitrary reference
available, and the criterion was hashed (`9631b4711f99a631…`) before the first
barrier was computed.

The clause made this pilot-gated and forbade part-running it. The pilot measured
3.52 s per path against 52 paths — 183 s against a 900 s budget — so it ran
whole.

| set | witness-pair barrier depth | null-control barrier depth | pairs at or below the floor | basins at the floor |
|---|---|---|---|---|
| chart G, `d = 4` | min **0.68**, median **8.31**, max 2239 | min **339**, median **9379** | **6 of 13** | 20 of 26 members |
| chart J, `d = 16` | min **16.1**, median **468**, max 9397 | min **1332**, median **9479** | **0 of 13** | 26 of 26 members |

**The null control is what makes this readable, and it passes cleanly.** The same
criterion over the same number of ordinary prior draws that form no witness pair
returns barriers with a *minimum* of 339 log-units in chart G — forty-two times
the floor — against a witness-pair *median* of 8.3. Generation 8's basin count in
chart L was close to trivial against its null control and was reported as such;
this one is not: the separation between witness pairs and ordinary pairs is
three orders of magnitude in the median.

**And the two charts are telling different stories, which the profile metric
could not see.**

* *Globally*, in **chart G at `d = 4`**, the median witness pair is separated by
  a barrier of 8.31 log-units against a floor barrier of 8.0 — the likelihood between the two
  members is essentially flat at the instrument's own resolution, and six of the
  thirteen pairs sit at or below the floor. Those are not two isolated maxima;
  they are a **ridge the instrument cannot resolve**, which is a stronger form of
  non-identifiability than a witness pair alone establishes.
* In **chart J at `d = 16`**, no witness pair is within the floor barrier and the
  median is 468 log-units, fifty-nine times the floor. Those pairs *are* two
  distinct basins that happen to produce indistinguishable terminal current.

Both are global non-identifiability. They are different shapes of it, and one
generation of profile-distance clustering could not have distinguished them.

**One correction to generation 8's own reading.** Its §5 reported within-cluster
barriers of median 630 log-units and concluded that a single-linkage cluster at
0.3 decades is not a likelihood basin. That is right about the *clusters*, but it
was measured on an index-ordered sample of arbitrary pairs, not on the witness
pairs. Measured on the witness pairs themselves, chart G's are at the floor. The
generation-8 sentence *"the number of likelihood basins is larger than the number
of profile-distance clusters"* holds for chart J and is the wrong way round for
chart G's witness pairs.

---

## 6. Negative control (mandatory)

The clause names the case: *an ordering measured at one operating point, stated
unqualified. The battery rejects it on `SPEC-g9-1`.*

| # | predicate | case | result |
|---|---|---|---|
| 1 | `ordering_is_supported_as_general`, the same predicate that judges §2 | exactly the generation-8 evidence — the four-way ordering at the *global* witness pair 0 member a of **chart G**, `d = 4`, over 16 biases spanning 0.15–0.90 V — offered as a general claim | **REJECTED**: *an ordering measured at one operating point is a measurement of that point; generality is a claim about the others, and none were measured* |
| 2 | the same predicate, run the other way | three synthetic points carrying one order under both statistics | **ACCEPTED** — a predicate that only ever rejects is not a predicate |
| 3 | the §4 refinement battery | two chart-J devices with identical doping magnitudes and junctions at 0.25 L and 0.75 L | **ABOVE THE FLOOR at every refinement** — the battery can separate a pair, so §4's survivals mean something |
| 4 | the §2 chart discriminator | chart J with `junction_scale = 0`, which pins the junction where charts G and L pin it | **NOT DIFFERENT** — junction column norm 0, magnitude columns identical |

All four behave as required: `True`.

Control 1 is the one that matters. The predicate that rejects the
one-operating-point claim is the *same function* that certifies or refuses the
nine-point result, so it cannot have been tuned to pass the answer this
generation wanted — and in fact it refuses that answer too, on the second clause
rather than the first: the ordering is not the same at every point measured.

---

## 7. What may be said, and what may not

### Supported

* **The ordering is operating-point dependent.** Five distinct orderings of
  `{observation set, junction, dimension, interpolant}` appear across nine
  further operating points under the larger-movement statistic, four under the
  milder one. The generation-8 order is reproduced at 2 of 9 and at 0 of 9
  respectively.
* **The observation set dominates the local spectrum everywhere tested.** Its
  largest movement spans 0.925 – 1.080 across all twelve operating points, while
  each of the other three axes swings by more than a factor of twenty. *What you
  measure* is the robust statement; the ranking of the other three is not.
* **Chart-invariance is a property of a cell, not of the charts.** The chart G to
  chart L movement at matched `d` is 2.6% at its best and 101.5% at
  `device_p50` in the `0.15–0.50 V` window; at the generation-8 device alone,
  narrowing the window takes it from 2.8% to 30.7%.
* **The two charts are far apart in profile space and close in the observable.**
  More than 1.2 decades apart in `log10|C|` by least-squares projection, and at
  most 2.7% apart in terminal current over the window their spectra are compared
  in, at every operating point measured.
* **Chart J contains chart G**, bit for bit, at all twelve operating points, so
  every junction movement is measured within one family.
* **A local rank is a curve in the observation set as well as in the cutoff.** At
  the generation-8 device in chart G at `d = 16`, the identifiable count at a 2%
  cutoff runs from 1 to 4 as the bias window widens from 0.10 V to 0.75 V about a
  fixed centre, and does not move at all as spacing runs from linear to
  geometric over a fixed window.
* **The junction position is globally non-identifiable** (chart J, `d = 16`,
  0.15–0.90 V, 16 biases): the 694 nm / 271 nm pair survives refinement to
  `N = 1201` and `tol_carrier = 1e-12`, its observational distance falling 1.7%.
* **Six of the thirteen chart-J witness pairs do not survive that refinement**, so
  the count of thirteen was a property of the 301-node grid.
* **The chart-G witness pairs are a ridge, not two points.** Their median
  likelihood barrier is 8.31 log-units against a floor barrier of 8.0, with six
  of thirteen at or below it, against a null control whose minimum is 339.

### Not supported, and not to be written

* **Any ordering of the four sensitivities as a general claim.** Withdrawn by
  measurement, not qualified. Only *the observation set dominates* survives, and
  only over the devices and windows in `outputs/g9/op_points.json`.
* **"The chart does not move the spectrum at matched `d`"**, with or without the
  interpolant-family qualifier generation 8 added. It moves it by 101% at one of
  the nine points.
* **Thirteen chart-J witness pairs.** Seven survive refinement; the number
  thirteen may not be quoted without the refinement result beside it.
* **Any rank fraction compared across charts.** Unchanged, and now further
  weakened: the rank moves with the device *and* the window within a single
  chart.
* **Any bare integer rank whose cell has no measured population gap.** Unchanged,
  and the licensed set is now a property of the `(chart, d, device, window)` cell
  rather than of `(chart, d)`.
* **Any frequency or probability of degeneracy in any chart.** Unchanged.
* **Any contraction number at the instrument's own 2% noise.** Unchanged.
* **Any full-spectrum comparison involving chart J without stating
  `junction_scale`.** Unchanged.
* **44% as the observable-space distance between the two compared chart cells.**
  It could not be re-derived and the measured value is at most 2.7%.
* **Any statement that an identifiable rank is a property of the device.** It is
  a property of the `(device, observation set)` pair, and §3 measures the
  observation-set half as a curve.

---

## 8. Ruling premises corrected

Recorded in the same voice generation 8 used for the same purpose: a ruling that
arrives before the measurement is entitled to be wrong about it.

1. **§2's "devices 44% apart in the observable" is not measurable here.** The
   figure carried no invocation and could not be reproduced; on the two cells
   whose spectra are compared it is 0.82% at the generation-8 operating point and
   at most 2.67% anywhere. The inference built on it — that the invariance result
   is *stronger* than it looked — inverts: the spectra agree because the two
   devices are nearly indistinguishable through this instrument in this window.
2. **§3's "`mypy_findings: 25` carries scope and method" is half right.** It
   carries a *stated* scope, and the stated scope is wrong: 25 is `mypy src` over
   44 files, not the tracked tree, which gives 150 over 112.
3. **§4's "static analysis of 96 files" is out of date.** The scan covers 110
   files at this generation. The direction matters — the unevidenced surface has
   grown 15% since the finding was assigned — so the cost statement carries 110
   and records the growth.
4. **The generation-8 ordering summary is under-specified, not merely
   unreplicated.** Its two natural statistics disagree at its own operating
   point. This is prior to the replication question and would have been true had
   `SPEC-g9-1` never run.
5. **Generation 8's "the number of likelihood basins is larger than the number of
   profile-distance clusters" is the wrong way round for chart G's witness
   pairs**, which sit at the floor barrier. It holds for chart J.

---

## 9. What generation 9 did not do

* **`SPEC-g9-1` did not hold, so the ruling's "if g9-1 holds, stop" does not
  apply.** No new scope was opened anyway: no fourth chart, no `S-5`, no `S-2`.
  The falsification is reported and the headline is narrowed to what nine points
  support.
* **`rank(observation set)` was measured at two devices, not four.** Which two,
  and why, is stated in §3. The other two are in `outputs/g9/op_points.json` at
  three windows each and their ranks appear in §2's cells.
* **The barrier metric covers the witness pairs and an equal-sized null control,
  not every pair among the members.** That is what the clause asked for and what
  the pilot admitted; walking every pair remains unmeasured.
* **`papers/CORRIGENDA_g6.md` and preservation are unchanged and are the
  operator's.** `R-3` reserves `papers/**`; `TestParkedPapersInstance` still pins
  the count at one and still fails in both directions.
