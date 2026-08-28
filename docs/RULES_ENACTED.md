# Rules enacted by operator ruling

Append-only. Rules referenced throughout this repository — `PH-*`, `SW-*`, `DOC-*`,
`AH-*`, `R-*`, `SK-*` — originate in operator rulings, which are not files in this
tree. Most were absorbed as behaviour and cited at their point of use.

That worked until generation 7 wrote `SW-20` into three source files and a reader
had nowhere to look it up. A rule that exists only in a message is unenforceable
and, once the message scrolls away, unrecoverable. This file is where enacted
rules land from now on, with the defect that motivated each one and how it is
enforced.

Rules enacted **before** generation 7 are not backfilled here: reconstructing them
from citations would be inventing text and attributing it to the operator. They
remain cited at their points of use, and `RULE-01` in `docs/audit/AUDIT_g7.md`
records the gap.

---

## `SW-20` — a guard over source code is written over the AST

**Enacted** operator ruling, 2026-08-25 §3.5.

> A guard whose subject is source code is implemented over the AST, never over
> characters, and excludes its own source and the documentation describing it
> from its search scope. Every guard ships with **both** controls: a planted
> violation it must catch, and prose describing the violation it must not fire
> on.

**The defect that forced it.** Generation 6 shipped four guards that could not
fire. `docs/audit/AUDIT_g6.md` §5 generalises them as one class rather than four
slips. The clearest instance: a guard searching for the string `def bernoulli`
matched *its own pattern literal* the moment it was committed, so it reported a
violation of itself forever and its authors learned to ignore it.

A character scan cannot distinguish code from prose *about* code. An AST walk can,
because prose is not in the AST.

**Enforced by**

| guard | subject | AST? | controls |
|---|---|---|---|
| `scripts/check_python_support_floor.py` | source code | yes — `ast.parse` and a `NodeVisitor` | `tests/test_python_support_floor_g7.py`: one planted violation per detector, plus a module whose *text* contains every pattern it searches for and whose *code* uses none of them |
| `tests/test_claim_surface_g7.py` | prose | n/a — there is no AST for prose | the letter does not apply; the purpose does. Both controls implemented, own source and explanatory documents excluded from scope, and the exclusion asserted rather than trusted |

The second row is the honest reading: `SW-20`'s mechanism is specific to code, its
*purpose* — a guard must be shown to fire, and shown not to fire on descriptions
of what it forbids — is not.

---

## `DOC-07` — a commit message never asserts a measured count or metric

**Enacted** operator ruling, 2026-08-25 §3.5.

> Commit messages never assert a measured count or metric. They reference the
> manifest or artefact that carries it. A count in a commit message is a claim on
> an unguardable surface.

**The defect that forced it.** Commit `1a090f0` asserts `420 passed` in its
message. The tree it committed produced 437 passed and 1 failed. Under `R-4` a
commit message cannot be corrected, so the false claim is permanent; `d3b7693`
corrects it forward, and `docs/gen/DECISIONS.md` records why that is the only
available remedy.

A commit message is the one surface in this repository that no test can fix after
the fact. The rule removes the class of claim that would need fixing.

**Enforced by** `tests/test_commit_messages_g7.py`. The guard scans commit
messages created after the rule was enacted and rejects assertions of the form
"N passed", "N tests", "N of M passing". Its positive control is `1a090f0` itself:
the guard must flag that message, and the test fails if it does not — which also
proves the guard is not vacuous. History before the enactment commit is out of
scope, because `R-4` makes it uncorrectable and a guard that fails on
uncorrectable history is a guard people disable.

---

## `OPS-01` — a rule that lives only in a ruling does not exist

**Enacted** operator ruling, 2026-08-26 §7, *against the operator*.

> Every rule I enact lands in `docs/RULES_ENACTED.md` **with a guard and both
> controls, in the generation it is enacted**, or it is not enacted. Retro-apply
> to `PH-22`, `SW-20`, `DOC-07`, and now `REP-01`, `SPEC-11`'s rank-curve rule,
> and `OPS-01` itself.

**The defect that forced it.** Generation 7 audited the rulings and found that
`SW-20` and `DOC-07` — both cited in source files, both treated as binding — had
never existed anywhere but in chat text. `RULE-01` in `docs/audit/AUDIT_g7.md`
records that finding. `OPS-01` is its generalisation from *those two rules* to
*the mechanism that produced them*: the operator's rules had no home in the tree,
so of course some of them had no home in the tree.

**Enforced by** `tests/test_rules_enacted_g8.py`. The guard parses this file,
extracts every `##`-level rule heading, and asserts that each one carries an
**Enacted** provenance line, a **defect** section, and an **Enforced by** line
naming a test module that exists and contains both controls. Its positive control
plants a rule section with no guard and requires the parser to reject it; its
negative control is this paragraph, which describes the forbidden shape without
being it.

**Scope, stated rather than assumed.** This file is not a complete list of the
rules this repository obeys. Rules enacted before generation 7 — `PH-*`, `AH-*`,
`R-*`, `SK-*` and most of `SW-*` — are cited at their points of use and their
original wording is not in the tree. Reconstructing them and attributing the
reconstruction to the operator would be worse than the gap. `PH-22` below is the
one exception the ruling names, and it is marked for what it is.

