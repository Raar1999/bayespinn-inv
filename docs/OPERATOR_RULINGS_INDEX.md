# OPERATOR_RULINGS_INDEX — the rulings, the corrections against them, and the operator's own defects

**Ordered by** the operator handoff of 2026-09-07, §6 · **Date** 2026-09-07
**Not a generation.** No `LOOP_STATE` increment, no ladder movement, no spec.
**Sources** `RULINGS.md`, `docs/AUDIT_MASTER.md`, the generation result and audit
documents, `docs/RULES_ENACTED.md`, `docs/gen/DECISIONS.md`,
`docs/OPERATOR_TASKS.md`, and the `g15` paper documents. Every row below names
the tree file it is read from. **Nothing here is reconstructed**: where the tree
does not hold something the handoff asked for, this document says so and stops.

---

## 1. What this document can and cannot be

The loop's reasoning is in the tree, generation by generation. The operator's is
not. Operator rulings arrive as messages and are **not files in this
repository** — `docs/RULES_ENACTED.md` says so in its own opening paragraph, and
that gap is the defect `OPS-01` was enacted to close going forward. Everything
recoverable about a ruling is therefore a *citation of it* by a document that
acted on it.

Three consequences, stated before the tables so nothing below is read as more
than it is.

**(a) This is an index of citations, not a transcript.** Where a ruling is
quoted in the tree the quotation is reproduced with its source. Where it is only
cited, the entry says what the citing document says the ruling ordered, and
nothing else. No ruling text is reconstructed from its effects — the prohibition
`OPS-01`'s scope paragraph states for pre-generation-7 rules applies to this
document in full.

**(b) Section numbers collide, and the tree cannot always tell the rulings
apart.** Several rulings share a date and are cited only as *"the ruling of
`<date>` §N"*. §2 of some 2026-08-28 ruling authorised the close addendum's
bounded refinement; §2 of some 2026-08-28 ruling enacted `PILOT-01`. §3 of one
enacted `DOC-08`; §3 of one enacted `SKIP-01`. These are not the same section and
the tree does not disambiguate them beyond the descriptive names the result
documents attach — *the reserved-item ruling*, *the pass-4 ruling*, *the
`PROV-08` / `CI-02` / `MECH-01` pass 3 ruling*. §2 below uses those names where
they exist and marks the collisions where they do not. This is itself a finding
about the record and is stated in §5.

**(c) The eighteen operator defects are not in the tree.**
`docs/PAPER_FINAL_g15.md` §2 establishes it in as many words: *"The operator
numbers their own defects in the rulings, and the tree does not hold that
list."* Two carry their number here — the ninth and the eighteenth — and a
further set are recorded as operator errors without one. §4 gives what exists.
The remaining numbers are absent, and the handoff's instruction is to omit rather
than reconstruct, so they are omitted.

---

## 2. The rulings, in date order

### 2026-08-25 — the ruling that started the loop

**Recorded at** `docs/AUDIT_MASTER.md` §9; `docs/gen/DECISIONS.md`, whose title
line is *"Decision ledger — autonomous decisions under the operator ruling of
2026-08-25"*.

**What it decided, as the tree records it.** It authorised the audit loop and the
autonomy under which generation 0 ran. Its first product was the loop's first
finding: the repository's only commit was the **pre-audit** project, and both
prior audit cycles existed solely as uncommitted working-tree state
(`PROV-06`; adoption commit `c115757` on `loop/champion`, parent `6577f4b`).

### 2026-08-25 — the generation-6 ruling

**Recorded at** `docs/audit/AUDIT_g6.md`, whose section headings are the ruling's
own clause numbers; `docs/REPRO01_LEAF_AUDIT_g6.md`; `docs/WINDOWS_RISK_g6.md`;
`docs/gen/DECISIONS.md` `DEC-g7-2`; `docs/RULES_ENACTED.md`.

