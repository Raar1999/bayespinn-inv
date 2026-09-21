# CORRIGENDA — `papers/**`

Append-only. `papers/**` is operator-reserved (`R-3`), so the loop never edits it.
Where a measurement contradicts a line in the paper, the correction is written
here with its evidence and the operator applies it. One file, appended to — not a
new escalation each time.

Each entry gives: the exact line, its current text, the measured replacement, the
command that reproduces the measurement, the manifest backing it, and the finding
ID that forced it.

**Correction, 2026-09-09 — the reservation named in the preamble above is no
longer live, and the preamble is left as written.** `R-3` reserved `papers/**`
until the close ruling of 2026-08-29 §4 assigned the paper to the loop and
lifted it; `docs/OPERATOR_TASKS.md` `OT-2` is `DISCHARGED 2026-08-29` on that
basis, `papers/draft.md` joined the claim surface in
`tests/test_claim_surface_g7.py` at the same time, and `COR-1` through `COR-6`
were applied to the draft directly rather than handed to an operator. Only the
`outputs/**/manifest.json` half of `R-3` survives. The preamble's sentence was
true on this file's date and is not edited, for the same reason `ADR-0001` was
not edited under `COR-4`: it is a dated statement, and rewriting it would remove
the evidence that a lifted reservation was carried forward for eleven days.
Entries from `COR-7` on are written **and applied** in the same pass, and each
says so.

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

---

## COR-4 — `papers/draft.md` §1 contribution 1 and `README.md` · the equilibration gain is a withdrawn figure still asserted as live

**Found by** `docs/UNDERCLAIM_SWEEP_g15.md` `U-1` (HIGH), 2026-09-02, which named
this correction `COR-4` and did not write it. Applied 2026-09-07 under the
operator handoff of that date, §5.2.
**Rule** the same one `COR-3` runs on: a withdrawn figure is withdrawn
everywhere, not only where the withdrawal was recorded.

### Current text — two live sites

**(a)** `papers/draft.md` §1, contribution 1:

> equilibrated continuity solves (**1730×** improvement in the equilibrium
> mass-action law)

**(b)** `README.md`, the solver section:

> Equilibration improves the equilibrium mass-action law by **1730×**
> (ADR-0001).

### Why it is wrong

`docs/CLAIM_EVIDENCE_MATRIX.md` row `X17` withdrew the figure and says why in as
many words:

> The `1.32e-2` starting point is sound (measured `6.77e-3`, 1.95× — within
> tolerance). The `7.62e-6` endpoint is not: the adopted solver reaches
> `9.7e-10`, so the real gain is ~**7.0e6×**, not 1730×. The published figure
> understated the improvement by ~4000×.

Row `S1` carries the replacement. `1730×` was measured on the **pre-audit**
solver; the solver the paper describes is the adopted one. Of the withdrawn
literals listed in the matrix's §3, the sweep's search found this the **only one
still asserted as live** anywhere on the fourteen-document claim surface — every
other hit was a mention of a withdrawal, which is the correct way for a withdrawn
literal to appear.

Note the direction, which is `COR-3`'s again. The summary carried a superseded
version's number after the ledger moved underneath it, and the error runs
*against* the paper: it claims a solver improvement about four thousand times
smaller than the one it has. The mechanism is indifferent to direction — nothing
re-derives a summary when the ledger changes — and it happened to surface as an
underclaim twice running.

### Measured replacement — applied

**Two residuals, not the ratio.** A ratio of about seven million invites the
question of how hard the baseline was tried; two values, each with the quantity
it measures and the configuration that produced it, are a measurement and answer
that in advance.

**(a)** `papers/draft.md` §1, contribution 1:

> equilibrated continuity solves — on the 1 µm N_A = N_D = 1e22 m⁻³ junction at
> zero bias the equilibrium mass-action violation max|np/n_i² − 1| is 6.8e-3
> with a plain `spsolve` and 9.7e-10 equilibrated —

**(b)** `README.md`, the solver section:

