# PAPER_AUDIT_g15 — is the paper readable, and is it persuasive

**Ordered by** operator close-out order of 2026-08-29, T3–T6 · **Subject**
`papers/draft.md` at `65bef05` plus the structural edits this order authorised
**Not a generation.** No `LOOP_STATE` increment, no ladder movement, no spec.
**Status of every claim sentence in the paper: unchanged.** Proposed changes to
claim sentences are in `docs/PAPER_RECOMMENDATIONS_g15.md` and none is applied.

Fourteen generations made every sentence in this paper true. Nothing had yet
asked whether it is *readable*, and no guard in this repository measures that.
This document asks. It is an editorial audit, and where it disagrees with the
paper it is expressing a judgement about a reader, not a finding about a fact.

---

## 1. Presence — what exists, what is a stub, what is absent

| element | state | size |
|---|---|---|
| Title | present | one line, 21 words |
| Abstract | present, **badly oversized** | **754 words** |
| §1 Introduction | present, **thin outside the list** | 291 words, of which the contributions list is ~220 |
| §2.1 Drift–diffusion | present | 8 lines, equations |
| §2.2 Related work | **was a 72-word paragraph**; now a four-strand skeleton with two gaps marked | rewritten under this order |
| §2.3 Forward model | present | 1 paragraph |
| §3 Method | present, strong | §3.1 oracle, §3.2 identifiability and the chart convention |
| §4 Experiments | present | ten subsections |
| **Discussion** | **ABSENT** | — |
| §5 Limitations | present, **the strongest section in the paper** | 14 bullets |
| §6 Conclusion | present | one paragraph, ~200 words |
| **Figures** | **ZERO** | see §5 below |
| Tables | present | **6** |
| References | present | was 18 entries; **8 works cited in §2.2 had no reference entry at all**, added under this order → 26 |

Three observations the table does not carry.

**There are no figures at all.** The word *figure* appears twice in the draft and
both times it means *number* — "every figure here travels with the noise level
that set it". Four PNGs exist in `outputs/calib_surrogate/figures/` and
`outputs/inv_sweep_surrogate/figures/` and **none is referenced**. A 6,179-word
paper whose central results are a spectrum, a curve, and a pair of overlapping
I–V traces is currently delivered entirely as prose and six tables. This is the
single largest readability defect, and §5 below names the six figures that would
fix it.

**There is no Discussion.** §5 Limitations does the caveating and §6 Conclusion
does the summarising, and nothing does the synthesis — the section where the
identifiability result, the global result and the gradient-fidelity result are
put in one frame and the reader is told what they add up to. §6 gestures at it in
one sentence and then lists.

**§4.2 is 988 words — more than twice the introduction and the whole of §2 put
together (291 + 187).** That is not automatically wrong; §4.2 is where the work
is. But it was **13.7× the pre-edit related-work paragraph**, and that imbalance
is what a reviewer's eye lands on first.

---

## 2. Contribution placement — where the reader first learns what was found

**The predicted pathology is absent.** A paper built by an audit loop is expected
to put the methods before the contribution. This one does not: the contributions
list is at **§1, paragraph 2**, immediately after a four-sentence motivation and
long before §2 Background. The reader learns what was found on the first page.

Three real placement defects sit inside that structure.

**(a) The list omitted the result the abstract calls the one that ties the
pipeline together.** Items 1–6 covered the solver, the local analysis, the
witness pairs, the protocol, the acquisition negative result and the audit
ledger. §4.8 — *the identifiability spectrum predicts, direction by direction,
where a learned surrogate's gradients can be trusted* — **was not among them**,
while `docs/NOVELTY_AUDIT.md` §6.2 rates it (as `C6`) the project's highest
novelty candidate and the abstract gives it a paragraph beginning "Finally — and
this is the observation that ties the pipeline together". A contribution the
paper's own novelty audit ranks first was missing from the contributions list.
**Corrected under this order** as item **7**, appended rather than inserted: `docs/G10_RESULT.md` §6.1 records item 6 being added at generation 10, and renumbering would silently break that dated reference. Where it belongs in the list is a separate question, and it is in the recommendations document.

