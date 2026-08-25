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
