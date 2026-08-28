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
