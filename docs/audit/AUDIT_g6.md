# AUDIT_g6 — Phase A ledger

**Generation** 6 · **Date** 2026-08-25 · **Champion at entry** `3302817` → `bf5aa21`
**Branch** `loop/champion` · **Ruling** operator amendment for generation 6

Phase A executed §3.1 (blocking), §3.5, §3.4 and §3.2a in that order. §3.1 was
completed before anything else proceeded.

---

## 0. Ground truth

| gate | result |
|---|---|
| ruff | exit 0 |
| suite | **438 passed, 0 failed** (403 at entry; +35 this generation) |
| selftest | PASS |
| mypy | **25**, the package only and never the tracked tree — unchanged from the generation-0 baseline |

---

## 1. §3.1 — REPRO-01 leaf audit · **generation 1 was wrong**

Full record: `docs/REPRO01_LEAF_AUDIT_g6.md`.

Generation 1 described the 41 differing leaves as "diagnostics only". That was an
assertion, not a measurement. Checked leaf by leaf, **7 of the 41 back published
numbers**:

| leaf class | n | claim |
|---|---:|---|
| `analysis_convergence[*]/sigma_ratio_1_2` | 2 | `papers/draft.md:169`, σ₁/σ₂ = 6.11–6.13 |
| `ldd/equivalence_twin/iv_max_rel_change` | 1 | **C14** |
| `ldd/linear_response_check[*]/ratio` | 4 | **C15** |

All three re-measured against the regenerated artefact. **None withdrawn:**

| claim | published | 2026-08-19 | regenerated |
|---|---|---|---|
| C14 | 0.02–1.3 % | 0.0240–1.2750 % | **0.0240–1.2750 %** |
| C15 | 0.995–1.04 | 0.994986–1.039707 | **0.994986–1.039707** |
| σ₁/σ₂ | 6.11–6.13 | 6.1070–6.1230 | **6.1070–6.1229** |

The correct statement is not "these are diagnostics" but **"the leaves that back
published numbers do not move those numbers at their published precision"**.
Weaker, and true.

The 2026-08-19 artefact is **retired**. Every identifiability claim now points at
`outputs/identifiability_g1/`, which carries a `tree_digest` and reproduced
bit-identically on an independent re-run.

## 2. §3.5 — PH-22 retro-sweep · **negative result: no second GRAD-02**

PH-22 says a float64 envelope does not transfer to float32. The sweep looked for
quantities used on **both** sides of the solver/network boundary — a single-dtype
quantity cannot fail the GRAD-02 way. Two cross it, and both degrade gracefully:

| quantity | float64 | float32 |
|---|---:|---:|
| SI ↔ scaled doping round trip | 1.678e-16 | 8.714e-08 |
| symlog round trip | 2.030e-15 | 8.823e-07 |

Both sit at their dtype's epsilon. `bernoulli` has exactly one definition, NumPy,
in a module that does not import torch — so PH-10's "full double range" is
correctly scoped.

**Carried into S-1:** the float32 path cannot resolve doping differences below
~1e-7 relative. The oracle can. That is an independent reason — separate from
GRAD-01 — why the surrogate cannot arbitrate a degeneracy search, and it is now
written into `ADR-0007`.

Envelopes annotated per dtype in `scaling.py`, `identifiability.py` (both
Jacobians) and `scharfetter_gummel.py`; pinned by
`tests/test_dtype_envelopes_g6.py`.

## 3. §3.4 — CRLF made durable · **the guard caught its own author**

`.gitattributes` pins `* -text`. Not `text=auto`: the index holds **119 CRLF, 74
LF, 2 mixed** files, and normalising would rewrite 119 of them and silently
invalidate `PRESERVE_MANIFEST_g0.sha256`. Mixed endings are untidy but they are
what was measured.

Within the hour, the new guard failed on **three of this generation's own edits**.
`identifiability.py`, `scharfetter_gummel.py` and `test_robustness.py` had all
been silently normalised CRLF→LF by a Python helper that reads with universal
newlines and writes with `newline=""`. Restored with content preserved.

A repository-wide byte convention that only a hand check enforces does not survive
contact with tooling. `core.autocrlf` and `core.eol` are now recorded in every
manifest.

## 4. §3.2a — CI executed locally · `docs/WINDOWS_RISK_g6.md`

`ci.yml` is valid YAML. Its three `run` steps execute on Python 3.11.9 / Windows:
Lint 0, Test 0, notebook generator 0.

**`SPEC-g6-3a` passes for the 3.11 leg only.** The 3.9 and 3.12 legs are
**unevaluated, not passing** — neither interpreter exists on this machine. That
distinction is exactly why `CI-01` was a false closure once already.

### New findings

**BUG-14 recurrence (fixed).** `tests/test_robustness.py:278` read a UTF-8
manifest with the platform encoding. Under cp1252 that mis-decodes silently. Fixed,
and the file-by-file part of BUG-14 removed: an AST guard now fails on any text
`open`/`read_text`/`write_text` without `encoding=` anywhere in `src/`, `scripts/`
or `tests/`.

**`NB-02` (MEDIUM, OPEN).** `scripts/build_notebooks.py` regenerates the twelve
notebooks **without executed outputs**, and `test_notebooks.py` asserts they *have*
outputs — the evidence for claim `U1`. CI is green **only because `Test` (step 5)
runs before the generator (step 6)**, and nothing states that dependency. Running
the step verbatim during this sweep destroyed all twelve; they were restored from
`HEAD` via `git archive` and digest-verified 12/12 (`R-4` forbids `git checkout`).
Left open: separate concern (`SW-08`), and the fix has options worth competing.

### Checked and clean

Case-only filename collisions: **0**. Hardcoded path separators in `src/` string
literals: **0**. POSIX-only Makefile commands: present but crash-class, and the
ruling ranks by silent wrongness.

---

## 5. A recurring defect in the loop's own output

Four times now, a guard whose subject is source code has been implemented by
matching characters, and has tripped on prose describing the very thing it guards:

| generation | pattern | matched |
|---|---|---|
| 1 | `weights_only=False` | the comment documenting SEC-02 |
| 2 | `"scripts"` | the comment documenting PKG-04 |
| 6 | `torch` | the comment documenting GRAD-03 |
| 6 | `def bernoulli` (via `git grep`) | **the test's own search pattern**, once committed |

All four were fixed the same way: read the syntax tree. Comments and string
literals are not code in an AST. Recorded here as a defect class of this loop
rather than four separate slips.

The fourth also produced a **process** error: `1a090f0` was committed with a
message stating "420 passed" when the suite was 437 passed / 1 failed. `R-4`
forbids amending, so the error stands in history and is corrected in `d3b7693`.

---

## 6. Phase A exit

- No `CRITICAL` opened. `NB-02` is MEDIUM.
- `E-2` not triggered: no published claim contradicted. The three that could have
  been (C14, C15, σ₁/σ₂) were re-measured and hold.
- Finding statuses assigned per §1 of the ruling:
  `PROV-03` → `ACCEPTED-PERMANENT` (cost statement in `GEN_g6.md`, with REPRO-01
  as its first quantified instance); `SPEC-g0-3b`/`CI-01` → `OPERATOR-BLOCKED`
  (`docs/OPERATOR_TASKS.md`); `REPRO-01` → `UNRESOLVABLE-BY-CONSTRUCTION` (what
  was lost, and when, in the leaf audit §4).
