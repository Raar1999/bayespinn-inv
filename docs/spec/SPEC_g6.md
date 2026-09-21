# SPEC_g6 — generation 6, frozen

**Generation** 6 · **Date** 2026-08-25 · **Champion at entry** `bf5aa21`
**Target** S-1, global identifiability — the highest remaining scientific risk
**Ruling** operator amendment for generation 6, §4
**Supersedes** nothing. `SPEC_g0` clauses remain in force.

---

## 0. The arbiter rule, restated because it is this generation's CRITICAL surface

`GRAD-01` measured surrogate directional derivatives as agreeing with the oracle
**only inside the identifiable subspace**: mean cosine +0.504 inside, −0.001
outside, unchanged by a 33× training-budget increase. A global identifiability
study probes precisely *outside* that subspace.

**The surrogate may not arbitrate any global claim.** It may propose; the oracle
confirms or rejects before anything enters a table. Any candidate whose headline
number traces to a surrogate evaluation outside the certified subspace is an
automatic discard.

PH-22 sharpens this with a second, independent reason measured in Phase A: the
surrogate path is float32 and cannot represent doping differences below ~1e-7
relative. The oracle is float64 (round-trip 1.678e-16). A float32 instrument
cannot resolve the degeneracies this study exists to find.

---

## 1. Measured baselines — the pilot (§4.5)

All on the audit machine: Windows 11, Python 3.11.9, CPU, N=301 uniform grid,
1 µm Si PN junction, 19 biases over 0–0.9 V.

### 1a. Oracle cost

| grid | s per I–V curve (19 biases) | ms per solve |
|---|---:|---:|
| N=201 | 0.312 | 16.4 |
| **N=301** | **0.360** | **18.9** |
| N=601 | 0.582 | 30.7 |

Peak traced memory: **0.2 MB** per curve. Memory is not a constraint; wall-clock
is. **Budget unit: 1 oracle I–V curve ≈ 0.36 s, so ≈ 10,000 curves per hour.**

### 1b. Solver discretisation floor — and a correction to the first attempt

The first pilot reported `|I(301)−I(601)|/|I| = 2.32e-02` and
`|I(601)−I(1201)|/|I| = 1.73e-01`, i.e. error *growing* under refinement. That was
an artefact of the measurement, not the solver: the maximum was taken over the
biases the **N=301** solve certifies, and it was dominated by `V = 0.05`, which the
**N=1201** solve refuses to certify (`current_is_trustworthy() == False`). PH-08
says no current is reported where the solver does not certify it; the first pilot
violated that and was discarded.

Re-measured over the 17 of 19 biases trustworthy in **all three** grids:

| comparison | max relative difference |
|---|---:|
| N=301 vs N=601 | **2.86e-03** |
| N=601 vs N=1201 | **1.58e-02** |

Still not monotone, and the cause is localised: for `V ≥ 0.15` the differences
halve under refinement (1.47e-03 → 1.20e-03 at V=0.15; 1.18e-03 → 5.97e-04 at
V=0.30; 2.24e-04 → 1.19e-04 at V=0.90), which is ordinary convergence. The
non-monotone maximum comes entirely from `V = 0.10`, where I ≈ 1.3e-03 A/m² and
the solver's own current noise floor competes with discretisation.

**Adopted observation set: `V ∈ [0.15, 0.90]`, 16 points.** Not a convenience: it
is the range over which the oracle's discretisation error is measured to converge,
and it is chosen *before* any witness search (`AH-16`).

Over that set:

| floor | value | basis |
|---|---:|---|
| solver discretisation floor | **1.5e-03** | max \|I(301)−I(601)\|/\|I\| for V ≥ 0.15 |
| measurement noise floor | **2.0e-02** | the project's standard 2% relative noise |
| **distinguishability floor** | **2.0e-02** | `max` of the two |

Both are reported, never subtracted (PH-13). The noise floor dominates by ~13×,
so at 2% noise this study is noise-limited rather than solver-limited — which is
the regime a physical identifiability claim should be made in.

### 1c. Pre-registered `n` (PH-17, `AH-14`, `AH-15`)

Projected against a 6 h generation budget, targeting ≤ 45 min of oracle time:

| stage | oracle curves | projected wall-clock |
|---|---:|---:|
| witness search, d=4 | 2,000 | ≈ 12 min |
| contraction spectrum, d=4 | 2,000 | ≈ 12 min |
| dimension sweep, d ∈ {2, 4, 8} | 3 × 1,000 | ≈ 18 min |
| **total** | **7,000** | **≈ 42 min** |

**These `n` are fixed here, before the first production sample.** If the budget
proves insufficient, the *scope of the claim* is reduced — never the `n` behind it
(§4.5, `SCI-03` precedent).

**The prior is fixed and hashed before sampling** (`AH-14`): log-uniform in doping
magnitude over `[1e21, 1e23]` m⁻³ per anchor, sign fixed by the profile family
(p-side negative, n-side positive). Its SHA-256 is recorded in the run manifest.

---

## 2. Mandatory clauses

### SPEC-g6-1 — Witness search

**CLAUSE** Search for pairs `(θ, θ′)` far apart in parameter space whose oracle
observations differ by less than the distinguishability floor. A found pair is a
concrete, checkable witness of global non-identifiability and is reported with
both profiles, both I–V curves, the observational distance, and both floors.