> On the 1 µm N_A = N_D = 1e22 m⁻³ junction at zero bias the equilibrium
> mass-action violation max|np/n_i² − 1| is **6.8e-3** with a plain `spsolve`
> and **9.7e-10** equilibrated
> (`test_sg_numerics.py::test_equilibration_beats_plain_spsolve`). ADR-0001
> states **1730×** for the same comparison measured on the pre-audit solver;
> that figure is withdrawn as `X17` in `docs/CLAIM_EVIDENCE_MATRIX.md`.

### Evidence

Run the body of the guarding test and read both sides, rather than only its
assertion:

```
PYTHONPATH=src python -c "
import sys, numpy as np
sys.path.insert(0, 'tests')
from test_sg_numerics import _setup, _pn
from bayespinn_inv.solvers.scharfetter_gummel import ScharfetterGummel1D, SGConfig
from bayespinn_inv.physics.constants import SILICON
s, grid, _ = _setup()
doping = _pn(s, grid)
for eq in (False, True):
    sg = ScharfetterGummel1D(grid, s, SILICON, SGConfig(equilibrate=eq, max_outer=60))
    st = sg.solve(doping, bias=0.0)
    r = (st.n / s.n_star) * (st.p / s.n_star)
    print(eq, '%.4e' % float(np.max(np.abs(r - 1.0))))
"
```

| | |
|---|---|
| **Measured 2026-09-07 on this tree** | plain `spsolve` `6.7705e-03`; equilibrated `9.7290e-10` |
| **Ledger rows** | `X17` (withdrawal), `S1` (replacement), `docs/CLAIM_EVIDENCE_MATRIX.md` |
| **Guarding test** | `tests/test_sg_numerics.py::TestGummelConvergenceIsHonest::test_equilibration_beats_plain_spsolve`, which asserts the ratio exceeds 100× and reports neither side |
| **Reproduces** | `docs/UNDERCLAIM_SWEEP_g15.md` §3's re-measurement, to five digits |

### `ADR-0001` is not corrected

`docs/adr/ADR-0001-…md` lines 61 and 69 state `1730×` and keep it. It is a dated
decision record, the figure was true on 2026-08-19, and the decision it justifies
— equilibrate the continuity solves — is unaffected by the endpoint moving. It
receives a **dated pointer**, appended 2026-09-07, giving the withdrawal, the two
current residuals and the configuration, and nothing else. Correcting the record
itself would destroy the thing an ADR is for.

### After applying

No guard changes state. Nothing in the tree binds contribution 1 to matrix row
`S1`, which is why a withdrawn literal survived on the claim surface for the
generations between `X17` and this entry. `docs/UNDERCLAIM_SWEEP_g15.md` §7 names
the guard that would have caught it — one that fails when a literal recorded as
withdrawn still appears live — and gives the reason it is not built here: its list
of literals would be hand-maintained, which is a presence check that goes stale
(`AGE-01`, `FILL-01`). The hand search that found this took under a minute and is
recorded in that document's §1.

---

## COR-5 — `papers/draft.md` §4.9 · the compute claim rests on a wall-clock the ledger excludes, and is false as stated

**Found by** `docs/UNDERCLAIM_SWEEP_g15.md` §5 `O-2`, an opposite-direction
finding the underclaiming sweep reported rather than suppressed. Applied
2026-09-07 under the operator handoff of that date, §5.1.
**Rule** the general form of `AH-12`: a comparative word carries the comparison
it was measured on.

### Current text

> A budget-matched ensemble, trained *faster* than either single-network
> method, still beats both, so this is not a compute advantage.

### Why it is wrong

`outputs/uq_benchmark/uq_benchmark.json`, `cost.train_seconds`:

| method | train_seconds |
|---|---:|
| deep ensemble, budget-matched | 6.655 |
| MC-dropout (tuned) | 9.216 |
| SWAG (tuned) | **6.259** |

The ensemble is faster than MC-dropout and **slower than SWAG**, by 0.40 s of
6.3 — about 6%. *Either* is false. Matrix row `D6` prints all three values
(`6.7 s train (vs 9.2 s / 6.3 s)`) and the sentence read only the first.

