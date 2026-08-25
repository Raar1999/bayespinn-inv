# WINDOWS_RISK_g6 — portability sweep for the one CI leg that has never run

**Ordered by** operator ruling of generation 6, §3.2a · **Date** 2026-08-25
**Premise, stated by the ruling:** BUG-14 was a Windows-only encoding defect
invisible to a Linux matrix. **Assume there is a second one.**

Ranked by likelihood of a **silent wrong answer**, not of a crash. A crash on the
Windows leg is loud, cheap and gets fixed. A wrong number that only appears on
Windows is the failure this repository has already had once.

The audit machine is Windows 11 / Python 3.11.9, so "Windows" here is the platform
everything in generations 0–6 was actually measured on. The untested leg is
**Linux**, which the CI matrix covers three times over and which has never run
either. Both directions are treated below.

---

## Rank 1 — text I/O using the platform encoding · **FOUND, FIXED, GUARDED**

**Severity** MEDIUM · **Silent-wrong-answer risk** HIGH

BUG-14 was fixed file by file. Nothing prevented the next one, and the sweep found
it:

```
tests/test_robustness.py:278    d = json.loads(p.read_text())
```

`RunManifest.write()` writes UTF-8 explicitly. This read used the platform
encoding — cp1252 on the Windows leg. The manifest's `environment` block carries
`platform.processor()` and, since generation 6, `git_autocrlf`; any non-ASCII in
those either raises `UnicodeDecodeError` (loud) or **mis-decodes and compares the
mangled result** (silent). The test would then assert on text that is not what was
written.

Fixed, and the file-by-file part removed:
`tests/test_line_endings_g6.py::TestNoTextIoUsesThePlatformEncoding` walks the AST
of every file under `src/`, `scripts/` and `tests/` and fails on any
`open`/`read_text`/`write_text` in text mode without `encoding=`. Binary mode is
exempt. A control asserts the walk finds >20 such calls, so it cannot pass by
scanning nothing.

**Residual risk: none known.** Offenders after the fix: 0.

## Rank 2 — line-ending conversion altering file content · **FOUND, FIXED, GUARDED**

**Severity** HIGH · **Silent-wrong-answer risk** HIGH

`core.autocrlf=true` was set at system level on the adopting machine with no
`.gitattributes`. The index holds **119 CRLF, 74 LF, 2 mixed** files. Staging under
that configuration rewrites 119 files, which would have silently invalidated the
`c115757` attestation and `PRESERVE_MANIFEST_g0.sha256` — a digest comparison that
fails for reasons having nothing to do with the project.

This is the highest silent-wrong-answer risk in the repository because it corrupts
the *evidence* rather than the code, and the corruption is invisible in a diff
viewer.

Fixed in §3.4: `.gitattributes` pins `* -text`, and
`tests/test_line_endings_g6.py` fails if index and working-tree line endings ever
disagree.

**It caught its author within the hour.** Three of this generation's own source
edits were made with a Python helper that reads with universal newlines and writes
with `newline=""` — which silently converts CRLF to LF. `identifiability.py`,
`scharfetter_gummel.py` and `test_robustness.py` were all normalised without any
visible sign. The guard flagged all three; they were restored to CRLF with content
preserved. **A repository-wide convention that only a hand check enforces will not
survive contact with tooling.**

## Rank 3 — the CI's own notebook step destroys committed evidence · **FOUND, OPEN**

**Severity** MEDIUM · **Silent-wrong-answer risk** MEDIUM · **New finding: `NB-02`**