---

## `PH-22` — dtype is part of a measurement, and the two paths are not interchangeable

**Enacted** before generation 7; backfilled here at generation 8 by operator
ruling §7.

> **Provenance warning, and this is the honest form of the backfill.** The
> operator's original wording of `PH-22` is not in this tree. What follows is
> **reconstructed from its points of use** — nine call sites across
> `inverse/charts.py`, `inverse/identifiability.py`,
> `inverse/global_identifiability.py` and `tests/test_dtype_envelopes_g6.py` —
> and is therefore a description of the rule as the code obeys it, not a quotation
> of the rule as it was issued. It is recorded in this weaker form because
> inventing text and attributing it to the operator is the failure mode this file
> exists to prevent. `OPS-01` cannot be satisfied retroactively for a rule whose
> text was never written down; it can only be satisfied going forward.

As the code obeys it:

> A published identifiability number is arbitrated on the float64 NumPy oracle
> path and on no other. The float32 surrogate path may propose and may not
> arbitrate. Every function states which path it is on, and the two are reported
> with separate envelopes rather than averaged, compared or substituted.

**The defect that forced it** (as recorded at the points of use). Doping
differences below about `1e-7` relative are not representable in float32, while
the float64 oracle round-trips at `1.678e-16`. A global identifiability study
probes exactly the directions in which two profiles differ least, so arbitrating
one on the float32 path would manufacture indistinguishability out of arithmetic.
`GRAD-01` is the independent second reason: surrogate directional derivatives
agree with the oracle **only inside** the identifiable subspace (mean cosine
`+0.504` inside, `-0.001` outside, unchanged by a 33× training-budget increase),
which is precisely not where a global study looks.

**Enforced by** `tests/test_dtype_envelopes_g6.py`, which measures both
round-trips and asserts the separation, and by `SPEC-g6-5`'s standing
requirement that the oracle-arbitrated scripts never import the surrogate. The
generation-8 additions inherit it: `bayespinn_inv.inverse.modes` is float64
throughout and calls nothing else.

---

## `REP-01` — a representation error states the method that produced it

**Enacted** operator ruling, 2026-08-26 §1.

> Every representation, embedding, projection, or approximation error states the
> method that produced it, in the same table cell or sentence as the value. Where
> more than one method is admissible, the reported value is the best admissible
> one, and the ordering is pinned by test.
> `test_projection_is_at_least_as_good_as_collocation` is the model; generalise
> it.

**The defect that forced it.** The generation-7 ruling's headline — *"the
published local analysis was conducted in a chart blind to the degeneracy"* —
rested on one figure: witness member b embeds into chart L at **146% of the
instrument floor**, i.e. outside it. The figure was arithmetically correct and
came from a **collocation** embedding. Under least-squares projection followed by
refinement in observation space the same member reaches **2.2%** of the floor: a
factor of **67**, on the same object, decided by a method the number did not
carry. The headline was withdrawn in full, and the fault was split — one party
supplied a number without its method, the other built on it without asking.

**Enforced by** `tests/test_rep01_g8.py`. The guard sweeps every committed
measurement artefact and fails on any JSON object that reports a
representation-shaped error without naming a method **in that same object** —
the machine-readable form of "the same table cell". Its positive control is the
withdrawn g7 table row stripped of its method; its negative control is a record
whose *text* contains the forbidden key names inside prose and whose *structure*
does not report them.

`TestTheBestAdmissibleMethodIsTheOneReported` pins the ordering clause against
the g7 artefact: for each witness member, the method the artefact calls best must
be the best, and must beat collocation.

### Amendment, generation 9 — the same rule, applied to the state file

**Enacted** operator ruling, 2026-08-26 §3.

> Apply `REP-01` forward to the whole baseline block, not just this field:
> **every number in a state file carries its invocation.**

**The defect that forced the amendment.** `LOOP_STATE_v5.json` recorded
`"ruff_exit": 0`. The field carried no scope and no command, and the two
defensible scopes disagreed: `ruff check .` exited **1** with findings in
`notebooks/` while `ruff check src tests scripts` exited **0**. One verdict was
recorded and two existed.

The field beside it was supposed to be the good example, and it is not quite one
either. `"mypy_findings": 25` came with the note *"25 over the tracked tree"*.
That scope is wrong: 25 is what `mypy src` reports over 44 files. Over the
tracked tree — `mypy src tests scripts`, 112 files — it is 150. The number was
right and the sentence describing it was not, which is exactly what an
invocation prevents and a prose note does not: a command can be re-run, a
description can only be re-read.

So the rule generalises off representation errors. A baseline number
approximates the tree in the same sense a projection approximates a profile: it
depends on a method, and quoting it without the method makes it unfalsifiable.

**Enforced by** `tests/test_loop_state_g9.py`. Every entry in the state file's
`baselines` block must be an object carrying a non-empty `invocation` and at
least one number, and for records marked rerunnable the guard **runs that
invocation** and compares the recorded verdict against what the command returns
today — so a baseline goes stale loudly rather than quietly. Measurements that
cannot be re-run inside the suite — the suite's own wall clock, which cannot
measure itself — carry `conditions` and `measured_at_commit` instead, and both
are asserted present and non-empty, because a timing number without its
conditions is the same defect wearing a stopwatch. Its positive control plants
the literal `{"ruff_exit": 0}` and requires rejection; its negative controls are
a note whose *prose* contains the word "invocation" without carrying one, which
must be rejected, and a correctly formed block, which must not be.