| clause | what it ordered | where the work is |
|---|---|---|
| §3.1 | the `REPRO-01` leaf audit | `docs/REPRO01_LEAF_AUDIT_g6.md`; `AUDIT_g6` §1, which concludes **generation 1 was wrong** |
| §3.2 | **exactly two outcomes and no third** on the 3.9 support claim: a green leg, or the floor moves and the claim is withdrawn | `DEC-g7-2` — the leg could not run, so the floor moved to 3.11 |
| §3.2a | execute CI locally and rank the Windows risks | `docs/WINDOWS_RISK_g6.md`; `AUDIT_g6` §4 |
| §3.4 | make the CRLF fix durable | `AUDIT_g6` §3 — `.gitattributes` pins `* -text`; the guard caught its own author |
| §3.5 | the `PH-22` retro-sweep; **and** the enactment of `SW-20` and `DOC-07` | `AUDIT_g6` §2 (negative result: no second `GRAD-02`); `docs/RULES_ENACTED.md`, which cites *"operator ruling, 2026-08-25 §3.5"* for both rules |

**One thing the tree does not settle.** `AUDIT_g6` reads §3.5 as the `PH-22`
retro-sweep and `RULES_ENACTED` reads §3.5 as the enactment of two rules. Both
citations are of a 2026-08-25 §3.5. Whether that is one clause carrying two
orders or two rulings sharing a date and a number cannot be told from the tree,
and it is not guessed at here.

### 2026-08-26 — the `G7-R` sequencing ruling

**Recorded at** `docs/audit/AUDIT_g7.md`; `docs/gen/DECISIONS.md` §*"G7-R
SEQUENCING"* → `DEC-g7-1`.

**What it decided.** Reconciliation only, against one commit, under a recorded
CI waiver. *"No new scientific scope was opened."* It also **withdrew its own §7
CI precondition as over-scoped** and corrected `SPEC-g7-2`'s interpretation
clause — two self-corrections inside one ruling, honoured at `DEC-g7-1`.

### 2026-08-26 — the post-generation-8 ruling

**Recorded at** `docs/audit/AUDIT_g8.md` §3, which escalates against four of its
clauses; `docs/RULES_ENACTED.md`.

| clause | what it ordered |
|---|---|
| §1 | `REP-01` — a representation error states the method that produced it |
| §4 | a model of `CHART-01` as *"two reconstruction operators for one coordinate vector"* |
| §5 | a bare integer rank is justified *"only where a gap justifies it — which today means `d=4` only"* |
| §7 | `OPS-01`, **enacted against the operator**: every rule lands in `docs/RULES_ENACTED.md` with a guard and both controls in the generation it is enacted, with `PH-22`, `SW-20`, `DOC-07`, `REP-01`, `SPEC-11`'s rank-curve rule and `OPS-01` itself retro-applied |
| §8 | a test asserting `champion` is never the commit that wrote the state file |
| §9 | five `SPEC-g8-N` clauses, each with a falsifier, and a mandatory negative control |

### 2026-08-26 — the post-generation-9 ruling

**Recorded at** `docs/audit/AUDIT_g9.md`; `docs/audit/AUDIT_g10.md`;
`docs/RULES_ENACTED.md`; `docs/OPERATOR_TASKS.md`.

| clause | what it ordered |
|---|---|
| §2 | promote a figure from the loop's own verification report — *chart G and chart L return currents 44% apart on the same coordinate vector* — into the table carrying the 2.8% spectral agreement |
| §3 | `REP-01` applied forward to the whole baseline block: **every number in a state file carries its invocation** |
| §4 | `WIT-01` — a separation the representation cannot carry is not a witness |
| §4 | *(a different ruling of the same date, per `OPERATOR_TASKS.md`)* the `CI-01` remote decision, whose stated default fired at generation 9 and made `CI-01` `ACCEPTED-PERMANENT` |
| §5 | `SPEC-11`'s rank-curve rule, and the `SPEC-g10-2` ridge/basin clause with its falsifier |
| §10 | *(per `OPERATOR_TASKS.md`, generation 8)* the correction that `OT-1` requires a remote to be added first |

The §4 and §10 rows are cited by `docs/OPERATOR_TASKS.md` as *"the ruling of
2026-08-26"* and cannot be assigned to the same ruling as the §2–§5 rows above
without inventing a mapping. They are listed and left unmerged.

### 2026-08-26 — the closing ruling

**Recorded at** `docs/CLOSE_RULING.md`; `docs/G10_RESULT.md` §§474, 502;
`docs/CLAIM_EVIDENCE_MATRIX.md`; `docs/RULES_ENACTED.md`.

