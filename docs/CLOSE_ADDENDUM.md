# Close addendum — `WIT-02` satisfied for chart G, and the ridge measured on all thirteen

**Status** the closing ruling of 2026-08-26 ended the technical work. This is the
one bounded refinement the operator ruling of **2026-08-28 §2** authorised
afterwards, and it is authorised narrowly:

> Authorised, narrowly: refine chart G's remaining ten pairs, recompute
> barriers, update the register. No new witnesses, no new charts, no new
> windows, no chart L.

It exists because `WIT-02` — the operator's own rule, enacted at close — opened a
gap under the one claim the closing ruling declared safe. After this, the
technical work ends for good. There is no generation 11 and this is not one: no
new scientific scope is opened, one pre-existing rule is brought into compliance
on one set, and the claim it carries is remeasured under the criterion that
already existed.

**Measurement conditions, once, for every number below.** Oracle-arbitrated,
301-node production grid. **Prior** log-uniform on `|doping|` over 1e21–1e23 m⁻³
per anchor, hash `ba11a6d5357388cb…`, unchanged since generation 6. **Noise
model** relative, i.i.d., at a **noise level of 2%** (`noise_rel = 0.02`), which
is also the **distinguishability floor** — two devices closer than `2.0e-02` in
the observable are the same device to this instrument. **Observation set** 16
bias points over 0.15–0.90 V. **Discretisation floor** `1.5e-3` relative
(`ADR-0002`). Every witness count below is admissible under `WIT-01` at an
admissibility ratio of 1.000 and carries its `WIT-02` refinement coverage.

Artefacts: `outputs/wit02_chartG/{preregister,refine,recount}.json`,
`outputs/close/wit02_register_v2.json`, manifest
`outputs/wit02_chartG/manifest.json`. Script `scripts/run_wit02_chartG.py`.

---

## 1. Why chart G, when chart L is the uncovered set

The close register assigned `WIT-02`'s exposure to chart L, which is at 0 of 37
refined and carries the dimension reading. The ruling reassigns it on the
margins, and the reassignment is arithmetic rather than judgement:

| set | refined at close | median barrier | margin against the floor barrier |
|---|---|---|---|
| **chart L**, `d = 16` | 0 of 37 | 1696 log-units | **212 floor units** |
| **chart G**, `d = 4` | 3 of 13 | 8.31 log-units | **+3.9%** |
| **chart J**, `d = 16` | 13 of 13 | 468 log-units | 59 floor units |

A basin at 212 floor units does not become a ridge because some of its members
separate under refinement — the classification survives losing members, and
losing members can only *raise* the surviving median or leave it alone in the
direction that matters. The ridge is the claim that lives **at** the floor, which
is exactly where generation 9 measured refinement to bite, and it stood on
**3 of 13** pairs at a **3.9%** margin. So the exposed claim was the ridge, and
the ten untested pairs were under it.

---

## 2. The refinement — 12 of 13 survive; one separates

Generation 6's battery, imported rather than restated (`run_g9.REFINEMENT_GRIDS`
and `run_g9.REFINEMENT_TOLS`): `N = 301 → 601 → 1201` crossed with the default
tolerance and `tol_carrier = 1e-12, max_outer = 200`. A pair **survives** iff its
observational distance stays below the distinguishability floor at **all six**
rows. All thirteen chart-G witness pairs were run; the three generation 6 had
already done are a reproduction control and the other ten are the measurement.

Globally, in **chart G** at **d = 4**, of **13 of 13** witness pairs refined,
**12 survive** and **1 separates**:

