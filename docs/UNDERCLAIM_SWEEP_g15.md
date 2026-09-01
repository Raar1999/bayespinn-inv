# UNDERCLAIM_SWEEP_g15 — where the evidence supports more than the sentence says

**Ordered by** operator ruling of 2026-09-02 (paper, final) §3 · **Date** 2026-09-02
**Not a generation.** No `LOOP_STATE` increment, no ladder movement, no spec.
**Report only. Nothing in this document is applied.** Every entry is a finding
about a sentence, with the artefact beside it; no sentence was edited under this
sweep. The two paper edits made the same day were ordered by §2 and §4 of the
ruling and are recorded in `docs/PAPER_FINAL_g15.md`, not here.
**Positive control** `COR-3`, §2 below. It appears.

---

## 1. What was swept, and how

**The question.** Fifteen generations of guards in this repository point one
way. `AH-12`'s vocabulary rules, `PH-15` and `PH-21`'s labelling, `DOC-08`, the
expectation that the withdrawal section is non-empty, every falsifier
pre-registered against the loop's own results — all of it catches a sentence
stronger than its evidence. Nothing catches a sentence *weaker* than its
evidence, and `COR-3` showed that the second error occurs: the contributions
list carried the withdrawn *neutral* framing of the acquisition result while
§4.6 carried the surviving *harmful* one, and the withdrawn version was the
flattering one. A system tuned that hard in one direction produces the opposite
error systematically and invisibly. This sweep is the one bounded look in the
other direction.

**The method.** For each result sentence, find the artefact its number or its
framing came from — through `docs/CLAIM_EVIDENCE_MATRIX.md` where a row exists,
directly from `outputs/` otherwise — and compare the strength of the sentence
with the strength of what the artefact shows. Report where the artefact supports
more than the sentence says: a qualifier with no measurement behind it, a hedge
inherited from a superseded version, a *may* or *suggests* where the artefact
shows a measured separation, a scope narrower than the data covers, a number
smaller than the one the ledger now holds. The reverse cases — sentence stronger
than artefact — are not the target, but where the same pass found one it is
reported in §5 rather than suppressed, because suppressing a found defect would
be this sweep committing the error it was ordered to look for.

**The scope.** `papers/draft.md` in full — abstract, contributions list,
§3–§6 — and `README.md`'s results table and its caveats. Those are the surfaces
where a *summary* stands in front of a *body*, which is the shape `COR-3` had:
the body was right and the summary lagged it. The remaining claim-surface
documents (`docs/G8_RESULT.md` through `docs/G11_RESULT.md`,
`docs/CLAIM_EVIDENCE_MATRIX.md`, `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`,
`docs/CHART_RECONCILIATION_g7.md`, `docs/CLOSE_RULING.md`,
`docs/CLOSE_ADDENDUM.md`, `ADR-0007`) transcribe artefact values into tables at
the generation that measured them and carry no editorial layer between number
and sentence; they were not swept, and that is a scoping decision stated rather
than an omission.

**One instrument built for the sweep and run by hand.** The matrix's §3 lists
every literal this project has withdrawn — `13 orders`, `~500×`, `4.6%`,
`30% → 71%`, `2.8e-7`, `7.6e-6`, `1730×`, `3–5 of 16`, *no distinguishable
advantage*, *first to evaluate*, *strong-inversion stiffness*. A withdrawn
literal still asserted on the claim surface is a superseded version leaking
into a live document, which is one of the shapes the ruling names. Every one of
those literals was searched for across all fourteen claim-surface documents.
The result is in §3, finding `U-1`, and it is the sweep's main product.

---

## 2. The positive control — `COR-3`

The control is the text **before** `COR-3` was applied. At `e39cb60^`,
`papers/draft.md` line 115 read:

> 5. A negative result: uncertainty-driven bias acquisition **does not beat
>    random selection** on this task at any measured budget.