**What it decided.** It **ended the technical work**. *"No generation 11. No
`S-5`, no `S-2`, no fourth chart, no minimum-energy path."* Its clauses:
§1 three corrections ratified; §2 `WIT-02` enacted — every witness is refined
before it is counted; §3 the barrier bound direction carried through the whole
claim surface, and the ridge result declared safe; §5 one free check; §6 the
spine, six items.

### 2026-08-28 — the operator directive that fused authority

**Recorded at** `LADDER.md`; `RULINGS.md`; `LOOP_STATE_v10.json`;
`docs/CLOSE_RULING.md`'s second amendment.

**What it decided.** It fused operator authority into the loop and replaced the
two-party arrangement with three instruments written down and hashed **before**
the data: the condition ladder `L0`–`L3` (`LADDER.md`, §7), the self-ruling
ledger (`RULINGS.md`, §8), and the unreachability standard `U-STRUCT` /
`U-INSTR` / `U-BUDGET` / `U-EMPIR` with `U-0` (§2). §6 reserves `git push` and
anything needing credentials by name. §8 instructs generation 11's Phase A.
`RULINGS.md`'s own preamble records what the fusion costs: *"a ruling written by
the party that produced the measurement is a weaker instrument than one written
by a party that did not."*

### 2026-08-28 — the close-addendum ruling

**Recorded at** `docs/CLOSE_ADDENDUM.md`; `docs/CLOSE_RULING.md`'s first
amendment; `docs/RULES_ENACTED.md`; `outputs/wit02_chartG/preregister.json`,
which carries the authorisation verbatim.

**What it decided.** §2 authorised **one** bounded refinement after the close —
chart G's ten unrefined witness pairs, the barriers recounted over what survives,
the register updated, **chart L excluded by name** — because `WIT-02`, the
operator's own rule enacted at close, had opened a coverage gap under the one
claim the closing ruling declared safe. §3 enacted `DOC-08` and ordered one sweep
of the claim surface against it.

### 2026-08-28 — the reserved-item ruling

**Recorded at** `docs/G12_RESULT.md`; `RULINGS.md` `RULING g12`;
`docs/RULES_ENACTED.md`; `LOOP_STATE_v11.json`.

**What it decided.** It answered the reserved item, gated `git push` on six
checks, ordered the line-ending fix re-verified, and approved `MECH-01`'s second
method with both outcomes stated first. Rules enacted: §1 `OPS-02` — Phase A
audits the operator's actions on the repository; §2 `PILOT-01` — a measurement is
never declined on a plausibility argument; §3 `SKIP-01` — a skip is a failure
unless it carries a reason and an expiry; §5 `EOL-02` — every text-mode write
states its line ending.

### 2026-08-28 — the `PROV-08` / `CI-02` / `MECH-01` pass-3 ruling

**Recorded at** `docs/G13_RESULT.md`, whose opening paragraph states the whole of
it.

**What it decided.** The pre-rewrite objects copied **before anything else**;
`EXT-04` frozen; the pull request and `EXT-05` reserved to the operator; and
`MECH-01`'s magnitude statistic de-confounded, pre-registered and tested out of
sample.

### 2026-08-28 — the pass-4 ruling

**Recorded at** `docs/G14_RESULT.md`; `docs/UEMPIR_MECH01_g14.md`;
`docs/RULES_ENACTED.md`.

**What it decided.** The archive question resolved with an accession/derivative
split; one last `MECH-01` method; `DIFF-01` enacted (§5) — a mechanical edit
states its blast radius before it runs; and, in `G14_RESULT`'s word,
*decisively*, **the terminal condition fixed before the method ran**.

### 2026-08-29 — the close ruling

**Recorded at** `docs/RULES_ENACTED.md` (`PRE-01`); `docs/OPERATOR_TASKS.md`
`OT-2`; `papers/CORRIGENDA_g6.md` `COR-1`; `tests/test_claim_surface_g7.py`.

**What it decided.** §3 enacted `PRE-01` — a pre-registration's outcome space is
checked before it is hashed. §4 **assigned the paper to the loop**, which lifted
`R-3` over `papers/**`; `COR-1` was applied the same day, the parked-instance
guard was replaced by putting `papers/draft.md` on the claim surface, and `OT-2`
was discharged after nine blocked cycles.

### 2026-08-29 — the close-out order, the close-out ruling, and the close-out query