| pair | distance at `N=301` | % of floor | distance at `N=1201` tight | change | survives |
|---|---|---|---|---|---|
| 0 ‡ | 1.2255e−02 | 61.3% | 8.6089e−03 | −29.8% | yes |
| 1 ‡ | 1.3788e−02 | 68.9% | 1.3442e−02 | −2.5% | yes |
| 2 ‡ | 1.4224e−02 | 71.1% | 1.4521e−02 | +2.1% | yes |
| 3 | 1.4927e−02 | 74.6% | 1.8178e−02 | +21.8% | yes |
| 4 | 1.5320e−02 | 76.6% | 1.5251e−02 | −0.4% | yes |
| 5 | 1.6534e−02 | 82.7% | 1.6497e−02 | −0.2% | yes |
| 6 | 1.7529e−02 | 87.6% | 1.7515e−02 | −0.1% | yes |
| 7 | 1.8451e−02 | 92.3% | 1.8246e−02 | −1.1% | yes |
| 8 | 1.8681e−02 | 93.4% | 1.9379e−02 | +3.7% | yes |
| 9 | 1.8861e−02 | 94.3% | 1.8322e−02 | −2.9% | yes |
| 10 | 1.9536e−02 | 97.7% | 1.9812e−02 | +1.4% | yes |
| 11 | 1.9543e−02 | 97.7% | 1.9274e−02 | −1.4% | yes |
| **12** | 1.9779e−02 | 98.9% | **2.1932e−02** | **+10.9%** | **no** |

Pair 12's distance crosses the floor at the finest grid: it was a solver artefact
and is withdrawn from the witness set. Twelve remain.

### 2.1 Controls

| | control | result |
|---|---|---|
| `R1` | the three pairs generation 6 refined, re-run here through generation 9's code path | **PASS** — bit-identical `N=301` distances, 3 of 3, and both survival verdicts agree. Two code paths, one measurement, so the ten new pairs and the three old ones are commensurate |
| `N1` | globally, in **chart G** at **d = 4**, a **null-control** pair — consecutive ordinary prior draws that form no witness pair — through the same battery | **PASS** — distance `9.777e−01` against a floor of `2.0e−02`, 0 of 6 rows below the floor. A battery that cannot separate two distinguishable devices could not evidence that a witness pair is inseparable |
| `D1` | determinism | **PASS** — the whole pipeline was run twice, once phase by phase and once in a single invocation; `refine.json`, `recount.json` and the register are identical apart from wall-clock fields |

`N1` was pre-registered with its failure mode: had the null pair come out *below*
the floor, it was to be reported as a witness the generation-6 search missed and
**not** swapped for another pair. Re-picking until a control behaves is the
tuning `PH-11` forbids.

### 2.2 A free finding — the ordering transfers, the threshold does not

Generation 10 found that survival on **chart J** at `d = 16` was predicted exactly
by **headroom against the floor**: the 7 of 13 survivors were the 7 smallest
distances at `N=301` (max `0.01844`) and the 6 that separated were the 6 largest
(min `0.01873`). That reading was measured on one set and is not what this run was
authorised to establish. It reproduces here, on a different chart at a different
dimension: globally, in **chart G** at **d = 4**, the 12 of 13 survivors are the 12
smallest distances (max `0.019543`, 97.7% of the floor) and the single pair that
separates is the largest (`0.019779`, 98.9%). Perfectly ordered again, with no
geometry in it.

**The boundary moved, and that is the useful half.** Chart J's split sits between
92.2% and 93.65% of the floor; chart G's sits between 97.7% and 98.9%. The
*ordering* by headroom transfers across two charts and two dimensions; the
*location* of the split does not. A margin band calibrated on chart J's numbers
would have been a threshold fitted to one set, which is the arithmetic reason
`WIT-02` declined a band and refined everything instead — now measured on two sets
rather than argued from one.

---

## 3. The recount — the ridge stands, and the margin moves the safe way

The refinement decides **which pairs are counted**, and nothing else. The barrier
criterion is generation 9's, imported with its hash checked against
`outputs/g9/preregister.json` and `outputs/g10/preregister.json`; the classifier is
generation 10's `RidgeBasinDecision`, unchanged, `ridge_fraction = 1/3`; the grid
is the production `N = 301` every committed barrier was measured on. Recomputing
barriers on the *refined* grid would have replaced `SPEC-g10-2`'s measurement with
a different one and then compared it against two sets that were never measured that
way; the pre-registration forbids it by name.

**Reproduction control.** All thirteen pairs were re-measured first through
`run_g10._barrier_set` — the same function that produced
`outputs/g10/ridge_basin.json` — and every per-pair depth reproduces generation
10's **bit-identically**, median `8.314616217138337` against
`8.314616217138337`. The counted subset's depths are then identical to the full
run's for the same pairs, 12 of 12.

