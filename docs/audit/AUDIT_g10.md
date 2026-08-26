# AUDIT g10 — the rule that did not reach its defect, and two premises that did not survive

Companion to `docs/G10_RESULT.md`, which carries the science. This carries the
findings about the loop itself: where a ruling's premise did not survive contact
with the tree, where a guard caught its own author, and where a rule was enacted
against a defect it turns out not to reach.

---

## 1. The ruling's own falsifier for `SPEC-g10-2` is inverted

**The text.** The ruling of 2026-08-26 §5 states the clause and its falsifier:

> **SPEC-g10-2 — Ridge/basin disambiguation** per §3: barriers on the chart-L
> d=16 witnesses, matched d against chart J.
> *F:* chart L d=16 sits at the floor like chart G d=4, which would make the
> ridge/basin split a dimension effect rather than a chart effect and rewrite §3.

**Why it is backwards.** Three cells are in play: chart G at `d=4` (ridge), chart
J at `d=16` (basin), and the new cell, chart L at `d=16`.

| chart L `d=16` comes out as | the split then separates | which axis is that |
|---|---|---|
| **RIDGE** | {G `d=4`, L `d=16`} against {J `d=16`} | **chart** — two charts at one `d` disagree, and `d=4` and `d=16` sit on the same side |
| **BASIN** | {G `d=4`} against {L `d=16`, J `d=16`} | **dimension** — the only ridge is the low-dimensional cell |

The ruling assigns the *dimension* reading to the *ridge* outcome. It is the
other way round: an outcome that puts `d=4` and `d=16` on the same side of a
split is exactly what a dimension effect cannot produce.

**How it was handled.** The correction is written into
`RidgeBasinDecision`, hashed as `88748b9f…`, and recorded in
`outputs/g10/preregister.json` **before the third witness set was measured**. A
correction to a ruling's logic that arrives after the number is indistinguishable
from a reading of the number; one that arrives before it, with a hash, is not.
The measurement then returned BASIN, so the dimension reading is the one that
holds — under the corrected table, not the ruling's.

**Why this matters beyond bookkeeping.** §6 of the same ruling proposes a paper
spine whose item 4 is *"Its geometry is not universal: a ridge at the instrument
floor in one chart, isolated basins at 59× the floor in another."* That sentence
is now withdrawn: both `d=16` charts are basins. What replaces it is in
`docs/G10_RESULT.md` §6 and is two statements rather than one.

---

## 2. The premise `WIT-01` was ordered on does not hold

**The text.** The ruling §2, reviewing generation 9:

> **g9-3.** … The pairs that separate under refinement are those whose junctions
> were nearly coincident — 0.4 nm apart, rising 195% — which is sub-grid and was
> never a witness.

**Measured** against `outputs/g9/junction_refine.json`, node spacing 3.333 nm:

| | junction separations (nm) |
|---|---|
| the 7 pairs that **survive** refinement | 26.6, 41.7, 63.2, 177.1, 178.4, 249.5, 422.9 |
| the 6 pairs that **separate** under refinement | 0.4, 3.4, 9.0, 196.2, 246.2, 412.2 |

One of the six is sub-node. The other five separate with junctions up to 124
nodes apart, and the surviving set includes pairs at 26.6 and 41.7 nm — closer
than four of the six that separate. Junction separation does not predict
refinement survival.

**What does.** Sorted by observational distance at `N=301`, survival is exactly
the seven smallest against the six largest: the largest surviving distance is
`0.01844`, the smallest separating one `0.01873`, against a floor of `0.02`. Four
of the six cross the floor on a relative move of 1.2%–7.9%, the same size as
moves seen in survivors (`+4.8%`, `+5.6%`). Only two rises are large on their own
terms — `+195%` at 0.4 nm and `+29%` at 9.0 nm, both within three nodes — and
those two are the genuine discretisation artefacts.

**Consequence for the rule.** `WIT-01` admits **all thirteen** chart-J pairs,
including the 0.425 nm one, because every one of them qualifies on a magnitude
coordinate. So the rule would not have prevented the generation-9 finding it was
enacted in response to. This is recorded rather than smoothed over: the rule is
still worth having — it is what stands between a future chart with a quantised
coordinate and a published count of its own grid — but the loop should not
believe it closed a hole it did not close.