The finding-count comparison is version-gated and says so when it skips: a count
moves with the analyser, and a guard that fails on an upgrade is a guard someone
deletes.

**What the guard found on its first run**, recorded because a guard's first run is
the only unbiased one it ever has: **three** generation-7 artefacts violate
`REP-01` — `containment.json` (4 records), `spectra.json` (4 records) and
`manifest.json` (the same 8, embedded). Under `R-4` a committed artefact is not
rewritten, so they are listed in `PRE_ENACTMENT_VIOLATIONS` with the method that
actually produced each number, read out of the code that ran. The list is
asserted **exactly**, which makes it a guard on those files rather than an
amnesty for them: a new violation there fails, and so does quietly repairing one.

---

## `SPEC-11` rank-curve rule — a rank is a curve over cutoffs, not an integer

**Enacted** operator ruling, 2026-08-26 §5.

> Every rank is reported as **rank(cutoff)** over the range of defensible
> cutoffs, with the spectrum, the chosen cutoff, and whether that cutoff sits in
> a population gap. A bare integer rank appears only where a gap justifies it —
> which today means `d=4` only.

**The defect that forced it.** Generation 7 measured the identifiable rank in
four `(chart, d)` cells and, in doing so, measured where the operational cutoff
sits relative to the spectrum's largest multiplicative gap. At `d = 4` it sits
inside the gap (×7.39 in chart G, ×17.46 in chart L); at `d = 16` it does not
(×4.99 and ×5.12, cutoff outside). So "3 of 4" separates two populations of
singular values and "4 of 16" applies a threshold to a smooth decay. They are
different kinds of object, and six generations quoted them in the same voice.
`PH-11` forbids a tuned cutoff; this extends it to the case where the cutoff is
not tuned and the *rank* is still not a property of the spectrum.

**Enforced by** `bayespinn_inv.inverse.identifiability.rank_cutoff_record`, which
is the only way generation-8 machinery reports a rank, and
`tests/test_rank_curve_g8.py`. The record carries the spectrum, the curve over the
inherited `NOISE_GRID`, the operational cutoff, the largest gap and whether the
cutoff is inside it, the plateau of noise levels over which the rank does not
move, and a `bare_integer_rank_justified` flag that is `False` unless the gap
criterion is met. The gap criterion itself is **inherited unchanged from
generation 7**, which is what keeps `AH-14` clean: it cannot have been chosen
after seeing the generation-8 cells.

The guard's positive control is a synthetic spectrum with a clean decade gap at
the cutoff, which must be flagged justified; its negative control is a smoothly
decaying spectrum, which must not be — and a guard that flagged both would be
worthless, so both directions are asserted.

**Also enforced on the prose**, because a rule about how a number is reported has
to reach the documents that report it.
`tests/test_claim_surface_g7.py::TestEveryUnlicensedRankCarriesItsCutoff` fails
when a rank fraction whose denominator has no measured population gap appears in
a passage that does not carry a cutoff. The licensed set of denominators is read
from `outputs/g8/ranks.json` rather than written into the test, so re-measuring
the cells moves the guard with them. On its first run it found three live
instances — one in `README.md`, one in `docs/RELEASE_READINESS.md` and a table
header in `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md` — all now carrying their cutoff.
Its negative control is the *not to be written* list in
`docs/CHART_RECONCILIATION_g7.md`, which quotes the forbidden shape in order to
forbid it; the exemption is keyed on prohibition vocabulary and deliberately
excludes "not comparable", so a disclaimer cannot buy a bare rank past the guard.
A second control asserts exactly that.

The rule generalises past ranks. `bayespinn_inv.inverse.modes.count_basins`
reports a **basin count** the same way, over a threshold grid, because a cluster
count is also an integer obtained by thresholding a continuous structure.

---

## `WIT-01` — a separation the representation cannot carry is not a witness

**Enacted** operator ruling, 2026-08-26 §4 (post-G9).

> A pair whose separation along any coordinate falls below the grid resolution
> is not a witness and is excluded **before** counting, not filtered afterwards
> by refinement. State the admissibility ratio and apply it to every existing
> witness count.

**The defect that forced it.** Generation 9 put all thirteen chart-J witness
pairs through the generation-6 refinement battery and six of them separated. One
of the six had junctions **0.425 nm** apart on a grid whose node spacing is
**3.333 nm**. `ChartJ.reconstruct` places the sign flip with `x_si < x_j`, so
those two junctions build the same profile bit for bit; the 0.425 nm was a
property of the grid and had been published as a property of a device.
Refinement caught it, but refinement is the wrong instrument for the job — it
costs three oracle solves per bias per pair, and it fires after the number is in
print. The chart could have said it for free, before the count existed.

**What the rule turned out to mean, which is not what it was expected to mean.**
Read literally — *reject the pair if any one coordinate is separated by less than
its resolution* — the rule rejects almost every real witness, including the ones
it exists to protect: two chart-J devices sharing a junction are separated by
exactly zero in that coordinate, and they are a perfectly good witness. So it is
implemented on the separation that **qualifies** the pair: admissible iff some
coordinate is separated by at least `min_separation_decades` *and* that
separation is resolved by the reconstruction.

