# Generation 11 — `WIT-02` closed on every set, `HIST-01` repaired, and a ratified premise falsified

**Status** the first generation under fused operator authority. The operator
directive of 2026-08-28 replaced the two-party arrangement with a condition
ladder (`LADDER.md`), a self-ruling ledger (`RULINGS.md`) and an unreachability
standard that has to be *earned* rather than asserted. This document is the
measurement; `RULINGS.md` carries the ruling.

**The ladder moved up.** `L2 → L1`. It was not descended from.

**Measurement conditions, once, for every number below.** Oracle-arbitrated,
301-node production grid. Prior log-uniform on `|doping|` over 1e21–1e23 m⁻³ per
anchor, hash `ba11a6d5357388cb…`, unchanged since generation 6. Noise relative,
i.i.d., **2%** (`noise_rel = 0.02`), which is also the **distinguishability
floor**. Observation set 16 bias points over 0.15–0.90 V. Refinement battery
`N ∈ {301, 601, 1201}` × `{default, tight}`, `tol_carrier_tight = 1e-12`,
imported from `run_g9` rather than restated. `CPython 3.11.9, win32` — and no
claim here has been evidenced on any other interpreter or operating system
(`PROV-07`).

---

## 1. `WITNESS-04` is closed — chart L refined in full, 37 of 37

`WITNESS-04` has been open since generation 7 and load-bearing since generation
10. Globally, chart L's 37 witness pairs at `d = 16` carry the chart-L basin
search statement and, through it, the **dimension reading** — and no refinement
of that set had ever been run. Under `WIT-01` the admissibility ratio is
**1.000** in all three charts, so admissibility removes none of them; the
distinguishability floor is **2.0e-02** = max(noise 2.0e-02, solver
discretisation 1.5e-03). `docs/CLOSE_RULING.md` §3 registered the non-compliance
rather than repairing it, because refining 37 pairs was new solving the close
forbade.

### 1.1 The pilot, which is what made the verdict unavailable

The directive §2 states that **a `U-BUDGET` verdict without a measured pilot is
void**, and §7 said to pilot this item before ruling on it. Declaring a hard
thing impossible is the cheapest way to finish, and the pilot is the thing that
takes that option away.

`scripts/pilot_wit02_chartL.py`, 3 pairs, `outputs/g11/pilot_chartL.json`:

| | measured |
|---|---|
| per pair | **7.5 s** (7.2–7.7, spread **×1.07**) |
| projected, all 37 | **278 s** |
| projected, + null control | **286 s** |
| **actually taken** | **288 s** — the projection was low by **3.5%** |

The spread is what makes the extrapolation checkable rather than asserted: the
battery's cost is set by the grid and the tolerance, both fixed, so it should
not depend on which pair is solved, and ×1.07 says it does not.

**A five-minute experiment cannot carry a budget verdict.** `U-BUDGET` was
therefore unavailable, no rung was descended, and the work was done.

### 1.2 The result

`scripts/run_wit02_chartL.py`, pre-registered before the first solve
(`outputs/g11/wit02_chartL/preregister.json`, scope hash
`dd3309fbbfd1270d…`, outcomes hash `8a3e9e3ed0da3cda…`).

**37 of 37 refined. 26 survive. 11 separate.**

| set | pairs | refined | surviving | lost |
|---|---|---|---|---|
| chart G, `d=4` | 13 | 13 of 13 | 12 | 1 (7.7%) |
| **chart L, `d=16`** | **37** | **37 of 37** | **26** | **11 (29.7%)** |
| chart J, `d=16` | 13 | 13 of 13 | 7 | 6 (46.2%) |

`WIT-02` is now satisfied on **all three** committed witness sets.
`outputs/close/wit02_register_v3.json`; versions 1 and 2 stay on disk unchanged.

### 1.3 Controls

All four are global statements in chart L at `d = 16`, the cell the refinement
covered.

