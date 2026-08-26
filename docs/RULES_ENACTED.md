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

The rule generalises past ranks. `bayespinn_inv.inverse.modes.count_basins`
reports a **basin count** the same way, over a threshold grid, because a cluster
count is also an integer obtained by thresholding a continuous structure.