**(b) The first thing the reader is told is the least distinctive thing the paper
did.** Item 1 is the solver's convergence contract. It is good engineering and it
is not why anyone would cite this paper. Items 2, 3 and 7 are. The ordering is
chronological — the order the work happened in — rather than ordered by what a
reader should carry away. Reordering is a claim-sentence-adjacent change and is
proposed in the recommendations document rather than applied.

**(c) Item 5 states a framing the paper's own §4.6 withdraws.** The item reads
*"uncertainty-driven bias acquisition does not beat random selection"*. §4.6 says
that was an earlier version's finding and that re-measurement showed it is *"not
neutral but **actively harmful**"* (−0.31 mean rank against random, 2 wins / 9
losses), and `docs/NOVELTY_AUDIT.md` §6.3 records the neutral framing as
**withdrawn**. The contributions list is carrying a withdrawn claim. This is an
internal inconsistency a reviewer will find, and it is a claim sentence, so the
fix is in the recommendations document.

---

## 3. The abstract test

**Can a reader who has never seen this repository state, from the abstract alone,
what was found and why it matters?**

**No — not from any single sentence.** The two halves both exist, at word 130
and word 581 of a 754-word abstract, and are **451 words apart**.

The opening sentence is framing rather than finding:

> *"We present an audited, reproducible pipeline for inverse semiconductor doping
> recovery from terminal current–voltage measurements, and use it to put numbers
> on four things this area usually states qualitatively."*

That tells the reader the paper is careful. It does not tell them anything was
found. The nearest sentence carrying **what was found** is in the third
paragraph:

> *"…a 19-point forward-bias sweep over an 0–0.9 V observation window at 2%
> relative measurement noise determines only 3–4 of 16 profile degrees of
> freedom…"*

and the nearest sentence carrying **why it matters** is in the sixth:

> *"…'the surrogate is accurate' and 'the surrogate's gradients are usable' are
> different claims, and the spectrum says which directions the second one
> covers."*

No sentence carries both. The first sits at word 130, the second at word 581,
and *"We claim no new method"* is at word 731 — so the reader meets the
disclaimer 150 words after the only sentence that says why the work matters.

Two structural consequences follow. First, at **754 words** the abstract is three
to five times any workshop limit and will be cut by someone — the only question
is whether the authors choose what survives. Second, the *First / Second / Third
/ Finally* scaffold asks the reader to hold four results with no ranking among
them, so the one the paper cares about most arrives last and unmarked as the most
important.

---

## 4. Scoping versus legibility in §4.2

The instruction is to separate qualification that is **load-bearing** from
qualification that **obscures**, and only the second is a problem. The finding is
that §4.2 has almost no qualification of the second kind — **and is still hard to
read, because the qualifiers are in discovery order rather than reader order.**

### 4.1 Load-bearing — removing these changes the truth value

| # | qualifier | why it is load-bearing |
|---|---|---|
| L1 | *in chart L at `d=16`* | §3.2 establishes that numbers from different charts are over different manifolds. Without the label the number is over an unstated manifold. Guard-enforced by `SPEC-g7-6`. |
| L2 | *at 2% relative noise* | The count is a threshold against an **absolute** cutoff. §4.1 shows the same device moving across noise levels from 20% down to 1e-4%. The integer is meaningless without the level that set it. |
| L3 | *about a fixed 0.525 V centre* | This is what separates the width axis from the spacing axis. It is not a caveat, it is the experiment. |
| L4 | *at 12 of 12 operating points tested* | The surviving form of a pre-registered falsifier that fired. Removing it restores the ranking claim `SPEC-g9-1` killed. |
| L5 | *local* | `PH-21`, and the reason §4.3 exists at all. |
| L6 | *in the normalised spectrum* | Without it the trailing-value growth is arithmetically inconsistent with the leading value moving downward in the same paragraph. |