Applied that way it removes **nothing**. Every witness pair in this repository
qualifies on a magnitude coordinate, magnitude coordinates reach the grid exactly
through `charts._lerp`, and the admissibility ratio is `1.000` in all three
charts — chart G at `d=4` 13/13, chart L at `d=16` 37/37, chart J at `d=16`
13/13. `WIT-01` is, on today's chart inventory, a **chart-J rule with no live
instance**. That is the result, and it is exactly why the ratio has to be stated
rather than assumed: "the rule does not bite here" and "the rule was never
applied here" are different sentences, and only the first one is checkable.

What the rule *does* catch is a reported **quantity** rather than a count. One
chart-J pair's junction separation of 0.425 nm is a difference the representation
does not carry, and it should never have been quoted as a junction separation at
all.

**Enforced by** `bayespinn_inv.inverse.charts.Chart.coordinate_resolution` and
`Chart.separation_is_resolved`, which put the resolution on the *chart* rather
than in a search — the base class returns zero for every magnitude coordinate and
`ChartJ` overrides the junction with an exact node-index test — and
`tests/test_witness_admissibility_g10.py`, which guards the predicate and the
prose together. Its positive control plants a pair whose only qualifying
separation is a 0.06 nm junction move inside one node interval, built in the
logistic's saturated tail so that it reaches the 0.3-decade criterion and is
still sub-node; the rule must reject it, and must reject it *for the stated
reason* rather than by failing the separation criterion first. Its negative
controls are the headline 694 nm / 271 nm pair, which must be admitted, and a
pair sharing a junction, which must also be admitted. On the prose side, a
claim-surface document quoting a witness count must point its reader at the
ratio; the citation pattern deliberately does not accept a bare "admissible",
because three documents contain *"the best of the two admissible projections"* and
the first version of the guard passed all three on that phrase — a measured false
negative, now pinned by its own control so it cannot reopen.

**The premise it was ordered on does not hold, and that is recorded rather than
quietly dropped.** The ruling states that the chart-J pairs which separate under
refinement "are those whose junctions were nearly coincident — 0.4 nm apart …
which is sub-grid and was never a witness". Of the six that separate, **one** has
a sub-node junction separation. The other five separate with junctions 9, 196,
246 and 412 nm apart, and pairs that *survive* include separations of 26.6 nm and
41.7 nm. Junction separation does not predict refinement survival;
`outputs/g10/wit01.json` carries the table and `docs/G10_RESULT.md` §3 carries
what does.

---

## `WIT-02` — every witness is refined before it is counted

**Enacted** closing operator ruling of 2026-08-26 §2.

> Every witness is refined before it is counted. Not the ones near the floor —
> all of them. `WIT-01` stays for the sub-grid case it does catch.

**The defect that forced it.** `WIT-01` was enacted against a defect it does not
reach. Retro-applied to every committed set it removes **nothing** — the
admissibility ratio is 1.000 in all three charts — because every pair qualifies
on a doping magnitude and magnitude coordinates reach the grid exactly. It
admits all thirteen chart-J pairs including the one whose junctions are 0.425 nm
apart on a 3.333 nm grid, because that pair qualifies elsewhere.

What actually predicts which pairs separate under refinement is **headroom
against the distinguishability floor**. The 7 survivors are exactly the 7
smallest distances at `N=301`, maximum `0.01844`; the 6 that separate are the 6
largest, minimum `0.01873`; the floor is `0.02`. A perfect split with no
geometry in it at all.

**Why there is no threshold, and why the absence is the point.** The obvious
rule to write from that split is a margin band — refine anything within some
percentage of the floor. The operator declined it, and the reason is arithmetic:
the observed boundary sits between **92.2%** and **93.65%** of the floor, a gap
of 1.4 percentage points. That is not `BUG-13`'s eleven orders of magnitude. A
threshold chosen inside a band that narrow is tuned by construction, whatever
its author intended, and `PH-11` forbids it. Refining every witness needs no
threshold to defend, and the cost is known to be affordable: thirteen pairs went
through the battery inside one bounded generation.

**What the rule gets at close, which is a register and not compliance.**
Refining the uncovered pairs is new solving. The closing ruling §5 permits
arithmetic on existing artefacts only and orders a stop, and there is no
generation 11. So `WIT-02` is enacted with its non-compliance **measured and
published** rather than enacted and quietly violated:

| global witness set | witness pairs | refined | surviving |
|---|---|---|---|
| **chart G**, `d = 4` | 13 | **3** (23.1%) | 3 of 3 |
| **chart L**, `d = 16` | 37 | **0** (0.0%) | — |
| **chart J**, `d = 16` | 13 | **13** (100%) | 7 of 13 |

One set of three is compliant. The uncovered one is the set the dimension
reading rests on (`WITNESS-04`, raised to load-bearing at generation 10), and
the one set that *was* refined in full lost 6 of 13 members.