| | control | result |
|---|---|---|
| `R1` | every pair's `N=301` default distance reproduces the committed `witness_pair_distance` bit-identically | **PASS**, 37 of 37 |
| `N1` | a chart-L null-control pair — consecutive ordinary draws forming no witness pair — must **not** survive | **PASS**, worst distance 0.4507 against a floor of 0.02 |
| `P1` | two **identical** devices must survive, at distance exactly zero | **PASS** |
| `D1` | one pair's battery re-run; all six distances bit-identical | **PASS** |
| `B1` | the full 37-pair barrier set reproduces `outputs/g10/ridge_basin.json` | **PASS**, 37 of 37 depths and the median identical |
| `S1` | each counted pair's depth in the subset run equals its depth in the full run | **PASS**, 26 of 26 |

`P1` is the control `IA-1` asks for and the one chart G's run did not have: a
battery that rejected everything would separate two identical devices, and every
"separates" verdict above would then be vacuous. `R1` is weaker than chart G's
reproduction control in a stated way — chart G compared **two generations' code
paths**, `R1` compares this code path against the **artefact it reads**, so it
cannot detect a defect already present when `outputs/g8/reproduce.json` was
written. Chart L had no previously refined pairs to do better with; that is what
0 of 37 meant.

### 1.4 The recount — the classification does not move

Barriers recounted over the 26 survivors through `run_g10._barrier_set`, the
same imported function that produced generation 10's numbers, under generation
9's `BarrierCriterion` (`9631b4711f99a631…`) and generation 10's
`RidgeBasinDecision` (`88748b9f6d4e3ed8…`), both verified unmoved before the
first solve.

| | all 37 (generation 10) | 26 survivors |
|---|---|---|
| median barrier | 1696.11 | **1782.48** |
| median in floor units | 212.01 | **222.81** |
| pairs at or below the floor barrier | 0 of 37 | **0 of 26** |
| shallowest pair | 22.60 | **132.18** |
| classification | `BASIN` | **`BASIN`** |

**`FLIPPED: False`.** The `RIDGE` branch was pre-registered as plainly as the
`BASIN` one — *if chart L is a ridge, the dimension reading dies* — and it is
not what was measured.

The median deepened because the pairs that separated were the shallow ones: the
shallowest surviving barrier is **132 floor units**, up from 22.6. This is
reported as what it is. It does **not** make the basin a stronger result: a
basin is a statement about pairs that *are* witnesses, and eleven of them turned
out not to be.

### 1.5 What full coverage does not buy

`WIT-02` tests **witnesses**, not **connectivity**. Every barrier is still the
depth along a **straight line** in one chart's own coordinates and therefore an
**upper** bound (`BOUND-01`); the minimum-energy path was **not** computed
(`PATH-01`). Both `d=16` results remain **search statements** — no connecting
path below the floor was found — and refining the witnesses does not convert
either into a separation. `AH-13` applies unchanged.

---

## 2. `HIST-01` — the hashes were rewritten, not lost

Carried for three generations as `UNREPAIRABLE FROM INSIDE THE TREE`. It was
repairable from inside the tree the whole time.

`git filter-repo` rewrote this branch on **2026-08-28 at 09:16**, giving every
commit from `c115757` forward a new hash, and left the `old → new` table in
`.git/filter-repo/commit-map`. **All 26 recorded hashes resolve** — 25 through
the map, 1 directly — under three verifications, of which the second is
independent evidence rather than restatement: the mapped commit's **own message**
names the generation the state file recorded it under, 16 of 16, and those
messages predate the rewrite.

**Eight failing guards now pass and none was weakened**; `resolve_commit` refuses
an absent, malformed or unverified map and the guard fails exactly as before.

**Three more guards were silently *skipping*, and they are the worse half of the
finding.** Two are in `tests/test_commit_messages_g7.py`, whose helper turns a
non-zero `git` exit into `pytest.skip`: neither
`git log … 3e05c9da…^..HEAD` nor `git log -1 1a090f0` could resolve, so **the
guard that polices `DOC-07` was not running over the range it was written for**,
and a green suite said nothing about it. The third was in
`tests/test_loop_state_g8.py`. All three now run. A failing guard is visible; a
skipping one is a guard that has quietly stopped existing.

Restoring them required the map to carry the **complete** rewrite table rather
than only the hashes a state file cites: `1a090f0` appears in no `LOOP_STATE`
file, and a subset map would have left it — and every other hash recorded in a
document, a module or a commit message — unresolvable the moment
`.git/filter-repo/` is gone. All 35 rewritten commits are preserved.

