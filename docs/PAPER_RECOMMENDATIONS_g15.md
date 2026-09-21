# PAPER_RECOMMENDATIONS_g15 — proposed changes to claim sentences

**Ordered by** operator close-out order of 2026-08-29, T6 · **Subject**
`papers/draft.md`
**NOTHING IN THIS FILE IS APPLIED.** Every entry is a proposal. The paper is
unchanged by this document, and remains unchanged until someone with authority
over claim sentences acts on an entry here.

The close-out order permits additive and structural changes to the paper
directly, and reserves any change to a sentence that states a result. This file
is where the reserved half went. Companion analysis, with the reasoning behind
each entry, is in `docs/PAPER_AUDIT_g15.md`.

**No entry here has been tested against the claim-surface guards**, because none
has been applied and the guards read the paper rather than this file. That is not
a formality. Two of the *structural* edits made directly under this order — a
navigation sentence in §1 and one in the §2.2 rewrite — fired
`test_claim_surface_g7.py::TestEveryStatementNamesItsChart` on the first attempt,
because each summarised §4.3's result without carrying its chart and dimension.
Both were rewritten to carry them, and the guard was not touched. Expect the same
of anything below: **assume the first attempt fails, and let the guard say so.**

---

## How to read an entry

Each carries the **current text** verbatim, the **proposed text**, and the
**reason**. Where the proposal rests on a number, the artefact holding that
number is named. Where the proposal cannot be evidenced, it says so, and the
proposed text says so too.

---

## R-1 — contributions item 5 carries a framing §4.6 withdraws

**Location** §1, contributions list, item 5
**Class** internal inconsistency · **Priority** high, trivial effort

**Current text**

> 5. A negative result: uncertainty-driven bias acquisition does not beat random
>    selection on this task at any measured budget.

**Proposed text**

> 5. A negative result, and it is stronger than neutral: uncertainty-driven bias
>    acquisition is **worse than random** for inverse identifiability on this
>    task — `max_std` loses 0.31 of a rank unit against random selection across
>    four device families, five budgets and twelve seeds, while two textbook
>    design criteria gain 0.39. Predictive uncertainty and inverse
>    identifiability are not the same question.

**Reason.** §4.6 explicitly records that *"an earlier version of this section
reported that `max_std` acquisition showed 'no distinguishable advantage' over
random"* and that re-measurement found it *"not neutral but actively harmful"*.
`docs/NOVELTY_AUDIT.md` §6.3 lists the neutral framing as **withdrawn**. The
contributions list was never updated and is carrying the withdrawn version. A
reviewer who reads the list and then §4.6 finds the paper contradicting itself
about its own negative result — and in the direction that makes the result
weaker than it is.

**Evidence** `outputs/experiment_design/experiment_design.json`; §4.6's table.

---

## R-2 — §5 does not mention prior dependence

**Location** §5 Limitations, new bullet
**Class** omission of an answerable limitation · **Priority** high, trivial effort

**Current text** — none. There is no bullet on this subject.

**Proposed text** (new bullet, to sit immediately after the barrier bullet)

> - **The global result is a statement about a prior as much as about a device.**
>   Every witness pair is drawn from a stated prior — log-uniform over
>   `1e21–1e23 m⁻³` per magnitude anchor, with chart J's junction coordinate
>   carrying its own uniform prior over physical position and its own hash — and
>   fixed before sampling. A narrower physically-motivated prior could exclude
>   these pairs entirely. We report existence under the stated prior and make no
>   claim about how often degeneracy occurs, or about whether it survives a
>   tighter one.

**Reason.** This is the first question an inverse-problems reviewer asks about a
sampling-based global result, and the repository has already answered it:
`docs/CLAIM_EVIDENCE_MATRIX.md` §7 states that *"nothing outside the stated prior
(a narrower physical prior could exclude these witnesses entirely)"* is
established, and §8 gives the prior, its bounds and its hash. The paper carries
neither the caveat nor the prior. This is the cheapest substantive improvement
identified anywhere in this audit: the work is already done and simply is not in
the paper.

**Evidence** `docs/CLAIM_EVIDENCE_MATRIX.md` §7 and §8; prior hash
`236ff6576a850965…`; `outputs/g8/manifest.json`.