**Enforced by** `scripts/run_close.py::wit02_register`, which builds
`outputs/close/wit02_register.json` by matching each refinement record to its
witness pair on **exact equality** of the separation in decades against
`WIT-01`'s `max_separation` for the same set — so coverage is measured and
"three of the thirteen" is a fraction rather than a recollection — and
`tests/test_witness_refinement_close.py`, which re-derives every coverage figure
from the source artefacts, refuses to let a set become compliant without a named
artefact covering every offered pair, and requires each claim-surface document
quoting a witness count to point at the register.

Its positive control plants a separation one nanodecade off a real one and
requires the match to fail, because a coverage figure built on approximate
matching could be counting another set's pairs. Its prose control is the same
shape as the one `WIT-01`'s guard needed: the citation pattern deliberately does
not accept the bare word *refinement*, since grid refinement of the
discretisation is discussed throughout this repository and has nothing to do
with witness coverage — and it was then widened once, on a measured false
positive, to accept `docs/G8_RESULT.md`'s *"7 of which survive grid refinement"*,
where the intervening word had made a real witness-refinement statement
unquotable.

**What enacting it changed.** Four claim-surface documents quoted a witness
count with no coverage beside it, and one of them — `README.md` — said *"all
tested pairs survive 4× grid refinement"* of a set in which 3 of 13 pairs had
ever been tested. That sentence is true and reads as its opposite. It is the
reason the rule is worth having even though it closes nothing: before `WIT-02`,
"not refined" and "refined, fine" were the same sentence on the claim surface.

---

## `DOC-08` — no bare universal quantifier over a filtered set

**Enacted** operator ruling of 2026-08-28 §3.

> No bare universal quantifier over a filtered set. "All tested X" is written
> "n of N X tested, all surviving". Every count carries its denominator; every
> metric carries its scope.

**The defect that forced it.** `README.md` said *"all tested pairs survive 4×
grid refinement"* of a set in which 3 of 13 pairs had ever been tested. The
sentence is **true and reads as its opposite**, which is what makes the class
worth naming: no reviewer catches it, because nothing in it is false.

It is the third instance of one family, not a third slip. The other two are the
generation-8 baseline's bare `"ruff_exit": 0`, which carried neither scope nor
command and so said nothing about which paths were linted, and the same
baseline's `mypy_findings: 25`, which carried a *stated* scope that was the
wrong one — 25 is `mypy src` over 44 files, and the tracked tree is 150. Each
was found by a different generation looking for something else. **The family is
a quantifier or metric stated without its denominator or scope, where the
natural reading is the false one**, and it had already cost three findings when
the rule was written.

**What the sweep found.** Three live instances on the claim surface, all of the
same postmodifier shape the flagship sentence has:

| document | sentence | population |
|---|---|---|
| `docs/CLOSE_RULING.md` §5 item 3 | *"survives refinement in every chart tested"* | two of the three committed witness sets had been through the battery; chart L never has |
| `docs/G10_RESULT.md` §7 item 3 | the same sentence | the same |
| `docs/G9_RESULT.md` §1 | *"at every operating point tested"* | twelve |

All three were in a **spine item or a headline**, which is where the family
concentrates: the sentence that compresses a result is the sentence that drops
the denominator. The generator was fixed too —
`scripts/run_witness_falsifier.py` capped its loop at `pairs[:3]` and wrote the
verdict *"all tested pairs survive grid refinement and a tighter tolerance"*.
The cap is now an argument that defaults to every offered pair, and the verdict
reads *"n of N pairs tested; all n survive"*.

**Enforced by** `tests/test_quantifier_scope_doc08.py`, over
`CLAIM_SURFACE_G10` plus `docs/CLOSE_ADDENDUM.md`. Two arms: a universal
quantifier attached to a set marked as selected by having been *tested*,
*refined*, *examined* and the rest, in a unit stating no denominator; and a
`mypy`, `ruff` or `pytest` count on the claim surface with neither its
invocation nor its scope, which is `REP-01`'s rule for the state file applied to
prose.

Its positive controls are the real defects rather than proxies: the exact
`README.md` sentence for the first arm, and both of the operator's two examples
for the second — `"ruff_exit": 0`, and a `mypy` count of 25 quoted with no
scope beside it, where the tracked-tree scope gives 150 over 125 files. Its negative controls
are the statement of `WIT-02` itself (*"every witness is refined before it is
counted"*, which is the forbidden shape and is also the sentence enacting the
forbidding), a prohibition list quoting the pattern, and a measured false
positive: `docs/CHART_RECONCILIATION_g7.md`'s *"each direction probed **by** an
object drawn in its own source chart"*, which describes a method and asserts
nothing about a subset. That sentence was flagged by the first version of the
pattern and is why a participle followed by an agent is excluded.

**Its second arm overlaps an existing guard, and the overlap is deliberate.**
`tests/test_mypy_scope_g10.py` already enforces the same scope requirement for
`mypy` alone, enacted at generation 10 under `REP-01`. `DOC-08`'s arm generalises it to `ruff`
and `pytest` and states the class; the `mypy` guard is narrower, has the better
error message for its own case, and stays. Two guards firing on one sentence is
a cost worth paying over a class that has produced three findings — and the
overlap was measured, not assumed: writing this section tripped the generation-10
guard on the sentence quoting the defect.