There is a second defect underneath the first, and it is the one that matters.
`docs/CLAIM_EVIDENCE_MATRIX.md` §6 excludes timing fields from this project's
reproduction comparisons in as many words — *"Wall-clock is not a scientific
claim and the machine was under load throughout — `train_seconds` roughly doubled
on several runs"*. So the sentence rested on the one class of number the ledger
explicitly does not stand behind, and a re-run on a differently loaded machine
could reverse it. The claim the experiment actually supports is about the
**training budget**, which is exact and deterministic: `config.epochs` is 2500 for
every method, and the budget-matched ensemble's own note records *"total epochs
matched to the single-network methods (2500) rather than 5x it"*.

### Measured replacement — applied

> A budget-matched ensemble — the same 2500 total training epochs each
> single-network method receives, split across five members rather than
> multiplied by five — still beats both, so this is not a compute advantage.
> On the clock that ensemble takes 6.7 s against MC-dropout's 9.2 s and SWAG's
> 6.3 s, faster than one and marginally slower than the other; the claim rests on
> the matched epoch budget rather than on the wall-clock, which this project
> excludes from its reproduction comparisons.

The conclusion — *this is not a compute advantage* — is unchanged, and is now
carried by the number that supports it. The wall-clock is reported rather than
dropped, with the caveat that makes it readable.

### Evidence

```
PYTHONPATH=src python scripts/run_uq_benchmark.py
```

| | |
|---|---|
| **Artefact** | `outputs/uq_benchmark/uq_benchmark.json`, `methods.*.cost.train_seconds` and `config.epochs` |
| **Matrix row** | `D6` |
| **Timing exclusion** | `docs/CLAIM_EVIDENCE_MATRIX.md` §6 |
| **Numbers changed** | none — all four were already in the artefact; three were not in the sentence |

### After applying

No guard changes state. No guard in this tree reads a comparative adjective
against the artefact that would settle it, and `O-2` was found by a hand sweep
rather than by a check. Recorded here so the absence is a known gap and not a
silent one.

### The two siblings not corrected here

The same sweep reported `O-3` and `O-4`, both on the claim surface and neither in
the operator handoff's §5.1 scope. They stay open and are named so they are not
lost: `O-3`, §4.5's *"variance inflation T = 2.08"* against `2.0927` in
`outputs/results/results.json` (README and matrix row `C10` both say 2.09); `O-4`,
§4.1's *"Conclusion stable across finite-difference steps (0.01–0.05 decades) and
SNR thresholds (1e4–1e8): identifiable rank 4"* against the
`(min_snr = 1e4, rel_step = 0.01)` row of `analysis_convergence`, which gives 3.
`O-4` is the same class as `COR-5` — a stability word contradicted by one row of
the table it summarises — and is the larger of the two.

---

## COR-6 — the abstract's `3–4 of 16` against §4.1's own table · the licence was in the ledger and not in the paper

**Found by** `docs/UNDERCLAIM_SWEEP_g15.md` §4, which reported it as a boundary
case its method surfaced and then resolved against an artefact the paper does not
cite. Applied 2026-09-07 under the operator handoff of that date, §5.3, which gave
two options — state the licensing where the claim is made, or widen the range —
and this entry takes the first.
**Rule** `AGE-01`'s sibling in spirit: a narrowing that a ledger row licenses is
licensed only where a reader can see the row.

### Current text — a headline and a table at different analysis settings

**(a)** Abstract:

> …determines only **3–4 of 16** profile degrees of freedom — a *local* rank, at
> four device families — and improving the instrument by four orders of
> magnitude roughly doubles it.

**(b)** §4.1's table, three paragraphs below it, gives **4**, **5**, **3**, **4**
for the four families, and carries no statement of the analysis settings it was
taken at.

### Why it is wrong

Both numbers are right and they are measured at **different analysis settings**,
which the paper never says.

