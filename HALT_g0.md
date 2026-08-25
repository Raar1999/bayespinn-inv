# HALT — generation 0

**Triggered** 2026-08-25, Phase A exit, before any Phase B work.
**Rule** SK-17 — *"a manifest whose `git.commit` does not match the tree that produced it."*
**Ledger** `docs/audit/AUDIT_g0.md` (findings PROV-06, SCI-08, PROV-01/02/03).

---

## 1. Trigger

Every manifest under `outputs/` records `git.commit: 6577f4b87a65cd2c255062e42ea5181f04483e93`.
That commit cannot have produced those results.

Measured by extracting the commit into a scratch tree
(`git archive HEAD src | tar -x -C <scratch>`) and running the same physics:

| Quantity | `HEAD` = 6577f4b | working tree (produced the results) |
|---|---|---|
| `src` modules | 34 | 40 |
| tests collected | 42, in 4 files | 246, in 13 files |
| `SGConfig(equilibrate=…)` | **`TypeError` — option absent** | present |
| built-in potential rel. error | 2.7558e-07 | 7.243e-14 |
| mass action max\|np−1\| | 6.1019e-03 | 2.934e-09 |
| BUG-11 / BUG-13 fixes | absent | present |

The commit is the **pre-audit** repository. Both audit cycles' fixes, the 204 tests
that verify them, all seven experiment launchers, the five ADRs, `AUDIT_MASTER.md`,
`CLAIM_EVIDENCE_MATRIX.md`, `RELEASE_READINESS.md`, `CHANGELOG.md` and the CI workflow
are **untracked** — present on disk, absent from git.

`git.dirty: true` is recorded, but `git_is_dirty()` runs
`git status --porcelain --untracked-files=no` (`utils/provenance.py:57`), so the flag
is structurally blind to all 33 untracked paths. It cannot distinguish a typo from a
different solver.

## 2. What is *not* wrong

Stated plainly, because it bounds the blast radius:

- The headline science is **exactly reproducible**. A full re-run of
  `scripts/run_results.py` (2500 epochs, M = 5, full protocol — not a smoke run)
  reproduced **all 174 numeric leaves bit-identically**, C1–C11 and C21–C22 included.
- `outputs/results/manifest.json` agrees with its `results.json` on all 102 shared
  leaves — **0 mismatches**. Nothing is fabricated.
- 240 tests pass, from the checkout **and** against the installed wheel; `ruff` is
  clean; the physics selftest passes both ways.

The defect is provenance, not honesty: the numbers are real and repeatable, but the
tree that makes them repeatable is not in the repository.

## 3. Last-good commit and rollback

There is exactly one commit in this repository:

```
6577f4b87a65cd2c255062e42ea5181f04483e93   (main)
```

**No repair was attempted (SK-18).** Nothing under `src/`, `configs/`, `scripts/` or
any pre-existing test file was modified at any point in generation 0. `git status`
shows the same 70 modified tracked files it showed at kickoff.

This generation added exactly three paths, all new files, none overwriting anything:

```
docs/audit/AUDIT_g0.md          Phase A ledger
HALT_g0.md                      this file
tests/test_claim_surface_g0.py  SCI-08 regression (fails pre-fix: 5 failed / 1 passed)
outputs/results_g0/             re-run of run_results.py (never into outputs/results/)
```

Exact rollback — removes only this generation's additions, touches nothing else:

```bash
rm -rf outputs/results_g0
rm -f  docs/audit/AUDIT_g0.md HALT_g0.md tests/test_claim_surface_g0.py
rmdir  docs/audit 2>/dev/null || true
```

To inspect the committed (pre-audit) tree without disturbing the working tree:

```bash
git archive HEAD src tests | tar -x -C /some/scratch/dir
```

Do **not** `git checkout` or `git stash`: the working tree holds the only copy of both
audit cycles.

---

## 4. ESCALATE

```
ESCALATE E-3 @ generation 0, phase A
WHAT:      The only commit in this repository is the pre-audit project; both audit
           cycles exist solely as uncommitted working-tree state, and every result
           manifest names that commit as its provenance.
EVIDENCE:  docs/audit/AUDIT_g0.md PROV-06, SCI-08, PROV-01/02/03.
           git archive HEAD src | tar -x  ->  SGConfig has no `equilibrate`
             (TypeError); V_bi rel err 2.7558e-07 vs 7.243e-14; mass action
             6.1019e-03 vs 2.934e-09; 42 tests vs 246.
           git ls-files outputs/  ->  only results.json, results_summary.md tracked;
             outputs/results/manifest.json is gitignored, so a fresh clone ships the
             headline results with no provenance record at all.
           204 of 246 collected tests (83%) are in untracked files.
OPTIONS:   1) Commit the working tree on a new branch, re-run every experiment against
              that commit, and regenerate the manifests. Restores provenance for
              everything. Cost: one full results regeneration (~17 min measured for
              run_results.py; the other six launchers are unmeasured this session).
           2) Commit the working tree but keep the existing manifests. Cheap, and
              wrong: the manifests would still name a commit that did not produce them.
           3) Do nothing. Consequence: the repository as cloned is the pre-audit
              project with a 42-test suite and live BUG-11/BUG-13, while its README
              advertises 240 tests and an audited solver. Every claim in
              AUDIT_MASTER, CLAIM_EVIDENCE_MATRIX and RELEASE_READINESS is
              unverifiable by anyone who clones it, and one power failure loses both
              audit cycles.
BLOCKED:   Phase B (spec), Phase C (candidates) and every gate that depends on a
           commit: G-REPRO in full, G-CODE's CI clause (CI-02 — .github/workflows/ci.yml
           is untracked, so CI has never run), and SW-15 (no ledger may be marked
           complete while git.dirty backs the headline numbers).
           Also blocked pending the operator's answer: which tree is authoritative.
           tests/test_claim_surface_g0.py currently encodes "the working tree is
           correct, update the documents". If HEAD is instead authoritative, that
           contract is inverted and the test must be rewritten.
```

## 5. Recommended first candidate for generation 1

Not executed — recorded so the next generation does not have to re-derive it.

Under option 1, the first candidate is **not** a code change. It is: create
`loop/champion` from the working tree, commit it, then re-run the seven experiment
launchers with `--out outputs/<experiment>_g1/` and diff every manifest against the
`_g0` re-run already on disk. `outputs/results_g0/` is a measured, bit-identical
baseline to diff the first post-commit run against — that comparison is the cheapest
available proof that committing changed nothing scientific.

`SCI-08` cannot be closed before that: until one tree is authoritative, there is no
fact of the matter about which number the documents should quote.
