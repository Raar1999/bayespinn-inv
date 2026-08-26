# AUDIT — generation 8, the final technical generation

One tree, one commit. The machinery landed first at `01f0281` and every
measurement ran against it; `outputs/g8/manifest.json` records that commit with
`dirty=false`.

**Reading of "6 h, 5 candidates".** The ruling's §9 lists exactly five
`SPEC-g8-N` clauses, each with its own `F:` falsifier, and then makes the
negative control mandatory. That is the generation-7 shape — clauses with
falsifiers — rather than the generation-0 shape — a population of competing
patches scored against one another (`docs/gen/CANDIDATES_g0.md`). Read the second
way there would be no population to build, because none of the five clauses
admits competing implementations of the same change. The first reading is taken,
and it is recorded here rather than assumed.

**No `GEN_g8.md`.** Generation 7 recorded its handoff in
`docs/audit/AUDIT_g7.md` plus its state file rather than a separate generation
report, and generation 8 follows it. The result is
[`docs/G8_RESULT.md`](../G8_RESULT.md); the state is `LOOP_STATE_v5.json`; this
file is the audit and the handoff.

---

## 1. Spec clause status

| clause | status | evidence |
|---|---|---|
| `SPEC-g8-1` | **PASS** | PASS - CHART-01 closed structurally, not documented away. One reconstruction operator; the solver raises instead of interpolating; an AST guard fails when a second path appears, per call rather than per file. 24 profiles frozen from the deleted code path reproduce byte for byte, and both prior witness searches reproduce exactly. Falsifier (a second reconstruction path can be introduced without a test failing) does NOT fire. — `docs/G8_RESULT.md` §1; `tests/test_one_reconstruction_g8.py` |
| `SPEC-g8-2` | **PASS** | PASS, and the falsifier FIRES as the ruling anticipated. Chart J makes the junction a free continuous coordinate; at s=0 it is chart G at d-1 bit for bit (positive control). Displacing the junction moves the unit-homogeneous magnitude-block spectrum by 219% and 9.1% against chart G at d=15, versus 2.8% for the chart-G-to-chart-L change. The invariance claim is retired to its measured family. — `docs/G8_RESULT.md` §2; `tests/test_charts_g8.py`; `outputs/g8/chart_j.json` |
| `SPEC-g8-3` | **PASS** | PASS, and the falsifier FIRES. Observation-set perturbation moves the leading spectrum by 19.8% (same 16 biases, same range, geometric instead of linear spacing) up to 97.4% (narrowed to 0.30-0.60 V), against 2.8% for the chart change. Unchanged after sqrt(rows-used) normalisation. The identifiable count itself falls from 4 to 2 over the narrowed range. — `docs/G8_RESULT.md` §3; `outputs/g8/obs_set.json` |
| `SPEC-g8-4` | **PASS** | PASS - rank(cutoff) curves for all six cells, with the spectrum, the chosen cutoff, the largest multiplicative gap and whether the cutoff sits inside it. A bare integer is licensed in 2 of 6 cells (G_d4, L_d4). Falsifier (one bare integer rank survives where no population gap exists) does NOT fire: the claim surface quotes none. — `docs/G8_RESULT.md` §4; `tests/test_rank_curve_g8.py`; `outputs/g8/ranks.json` |
| `SPEC-g8-5` | **PASS** | PASS - criterion frozen, hashed and written to the artefact before any distance was computed; count reported as a curve over thresholds and stated as a lower bound. Basins at the pre-registered 0.3 decades: {"chart_G_d4": 20, "chart_L_d16": 67, "chart_J_d16": 26}. Falsifier (a count without its criterion, or a criterion chosen after seeing the clusters) does NOT fire. — `docs/G8_RESULT.md` §5; `tests/test_modes_g8.py`; `outputs/g8/modes.json` |
| `SPEC-g8-negative-control` | **REJECTED as required** | REJECTED as required, four times, end to end through the same predicates: the witness search on a distinguishable pair, the chart discriminator on a pinned junction, the cluster criterion on known-answer sets, and the solver on a chartless parameter vector. all_controls_pass=True. — `docs/G8_RESULT.md` §6; `outputs/g8/negative_control.json` |
| `OPS-01` | **PASS** | PASS - REP-01, SPEC-11's rank-curve rule, OPS-01 itself and a marked-as-reconstructed PH-22 are in docs/RULES_ENACTED.md, each with a guard and both controls, and tests/test_rules_enacted_g8.py asserts that transitively. See the escalation in docs/audit/AUDIT_g8.md section 3.1: PH-22 cannot be backfilled as a quotation because its text is not in the tree. — `docs/RULES_ENACTED.md`; `tests/test_rules_enacted_g8.py` |
| `SPEC-g0-3b-windows` | **OPERATOR-BLOCKED (hard)** | OPERATOR-BLOCKED (hard), unchanged; substitute evidence docs/WINDOWS_RISK_g6.md. — `docs/WINDOWS_RISK_g6.md` |