| | source | `rel_step` | `min_snr` | the four families |
|---|---|---:|---:|---|
| §4.1's table | `outputs/identifiability/identifiability.json`, matrix `C12` | 0.05 | 1e8 | 4, 5, 3, 4 |
| the abstract's range | `outputs/identifiability_robustness/identifiability_robustness.json`, matrix `D14` | 0.01 | 1e4 | 3, 4, 3, 3 |

Matrix row `D14a` licenses the narrowing in as many words: *rank 5–6 appears only
at larger finite-difference steps (0.02–0.05), which lower the **analysis** noise
floor rather than revealing more physics*. The matrix also records that the
headline `3–5` was **corrected to `3–4`** at the reference conditions, so widening
the range back to 3–5 would restore a figure the ledger has already withdrawn.
That is why the handoff's second option is not the one taken here.

**The defect is the placement, not either number.** A reviewer who reads the
table under the abstract sees 5 and 3–4 disagree, goes looking for the licence,
and does not find it: `D14`, `D14a` and `IDENT-02` are in the ledger and none of
them is in the paper.

### Measured replacement — applied

Two sites, one clause each way.

**(a)** Abstract, the licence stated where the claim is made:

> …determines only **3–4 of 16** profile degrees of freedom — a *local* rank, at
> four device families, at the reference analysis conditions of §4.1 — and
> improving the instrument by four orders of magnitude roughly doubles it.

**(b)** §4.1, a new paragraph immediately under the table and before
*Validation*:

> *Analysis settings, and why the abstract says 3–4.* The four rows above are
> taken at a finite-difference step of 0.05 decades and an SNR threshold of 1e8.
> The **3–4 of 16** *local* range quoted in the abstract and in §6 is the same
> four families in chart L at `d=16`, over the same 19-point forward-bias
> observation window (0–0.9 V) at 2% relative noise, measured at the reference
> analysis conditions of the robustness sweep — step 0.01 decades, SNR threshold
> 1e4 — where they give 3, 4, 3 and 3. A coarser step lowers the *analysis*
> noise floor rather than revealing more physics, and that is what lifts the
> asymmetric-step device to 5 in the table above; the reference conditions carry
> the claim and the table's rows are the raw counts.

### Evidence

```
PYTHONPATH=src python scripts/run_identifiability.py
PYTHONPATH=src python scripts/run_identifiability_robustness.py
```

| | |
|---|---|
| **Table settings, read 2026-09-07** | all four devices carry `min_snr_used = 1e8`, `rel_step = 0.05` in `outputs/identifiability/identifiability.json` |
| **Reference conditions** | `config.base` of `outputs/identifiability_robustness/identifiability_robustness.json`: `P = 16`, `n_bias = 19`, `v_max = 0.9`, `grid_n = 301`, `rel_step = 0.01`, `min_snr = 1e4`, `level = 1e22`, noise 0.02 |
| **Ranks at those conditions, read 2026-09-07** | step-symmetric 3, step-asymmetric 4, graded 3, LDD 3 |
| **Matrix rows** | `C12` (the table), `D14` (the headline), `D14a` (the licence) |
| **Numbers changed** | none — both sets were already measured; neither was in the paper beside the other |

### The guards fired on the first attempt, and were not touched

`docs/PAPER_RECOMMENDATIONS_g15.md`'s preamble predicts this and it happened
exactly as predicted. The first draft of the §4.1 paragraph tripped three guards
at once — `test_claim_surface_g0.py` (no local/global label),
`test_claim_surface_g7.py` (missing the `regime` field), and
`test_claim_surface_g9.py` (a rank fraction with no observation window). The
paragraph was rewritten to carry the regime, the chart, the dimension and the
window; no guard was edited, no exemption was added, and all three pass on the
text above. That is the same sequence the two structural edits of the close-out
order went through, recorded in that document's preamble.

### Not corrected here — `O-4`, in the paragraph immediately below