Six qualifiers, all earning their place. This is the paper's discipline working
rather than obstructing.

### 4.2 Obscuring — removing these costs nothing

| # | what obscures | where |
|---|---|---|
| O1 | **The scope tuple is re-declared three times.** *"both in chart L at `d=16` and both at 2% relative noise"* opens the section; three paragraphs later, *"Over 16 bias points at 2% noise in chart L at `d=16`"*; §4.8 then restates the whole tuple again. §3.2 already declares this as a standing convention. | §4.2 opening, §4.2 ¶4, §4.8 ¶1 |
| O2 | **The withdrawn claim gets more space than the surviving one.** The surviving one-against-three result is one sentence; the *"This was pre-registered the other way round"* paragraph that follows spends ~90 words on 2-of-12 and 0-of-12 statistics about a claim that is **no longer being made**. The provenance is a virtue; its placement makes the section's headline look like a retraction. | §4.2 ¶3 |
| O3 | **Three falsifications stacked with no topic sentence.** The flattening paragraph refutes rigid-sliding, then decomposes scale against shape, then refutes leading-vector broadening — three pieces of evidence for one conclusion that is never stated first. | §4.2 ¶5 |
| O4 | **317 words of failure precede the finding.** The failure block opens at word 487 of a 988-word section and the blockquote the section itself calls *"the paragraph we are willing to put our name to"* does not arrive until word 804 — so a third of the section, positioned squarely in its middle, is what did not work. A reviewer who stops early reads §4.2 as a null result. | §4.2 ¶6–9 |
| O5 | **The smoothness reading is stated twice** within 200 words — once in the characterisation paragraph, once inside the blockquote. | §4.2 ¶10 and the blockquote |
| O6 | **The surviving hypothesis hedges four times in five sentences** — *"without claiming it"*, *"consistent with everything measured here and established by none of it"*, *"would explain"*, *"a statement about conditioning rather than"*. One hedge does this job. | §4.2, final paragraph |

**The diagnosis.** §4.2 is not over-qualified. It is **ordered by the sequence in
which the authors learned things**, which puts the confession before the claim
four separate times. A reader needs the finding, then the evidence, then the
failures. A signposting paragraph naming that shape was added at the head of the
section under this order — it asserts nothing, and it lets a reader skip to the
blockquote. Reordering the section's body is proposed in the recommendations
document, not applied.

---

## 5. Figures — what a figure would carry better than prose

Six, each named with the artefact it would be generated from. **None is created
here.**

| # | figure | what it carries that prose does not | artefact |
|---|---|---|---|
| **F1** | Singular spectrum against the noise floor, four device families, chart L at `d=16`, with the cutoff drawn as a horizontal line | Makes the *threshold count* visible. §4.1 says twice, in prose, that the integer is a count against a cutoff and not a gap between two populations; one plot with the cutoff drawn ends the argument. | `outputs/identifiability/identifiability.json` |
| **F2** | Identifiable count against bias-window **width**, two devices, with the **spacing** control overlaid as a flat line | **The most persuasive single object the paper could have.** The whole of §4.2's second measurement — one rising curve and one flat one, in one panel. Currently four numbers in a sentence. | `outputs/g9/rank_obs.json` |
| **F3** | Normalised spectrum against window width, with the scale/shape decomposition as a stacked bar per index | Carries the flattening result and the 95.6–97.9% shape share, and shows the leading value moving *down* while the trailing ones rise — the fact that makes the whole paragraph work and that prose has to assert. | `outputs/close/spectrum_shape.json` |
| **F4** | **The headline pair.** Two doping profiles overlaid (junctions at 694 nm and 271 nm), their two I–V curves overlaid beneath, with the 2% band shaded | **The figure a device reviewer would understand the entire paper from.** Two visibly different devices, two curves inside the noise band. It does not exist. | `outputs/close/wit02_register_v3.json` plus the SG solver |
| **F5** | Profile-likelihood barrier along the straight line between pair members: chart G at `d=4` against chart J and chart L at `d=16`, floor drawn, with a dashed hypothetical shallower path | Makes the ridge/basin contrast visible **and** makes the upper-bound caveat visible instead of textual — the dashed path is the honest picture of what was not computed. | `outputs/g10/ridge_basin.json` |
| **F6** | Cosine agreement between reference and surrogate directional derivatives against singular-value index, cutoff marked, both training budgets | Carries §4.8 — the contribution the abstract calls the tying-together one — as a one-glance result: points near +0.5 left of the line, near 0 right of it, and the two budgets on top of each other outside. | `outputs/gradient_fidelity/gradient_fidelity.json` |

