# AUDIT_g1 — Phase A ledger

**Generation** 1 · **Date** 2026-08-25 · **Champion at entry** `06eb32f`
**Champion at exit** `9670bec` · **Branch** `loop/champion`
**Prior state** `LOOP_STATE_v1.json` · **Prior report** `docs/gen/GEN_g0.md`

Generation 0 left one gap larger than all the others: `SPEC-g0-1` claims that a
single commit reproduces the entire claim surface, but only **one of seven**
experiments had actually been re-run. This generation closed that gap by
measurement.

---

## 0. Ground truth

| gate | result |
|---|---|
| ruff | exit 0 |
| suite | **352 passed, 0 failed** (was 309 at the g0 champion) |
| selftest | PASS |
| mypy | **25** findings, the package only and never the tracked tree — unchanged from the generation-0 baseline |

Provenance of this audit's own tree, from the fixed `RunManifest`:

```json
"git": {"commit": "9670bec…", "dirty": true,
        "tracked_modified": 1, "untracked": 2,
        "tree_digest": "99996de367ae56b5…"}
```

That block is itself the `PROV-02` fix working: a generation-0 manifest would
have said only `dirty: true`, and could not have told a reader whether one file
or an entire subsystem was missing.

---

## 1. A-5 — re-verification of prior claims

`A-5` requires re-running claims promoted by *earlier generations of this loop*
alongside claims sampled from the pre-existing matrix. Own output gets no special
standing.

### 1a. Generation-0 promoted claims

Each is guarded by a test that **re-measures** rather than hard-codes, so a full
suite run re-verifies it by construction rather than by assertion.

| claim | promoted value | re-verified |
|---|---|---|
| built-in potential rel. error | `7.24e-14` | ✅ selftest prints `7.24e-14` |
| mass action at equilibrium | `2.93e-09` | ✅ selftest prints `2.93e-09` |
| GRAD-02/03 closed, float64 | 0 non-finite / 402 | ✅ 41 ohmic tests green |
| GRAD-02/03 closed, float32 | 0 non-finite / 402 | ✅ same |
| PROV-02 dirty detection | untracked counts | ✅ 16 provenance tests green |
| blast radius of GRAD-03 | 0/26 weight tensors | ✅ pinned and green |

### 1b. Experiment re-verification — the `SPEC-g0-1` gap

All seven experiment launchers re-run into `outputs/<experiment>_g1/`, compared
leaf-by-leaf against the recorded artefact. **Timing fields are separated out
rather than counted as disagreements**: wall-clock is not a scientific claim, and
the machine was under load throughout (`train_seconds` roughly doubled).

| experiment | leaves | non-timing differences | verdict |
|---|---|---|---|
| `run_results` (generation 0) | 174 | **0** | ✅ bit-identical |
| `uq_benchmark` | 471 | **0** (10 timing) | ✅ D4, D5, D6 |
| `uq_tuning` | 424 | **0** (22 timing) | ✅ D4, D5 |
| `pinn_vs_surrogate` | 21 | **0** (2 timing) | ✅ D1, D2, D3 |
| `experiment_design` | 5066 | **0** (4 timing) | ✅ D10, D11, D12 — 2102/2102 integers identical |
| `gradient_fidelity` | 1639 | **0** (4 timing) | ✅ D7, D8, D9 |
| `identifiability_robustness` | 3287 | **0** (0 timing) | ✅ D13, D14, D14a — 1847/1847 integers identical |
| `identifiability` | 375 | 41 | ⚠️ `REPRO-01` — **all ranks identical** |

**Totals: 11,457 numeric leaves across eight experiments; 41 non-timing
differences, all in one experiment, all diagnostics; zero integer-valued leaves
changed anywhere.**

**`pinn_vs_surrogate` is the load-bearing one.** It re-ran *with* the
GRAD-02/GRAD-03 fix in place, and reproduced bit-identically:

```
pinn      median_rel_err  0.9999970197631748  ->  0.9999970197631748
pinn      p90_rel_err     1.0000456802107016  ->  1.0000456802107016
pinn      frac_within_50pct  0.05555555555555555 -> 0.05555555555555555
surrogate median_rel_err  0.026436009151515727 -> 0.026436009151515727
```

Generation 0 asserted, from a measurement of 0 NaN in 26 weight-gradient tensors,
that the fix could not disturb `D1`/`ADR-0004`. This is that assertion tested
end-to-end rather than argued: **it holds bit-for-bit.**

### 1c. Matrix claims

