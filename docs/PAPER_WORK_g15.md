# PAPER_WORK_g15 — what the close-out ruling ordered, and what came of it

**Ordered by** operator close-out ruling of 2026-08-29, §§1–7
**Not a generation.** No `LOOP_STATE` increment, no ladder movement, no spec.
**Supersedes forward** `docs/PAPER_AUDIT_g15.md` §4.1 row `L1` and §5's closing
paragraph, at §4 below. That document is a dated record and is not edited.

---

## 1. The ledger

| § | ordered | state |
|---|---|---|
| 1 | commit both documents, the structural edits and the `EXEMPT` entries, having **verified** the suite fails without them | **done** — `157a785`. The guard that fails is `test_age01_surface_coverage_close`, not `test_claim_surface_g7` |
| 2 | do not make the repository public; check which billing state blocks CI | **recorded, operator action** — `docs/OPERATOR_TASKS.md`, final entry. `CI-01` unchanged |
| 3 | score `WINDOWS_RISK_g6.md` against local Windows evidence; check `NB-02` by running the notebook step first | **done** — `docs/WINDOWS_LEG_SCORED_g15.md`. Four of five confirmed, none refuted, `NB-02` reproduced |
| 4 | no 3.9 leg; floor stays 3.11; nothing reopens | **confirmed, nothing reopened.** One consequence found: the *paper* still said 3.9 |
| 5 | call the venue | **device audience** — `docs/adr/ADR-0008-...md` |
| 6.1 | figures, `F4` first, then `F2` and `F6` | **done** — `scripts/make_figures_g15.py`, Figures 1–3 in the draft |
| 6.2 | argue the 2% floor as a sensitivity | **done** — `scripts/floor_sensitivity_g15.py`, stated in §4.3 |
| 6.3 | reorder §4.2 and the abstract | **done** |
| 6.4 | keep contribution 7's number, foreground it | **done** |
| 7 | source the related-work gaps yourself and verify each | **done** — six references, each opened, each confirmed through Crossref |

Two corrections were forced by the work rather than ordered by it: `COR-2` and
`COR-3` in `papers/CORRIGENDA_g6.md`.

---

## 2. What the figure work actually bought, which was not a figure

`F2` was ordered as the second-most valuable figure. Its value turned out to be
that **labelling it found a false claim in the paper.**

To draw the axis label the script needed the chart the curves were measured in.
`scripts/run_g9.py::phase_rank_obs` calls `cell_spectrum(sg, G16, m16, b, cfg)`
and contains no `ChartL`; `docs/CLAIM_EVIDENCE_MATRIX.md` row `I5` has said
**chart G, `d=16`** since generation 9. The paper said **chart L** at three
sites. `COR-2` has the full record.

The general form is worth stating because it is cheap to repeat: **a figure has
to be labelled from the code, and prose does not.** A sentence can carry a scope
label that nobody checks. An axis cannot be drawn without deciding what the axis
is. Making a figure is therefore a claim-checking operation, and it found a
defect that fifteen generations of guards, a claim surface, four claim-surface
modules and an editorial audit had all passed over.

`F4` was built to cross-check itself for the same reason: it re-derives the
694 nm and 271 nm junction positions through `ChartJ.junction_position` and
asserts them against `outputs/g9/junction_refine.json` to 1e-12, so the figure
is not the only place its own headline number is computed.

---

## 3. Guard limitations this exposed, none of them fixed here

Three, each named and left open, because each costs a generation to close and
this was a paper task.

**`SPEC-g7-6` checks presence, not correctness.** It requires a rank fraction to
carry a chart label. It cannot check the label is right, because nothing binds a
sentence to the artefact its number came from. `COR-1`'s applied record shows the
labels being added *under this guard's pressure*; at least one was added wrong.
A guard that demands a field it cannot validate converts a missing label into a
wrong one, and a wrong label is worse — it reads as scoped, so nobody re-checks
it.

**The artefact cannot arbitrate.** `cell_spectrum` returns `chart` and
`chart_label`; `phase_rank_obs` drops both when building its rows. So
`outputs/g9/rank_obs.json` does not record the chart its own numbers were taken
in. Fixing it means re-running generation 9 under `R-4`, which is not a paper
task.