Globally, in **chart G** at **d = 4**, over the **12 of 13** pairs that survive
refinement:

| | generation 10, 13 pairs, 3 of 13 refined | here, 12 pairs, 13 of 13 refined |
|---|---|---|
| pairs at or below the floor barrier | 6 of 13 = **0.462** | 6 of 12 = **0.500** |
| classification (`ridge_fraction = 1/3`) | **RIDGE** | **RIDGE** |
| median barrier depth | 8.31 log-units | **6.46 log-units** |
| median in floor units | 1.039 | **0.808** |
| margin against the floor barrier | **+3.9%** | **−19.2%** |
| median depth per unit path length | 15.35 | **11.45** |
| null-control median | 9379 (1172 floor units) | 7651 (956 floor units) |

**The ridge did not flip, and it did not merely survive.** The pair that separated
was one of the seven *above* the floor barrier (depth 13.57 log-units), so removing
it left the six pairs the classification rests on untouched and pulled the median
down through them. The claim the ruling flagged as exposed — a median 3.9% above
the floor barrier, measured on three of thirteen pairs — is now a median **19.2%
below** the floor barrier measured on **all thirteen**. Every barrier is an
**upper** bound (`PATH-01`), so a median below the floor barrier says the true
median is at most there: the bound direction and the recount push the same way.

Had it gone the other way it was pre-registered to be reported the same way. The
outcome table was written to `outputs/wit02_chartG/preregister.json` with its hash
before the first solve, keyed on the classifier's own output, and the ruling fixed
the reporting in advance: *"If it flips the ridge, that is the result."* It did
not flip; that sentence is why this paragraph can be believed.

**What this does not establish.** The recount does not make the ridge a claim about
connectivity, and it does not touch `PATH-01`: the barrier still walks a straight
line in chart G's own coordinates, the minimum-energy path is still not computed,
and the two `d = 16` results are still search statements. It also does not
establish anything about chart L.

---

## 4. The register, version 2

`outputs/close/wit02_register_v2.json`. Version 1 stays on disk unchanged — it is
the record of what the coverage was when `WIT-02` was enacted, and the gap it
reports is why this run exists.

| global witness set | witness pairs | refined under `WIT-02` | surviving | compliant |
|---|---|---|---|---|
| **chart G**, `d = 4` | 13 | **13 of 13** (100%) | **12 of 13** | **yes** |
| **chart L**, `d = 16` | 37 | **0 of 37** (0.0%) | — | no |
| **chart J**, `d = 16` | 13 | 13 of 13 (100%) | 7 of 13 | yes |

Two of the three committed witness sets now satisfy `WIT-02`. **Chart L is
unchanged and still uncovered**: 0 of 37, never refined, and it is the set the
dimension reading rests on. `WITNESS-04` stays **open and load-bearing**; the
ruling excluded chart L by name and refining 37 pairs across three grids is not
authorised.

The register is measured, not asserted: coverage is established by matching each
refinement record to its witness pair on exact equality of the separation in
decades against `WIT-01`'s `max_separation` for the same set. Version 2 is built by
a second implementation of that match, and the two sets that did not move —
chart L and chart J — come out identical to version 1, which is what makes the one
that did move a measurement rather than a difference between two builders.
`tests/test_witness_refinement_close.py` re-derives every figure from the
artefacts.

---

## 5. What changes on the claim surface

* **Spine item 4** gains its coverage in the same breath as its classification, and
  its numbers move: chart G at `d = 4` is a ridge on **13 of 13** refined pairs,
  **12 surviving**, 6 of 12 at or below the floor barrier, median **0.81 floor
  units**. Chart L stays 0 of 37 at 212 floor units and chart J 13 of 13 at 59.
* **Spine item 3** loses a bare universal. *"survives refinement in every chart
  tested"* was true over two of the three committed sets and read as three;
  `DOC-08` is what caught it.
* **Every witness count** for chart G now reads *13 of 13 refined, 12 surviving*
  rather than *3 of 13 refined, the other 10 never refined*.
* **`WITNESS-04`** stays open, narrowed to chart L alone.
* **The mechanism question is untouched.** `MECH-01` is exactly where the close
  left it.