---

## 2. Findings opened, changed and closed this generation

| finding | severity | status | note |
|---|---|---|---|
| `CHART-01` | HIGH | **RESOLVED-STRUCTURALLY** | One reconstruction operator in charts._lerp; a doping vector crosses API boundaries only as grid values or as ChartedDoping; ScharfetterGummel1D.solve raises DopingChartError otherwise; an AST guard with both SW-20 controls fails when a second path appears. The pre-fix census found the implicit resampler load-bearing at five call sites in src/ and nine in tests/, including the published local rank and the surrogate's training set - the ruling's model of the defect was too small, see AUDIT_g8 section 3.2. |
| `CHART-02` | MEDIUM | **RESOLVED** | Subsumed by CHART-01's fix. ScharfetterGummel1D.solve no longer resamples a short doping array at all, so there is no silent chart left to depend on. |
| `SPEC-11` | MEDIUM | **MITIGATED** | rank_cutoff_record is now the only way g8 machinery reports a rank, and it reports a curve. The ruling's 'which today means d=4 only' is corrected by measurement to 'chart G d=4 and chart L d=4 only' - the licence follows the gap, not the dimension (chart J at d=4 has no gap either). |
| `DOC-07-a` | LOW | **MITIGATED** | The DOC-07 guard was too narrow to catch the generation-8 machinery commit, whose message asserts a measured count of this tree that the census contradicts. Under R-4 the message stands; the correction is forward in docs/G8_RESULT.md and docs/audit/AUDIT_g8.md. The guard is widened at generation 8 with that commit as its positive control. |
| `CI-01` | MEDIUM | **OPERATOR-BLOCKED** | Still blocked, and the ruling's section 10 puts a decision ahead of the command: remote or no remote. Unanswered as of this champion. docs/OPERATOR_TASKS.md is corrected to state that OT-1 requires adding a remote first, so the file no longer describes a command that cannot run. |
| `EOL-01` | LOW | **OPEN** | Amended by generation 8: writing with newline='' is only half the rule. Reading a CRLF file in text mode also normalises, so a read-modify-write round trip rewrites the whole file even when the write is careful. Generation 8 did exactly that to 20 tracked files and tests/test_line_endings_g6.py caught it before the commit. Tools that rewrite tracked files must open with newline='' on BOTH ends. |
| `FALSIFIER-01` | MEDIUM | **OPEN** | Opened at generation 8. run_witness_falsifier.py re-derived chart G by hand instead of importing it, so the generation-6 falsifier was a copy of the study it falsified and could only have detected a solver-level error, never a chart-level one. The witness result survives - g8 re-ran both through one class and got identical counts - but the independence the falsifier was supposed to supply was never there. Both now call ChartG; what remains open is that no falsifier in this repository has been audited for the same defect. |

`CHART-02` closes because `CHART-01`'s fix removes the mechanism it described: there is no silent resampler left for a call site to depend on. `FALSIFIER-01` and `DOC-07-a` are opened by this generation, both against work this loop shipped rather than against the code it audits. Everything else is carried forward; `LOOP_STATE_v5.json` is the full list.

---

## 3. Escalations against the ruling

`§1` asks for escalation at the same rate. Five, in descending order of
consequence.

### 3.1 `§7`'s retro-application of `PH-22` cannot be honoured as written

The ruling orders `PH-22` backfilled into `docs/RULES_ENACTED.md` "with a guard
and both controls, in the generation it is enacted". Two clauses of that cannot
be satisfied for `PH-22`, and saying so is cheaper than pretending.

* **The text does not exist in the tree.** `PH-22` is cited at nine call sites
  and quoted at none. Writing a quotation would be inventing operator text,
  which is the failure `docs/RULES_ENACTED.md` was created to prevent. It is
  recorded as a *reconstruction from its points of use*, marked as such in the
  file, and
  `tests/test_rules_enacted_g8.py::test_the_ph22_backfill_is_marked_as_reconstructed`
  asserts the marking so it cannot be quietly upgraded to a quotation later.
* **Its guard predates `SW-20` and does not ship both controls.**
  `tests/test_dtype_envelopes_g6.py` *measures* the two round-trip errors and
  asserts their separation. A measurement has no violation to plant. Retro-fitting
  a control to it and then claiming the rule was always enforced would be the same
  species of statement `OPS-01` exists to stop, so the gap is recorded in a
  one-entry exemption list the guard asserts cannot grow.