---

## R-3 — the noise model is stated but never argued

**Location** §4.1, first paragraph (amend) and §5 (new bullet)
**Class** unevidenced load-bearing assumption · **Priority** high, trivial effort

**Current text** (§4.1)

> The prior is the chart's own uniform prior over log-doping anchors; the noise
> model is relative Gaussian on the terminal current; the distinguishability
> floor is the solver's reported `current_noise_floor` and the discretisation
> floor is 1.5e-3 log-units.

**Proposed text** (§4.1, amended)

> The prior is the chart's own uniform prior over log-doping anchors; the noise
> model is independent relative Gaussian on the terminal current at a level of
> 2%, **chosen as a round figure rather than calibrated against an instrument**;
> the distinguishability floor is the solver's reported `current_noise_floor` and
> the discretisation floor is 1.5e-3 log-units.

**Proposed text** (§5, new bullet)

> - **The 2% relative-Gaussian noise model is a modelling choice, not an
>   instrument measurement, and every rank in this paper is a count against it.**
>   We have not calibrated it against a real current–voltage measurement chain,
>   and a real one would not be relative-Gaussian across ten decades of current:
>   near the noise floor the error is additive, and a real sweep switches ranges.
>   §4.1's noise sweep shows what the count does as the level moves — 2 dof at
>   20% and 9 at 1e-4% — so a reader who has a different instrument in mind can
>   read the answer off that row rather than off our headline.

**Reason.** A search of the audit ledger, the rulings, the claim-evidence matrix
and the paper finds the 2% figure **stated everywhere and argued nowhere**. It is
the single most load-bearing unevidenced number in the paper: every identifiable
count, the distinguishability floor, and the witness-pair admission criterion all
sit on it. A device physicist will ask about it in the first paragraph of their
review. Conceding it costs one clause and one bullet, and §4.1's existing noise
sweep already contains the material that makes the concession survivable.

**Evidence** none for the 2% figure — that absence *is* the finding. The noise
sweep is in `outputs/identifiability/identifiability.json`.

---

## R-4 — no reason is given for not attempting a structural identifiability analysis

**Location** §4.3, opening paragraph (amend), or §5 (new bullet)
**Class** unaddressed methodological objection · **Priority** moderate, low effort

**Current text** (§4.3, opening)

> A local Jacobian rank is a statement about an infinitesimal neighbourhood. It is
> structurally incapable of detecting whether two *far apart* profiles produce the
> same measurement, so we searched for such pairs directly.

**Proposed text**

> A local Jacobian rank is a statement about an infinitesimal neighbourhood. It is
> structurally incapable of detecting whether two *far apart* profiles produce the
> same measurement. The stronger instrument would be a formal identifiability
> analysis, which returns a statement about the whole parameter space rather than
> about the pairs a search happens to reach; **we did not attempt one, and the
> reason is a limitation rather than a judgement about its value** — [state the
> reason: e.g. the forward map is a PDE solve with no closed form, so the
> differential-algebraic route is not directly available at these dimensions].
> What a direct search returns instead is existence, which is weaker, and which
> we report as existence throughout.

**Reason.** *"'Witness pair' is doing work a formal identifiability result would
do better"* is the inverse-problems reviewer's strongest objection and the paper
has no answer to it — not a weak answer, no answer. There is very likely a good
reason the formal route was not taken, and stating it converts an apparent
oversight into a scoping decision.

**This entry is incomplete on purpose.** The bracketed clause is left unfilled
because the reason is not recorded anywhere in the repository and this audit will
not invent one. Somebody who knows why must write that clause. `CITE-01`'s
discipline applied to a methodological claim rather than a citation.

**Evidence** none. That is the entry.

---

## R-5 — the identifiability conclusion is untested outside the transport model, and §5 does not say so

**Location** §5 Limitations, amend the final bullet
**Class** scope of an existing limitation · **Priority** moderate, trivial effort

**Current text**

> - 1D transport only; the 2D solver handles Poisson without continuity.
> - Boltzmann statistics, constant mobility, no interface traps.

**Proposed text**

