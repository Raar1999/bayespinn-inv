# Provenance bifurcation — generation 0 supersession record

**Adoption commit** `c115757f3e9829cd1feb8bb86d739bfd74ff2dcf` on `loop/champion`
**Parent** `6577f4b87a65cd2c255062e42ea5181f04483e93` — untouched: never rewritten, amended or reset
**Findings** AUDIT_g0 `PROV-06` (CRITICAL), `PROV-01`, `PROV-02`, `PROV-03`, `PROV-04`, `SCI-08`
**ADR** `ADR-0006`

This record exists because the existing manifests are protected (`R-3`) and are
**not** edited. Each one still names a commit that cannot have produced it. This
file is the correction; the manifests themselves stay as they are.

---

## 1. Why `6577f4b` cannot have produced any of these results

`git archive 6577f4b src | tar -x` into a scratch tree and run the same physics:

| Property | `6577f4b` (claimed) | adopted tree `c115757` (actual) |
|---|---|---|
| `src` modules | 34 | 40 |
| tests collected | 42, in 4 files | 246, in 13 files |
| `SGConfig(equilibrate=...)` | **raises `TypeError` — option absent** | present |
| built-in potential rel. error | `2.7558e-07` | `7.243e-14` |
| mass action `max|np-1|` | `6.1019e-03` | `2.934e-09` |
| BUG-11 / BUG-13 fixes | absent (0 grep hits) | present |

The decisive one is `equilibrate`. Every result in `outputs/` was produced by a
solver whose continuity solve is two-sided-equilibrated. `6577f4b` has no such
option and no code path for it. The claimed commit is not a slightly older version
of the producing code; it is a different program.

`6577f4b`'s 42-test suite is *precisely* the "42-test suite" that `README.md:106`
describes as the **pre-audit** state.

## 2. Per-manifest record

| # | manifest | claimed commit | dirty | do the numbers reproduce? |
|---|---|---|---|---|
| 1 | `outputs/experiment_design/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 2 | `outputs/gradient_fidelity/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 3 | `outputs/identifiability/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 4 | `outputs/identifiability_robustness/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 5 | `outputs/pinn_vs_surrogate/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 6 | `outputs/results/manifest.json` | `6577f4b87a` | `True` | **Yes -- 174/174 numeric leaves bit-identical.** Re-run 2026-08-25 into `outputs/results_g0/`. |
| 7 | `outputs/results_g0/manifest.json` | `6577f4b87a` | `True` | **Yes -- this *is* the re-run.** Same tree, produced before adoption. |
| 8 | `outputs/smoke/manifest.json` | `**absent**` | `None` | No `git` block at all: `commit: null`, `dirty: null`. Provenance absent, not merely wrong. |
| 9 | `outputs/surrogate_ensemble/manifest.json` | `**absent**` | `None` | No `git` block. Records artefact paths under `/home/claude/bayespinn-inv/`, a **different machine** from every other manifest (`C:` + `Users` + `abhis`). Mixed-machine provenance (`SW-18a`). |
| 10 | `outputs/uq_benchmark/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
| 11 | `outputs/uq_tuning/manifest.json` | `6577f4b87a` | `True` | Not re-verified in generation 0. The experiment was not re-run, so whether its numbers reproduce under the adoption commit is **unknown** -- recorded as unknown, not assumed. |
Rows 1–5, 10 and 11 are marked unknown deliberately. Their experiments were not
re-run in generation 0, and `AH-07` forbids substituting an assumption for a
measurement. They are candidates for re-verification in a later generation; until
then "unknown" is the honest entry.

Rows 8 and 9 are worse than wrong: they carry no `git` block at all, so there is
nothing to correct. Row 9's artefact paths show it was produced on a **different
machine** from every other manifest in the repository.

## 3. What the adoption commit fixes, and what it cannot

**Fixed.** From `c115757` forward, one commit contains the solver, its 246 tests,
its experiment launchers, its CI workflow and its documentation. `outputs/` is now
tracked — all 42 files, including every `manifest.json` — so a clone ships the
evidence with the claims (`PROV-01`).

**Fixed.** `git_is_dirty()` counts untracked files, and `RunManifest` records
`tracked_modified`, `untracked` and a `tree_digest` as separate fields, so no
future manifest can report a tree missing six source modules as clean
(`PROV-02`, `ADR-0006`).

**Not fixed, and never will be.** `PROV-03`: the adopted tree has no attestable
origin. Nothing in git records who wrote this code, when, in what order, or against
what evidence. The adoption commit makes the tree attestable *from here forward*;
it cannot make its past attestable. **No candidate in any generation may mark
`PROV-03` closed.**

## 4. Preservation, and what was deliberately not adopted

Before any git operation the tree was copied — untracked files included — to two
paths outside the repository, and both copies were verified file-by-file:

```
files preserved   : 212
total bytes       : 4,117,152
digest-of-digests : 9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd
copy A            : <scratch>/g0/preserve_A          verified 212/212
copy B            : D:/bayespinn-inv/_preserve_g0_B  verified 212/212
```