The artefact is `outputs/experiment_design/experiment_design.json`, row `D10`
of the matrix: `max_std` scores **−0.31** mean identifiable rank against random
over twenty (family, budget) cells, with a win/tie/loss record of **2 / 9 / 9**.
The sentence says *not better*; the artefact shows *worse*, with a measured
separation and a direction. The method of §1 — sentence beside artefact,
compare strength — flags it as an underclaim in one step, and it also flags
the second symptom: `docs/NOVELTY_AUDIT.md` §6.3 records the neutral framing as
**withdrawn**, so the sentence was a superseded version surviving in a summary.

**The control appears in the output.** The sweep is measuring what it claims
to. Had the method not flagged this sentence, nothing below would be worth
reading.

---

## 3. Findings — the evidence supports more than the sentence says

### `U-1` · contribution 1 states a solver gain the ledger withdrew as too small by three orders of magnitude · **HIGH**

**The sentence.** `papers/draft.md` §1, contribution 1:

> equilibrated continuity solves (**1730×** improvement in the equilibrium
> mass-action law)

and `README.md` line 291, in the solver section:

> Equilibration improves the equilibrium mass-action law by **1730×**
> (ADR-0001).

**The artefact.** Matrix row `S1` and its superseding entry `X17`. The figure
`1.32e-2 → 7.62e-6 (1730×)` was measured on the pre-audit solver; the adopted
solver reaches `9.7e-10`, and `X17` records in as many words: *"the real gain is
~7.0e6×, not 1730×. The published figure understated the improvement by
~4000×."* The matrix marks the 1730× **withdrawn**.

**Re-measured today, on this tree**, by running the body of
`tests/test_sg_numerics.py::test_equilibration_beats_plain_spsolve` and reading
both sides rather than only the assertion:

| | max \|np − 1\| at equilibrium |
|---|---:|
| plain `spsolve` | 6.770e-3 |
| equilibrated | 9.729e-10 |
| gain | **6.96e6×** |

**Why it is an underclaim and not a typo.** The number in the sentence is not
wrong by transcription; it is the figure a superseded version of the project
published, carried forward into the contributions list after the ledger moved
underneath it. That is exactly `COR-3`'s mechanism — the summary was not
re-derived when the body was — in the other numerical direction: the paper is
claiming a solver improvement about four thousand times smaller than the one it
has. Of the withdrawn literals in the matrix's §3, **this is the only one still
asserted as live on the claim surface.** Every other hit of the §1 search is a
mention — *"this gate previously read 2.8e-7"*, *"earlier versions of this
README said no distinguishable advantage"*, *"the documented strong-inversion
stiffness limitation was this bug"* — which is the correct way for a withdrawn
literal to appear.

**Also carried by** `docs/adr/ADR-0001-…md` lines 61 and 69, which is a dated
decision record and is not on the claim surface; noted so that whoever repairs
the paper knows the ADR states the same number and states it as of its date.

**Not applied.** The repair is a one-number change at two live sites and a
corrigendum entry (`COR-4` would be its name), and under the ruling it is
reported, not made.

### `U-2` · §3.2 hedges a count the record has · **LOW**

**The sentence.** `papers/draft.md` §3.2, *inherited obstructions are re-tested,
not carried*:

> and **at least one** turned out to be false on the first attempt, having
> never been tried.

**The record.** `docs/RULES_ENACTED.md` `OBS-01` names two, each with the
document that found it: `DOC-03a`, the README badge recorded as unchangeable
and changed in one line; and `HIST-01`, carried for three generations as
`UNREPAIRABLE FROM INSIDE THE TREE` while `.git/filter-repo/commit-map` sat in
the repository. `docs/WINDOWS_LEG_SCORED_g15.md` §1 records a third — the Windows
leg carried for eight generations as *not obtainable on this host by any means*,
on a host that is Windows. Three instances, each dated, each with a record.

**Why it is an underclaim.** *At least one* is a hedge with a measurement behind
it: the count is three and the paper could say three. The sentence is true and
weaker than the record. It is LOW because the sentence is a methods remark and
not a result, and because the count is of the project's own errors rather than
of a device.

