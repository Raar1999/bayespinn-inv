# FINAL_REPORT_v1 — audit loop, generations 0–5

**Repository** `bayespinn-inv` · **Date** 2026-08-25
**Branch** `loop/champion` · **Parent** `6577f4b` (pre-audit, untouched)
**Champion** `b5218b1` · **Ruling** operator amendment of 2026-08-25

---

## 0. Termination status — stated first, because it did not happen

**The loop did not reach a §8 termination condition.** It is reported here at the
end of generation 5.

| condition | status |
|---|---|
| `T-1` all clauses PASS, no open CRITICAL/HIGH | **unreachable as specified.** `SPEC-g0-3` requires a retrievable CI run log per matrix leg; `R-4` prohibits `git push` and `SK-09` prohibits network access, so CI cannot run. `PROV-03` is permanently open by construction. `T-1` cannot be satisfied under the current rules. |
| `T-2` generation 8 completes | not reached — 6 generations (0–5) completed |
| `T-3` 48 h global wall-clock | not reached |
| `T-4` three consecutive stagnant generations | not reached — every generation promoted |
| `T-5` reserved halt (`R-1`, `R-5`, `R-6`) | none arose |

Reporting a termination that did not occur would be the most damaging thing this
document could do, so it is stated first. §9 says exactly what generation 6
inherits.

---

## 1. Findings opened and closed

| gen | opened | closed | severity-weighted closed |
|---|---|---|---|
| 0 | 3 CRITICAL, 6 HIGH, 4 MEDIUM, 4 LOW | 3 CRITICAL, 5 HIGH | **44** |
| 1 | 1 MEDIUM | 1 MEDIUM (`SEC-02`) | 2 |
| 2 | — | 1 MEDIUM (`PKG-04`) | 2 |
| 3 | — | 1 MEDIUM (`API-05`) | 2 |
| 4 | — | 1 MEDIUM (`SW-04a`) | 2 |
| 5 | — | 2 LOW (`DOC-05`, `DOC-06`) | 2 |
| **total** | **18** | **15** | **54** |

### Closed

| id | sev | what it was |
|---|---|---|
| `PROV-06` | CRITICAL | the repository's only commit was the **pre-audit project**; both audit cycles existed solely as uncommitted working-tree state |
| `PROV-02` | CRITICAL | `git_is_dirty()` used `--untracked-files=no`; a tree missing three source modules reported **clean** |
| `SCI-08` | CRITICAL | the claim surface quoted two mutually exclusive code states at once |
| `PROV-01` | HIGH | every `manifest.json` was gitignored — a clone shipped results with no provenance |
| `SCI-11` | HIGH | identifiability stated with no local/global label (PH-21) |
| `GRAD-02` | HIGH | NaN gradients above `C_s = 1.3922e8` — top 21.4% of the doping envelope |
| `GRAD-03` | HIGH | …and in float32, across **41 of 41** envelope points — 100% |
| `PROV-04` | HIGH | manifests naming a commit that cannot have produced them — superseded, not edited |
| `SEC-02` | MEDIUM | `weights_only=False` in library code, plus a warn-then-unsafe fallback |
| `PKG-04` | MEDIUM | library `exec_module`d a file from the source checkout (`SW-17`) |
| `API-05` | MEDIUM | minibatch sampling read the global RNG (`SW-09`) |
| `SW-04a` | MEDIUM | `except Exception: pass` in library code |
| `DOC-05`, `DOC-06` | LOW | prose contradicted by measurement |

### Open

| id | sev | why |
|---|---|---|
| `PROV-03` | HIGH | **permanent.** The adopted tree has no attestable origin. No candidate may close it. |
| `CI-01` | MEDIUM | reopened. The workflow had never been committed; `R-4` blocks the push that would exercise it. |
| `REPRO-01` | MEDIUM | **unresolvable** — see §5. Not a defect; a measured consequence of `PROV-03`. |
| `PROV-05`, `SW-18a` | LOW | manifest coverage and absolute paths in *existing* manifests, which `R-3` protects |
| `S-3` | unassigned | duplicate ohmic physics remains; equivalence pinned in value **and** gradient |

