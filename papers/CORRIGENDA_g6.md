# CORRIGENDA — `papers/**`

Append-only. `papers/**` is operator-reserved (`R-3`), so the loop never edits it.
Where a measurement contradicts a line in the paper, the correction is written
here with its evidence and the operator applies it. One file, appended to — not a
new escalation each time.

Each entry gives: the exact line, its current text, the measured replacement, the
command that reproduces the measurement, the manifest backing it, and the finding
ID that forced it.

---

## COR-1 — `papers/draft.md:255` · identifiable rank stated without its regime

**Finding** `SCI-11` (HIGH), opened `AUDIT_g0`, generation 0
**Rule** `PH-21` — a local Jacobian rank is never reported as an identifiability
result without the word *local*, and `§4.2` of the generation-6 ruling, which
additionally requires the parameterisation dimension, prior, noise and floors.
**Raised by** `tests/test_claim_surface_g0.py::TestParkedPapersInstance`

### Current text (line 255, in §4.6 "Surrogate accuracy does not imply surrogate gradients")

> If terminal I–V determines only 3–4 of 16 doping directions, then a surrogate
> trained only on I–V is constrained only in that subspace.

### Why it is wrong

The number is right; the scope label is missing. `inverse/identifiability.py`
computes a **local** Jacobian rank at one operating point and says so throughout
("the **local** Jacobian", "Local identifiability of a forward map at one
operating point"). The paper labels it correctly three times — lines 23, 73, and
an explicit limitation at line 349 — but not here.

A reader quoting this sentence alone carries none of that context, and "terminal
I–V determines only 3–4 of 16 doping directions" reads as a **global** statement
about the measurement. It is not one. Global, sampling-based non-identifiability
was unmeasured when this was written; generation 6 is the first attempt at it.

The same defect was corrected at six other sites in generation 0 — `README.md`
rows 51, 70, 267 and 340, and `docs/RELEASE_READINESS.md` rows 72 and 189. This is
the seventh and last, and the only one the loop may not touch.

### Measured replacement

> If terminal I–V determines only 3–4 of 16 doping directions **at a given
> operating point** — a *local* Jacobian rank, not a global claim — then a
> surrogate trained only on I–V is constrained only in that subspace.

The minimal change is the inserted clause; the rest of the sentence and the
paragraph that follows are unaffected. §4.6's argument does not depend on the
distinction, which is precisely why the qualifier went missing.

### Evidence

```bash
PYTHONPATH=src python scripts/run_identifiability.py --out outputs/identifiability_g1
```

| | |
|---|---|
| **Manifest** | `outputs/identifiability_g1/manifest.json` |
| **Commit** | `6f1d939d231fbab96885e7d3d5ec84105172a443` |
| **Tree digest** | `0210e79c0ee2bfa90c9afab3bf012672…` |
| **Produced** | 2026-08-25T13:39:09+00:00 |
| **Measured ranks** | `step_symmetric` 4, `step_asymmetric` 5, `graded` 3, `ldd` 4 — all of 16, at 2% noise |
| **Reproducibility** | bit-identical on an independent re-run (`outputs/identifiability_g1b/`, 375 leaves, 0 differing) |

The 2026-08-19 artefact this claim was originally written against is **retired**
and must not be cited — see `docs/REPRO01_LEAF_AUDIT_g6.md`. The regenerated
artefact above supersedes it and carries a `tree_digest`, which the retired one
could not.

### After applying

`tests/test_claim_surface_g0.py::TestParkedPapersInstance` pins the count of
unqualified passages in `papers/draft.md` at **1** and fails in **both**
directions. Applying this corrigendum drops the count to 0, and that test will
fail **by design** — it is the signal to move `papers/draft.md` into the
`CLAIM_SURFACE` tuple in the same file and delete the parked-instance class.

```bash
PYTHONPATH=src python -m pytest tests/test_claim_surface_g0.py -q
```

Declining the correction is also a resolution, provided it is recorded. The
argument for declining would be that line 349 already carries the limitation and
§4.6 does not rest on the distinction. The argument against is that a sentence
readers quote in isolation should be true in isolation.

---

## COR-1 — **APPLIED**, 2026-08-29

**Applied under** the operator ruling of 2026-08-29 §4, which closed the loop and
assigned the paper to it: *"Nothing further is ordered. Mine: the pull request,
and `EXT-05`. Yours: the paper."* That released `R-3` over `papers/**`, which is
the condition this corrigendum was waiting on — nine cycles.

**What was written.** The corrigendum's minimal change is the inserted
operating-point clause, and it is in. Two further qualifiers were added at the
same site, and they are *not* part of COR-1 — they are the price of the guard
transition below, and are recorded here so the difference is visible:

> If terminal I–V determines only 3–4 of 16 doping directions in **chart L** at
> `d=16` **at a given operating point**, over the 0–0.9 V bias window and at 2%
> measurement noise — a *local* Jacobian rank, not a global claim, and one that
> `rank(observation set)` shows moving with the window — then a surrogate trained
> only on I–V is constrained only in that subspace.

`SCI-11` is closed. It was the seventh and last instance, and the only one the
loop could not touch.

**The guard transition the corrigendum predicted, carried out.** COR-1 stated
that applying it drops `TestParkedPapersInstance`'s count to zero and that the
test then *fails by design*, as the signal to move `papers/draft.md` into
`CLAIM_SURFACE` and delete the parked class. Both were done. A pinned count is a
placeholder for a guard; the guard is now the thing.

**And the paper joined the wider claim surface**, which COR-1 did not ask for and
which is a judgement rather than an instruction. `papers/draft.md` is now in
`CLAIM_SURFACE_G7` — and so, by cascade, in `_G9`, `_G10` and `_DOC08` — because
the close-ruling rewrite gave it the local rank, the observation-set result and
the witness sets. That tuple's own stated rule is *"a document that publishes the
result and is not on this list is unguarded"*, and the paper was outside it only
because `R-3` had reserved it. Leaving the strongest statements of the result in
the one document nobody guarded would have inverted the point of the guard.

Joining cost four real corrections, each named by a guard rather than by a
reviewer:

| guard | what it caught |
|---|---|
| `test_claim_surface_g7` | the abstract's global paragraph named no chart; contribution 3 named no chart and no dimension |
| `test_claim_surface_g9` | the repaired COR-1 sentence quoted a rank without its observation window — the defect COR-1 is *about*, in a different coordinate |
| `test_quantifier_scope_doc08` | *"at every operating point tested"*, twice, with no denominator |

The second row is worth keeping. The sentence this corrigendum exists to repair,
once repaired, was still unguarded in a second dimension: it carried its regime
and not its window. A correction written a generation before the guard that would
have caught the rest of it is a correction that fixes what was visible at the
time, and that is an argument for guards over corrigenda, not against this one.

### Evidence

```bash
PYTHONPATH=src python -m pytest tests/test_claim_surface_g0.py \
    tests/test_claim_surface_g7.py tests/test_claim_surface_g9.py \
    tests/test_quantifier_scope_doc08.py \
    tests/test_witness_admissibility_g10.py \
    tests/test_witness_refinement_close.py -q
```

| | |
|---|---|
| **Result** | 217 passed, 9 skipped |
| **Applied at** | 2026-08-29, after the close ruling |
| **Closes** | `SCI-11`, `OT-2` |
| **Supersedes nothing** | this file stays append-only; the entry above is the record of what was written, not a replacement for it |

---

## COR-2 — `papers/draft.md` §4.2 and the abstract · the observation-set result is labelled with the wrong chart

**Found by** the figure work ordered in the operator ruling of 2026-08-29 §6,
while labelling `F2`. The label was read from the code rather than from the
paper, and the two disagreed.
**Applied** the same day, under the same ruling that released `R-3` and assigned
the paper to the loop. `COR-1`'s two-part shape is kept: what was wrong, then
what was written.
**Rule** `CHART-01` and `SPEC-g7-6` — a rank is measured *in a chart, at a
dimension, over an observation set*, and the paper's own §3.2 says numbers
carrying different labels are not comparable term by term.

### Current text — three sites, one error

| # | line | text |
|---|---|---|
| a | abstract | *"Bias-window **width** sets the local rank in chart L at `d=16` — 1 to 4 and 2 to 4 at two devices"* |
| b | §4.2 ¶1 | *"Two measurements make that concrete, both in **chart L** at `d=16` and both at 2% relative noise."* |
| c | §4.2 ¶4 | *"Over 16 bias points at 2% noise in chart L at `d=16`, widening the window from 0.10 V to 0.75 V…"* |

### Why it is wrong

**The measurement is in chart G, not chart L.** `scripts/run_g9.py`'s
`phase_rank_obs` builds the two curves like this:

```python
G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
...
m16 = np.interp(G16.anchors, G4.anchors, th4)
cell, _, _ = cell_spectrum(sg, G16, m16, b, cfg)      # width curve
cell, _, _ = cell_spectrum(sg, G16, m16, b, cfg)      # spacing curve
```

There is no `ChartL` in that function. The device is lifted from chart G at
`d=4` to chart G at `d=16` by interpolation over the anchors, and both curves are
taken in chart G at `d=16`.

**`docs/CLAIM_EVIDENCE_MATRIX.md` row `I5` already says so**, and has since
generation 9: *"A local rank is a curve in the observation set as well as in the
cutoff (**chart G**, **d=16**)"*, with the same 1 → 4 climb over the same
windows. Row `J1`, the localisation falsifier measured over the same sweep, is
labelled **chart G, d=16** too. The paper diverged from the matrix; the matrix
was right.

**Site (b) is wrong in a second and worse way.** It says *both* measurements are
in one chart. The first measurement compares four axes — observation set,
junction, dimension and **interpolant** — and the interpolant axis *is* the
chart: `run_g9.py` computes it as `movements["G_to_L_at_d16"]`, the spectral
movement from the `G_d16` cell to the `L_d16` cell. A measurement whose ×39
interpolant span is produced by changing chart cannot be conducted "in chart L".
Saying it is makes the sentence contradict the number three lines below it.

**The numbers were never wrong.** 1 → 4, 2 → 4, ×1.17, ×21–×39, 2.1%/2.8%
against 56%/58% all reproduce from `outputs/g9/rank_obs.json` and match `I5` and
`I2`. Only the scope label is wrong — the same defect class as `COR-1`, in the
chart coordinate instead of the local/global one.

### How it got in, and this is the part worth keeping

`COR-1`'s applied entry records the chart labels being added **under guard
pressure**:

> *"`test_claim_surface_g7` — the abstract's global paragraph named no chart;
> contribution 3 named no chart and no dimension"*

The guard requires that a rank fraction **carry** a chart label. It cannot check
that the label is the **right** one, because nothing binds a sentence to the
artefact its number came from. Under that pressure the label supplied was the
paper's default — chart L, *"the parameterisation this project uses"*, correct
for §4.1 and carried across to §4.2 where it is not. A guard that demands a
field and cannot validate it converts a *missing* label into a *wrong* one, and a
wrong label is worse: it reads as scoped, so no later reader checks it.

**The artefact could not have caught it either.** `cell_spectrum` returns
`chart` and `chart_label` fields, and `phase_rank_obs` drops both when it builds
the `width_curve` and `spacing_curve` rows. `outputs/g9/rank_obs.json` therefore
does not record the chart its own numbers were taken in, and a reader checking
the paper against the artefact finds nothing to check. That is the root cause and
it is **not fixed here** — fixing it means re-running generation 9, and `R-4`
governs. It is recorded as a defect against the artefact.

### Measured replacement — applied

(a) → *"Bias-window **width** sets the local rank in **chart G** at `d=16` — 1 to
4 and 2 to 4 at two devices, at 2% noise, as the window widens about a fixed
centre"*

(b) → *"Two measurements make that concrete, both at 2% relative noise. Their
scopes differ and the difference matters: the first varies the parameterisation
*itself* as one of the four axes it compares, so it is not conducted inside any
single chart; the second is in **chart G** at `d=16`. Neither is the chart-L
measurement of §4.1, and a rank from one is not comparable term by term with a
rank from another (§3.2)."*

(c) → *"Over 16 bias points at 2% noise in **chart G** at `d=16`, widening the
window from 0.10 V to 0.75 V…"*

**§4.1 is untouched and was always right.** `scripts/run_identifiability.py`
builds `ChartL(N_ANCHOR, …)`, so the *"3–4 of 16 in chart L at `d=16`"* of the
abstract, §4.1 and §6 is correct as written. The correction is confined to the
observation-set result.

**A consequence for `docs/PAPER_AUDIT_g15.md` §4.1.** That table lists *"in chart
L at `d=16`"* as load-bearing qualifier `L1`, on the reasoning that without the
label the number is over an unstated manifold. The reasoning holds and the
example was wrong: `L1` was load-bearing **and false**, which is the strongest
possible form of the audit's own point. The audit is a dated record and is not
edited; this entry supersedes its `L1` row forward.

### Evidence

```bash
PYTHONPATH=src python scripts/run_g9.py --phases rank_obs      # regenerates the artefact
PYTHONPATH=src python scripts/make_figures_g15.py              # F2, labelled from the code
```

| | |
|---|---|
| **Artefact** | `outputs/g9/rank_obs.json` |
| **Corroborating record** | `docs/CLAIM_EVIDENCE_MATRIX.md` rows `I2`, `I5`, `J1` |
| **Source of truth** | `scripts/run_g9.py::phase_rank_obs`, `ChartG(16, x_si)` |
| **Figure** | `outputs/figures_g15/F2.png`, manifest `outputs/figures_g15/manifest.json` |
| **Numbers changed** | none |
| **Labels changed** | three |

### After applying

No guard changes state. `test_claim_surface_g7` passed before this correction and
passes after it, because a chart label was present in all three sentences both
times — which is exactly the finding. **The guard cannot see this class of
defect**, and recording that is more useful than the correction itself.

---

## COR-3 — `papers/draft.md` §1 contribution 5 · the contributions list carries a framing the paper itself withdrew

**Found by** `docs/PAPER_AUDIT_g15.md` §2(c), which reported it as an internal
inconsistency a reviewer will find. Applied here under the ruling of 2026-08-29,
which assigned the paper to the loop.
**Rule** the general one this project runs under: a withdrawn framing is
withdrawn everywhere, not only where it was first written.

### Current text

> 5. A negative result: uncertainty-driven bias acquisition **does not beat
>    random selection** on this task at any measured budget.

### Why it is wrong

`docs/NOVELTY_AUDIT.md` §6.3 records the withdrawal in as many words:

> **Withdrawn:** the framing that the project's active learning is a neutral
> result. It is not neutral. `max_std` acquisition is **worse than random** for
> inverse identifiability (`DES-01`). The README and paper draft say so.

§4.6 of the paper says so — *"it is not neutral but **actively harmful**"*, with
`max_std` at **−0.31** mean identifiable rank against random and a 2 / 9 / 9
win-tie-loss record over the twenty (family, budget) cells. **The contributions
list was not updated with it.** So the paper's summary of itself states the
weaker, withdrawn claim and its body states the stronger, surviving one, three
hundred lines apart.

Note the direction. This is not the usual defect of a summary overclaiming
relative to its body: the list **under**claims, and the withdrawn framing is the
*more flattering* one — "our method was neutral" reads better than "our method
was harmful". The paper was carrying a version of its own negative result that
was too kind to itself, which is the more interesting way round and the reason
this is worth a record rather than a silent edit.

### Measured replacement — applied

> 5. A negative result: uncertainty-driven bias acquisition is **worse than
>    random** selection on this task — `max_std` costs −0.31 mean identifiable
>    rank against random over 20 (family, budget) cells, winning 2 and losing 9.
>    An earlier version of this project reported the weaker claim that it merely
>    failed to beat random; that framing is withdrawn and §4.6 records why.

### Evidence

```bash
PYTHONPATH=src python scripts/run_experiment_design.py
```

| | |
|---|---|
| **Artefact** | `outputs/experiment_design/experiment_design.json` |
| **Body text agreeing** | `papers/draft.md` §4.6, table row `max_std` |
| **Withdrawal recorded at** | `docs/NOVELTY_AUDIT.md` §6.3, finding `DES-01` |
| **Numbers changed** | none — the numbers were already in §4.6 and are now also in the list |

### After applying

No guard changes state, and for the same reason as `COR-2`: no guard reads the
contributions list against §4.6. Two guards would have caught this class and
neither exists — one binding a summary claim to the section that evidences it,
and one that fails when a framing recorded as withdrawn still appears in the
tree. The second is cheap and is worth building; it is named here and not built,
because building it is a generation's work and this is a correction.