`docs/UNDERCLAIM_SWEEP_g15.md` §5 `O-4` reports that §4.1's *Validation*
sentence — *"Conclusion stable across finite-difference steps (0.01–0.05
decades) and SNR thresholds (1e4–1e8): identifiable rank 4, σ₁/σ₂ =
6.11–6.13"* — is contradicted by its own artefact: the
`(min_snr = 1e4, rel_step = 0.01)` row of `analysis_convergence` gives
identifiable rank **3**, and the ratio runs 6.107–6.123, so 6.11–6.12. Read
2026-09-07 on this tree, both hold.

It is not corrected because the operator handoff of 2026-09-07 scoped §5.1 to two
named overclaims and this is a third. It now sits one paragraph below a
correction that publishes a 3 at exactly the settings that sentence calls stable
at 4, which makes it the most visible remaining inconsistency in §4.1 rather than
a buried one. Whoever takes it needs no new measurement: the mechanism is the
same one this entry states — the smallest step at the loosest threshold has the
highest analysis floor — and `D14a` already licenses the wording.

---

## COR-7 — `papers/draft.md` §4.1 *Validation* · the convergence study is called stable at a rank one of its own rows does not give

**Forced by** `docs/UNDERCLAIM_SWEEP_g15.md` §5 `O-4` · **applied in this pass**

### Current text

> *Validation.* Predicted response $\|Jv\|$ vs an independent re-solve: ratios
> **0.995–1.04** for all resolved directions across all four families.
> Conclusion stable across finite-difference steps (0.01–0.05 decades) and SNR
> thresholds (1e4–1e8): identifiable rank 4, $\sigma_1/\sigma_2 = 6.11$–6.13.

### Why it is wrong

Two defects in one sentence, both against `analysis_convergence` in
`outputs/identifiability/identifiability.json`, which is the artefact the
sentence summarises.

**The rank.** The block holds five rows. `identifiable_rank` is 4 in four of
them and **3** in the `(min_snr = 1e4, rel_step = 0.01)` row. *Stable … rank 4*
is contradicted by a fifth of its own evidence.

**Which row dissents is the part that matters.** `(1e4, 0.01)` is the reference
condition of the robustness sweep, and therefore the condition `COR-6` had just
finished naming in the paragraph immediately above as the one carrying the
abstract's `3–4`. After `COR-6` the paper published a 3 at those settings one
paragraph above a sentence calling them stable at 4. `COR-6` did not create the
defect — the sentence was already false against its artefact — but it moved the
contradiction inside a single page, which is why this entry is applied rather
than carried.

**The ratio.** `sigma_ratio_1_2` runs 6.1070–6.1230 across the five rows.
Rounded to the two decimals the sentence uses, that is **6.11–6.12**: 6.123
rounds to 6.12, not 6.13.

### Measured replacement — applied

> *Validation.* Predicted response $\|Jv\|$ vs an independent re-solve: ratios
> **0.995–1.04** for all resolved directions across all four families. The
> analysis-convergence study re-estimates the Jacobian on the reference device
> (symmetric step) at five combinations of finite-difference step (0.01–0.05
> decades) and oracle SNR threshold (1e4–1e8). The leading spectrum is stable
> across all five: $\sigma_1/\sigma_2 = 6.11$–6.12. The identifiable rank is
> **4 at four of them and 3 at the fifth**, which is the reference condition of
> the paragraph above — step 0.01 decades, SNR threshold 1e4, the loosest
> threshold of the five. It admits 15 bias rows where the other four keep
> 10–12, and the extra rows are the low-SNR ones: against the next setting at
> the same step (SNR 1e6) the estimated Jacobian entry noise is 440× larger and
> the spectral floor the rank is counted against 490× higher. The rank moves
> with the analysis floor rather than with the physics — the same mechanism
> that lifts the asymmetric-step device to 5 at the coarsest step in the table
> above, running the other way.