**BASELINE** No global witness search has ever been run on this project. The local
result is 3–4 identifiable directions of 16 at the reference operating point; the
remaining 12–13 are locally flat, but no pair of *distant* profiles has been
exhibited. `C14` exhibits equivalence *twins* — profiles differing by up to 1.26×
locally, changing I–V by 0.024–1.275% — which is a local statement.

**TARGET** Report the closest pair found, by observational distance, together with
its parameter-space separation. Budget: 2,000 oracle curves, pre-registered above.

**REGIME** d=4, prior as §1c, `V ∈ [0.15, 0.90]` (16 points), 2% relative noise,
distinguishability floor 2.0e-02, oracle at N=301.

**FALSIFIER** No witness found within the pre-registered budget. Then the claim is
**"no witness found at this budget"**, not "identifiable" — `AH-13`.

**GATE** `G-PHYS`, `G-STAT`, `SPEC-g6-5`.

**COST CEILING** 2,000 oracle curves ≈ 12 min.

**RISK** A witness that is a *solver* artefact rather than a physical degeneracy.
This is what the generation's falsifier candidate exists to attack.

### SPEC-g6-2 — Contraction spectrum

**CLAUSE** Report the prior → posterior variance ratio per direction, on the
oracle, over the pre-registered `n`, and compare the number of materially
contracting directions with the local rank of 3–4.

**BASELINE** Never measured. The local Jacobian rank at the reference point is 4
(`step_symmetric`), of 16.

**TARGET** A contraction ratio per direction with `n = 2,000`, each direction
labelled contracting or not against a stated threshold.

**REGIME** As SPEC-g6-1.

**FALSIFIER** Contraction rank materially exceeds the local rank — which would mean
the local framing *understates* the available information, and README, the matrix
and the draft all change.

**GATE** `G-STAT`, `SPEC-g6-5`.

**COST CEILING** 2,000 oracle curves ≈ 12 min.

**RISK** Reporting contraction against an unstated or post-hoc prior (`AH-15`).
The prior is hashed before sampling.

### SPEC-g6-3 — Dimension sweep

**CLAUSE** The result is reported as a function of `d`. "Rank 3–4" is meaningless
without its denominator.

**BASELINE** `D13` measured that the *local* rank does not grow with the
parameterisation: P = 8 → 32 leaves it at 3–4. Whether the *global* picture behaves
the same way is unmeasured.

**TARGET** d ∈ {2, 4, 8}, n = 1,000 each.

**FALSIFIER** A single-`d` result presented as the identifiability result.

**GATE** `G-STAT`.

**COST CEILING** 3,000 oracle curves ≈ 18 min.

**RISK** d=8 at n=1,000 is thinner per dimension than d=2 at n=1,000. The `n` is
stated per `d` and the thinning is stated with it.

### SPEC-g6-4 — Local/global relationship

**CLAUSE** State explicitly whether the local Jacobian rank predicts the global
contraction rank, at which operating points, and where it fails.

**BASELINE** The two have never been compared. The local rank is 4 at the
reference point.

**TARGET** A stated relationship, not two numbers side by side.

**FALSIFIER** Local and global reported adjacently with no stated relationship.

**GATE** `G-STAT`, `G-DOC`.

**COST CEILING** Analysis only; reuses SPEC-g6-2's samples.

**RISK** Concluding agreement from a single operating point.

### SPEC-g6-5 — Arbiter compliance

**CLAUSE** Every global number traces to an oracle evaluation with its
trustworthiness flag recorded.

**BASELINE** The surrogate is 152× faster and would make every stage above ~100×
cheaper. That is exactly the temptation this clause exists to remove.

**TARGET** Every reported observation carries `converged` and
`current_is_trustworthy()`; the count of rejected-as-untrustworthy evaluations is
reported, not silently dropped (`PH-19`).

**FALSIFIER** One headline number traceable to a surrogate call outside the
certified subspace.

**GATE** `G-PHYS` — and this is the generation's `CRITICAL` reward-hacking surface.

**COST CEILING** n/a.

**RISK** The negative-control candidate is built specifically to violate this and
must be rejected by the battery.

### SPEC-g6-6 — Claim surface synchronisation

**CLAUSE** Whatever S-1 concludes, every statement of the identifiability result
in README, `CLAIM_EVIDENCE_MATRIX`, `RELEASE_READINESS` and the corrigendum carries
local/global label, regime, `d`, prior, noise, and both floors.

**BASELINE** Generation 0 corrected six of seven instances to carry local/regime.
None of them carries `d`, prior, or floors, because none of those existed yet.

**TARGET** A grep finds zero statements missing any of the five conditions of §4.2.

**FALSIFIER** One statement missing any condition.

**GATE** `G-DOC`.

**COST CEILING** Documentation only.

**RISK** `papers/draft.md` is `R-3` and can only be corrected by corrigendum.

---

## 3. Freeze

Hash recorded in `LOOP_STATE_v3.json`. The prior specification is hashed
separately and before sampling, per `AH-14`. A defect in this spec is fixed by
writing `SPEC_g7.md` that cites and supersedes it, never by editing this file.