Of those 212, **164 were adopted** and attested byte-identical against
`git archive c115757` (164/164, 0 mismatched, 0 missing). The commit also carries
`PRESERVE_MANIFEST_g0.sha256` and `PRESERVE_MANIFEST_g0.meta.json`, created after
the snapshot and therefore outside it — 166 files in the commit.

The remaining **48 files were deliberately not adopted**: regenerable build output
(`build/` 41, `src/bayespinn_inv.egg-info/` 6, `dist/` 1; 464,111 bytes total),
excluded by `.gitignore` by design and reproducible with `make build`. They are
enumerated here with their digests so the exclusion is accounted for rather than
silent, and both preserved copies retain them.

| sha256 (first 16) | path |
|---|---|
| `8ecff2b7e525b463` | `build/lib/bayespinn_inv/__init__.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/active_learning/__init__.py` |
| `5ae93ec42636e36e` | `build/lib/bayespinn_inv/active_learning/design.py` |
| `0a8f0964706530b8` | `build/lib/bayespinn_inv/active_learning/loop.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/bayesian/__init__.py` |
| `eeded447b3440c76` | `build/lib/bayespinn_inv/bayesian/ensembles.py` |
| `b056cd33d3b98041` | `build/lib/bayespinn_inv/bayesian/mc_dropout.py` |
| `bb93149ee653edbc` | `build/lib/bayespinn_inv/bayesian/surrogate_uq.py` |
| `a457a7ec33c99e83` | `build/lib/bayespinn_inv/bayesian/swag.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/benchmarks/__init__.py` |
| `747cf7ec332d1321` | `build/lib/bayespinn_inv/benchmarks/sg_vs_pinn.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/calibration/__init__.py` |
| `7e758f6f3234ae69` | `build/lib/bayespinn_inv/calibration/metrics.py` |
| `7823be5f3bbc74e0` | `build/lib/bayespinn_inv/cli.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/data/__init__.py` |
| `ba70591557b25310` | `build/lib/bayespinn_inv/data/datasets.py` |
| `82bce5e0045325b3` | `build/lib/bayespinn_inv/data/splits.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/inverse/__init__.py` |
| `a029afa3508cb115` | `build/lib/bayespinn_inv/inverse/identifiability.py` |
| `34bd7f61c7c80266` | `build/lib/bayespinn_inv/inverse/inverse_design.py` |
| `0a17e9379ab70942` | `build/lib/bayespinn_inv/physics/__init__.py` |
| `55fbf838a9ccf4cc` | `build/lib/bayespinn_inv/physics/constants.py` |
| `0f185368c1235195` | `build/lib/bayespinn_inv/physics/scaling.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/pinn/__init__.py` |
| `a6f87eafeebb5c2b` | `build/lib/bayespinn_inv/pinn/forward_pinn.py` |
| `fb8cefd875a9d4d4` | `build/lib/bayespinn_inv/pinn/losses.py` |
| `406f601b0b50875a` | `build/lib/bayespinn_inv/pinn/network.py` |
| `e3b0c44298fc1c14` | `build/lib/bayespinn_inv/py.typed` |
| `152a143ba08ddaf2` | `build/lib/bayespinn_inv/solvers/__init__.py` |
| `50a2a975475328e8` | `build/lib/bayespinn_inv/solvers/grid_2d.py` |
| `e05213652e73d9d3` | `build/lib/bayespinn_inv/solvers/mos_cap_2d.py` |
| `8d44da7904ab6c7a` | `build/lib/bayespinn_inv/solvers/scharfetter_gummel.py` |
| `647ed9c073612983` | `build/lib/bayespinn_inv/surrogate/__init__.py` |
| `2f1add3a0edee4d9` | `build/lib/bayespinn_inv/surrogate/adapters.py` |
| `f86c42fb35a08b96` | `build/lib/bayespinn_inv/surrogate/iv_surrogate.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/training/__init__.py` |
| `2dbd5f530c63af00` | `build/lib/bayespinn_inv/training/trainer.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/utils/__init__.py` |
| `af3ee213f2686329` | `build/lib/bayespinn_inv/utils/provenance.py` |
| `20cf28060f4ee487` | `build/lib/bayespinn_inv/visualization/__init__.py` |
| `6736f495cf766b4d` | `build/lib/bayespinn_inv/visualization/plots.py` |
| `43ecd66bde58e2f9` | `dist/bayespinn_inv-0.1.0.dev0-py3-none-any.whl` |
| `8214fa8c85b0b9b3` | `src/bayespinn_inv.egg-info/PKG-INFO` |
| `9bfff8f76ef2ddfd` | `src/bayespinn_inv.egg-info/SOURCES.txt` |
| `01ba4719c80b6fe9` | `src/bayespinn_inv.egg-info/dependency_links.txt` |
| `e2947ff6b6ffa99a` | `src/bayespinn_inv.egg-info/entry_points.txt` |
| `fd7f7d0b4ef598b4` | `src/bayespinn_inv.egg-info/requires.txt` |
| `e7b01aecb38ce6a7` | `src/bayespinn_inv.egg-info/top_level.txt` |