Three things the replacement adds that the original asserted without support.
The study is on **one device**, not four: `scripts/run_identifiability.py`
carries `ref = devices["step_symmetric"]` under the comment *analysis-convergence
study on the reference device*, and the *all four families* of the first
sentence belongs to the re-solve ratios alone. The settings are a **diagonal of
five**, not a grid of step × threshold. And the mechanism is named, so the row
that gives 3 reads as the analysis floor moving rather than as a result in
tension with the table.

### Evidence

```
PYTHONPATH=src python scripts/run_identifiability.py
```

`analysis_convergence` in `outputs/identifiability/identifiability.json`, read
2026-09-09 on this tree:

| `min_snr` | `rel_step` | `n_rows` | `entry_noise` | `spectral_floor` | `identifiable_rank` | `sigma_ratio_1_2` |
|---:|---:|---:|---:|---:|---:|---:|
| 1e4 | 0.01 | 15 | 2.5841e-3 | 4.0033e-2 | **3** | 6.1230 |
| 1e6 | 0.01 | 12 | 5.8650e-6 | 8.1268e-5 | 4 | 6.1087 |
| 1e6 | 0.03 | 12 | 1.9550e-6 | 2.7089e-5 | 4 | 6.1111 |
| 1e7 | 0.03 | 11 | 4.4261e-7 | 5.8718e-6 | 4 | 6.1070 |
| 1e8 | 0.05 | 10 | 3.3217e-8 | 4.2017e-7 | 4 | 6.1137 |

| | |
|---|---|
| **440× and 490×** | `2.5841e-3 / 5.8650e-6 = 440.6` and `4.0033e-2 / 8.1268e-5 = 492.6`, both against the row at the same `rel_step`, so the comparison isolates the threshold |
| **Reference device** | `scripts/run_identifiability.py`, `ref = devices["step_symmetric"]` |
| **Reference conditions** | `config.base` of `outputs/identifiability_robustness/identifiability_robustness.json`: `rel_step = 0.01`, `min_snr = 1e4` — the same pair as the dissenting row |
| **Matrix row** | `D14a`, which licenses the narrowing and states the mechanism this entry restates |
| **Numbers changed** | none — every figure above was already in the artefact |

### After applying

§4.1 states a rank that varies with the analysis setting, states which setting
gives which, and states why. The 3 in the *Validation* paragraph and the 3, 4, 3
and 3 in the paragraph above it are now the same measurement at the same
conditions rather than two numbers a reader must reconcile unaided. `O-4`
closes.

---

## COR-8 — `papers/draft.md` §4.5 · the variance-inflation temperature is transcribed to the wrong second decimal

**Forced by** `docs/UNDERCLAIM_SWEEP_g15.md` §5 `O-3` · **applied in this pass**

### Current text

> Calibration, **pre and post on the identical test set** (n=140), variance
> inflation $T=2.08$ fitted on a disjoint split:

### Why it is wrong

`H3_calibration.temperature` in `outputs/results/results.json` is
`2.0926970199407045`. To two decimals that is **2.09**. No artefact carries
2.08, and the two other places that state the calibration temperature as a
result — `README.md`'s results table and `docs/CLAIM_EVIDENCE_MATRIX.md` row
`C10` — both say 2.09. This is a transcription into the paper, not a
disagreement between artefacts.

It is the smallest defect in this pass, and being on the claim surface is the
whole of its justification for being here: a reader who spot-checks one number
against the ledger may well check this one, and finding it wrong costs the
sentences around it their credibility for no gain.

### Four sites quote the old value and are deliberately not edited

Correcting §4.5 makes `2.08` stale wherever another document describes what §4.5
said. Each of those is a **dated record of a past comparison**, not a statement
of the calibration result, and `AGE-01` is the reason to leave them:

* `docs/PAPER_FINAL_g15.md` §2 — inside a block quotation. A quotation is not
  editable without ceasing to be one.
* `docs/PAPER_WORK_g15.md` §4 — the table that established the four unreferenced
  PNGs came from a different run, `T = 5.07` against the paper's value at the
  time. The comparison it records was made against 2.08 and was correct.
* `docs/OPERATOR_RULINGS_INDEX.md` §3 row 21 and §4 row 18 — both restate that
  same comparison as what caught the eighteenth operator defect.