Two existing PNGs — the reliability diagrams in
`outputs/calib_surrogate/figures/` — are already generated and unreferenced, and
would serve §4.5 as they are.

---

## 6. Related work — what must be engaged, and where the gap is open

`CITE-01` governs: gaps are reported here and **not filled**. A reference this
audit cannot open does not appear in this document or in the paper. §2.2 was
rewritten under this order into a four-strand skeleton carrying exactly the
verdicts below.

| strand | what the section needs | state |
|---|---|---|
| **(a) Local identifiability practice in device inversion** | The canonical formulation of doping identification in the stationary drift–diffusion system, and its known ill-posedness | **COVERED, verified.** Burger, Engl, Leitão & Markowich 2001 and 2004; Burger, Engl, Markowich & Pietra 2002; arXiv:2408.11485; the 1990–91 *Solid-State Electronics* inverse-device-modelling line. All carry retrievable sources in `docs/NOVELTY_AUDIT.md` §Sources. |
| **(a′) SVD analysis of the doping-to-measurement map specifically** | A source for `NOVELTY_AUDIT`'s own assertion that *"singular-value analysis of the doping-to-measurement map also already appears in this literature"* | **GAP, and it is one of ours.** That sentence is stated in the repository **without a citation**. Aster, Borchers & Thurber covers the method generically; nothing cited covers it *in this problem*. The paper's central method may therefore be either standard practice or a small contribution, and the repository does not currently know which. |
| **(b) Experiment design** | The design criteria §4.6 compares, and prior optimal-design work for this problem class | **COVERED, verified.** Fedorov 1972; Atkinson & Donev 1992; Alexanderian et al. 2014; arXiv:1711.05878, arXiv:1802.06517, arXiv:2402.16520 — all recorded in `NOVELTY_AUDIT` §6.1. **Three of those six were verified in the repository and had never been cited in the paper**; §2.2's rewrite adds them. |
| **(c) Global identifiability methods** | A positioning of the witness-pair search against structural identifiability (differential-algebraic and series methods) and against practical identifiability by profile likelihood — including why the formal route was not taken | **GAP, OPEN, and the most consequential of the four.** §4.3 *uses* a profile-likelihood construction and cites nothing for it. The paper has no statement of what a formal result would establish that a search cannot. |
| **(d) Parameterisation choice in inverse problems** | Prior work on discretisation as regularisation, and on how a recovered object depends on the parameterisation chosen | **GAP, OPEN, complete.** The *chart* construction of §3.2 is the paper's own framing and carries **no citation of any kind**. The paper asserts and measures the dependence without locating either in the literature. |

**Effort estimate for the two open gaps:** one literature session each. Neither
is a research problem; both are searches that have not been run. They are the
paper's cheapest large improvement at a methods venue.

---

## 7. Reviewer simulation

Three personas, their objections in their own voice, and for each: **can the
repository answer it, and with what artefact.**

### 7.1 The device physicist