**What it does not reach, measured rather than assumed.** A count spelled as a
word with no denominator — *"All three pairs put through the falsifier
survived"*, where the population is thirteen — is an instance of the family and
the patterns do not catch it. `test_a_worded_count_is_a_recorded_limit_of_this_guard`
pins that limit so it stays visible. The widening that would catch it also
catches *"admissibility ratio 1.000 in all three charts"*, where three **is** the
population, and a guard demanding "3 of 3" there is a guard about typography.
The sentence itself was repaired by the sweep; the class it belongs to is
recorded as open.


---

## `OBS-01` — an inherited obstruction is re-tested before it is re-asserted

**Enacted** generation 11, 2026-08-28, under fused operator authority
(`RULINGS.md`, ruling `g11`).

> A finding whose status asserts that something **cannot** be done is a claim
> about the tree. It carries the check that establishes it and the generation
> that ran that check, and a generation that re-asserts it without re-running
> the check is making a claim it did not test.

**The defect that forced it.** `HIST-01` was carried for three generations as
`OPEN, PRE-EXISTING, UNREPAIRABLE FROM INSIDE THE TREE`. The repair was
`.git/filter-repo/commit-map`, a file that had been sitting in this repository
since before the finding was last restated. Nobody ran `ls .git`. Eight guards
failed and three more silently skipped — including the `DOC-07` commit-message
guard, which was therefore not running over the range it was written to police —
for want of a check nobody performed because the impossibility had already been
written down. `docs/HIST01_REPAIR_g11.md`.

**It is the second instance of the class, and the first was already named.**
`docs/CLOSE_RULING.md` §5.1 recorded `DOC-03a` one generation earlier: the
README badge that generation 10 recorded as unchangeable, which turned out to be
changeable in one line, because *nothing had ever tried it*. That section drew
exactly the right conclusion —

> An obstruction inherited from an earlier generation is a claim about the tree,
> it is exactly as checkable as any other claim about the tree, and this loop
> found that they were not being checked.

— and then did not enact anything, so the next generation inherited a larger
instance of the same defect. `OPS-01` says a rule that lives only in a ruling
does not exist; this is what happens when a *finding* that should have been a
rule is left as prose.

**What it requires.** Any open finding in a `LOOP_STATE` file whose `status`
asserts impossibility — the words `UNREPAIRABLE`, `UNRESOLVABLE`, `IMPOSSIBLE`,
`CANNOT`, `PERMANENT`, `BY-CONSTRUCTION` — must carry a `last_tested` object:

```json
"last_tested": {
  "generation": 11,
  "check": "the command or inspection that was actually run",
  "result": "what it returned"
}
```

Not a citation of the ruling that assigned the status. **The check.** A status
whose evidence is another document asserting the same status is the thing this
rule exists to stop.

**Enforced by** `tests/test_inherited_obstructions_g11.py`, over the current
state file, with both controls: a planted finding asserting impossibility with
no `last_tested` is caught, and a planted finding carrying one whose `check`
merely cites a document rather than naming a command is also caught. The
positive control is that the real findings pass, which would fail if the
predicate matched nothing.

**What it does not do, stated so it is not over-read.** It does not require the
check to be *cheap*, or to be re-run every generation — `PROV-03` and
`REPRO-01` are genuinely permanent and re-running their checks proves nothing
new. It requires that the check exist, be named, and be attributable to a
generation that ran it, so that a reader can see the difference between *tested
and impossible* and *never tried*. `HIST-01` sat in the second category while
reading like the first.

**A measured limitation.** The rule reaches statuses, not prose. A finding whose
`status` is `OPEN` while its `note` argues at length that nothing can be done is
not caught, and `CHART-03` is close to that shape. Widening the predicate to
note text was tried and rejected: it fires on every note that *describes* an
impossibility it does not assert, including this rule's own entry. Recorded as a
limit rather than papered over.

---

## `OPS-02` — Phase A audits the operator's actions on the repository

**Enacted** operator ruling of 2026-08-28 §1, after the reserved-item report.

> An operator action on the tree is an unattested change to the object of study.
> Phase A audits `git remote -v`, `.git/config` mtime and its commit-defining
> settings, `.git/hooks/` **and** `core.hooksPath`, `filter-repo` artefacts, and
> reflog head movement not attributable to the loop's own commits.

**The defect that forced it.** On 2026-08-28 the operator ran `git filter-repo`
at **09:16:38** and added a remote at **09:20:50**. The loop noticed neither
until generation 11 went looking — nine hours and one whole generation later. In
between, the close addendum ran and closed while eight guards were failing on
hashes the rewrite had renamed, three more were silently skipping for the same
reason, and `CI-01` was carried as `ACCEPTED-PERMANENT` on the premise that no
remote would ever exist, while a remote existed.

This loop was built on the premise that unattested changes to the object of
study get detected. They were not.

**Why `core.hooksPath` is named explicitly.** The `commit-msg` hook that strips
attribution trailers lives at `~/.git-hooks`, outside the repository. `ls
.git/hooks` reports nothing, and a repository-local check would conclude no hook
is installed while one is running on every commit. A surface that is only
visible from outside the repository is exactly the surface an in-repository
audit misses.