The mismatch those three record — a factor of about 2.4 between the PNG run and
the results run — is unchanged by this correction, so nothing they conclude
moves. Editing them would rewrite the evidence for a finding to make a later
number agree with it, which is the move `docs/CLAIM_EVIDENCE_MATRIX.md`'s
withdrawal discipline exists to prevent.

### Measured replacement — applied

> Calibration, **pre and post on the identical test set** (n=140), variance
> inflation $T=2.09$ fitted on a disjoint split:

### Evidence

```
PYTHONPATH=src python scripts/run_results.py
```

| | |
|---|---|
| **Artefact, read 2026-09-09** | `outputs/results/results.json`, `H3_calibration.temperature = 2.0926970199407045` |
| **Agreeing sites** | `README.md` results table, `T=2.09`; `docs/CLAIM_EVIDENCE_MATRIX.md` `C10` |
| **Precision** | two decimals, matching the sentence's existing convention and both agreeing sites; the further digits are not reported because nothing else reports them |
| **Numbers changed** | one, toward the artefact |

### After applying

The coverage table beneath the sentence is unchanged — it was already right —
and the paper agrees with the README and the matrix. `O-3` closes.

---

## COR-9 — `papers/draft.md` §3.2 · a methods claim hedged below the count the record holds

**Forced by** `docs/UNDERCLAIM_SWEEP_g15.md` §3 `U-2` · **applied in this pass**

### Current text

> Where an earlier round of this work recorded that something could not be done,
> later rounds re-tested the obstruction rather than inheriting it — and **at
> least one** turned out to be false on the first attempt, having never been
> tried.

### Why it is wrong

*At least one* is a hedge standing in front of a count the tree holds, which is
the shape `U-1` and `COR-3` had in the other direction. The record names three,
each dated, each from a different round:

1. **`DOC-03a`** — the README badge that generation 10 recorded as unchangeable
   and that changed in one line, *because nothing had ever tried it*
   (`docs/RULES_ENACTED.md` `OBS-01`, quoting `docs/CLOSE_RULING.md` §5.1).
2. **`HIST-01`** — carried three generations as `UNREPAIRABLE FROM INSIDE THE
   TREE` while `.git/filter-repo/commit-map`, the file that performed the
   repair, sat in the repository. Nobody ran `ls .git`
   (`docs/HIST01_REPAIR_g11.md`).
3. **The Windows leg** — carried eight generations as *not obtainable on this
   host by any means*, on a host that is Windows
   (`docs/WINDOWS_LEG_SCORED_g15.md` §1).

The sentence is true as written and weaker than its evidence, and the hedge
costs the paragraph its point: the paragraph argues that inherited obstructions
go unchecked, and three instances argue that where one does not.

### Measured replacement — applied

> …later rounds re-tested the obstruction rather than inheriting it — and
> **three, each from a different round**, turned out to be false on the first
> attempt, having never been tried: a documentation badge recorded as
> unchangeable and then changed in one line; a history repair recorded as
> impossible from inside the repository while the file that performed it sat in
> `.git`; and a platform test leg recorded as unobtainable on this host, on a
> host that is that platform.

The three are described rather than cited by ID, because `DOC-03a`, `HIST-01`
and the Windows leg are this repository's finding names and mean nothing to a
reader of the paper. Each description is specific enough to be matched to the
ledger by anyone who has it.

### Evidence

| | |
|---|---|
| **Instance 1** | `docs/RULES_ENACTED.md` `OBS-01`: *"the README badge that generation 10 recorded as unchangeable, which turned out to be changeable in one line, because nothing had ever tried it"* |
| **Instance 2** | `docs/RULES_ENACTED.md` `OBS-01` and `docs/HIST01_REPAIR_g11.md`; the finding was carried three generations |
| **Instance 3** | `docs/WINDOWS_LEG_SCORED_g15.md` §1, quoting the close-out ruling: *"I wrote that the Windows leg was 'not obtainable on this host by any means' and carried it for eight generations. **The host is Windows.**"* |
| **Denominator** | none is stated, because the record holds a count of instances found and no population of obstructions re-tested. `DOC-08` asks that a count carry its scope; the scope given is *each from a different round*, which is what the record supports and no more |
| **Numbers changed** | none — the count was measured before the sweep and had not been carried into the paper |

