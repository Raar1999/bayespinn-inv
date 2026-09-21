# ADR-0008 — The paper is written for a device audience, not a methods one

**Status:** Accepted · **Date:** 2026-08-29 · **Decided by:** operator ruling of
2026-08-29 §5, which reserved the call and then made it
**Relates to:** `docs/adr/ADR-0003-scope-of-the-research-claim.md`,
`docs/PAPER_AUDIT_g15.md` §7, `docs/NOVELTY_AUDIT.md` §6.2, `papers/draft.md`

## Context

`docs/PAPER_AUDIT_g15.md` §7 simulated three reviewers against the draft and
reported the objections each would raise, marking for every objection whether the
repository can answer it. The audit reported the resulting asymmetry and declined
to choose between two framings, because which venue the paper is written for is
an editorial decision rather than a measurement.

The two framings were:

**Methods framing.** The contribution is the identifiability machinery — the
chart construction, the rank-as-a-property-of-the-measurement result, and the
gradient-fidelity prediction — with drift–diffusion as the worked example.

**Device framing.** The contribution is what terminal I–V can and cannot
determine about a doping profile, with the identifiability machinery as the
instrument that establishes it.

## The asymmetry that decides it

**The methods framing carries a single fatal question.** It rests on
generalisation past semiconductors, and every result in this repository is
evidenced on **one PDE family with no second system tested**. A reviewer asks
*"what makes you think this transfers?"* in one sentence, and there is no answer
anywhere in the tree — not a weak answer, no answer. A framing whose central
claim has no evidence behind it is not a framing this project can defend, and the
whole discipline of the audit loop is against asserting it.

**The device framing's weaknesses are the ordinary kind.** `PAPER_AUDIT_g15.md`
§7.1 lists four: the 1D model with constant mobility and Boltzmann statistics; the
unargued relative-Gaussian noise model; the absent measurement chain; and the
ten-decade sweep. Every simulation paper in this field carries some version of
all four, and reviewers accept them when they are stated. This paper's
limitations section is stronger than most published ones, and after the additions
of 2026-08-29 it states all four explicitly, including the sharpest — that the
mechanism producing §4.2's result is the mechanism a real measurement chain would
most distort.

Four ordinary weaknesses that are stated beat one fatal question that is not
answerable.

## Decision

**The paper is written for a device/TCAD audience.**

1. **The headline is the 694 nm / 271 nm junction pair.** Two devices whose
   metallurgical junctions sit 423 nm apart in a 1000 nm device, whose terminal
   I–V curves differ by at most 1.79% over the measured window. It is Figure 1,
   it opens the abstract, and it appears in §1 before §2 Background.
2. **The observation-set result is the supporting methods contribution**, not the
   product. It is what makes the headline a general statement rather than an
   anecdote about one pair.
3. **The generalisation claim is kept, and kept as conjecture.** It is a single
   labelled paragraph in §6 saying what we would *expect* to transfer — that the
   parameterisation is part of the claim, and that gradient trustworthiness
   follows the identifiable subspace — with an explicit statement that neither is
   established by the evidence here and that testing them needs a second forward
   model. It is not the frame and it is not in the abstract.
4. **The venue line at the head of the draft says all of this**, so that a reader
   who never opens this file still learns which document they are reading.

## Options considered

1. **Methods framing.** Rejected. The generalisation claim it needs is
   unevidenced and the repository knows it; `ADR-0003` already established that no
   component of this project is methodologically new, which removes the other
   route to a methods contribution.
2. **Device framing.** Chosen.
3. **Neither — split into two papers.** Not considered seriously and recorded so
   the omission is deliberate. There is one result set; splitting it would leave
   both halves thinner and would put the same figures in two places.

## Consequences

**Accepted, and worth naming.** The gradient-fidelity result of §4.8 is the
project's highest-ranked novelty candidate — `docs/NOVELTY_AUDIT.md` §6.2 rates
it *"low as method; moderate as a diagnostic framing and a measured result"* —
and a device venue is not where that lands hardest. This decision costs the paper
its best methods card. It is taken anyway, because the alternative is to lead
with a claim we cannot support, and a well-placed weaker card beats an
unsupportable stronger one.

The result is not hidden. It is contribution 7, it is Figure 3, it is foregrounded
in the roadmap by importance, and the abstract's opening paragraph names it as
the sharpest consequence of the measurement. What changes is that the paper does
not *rest* on it.

## Reversal

If a second forward model with different physics is put through the same protocol
and the two transferable statements of §6 hold, the generalisation claim becomes
evidenced and the methods framing becomes available. That experiment has not been
run and is not scheduled. Until it is, this ADR stands, and reopening it requires
that measurement rather than an argument.