**Enforced by** `tests/test_operator_actions_g12.py`, over
`outputs/g12/operator_actions.json` produced by
`scripts/audit_operator_actions.py`. Both controls: a planted audit missing one
of the five surfaces is caught, and a planted audit whose `filter_repo` surface
reports absent while `.git/filter-repo/` exists is caught — that being the
plausible failure, an audit that runs and reports nothing.

**What it deliberately does not do.** It does not judge whether an operator
action was correct; that is the operator's authority, and a detector that
editorialised is a detector people switch off. It records *what changed*.

**A measured limitation.** It cannot see actions that leave no trace — a file
edited and reverted, a config set and unset, a hook installed and removed
between generations. The artefact says so in `what_it_cannot_see` rather than
implying completeness.

---

## `PILOT-01` — a measurement is never declined on a plausibility argument

**Enacted** operator ruling of 2026-08-28 §2.

> Either a measurement is priced by pilot and then declined on `U-BUDGET` with
> the number, or it is run. *"It will not change the answer"* is a prediction,
> and predictions are cheap where the measurement is cheap.

**The defect that forced it.** Chart L's 37 witness pairs were published as a
`WIT-02` gap across three generations, and the closing ruling declined the
measurement on the argument that a basin at 212 floor units cannot become a
ridge. The reasoning was right about the outcome and **irrelevant to the
decision**: the pilot came out at 7.5 s per pair and the run took 288 seconds.
Nobody had measured what a five-minute measurement cost.

The operator recorded this as the ninth operator error and the shape of it is
worth keeping: a plausibility argument about the *result* was used to settle a
question about the *cost*.

**How it interacts with `U-BUDGET`.** The unreachability standard already voids
a budget verdict that carries no measured pilot. `PILOT-01` closes the other
half: without it, a measurement could be declined with no verdict at all, simply
by never being proposed. The rule makes the pilot the precondition of the
decision rather than of the verdict.

**Enforced by** `tests/test_pilot_first_g12.py`. Any measurement a state file
records as declined, deferred or out of scope must carry a `pilot` block with a
measured number and the invocation that produced it. Both controls: a planted
decline whose justification is a plausibility argument with no pilot is caught,
and a planted decline carrying a real pilot passes — the latter would fail if
the predicate rejected everything.

**A measured limitation.** It reaches declines that are *recorded*. A
measurement nobody proposes is invisible to it, and chart L was in that state
for two of its three generations. The rule shortens the gap; it does not close
it.

---

## `SKIP-01` — a skip is a failure unless it carries a reason and an expiry

**Enacted** operator ruling of 2026-08-28 §3.

> The suite reports skip counts with reasons in the same line as passes, and any
> guard that skips is reported as not guarding.

**The defect that forced it.** `HIST-01` made eight guards fail and **three
skip**. The eight were loud. The three were not, and two of them were
`tests/test_commit_messages_g7.py` — the guard that polices `DOC-07` — which
had stopped running over the range it was written for because its helper turns a
non-zero `git` exit into `pytest.skip`. A green suite reported that as green.

The operator placed it in the same family as a positive control that passes
whatever the rule does: **a failing guard is loud, a skipping guard reports
green**, and the second is the more dangerous of the two.

**What it requires.** Every skip the suite emits is registered in
`docs/SKIP_REGISTER.json` with the reason pattern, why the skip is legitimate,
and an **expiry** — the condition or generation after which it is a finding
rather than a skip. An unregistered skip is a failure. An expired registration
is a failure.

**Enforced by** `tests/test_skip_register_g12.py`, over
`outputs/g12/skips.json` produced by `scripts/report_skips.py`, which runs the
suite and records every skip with its reason. Both controls: a planted
unregistered skip reason is caught, and a planted registration whose expiry has
passed is caught. The positive control is that the real skip set passes, which
would fail if the matcher matched nothing.

**Why the register is a file and not a decorator.** A `reason=` string already
exists on every skip in this repository and none of them was enough — the two
`DOC-07` skips carried a perfectly clear reason, in `git`'s own words, and still
went unnoticed for a generation. The reason was never the missing part. What was
missing is a place where the *set* of accepted skips is written down, so that a
new one has to be added deliberately.

---

## `EOL-02` — every text-mode write states its line ending

**Enacted** operator ruling of 2026-08-28 §5.

> Every text-mode write states its line ending explicitly — `open(p, "w",
> newline="\n")`, or `newline=""` where a writer manages its own.

**The defect that forced it.** The line-ending category had bitten three times,
and the operator's diagnosis is the part worth keeping: **`.gitattributes` binds
git, not the interpreter.** `tests/test_line_endings_g6.py` proves a checkout
returns the committed bytes, and that guard is sound and stays. It says nothing
about the bytes this project *writes*. Both recent incidents were on that side —
Python's text mode translates `"\n"` to `os.linesep` on write, so on Windows a
bare `open(p, "w")` or `Path.write_text(s)` emits CRLF while the author reads the
source and sees LF. The artefact then differs by platform, and a hash over it
differs with it.

Nothing in `.gitattributes` can reach that, because the file never goes through
git on the way out. Only the call site can.

**The rule is explicitness, not LF.** `newline=""` is what `csv` requires, since
its writers emit CRLF themselves and would double it under any translation. Two
call sites in this tree — `scripts/run_benchmark_sweep.py` and
`scripts/run_inverse_sweep.py` — already relied on exactly that, predate the rule
and pass the guard unchanged. A test asserts they still open that way, so a later
mechanical rewrite cannot quietly turn their `newline=""` into a line feed.