> - 1D transport only; the 2D solver handles Poisson without continuity.
> - Boltzmann statistics, constant mobility, no interface traps — **and the
>   identifiability conclusion has never been tested under any relaxation of
>   these.** Field-dependent mobility, Fermi–Dirac statistics and trap-assisted
>   transport all change the shape of the forward map, and it is the shape of the
>   forward map that sets the rank. We state the model restrictions as
>   restrictions on the *result*, not only on the solver.

**Reason.** The two bullets currently read as restrictions on the *simulator*.
The paper's central claim is about the *forward map's structure*, and the same
restrictions bound that claim far more tightly than they bound the code. A device
reviewer reads the current bullets as an admission about the tool and then asks
the question anyway. Saying it once, at the level of the result, is stronger than
being asked.

**Evidence** none required — this narrows an existing claim rather than making a
new one. Nothing in the repository contradicts it.

---

## R-6 — measurement-chain realism

**Location** §5 Limitations, new bullet
**Class** unaddressed objection · **Priority** moderate, trivial effort

**Current text** — none.

**Proposed text**

> - **No measurement chain is modelled, and the chain would act where the result
>   lives.** The forward model has ohmic Dirichlet contacts and no series
>   resistance, self-heating or contact non-ideality. The rank climb of §4.2 is
>   driven by *widening the bias window*, and the top of that window is where
>   series resistance and self-heating dominate a real diode's I–V. Whether the
>   climb survives a realistic chain is untested, and it is the specific
>   robustness question we would ask first of this paper.

**Reason.** §7.1 of the audit document: this is the device physicist's sharpest
objection because the confound is not generic — it sits exactly on the mechanism
that produces the paper's second result. A limitation that names the specific
place it bites is more credible than a general disclaimer, and the paper has
neither at present.

**Evidence** none. The forward model's contact treatment is in §2.1 and §3.1;
the absence of a series-resistance term is a fact about the model.

---

## R-7 — the abstract's opening sentence carries no finding

**Location** Abstract, opening
**Class** legibility of a claim sentence · **Priority** very high, low effort
**Depends on** the venue decision (see `PAPER_AUDIT_g15.md` §8), which is not
the loop's to make. Two variants are given and **neither is recommended over the
other**.

**Current text**

> We present an audited, reproducible pipeline for inverse semiconductor doping
> recovery from terminal current–voltage measurements, and use it to put numbers
> on four things this area usually states qualitatively.

**Proposed text — device framing**

> A forward-bias current–voltage sweep of a one-micron silicon diode, measured at
> 2% relative noise, determines only three to four of sixteen doping degrees of
> freedom in the parameterisation we use — and we exhibit two devices whose
> metallurgical junctions sit 423 nm apart in that same micron and whose I–V
> curves differ by about 1%, below the noise floor. What a terminal measurement
> cannot see, no amount of inversion recovers.

**Proposed text — methods framing**

> How much of an inverse problem's parameter space a measurement determines is a
> property of the **measurement protocol**, not of the system being measured, and
> it can be measured rather than assumed. On an inverse doping problem we show
> that which biases are swept dominates three other candidate sensitivities at
> every operating point tested, that the mechanism is the singular spectrum
> flattening rather than its leading direction gaining, and that the resulting
> spectrum predicts — direction by direction — where a learned surrogate's
> gradients can be trusted.

**Reason.** `PAPER_AUDIT_g15.md` §3: no sentence in the current 743-word abstract
carries both *what was found* and *why it matters*; the two halves are roughly
500 words apart. Both proposals above join them in one sentence, and both are
assembled from numbers already in the paper. The device variant's "423 nm" is
arithmetic on 694 and 271, both already published.

**Both variants are untested against the claim-surface guards.** The device
variant states a rank fraction and would need its chart and dimension; the
methods variant states an ordering and a spectral claim and would need the same.
Whoever applies one runs `tests/test_claim_surface_g7.py` and expects it to fire
on the first attempt.

**Evidence** `outputs/identifiability/identifiability.json`;
`outputs/close/wit02_register_v3.json`; `outputs/g9/rank_obs.json`;
`outputs/close/spectrum_shape.json`; `outputs/gradient_fidelity/gradient_fidelity.json`.

---

## R-8 — the abstract is 743 words

**Location** Abstract, whole
**Class** structural, but every cut lands on a claim sentence · **Priority** very
high, low effort

