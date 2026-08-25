# FINAL_REPORT_v2 — audit loop, generations 0–6, terminated

**Repository** `bayespinn-inv` · **Date** 2026-08-25
**Branch** `loop/champion` · **Parent** `6577f4b` (pre-audit, untouched)
**Supersedes** `FINAL_REPORT_v1.md`, which reported a non-termination

---

## 0. Termination — `T-1` reached

| condition (amended §1) | status |
|---|---|
| all mandatory spec clauses `PASS` | ✅ `SPEC-g0-1,2,4,5,6,7`; `SPEC-g0-3a` for every leg available; `SPEC-g6-1…6` |
| no open `CRITICAL` | ✅ none |
| no open `HIGH` lacking one of the three statuses | ✅ only `PROV-03`, `ACCEPTED-PERMANENT`, cost statement in `GEN_g6.md` §2 |
| terminal adversarial generation produces no new `HIGH`+ | ✅ six falsifiers, **one new MEDIUM** |

`v1` reported that termination had not occurred, because `T-1` as originally
written was unreachable. The operator amended it, and it is now satisfied on the
evidence below.

Budget: ≈ 5 h of the 48 h global ceiling. 7 generations of a 12 ceiling.

---

## 1. Findings, by generation

| gen | opened | closed | severity-weighted closed |
|---|---|---|---|
| 0 | 3 CRIT, 6 HIGH, 4 MED, 4 LOW | 3 CRIT, 5 HIGH | 44 |
| 1 | 1 MED | 1 MED (`SEC-02`) | 2 |
| 2 | — | 1 MED (`PKG-04`) | 2 |
| 3 | — | 1 MED (`API-05`) | 2 |
| 4 | — | 1 MED (`SW-04a`) | 2 |
| 5 | — | 2 LOW | 2 |
| 6 | 2 MED (`NB-02`, `PROV-07`), 1 LOW | 1 LOW (BUG-14 recurrence) | 1 |
| **total** | **21** | **16** | **55** |

### Open at termination

| id | sev | status | why |
|---|---|---|---|
| `PROV-03` | HIGH | **`ACCEPTED-PERMANENT`** | the adopted tree has no attestable origin; the evidence needed to close it no longer exists. Cost statement: `GEN_g6.md` §2 |
| `CI-01` / `SPEC-g0-3b` | MED | **`OPERATOR-BLOCKED`** | needs a `git push`; `R-4` forbids it. Commands: `docs/OPERATOR_TASKS.md` OT-1 |
| `REPRO-01` | MED | **`UNRESOLVABLE-BY-CONSTRUCTION`** | 41 numbers whose explanation requires a tree overwritten before generation 0 preserved anything |
| `NB-02` | MED | open | the CI notebook step destroys the committed executed outputs; CI is green only by step ordering |
| `PROV-07` | MED | open | found by A-6: code in a `.gitignore`'d directory is invisible to all three provenance fields |
| `PROV-05`, `SW-18a` | LOW | open | concern *existing* manifests, which `R-3` protects |
| `S-3` | — | open, pinned | duplicate ohmic physics remains; equivalence pinned in value **and** gradient over 402 points |

---

## 2. The scientific result

**Global non-identifiability is demonstrated by concrete witness, and survives
falsification.**

At d=4 over a 1e21–1e23 m⁻³ log-uniform prior, 16 biases over 0.15–0.90 V, and a
2.0e-02 distinguishability floor = max(noise 2.0e-02, solver 1.5e-03):

- **13 witness pairs** among 1,999,000 examined
- the closest differs by **8.18× in doping** at one anchor and **1.23% in I–V**
- all three pairs tested **survive** 4× grid refinement (N=301/601/1201) and
  `tol_carrier=1e-12`; pair 0's distance *falls* 1.23e-02 → 8.61e-03

Oracle-arbitrated throughout. The surrogate was never called, for two independently
measured reasons: `GRAD-01` (its derivatives are informative only *inside* the
identifiable subspace, which is not where this study looks) and `PH-22` (its
float32 path cannot represent doping differences below ~1e-7 relative, where the
oracle round-trips to 1.678e-16). `ADR-0007`.

For scale: `C14`'s equivalence twins were **constructed** along locally flat
directions and differ by 1.26×. These were **found by search** and differ by 8.18×.

