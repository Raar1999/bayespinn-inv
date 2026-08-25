# GEN_g0 — generation 0

**Date** 2026-08-25 · **Branch** `loop/champion` · **Champion** `06eb32f`
**Ruling** operator amendment of 2026-08-25 (halt lifted, standing delegation)

| commit | what |
|---|---|
| `6577f4b` | parent — the pre-audit project, untouched |
| `c115757` | adoption of the working tree, attested 164/164 |
| `4baccf6` | mandatory sequence: PROV-02 fix, claim surface, `SPEC_g0` frozen |
| `01bb813` | falsifier product: float32 gate + blast-radius pin, `outputs/results_g0r/` |
| `06eb32f` | **champion** — promoted candidate g0c2 |

---

## 1. What ran

### §6 mandatory sequence

| step | outcome |
|---|---|
| 0 preserve | 212 files, 4,117,152 bytes, digest-of-digests `9cd95213…`; two external copies, **both verified 212/212** |
| 1 adopt | `git switch -c loop/champion`; 166 files staged; **all 166 byte-identical to the working tree before commit** |
| 2 attest | `git archive c115757 \| tar -x` vs the preserve manifest → **164/164 byte-identical, 0 mismatched, 0 missing**. PASS |
| 3 PROV-02 | fixed first, before any manifest was regenerated. AH-08 both outcomes recorded |
| 4 regenerate | full `run_results.py` (2500 epochs, M=5, no `--quick`) → **174/174 leaves bit-identical**. PASS, no halt |
| 5 supersede | `docs/PROVENANCE_BIFURCATION_g0.md`, 11 manifests, existing files untouched |
| 6 claim surface | 3 figures withdrawn, 6 identifiability statements qualified, 1 parked under R-3 |
| 7 addendum | full battery re-run against the adoption commit — below |

**`core.autocrlf` was `true` at system level with no `.gitattributes` and 39+ CRLF
files.** Staging would have rewritten line endings and failed step 2. It was set
to `false` **locally** before staging so adoption preserved bytes exactly — the
ruling forbids *normalising past* a rewrite, not preventing one (`DEC-g0-1`).

### Gate battery at the champion

| gate | result |
|---|---|
| ruff | exit 0 |
| suite | **309 passed, 0 failed** |
| selftest (checkout) | PASS |
| mypy | 25 findings — **unchanged** from the generation-0 baseline |
| wheel build | fresh build succeeds |
| selftest (installed) | PASS |
| suite vs installed wheel | **308 passed, 1 skipped** |
| CI matrix | **FAIL — unevaluable.** `R-4` prohibits `git push`; see `SPEC-g0-3` |

The single skip is `test_manifest_reports_this_repository_honestly`, which skips
when the package is not imported from a checkout. That is the correct behaviour
and not a gap: the installed package reports provenance as **unknown** rather than
falsely reporting clean, which is the `Optional` contract `ADR-0006` specifies.

---

## 2. Findings

| id | severity | status |
|---|---|---|
| PROV-06 | CRITICAL | VERIFIED — tree adopted and attested |
| PROV-02 | CRITICAL | VERIFIED — untracked files now count |
| SCI-08 | CRITICAL | VERIFIED — 3 figures withdrawn |
| PROV-01 | HIGH | VERIFIED — `outputs/` tracked |
| SCI-11 | HIGH | VERIFIED (1 instance parked under R-3) |
| GRAD-02 | HIGH | VERIFIED — closed by g0c2 |
| GRAD-03 | HIGH | VERIFIED — opened by the falsifier, closed by g0c2 |
| PROV-04 | HIGH | SUPERSEDED — recorded, manifests not edited |
| **PROV-03** | **HIGH** | **OPEN — PERMANENT.** Never closes |
| **CI-01** | MEDIUM | **REOPENED** — the workflow had never run |
| SEC-02, PKG-04, API-05, SW-04a | MEDIUM | **OPEN** — not attacked this generation |
| PROV-05, SW-18a, DOC-05, DOC-06 | LOW | **OPEN** |

