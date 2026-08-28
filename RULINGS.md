# `RULINGS.md` — self-rulings under fused operator authority

**Instantiated** 2026-08-28, before generation 11 Phase A. Hashed at
instantiation per the directive §8; the instantiation hash is the hash of this
file with **no rulings in it**, which is the only hash of it that can be taken
before the data exists. Every later generation appends and re-hashes, and each
ruling records the hash of the file it was appended to.

Until 2026-08-28 two parties ran this loop: an executor that measured and an
operator that ruled. The operator supplied three things the executor did not — a
party with no stake in the previous generation's output, authority to declare
scope closed, and someone to be wrong in a *different direction*. Fusing the
roles removes the second party, not the second function. This file is where the
second function is reconstructed from the inside, and it is worth being explicit
that a ruling written by the party that produced the measurement is a weaker
instrument than one written by a party that did not. The mechanisms below are
what stand in for the missing independence; none of them is that independence.

---

## The form every ruling takes

```
RULING g<N>
RATIFIED:   what stands, with the evidence that makes it stand
CORRECTED:  what the previous ruling or spec got wrong, named as an error
ENACTED:    new rules, each with a guard and both controls, this generation
LADDER:     rung held / descended / climbed, with the §2 verdict if descended
NEXT:       the single highest-severity target, with why it beats the others
PREMISES:   what this ruling rests on that has not itself been measured
```

## The rules that govern this file

* **`SR-1` premise ledger.** Every ruling lists its unmeasured premises. When a
  later generation invalidates one, it traces **forward** to every decision
  resting on it and reopens each. The 44% and the sub-grid premise were both
  caught by luck; this makes it systematic.
* **`SR-2` correction rate.** A ruling that ratifies everything and corrects
  nothing is a signal, not an achievement. Corrections per generation are
  tracked in the table below. **Two consecutive generations at zero triggers a
  mandatory red generation**, regardless of where the ladder stands.
* **`SR-3` devil's advocate, before promotion.** For the candidate about to be
  promoted, write the strongest available case that it is wrong — an argument,
  not a caveat list — and answer it in the ruling. If the answer is "we would
  need to measure X", X is the next generation's first clause.
* **`SR-4` adversary against self.** Phase A re-audits the previous
  generation's *ruling*, not only its measurements. Rulings are claims and get
  the same treatment.

## Correction rate — `SR-2` ledger

| generation | corrections | zero-streak | red generation triggered |
|---|---|---|---|
| (pre-fusion g0–close addendum) | operator-written; not counted under `SR-2` | — | — |
| `g11` | **9** — three of them errors in this loop's own rulings, two of them errors of mine made during the generation | 0 | no |
| `g12` | **7** — four of them mine, including the pre-registered discriminator its own control killed and a DOC-07 violation the guard I restored caught in my own commit | 0 | no |

---

# `RULING g11` — the first under fused authority

**Written** 2026-08-28. **Appended to** `RULINGS.md` at instantiation hash
`43f7182d77c8f66e73a8fe1dce60233833cd5497c3c3c5b7888ae819277f6fe1`.
**Ladder** `LADDER.md` at
`a2596365f4ec053ba7fda37901c1bd8a11db264f4954a080f6801446743a7926`, unedited.
**Measurement** `docs/G11_RESULT.md`, `docs/HIST01_REPAIR_g11.md`.

---

## `RATIFIED`

**`WIT-02` is satisfied on all three committed witness sets.** Chart L's 37
witness pairs went through generation 6's battery, imported rather than
restated: **37 of 37 refined, 26 survive, 11 separate**. Six controls, all
passing, and two of them are what make the result mean anything — `N1`, a
chart-L null pair that must not survive and did not (0.4507 against a floor of
0.02), and `P1`, two identical devices that must survive and did, at distance
exactly zero. `P1` is the control chart G's run did not have: without it, a
battery that rejected everything would produce the same "11 separated" headline.
`outputs/close/wit02_register_v3.json`, derived by matching rather than
asserted, with versions 1 and 2 left on disk.