> *"You have a 1D drift–diffusion model with constant mobility, Boltzmann
> statistics, no interface traps and ohmic Dirichlet contacts, and you are
> telling me something about what I can measure on silicon."*

**Partially answerable.** §5 states every one of those restrictions. What the
repository cannot supply is any evidence that the *identifiability conclusion*
survives them — the 2D solver handles Poisson without continuity, so the question
has never been asked in 2D. §5 lists the model restrictions; it does not say that
the conclusion is untested under them. That distinction belongs in the paper.

> *"Where does 2% relative Gaussian noise come from? Real I–V measurement is not
> relative-Gaussian across ten decades of current — near the floor it is
> additive, and the instrument switches ranges."*

**NOT ANSWERABLE. This is the paper's most exposed assumption and the repository
contains no justification of it anywhere.** A search of the audit ledger, the
rulings, the claim-evidence matrix and the paper returns the noise model
*stated* — *"independent Gaussian in relative current at a level of 2%"* — and
never *argued*. Every rank number in the paper is a threshold count against this
number. There is no artefact to point at.

> *"Would the 694 nm / 271 nm pair survive a real measurement chain — series
> resistance, self-heating, contact non-ideality, temperature drift?"*

**NOT ANSWERABLE, and the objection is sharper than it first looks.** The forward
model has no series resistance. The rank gain in §4.2 comes from *widening the
bias window*, and the top of that window is exactly where series resistance and
self-heating dominate a real diode's I–V. **The mechanism that gives the paper
its result is the mechanism a real measurement chain would most distort.**
Nothing in the repository addresses this.

> *"Ten decades of current in one sweep?"*

**Partially answerable.** §4.4 reports the measured range and the 13 dropped
(profile, bias) pairs that fell below the solver's own floor. What is absent is
any statement that a real sweep would be range-switched with per-decade accuracy,
which is a different noise model again.

> *"Is the solver right?"*

**Strongly answerable, and it is the paper's best-evidenced claim.** §3.1's error
bar tracking `1/SNR` across five decades; §4.10's four physics defects each with
a regression test; the corrected 2D Newton Jacobian reproducing textbook
inversion pinning near `2φ_F`; per-run manifests under `outputs/*/manifest.json`.

### 7.2 The inverse-problems methodologist

> *"Your witness pairs are drawn from a prior. A narrower physical prior might
> exclude them entirely. What is the prior dependence of the global result?"*

**ANSWERABLE FROM THE REPOSITORY AND ABSENT FROM THE PAPER — the cheapest fix in
this audit.** `docs/CLAIM_EVIDENCE_MATRIX.md` §7 states it in as many words:
*"nothing outside the stated prior (a narrower physical prior could exclude these
witnesses entirely)"*. §8 gives the prior, its bounds and its hash
(`236ff6576a850965…`), and records that chart J's junction coordinate carries its
own prior and its own hash. **§5 of the paper does not mention prior dependence
at all.** The answer exists, is hashed, and is not in the paper.

> *"Local and global are different claims, and papers in this area routinely
> conflate them."*

**Strongly answerable.** `PH-21` forbids reporting a local rank without the word
*local*; `COR-1` is a recorded correction of exactly that slip; §4.3 exists
because the distinction is real; and the claim-surface guards enforce it
mechanically across the whole tree. This is the paper's strongest methodological
position, and it is currently invisible to a reader, because the guards are not
mentioned in the paper.

> *"Your barrier is a straight line in chart coordinates. That is an upper bound.
> You have not computed a minimum-energy path, so you cannot claim a basin."*

**Answerable, and the paper already volunteers it.** §4.3 states it, §5 repeats
it, and `docs/CLAIM_EVIDENCE_MATRIX.md` §9 records that the repository had the
bound direction *backwards* for a generation and corrected it, weakening both
`d=16` results to search statements as a consequence. A reviewer raising this
finds the paper already there.

> *"'Witness pair' is doing work that a formal identifiability result would do
> better."*