**Stated limits.** Contraction at the instrument's own 2% noise is **not
measured** — the estimator collapses (ESS 1.0 of 2,000, all variance ratios 0.000,
which would report as "4 of 4 directions contract"). The measurable band is narrow:
at 10× the noise, ESS 71, **3 of 4** directions contract. The d=8 point of the
dimension sweep is confounded with sampling density (500 → 250 → 125 samples per
dimension) and is not evidence of less information at higher `d`. Nothing is
established at d=16, the parameterisation the local result uses.

---

## 3. Claims withdrawn

Non-empty, as `A-7` requires.

| withdrawn | replaced by | why |
|---|---|---|
| built-in potential `2.8e-7` | **`7.243e-14`** | measured the *pre-audit* solver; `git archive 6577f4b` reproduces `2.7558e-07` exactly |
| mass action `7.6e-6` | **`2.93e-9`** | same cause |
| equilibration gain `1.32e-2 → 7.62e-6` (1730×) | **`6.77e-3 → 9.7e-10`** (7.0e6×) | the endpoint understated the project's own improvement by ~4000× |
| identifiability without a regime label | `local` + regime, 6 of 7 sites | `PH-21`; the 7th is `R-3`-protected and has a corrigendum |
| **"global non-identifiability is unmeasured"** | **13 witnesses, up to 8.18×** | measured in generation 6 |
| GRAD-02's scope, *the loop's own* | 41/41 float32 envelope points | its own falsifier overturned it in the same generation |
| generation 1's "diagnostics only" | 7 of 41 leaves back published numbers | its own leaf audit overturned it in generation 6 |

The last two matter most: **the loop twice overturned its own findings**, once
within a generation and once across five.

---

## 4. Negative results, stated as results

1. **No second GRAD-02.** The PH-22 retro-sweep found both boundary-crossing
   quantities degrade gracefully to their dtype's epsilon; `bernoulli` never
   crosses. Reported as an absence.
2. **Contraction is not measurable at the instrument's noise level** with prior
   importance sampling at n=2,000. A method limitation, reported as one; reaching
   2% needs SMC or MCMC, not a larger `n`.
3. **The BLAS-threading hypothesis for `REPRO-01` was wrong** — six runs, one
   hash. Recorded as wrong.
4. **Solve time did not discriminate** between the generation-0 candidates; the
   proof is `g0c2` reading −12.4% while provably unable to touch the solver.
5. **An attestation probe was discarded as invalid** — relative imports bypassed
   the guard it relied on.
6. **The A-6 falsifiers mostly failed**, which is the point: 5 of 6 found nothing.
7. **Fixing GRAD-02/03 and API-05 changed no published number** — both confirmed
   bit-identically rather than argued.

---

## 5. Reproduction evidence

`SPEC-g0-1` went from **1 of 7** experiments verified to all eight artefacts
re-run and compared leaf-by-leaf: **11,457 numeric leaves, 41 non-timing
differences (all in one experiment, all diagnostics), zero integer-valued leaves
changed anywhere.** The integers are where the ranks live, so every identifiability
claim reproduces exactly.

The load-bearing one: `run_pinn_vs_surrogate` re-ran *with* the GRAD-02/03 fix and
reproduced bit-identically (PINN median `0.9999970197631748`), confirming end-to-end
what generation 0 had argued from 0 NaN in 26 weight-gradient tensors.

---

## 6. Pareto trajectory

| gen | promoted | f1 | f7 | f8 |
|---|---|---|---|---|
| 0 | `g0c2` asinh ohmic | 4 | 1 file, 0 new symbols | **1** |
| 1 | SEC-02 | 2 | 2 files | 0 |
| 2 | PKG-04 | 2 | 3 files, 1 new symbol | 0 |
| 3 | API-05 | 2 | 1 file | 0 |
| 4 | SW-04a | 2 | 1 file | 0 |
| 5 | DOC-05/06 | 2 | 2 files | 0 |
| 6 | S-1 + Phase A | — | 6 files, 3 new symbols | **1** |