The full account, including the four external copies that were examined and were
all dead ends, and the `V3` check whose first draft was wrong: **`docs/HIST01_REPAIR_g11.md`**.

---

## 3. A ratified premise is falsified — headroom does not predict survival

`docs/CLOSE_RULING.md` §2 ratified corrected premise **(b)**:

> What predicts survival is **headroom** against the distinguishability floor:
> the 7 survivors are exactly the 7 smallest distances at `N=301` and the 6 that
> separate are the 6 largest.

That was measured on **chart J** and confirmed on **chart G**. Chart L is the
first set to meet the rule without having helped form it, and it is also the
largest. `scripts/check_headroom_g11.py`, arithmetic over existing artefacts,
`new_solves = 0`, `outputs/g11/headroom.json`:

| set | n | separating | spearman | **concordance** | bands | formed the premise |
|---|---|---|---|---|---|---|
| chart G, `d=4` | 13 | 1 | +0.463 (p=0.111) | 1.000 | clean, 0.977 / 0.989 | yes |
| chart J, `d=16` | 13 | 6 | +0.866 (p=0.000) | 1.000 | clean, 0.922 / 0.937 | yes |
| **chart L, `d=16`** | **37** | **11** | **−0.033 (p=0.845)** | **0.479** | **overlap, 0.996 / 0.533** | **no** |

*Concordance* is the premise stated as the predictive claim it is: the
probability that a separating pair sits further from the floor than a surviving
one. **1.000** is the perfect ordering the premise describes; **0.500** is a
coin. Chart L returns **0.479**.

**The premise holds on exactly the two sets that formed it and carries no
information on the one that did not.** The surviving and separating bands
overlap across half the floor: a chart-L pair can survive at 0.996 floor units
while another separates at 0.533.

**This does not say the two 13-pair results were wrong.** They reproduce. It
says the rule read off them does not generalise — the same shape as generation
9's finding that a four-way sensitivity ordering measured at one operating point
did not survive nine more, and a reminder that chart G's clean split rests on a
**single** separating pair.

**It strengthens the close's refusal to adopt a margin band, and for a better
reason than the one recorded.** That refusal rested on the band being 1.4
percentage points wide and therefore tuned (`PH-11`). Chart L is the stronger
argument: across 37 pairs **there is no band to tune**. The decision was right;
its recorded justification was weaker than the truth.

`SR-1` traces this forward. Spine item 3's clause *"survival is predicted by
headroom against the floor, not by geometry, in both refined sets"* was true of
the two sets it named and is **not** true of the three that now exist; it is
amended in §5.

---

## 4. Two statuses that had stopped describing the world

### 4.1 `CI-01` reverts — **a remote now exists**

`git remote -v` is no longer empty. `origin` points at
`https://github.com/Raar1999/bayespinn-inv.git`, `.git/config` carries the
stanza with an mtime of 2026-08-28 **09:20** — four minutes after the
`filter-repo` run — and `refs/remotes/origin/main` resolves, so it was fetched
from as well as configured. One operator action on that morning did both, and
the loop noticed neither until generation 11 went looking.

`docs/OPERATOR_TASKS.md` already carried the reversion condition:

> *If a remote is added later the status reverts and the cost statement is
> superseded forward, not deleted.*

**`CI-01`: `ACCEPTED-PERMANENT` → `OPERATOR-BLOCKED`.** The condition that made
it permanent — *there will be no remote* — is false. A status that outlives its
own premise is exactly the defect that file exists to record.

**Nothing is closed by this.** `.github/workflows/ci.yml` has still never
executed, the 3.9 floor is still a static scan, `PROV-07` is still `win32`-only.
`git push` is reserved by `R-4` and again by directive §6. What is newly true is
only that **the action is available**: for nine generations `OT-1` named a
command whose precondition did not exist.

### 4.2 `PROV-07` reclassified

`MITIGATED-PENDING-CI` → **`OPERATOR-BLOCKED`**. *Pending* was the wrong word
for nine generations. Nothing was pending, because nothing was going to happen
without a reserved action. Naming the reservation is what makes the status
describe the world — and it is what makes the `L0` rung's *"no open HIGH outside
`ACCEPTED-PERMANENT` / `OPERATOR-BLOCKED`"* readable rather than ambiguous.

---

## 4.3 `IA-2` — the archive re-run, and it found nothing

