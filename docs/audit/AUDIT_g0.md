# AUDIT_g0 — Phase A ledger

**Generation** 0 (bootstrap; no `LOOP_STATE` existed) · **Date** 2026-08-25
**Tree** `6577f4b87a65cd2c255062e42ea5181f04483e93`, branch `main`, **dirty**
**Environment** Python 3.11.9 · NumPy 2.4.4 · SciPy 1.17.1 · PyTorch 2.11.0+cu128 ·
Windows 11 (10.0.26200) · CPU · `make` not installed (targets executed directly)

Phase A was read-only with respect to `src/`, `tests/`, `configs/` and `scripts/`.
No file in those trees was modified. New experiment output was written only to
`outputs/results_g0/` (never into an existing results directory, SK-05).

---

## 0. Ground truth — measured, not inherited

| Gate | Command actually run | Result |
|---|---|---|
| `make lint` (ruff) | `python -m ruff check src/bayespinn_inv tests scripts` | **exit 0**, "All checks passed!" |
| `make lint` (mypy, advisory) | `python -m mypy src/bayespinn_inv` | **25 errors in 9 files** (40 source files checked) — baseline |
| `make test` | `PYTHONPATH=src python -m pytest tests -q --tb=short` | **240 passed**, 63.84 s |
| `make selftest` | `PYTHONPATH=src python -m bayespinn_inv.cli selftest` | **PASS** (6/6 checks) |
| wheel build | `setuptools.build_meta.build_wheel` (see §5) | ok; all 40 modules **byte-identical** to committed `dist/*.whl` |
| `make check-install` (selftest) | `<venv>/Scripts/bayespinn.exe selftest` | **PASS** |
| `make check-install` (suite) | `<venv>/Scripts/python -m pytest tests -q` against the **installed wheel** | **240 passed**, 54.22 s |
| CI matrix (incl. Windows job) | — | **CANNOT BE EVALUATED** → FAIL (see CI-02) |

`mypy` baseline for the "may not increase" rule: **25**, over
`python -m mypy src/bayespinn_inv` — the package only, never the tracked tree.
Test-count baseline for the "may only go up" rule: **240**.

---

## 1. Findings