---

## 3. `WIT-01` as literally worded is unimplementable, and the reading is stated

> A pair whose separation along **any coordinate** falls below the grid
> resolution is not a witness.

Taken literally: two chart-J devices sharing a junction have a junction
separation of exactly zero, which is below any positive resolution, so the rule
rejects them. They are a perfectly good witness — the generation-8 headline pair
survives the literal reading only by accident of where its junctions happen to
sit. The literal rule deletes most of the witness set it was enacted over.

The reading taken is stated in full in
`src/bayespinn_inv/inverse/witness_admissibility.py` and reproduced in
`docs/G10_RESULT.md` §3.1: the rule applies to the separation that **qualifies**
the pair. Coordinates separated by a nonzero but unresolved amount are counted
and reported separately rather than being treated as either, which is where the
0.425 nm junction separation is caught.

`OPS-01` is why this is in the tree rather than in a reply: a rule that lives
only in a ruling does not exist, and a rule whose implementation silently differs
from its wording is worse than one that does not exist.

---

## 4. A guard caught its own author, twice, in the same module

### 4.1 The prose citation pattern passed three documents for the wrong reason

The first version of `_ADMISSIBILITY_CITATION` in
`tests/test_witness_admissibility_g10.py` accepted a bare `admissible`. Three
claim-surface documents — `docs/CLAIM_EVIDENCE_MATRIX.md`, `docs/G8_RESULT.md`
and `docs/G9_RESULT.md` — contain the phrase *"the best of the two **admissible**
projections"*, which is a statement about collocation and has nothing to do with
witness admissibility. All three passed the guard while carrying witness counts
with no ratio anywhere near them.

Caught by inspecting *why* the passing documents passed, rather than by trusting
that they did. The pattern now requires `WIT-01`, `admissibility ratio`,
`admissible under WIT-01`, or the artefact path, and
`test_an_unrelated_use_of_the_word_admissible_does_not_satisfy_it` pins the exact
phrase so the loophole cannot reopen. A measured false negative, not a
hypothetical one.

### 4.2 The positive control would have passed whatever the rule did

`SW-20` requires a planted violation the guard must catch. The obvious plant for
`WIT-01` is two chart-J devices whose junctions differ by a fraction of a node —
and it is worthless, because a junction coordinate difference that small is below
`min_separation_decades` and the **separation criterion** rejects the pair before
`WIT-01` is consulted. The control would have reported "rejected" if `WIT-01` had
been deleted entirely.

The construction that actually tests the rule uses the logistic's saturated tail,
where `dx_j/ds` has collapsed: at `s ≈ 4` a **0.4-decade** move in the junction
coordinate — comfortably past the criterion — shifts the junction by 0.06 nm and
leaves it inside the same node interval. The control now asserts the rejection
**reason**, not merely the rejection, and the same repair was applied to negative
control 3 in `scripts/run_g10.py`, which had the same defect.

A control that passes for the wrong reason is worse than a missing control,
because it reports that the guard works.

---

## 5. `DOC-07`'s widened guard fired on a live message again

The first draft of the generation-10 machinery commit message asserted five
spelled-out counts — `three committed witness`, `one node`, `Three witness`,
`one module`, `five findings`. `tests/test_commit_messages_g7.py` rejected it
before the commit was built on, and the message was rewritten.