**NOT ANSWERABLE, and it is this reviewer's strongest card.** No structural
identifiability analysis was attempted, and the paper never says why not. There
may be a good reason — the forward map is a PDE solve, and differential-algebraic
methods may be infeasible at `d=16` — but the repository does not contain that
argument. This is the same gap as related-work strand (c).

> *"Your 'rank' is a count above a threshold, not a rank."*

**Answerable, said once, and buried.** §4.1 says exactly this in an italicised
mid-paragraph aside and gives the gap collapsing from 230.6× to 4.99×. It is a
concession that would read better as a definition, stated at first use.

### 7.3 Reviewer 2

> *"What is new here relative to standard practical-identifiability analysis?"*

**Answerable — and the paper's answer currently works against it.**
`NOVELTY_AUDIT` concludes that no component is methodologically new, and the
paper says *"We claim no new method"* twice, in the abstract and in the
conclusion. The defence exists — `NOVELTY_AUDIT` §6.2 rates the gradient-fidelity
framing (`C6`) as *"low as method; moderate as a diagnostic framing and a
measured result"*, and characterises the closest prior work as reaching a **more
optimistic** conclusion in another domain without an undertraining control.
**The paper never deploys that as a defence.** It concedes, and then does not say
what remains.

> *"`MECH-01` is open. That is a hole."*

**Well answered, and it is a genuine strength.** Three pre-registered methods,
each with its measured failure mechanism; one registered decision rule whose
label the measurement contradicted, reported as contradicted rather than
relabelled (`docs/UEMPIR_MECH01_g14.md`); one surviving hypothesis named as
future work and not claimed. A reviewer pressing this gets a better answer than
most papers give to a solved question.

> *"Is the ordering result a finding, or a restatement of 'measurement design
> matters'?"*

**Partially answerable, and this is the sharpest objection in the simulation.**
The answer exists in §4.2 and is never framed as an answer. It has three parts:
the observation set is not merely *one* factor but dominates three others by an
order of magnitude at every operating point tested; the original *ranking* claim
was falsified by the authors' own pre-registered test, and the surviving claim is
the weaker one; and the mechanism is spectrum **flattening** rather than gain,
which is a specific and falsifiable statement that "measurement design matters"
does not make. **What the paper never does is say what a reader would have
predicted instead** — and without that contrast the result reads as a
quantification of the obvious.

> *"Does the paper overstate?"*

**No, and the risk runs the other way.** Fourteen limitation bullets, three
failed mechanisms reported at length, a withdrawn ranking claim, a withdrawn
neutrality claim, *"we claim no new method"* twice, and a conclusion that ends on
what is open. A reviewer may reasonably conclude the authors do not believe their
own paper. **Under-claiming is this draft's characteristic failure mode**, and it
is the direct consequence of fourteen generations optimising for every sentence
being true.

### 7.4 The objections with no answer in the repository

These are the paper's real limitations. They belong in §5, in the paper's own
voice, not as a defensive appendix. Proposed wording is in the recommendations
document.

1. **The noise model has no stated basis.** 2% independent relative Gaussian is a
   modelling choice, it is load-bearing for every rank number in the paper, and
   nothing in the repository argues for it.
2. **Measurement-chain realism is untested.** No series resistance, no
   self-heating, no contact non-ideality — and the rank gain lives at the top of
   the bias window, where those dominate.
3. **No structural-identifiability analysis was attempted, and no reason is
   given.** Either the reason is stated or the analysis is done.
4. **The identifiability conclusion is untested outside 1D constant-mobility
   Boltzmann transport.** §5 lists the model restrictions but does not say the
   *conclusion* has never been checked under them.
5. **Prior dependence of the global result is unstated in the paper.** Unlike the
   other four, this one is answerable today from `CLAIM_EVIDENCE_MATRIX` §7–§8 —
   it is an omission rather than a hole.

---

## 8. Venue analysis — two framings, both reported, neither chosen