---

## 2. Claims that changed

| claim | before | after | evidence | commit |
|---|---|---|---|---|
| Built-in potential rel. error | `2.8e-7` | **`7.243e-14`** | n=1, grid-independent over N=101…601 | `4baccf6` |
| Mass action at equilibrium | `7.6e-6` | **`2.93e-9`** | 301 nodes | `4baccf6` |
| Equilibration gain | `1.32e-2 → 7.62e-6` (1730×) | **`6.77e-3 → 9.7e-10`** (7.0e6×) | 201-node grid | `4baccf6` |
| Identifiability | unqualified | **`local`** + operating point, noise, P, observation count | 4 devices | `4baccf6` |
| GRAD-02 scope *(the loop's own)* | NaN above `C_s ≈ 3.2e8`, float64 | **41/41 envelope points, float32** | 402 points | `01bb813` |
| Test suite | 240 | **403** | collected | `b5218b1` |
| Suite wall-clock | "~1 min 45 s" (unsourced) | **64.0 s** (n=3, 61–65 s) | measured | `b5218b1` |

---

## 3. Claims withdrawn

`A-7`: an empty withdrawal section is evidence the loop was not adversarial. It is
not empty.

**X15 — "built-in potential rel. error 2.8e-7."** Withdrawn, not corrected. Never a
guess: `git archive 6577f4b` and re-running reproduces `2.7558e-07` exactly. It
measured the **pre-audit** solver — a program the project no longer ships.
`RELEASE_READINESS` marked "Reference solver validated ✅" citing it.

**X16 — "mass action 7.6e-6."** Same cause, same tree.

**X17 — "equilibration improves mass action 1.32e-2 → 7.62e-6, a 1730× gain."** The
starting point was sound (`6.77e-3`, 1.95× away). The endpoint was not: the
adopted solver reaches `9.7e-10`, a true gain of ~**7.0e6×**. The published figure
understated the project's own improvement by ~4000×.

**X18 — identifiability without its regime.** Qualified rather than withdrawn; six
of seven instances corrected, one parked under `R-3`.

**The loop's own GRAD-02 scoping.** Generation 0 recorded "NaN for |C_s| ≳ 3.2e8"
from a float64 measurement. Its own falsifier broke that in the same generation:
float32 — the training dtype — fails at `C_s = 7.079e3`, *below* the envelope.
21.4% became 100%.

---

## 4. Pareto trajectory

| gen | front | promoted | f1 | f7 | f8 |
|---|---|---|---|---|---|
| 0 | {`g0c2`, `g0c4`} | `g0c2` | 4 | 1 file, 0 new symbols | **1** |
| 1 | {SEC-02} | SEC-02 | 2 | 2 files, 0 new symbols | 0 |
| 2 | {PKG-04} | PKG-04 | 2 | 3 files, 1 new symbol | 0 |
| 3 | {API-05} | API-05 | 2 | 1 file, 0 new symbols | 0 |
| 4 | {SW-04a} | SW-04a | 2 | 1 file, 0 new symbols | 0 |
| 5 | {DOC-05/06} | DOC-05/06 | 2 | 2 files, 0 new symbols | 0 |

Generation 0's front was decided on tie-break (b), lower blast radius, after f1
tied at 4. It tied because **S-3 carries no Phase-A severity**, and `AH-09` forbids
assigning one after the candidates exist to justify a promotion — which would have
handed it to a candidate that makes the oracle import the legacy PINN package
(module graph 8 → 10, measured).

Generations 1–5 each had a single viable candidate against a specific open
finding, so the front was a single point; the discipline that mattered there was
`AH-08` (regression before fix, both outcomes recorded) rather than selection.

---

## 5. Negative results, stated as results

1. **Solve time does not discriminate between the generation-0 candidates.** n=25,
   median + IQR; every interval overlaps. The proof it is noise-dominated is
   `g0c2` reading **−12.4%** while touching only `pinn/losses.py`, which the solver
   never imports. `g0c3`'s +5.4% was therefore **not** used as a cost.
2. **The BLAS-threading hypothesis for `REPRO-01` is wrong.** The forward Jacobian
   is bit-identical twice within one process, across three processes at default
   thread counts, and across three more with all thread variables pinned to 1. Six
   runs, one SHA-256. Recorded as wrong.
3. **`REPRO-01` is not a numerics defect.** `run_identifiability.py` re-run twice
   on the current tree: **375 leaves, 0 differing — bit-identical to itself.**
   `run_identifiability_robustness.py`, exercising the same solver 88 times,
   reproduced bit-identically across 3287 leaves. So the 41 differing floats
   versus the 2026-08-19 artefact come from a **producing tree that cannot be
   identified**. That explanation cannot be confirmed either, because confirming
   it would require the tree that was lost. It is the first **quantified** cost of
   `PROV-03`: 41 numbers that can never be explained.
4. **Fixing GRAD-02/GRAD-03 changed nothing in the PINN result.** Predicted from 0
   NaN in 26 weight-gradient tensors; confirmed by a bit-identical re-run.
   `ADR-0004` stands.
5. **Fixing API-05 changed nothing on the path every experiment uses.** Full-batch
   training is bit-identical pre- and post-fix (`c3aa71f10f7f8172`, same loss to
   every digit), and the global RNG is untouched.
6. **An "attestation" probe was discarded as invalid.** A check for whether the
   oracle survives retiring `pinn/` returned `True` for every candidate including
   the one that imports it — relative imports bypass the `builtins.__import__`
   guard it used. Not reported; the module-count measurement replaced it.
7. **The same test-design mistake was made twice.** Generations 1 and 2 both first
   wrote guards that substring-matched source text, and both failed on the comments
   documenting the finding. Both are now AST-level, which comments cannot satisfy.

---

## 6. Reproduction evidence

`SPEC-g0-1` went from **1 of 7** experiments verified to all eight artefacts
re-run and compared leaf-by-leaf.

| experiment | leaves | non-timing diff | integers changed |
|---|---|---|---|
| `run_results` | 174 | **0** | 0 |
| `uq_benchmark` | 471 | **0** | 0 / 136 |
| `uq_tuning` | 424 | **0** | 0 / 98 |
| `pinn_vs_surrogate` | 21 | **0** | 0 / 9 |
| `experiment_design` | 5066 | **0** | 0 / 2102 |
| `gradient_fidelity` | 1639 | **0** | 0 / 283 |
| `identifiability_robustness` | 3287 | **0** | 0 / 1847 |
| `identifiability` | 375 | 41 | **0 / 79** |

**11,457 numeric leaves. 41 non-timing differences, all in one experiment, all
diagnostics. Zero integer-valued leaves changed anywhere** — and the integers are
where the ranks live, so every identifiability claim reproduces exactly.

Timing fields were excluded and reported separately: the machine was loaded and
`train_seconds` roughly doubled. Counting that as non-reproduction would be
dishonest in the other direction.

---

## 7. What remains not release-grade

- **Provenance before `c115757` is unrecoverable, permanently** (`PROV-03`).
  Seven of eleven pre-existing manifests remain marked *not re-verified* in
  `docs/PROVENANCE_BIFURCATION_g0.md` rather than assumed good.
- **CI has still never run** (`CI-01`). `G-CODE`'s CI clause is FAIL, not skip.
- **Extrapolation (38% median, p90 860%) and family transfer (84% median)** remain
  poor and remain labelled. Unchanged by this loop.
- **σ is informative (ρ = +0.82) but over-conservative off-distribution** and is not
  a calibrated error estimate there. Unchanged.
- **The pure-physics PINN is legacy at 100% median relative error** (`ADR-0004`),
  now re-verified bit-identically.
- **`S-3`**: duplicate ohmic physics remains, equivalence pinned rather than removed.

---

## 8. The single highest remaining scientific risk

**Identifiability is local, and global non-identifiability is unmeasured.**

The measured result is the numerical rank of the forward Jacobian at one operating
point: 3–4 of 16 doping degrees of freedom at 2% noise (1 µm Si PN junction,
N_A = N_D = 1e22 m⁻³, 19 bias points over 0–0.9 V, P = 16), and 1–6 (median 3)
across 88 measurements spanning six axes. It does not grow with the
parameterisation: P = 8 → 32 leaves it at 3–4. All of it re-verified this session,
bit-identically, across 3,662 leaves.

Quantified gap: **zero** sampling-based or posterior-contraction measurements
exist. Nothing rules out distant doping profiles that fit the same I–V equally
well. A local Jacobian rank cannot.

This loop did not reduce that risk — scope was frozen behind `SPEC-g0-1` by §7 of
the ruling, and that clause only became satisfiable in generation 1. What the loop
did was stop the risk being *hidden*: every statement of the result now carries
the word `local` and its regime in every document the loop may edit. The one
remaining unqualified passage, `papers/draft.md:255`, is protected by `R-3`, pinned
by a test that fails in both directions, and escalated.

---

## 9. Rollback map

| gen | commit | what |
|---|---|---|
| — | `6577f4b` | pre-audit project. **Not** a rollback target: 42 tests, no `equilibrate`, live BUG-11/BUG-13 |
| 0 | `c115757` | adoption, attested 164/164 |
| 0 | `4baccf6` | PROV-02 fix, claim surface, `SPEC_g0` frozen |
| 0 | `01bb813` | falsifier product; `outputs/results_g0r/` |
| 0 | `06eb32f` | champion g0 — candidate g0c2 |
| 1 | `9670bec` | champion g1 — SEC-02 |
| 1 | `91f89b0` | hygiene: untrack accidentally committed run logs |
| 2 | `aff9195` | champion g2 — PKG-04 |
| 3 | `3302817` | champion g3 — API-05 |
| 4 | `de1b6f6` | champion g4 — SW-04a |
| 5 | `b5218b1` | **champion g5** — DOC-05, DOC-06 |

```bash
git switch -c inspect/<name> <commit>                  # branch, never a detached checkout
git archive <commit> | tar -x -C /some/scratch/dir     # inspect without touching the tree
git revert --no-commit <commit> && git commit          # undo one generation
```

**Preserved outside the repository** — the pre-adoption tree, 212 files,
digest-of-digests
`9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd`, verified
212/212 in each of two independent copies:

```
<scratch>/g0/preserve_A
D:/bayespinn-inv/_preserve_g0_B
```

Do **not** `git stash` or `git clean`: those copies and this branch are the only
records of the pre-adoption state.

---

## 10. What generation 6 inherits

1. **S-1, global identifiability.** `SPEC-g0-1` now passes on the evidence in §6,
   so scope unfreezes automatically (§7 of the ruling). This is the only remaining
   item that reduces §8's risk, and it is the highest-value work left.
2. **`S-3`**, if a Phase-A severity is assigned to it. That would move f1 and
   legitimately reverse generation 0's ordering — `g0c3` may then be revived, but
   only by citing its archive entry.
3. **`S-2`**, GRAD-01 in 2D and with a second architecture. The 1D result was
   re-verified bit-identically this session, so the baseline is solid.
4. **`PROV-05`, `SW-18a`** — both concern *existing* manifests, which `R-3`
   protects, so both need a supersede-not-mutate design.
5. **`CI-01`** stays open until an operator can push.

**Do not re-propose:** any fix narrowing the doping envelope (`AH-02`, archived as
`g0c6`); input-masking that keeps the quadratic (archived as `g0c1`, dominated).