### After applying

The methods paragraph states its count. `U-2` closes.

---

## COR-10 — `papers/draft.md` §4.10 · the audit section stops where the audit did not

**Forced by** `docs/UNDERCLAIM_SWEEP_g15.md` §3 `U-4` · **applied in this pass**

### Current text

> Fourteen defects across two audit cycles. Four produced silently wrong physics
> while the test suite of the day passed:

followed by four bullets, and then §5.

### Why it is wrong

Neither sentence is false. Both are scoped — *across two audit cycles* — and
`docs/AUDIT_MASTER.md` supports both: forty-seven findings, of which fourteen
are numbered `BUG-xx`, seven of those CRITICAL. This is a scope finding. What
the evidence supports and the paper did not say is that the audit ran on for
fifteen further rounds, and that the later findings are the ones bearing on the
reproducibility claims the paper makes elsewhere.

§4.10's own headline is how easily plausible numbers survive a passing test
suite. `PROV-06`, `REPRO-01` and `DIFF-01` are the sharpest instances of that in
the tree and none of them was in the section.

### Measured replacement — applied

A paragraph after the four bullets and before §5:

> **The audit did not stop at those two cycles, and what it found afterwards is
> about reproducibility rather than physics.** The ledger holds forty-seven
> findings; the fourteen above are the ones numbered as numerical or solver
> defects, and fifteen further rounds of review followed the second cycle. Those
> rounds found that the repository had bifurcated and `HEAD` was the pre-audit
> project, so the tree carrying the results was not the tree under version
> control; that forty-one published numbers can never be explained, because the
> working tree that produced them was never committed; that the repair for a
> finding carried three rounds as *unrepairable from inside the repository* had
> been sitting in `.git` throughout; and that a mechanical line-ending edit
> changed 9,832 lines to fix 68, with the suite green before and after, because
> every file was individually correct. The last two are the same lesson as the
> four defects above, one level up: a passing suite is evidence about the
> properties it was written to check and about nothing else, and aggregate blast
> radius was not one of them.

**The abstract's half of `U-4` is not applied.** *"an adversarial audit that
found fourteen defects in its first two cycles, seven critical"* is scoped, is
true, and sits in the abstract, which is reserved to the operator pending a
venue. It is left to that pass rather than corrected here, and it is consistent
with the widened §4.10 as it stands.

### Evidence

| | |
|---|---|
| **Forty-seven, fourteen, seven** | `docs/AUDIT_MASTER.md` header: *"47 findings total, of which 14 are numbered `BUG-xx`… Seven are CRITICAL"* |
| **Fifteen further rounds** | `LOOP_STATE_v15.json`, `generation = 14`; generations 0–14 are `docs/AUDIT_MASTER.md` §§9–13, all of which follow §8, the second cycle |
| **Bifurcation** | `PROV-06`, `docs/AUDIT_MASTER.md` §9; `docs/PROVENANCE_BIFURCATION_g0.md` |
| **Forty-one numbers** | `REPRO-01`, `docs/AUDIT_MASTER.md` §10 and `docs/REPRO01_LEAF_AUDIT_g6.md` |
| **The repair in `.git`** | `HIST-01`, `docs/HIST01_REPAIR_g11.md`; carried three generations |
| **9,832 lines to fix 68** | `docs/G13_RESULT.md`; `docs/SWEEP_REGISTER.json`, `actual_changed_lines = 9832`; `DIFF-01` enacted at generation 14 |
| **Numbers changed** | none — every figure is transcribed from the ledger |

### After applying

§4.10 covers the audit it names. `U-4` closes for the body; the abstract's
sentence is unchanged and left to the operator's abstract pass.