### `U-3` · §2.2(c) conceded the instrument criticism without stating where the paper uses the preferred instrument · **MEDIUM — applied the same day under §4 of the ruling, not under this sweep**

**The sentence, before today's edit.** `papers/draft.md` §2.2(c), second
paragraph, ended:

> the honest reading is that §4.1 buys breadth at the price of the sharper
> instrument.

**The artefacts.** `outputs/g9/basins.json`, `outputs/g10/ridge_basin.json`,
`outputs/close/wit02_register_v3.json` — every barrier in §4.3 is a
profile-likelihood construction along a straight line in chart coordinates,
which is the instrument Wieland et al. (2021) argue *for* against the
Fisher-information family that §4.1's Jacobian spectrum belongs to. The paper's
own §2.2(c) first paragraph says §4.3 is profile likelihood; its second
paragraph then concedes the Fisher criticism against §4.1 and stops, without
saying that the geometric claims are made with the instrument the critic
prefers.

**Why it is an underclaim.** The concession was correctly scoped and the
defence it licenses was not stated. The evidence supports *"the rank claims use
the criticised instrument and the geometric claims use the preferred one"*;
the paper said only the first half. The ruling's §4 ordered exactly this
repair, and it is applied in this commit as an order of the ruling; it is listed
here because the sweep's method finds it independently and the sweep should
show that it does.

### `U-4` · §4.10 reports two audit cycles of a fifteen-generation audit · **LOW, scope**

**The sentence.** `papers/draft.md` §4.10:

> Fourteen defects across two audit cycles. Four produced silently wrong
> physics while the test suite of the day passed

and the abstract: *"an adversarial audit that found fourteen defects in its
first two cycles, seven critical"*.

