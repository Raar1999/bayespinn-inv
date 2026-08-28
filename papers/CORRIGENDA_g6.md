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