**Recorded at** `docs/PAPER_WORK_g15.md` §1 (as *"close-out ruling … §§1–7"*);
`docs/PAPER_AUDIT_g15.md` and `docs/PAPER_RECOMMENDATIONS_g15.md` (as *"close-out
order … T1–T6"*); `docs/RULES_ENACTED.md` `AGE-01` (as *"close-out query"*);
`docs/OPERATOR_TASKS.md`, last three entries; `docs/WINDOWS_LEG_SCORED_g15.md`.

The tree gives this date **three different names and two numbering schemes**, and
does not say whether they are one ruling or several. Both schemes are listed.

| clause | what it ordered | where the work is |
|---|---|---|
| T1 | delegated `OT-1` to the loop by name, lifting `R-4`'s prohibition on `git push` and `SK-09`'s on network access for one command sequence | `docs/OPERATOR_TASKS.md`, *OT-1 executed* |
| T2 | reserved the `EXT-05` decision, then made it | `docs/OPERATOR_TASKS.md` `OT-3` — declined on cost, permanently |
| T3–T6 | the paper's readability audit, the reviewer simulation, the venue analysis, and the reserved half in a recommendations document | `docs/PAPER_AUDIT_g15.md`, `docs/PAPER_RECOMMENDATIONS_g15.md` |
| §1 | commit both documents and the `EXEMPT` entries, **having verified the suite fails without them** | `157a785` |
| §2 | do not make the repository public; check which billing state blocks CI | `docs/OPERATOR_TASKS.md`, final entry |
| §3 | score `WINDOWS_RISK_g6.md` against local Windows evidence; check `NB-02` by running the notebook step first | `docs/WINDOWS_LEG_SCORED_g15.md` |
| §4 | no 3.9 leg; the floor stays 3.11; nothing reopens | confirmed; one consequence — the *paper* still said 3.9 |
| §5 | call the venue | `docs/adr/ADR-0008` — a device **audience**, not a journal |
| §6.1–6.4 | figures, `F4` first; argue the 2% floor as a sensitivity; reorder §4.2 and the abstract; keep contribution 7's number and foreground it | `scripts/make_figures_g15.py`, `scripts/floor_sensitivity_g15.py`, `papers/draft.md` |
| §7 | source the related-work gaps and verify each | six references, each opened, each confirmed through Crossref |
| — | the close-out **query** | `AGE-01` enacted — an artefact encodes the rule set of its own date |

### 2026-09-02 — the final paper ruling

**Recorded at** `docs/PAPER_FINAL_g15.md` §1, which is the ruling's own ledger;
`docs/UNDERCLAIM_SWEEP_g15.md`.

| clause | what it ordered | state |
|---|---|---|
| §1 | record the four-PNG suggestion as the operator's own defect, the eighteenth | recorded |
| §2 | the figure finding into the paper's methods section, `COR-2` as the worked instance; the presence-check failure class beside `AGE-01`, **with no guard** | `papers/draft.md` §3.2; `FILL-01` |
| §3 | one bounded underclaiming sweep, **report only**, with `COR-3` as the positive control | `docs/UNDERCLAIM_SWEEP_g15.md`; the control appears |
| §4 | cite Natterer 1977 at the chart section's opening; state Wieland 2021 as a limitation and state that §4.3 is not subject to it | `papers/draft.md` §2.2(c), §3.2, §5 |
| §5 | confirm which section is 553 words; enter `find.exe` shadowing as `WINDOWS_RISK_g6.md`'s sixth rank | confirmed: the abstract, 551 words by this tree's counter; rank 6 entered |
| §6 | closed | — |

### 2026-09-07 — the handoff

**Recorded at** this document, `papers/CORRIGENDA_g6.md` `COR-4` and `COR-5`, and
the dated pointer appended to `docs/adr/ADR-0001`.

**What it decided.** §5.1 correct two overclaims contradicted by their own
artefacts; §5.2 correct the `1730×` equilibration figure at its two live sites,
**reporting the two residuals rather than the ratio**, with `ADR-0001` receiving a
dated pointer and nothing else; §5.3 the abstract, which stays blocked on the
venue; §5.4 the CI billing check, which is the operator's; §6 this document.

### After 2026-09-07 — the ruling on the handoff · applied 2026-09-09

**Recorded at** `papers/CORRIGENDA_g6.md` `COR-7` through `COR-10` and its
preamble correction; `docs/RULES_ENACTED.md`, the sub-entry beside `AGE-01` and
`FILL-01`; `CHANGELOG.md`; this entry.

**Its date is not recoverable from the tree,** which is §5 of this document
operating on the very ruling that ratified §5. It followed the handoff of
2026-09-07 and was applied on 2026-09-09; the entry is dated by what can be
sourced rather than by what can be inferred, which is the correction the ruling
itself made against the handoff.

**What it decided.** §1 upheld six corrections the loop had filed against the
handoff and named two of them as the operator's own — that `R-3` over
`papers/**` had been lifted on 2026-08-29 by the close ruling and was carried
into the handoff anyway, so *a handoff that forbids the operation it commands*
would have blocked §5.1 and §5.2; and a date asserted from memory inside a
section about date-checking. §2 widened the scope from the handoff's two named
overclaims to **every claim on the claim surface contradicted by its own
artefact, in one pass** — `O-1` through `O-4`, `U-2`, `U-4` and the σ₁/σ₂
rounding — with the reason stated: `COR-6` had moved `O-4`'s contradiction into
a single page of §4.1, and batching corrections of one class by an arbitrary
scope is what produced the adjacency. §3 ratified §5.3's resolution as stronger
than the ruling it answered (widening 3–5 would restore a figure the matrix had
already withdrawn — `AGE-01` run backwards) and ratified the training-time
repair as a replaced metric rather than a corrected number. §4 accepted that
sixteen of the eighteen operator defects are unsourceable from the tree, held
that omitting rather than reconstructing was correct, and named the identifier
finding of §5 below as the more useful half. §5 ordered the commit.

**What it did not do.** It issued no new reservation, ordered no measurement,
and built no guard. The class recorded under §1 — a relative time reference in a
durable artefact is stale by construction — was recorded as a line in the
register beside `FILL-01` and explicitly not as a rule.

---

## 3. Where the loop corrected an operator ruling

Each row is a correction the tree records **in writing** against a ruling that
had already been issued. The finding ID is given where the tree assigns one; where
it does not, the column says so rather than inventing one.

| # | ruling corrected | what was wrong | the correction, and its ID | recorded at |
|---|---|---|---|---|
| 1 | 2026-08-26, `G7-R` | *"Chart L cannot represent either witness member to within the instrument floor."* | **False.** Best chart-L stand-ins reach 0.70% and 2.2% of the floor. The number the ruling reasoned from came from a collocation-only embedding in the loop's own scouting report — *"the error was mine, not the operator's"*. Pinned by `test_projection_is_at_least_as_good_as_collocation`. No finding ID | `AUDIT_g7` §5.1 |
| 2 | 2026-08-26, `G7-R` | `SPEC-g7-2`'s falsifier — *the embedded pair's distance exceeds the floor* | Fires under collocation (2.446e-02) and not under the best embedding (1.207e-02). A falsifier of that shape is only meaningful against a *best* embedding. No finding ID | `AUDIT_g7` §5.2 |
| 3 | 2026-08-26, `G7-R` | the §3.3 posterior geometry — an ESS collapse attributed to a posterior *"diffuse along the degenerate manifold"* | **There is no manifold.** The profile likelihood between the witness members is bimodal, two isolated maxima across a 242-log-unit barrier, 5 of 61 path points inside the floor. The remedy changes with the diagnosis: mode-hopping or tempering, not more samples. No finding ID | `AUDIT_g7` §5.3 |
| 4 | 2026-08-26, post-g8, §7 | `PH-22`'s retro-application *"with a guard and both controls, in the generation it is enacted"* | **Cannot be honoured as written.** `PH-22`'s text is not in the tree, and its guard is a measurement with no violation to plant. Recorded as a reconstruction, marked as such, with `test_the_ph22_backfill_is_marked_as_reconstructed` asserting the marking. `OPS-01` is satisfiable forward and not backward | `AUDIT_g8` §3.1 |
| 5 | 2026-08-26, post-g8, §4 | the model of `CHART-01` as two operators in files that never refer to each other | **Too small.** Five load-bearing call sites in `src/` and nine in `tests/`, across three grid resolutions, plus a **third** hand-written copy of chart G inside the generation-6 falsifier — so the falsifier was a copy of the study it falsified. Opened as `FALSIFIER-01` | `AUDIT_g8` §3.2 |
| 6 | 2026-08-26, post-g8, §5 | *"only where a gap justifies it — which today means `d=4` only"* | **One word too strong.** The licence follows the gap, not the dimension: chart J at `d=4` has no gap at the cutoff either. Correct statement: chart G at `d=4` and chart L at `d=4`. No finding ID | `AUDIT_g8` §3.3 |
| 7 | 2026-08-26, post-g8, §8 | the champion / state-file test, generalised | The natural generalisation is **false of correct history** — `922c2cc` is a champion that modified `LOOP_STATE_v4.json` legitimately. The guard asserts the ruling's sentence exactly and records what it deliberately does not assert. No finding ID | `AUDIT_g8` §3.4 |
| 8 | 2026-08-26, post-g9, §2 | promote the *44% apart* figure into the table | **The figure could not be reproduced.** It was reported without its invocation — no device, bias, grid, chart pair or projection — and the closest defensible construction gives 38.6% and reproduces those digits nowhere. The defect §3 of the same ruling is about, committed one section earlier | `AUDIT_g9` §1.1 |
| 9 | 2026-08-26, post-g9, §5 | `SPEC-g10-2`'s falsifier | **Inverted.** The ruling assigns the *dimension* reading to the *ridge* outcome; an outcome putting `d=4` and `d=16` on the same side of a split is exactly what a dimension effect cannot produce. No finding ID | `AUDIT_g10` §1 |
| 10 | 2026-08-26, post-g9, §2 | the premise `WIT-01` was ordered on — *the pairs that separate are those whose junctions were nearly coincident, which is sub-grid* | **Does not hold.** One of six is sub-node; the other five separate with junctions up to 124 nodes apart, and survivors include pairs closer than four of the six. What predicts survival is observational distance at `N=301`. `WIT-01` admits all thirteen chart-J pairs, so **it would not have prevented the finding it was enacted in response to.** No finding ID | `AUDIT_g10` §2 |
| 11 | 2026-08-26, post-g9, §4 | `WIT-01` as literally worded | **Unimplementable.** Two chart-J devices sharing a junction have separation exactly zero, so the literal rule deletes most of the witness set it was enacted over. The reading taken is written into the source and the result document, *because a rule whose implementation silently differs from its wording is worse than one that does not exist* | `AUDIT_g10` §3 |
| 12 | 2026-08-26, closing | the refusal of a margin band, on the ground that the band was 1.4 points wide | **The decision was right and its recorded justification was not the strongest available.** Chart L shows there is no band at all | `RULING g11` `CORRECTED` 5 |
| 13 | 2026-08-26, closing, §2(b) | the ratified premise *what predicts refinement survival is headroom against the floor* | **Falsified.** Perfect on the two 13-pair sets that formed it; on the 37-pair set that did not, concordance **0.479** against 0.500 for a coin, spearman −0.033 at p=0.845. `SR-1` traced it forward to spine item 3, amended | `RULING g11` `CORRECTED` 4; `docs/G11_RESULT.md` §5 |
| 14 | 2026-08-26, closing | the decline of chart L's refinement, on the argument that a basin at 212 floor units cannot become a ridge | **Right about the outcome and irrelevant to the decision.** The pilot came out at 7.5 s per pair; the run took 288 s. `PILOT-01` is the enactment. This is the **ninth operator error** | `docs/RULES_ENACTED.md` `PILOT-01` |
| 15 | 2026-08-28, directive, §7 | the directive's own guess that `CI-01` would take `U-INSTR` with reachability *a remote exists* | **Wrong when written** — the remote already existed. No verdict was issued, and the classification would have been false at the moment of issuing | `RULING g11` `CORRECTED` 6 |
| 16 | 2026-08-28, reserved-item, §3 | the diagnosis that three line-ending incidents mean the `.gitattributes` fix is incomplete **in coverage** | **Corrected.** 350 of 350 tracked files resolve to `attr/-text`; `* -text` is a wildcard that cannot miss a class. Incidents 2 and 3 were **tools** — Python's text mode rewriting an LF blob as CRLF on `win32` — which no `.gitattributes` can prevent. The incomplete half is the tool side | `RULING g12` `CORRECTED` 2 |
| 17 | 2026-08-28, reserved-item, §1.6 | the home-path regex `/(home\|Users)/[a-zA-Z0-9_.-]+` | **Forward-slash only**: 8 hits. Extended to Windows separators, **67 occurrences across 12 files**, ten added by this loop. `SW-18a` was recorded as two manifests; it is twelve files | `RULING g12` `CORRECTED` 3 |
| 18 | 2026-08-28, reserved-item, step 5 | the premise that the preservation copies hold pre-rewrite objects | **The finding is the absence.** Neither copy contains a `.git`; the archive zip is the pre-loop repository. `docs/COMMIT_HASH_MAP_g11.json` is therefore not a bridge to an independent record — it **is** the record, on one disk | `RULING g12` `CORRECTED` 4 |
| 19 | 2026-08-29, close-out | *"the 3.9 leg specifically"*, green or red | **There is no 3.9 leg.** It was removed at `AUDIT_g7` with the support claim it evidenced, and `>=3.11` makes one fail at install rather than at test. Neither branch of the order's disjunction can fire. `AGE-01`, and the file's own leg table is stale the same way | `docs/OPERATOR_TASKS.md`, *the 3.9 leg* |
| 20 | 2026-08-29, close-out, §3 | the belief that scoring `WINDOWS_RISK_g6.md` needed a GitHub runner — carried in `OT-1`'s own scoring table, five rows, every one `no` | **Four of the five never needed a remote.** The source document never made the error; its 2026-08-25 preamble says the audit machine is Windows and the untested leg is Linux. An artefact encoding the **instrument set** of its date — a form `AGE-01`'s own record does not name | `docs/WINDOWS_LEG_SCORED_g15.md` §1 |
| 21 | 2026-09-02, §1 | the four unreferenced PNGs called *"its own small finding"* | **An absence read as an oversight.** They are from a different run — `T = 5.07` against §4.5's `2.08` — and both directories predate `RunManifest`, which `RELEASE_READINESS` §7 already records. *"`AGE-01` inverted."* This is the **eighteenth operator defect** | `docs/PAPER_FINAL_g15.md` §2 |

**Two things this table is not.** It is not a list of the loop's corrections of
*itself* — `RULINGS.md`'s `CORRECTED` sections carry those. Its `SR-2` ledger
records nine corrections at `g11`, *"three of them errors in this loop's own
rulings, two of them errors of mine made during the generation"*, and seven at
`g12`, *"four of them mine"*. (`g12`'s `CORRECTED` section opens with the word
*Six* and then lists seven numbered items; the ledger's seven is used here and
the discrepancy is left as the source has it.) And it is not evidence that
the operator was wrong more often than the loop; the `SR-2` ledger counts only
post-fusion corrections and explicitly does not count the pre-fusion ones, so no
rate is computable across the whole loop and none is stated here.

**The table runs one way, and the other direction is recorded elsewhere.** The
ruling on the handoff of 2026-09-07 upheld six corrections filed *against the
loop's own handoff document*, two of which were substantive: the handoff carried
`R-3` over `papers/**` nine days after the close ruling of 2026-08-29 lifted it,
which would have forbidden the two edits the same handoff ordered; and it
asserted a date
from memory inside the section about checking dates. Those are recorded at
`papers/CORRIGENDA_g6.md`'s preamble correction and in `CHANGELOG.md`, not here,
because this table's subject is corrections the tree records against rulings. The
asymmetry of the table is a fact about its scope and not about the record.

---

## 4. The operator defects — what the tree holds

The handoff asks for eighteen, with what each cost and what caught it. **The tree
holds two by number and a further set without one.** The numbered list lives in
the rulings, which are not files here.

| number | the defect | what it cost | what caught it |
|---|---|---|---|
| **9** | a plausibility argument about the *result* used to settle a question about the *cost*: chart L's 37 witness pairs declined at the close because *a basin at 212 floor units cannot become a ridge* | chart L published as a `WIT-02` gap across **three generations**, and `L1` unreachable while it stood. The measurement, when finally run, cost **288 seconds** | generation 11's pilot — 7.5 s per pair, 278 s projected, 3.5% low. Enacted as `PILOT-01`, guard `tests/test_pilot_first_g12.py` |
| **18** | an absence read as an oversight: four unreferenced PNGs called a finding without checking whether they were unreferenced *by decision* | nothing measurable — the suggestion was resolved the other way and the correct answer was already in `RELEASE_READINESS` §7 | `docs/PAPER_WORK_g15.md` §4, which tabulated the run mismatch (`T = 5.07` against `2.08`) rather than following the suggestion |

**Recorded as operator errors without a number:**

* **The Windows leg carried for eight generations as *"not obtainable on this
  host by any means"*, on a host that is Windows.** Cost: eight generations in
  which four of `WINDOWS_RISK_g6.md`'s five predictions could have been scored
  and were not. Caught by the close-out ruling of 2026-08-29, in the operator's
  own words, and scored in `docs/WINDOWS_LEG_SCORED_g15.md`.
* **Three undetected operator actions inside fifteen minutes on 2026-08-28** —
  the `commit-msg` hook at 09:06:36, the `filter-repo` rewrite at 09:16:38, the
  remote at 09:20:50. Cost: `HIST-01`, eight failing guards, three silently
  skipping, and a generation of repair. Caught a generation late by the
  reserved-item report assembling the ordering by hand, then by `OPS-02`'s first
  run, which recovered the same ordering mechanically
  (`tests/test_operator_actions_g12.py`).

**What is absent and is not reconstructed.** Defects 1–8 and 10–17 carry no
number anywhere in the tree. Rows 1–8, 12–13, 15–20 of §3 above are corrections
against rulings and several of them are plainly the same events the operator
numbered, but *which number belongs to which* is not recoverable, and assigning
one would be inventing the operator's own accounting. `docs/PAPER_FINAL_g15.md`
§2 reached the same conclusion when it needed the count and could only say where
the nearest tree records were.

**Stated plainly, so the numbering is not read as complete.** The operator's
defect list lives in the session messages that carried the rulings. Those
messages are not files in this repository and are not recoverable from it. What
this section holds is two numbered defects and a further set recorded without
numbers, and that is the whole of what the tree can support — not an
abbreviation of eighteen, and not eighteen with sixteen omitted for brevity. A
reader who counts the rows here is counting what survives in the tree.

---

## 5. What this index found about the record itself

**The rulings are cited by date and section, and the dates repeat.** §2 above
lists four rulings dated 2026-08-26 and five dated 2026-08-28, and their section
numbers collide: two different §2s on 2026-08-28 (the close addendum's bounded
refinement, and `PILOT-01`), two different §3s on the same date (`DOC-08`, and
`SKIP-01`), and two different §4s on 2026-08-26 (`WIT-01`, and the `CI-01`
remote decision). Where a result document attached a descriptive name
— *the reserved-item ruling*, *the pass-4 ruling*, *the closing ruling* — the
citation is recoverable. Where it did not, *"the ruling of 2026-08-26 §4"* names
two different orders in two different files, and nothing in the tree resolves it.

**This is `OPS-01`'s defect one level up.** `OPS-01` says a rule that lives only
in a ruling does not exist, and it fixed the *rule* half: every rule enacted from
generation 8 on lands in `docs/RULES_ENACTED.md` with its guard. The *citation*
half was never fixed. A ruling still has no identifier, so a document that acts on
one can only point at a date and a number, and two rulings on one date make that
pointer ambiguous. The cost is small and real: this index cannot merge two rows
that are probably one ruling, and says so instead.

**The fix, named and not built.** A ruling gets an identifier at the moment it is
acted on — `OR-<date>-<n>`, assigned by the first document that cites it and
carried by every later one. It is not built here for the same reason `FILL-01`
was not: this is a record, not a generation, and a register of identifiers
assigned retroactively to messages that are not in the tree would be a
reconstruction wearing an identifier scheme.

---

## 6. What this document did not do

* It did not reconstruct a ruling's text from its effects. Every quotation above
  is a quotation the tree already holds.
* It did not assign operator-defect numbers. Two are sourced; the rest are absent
  and stay absent.
* It did not merge rulings that share a date. Where the tree cannot tell them
  apart, neither does this.
* It did not measure anything. No script was run against the physics, and every
  number quoted is read from the document named beside it.
* It did not correct any ruling. §3 is an index of corrections the loop had
  already made and recorded.