**Current text** — seven paragraphs, 743 words, organised *First / Second /
Third / Finally* plus an audit paragraph and a no-novelty disclaimer.

**Proposed change** — reduce to roughly 200 words with this content budget:

| keep | words | why |
|---|---|---|
| The joined finding-and-consequence sentence of `R-7` | ~50 | The thing a reader must leave with. |
| The observation-set result, one sentence, with its scope | ~35 | The paper's most transferable claim. |
| The global result, one sentence, existence only | ~30 | Establishes that the local number is not the whole story. |
| The gradient-fidelity result, one sentence | ~40 | The tying-together observation, which currently arrives last. |
| *"We claim no new method"* | ~15 | Keep. It is true and it is a virtue. |

| cut | words freed | why it can go |
|---|---|---|
| The solver's `1/SNR` diagnostic paragraph | ~70 | Real, and it is a methods-section fact, not an abstract-level finding. |
| The equivalence-twin numbers | ~30 | Better as a figure (F4) than as three numbers in an abstract. |
| The full flattening decomposition (σ₁ motion, shape-term share) | ~90 | Belongs to §4.2; nobody can absorb it at abstract altitude. |
| The three failed-method summary | ~40 | Reduce to a clause: the mechanism is open. |
| The audit-defect paragraph | ~120 | Genuinely interesting, genuinely not the paper's contribution. One clause. |

**Reason.** At 743 words the abstract exceeds any plausible venue limit by three
to five times and will be cut by somebody. The choice available is whether the
authors do it. Each line above is a claim sentence, which is why the whole entry
is here rather than applied.

---

## R-9 — §4.2's finding follows its failures

**Location** §4.2, block order
**Class** reordering of claim sentences — no rewriting · **Priority** high,
low–moderate effort

**Current order**

1. The four-axis comparison, one-against-three.
2. The pre-registration paragraph — the ranking that was falsified.
3. Width against spacing.
4. The flattening decomposition.
5. Three failed mechanisms, numbered, ~350 words.
6. The characterisation paragraph.
7. The blockquote: *"the paragraph we are willing to put our name to"*.
8. The surviving hypothesis.

**Proposed order**

1. **The blockquote, promoted to the head of the section** as its thesis
   statement.
2. The four-axis comparison.
3. Width against spacing.
4. The flattening decomposition.
5. The pre-registration paragraph — moved down, next to the failures where it
   belongs, since it is provenance rather than result.
6. Three failed mechanisms.
7. The characterisation paragraph.
8. The surviving hypothesis.

**Reason.** `PAPER_AUDIT_g15.md` §4: §4.2 is not over-qualified, it is ordered by
the sequence in which the authors learned things, which puts the confession
before the claim four separate times. **No sentence is rewritten by this
proposal.** Four blocks move. It is listed here rather than applied because
moving a blockquote to the head of a section changes which sentence a reader
takes as the section's claim, and that is a claim-surface decision even when the
words are identical.

A signposting paragraph naming the section's shape *was* added directly under
this order, as an interim measure that asserts nothing. If `R-9` is applied that
paragraph should be deleted, not kept alongside.

---

## R-10 — the paper concedes novelty without stating what remains

**Location** Abstract, closing; §6 Conclusion, closing
**Class** under-claiming · **Priority** moderate, low effort

**Current text** (abstract)

> **We claim no new method.** Every component is standard, and inverse doping
> recovery is a mature field. The contribution is validation, measurement and
> reproducibility.

**Proposed text**

> **We claim no new method.** Every component is standard and inverse doping
> recovery is a mature field; what is new is the measurement and what it turns
> out to predict. The closest prior work on surrogate-gradient fidelity reaches a
> more optimistic conclusion in a different domain and runs no undertraining
> control, and we are not aware of prior work using an identifiability spectrum
> as a direction-by-direction predictor of where a learned model's gradients can
> be trusted.

**Reason.** `docs/NOVELTY_AUDIT.md` §6.2 and §6.4 already contain this argument,
written and sourced: `C6` is rated *"low as method; moderate as a diagnostic
framing and a measured result"*, and the prior work is characterised precisely.
The paper concedes and then stops. A reviewer looking for a reason to accept
needs the sentence after the concession, and the repository has already drafted
it.