The directive §4 makes this mandatory every generation: re-run **all** historical
negative controls, not this generation's. If any has started behaving
differently, standards have drifted and the rule is to halt and repair toward
strictness *before scoring anything*.

Every generation's own script was invoked with `--phases negative_control` and an
`--out` pointing into `outputs/g11/archive_rerun/`, so no archive artefact was
overwritten. The close addendum has no separate control phase, so its whole
refine phase was re-run.

| generation | controls | measured quantities identical | verdict unchanged |
|---|---|---|---|
| g8 | 4 | yes | yes |
| g9 | 4 | yes | yes |
| g10 | 5 | yes | yes |
| close addendum | 3 | yes | yes |

**16 controls across four generations, no drift.** The only differences anywhere
are wall-clock timings — which is what makes dropping them safe rather than
convenient. `outputs/g11/archive_rerun/summary.json`.

A negative result, and the one worth having: this generation added a `WIT-02`
row, repaired `HIST-01` and changed two statuses, and none of it moved a
historical control.

---

## 5. The spine, amended

`R-3` reserves `papers/**`. This is the spine, not an edit to the draft.
Items 1, 2, 5 and 6 are unchanged from `docs/CLOSE_RULING.md` §5. Items **3** and
**4** are amended; the amendments are marked.

3. **The degeneracy is real and survives refinement in all three committed
   witness sets, every one of which lost members.** Globally, in **chart G** at
   `d=4`, **13 of 13** refined and **12** surviving; in **chart J** at `d=16`,
   **13 of 13** and **7**; in **chart L** at `d=16`, **37 of 37** and **26**
   *(amended — chart L was 0 of 37 and untested)*. 8.18× and 14.75× in doping,
   694 nm against 271 nm in junction depth falling 1.7% under `N = 301 → 1201`.
   **What predicts survival is not known.** Headroom against the floor predicts
   it perfectly in the two 13-pair sets and not at all in the 37-pair one
   (concordance 1.000, 1.000, **0.479**), so no threshold is adopted and none is
   defensible *(amended — this clause said headroom predicted survival)*.

4. **Its geometry is dimension-dependent, not chart-dependent**: pairs sit at the
   instrument floor at `d=4` and do not at `d=16` in either chart. **The reading
   now rests on three fully refined sets** *(amended — one of the two `d=16`
   sets was previously unrefined)*: **chart G** `d=4`, 13 of 13 refined, 12
   surviving, 6 of 12 at or below the floor barrier, median **0.81** floor
   units; **chart J** `d=16`, 13 of 13, 7 surviving, **58.5** floor units, 0 at
   the floor; **chart L** `d=16`, **37 of 37, 26 surviving, 222.8** floor units,
   **0 of 26** at the floor. What the chart moves at matched `d` is the
   **depth** — 13× in witness-to-null ratio between two charts with matched path
   lengths. **The `d=16` results are search statements against an upper-bound
   barrier, not separation proofs**: no connecting path below the floor was
   found along the straight line, and the minimum-energy path was not computed.

---

## 6. Limitations

* **The mechanism is unexplained.** Why widening the bias window compresses the
  sensitivity spectrum toward its leading direction is not known. One method —
  localisation of the leading direction — has been tried and falsified.
  `MECH-01` open, and it is the ladder's remaining distance to `L0`.
* **The barrier is an upper bound and the minimum-energy path was not
  computed.** Both `d=16` results are searches that found nothing.
  `PATH-01` open, and full `WIT-02` coverage does not touch it.
* **What predicts refinement survival is unknown**, and the rule that was
  ratified as the answer is falsified on the largest set (§3).
* **The upper bias boundary is untested.** Not tested and found sound — never
  tested. `PH-15`.
* **No claim in this repository has been evidenced on any interpreter but
  CPython 3.11 or any operating system but `win32`.** A remote now exists; CI
  still has not run. `CI-01` and `PROV-07` `OPERATOR-BLOCKED`, `OT-1` stands and
  is now executable.
* **The basin/ridge classifier is binary over three cells**, and chart G's
  clean headroom split rests on a single separating pair.
* **`REPRO-01` is untouched by the `HIST-01` repair.** A commit hash is
  recoverable; the working tree that produced `outputs/identifiability/` on
  2026-08-19 is not.