**The chart-L classification does not move.** `BASIN` over the survivors, 0 of
26 at or below the floor barrier, and the full 37-pair set reproduces
generation 10's depths **bit-identically, 37 of 37, median included**. The
`RIDGE` branch was pre-registered as plainly as the `BASIN` one — *if chart L is
a ridge, the dimension reading dies* — and is not what was measured. The
dimension reading now rests on three fully refined sets.

**`HIST-01` is repaired.** All 26 recorded hashes resolve, 25 through
`.git/filter-repo/commit-map` and 1 directly, under three verifications of which
`V2` is independent: the mapped commit's own message names the generation the
state file recorded it under, 16 of 16, and those messages predate the rewrite.
Eight failing guards pass; none was weakened, and the resolver refuses an
unverified map. **Three guards were also silently skipping**, two of them the
`DOC-07` commit-message guard, which was therefore not running over the range it
was written to police.

## `CORRECTED`

Nine, and the first three are errors in what this loop had already ruled.

1. **`HIST-01`'s status was false, not merely stale.** `UNREPAIRABLE FROM
   INSIDE THE TREE` was carried for three generations. The repair was a file
   inside the tree the whole time. The four places the directive §7 named — `git
   fsck`, the two preservation copies, the pre-loop zip — were all examined and
   were all dead ends; the answer was in `.git/filter-repo/`, which nobody had
   listed. **This is the second instance of a class the close ruling had already
   named** (`DOC-03a`, §5.1) and did not enact anything about. `OBS-01` below is
   that enactment, one generation late.

2. **`CI-01` outlived its own premise.** It was made `ACCEPTED-PERMANENT` at
   generation 9 by a default that fired on the condition *there will be no
   remote*. **A remote exists** — `origin`, configured and fetched from, with
   `.git/config` stamped 09:20 on 2026-08-28, four minutes after the
   `filter-repo` run. The reversion condition was already written down.
   `ACCEPTED-PERMANENT` → **`OPERATOR-BLOCKED`**. Nothing is closed by this: CI
   has still never run.

3. **`PROV-07` was mislabelled for nine generations.** `MITIGATED-PENDING-CI`
   says something is pending. Nothing was pending; nothing was going to happen
   without an action reserved to the human. → **`OPERATOR-BLOCKED`**.

4. **A ratified premise is falsified.** `docs/CLOSE_RULING.md` §2 (b) — *what
   predicts refinement survival is headroom against the floor* — holds
   perfectly on the two 13-pair sets that formed it and carries **no
   information** on the 37-pair set that did not: concordance **0.479** against
   0.500 for a coin, spearman −0.033 at p=0.845, bands overlapping from 0.53 to
   1.00 floor units. `SR-1` traces it forward to spine item 3, amended in
   `docs/G11_RESULT.md` §5. The same shape as generation 9's ordering result,
   and a reminder that chart G's "clean split" rests on **one** separating pair.

5. **The close's reason for refusing a margin band was weaker than the truth.**
   It refused because the band was 1.4 percentage points wide and a threshold
   inside it would be tuned. Chart L shows there is no band. The decision was
   right; its recorded justification was not the strongest available.

6. **The directive's own guess about `CI-01` was wrong when written.** §7
   proposed `U-INSTR` with reachability condition *a remote exists*. The remote
   already existed. No verdict was issued, and the classification would have
   been false at the moment of issuing.

7. **`WITNESS-04` was never a budget question**, which only a pilot could
   establish. 7.5 s per pair, 278 s projected, 288 s actually taken — the
   projection low by 3.5%. Three generations treated 37 pairs as out of scope
   without measuring it once.

8. **My own `V3` check was wrong in its first draft.** It anchored on the commit
   that *added* each state file and reported `LOOP_STATE_v4` and `v5` as
   violations. Both were amended after being added, by commits whose messages
   say so. A verification that reports two false violations gets ignored the
   third time. Recorded in `docs/HIST01_REPAIR_g11.md` §3.1 rather than tidied
   away.

9. **My own `EOL-01` "repair" was a worse instance of `EOL-01`.** I matched on
   *working-tree CRLF* instead of on *index and working tree disagreeing*, and
   converted 178 files whose blobs are legitimately CRLF. Caught by `git
   status`, reverted byte-for-byte from the index under a guard that refused any
   file differing by more than line endings — 177 restored, 0 refused. The real
   lesson is narrower and is now on the record: **Python's text mode rewrites an
   LF-blob file to CRLF on this platform**, so every `write_text` to a tracked
   file is an `EOL-01` violation waiting to happen. It happened again later on
   `docs/CLOSE_RULING.md`, where it buried a 51-line edit inside an 866-line
   diff until the endings were restored.

## `ENACTED`

**`OBS-01` — an inherited obstruction is re-tested before it is re-asserted.**
Full text `docs/RULES_ENACTED.md`. A finding whose status asserts impossibility
carries the *check* that establishes it and the generation that ran it; a
citation of the ruling that assigned the status is not a check.

Guard `tests/test_inherited_obstructions_g11.py`, with both controls: a planted
bare impossibility is caught, and a planted `last_tested` whose `check` is a
document reference is caught — that being the plausible failure, not the
malformed one. The positive control is that a real named check passes, which
would fail if the predicate rejected everything. Its recorded limitation — the
rule reaches statuses, not note prose — is **measured** by
`test_the_widened_predicate_is_measured_to_over_fire`, which runs the rejected
widening over the real findings and requires it to over-fire, rather than
asserting that it would.

## `LADDER`

**Climbed, `L2` → `L1`.** Not descended from, and **no unreachability verdict
was issued in this generation** — none was available, and the pilot is what took
`U-BUDGET` off the table for the only item where it was plausible.

`L1` is *every spine item on full coverage; `MECH-01` stated as an open question
with its narrowing measured*. Coverage is 1.000 on all three sets. `MECH-01`'s
narrowing was measured at the close and is unchanged: not *why does the window
set the rank* but **why does widening the bias window compress the sensitivity
spectrum toward its own leading direction**.

**`L0` is not reached and is not declared unreachable.** It needs `MECH-01`
answered and no open `HIGH` outside `ACCEPTED-PERMANENT` / `OPERATOR-BLOCKED`.
After the two status corrections above, `PROV-03` and `PROV-07` are both exempt
by the rung's own words, so **`MECH-01` alone is the distance to `L0`**. One
method has failed; `U-EMPIR` needs three by distinct methods, so no verdict is
available and none is written.

## `NEXT`

**`MECH-01`, by a second and distinct method: the observation side.**

It beats the alternatives because it is the only remaining item on the ladder.
`PATH-01` is larger scientifically — it is what would convert both `d=16`
searches into separations — but it needs a string solver or nudged elastic band,
and it changes no rung: `L0` does not mention it. `CI-01` and `PROV-07` are
reserved. `CHART-03` and `SPEC-11` are `MEDIUM` and move nothing on the spine.

The method, named precisely so that it is not a re-run of the failed one.
Generation 10 tested the **column** side — whether the leading right singular
*vector* localises over parameters — and falsified it. The second method is the
**row** side: which *bias points* carry `σ₂…σ₄`, and whether the points a
widening window adds are the ones that carry them. Same artefacts, different
axis, and a different way to be wrong.

`SR-3`, the devil's advocate against the candidate this generation promotes —
*chart L is refined, and the dimension reading rests on three covered sets*:

> The strongest case that it is wrong is that **coverage is not the thing the
> reading needs**. Refinement tests whether a pair is still a witness. The
> dimension reading is a claim about **barrier depth** at matched `d`, and every
> depth is an upper bound along a straight line. Full coverage removed eleven
> pairs whose status was doubtful and left the bound direction exactly where it
> was — so a reader could take "all three sets refined" as though the `d=16`
> results had been strengthened as *separations*, which they have not been.
> Worse, the eleven that went were the shallow ones, which *deepened* the median
> from 212 to 223 floor units: the number moved in the flattering direction for
> a reason that is bookkeeping, not physics.

Answered, and the answer is not a caveat. The claim promoted is coverage and the
classification's stability under it, and nothing else; the depth is stated as an
upper bound in the recount artefact, in the register's own
`what_full_coverage_does_not_mean`, and in a guard
(`test_the_recount_carries_the_bound_direction`) that fails if the bound
direction stops being carried. The median's rise is reported in
`docs/G11_RESULT.md` §1.4 **as bookkeeping** — *it does not make the basin a
stronger result: a basin is a statement about pairs that are witnesses, and
eleven of them turned out not to be.* And the thing that would settle it is
named rather than gestured at: **the minimum-energy path**, `PATH-01`, still not
computed and still out of scope.

## `PREMISES`

What this ruling rests on that has not itself been measured.

1. **The refinement battery is the right instrument for "is this still a
   witness".** Three grids and two tolerances, inherited from generation 6 and
   never independently justified. A pair that survives `N = 1201` might not
   survive `N = 4801`. Nothing here tests the battery's own sufficiency; `D1`
   tests only that it is deterministic.
2. **`WIT-01` admissibility is vacuous on all three sets** (ratio 1.000), so
   *admissible* is currently carrying no weight anywhere, and a set where it bit
   would behave differently.
3. **The chart-L reproduction control is weaker than chart G's**, and cannot
   detect a defect that was already present when `outputs/g8/reproduce.json` was
   written. Stated in the scope object, not discovered later.
4. **The commit map is trusted as `filter-repo`'s honest output.** `V2` checks
   it against commit messages, which is independent — but if `filter-repo` had
   mapped two commits onto one target, `V2` could still pass on both. Not
   checked; the map is injective in fact, and that it *must* be is not
   established here.
5. **`concordance` is the right way to state the headroom premise as a
   predictive claim.** It is a defensible choice, made after seeing that chart
   L's bands overlapped, and it is not pre-registered. The sign of the effect
   does not depend on it — spearman agrees — but the *number* 0.479 does.
6. **Reserved items are assumed to remain reserved.** `PROV-07`'s exemption from
   `L0` rests on `git push` being the human's. If that changes, `L0`'s distance
   changes with it.

---

# `RULING g12` — the pre-push audit, and a discriminator killed by its own control

**Written** 2026-08-28, under the operator ruling of the same date that answered
the reserved item. **Ladder** `LADDER.md`, unedited, hash unchanged.
**Measurement** `docs/G12_RESULT.md`.

---

## `RATIFIED`

**The push runbook ran in full, and the push did not.** Five of six steps pass.
Step 2 is clean on every pattern — the rewrite achieved exactly what it was for,
so provenance was not broken for nothing. Step 3 passes and reorders the story:
the `commit-msg` hook was installed at **09:06:36**, ten minutes *before* the
09:16:38 rewrite, so the two were not alternatives and the ruling's concern that
the rewrite was done *instead of* the hook does not hold. Step 4 passes on a
distinction worth stating: the remote's only ref is the one commit `filter-repo`
mapped **to itself**, so the push is a plain fast-forward of a new branch and no
force is required or would be.

**`MECH-01`'s second method reproduced its object exactly.** 72 of 72 singular
values bit-identical to generation 9. Whatever else this generation did or did
not establish, it was operating on the Jacobian generation 9 measured.

**`PILOT-01` was applied the same generation it was enacted**, and it worked in
the direction it was meant to: the row-side measurement was priced at 7.9 s per
cell before anything was decided about it, so no plausibility argument was
available.

**`OPS-02`'s first run recovered what the reserved-item report had to assemble
by hand**: hook 09:06:36, rewrite 09:16:38, remote 09:20:50 — three operator
actions inside fifteen minutes, none detected for a generation. It also reports
what an in-repository check structurally cannot: a hooks path outside the tree,
and a reflog shorter than the history.

## `CORRECTED`

Six. The first is mine, made inside this generation, and it is the one that
matters.

1. **My own pre-registered discriminator did not discriminate, and its own
   control proved it.** The row-side method registered a **sign** —
   `NEW_ROWS` iff the trailing directions sit further outside the core window
   than the head — and it returned `NEW_ROWS` at 16 of 16 width cells. `C1`
   then returned the same sign at **16 of 18 cells of the spacing axis**, where
   `SPEC-g9-2` measured the rank as not moving at all.

   A statistic that fires just as readily on the axis where nothing happens is
   describing a property these Jacobians have generally, not detecting an
   effect. **The verdict is void as a verdict.**

   What was done about it is the part I want on the record: the pre-registered
   verdict is **left standing, unedited**, in
   `outputs/g12/mech01_rows/verdict.json`. Rewriting the classification rule
   after seeing the control is precisely the violation pre-registration exists
   to prevent, and the fact that the rewritten rule would have produced a
   *weaker* claim does not make it permissible.

2. **The ruling's §3 diagnosis is corrected.** Three line-ending incidents do
   mean the fix is incomplete, but not in coverage: **350 of 350** tracked files
   resolve to `attr/-text`, every generation-11 and -12 module included, and `*
   -text` is a wildcard that cannot miss a class. `-text` binds **git**.
   Incidents 2 and 3 were both **tools** — Python's text mode rewriting an LF
   blob as CRLF on `win32` — which no `.gitattributes` can prevent. The
   incomplete half is the tool side, and generation 11's fix was local to its own
   scripts with nothing enforcing it.

3. **The ruling's §1.6 regex could not find what §1.6 is for.**
   `/(home|Users)/[a-zA-Z0-9_.-]+` is forward-slash only: 8 hits, all the known
   `SW-18a`. Extended to Windows separators, **67 occurrences across 12 files**,
   ten of them added by *this loop* in generation 11's own manifest. `SW-18a`
   was recorded as two manifests; it is twelve files.

4. **Step 5's premise does not hold, and the finding is the absence.** The
   ruling asks whether the preservation copies hold pre-rewrite objects and says
   that if so they are the only independent record. Neither copy contains a
   `.git` at all, and the archive zip is the **pre-loop** repository. No
   pre-rewrite object survives anywhere. `docs/COMMIT_HASH_MAP_g11.json` is
   therefore not the bridge to an independent record — it **is** the record, the
   sole surviving trace of ten generations' pre-rewrite identity, on one disk.
   This makes step 1 more urgent than it reads, not less.

5. **`.gitattributes` states counts about the tree that nobody re-measures.**
   Its comment says the index holds 119 CRLF, 74 LF and 2 mixed; measured now,
   **178, 157 and 2**. Stale by growth rather than wrong in kind, and the
   argument the comment makes does not depend on them — but a number in a
   document nobody re-derives is the exact surface `DOC-07` objects to.
   Recorded rather than edited, because rewriting a line-ending policy file to
   fix its own prose is the risk that file describes.

6. **I under-specified `all_controls_pass` in my own instrument.** It gates on
   `R1`, `N1` and `P1` and *not* on `C1` — so the artefact reports
   `all_controls_pass: true` for a run whose control axis invalidated its
   verdict. The flag is accurate about the three it names and misleading about
   the run, and it is left as produced with this correction beside it rather
   than recomputed.

7. **The `DOC-07` guard I restored caught me, in the generation that restored
   it.** `tests/test_commit_messages_g7.py` had been silently skipping since the
   rewrite; generation 11 restored it through the correction map; this is the
   first generation in which it has run. It failed on this generation's own
   repair commit `f00b6a0`, whose message asserts a spelled-out count of
   something the suite measured.

   `R-4` and the operator ruling's *"without exception"* both forbid amending
   it, so the violation is permanent. It is **parked and quoted**, not erased
   and not excluded by moving the guard's range, which would be the drift
   `IA-2` exists to catch. The parking fails in both directions: a parked entry
   must still offend, so it doubles as a history-rewrite detector.

   I would rather record this than any of the successes above. A guard reported
   green for a generation while not running, was repaired, and immediately
   found a real defect in the repairer's own work.

## `ENACTED`

Three, all from the ruling, each with a guard and both controls
(`docs/RULES_ENACTED.md`).

* **`OPS-02`** — Phase A audits the operator's actions.
  `tests/test_operator_actions_g12.py`. The negative control is *an audit that
  runs and reports nothing*, which is the plausible failure for a detector
  rather than the malformed one, and it is what a detector looks like after
  someone has made it stop complaining.
* **`PILOT-01`** — a measurement is never declined on a plausibility argument.
  `tests/test_pilot_first_g12.py`. Its negative control plants the closing
  ruling's own sentence about chart L. It also forces the state file to carry
  `declined_measurements` even when empty, so that a generation has to say out
  loud that it declined nothing.
* **`SKIP-01`** — a skip is a failure unless it carries a reason and an expiry.
  `docs/SKIP_REGISTER.json`, `scripts/report_skips.py`,
  `tests/test_skip_register_g12.py`. Its negative control plants the exact skip
  text that hid `HIST-01` for a generation and requires the guard to catch it.

## `LADDER`

**`L1` held.** Not climbed, not descended, and **no unreachability verdict was
issued or was available**.

`L0` needs `MECH-01` answered. It is not, and the count of failed methods is
**one, not two**. The row-side method was *inconclusive as pre-registered* — the
hypothesis was not falsified, the discriminator was too blunt — and a sharpened
version is the same method with a better statistic. Counting it as a second
failure would be inflating the count toward a `U-EMPIR` verdict, which is the
cheapest way to finish and the thing §2 of the directive exists to make
unavailable.

## `NEXT`

**`MECH-01`, third pass: the magnitude statistic, pre-registered, against new
cells.**

Priced at 7.9 s per cell. It needs *new* cells — a third device, or a held-out
axis — because a statistic cannot be pre-registered against data already seen,
and re-reading this generation's 36 cells with a statistic chosen from them
would be the same error dressed as a fix.

`SR-3`, the devil's advocate against what this generation promotes — *the width
axis carries a row-side concentration three times anything on the control axis,
peaking where the rank climbs*:

> The strongest case against it is that the comparison is between a **maximum**
> and a **maximum** over nine points each, with no distributional model and no
> pre-registered threshold. A ratio of 3.1–3.5× between two sample maxima drawn
> from curves with ranges 0.21 and 0.08 is not obviously outside what two
> unequal-variance curves would produce. Worse, the width curve's peak sits at
> 0.15 V — the *second* point on the axis — and a peak at the second of nine
> points is exactly where a boundary artefact would sit: at width 0.10 the core
> window and the measurement window are the **same set**, so `n_out = 1` of 16
> and the statistic is nearly degenerate there by construction. The rise from
> 0.10 to 0.15 may be that degeneracy relaxing rather than physics arriving.

Answered, and the answer is the next generation's first clause rather than a
rebuttal. The `n_out = 1` degeneracy at the narrowest width is real and is
visible in the artefact; it is why the pre-registered rule excluded the
narrowest window from the verdict in the first place. But it does **not**
explain the decay from 0.15 to 0.75, where `n_out` grows monotonically and the
statistic weakens — the opposite of what a shrinking-denominator artefact would
do. What would settle it: the same statistic computed with the core window
**held out of the measurement window entirely**, so no cell shares rows with the
reference. That is measurable, it is cheap, and it is registered here as the
third pass's first clause rather than argued about now.

## `PREMISES`

1. **The left singular vectors are the right object for "where a direction
   lives".** `|U[:,k]|²` over rows is a natural reading and it is not the only
   one; row leverage, or the influence of deleting a row on `σ_k`, would answer
   a related question differently and neither was computed.
2. **The reference core window is the right null.** It was fixed by
   `SPEC-g9-2` rather than chosen here, which protects against tuning but does
   not make it correct — and §`NEXT` names the specific way it may be biased.
3. **`N1` at ρ = −0.583 against a 0.7 bound is a pass.** It is, by the
   pre-registered rule, and it is the least comfortable margin in this
   generation. One Haar draw per width bounds gullibility; it does not estimate
   a null.
4. **The commit map is trusted as `filter-repo`'s honest output**, unchanged
   from generation 11 and now load-bearing for more: with no pre-rewrite objects
   surviving anywhere, nothing can cross-check it except the commit messages,
   which `V2` already uses.
5. **`git ls-remote` reflects the remote's real state.** One read, unauthenticated,
   at one moment. If the remote gains refs before a push, step 4's conclusion
   changes and must be re-run rather than recalled.
6. **The home-path count is a property of the tracked tree, not of what a
   reader would see.** 67 occurrences is what `git grep` finds; a published
   repository also exposes commit metadata, and that was checked separately
   (`Raar1999@users.noreply.github.com`) rather than assumed to be covered.