The choice changes emphasis far more than content. **This audit does not choose;
that is the operator's.**

### 8.1 Device audience

**The headline sentence becomes** a statement about silicon rather than about
spectra: terminal I–V cannot locate the metallurgical junction to better than
roughly four hundred nanometres in a one-micron device, once the doping either
side of it is free to compensate.

**What §4.3 becomes.** The lead. The headline pair moves to Figure 1 (**F4**
above) and grows a physical reading: 694 nm against 271 nm is **423 nm apart in a
1000 nm device** — arithmetic already published in `docs/G8_RESULT.md` and
`docs/CLAIM_EVIDENCE_MATRIX.md` §H7a, but present in the paper only as the two
endpoints. The grid-refinement survival (1.7% under `N = 301 → 1201`) and the
`WIT-02` refinement battery become the credibility argument rather than
procedural detail.

**What §4.2 becomes.** The methods contribution supporting it, and it shrinks.
The three failed mechanism hunts compress to a paragraph and a pointer at the
audit documents; a device reader does not need `corr(dz, b)` running −0.95 to
−0.98.

**What the repository can supply.** The 423 nm framing (arithmetic on published
numbers); the refinement battery and its survivor counts; the equivalence twins
(up to 1.26× local doping difference against 0.02–1.3% I–V difference); the
convergence contract and the four physics defects, which are exactly the
credibility a device audience asks for first.

**What it cannot.** Any statement that the pair survives a real measurement
chain. Any 2D result. Any experimental validation on a fabricated device. Any
statement about what instrument *would* resolve the junction. A device reviewer
will ask all four, and the honest answer to each is that the study is
computational.

### 8.2 Methods audience

**The headline sentence becomes** a statement about measurement protocols in
general: identifiability is a property of the measurement protocol rather than of
the system — measured rather than asserted, with the mechanism narrowed to
spectrum flattening and the residual explicitly open.

**What §4.2 becomes.** The lead, and it stays long — the twelve-operating-point
comparison, the falsified ranking, the flattening decomposition and the three
characterised failures are all load-bearing for a methods reader.

**What §4.3 becomes.** Support: evidence that the local statement is not the
whole story, with the dimension-dependence result as a secondary finding. The
device specifics become one illustrative example rather than the headline.

**What §4.8 becomes.** Second position, promoted from eighth. It is the transfer
result — a spectrum measured on the physics predicts something about a *learned*
model that was never measured — and at a methods venue that is the argument for
why the identifiability measurement was worth making at all.

**What the repository can supply.** The twelve-point comparison; the
pre-registration record and a falsifier that fired against its authors; the
`U-EMPIR` treatment of a decision rule whose registered meaning the data
contradicted; the 33× training-budget control that excludes undertraining.

**What it cannot, and it is fatal to the framing as stated.** The generalisation
— *past semiconductors* — is asserted by framing and evidenced on **one PDE
family, one solver, one problem class**. There is no second system. A methods
reviewer's first question is what happens on a different forward map, and the
repository has nothing for it.

**The asymmetry is this section's finding.** The methods framing has the more
general claim and the weaker evidence for the thing that makes it general. The
device framing has the narrower claim and can evidence all of it. The device
framing has no single fatal question; its four weaknesses are all of the ordinary
*this is simulation* kind.

---

## 9. Prioritised — what most improves the chance of acceptance, effect over effort