**The general point.** `OPS-01` is satisfiable forward and not satisfiable
backward. Every rule enacted from generation 8 on lands with its guard; every
rule enacted before generation 7 either has a guard already or has no recoverable
text, and no amount of retro-application changes which.

### 3.2 `§4`'s model of `CHART-01` was too small

The ruling describes "two reconstruction operators for one coordinate vector, in
files that never refer to each other, silently selected by which entry point was
called". The census taken before the fix found the implicit reconstruction
load-bearing at **five call sites in `src/`** and nine more in `tests/`, across
three grid resolutions — and found a **third** hand-written copy of chart G
inside `run_witness_falsifier.py`, the falsifier generation 6 used to check the
chart-G witness result.

Two things follow that the ruling could not have known.

* The surrogate's training set and the protocol splits — every supervised label
  this repository generates from the oracle — were produced through chart L. That is not itself a defect — the
  operator is grid-independent, so all three resolutions sample one chart — but
  it was nowhere written down, and "the local-study chart" undersells what chart
  L is.
* **The generation-6 falsifier was a copy of the study it falsified.** It
  re-derived chart G by hand rather than importing it, so it could detect a
  solver-level error and not a chart-level one. The result survives — §5 of the
  result document re-runs both through one class and gets identical counts — but
  the *independence* the falsifier was supposed to supply was never there. Opened
  as `FALSIFIER-01`, because no other falsifier in this repository has been
  audited for the same defect.

### 3.3 `§5`'s "which today means `d=4` only" is one word too strong

The ruling says a bare integer rank is justified "only where a gap justifies it —
which today means `d=4` only". Measured across six cells, the licence follows the
**gap**, not the dimension: chart J at `d=4` has no gap at the cutoff either. The
correct statement is *chart G at `d=4` and chart L at `d=4`*, and `d=4` is a
coincidence of those two charts rather than a property of the dimension.
`outputs/g8/ranks.json` carries the flag per cell.

### 3.4 `§8`'s test, generalised one step too far, fails on correct history

The ruling asks for "a test asserting `champion` is never the commit that wrote
the file". The natural-looking generalisation — *the champion never touches a
loop-state file* — is **false of correct history**: `922c2cc`, generation 7's own
champion, modified `LOOP_STATE_v4.json` to record a finding, and `7ef48c4` later
wrote the pointer. Both are right. A guard written the general way would fail on
`922c2cc` and be disabled within a generation, which is the `SW-20` failure mode.

`tests/test_loop_state_g8.py` therefore asserts the ruling's sentence exactly —
`champion_commit` is not the commit that last modified the state file — and its
docstring records what it deliberately does not assert.

### 3.5 `DOC-07`'s guard did not catch the commit that enacted `OPS-01`

Not an escalation against the ruling but against a guard this loop shipped, and
the same shape as the defect `OPS-01` names.

The generation-8 machinery commit `01f0281` says the implicit resampler was
"load-bearing at seven production call sites across three grid resolutions".
Three grid resolutions is right. **Seven is wrong**: the census found *five*
call sites in `src/` and nine more in `tests/`, and the message's author
conflated the two lists. A measured count of this tree, spelled out in words,
made permanent by `R-4`, in the commit that enacts the rule that rules must be
guarded. `tests/test_commit_messages_g7.py` matched digits beside
"passed"/"tests" and nothing else, so it did not fire. The narrowness was
deliberate and documented; it was also too narrow.

The guard is widened at generation 8 to catch a cardinal — digit or word — in
front of a noun naming something a run or a scan counts, with the vocabulary
explicit and `generations` deliberately excluded because it is a fact about
project history rather than a measurement. Its positive control is `01f0281`
itself, exactly as `1a090f0` is the control for the original patterns. Under
`R-4` the message stands; the correction is forward, here and in the result
document.

---

## 4. Defects generation 8 introduced and caught in itself

Recorded because a generation that reports only the defects it found in earlier
work is not auditing itself.

* **`EOL-01` fired against this generation's own tooling.** Twenty tracked files
  were rewritten from CRLF to LF by patch scripts that wrote with `newline=''`
  but *read* in text mode, which normalises. `tests/test_line_endings_g6.py`
  caught it before the commit. The finding's note is amended: the rule is
  `newline=''` on **both** ends of a round trip, not just the write.
* **A guard's own negative control caught a bug in the guard.** The first draft
  of `enforcing_modules` in `tests/test_rules_enacted_g8.py` matched
  `**Enforced by**` anywhere in a section, and the negative control — a defect
  paragraph that *mentions* the label inside backticks — made it read a module
  name out of prose about the rule. That is `SW-20`'s failure mode, found by the
  control `SW-20` requires, before shipping. The match is line-anchored now and
  the comment says why.