**The ledger.** `docs/AUDIT_MASTER.md` holds forty-seven findings, of which
fourteen are numbered `BUG-xx`, across the two cycles the paper describes — and
then continues: generation 0 found the repository had bifurcated and `HEAD` was
the pre-audit project (`PROV-06`); generation 6 found forty-one numbers that can
never be explained because their producing tree was never committed
(`REPRO-01`); generation 11 found a repair sitting in `.git` for three
generations (`HIST-01`); generation 13 found a codemod that changed 9,832 lines
to fix 68 with the suite green before and after (`DIFF-01`'s founding entry).
None of that is in §4.10.

**Why it is a scope finding and not a false sentence.** Both sentences are
scoped — *two audit cycles*, *its first two cycles* — and both are true as
scoped. What the evidence supports and the paper does not say is that the audit
did not stop where §4.10 stops, and that the later findings are the ones that
bear on the reproducibility claims the paper makes (§4.10's own headline is *how
easily plausible numbers survive a passing test suite*, and `REPRO-01` and
`DIFF-01` are the sharpest instances of it in the tree). The scope is narrower
than the data covers. LOW because widening it is an editorial choice about the
paper's length, not a correction.

---

## 4. A boundary case the method found, resolved by an artefact the paper does not cite

**The abstract, §4.8 and §6 say `3–4 of 16`; the §4.1 table beneath the
abstract says 4, 5, 3, 4.** The table is `outputs/identifiability/…json`,
matrix row `C12`, and its asymmetric-step device is **5**. The headline is
matrix row `D14`, measured at the reference analysis conditions of the
robustness run (`rel_step = 0.01`, `min_snr = 1e4`), where the four families
give 3, 4, 3, 3. `D14a` licenses the narrowing: *rank 5–6 appears only at
larger finite-difference steps (0.02–0.05), which lower the analysis noise floor
rather than revealing more physics*, and the §4.1 table's rows were taken at
`rel_step = 0.05`, `min_snr = 1e8`.

**Direction.** The summary is narrower than the table it summarises, so the
method flags it; the artefact then shows the narrowing is the *considered*
claim and the table's 5 is the raw one. So this is not an underclaim. It is a
headline and a table at different analysis settings, with the licence for the
difference in the ledger (`D14`, `D14a`, `IDENT-02`) and not in the paper. A
reviewer who reads the table under the abstract will see 5 and 3–4 disagree and
will not find `D14a`. Reported because the sweep's method surfaces it and
because it is the kind of thing `COR-2` taught this project to write down.

---

## 5. Incidental — the opposite direction, found by the same pass

Not the target. Reported rather than suppressed, for the reason given in §1.

| # | sentence | artefact | what the artefact shows |
|---|---|---|---|
| `O-1` | `README.md` lines 51 and 112: *"P=8→32 leaves it at **3–4**"* (twice) | `outputs/identifiability_robustness/…json`, matrix `D13` | rank by `P` is `{8: [4], 12: [3, 4], 16: [3, 4], 24: [2, 3, 4], 32: [3]}` — the range is **2–4**, and the symmetric step at `P = 24` is 2. `papers/draft.md` §5 says 2–4 and is right; the README overstates the stability |
| `O-2` | §4.9: *"A budget-matched ensemble, **trained faster than either** single-network method, still beats both"* | `outputs/uq_benchmark/uq_benchmark.json`, `cost.train_seconds` | budget-matched ensemble 6.66 s; MC-dropout 9.22 s; SWAG **6.26 s**. Faster than one, slower than the other. Matrix `D6` prints all three and the sentence read only the first. Wall-clock is also excluded from this project's reproduction comparisons as *not a scientific claim* (matrix §6), so the sentence rests on the one kind of number the ledger does not stand behind |
| `O-3` | §4.5: *"variance inflation $T=2.08$"* | `outputs/results/results.json`, `H3_calibration.temperature` | **2.0927**. README and matrix `C10` say 2.09. Transcription |
| `O-4` | §4.1: *"Conclusion stable across finite-difference steps (0.01–0.05 decades) and SNR thresholds (1e4–1e8): identifiable rank 4, σ₁/σ₂ = 6.11–6.13"* | `outputs/identifiability/…json`, `analysis_convergence` | the `(min_snr = 1e4, rel_step = 0.01)` row gives identifiable rank **3**; the other four rows give 4. σ₁/σ₂ runs 6.107–6.123, so 6.11–6.12. The mechanism is `D14a`'s: the smallest step at the loosest threshold has the highest analysis floor |

---

## 6. Checked and held

Result sentences whose strength matches the artefact. Listed so the sweep's
coverage is visible and so a later reader does not repeat the checks.

| sentence | artefact | held because |
|---|---|---|
| abstract: *"differ by at most 1.79% across a 0.15–0.90 V sweep"*; Figure 1: *"observational distance 0.0176"* | `outputs/figures_g15/manifest.json` | two different quantities, both right: the pointwise maximum relative I–V difference is 1.786%; the observational distance is 0.01755 |
| abstract: *"improving the instrument by four orders of magnitude roughly doubles it"* | `rank_vs_noise`, symmetric step | 4 at 2% → 9 at 1e-4% (4.3 decades) is 2.25×; *roughly doubles* is fair, and *more than doubles* would be the strongest honest form |
| §4.3: floor sensitivity 1.24% / 1.52% / 1.26%, *"survives a 1.6× better instrument"* | `outputs/floor_sensitivity_g15/…json` | 1.2369, 1.5166, 1.2551; headline ratio 1.62 |
| §4.2: *"the excess is **largely** attributable to the spread of the biases"* | `docs/G14_RESULT.md` §2.4 | at one held-out device the departure is entirely spread (residual percentile 0.492); at three devices a residual survives (0.880–0.947); *largely* is the calibrated word and *entirely* would overclaim |
| §4.2 final paragraph: the conditioning hypothesis, hedged four times | `docs/PAPER_AUDIT_g15.md` `O6` | the evidence establishes none of it, so the hedges are warranted in content; the multiplicity is form, already recorded by the audit |
| §4.6: *"the gain is modest (≈0.4 of a rank unit on a base of 3–4)"* | `experiment_design.json`, `D11` | +0.39 with 5 / 15 / 0; the zero-loss record is in the table two lines above the sentence |
| §4.8 and abstract: cosines +0.50 / −0.00, value error 4.5× over a 33× budget | `gradient_fidelity.json`, `D7`–`D9` | +0.504, −0.001, 1.1327 → 0.2518 (4.50×), 300 → 10 000 epochs |
| §4.3: witness counts, refinement survivors, barrier medians, 13× depth ratio | `wit02_register_v3.json`, `basins.json`, `J2a`, `J2b` | transcribed exactly, with the close-ruling weakening to search statements carried |
| §4.3: *"junction depths of 694 nm and 271 nm … moving 1.7% under N = 301 → 1201"* | `outputs/g9/junction_refine.json`, `I4a` | 1.7551e-2 → 1.7247e-2, −1.73% |
| §4.2: ×1.17 / ×26 / ×21 / ×39, *"at 12 of 12 operating points"* | `outputs/g9/op_points.json`, `I2` | exact |
| §4.4, §4.5, §4.7: forward errors, recovery, coverage, ρ = +0.824, 15.7× / 11.8× | `outputs/results/results.json`, `C1`–`C9`, `C21`, `C22` | exact, apart from `O-3` |
| §4.9: ρ +0.798 / +0.299 / +0.486, 21.3× / 1.4× / 2.5× | `uq_benchmark.json`, `D4`, `D5` | exact, apart from `O-2` |
| contribution 5 and §4.6: *worse than random*, −0.31, 2 / 9 / 9 | `D10` | this is `COR-3` applied; held |
| §2.2(a), §6: *"we add measurement, not method"*, *"none of it is a new method"* | `ADR-0003`, `docs/NOVELTY_AUDIT.md` §6 | a decision record, not a hedge; the novelty audit rates the strongest candidate *low as method, moderate as a diagnostic framing*, and the paper says that |

---

## 7. What the sweep says about the machinery

**Two real underclaims in a paper of about ten thousand words, and both have
the same mechanism.** `U-1` and `COR-3` are not hedging temperament. In both,
a *summary* — the contributions list — carried a figure or a framing from a
superseded version of the project after the *body* and the *ledger* had moved:
`1730×` after `X17` withdrew it, *does not beat random* after `DES-01` withdrew
it. The direction of the error is incidental to the mechanism; `X17` happened to
be a withdrawal upward and `DES-01` a withdrawal toward the harsher reading, so
both surfaced as underclaims, but a withdrawal in the other direction would have
surfaced as an overclaim through the same gap. The gap is that nothing
re-derives a summary when the ledger changes.

**The cheap instrument exists and was run once, by hand, in §1.** The
matrix's §3 is a list of withdrawn literals. Searching the claim surface for
each of them found `U-1` in under a minute and found nothing else live. That is
the guard `docs/PAPER_WORK_g15.md` §3 named and did not build — *one that fails
when a framing recorded as withdrawn still appears in the tree* — with the list
of withdrawn things read from the matrix rather than restated. It is not built
here either, under the same reasoning as before: building it is a generation's
work, this was a sweep, and a guard whose list of literals is hand-maintained is
a presence check that goes stale (`AGE-01`, `FILL-01`). The hand result is
recorded so that the next person can decide with the number in front of them
rather than with the argument.

**The hedges themselves are mostly right.** `U-2` is the only place a
qualifier was found standing in for a count the record has, and it is a methods
remark. Every hedge on a device result checked in §6 is calibrated to its
artefact. The ruling's premise — that a system tuned hard against overclaiming
will underclaim systematically — is confirmed in the *summary* layer and not in
the *results* layer. That is worth knowing: the falsifiers and the vocabulary
rules act on result sentences, and result sentences are fine; nothing acts on
lists, and lists are where both defects were.

---

## 8. Nothing applied

`U-1` is not corrected in `papers/draft.md` or `README.md`. `U-2` is not
reworded. `U-4`'s scope is not widened. §4's table is not annotated. `O-1`
through `O-4` are not fixed. `U-3` is applied, and the ruling's §4 is the
authority for it, not this sweep. The `COR-4` that `U-1` would need is named
and not written.