**Enforced by** `tests/test_eol02_line_endings_g13.py`, over the AST per `SW-20`,
with both controls: a planted module whose code performs both forbidden writes is
caught, and a module whose *text* contains every construct the scan looks for and
whose *code* contains none of them is not. Its own source is excluded from scope
and the exclusion is asserted rather than trusted — and, separately, the scan is
run over this module's own AST to show that the exclusion is not what is saving
it.

**What the enactment changed.** 68 call sites across 41 files in `src/`,
`scripts/` and `tests/`. All 68 were text-mode writes with no explicit newline;
none was a csv writer.

**A trap found while enacting it, and worth recording.** The first mechanical
pass added the keyword correctly and then wrote every file back through Python's
text mode, turning 25 CRLF files into LF — 9,832 lines changed to fix 68.
`.gitattributes` is `* -text`, so the CRLF/LF mixture in the index is the
committed truth, and `test_line_endings_g6.py` records it deliberately as *what
was measured*. The enactment was redone over bytes, preserving each file's
existing endings, asserting per file that its CRLF and LF counts are unchanged.
**A rule about line endings is exactly the rule most likely to damage line
endings while being applied.** What caught it was reading the diffstat, not the
guard, which went green either way.

**The same trap, twice more, in this document.** Writing this section through a
shell heredoc collapsed four backslash escapes into real line breaks, and one of
them put a literal CR into a file that is LF in the index — `git ls-files --eol`
reported `w/mixed` and `test_line_endings_g6.py` failed on the very document
describing the rule. It is the `OPS-03` shape again: the artefact that describes
a line-ending rule is unusually good at violating it.

**A measured limitation.** The scan reaches `open` (including `Path.open`) and
`Path.write_text` — the constructs through which this tree opens a text stream
for writing. Writers that own their handle end to end and never expose a mode —
`DataFrame.to_csv`, `numpy.savetxt`, `Figure.savefig` — are out of scope, because
the rule reaches call sites and those are not call sites where a line ending can
be stated. A `mode=` computed at runtime rather than written as a literal is also
invisible to it; there is none in the tree today.

---

## `DIFF-01` — a mechanical edit states its blast radius before it runs

**Enacted** operator ruling of 2026-08-28 §5 (the pass-4 ruling).

> Any mechanical or sweep edit states its expected changed-line count before it
> runs. A result exceeding the expectation by more than 2× halts the edit and is
> reported, regardless of whether the suite is green. Applies to normalisations,
> codemods, and rule enactments — the three places where correct-per-file and
> catastrophic-in-aggregate are the same operation.

**The defect that forced it.** The `EOL-02` enactment's first pass changed
**9,832 lines to fix 68** — 145× its own intent. It added the keyword correctly
at every one of the 68 call sites and then wrote every touched file back through
Python's text mode, normalising 25 CRLF files to LF. `.gitattributes` is
`* -text`, so that mixture is the committed truth and
`tests/test_line_endings_g6.py` records it deliberately as *what was measured*.

**The suite was green before the sweep and green after it.** That is the whole
point. Every file was individually correct; the damage existed only in
aggregate, and no guard in this repository measured aggregate. What caught it
was a reviewer reading the diffstat — a person, not a mechanism, and the
operator's word for that is the right one: a guard that passes a change two
orders of magnitude larger than its intent is not measuring blast radius.

**Why a ratio and not a line count.** Blast radius is relative to intent. A
three-line edit that touches forty lines is an incident; a four-thousand-line
edit that touches four thousand two hundred is not. A guard keyed to an absolute
count would miss the small-but-runaway case, which is the more common one.

**Enforced by** `docs/SWEEP_REGISTER.json` and
`tests/test_diff01_blast_radius_g14.py`.

A register nobody updates guards nothing — that is `SKIP-01`'s lesson, and
`SKIP-01` avoids it by comparing its register against the skips the suite
actually emits. There is no equivalent signal for "a sweep happened", so this
guard manufactures one from git: **a commit touching at least ten files is
sweep-shaped** and must appear in the register by subject. Hand edits are deep
and narrow; codemods are shallow and wide, and the file count is that signature.

Both controls ship: a planted overrun that did not halt is caught, and a sweep
that stayed within its estimate is not flagged — the second matters because a
guard that rejects everything also looks correct. A third control asserts the
threshold is a ratio rather than a count, by exhibiting one case of each kind.

**Scope**, following `DOC-07`'s own design: commits before the enactment commit
are out of scope, because `R-4` makes history uncorrectable and a guard that
fails on history nobody can fix is a guard people switch off. The generation-13
`EOL-02` sweep is registered as the founding entry and doubles as the guard's
**positive control from history** — the detector must still identify it as
sweep-shaped, and if it stops doing so the detector has gone vacuous.

**A measured limitation.** The file-count trigger is a proxy. A mechanical edit
confined to nine files is invisible to it, and a wide hand edit will be flagged
and need a register entry saying it was not mechanical. The first is the real
gap and it is stated rather than papered over: the rule reaches the *shape* of a
sweep, not its intent, because intent is not visible to a test.