* **A new guard caught a live instance on its first run.** "Frequencies stay
  uncompared across charts" had no guard — the claim-surface battery matches
  *rank fractions*, and a witness rate is not one. `TestNoFrequencyComparison`
  is narrow by design: it matches the two literal search budgets this repository
  has rather than trying to recognise "a frequency", because a guard that parses
  the concept fires on the sentences that forbid it. On its first run it flagged
  `docs/CHART_RECONCILIATION_g7.md`, where the disclaimer sat in the sentence
  *before* the one carrying both numbers — safe to read, unsafe to quote. The
  sentence now carries its own disclaimer. The guard's scope is one comparison;
  the rest of the frequency rule is enforced by review, and this sentence is
  where that is said rather than left implied.
* **The basin count as first designed would have overstated the result.**
  `SPEC-g8-5` asks how many basins the witness set is, and single-linkage
  clustering at 0.3 decades answers *many* in both older charts. In chart L at
  `d = 16` it answers "one basin per member", which reads as a very strong
  result and is close to a trivial one: two independent draws from a log-uniform
  box spanning two decades in each of sixteen coordinates are nearly certain to
  differ by more than 0.3 decades somewhere, so the metric separates almost any
  two draws. The null control — the same criterion over the same number of
  ordinary prior draws that form no witness pair — was added for that reason and
  is reported beside the count. In chart G at `d = 4` the control is informative
  and the measurement sits below it; in chart L it does not, and the document
  says so before it says the number. What survives is the qualitative answer,
  which is what the clause actually asked.
* **Two smaller defects in the generation-7 claim-surface guard.** Its regime
  matcher accepted "globally" and rejected "locally" — an asymmetry that makes a
  guard shape prose rather than check it, and that a writer discovers by having
  a correct sentence rejected. It is symmetric now, with controls both ways.
  And `docs/NOVELTY_AUDIT.md` publishes the rank to a reader and was not on the
  claim surface, so nothing checked it; it is on the list now, and the row it
  carries needed a cutoff and a chart to get there.
* **A wide rank plateau can be an artefact of the estimator.** The first
  `rank_cutoff_record` reported the plateau of noise levels over which the rank
  does not move, and chart J's plateau spanned the whole grid — because the rank
  had saturated at `resolvable_rank`, not because the spectrum has structure.
  `plateau_containing_operational_cutoff.limited_by_resolvable_rank` is the flag
  that stops that reading, and `tests/test_rank_curve_g8.py` asserts both
  directions of it.

---

## 5. Carried forward unchanged

`PROV-03` (`ACCEPTED-PERMANENT`, cost statement in `docs/gen/GEN_g6.md` §2, cost
not grown), `PROV-07` (`MITIGATED-PENDING-CI`, win32-only validation stated in
every manifest), `REPRO-01` (`UNRESOLVABLE-BY-CONSTRUCTION`), `NB-02`, `NB-03`,
`PROV-05`, `SW-18a`, `S-3`, and `SPEC-g0-3b-windows` (`OPERATOR-BLOCKED`, hard,
substitute evidence `docs/WINDOWS_RISK_g6.md`).

`CI-01` stays `OPERATOR-BLOCKED` and the ruling's §10 decision — remote or no
remote — is unanswered as of this champion. `docs/OPERATOR_TASKS.md` is corrected
so OT-1 no longer describes a command that cannot run.

---

## 6. Handoff

The technical work is finished. The paper's spine, in the order the evidence
supports it:

1. **A local identifiability analysis cannot detect multimodal degeneracy in
   principle.** A Jacobian spectrum is a derivative at a point; a second mode
   8–15× away in doping is not in its domain. The *local* and *global* results
   never disagreed — they measure different things, and one of them cannot see
   the phenomenon.
2. **Witnesses exist in independently constructed charts, and it is not only
   the doping magnitudes.** Chart G at `d=4`, chart L at `d=16` natively, and
   the chart-G witness transfers into chart L with its separation preserved.
   Generation 8 adds chart J, whose extra coordinate is the junction position,
   and finds witnesses there too — including a pair whose metallurgical
   junctions sit at opposite ends of the device with an I–V difference below the
   floor. Terminal I–V cannot locate the junction either, once the doping is
   free to compensate.
3. **The barrier is deep.** Two isolated maxima, 242 log-units apart in
   log-likelihood, against a control direction 43.7× steeper with no second
   mode. Gradient-based inversion cannot cross it: it returns whichever basin it
   started in, with a well-conditioned local spectrum in hand.
4. **What that means for inverse design.** Any method reporting a *local*
   uncertainty inherits this, and generation 8 adds the practical corollary: the
   local spectrum is far more sensitive to the observation set than to the
   parameterisation, so "how identifiable is this device" is a question about the
   experiment before it is a question about the model.

The chart-versus-dimension reconciliation is a methods section, not the result.