**Nothing binds a summary claim to the section that evidences it.** `COR-3`: the
contributions list carried the withdrawn *neutral* framing of the acquisition
result while §4.6 carried the surviving *harmful* one, three hundred lines apart.
A guard failing when a framing recorded as withdrawn still appears in the tree is
cheap and does not exist.

---

## 4. Two corrections to `docs/PAPER_AUDIT_g15.md`

That document is a dated record. It is not edited; this section supersedes it
forward, and both corrections are of the same kind — the audit reasoned correctly
about a case it had not checked.

**§4.1, row `L1`.** The table lists *"in chart L at `d=16`"* as a **load-bearing**
qualifier of §4.2, on the reasoning that without the chart label the number is
over an unstated manifold. **The reasoning is right and the example was false**:
that qualifier was load-bearing *and wrong*, which is a stronger illustration of
the audit's own point than the one it chose.

**§5, closing paragraph.** It says the two reliability diagrams in
`outputs/calib_surrogate/figures/` *"are already generated and unreferenced, and
would serve §4.5 as they are"*. **They would not, and referencing them would have
repeated `COR-2`.** They are from a different run:

| | `outputs/calib_surrogate/summary.json` | paper §4.5 |
|---|---|---|
| temperature | `T = 5.07` | `T = 2.08` |
| sample sizes | `n_val` 80, `n_test` 120 | `n = 140` |
| ECE | 0.223 → 0.086 | not reported |

The coverage direction disagrees too — the diagram shows the ensemble
*over*-covering, while §4.5's table reports it under-covering before
recalibration.

**And there is a decisive reason beyond the mismatch, already recorded in this
repository.** `docs/RELEASE_READINESS.md` §229 states that `calib_surrogate` and
`inv_sweep_surrogate` **predate `RunManifest`** and carry no provenance. Under
this project's own rules an artefact with no manifest cannot back a published
claim. All four unreferenced PNGs come from those two directories.

**So the four PNGs are unreferenced because they should be**, and the audit's
"four PNGs referenced by nothing is its own small finding" resolves the opposite
way to how it was written: the finding is not that the paper is ignoring usable
figures, it is that the paper has been correctly refusing to cite unprovenanced
ones. They are left uncited. Regenerating them under a manifest would make them
usable and is not ordered.

---

## 5. What is now true of the paper

| | before | after |
|---|---|---|
| figures | 0 | **3**, each regenerable by a named command, each with its inputs digested into a manifest |
| abstract | 754 words, finding at word 130, why-it-matters at 581 | **553 words**, both in the first paragraph |
| §4.2 | 317 words of failure before the defended claim | claim first, failures after, with a shape paragraph saying so |
| the 2% floor | asserted everywhere, argued nowhere | a stated sensitivity — witnesses survive to **1.24%**, with the two things that does not mean |
| §5 limitations | 14 bullets, no prior dependence, no noise-model caveat, no measurement chain, a stale 3.9 floor | 18 bullets, all four repaired |
| related work | 4 strands, 2 open gaps | 4 strands engaged, 1 narrower gap left marked |
| references | 26 | **32** |
| known-false claim sentences | 4 (3 chart labels, 1 withdrawn framing) | 0 known |

The paper is longer overall (about 9,800 words) and that is deliberate: the
growth is in limitations, related work and figure captions, and the two sections
a reader meets first are both shorter than they were.

---

## 6. What this did not do

* **`CI-01` and `SPEC-g0-3b` do not close.** Nothing here is a clean-runner CI
  run and the three Linux legs remain entirely unevidenced.
* **`NB-02` is reproduced, not fixed.** Its three fix options stand, narrowed by
  evidence but not chosen.
* **The three guard gaps of §3 are named and open.**
* **No new physics.** Both new scripts read committed artefacts and perform no
  solve. Every number that entered the paper was already measured; what changed
  is which of them are stated, in what order, and under which label.
* **The `(a′)` gap stands** — singular-value analysis of the doping-to-measurement
  map *specifically*. `NOVELTY_AUDIT` asserts it appears in this literature
  without a citation, and a search has not found one. It is marked in §2.2 as
  unsettled rather than filled, under `CITE-01`.