**Caution on the second half.** *"We are not aware of prior work…"* is a
negative claim about the literature and is only as good as the search behind it.
`NOVELTY_AUDIT` §6.1 records the search; whoever applies this should re-run it
rather than inherit it, which is `AGE-01` applied to a novelty claim.

---

## R-11 — the threshold-count concession is a definition in the wrong place

**Location** §4.1, move the italicised aside to first use
**Class** placement of a scoping sentence · **Priority** low–moderate, low effort

**Current text** (§4.1, mid-paragraph, after the noise sweep)

> The rank is a **threshold count** at this denominator, not a boundary between
> two populations of singular values, which is why every figure here travels with
> the noise level that set it; §4.2 shows the gap that would license a bare
> integer collapsing from 230.6× to 4.99× as the window widens.

**Proposed change.** Move this to §3.2, at the point where *identifiable rank* is
first defined, and reduce §4.1's instance to a back-reference.

**Reason.** *"Your 'rank' is not a rank"* is an objection a methodologist forms
on first reading the word, several pages before §4.1 answers it. A concession
that arrives after the reader has already decided reads as a retreat; the same
sentence at first use reads as a definition. Nothing about it changes except
where it sits — which is exactly why it is a claim-sentence move and is here
rather than applied.

---

## R-12 — the ordering result never says what a reader would have predicted instead

**Location** §4.2, after the one-against-three result
**Class** missing contrast · **Priority** moderate, low effort

**Current text** — none. The result is stated and the alternative is never named.

**Proposed text** (new sentence following the one-against-three paragraph)

> This is not the prior expectation. Junction position and parameterisation
> dimension are the two axes a device modeller and a numerical analyst
> respectively would nominate first, and both move the local spectrum by more
> than an order of magnitude when they move at all — they simply do not move it
> *consistently*, trading places with each other and with the interpolant
> depending on the device and the window. The observation set is the only axis
> that is large at every operating point tested, and *consistency* rather than
> *size* is what makes it the one worth designing against.

**Reason.** `PAPER_AUDIT_g15.md` §7.3: *"is this a restatement of 'measurement
design matters'?"* is Reviewer 2's sharpest objection, and the answer is in §4.2
but is never framed as an answer. The distinction the paper actually measured —
one axis is *consistently* dominant while three are *sporadically* larger — is
more interesting than the headline and is currently left for the reader to
extract from a table of spans.

**This is a claim sentence and it is not free.** It reinterprets the ×26, ×21 and
×39 spans as *sporadic largeness*, which is a reading of the data rather than a
restatement of it. It should be checked against `outputs/g9/op_points.json`
before use, and against `SPEC-g9-1`'s registered outcome space, since the whole
point of that pre-registration was to stop exactly this kind of after-the-fact
re-reading.

---

## Summary

| # | subject | priority | effort | evidence state |
|---|---|---|---|---|
| R-1 | contributions item 5 carries a withdrawn framing | high | trivial | evidenced |
| R-2 | prior dependence absent from §5 | high | trivial | evidenced, hashed |
| R-3 | noise model stated, never argued | high | trivial | **the absence is the evidence** |
| R-4 | no reason given for skipping formal identifiability | moderate | low | **incomplete — needs an author** |
| R-5 | conclusion untested outside the transport model | moderate | trivial | narrows an existing claim |
| R-6 | measurement-chain realism | moderate | trivial | model fact |
| R-7 | abstract's opening carries no finding | very high | low | evidenced, **two variants, venue-blocked** |
| R-8 | abstract is 743 words | very high | low | budget only |
| R-9 | §4.2's finding follows its failures | high | low–moderate | reorder, no rewriting |
| R-10 | novelty conceded, nothing claimed back | moderate | low | evidenced, re-verify the search |
| R-11 | threshold-count concession in the wrong place | low–moderate | low | move only |
| R-12 | ordering result lacks its contrast | moderate | low | **needs checking against `SPEC-g9-1`** |

Four of the twelve — `R-1`, `R-2`, `R-3`, `R-5` — are between one and three
sentences each and are fully evidenced today. Two — `R-4` and `R-12` — are
deliberately left incomplete, because completing them would mean inventing a
reason or re-reading a pre-registered result after the fact, and this audit does
neither.

**None of the twelve is applied.**