| claim | command | verdict |
|---|---|---|
| D20 README quick-start runs verbatim | extracted and executed | ✅ rc=0, monotone I–V, 8/8 biases trustworthy |
| D18 GaAs solves | `pytest -k GaAs` | ✅ 4 passed |
| S12 ECE floor at M=5 | `pytest -k floor` | ✅ 2 passed |
| D17 test suite | `pytest` | ⚠️ 240 → **352**; badge updated in the same candidate |

---

## 2. Findings

### REPRO-01 — `run_identifiability.py` does not reproduce its recorded artefact
| **Severity** | MEDIUM | **Status** | OPEN |

41 of 375 numeric leaves differ from `outputs/identifiability/identifiability.json`.
Median relative drift `1.906e-08`; maximum `5.840e-02`, at
`/devices/ldd/spectral_floor`.

**The claims are unaffected.** Every integer-valued leaf is identical — **0 of the
integer leaves changed** — so all four identifiable ranks (`step_symmetric` 4,
`step_asymmetric` 5, `graded` 3, `ldd` 4), every `resolvable_rank`, and all four
complete `rank_vs_noise` tables reproduce exactly. C12 and C13 hold.

**Runtime nondeterminism is ruled out, not assumed.** The forward Jacobian was
measured for bit-identity:

- twice within one process → identical, `max |ΔJ|/|J| = 0.000e+00`;
- three separate processes at default thread counts → same SHA-256;
- three separate processes with `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1`
  → same SHA-256.

Six runs, one hash. The initial hypothesis — BLAS thread-count-dependent reduction
order — is **wrong** and is recorded as wrong.

What remains is that the recorded artefact was produced on 2026-08-19 by a tree
that cannot now be identified. Its manifest says `6577f4b`, dirty — which
`PROV-04` establishes is not enough to reconstruct anything. So the most likely
explanation is a difference in the producing tree rather than in the runtime, and
**that explanation cannot be confirmed, because the producing tree is exactly what
was lost.** This is `PROV-03` made concrete: the first measurable cost of an
unattestable origin.

**Settled.** `run_identifiability.py` was re-run twice on the current tree:
**375 leaves, 0 differing — bit-identical to itself.** The script is fully
deterministic. `run_identifiability_robustness.py`, which exercises the same
solver 88 times, also reproduced bit-identically across 3287 leaves.

So the drift is **not** runtime nondeterminism. It is attributable to the
2026-08-19 artefact having been produced by a tree that cannot be identified —
and that explanation cannot be confirmed, because confirming it would require the
tree that was lost. `REPRO-01` is therefore recorded as **unresolvable**, not
closed: the first quantified cost of `PROV-03`.

### Carried open from generation 0

| id | severity | note |
|---|---|---|
| PROV-03 | HIGH | **permanent** — never closes |
| CI-01 | MEDIUM | reopened; `R-4` prohibits `git push`, so it cannot be closed here |
| PKG-04 | MEDIUM | `adapters.py:281` still `exec_module`s from the checkout. **Measured reachable**: `outputs/smoke/manifest.json` has `type: None` and would take that branch |
| API-05 | MEDIUM | `train_surrogate` minibatch path draws from the global RNG |
| SW-04a | MEDIUM | `except Exception: pass` in `provenance.py` |
| PROV-05, SW-18a, DOC-05, DOC-06 | LOW | untouched |
| S-3 | unassigned | duplication remains; equivalence pinned in value **and** gradient |

### Closed this generation

| id | severity | how |
|---|---|---|
| SEC-02 | MEDIUM | `weights_only=True` everywhere in library code; the warn-then-unsafe fallback removed after measuring that **all seven** shipped checkpoints load safely without it |

---

## 3. Non-findings — checked, sound

| area | outcome |
|---|---|
| Forward Jacobian determinism | bit-identical across 6 runs, 2 thread configurations |
| D1 / ADR-0004 under the g0c2 fix | **bit-identical** — the fix disturbed nothing |
| D4, D5, D6 (UQ backends) | 0 non-timing differences across 895 leaves in two experiments |
| README quick-start | runs verbatim, rc=0 |
| mypy | 25, the package only and never the tracked tree, unchanged — the SEC-02 fix introduced no new typing debt |
| Badge guard | fired correctly again at 309 → 352, as designed |

---

## 4. Phase A exit

- No `CRITICAL` opened. `REPRO-01` is `MEDIUM` and does not affect a published
  claim.
- `E-2` **not** triggered: no previously published claim is contradicted. The one
  candidate for it — that fixing GRAD-02/03 might have moved `D1` — was tested and
  reproduced bit-identically.
- `E-7` not triggered. `E-8` not triggered.
- `SPEC-g0-1` moves from **1 of 7** experiments verified to **4 of 7 confirmed**
  with three pending, and one (`identifiability`) confirmed at the level of every
  claim it makes while differing in diagnostics.