| ID | Sev | File / artefact | Evidence command | Measured | Expected / claimed |
|---|---|---|---|---|---|
| PROV-06 | **CRITICAL** | `HEAD` vs working tree | `git archive HEAD src \| tar -x`; re-run the physics | **HEAD is the pre-audit repository**: 34 modules, 42 tests, no `equilibrate` option, V_bi err **2.76e-7**, mass action **6.10e-3** | working tree: 40 modules, 240 tests, V_bi err **7.24e-14**, mass action **2.93e-9** |
| SCI-08 | **CRITICAL** | `README.md:56`, `docs/CLAIM_EVIDENCE_MATRIX.md:37,38,48`, `docs/RELEASE_READINESS.md:39` | `bayespinn selftest` on each tree | claim surface quotes **HEAD's** solver numbers but the **working tree's** test count and D-series | one document, two mutually exclusive code states |
| PROV-03 | **HIGH** | whole tree | `git ls-files --error-unmatch <path>` | 33 pre-existing untracked paths; **204 of 246 collected tests (83%) live in untracked files** | results claim provenance from `6577f4b` |
| PROV-01 | **HIGH** | `outputs/results/manifest.json` | `git ls-files outputs/` | only `results.json`, `results_summary.md` tracked; manifest is gitignored | SW-13: every result dir ships a manifest |
| PROV-02 | **HIGH** | `src/bayespinn_inv/utils/provenance.py:57` | `git status --porcelain --untracked-files=no` → 70; default → 99 | dirty flag blind to untracked files | docstring: "not reproducible from the commit alone… must be recorded" |
| GRAD-02 | **HIGH** | `src/bayespinn_inv/pinn/losses.py:130,133` | autograd through `ohmic_boundary_values` | **NaN** gradient for \|C_s\| ≳ 3.2e8 (N ≳ 3.2e24 m⁻³) | finite gradient across the documented 1e21–1e25 m⁻³ envelope |
| SCI-11 | **HIGH** | `README.md:51,340` | `grep -i "\blocal\b" README.md` | identifiability reported with **no** `local` qualifier | PH-21; `papers/draft.md:23,73,349` does label it |
| CI-02 | **HIGH** | `.github/workflows/ci.yml` | `git ls-files --error-unmatch` → not in git | CI has **never run**; `AUDIT_MASTER` CI-01 marked **VERIFIED** | G-CODE requires a green matrix incl. Windows |
| SEC-02 | MEDIUM | `training/trainer.py:386`; `surrogate/adapters.py:237` + 4 scripts | `grep -rn torch.load` | `weights_only=False` unconditional in library code; warn-then-unsafe fallback | SW-16: always `weights_only=True`; SW-03: a warning is not a forced status read |
| PKG-04 | MEDIUM | `surrogate/adapters.py:281` | `grep -n spec_from_file_location` | still `exec_module`s a file from the source checkout | SW-17 forbids it; mitigation only improved the error message |
| API-05 | MEDIUM | `surrogate/iv_surrogate.py:205` | double-run of `train_surrogate(..., batch_size=32)` | **not** bit-identical (`091450bf…` vs `cc67824a…`) | SW-09: every RNG seeded from `cfg.seed` |
| SW-04a | MEDIUM | `utils/provenance.py:83` | `grep -rn "except Exception"` | `except Exception: pass` in library code | SW-04 |
| PROV-04 | LOW | `outputs/{smoke,surrogate_ensemble}/manifest.json`; `outputs/{calib_surrogate,inv_sweep_surrogate}/` | manifest scan | `commit=None, dirty=None`; two dirs have **no** manifest | SW-13 |
| SW-18a | LOW | `outputs/results/manifest.json:217`, `outputs/surrogate_ensemble/manifest.json:58` | `grep -rn "C:\\Users\|/home/"` | `C:\Users\abhis\…` and `/home/claude/…` — two different machines | SW-18 forbids absolute home paths in manifests |
| PROV-05 | LOW | `outputs/results/manifest.json` | leaf comparison | `results` block covers H1/H2/H3 only; C11/C21/C22 (H4b/H5) have no manifest coverage | SW-13 |
| DOC-05 | LOW | `README.md:315` | `python -m pytest tests -q` | 63.8 s | "~1 min 45 s" |
| DOC-06 | LOW | `physics/constants.py:80` | `pytest -k GaAs` → 4 passed | GaAs **is** exercised | docstring: "not exercised in M1-M2" |

---

## 2. Finding detail

### PROV-06 — the repository has bifurcated: `HEAD` is the *pre-audit* project
**Severity CRITICAL.** This is the root cause of SCI-08 and it triggers SK-17.

`git archive HEAD src | tar -x` into a scratch tree and run the same physics:

| Quantity | `HEAD` = 6577f4b | working tree |
|---|---|---|
| `src` modules | **34** | 40 |
| tests collected | **42** (4 files) | 246 (13 files) |
| `SGConfig(equilibrate=…)` | **does not exist** (`TypeError`) | present |
| V_bi rel. error | **2.7558e-07** | 7.243e-14 |
| mass action max\|np−1\| | **6.1019e-03** | 2.934e-09 |
| BUG-11 / BUG-13 fixes | **absent** (0 grep hits) | present |

HEAD's 42-test suite is *precisely* the "42-test suite" `README.md:106` describes as
the **pre-audit** state. Both audit cycles — every fix, every regression test, every
experiment script, every ADR, the entire ledger — exist only in the working tree.

### SCI-08 — the claim surface mixes two mutually exclusive code states
**Severity CRITICAL.** My first pass recorded these as "numbers that reproduce under
no configuration". That was wrong, and the correction matters: **they reproduce
exactly — against `HEAD`.**

| Claim | Published | `HEAD` measures | working tree measures |
|---|---|---|---|
| C17 built-in potential rel. err | `2.8e-7` | **`2.7558e-07`** ✓ | `7.243e-14` |
| C18 mass action | `7.6e-6` | `6.10e-3` (this config) | `2.93e-9` |
| S1 equilibration gain | `1.32e-2 → 7.62e-6` | feature **absent** | `6.77e-3 → 9.7e-10` |

So the documents are not fabricated and they are not stale carry-over: the
solver-quality rows were measured honestly **on the committed code**. The defect is
that the *same* documents quote the **working tree** for everything else — the
240-test badge, the 2.8% forward error, all of D1–D20. No single code state
reproduces the whole claim surface, and nothing discloses the split.