Severity-weighted closed this generation: 3×CRITICAL(8) + 5×HIGH(4) = **44**.

---

## 3. Claims withdrawn

`AH-07`/`A-7`: this section is expected to be non-empty.

| claim | published | measured | why |
|---|---|---|---|
| Built-in potential rel. error | `2.8e-7` | `7.243e-14` | measured the **pre-audit** solver; `git archive 6577f4b` reproduces `2.7558e-07` exactly |
| Mass action at equilibrium | `7.6e-6` | `2.93e-9` | same cause |
| Equilibration gain | `1.32e-2 → 7.62e-6` (1730×) | `6.77e-3 → 9.7e-10` (7.0e6×) | endpoint understated the improvement by ~4000× |
| GRAD-02 scope (the loop's own) | "NaN above `C_s ≈ 3.2e8`" | float32: NaN across **41 of 41** envelope points | float64-only scoping; broken by the falsifier |

The fourth row is the loop withdrawing its **own** generation-0 finding. That is
the falsifier working as designed.

---

## 4. Pareto trajectory

First generation, so no prior front. Front = {`g0c2`, `g0c4`}; promoted `g0c2` on
tie-break (b), lower f7. Full genomes, gate records and measured objectives:
`docs/gen/CANDIDATES_g0.md`. Archive: `docs/gen/ARCHIVE.md`.

`f8` (falsification yield) = **1** — GRAD-03, which invalidated the audit's own
scoping of GRAD-02 in the same generation that produced it.

---

## 5. Escalations

| id | status |
|---|---|
| `R-3` @ `papers/draft.md:255` | **PARKED.** One unqualified identifiability passage in a protected file. Pinned by a test that fails in both directions (`DEC-g0-4`). |

No `R-1`, `R-5` or `R-6` condition arose. The `SK-17` halt of the pre-ruling
audit was lifted by the operator and closed by adoption + attestation.

---

## 6. Next generation must attack

Evidence-backed, in priority order.

1. **The six experiments never re-verified.** `docs/PROVENANCE_BIFURCATION_g0.md`
   marks 7 of 11 manifests "not re-verified" — `run_identifiability`,
   `run_identifiability_robustness`, `run_uq_benchmark`, `run_uq_tuning`,
   `run_experiment_design`, `run_gradient_fidelity`, `run_pinn_vs_surrogate`.
   `SPEC-g0-1` claims one commit reproduces the claim surface; only
   `run_results.py` was actually re-run. Until the rest are, that clause is
   asserted for 1 of 7 experiments and measured for none of the others. **This is
   the largest gap generation 0 leaves.**
2. **GRAD-01 under the fixed gradient.** The surrogate-gradient fidelity result
   (cosine +0.50 inside the identifiable subspace, −0.00 outside) was measured
   before GRAD-02/GRAD-03 were fixed. The fix touches `pinn/losses`, not the
   surrogate, so the result *should* be unchanged — but "should" is not
   "measured", and `A-5` requires re-verifying prior claims rather than
   inheriting them.
3. **SEC-02** (`weights_only=False` unconditionally in `trainer.py:386`, and a
   warn-then-unsafe fallback in `adapters.py:237` that `SW-03` forbids), and
   **PKG-04** (`adapters.py:281` still `exec_module`s a file from the source
   checkout, `SW-17`). Both are MEDIUM, both untouched.
4. **S-1 global identifiability** — the highest remaining *scientific* risk. The
   result is local; global sampling-based non-identifiability is unmeasured. Now
   correctly labelled everywhere the loop may edit, which makes the gap explicit
   rather than hidden. `SPEC-g0-1` must pass before scope unfreezes (§7).

**Not to be re-proposed:** any fix that narrows the doping envelope (`AH-02`,
archived as `g0c6`); input-masking while keeping the quadratic (archived as
`g0c1`, strictly dominated).