`f8 = 2` across the loop: GRAD-03 (g6's falsifier overturning g0's scoping) and the
REPRO-01 leaf audit (g6 overturning g1's characterisation).

---

## 7. What remains not release-grade

- **Provenance before `c115757` is unrecoverable, permanently** (`PROV-03`). Seven
  of eleven pre-adoption manifests remain *not re-verified* rather than assumed
  good.
- **CI has never run** (`CI-01`). `OPERATOR-BLOCKED`; `G-CODE`'s CI clause is FAIL,
  not skip. The 3.9 and 3.12 legs have never executed anywhere, and
  `pyproject.toml`'s claim that 3.9 support "is backed by the CI matrix" is
  currently unsupported.
- **`NB-02`, `PROV-07`** — two MEDIUM defects found in generation 6, not fixed.
- **Extrapolation (38% median, p90 860%) and family transfer (84% median)** remain
  poor and remain labelled.
- **σ is over-conservative off-distribution** and is not a calibrated error
  estimate there.
- **The pure-physics PINN is legacy at 100% median error** (`ADR-0004`),
  re-verified bit-identically.
- **`S-3`** — duplicate ohmic physics remains, equivalence pinned rather than removed.

---

## 8. The single highest remaining scientific risk

**The global result is established at d ∈ {2,4,8}; the published local result uses
d = 16, and the two have never been measured on the same parameterisation.**

S-1 removed the previous top risk — global non-identifiability is no longer
unmeasured. What replaces it is narrower and sharper: `3–4 of 16` (local, 2%
noise) and `3 of 4` (global, d=4, 20% noise) are not the same fraction, cannot be
quoted as though they were, and the study that would reconcile them — a witness
search and contraction spectrum at d=16 with `n` scaled to the dimension — was
outside the pre-registered budget.

Quantified gap: at d=8 with n=1,000 the sampler already has only 125 samples per
dimension and the contraction count falls to 1 of 8, confounded. A d=16 study needs
`n` scaled with `d`, which at 0.36 s per oracle curve is hours, not minutes.

---

## 9. Rollback map

| gen | commit | what |
|---|---|---|
| — | `6577f4b` | pre-audit project. **Not** a rollback target |
| 0 | `c115757` | adoption, attested 164/164 |
| 0 | `4baccf6` | PROV-02 fix, claim surface, `SPEC_g0` frozen |
| 0 | `01bb813` | falsifier product; `outputs/results_g0r/` |
| 0 | `06eb32f` | champion g0 — `g0c2` |
| 1 | `9670bec` · `91f89b0` | champion g1 — SEC-02, plus a hygiene correction |
| 2 | `aff9195` | champion g2 — PKG-04 |
| 3 | `3302817` | champion g3 — API-05 |
| 4 | `de1b6f6` | champion g4 — SW-04a |
| 5 | `b5218b1` | champion g5 — DOC-05/06 |
| 6 | `bf5aa21` | g6 Phase A |
| 6 | `1a090f0` · `d3b7693` | g6 Phase C machinery, and the correction to its commit message |
| 6 | `a59255e` | **champion — S-1 result** |

```bash
git switch -c inspect/<name> <commit>                  # branch, never a detached checkout
git archive <commit> | tar -x -C /some/scratch/dir     # inspect without touching the tree
git revert --no-commit <commit> && git commit          # undo one generation
```

**Preserved outside the repository** — the pre-adoption tree, 212 files,
digest-of-digests `9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd`,
**re-verified 212/212 in each of two independent copies at termination**:

```
<scratch>/g0/preserve_A
D:/bayespinn-inv/_preserve_g0_B
```

Do **not** `git stash` or `git clean`.

---

## 10. Operator actions

`docs/OPERATOR_TASKS.md`:

- **OT-1** — push `loop/champion` and trigger CI. Closes `SPEC-g0-3b` / `CI-01`.
  Expect 438 passed per leg; a different count is a finding. Watch the 3.9 leg
  especially — it has never run anywhere.
- **OT-2** — apply `papers/CORRIGENDA_g6.md` COR-1. Closes the last `SCI-11`
  instance. The parked-instance test will then fail **by design**, which is the
  signal to move `papers/draft.md` into `CLAIM_SURFACE` and delete that test.

---

## 11. Gates at termination

ruff **exit 0** · **438 passed, 0 failed** · selftest **PASS** · mypy **25**,
unchanged from the generation-0 baseline across seven generations · fresh wheel
builds, installs and imports with no checkout present.