| # | action | effort | effect | why |
|---|---|---|---|---|
| 1 | **Generate the six figures of §5.** | moderate — every artefact already exists | **very high** | A 6,200-word paper with zero figures, on results that are inherently graphical. F2, F4 and F6 alone change how the paper reads. |
| 2 | **Cut the abstract from 754 words to ~200, leading with one sentence carrying finding *and* consequence.** | low | **very high** | It is three to five times any limit and will be cut by someone. §3 above identifies the two halves that need joining. |
| 3 | **Add prior dependence to §5.** | trivial | high | Answers the methodologist's first question; the answer is already hashed in `CLAIM_EVIDENCE_MATRIX` §7–§8. A pure omission. |
| 4 | **State the noise model's basis, or state that it has none.** | trivial | high | The most exposed assumption in the paper, load-bearing for every rank number, currently invisible. One sentence removes a reviewer's best surprise. |
| 5 | **Reorder §4.2 so the finding precedes the failures.** | low–moderate | high | §4 above. No sentence needs rewriting; four blocks need moving. |
| 6 | **Fix contributions item 5 to match §4.6.** | trivial | moderate | An internal inconsistency carrying a withdrawn framing. Reviewers find these. |
| 7 | **Close related-work gaps (c) and (d).** | moderate — one literature session each | high at a methods venue | Two whole strands unengaged, one of which the paper's own method belongs to. |
| 8 | **Say why structural identifiability was not attempted.** | low | moderate | Converts the methodologist's strongest card into a scoping decision. |
| 9 | **Add a Discussion section.** | moderate | moderate | Nothing currently synthesises the three main results into one statement. |
| 10 | **Deploy the novelty defence instead of only conceding.** | low | moderate | The paper says *"no new method"* twice and never says what remains. `NOVELTY_AUDIT` §6.2 and §6.4 contain the argument, already written. |
| 11 | **Choose the venue and reorder §4 accordingly.** | low once chosen | high | Blocked on a decision that is the operator's, not the loop's. §8 reports both framings and chooses neither. |

**Items 3, 4, 6 and 8 are four sentences of work between them**, and they close
two of the three reviewer personas' opening questions. They are the highest ratio
in the table, and every one of them is a claim sentence — so all four are in
`docs/PAPER_RECOMMENDATIONS_g15.md` and none is applied.

---

## 10. What this audit did not do

- It did not change a claim sentence. Every proposal that touches one is in the
  recommendations document.
- It did not create a figure. §5 names six and generates none.
- It did not fill a citation gap. `CITE-01`: two strands are reported open and
  stay open.
- It did not choose a venue. §8 reports both framings, as ordered.
- It did not measure anything. No script was run against the physics; every
  number quoted here is read from `papers/draft.md` or from an artefact already
  in the tree.

---

## 11. `AGE-01` applied to this document

This document and `docs/PAPER_RECOMMENDATIONS_g15.md` both quote results, so
under the rule enacted at `65bef05` they cannot sit on neither list. Both are
added to `EXEMPT` in `tests/test_claim_surface_g7.py` with their reason: they are
**editorial records that quote the paper's claims in order to assess how they
read**, and neither publishes a result of its own. That is the same class as
`docs/REPRO01_LEAF_AUDIT_g6.md` and `papers/CORRIGENDA_g6.md`, which quote
published numbers in order to check or correct them.

The work order was written against the rules in force at `65bef05` and asked for
two new documents without naming this obligation. Noticing that the decision was
needed is the whole of `AGE-01`; making it costs one line each.

**`EOL-02` caught this order's own work, on the same pass.** The Python edits
that produced the corrected numbers in §1 and §3 wrote in text mode without
stating a line ending, so `docs/PAPER_RECOMMENDATIONS_g15.md` went into the index
as `LF` and came back out of the editor as `CRLF`.
`test_line_endings_g6.py::TestCheckoutReturnsWhatWasCommitted` failed on exactly
that one file — *a fresh checkout would alter it* — and on nothing else, because
the other four files this order touched were already `CRLF` in the index and the
same defect happened to preserve them. Both new documents are now written with an
explicit `newline="
"`, matching the twenty-of-twenty-six convention in `docs/`.

That is the second time in two generations that a guard has caught the generation
enacting it, and it is the intended behaviour rather than an embarrassment: the
rule that every text-mode write states its line ending was enacted at generation
13 precisely because inheriting the platform's default is invisible until a
checkout on another machine changes a file nobody edited.