`scripts/build_notebooks.py` regenerates all twelve notebooks **without executed
outputs**. `tests/test_notebooks.py::TestNotebooksHaveExecutedOutputs` asserts they
*have* outputs — that assertion is the evidence for claim `U1` ("all twelve
regenerated and re-executed").

The CI job runs them in this order:

```
4. Lint
5. Test                                   <- asserts outputs exist
6. Notebook generator must run            <- removes them
```

**CI is green only because step 5 precedes step 6.** Nothing states that
dependency; reordering the steps turns the matrix red for a reason no one will
connect to the reorder.

Worse locally: running `make notebooks` silently deletes the executed outputs of
all twelve notebooks. It was reproduced during this sweep — running the CI step
verbatim modified all 12 files, and they had to be restored from `HEAD` via
`git archive` and digest-verified 12/12.

Not fixed in generation 6: it is a separate concern from the portability sweep
(`SW-08`), and the fix has options worth competing — regenerate-with-outputs, a
`--check` mode that compares without writing, or reordering the CI steps and
documenting why. Left as `NB-02` for a later generation.

## Rank 4 — POSIX-only commands in the Makefile · **PRESENT, CRASH CLASS**

**Severity** LOW · **Silent-wrong-answer risk** NONE — these fail loudly

`Makefile` uses `rm -rf` (×4) and `find . -exec` (×2) in `clean` and
`check-install`. On Windows without a POSIX shell these fail immediately. `make`
was not installed on the audit machine at all, so every target was executed
directly by its documented command line throughout generations 0–6.

The `bin/` vs `Scripts/` split *is* already handled — `VENV_BIN` is computed from
`sys.platform`, which is the previous cycle's fix for this exact class.

Deliberately not fixed: it is a crash, not a wrong answer, and the ruling ranks by
silent wrongness. Recorded so the ranking is a decision rather than an oversight.

## Rank 5 — `/tmp` and `bin/` in the CI clean-install job · **PRESENT, SCOPED SAFE**

**Severity** LOW · **Silent-wrong-answer risk** NONE

`ci.yml` uses `/tmp` (×7) and `bin/` (×5). All of them are inside the
`clean-install` job, which is pinned `runs-on: ubuntu-latest`. Correct as written.
Flagged only because a future matrix expansion of that job to Windows would break
it silently at the *path* level — `/tmp/clean/bin/pip` resolves to nothing on
Windows, and a mistyped path in a shell script is a classic source of "the step
passed but did nothing".

## Checked and clean

| check | method | result |
|---|---|---|
| Case-only filename collisions (work on Windows, break on Linux) | `git ls-files`, lowercase collision map | **0** |
| Hardcoded path separators in `src/` string literals | AST walk over string constants | **0** (one LaTeX label `$\phi$` matched the regex and is not a path) |
| `bernoulli` reachable from a float32 path | AST walk of the function body and module imports | **0** — one NumPy definition, no torch import in the module |
| `ci.yml` is valid YAML | `yaml.safe_load` | valid; 2 jobs, 4+3 `run` steps |

One YAML curiosity worth knowing rather than fixing: `yaml.safe_load` parses the
workflow's `on:` key as the boolean `True` (YAML 1.1 treats `on`/`off`/`yes`/`no`
as booleans). GitHub Actions uses its own parser and is unaffected. Any *local*
tooling that reads the workflow with PyYAML must look up `True`, not `"on"`.

---

## What was actually executed, and what was not

`ci.yml`'s `run` steps, executed locally on Python 3.11.9 / Windows:

| step | command | exit |
|---|---|---|
| Lint | `python -m ruff check src tests scripts` | **0** |
| Test | `python -m pytest tests -q --tb=short` | **0** (419 passed, after the badge update) |
| Notebook generator (BUG-14 guard) | `python scripts/build_notebooks.py` | **0** — and it destroyed the notebook outputs, see Rank 3 |

**Not executed, and why:**

- The `Install` steps (`pip install torch --index-url …`, `pip install -e .[dev,sklearn]`)
  require network access, which `SK-09` prohibits.
- The 3.9 and 3.12 legs: neither interpreter exists on this machine. Only 3.11.9
  and 3.14 are installed, and 3.14 is outside the declared support range
  (`requires-python >=3.9`, classifiers to 3.12), so running it would produce a
  result about a configuration nobody claims.
- The `clean-install` job as written: `python -m build` needs `setuptools>=68.0` in
  an isolated environment and this machine has 65.5.0. The offline equivalent was
  run in generation 0 and again at the g0 champion — fresh wheel, installed into a
  venv, `bayespinn selftest` PASS, suite green against the installed package —
  with dependency *resolution* explicitly not verified.

**Therefore `SPEC-g0-3a` passes for the 3.11 leg only.** The 3.9 and 3.12 legs are
unevaluated, not passing. That distinction is the whole point of `CI-01` having
been a false closure once already, and it is not repeated here.

`SPEC-g0-3b` — the retrievable remote run log — remains `OPERATOR-BLOCKED`. The
exact commands are in `docs/OPERATOR_TASKS.md`.