Consequence: `docs/RELEASE_READINESS.md:39` marks **"Reference solver validated ✅"**
on `HEAD`'s numbers, while the *validated* solver being described is the uncommitted
one. Whichever tree a reader checks out, part of the claim surface is wrong for it.

The `tests/test_claim_surface_g0.py` regression written at Phase A exit encodes the
working tree as the intended state (5 failed / 1 passed pre-fix). If the operator
decides `HEAD` is instead authoritative, that test is the wrong contract and must be
rewritten — see the ESCALATE block in `HALT_g0.md`.

### PROV-01/02/03 — the results are not reproducible from the commit they name
Every headline manifest records `git.commit: 6577f4b…` with `git.dirty: true`.
That commit does **not contain** the code that produced the results: 29 paths are
untracked, including `inverse/identifiability.py`, `utils/provenance.py`, `cli.py`,
`bayesian/surrogate_uq.py`, `active_learning/design.py`, `data/splits.py`, all seven
`run_*.py` experiment launchers, eight test files, the CI workflow, and the entire
`docs/AUDIT_MASTER.md` / `CLAIM_EVIDENCE_MATRIX.md` / `adr/` corpus.

Quantified: **204 of 246 collected tests (83%) live in untracked files**, including
`test_sg_numerics.py` (58 tests — the regression suite for BUG-01 … BUG-13) and
`test_mos_cap_physics.py` (27 tests — BUG-05 … BUG-09). The 42 tests that *are*
tracked are exactly HEAD's pre-audit suite.

Consequence: **no D-series claim (D1–D20) and no C12–C15/C21/C22 is recoverable from
git.** They exist only in this working tree.

`git_is_dirty()` compounds this: it calls `git status --porcelain --untracked-files=no`,
so it is structurally blind to untracked files. A manifest can record `dirty: false`
while the entire producing codebase is absent from the commit. Here it happens to
record `true` only because 70 *tracked* files also differ.

`outputs/results/manifest.json` is itself untracked and matched by the `outputs/*`
ignore rule (only `results.json` and `results_summary.md` are un-ignored), so a fresh
clone ships the headline results with **no provenance record at all**.

Verified sound: the manifest's 102 numeric leaves match `results.json` **exactly**
(0 mismatches). The provenance defect is one of recoverability, not of fabrication.

### GRAD-02 — NaN gradients in the ohmic boundary condition (new)
`pinn/losses.py:130`:
```python
n_s_L = torch.where(posL, 0.5 * ( C_s_left  + sqrtL),
                          1.0 / (0.5 * (-C_s_left  + sqrtL)))
```
`torch.where` evaluates **both** branches. For large positive `C_s`,
`-C + sqrt(C²+4)` underflows to exactly `0.0` (measured: `1.49e-08` at `C_s=1e8`,
`0.0` at `C_s=1e9`), so the discarded branch is `inf`; the backward pass computes
`0 * inf = NaN`, which contaminates the gradient of the *selected* branch.

Measured onset — finite at `C_s = 10^8.25`, NaN from `10^8.5` onward:
```
C_s=1e8.25  grad= 8.27e-25   finite=True
C_s=1e8.50  grad= nan        finite=False
C_s=1e9.00  grad= nan        finite=False
```
`C_s = 3.2e8` ⇒ `N ≈ 3.2e24 m⁻³`. The solver's own BUG-11 comment states the claimed
doping range is **1e21–1e25 m⁻³**, so the NaN region sits inside the documented
envelope (top ~half-decade).