This is the second live catch (generation 9's machinery message was the first),
and both were on the same author's own message. `R-4` makes a commit message
uncorrectable once built on, so a guard that fires at commit time is the only
remedy that exists for this class.

---

## 6. `EOL-01` fired on this session's own edits

Four claim-surface documents and one module were edited through a Python helper
whose default newline translation rewrote LF blobs as CRLF in the working tree
and appended LF lines to a CRLF module. `tests/test_line_endings_g6.py` caught
all five: `i/lf w/crlf` on the documents, `i/crlf w/mixed` on
`src/bayespinn_inv/inverse/identifiability.py`.

The `.gitattributes` policy is `-text` — never convert — precisely so that a
checkout returns the bytes that `PRESERVE_MANIFEST_g0.sha256` attests. The
working tree was restored to match each blob rather than the blobs normalised,
which is what the policy requires and why the finding stays `OPEN` rather than
being closed by a bulk rewrite.

---

## 7. `DOC-03a` — the test-count badge and the row disagreed, and the badge's own wording is loose

**The row.** `README.md`'s capability table read *"Test suite | **678 passing**"*.
The suite has not collected 678 tests for several generations; the badge at the
top of the same file said 734 before this generation and is checked against live
collection by `tests/test_notebooks.py::TestDocumentedTestCountIsHonest`. So the
file contradicted itself, and the half a guard maintained was not the half a
reader met first.

The row now points at the badge rather than restating a total. Removing an
unguardable number is a better repair than updating it, because updating it
guarantees the same drift next generation — the same argument `DOC-07` makes
about commit messages.

**The badge, newly recorded as `DOC-03a` (LOW, OPEN).** The badge reads
`tests-N%20passing` and the guard compares `N` against **collection**, not
against passes. The suite currently collects more than it passes, because some
tests skip with a stated reason. The number is therefore honest as a *collected*
count and loose as a *passing* one. Changing the badge text would break the
guard's own regex, so the gap is recorded rather than papered over, and the
sub-counts beside it (58 solver-numerics, 27 MOS-cap physics, 41 ohmic-gradient)
were re-derived from live collection and are correct.

---

## 8. The two halves of the claim surface disagreed about a bound direction

`LOOP_STATE_v6.json` records, as generation 9's second remaining scientific
risk, that the barrier metric walks a straight line in chart coordinates so
*"every barrier reported is an **upper** bound on the true barrier -- a curved
path can only be shallower."* That is correct: the barrier is
`max(endpoints) - min(path)`, and a path that dips less shallowly has a higher
minimum and therefore a smaller barrier, so the true barrier is at most the
straight-line one.

`docs/CLAIM_EVIDENCE_MATRIX.md` §"What I1-I6a do not establish" said **lower**,
in the same sentence, with the same justification attached. One document had it
right and the other had it backwards for a generation, and the justification
clause was identical in both, which is how it survived reading.

Corrected in place with the correction marked. The direction is not cosmetic:
it is favourable for the ridge result, which says barriers are low, and
unfavourable for both basin results — including the chart-L basin this generation
uses to reclassify the split. Recorded here because a wrong statement of a
bound's direction is exactly the class of error that survives review, being one
word in a sentence everybody agrees with.

---

## 9. `CI-01` — the cost review this generation owes

`CI-01` is `ACCEPTED-PERMANENT` by the default the generation-8 ruling set, and
the status requires its cost to be reviewed for growth each generation rather
than remembered. The cost is the unevidenced surface: the static support-floor
scan can only falsify a floor, never confirm one, and it cannot see dependency
resolution at all; nothing in this repository has ever run on linux or darwin.

The scan's file count is the measurable part of that surface and is recorded in
`LOOP_STATE_v7.json` under `python_support_floor_scan`, with the generation-7 and
generation-9 values beside it so the direction is visible. Generation 10 adds
source modules, so the surface grows again. `docs/OPERATOR_TASKS.md` OT-1 stands
unchanged and records the reversion condition: if a remote is added, the status
reverts and the cost statement is superseded forward rather than deleted.

---

## 10. What this generation did **not** audit

* **The remaining falsifiers.** `FALSIFIER-01` opened at generation 8 — no
  falsifier in this repository had been audited for the defect that
  `run_witness_falsifier.py` re-derived chart G by hand. Generation 9 exercised
  the refinement battery and found it live. Generation 10 exercised the barrier
  metric and the chart discriminator through their controls, which is evidence
  they are live but is not the audit. Still `PARTIALLY-ADDRESSED`.
* **`WITNESS-04`.** The generation-7 chart-L native search has still never been
  re-checked at `N=1201`. Generation 10 used its 37 pairs for barriers, which
  does not test the pairs against refinement. The finding is unchanged, and it is
  now load-bearing for `SPEC-g10-2`: if some of those 37 separate under
  refinement, the chart-L basin classification is measured over a set that
  includes non-witnesses. The direction of that error is not obvious and is not
  guessed at here.
* **`SPEC-11`'s cell-keyed denominators.** `tests/test_claim_surface_g7.py` still
  reads licensed denominators from `outputs/g8/ranks.json`, which generation 9
  identified as the wrong key — the licence is a property of the
  `(chart, d, device, bias window)` cell. Not taken here either.