**Honest blast radius: no current published number is affected.** The protocol bands
are `train [1e21, 2e22]` (C_s ≤ 2.0e6) and `extrap [2e20, 8e22]` (C_s ≤ 8.0e6) — both
roughly two decades below onset. In particular **D1/ADR-0004 (the PINN's 100% error)
is _not_ confounded by this bug**; the PINN never saw C_s ≥ 3.2e8. This is a latent
defect in exported public API (`losses.__all__`), not a wrong result.

Scoped precisely: the *values* of the two duplicated ohmic implementations agree to
full precision across `C_s = 1e0 … 1e11` (S-3's "they agree today" holds). Only the
gradients diverge. The two sibling `torch.where` sites
(`data/datasets.py:219`, `pinn/forward_pinn.py:136`) are guarded by `+1e-30`, produce
no `inf`, and were verified to yield finite gradients — they are **not** affected.

### SCI-11 — the headline identifiability claim is unlabelled
`inverse/identifiability.py` is scrupulous: "the **local** Jacobian", "**Local**
identifiability of a forward map at one operating point", "standard
local-identifiability treatment". `papers/draft.md` labels it three times, including
an explicit limitation at line 349.

`README.md` — the document with the widest readership — uses the word `local` exactly
once (line 76, about *local doping*, unrelated). Its headline row 51 and contribution
row 340 both state "I–V determines only **3–4 of 16** doping dof at 2% noise" with no
local/global qualifier and no operating point. PH-21 forbids exactly this. The number
is correct; the scope label is missing, which invites reading a local Jacobian rank as
global non-identifiability — the S-1 seed risk, realised in the claim surface.

### CI-02 — CI-01 is a false closure
`AUDIT_MASTER` §6b records CI-01 as **VERIFIED**, describing a matrix over
3.9/3.11/3.12 plus a Windows job and a clean-install job. The file exists on disk and
is well written — but it is **untracked**, so it has never been committed, never
pushed, and never executed. §6 G-CODE requires a green CI matrix including the Windows
job; that clause is currently **unevaluable, therefore FAIL**.

---

## 2b. Claim re-verification (Phase A step 2) — k = 5 sample

Weighted toward the headline table. Every reproducing command was executed.

| # | Claim | Verdict |
|---|---|---|
| C1–C11, C21, C22 | the entire `run_results.py` headline block | ✅ **all 174 numeric leaves bit-identical** on re-run |
| C17 | built-in potential `2.8e-7` | ❌ **SCI-08** — reproduces on `HEAD`, not on the working tree |
| C18 / S1 | mass action, equilibration gain | ❌ **SCI-08** — same split |
| D17 | test suite 240 passing | ✅ 240 |
| D18 | GaAs PN junction solves | ✅ `pytest -k GaAs` → 4 passed |

The headline re-run is the strongest positive result of this generation:

```
PYTHONPATH=src python scripts/run_results.py --out outputs/results_g0
```
174/174 numeric leaves identical to `outputs/results/results.json`, including
C1 interpolation `0.027834281028660313`, C2 extrapolation `0.3818233071446869`,
C3 family transfer `0.8423089146208244`, C4 `9.961050987243652` decades.

This settles two gates at once: the headline science is **honest and exactly
reproducible**, and **G-REPRO's bit-identity requirement passes at full experiment
scale** (not a smoke run — 2500 epochs, M = 5, the full protocol). The reproducibility
problem in this repository is *not* the numbers; it is that the tree producing them is
absent from git.

---

## 3. Non-findings — checked this session, found sound

Silence is not a result; these were measured, not assumed.

| Area | What was checked | Outcome |
|---|---|---|
| Lint | `ruff` over `src tests scripts` | exit 0 |
| Suite | 240 tests, checkout **and** installed wheel | both green |
| Packaging | fresh wheel vs committed wheel | all 40 modules **byte-identical**; only `dist-info` metadata differs (older setuptools) |
| PKG-03 | `py.typed` in the wheel | present |
| PKG-01 | console script on a clean install | `bayespinn.exe selftest` works from the venv |
| API-03 | construction reseeding the global RNG | **fixed and verified**: `torch.manual_seed(123)` draws identical with/without an intervening `IVSurrogate(...)`; init weights bit-identical |
| SW-11 determinism | `train_surrogate` full-batch, twice | **bit-identical** (`c3aa71f1…`, loss `4.2578307329677045e-4`) |
| Seeding discipline | `run_results.py:143-144,250-251,345` | global `torch`/`numpy` seed + per-member `seed=m` + per-member `RandomState(m)` bootstrap + independent RNG per (level, noise, seed) |
| PH-08 conservation | `max\|J−Ī\|/\|Ī\|` across the device | `2.9e-4` @0.2 V, `8.1e-8` @0.4 V, `9.3e-11` @0.6 V |
| PH-09 equilibrium | terminal current at V=0 | `-9.7e-7` A/m², `trust=False` — correctly **not** reported |
| S-3 ohmic duplication | value agreement across `C_s = 1e0 … 1e11` | agree to full precision (gradients do not — GRAD-02) |
| S-4 GaAs | `pytest -k GaAs` | **4 passed** — seed item **closed**; D18 verified |
| PH-20 / SCI-01 / SCI-06 | `data/splits.py` | five level sets disjoint **by construction**, asserted at runtime, single shared implementation; levels never cross splits |
| PH-15 | README extrapolation & family-transfer rows | correctly labelled ("outside the training doping band", "trained on steps only") |
| SK-13 | README headline table | every statistic carries `n` and a 95% interval |
| DOC-03 | README test sub-counts | 58 solver-numerics ✓, 27 MOS-cap physics ✓, badge 240 ✓ (the "42-test suite" mention is legitimate pre-audit narrative) |
| U1 notebooks | execution counts in all twelve | all code cells executed |
| S12 ECE floor | `pytest tests/test_robustness.py -k floor` | 2 passed |
| `torch.where` siblings | `datasets.py:219`, `forward_pinn.py:136` | `+1e-30` guard prevents `inf`; gradients finite |
| Manifest integrity | 102 shared numeric leaves, manifest vs `results.json` | **0 mismatches** |
| Anti-drift guard | `test_notebooks.py::TestDocumentedTestCountIsHonest` | **works** — it collects the suite in a subprocess and asserts the README badge equals the count. Adding 6 tests at Phase A exit made it fire (`badge 240 vs collected 246`), exactly as designed. Best hygiene mechanism in the repository. |
| Injection sweep (SK-01/02) | docstrings, `TODO`/`FIXME`, notebook markdown, manifests, ledger prose | **no `INJECTION-*`**. All directive-sounding text found (e.g. `losses.py` "Matches the SG solver convention…") is descriptive documentation, not an instruction to the auditor. |

### Persona coverage (§4 step 3)
| Persona | Result |
|---|---|
| Physicist | PH-07/08/09 verified; conventions consistent; **GRAD-02** raised |
| Numerical analyst | grid-independence of V_bi measured; NaN-onset threshold bracketed to a quarter-decade |
| ML reviewer | splits disjoint by construction — no leakage found (**E-7 not triggered**) |
| Bayesian reviewer | ECE floor test green; README carries `n` + intervals throughout |
| Inverse-problem researcher | **SCI-11** — local/global label missing in README only |
| Research reviewer | claim surface vs `papers/draft.md` cross-checked; **SCI-08** raised |
| Reproducibility reviewer | **PROV-01/02/03**, API-05; determinism measured on the used path |
| Software engineer | SEC-02, PKG-04, SW-04a; mypy baseline fixed at 25, over `python -m mypy src/bayespinn_inv` |
| Industry engineer | doping envelope vs NaN onset quantified; `weights_only` footgun |
| Release engineer | **CI-02**; wheel verified; version single-sourced (VER-01 holds: `0.1.0-dev` from the attr) |

---

## 4. Recurrence check against historical defect classes

| Class | Pattern grepped | Verdict |
|---|---|---|
| BUG-14 encoding | text `open()` without `encoding=` | **clean** in `src`/`scripts` (only `test_notebooks.py` prose mentions it) |
| SEC-01 | `weights_only=False` | **RECURRED** → SEC-02 |
| PKG-02 | `exec`/`spec_from_file_location` from checkout | **RECURRED** → PKG-04 |
| API-03 | seeding in constructors | **fixed**, verified |
| BUG-11 duplicate physics | `_ohmic_bc` vs `ohmic_boundary_values` | duplication **persists**; values agree, gradients do not → GRAD-02 |
| SW-04 | bare `except` / `except…pass` | one instance → SW-04a |
| SW-18 | absolute home paths | **RECURRED** in manifests → SW-18a |
| aggregate-without-raw | manifest scan | two dirs manifest-less → PROV-04 |

---

## 5. Protocol deviations recorded (SK-12 / AH-07)

1. **`make` is not installed.** Every target was executed directly with the same
   command line the Makefile specifies. Recorded per gate in §0.
2. **`make check-install` could not be run as written, offline.** `python -m build`
   requires `setuptools>=68.0` in an isolated env (this box has 65.5.0), and a plain
   venv would need to download numpy/scipy/torch — both need network, which **SK-09
   forbids during audit**. Substitute actually run:
   `setuptools.build_meta.build_wheel` → `venv --system-site-packages` →
   `pip install --no-index --no-deps <wheel>`.
   **Verified sound:** import origin resolves to the venv's `site-packages`, not the
   checkout, so the suite genuinely ran against the installed wheel; and the fresh
   wheel is byte-identical to the committed one for all 40 modules.
   **Explicitly NOT verified:** dependency resolution from `pyproject.toml`, and the
   `setuptools>=68.0` build path. Those remain unevaluated, not passed.
3. **A plain venv on this machine is genuinely clean** (`ENABLE_USER_SITE=False`,
   `find_spec → None`), so the Makefile's own `check-install` is sound in principle;
   the leakage seen mid-audit was caused by the `--system-site-packages` substitute
   above and was suppressed before the gate was scored.
4. **The system Python carries an editable install pointing at this checkout**
   (`__editable__.bayespinn_inv-0.1.0.dev0.pth` → `D:\bayespinn-inv\…\src`). Noted
   because it makes "it imports fine" worthless as packaging evidence — the wheel run
   in §0 is the evidence.
5. **`make selftest` does not test the installed package** despite §2.1's description:
   the target sets `PYTHONPATH=src`, forcing the checkout. Only `check-install` exercises
   the installed path. Both were run separately in §0.

---

## 6. Phase A exit status

- **HALT under SK-17** — see `HALT_g0.md`. Trigger: *"a manifest whose `git.commit`
  does not match the tree that produced it."* Every manifest in `outputs/` records
  `git.commit: 6577f4b`, and that commit provably **cannot** produce those results —
  it has no `equilibrate` option, no BUG-11/BUG-13 fix, and a mass-action error six
  decades larger. `git.dirty: true` is disclosed, but it is computed with
  `--untracked-files=no` (PROV-02) and so cannot distinguish "a typo was fixed" from
  "a different solver, and 83% of the test suite, are missing from this commit".
- Adjudication (§0): Role A read `dirty: true` as adequate disclosure; Role B read the
  six-decade physics gap as a provenance failure. **Resolved by measurement, not
  preference** — HEAD lacks the feature entirely (`TypeError` on `equilibrate`), so
  the commit cannot have produced the results. Role B carries.
- `git.dirty: true` backs every headline number → **SW-15 blocks marking this
  generation's ledger complete** until PROV-01/02/03/06 are resolved. Recorded as
  `DIRTY-g0` per SK-16.
- Per SK-18, **no repair was attempted in this generation.** No file under `src/`,
  `configs/` or `scripts/` was modified at any point. Verified by mtime: of every file
  under `src/ scripts/ configs/ tests/`, only `tests/test_claim_surface_g0.py` is
  newer than the session start; all others retain their 2026-08-19 timestamps.
  AH-01 satisfied — no pre-existing test was edited, skipped, xfailed or narrowed.
- **Suite state at Phase A exit: 6 failed, 240 passed (246 collected).** ruff exit 0.
  The 6 failures are all intended and none indicates a new defect:
  - 5 × `test_claim_surface_g0.py` — the SCI-08 regression, required by AH-08 to fail
    on the pre-fix tree. Recorded pre-fix outcome: **5 failed / 1 passed**
    (`test_claim_matrix_equilibration_gain[before]` passes: `1.32e-2` vs `6.77e-3` is
    1.95×, inside the 10× band).
  - 1 × `test_notebooks.py::TestDocumentedTestCountIsHonest` — the repository's own
    badge guard firing because the suite grew 240 → 246. **Correct behaviour, not a
    defect.** It is not repaired here (SK-18); G-DOC already requires the candidate
    that lands these tests to update the README badge in the same candidate.
- **Baselines carried to generation 1:** mypy **25** findings over
  `python -m mypy src/bayespinn_inv` (may not increase);
  test count **246** (may only go up); ruff **exit 0**.
- **G-CODE fails at baseline** on the CI clause (CI-02): a gate that cannot be
  evaluated is FAIL, never skipped.
- One **CRITICAL** finding (SCI-08) is open. Per §4 Phase A exit and AH-08, a
  regression test that **fails on the pre-fix tree** must be written before any fix is
  attempted. No fix has been attempted.
- `E-2` is **not** triggered by GRAD-02: no previously published claim is contradicted
  (blast radius measured as two decades clear of every protocol band).
- `E-7` is **not** triggered: no leakage found.
- `E-8` is **not** triggered: no injection found.
