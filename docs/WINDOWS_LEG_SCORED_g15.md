# WINDOWS_LEG_SCORED_g15 — the portability sweep meets a run, on the host it was written on

**Ordered by** operator close-out ruling of 2026-08-29 §3 · **Subject**
`docs/WINDOWS_RISK_g6.md`, its five ranked predictions
**Not a generation.** No `LOOP_STATE` increment, no ladder movement, no spec.
**Evidence** `outputs/ci_local_g15/` (this commit), `outputs/nb02_ordering_g15/`
(the ordering experiment), `outputs/ci_local_g7/` (generation 7, retained)
**`SPEC-g0-3b` does not close here, and neither does `CI-01`.** §6 says why.

---

## 1. The correction that made this document possible

The close-out ruling records an operator error and it is the reason nothing had
been scored for eight generations:

> *I wrote that the Windows leg was "not obtainable on this host by any means"
> and carried it for eight generations. **The host is Windows.***

That is right, and the sharper version is that **`WINDOWS_RISK_g6.md` never made
the error.** Its own preamble, written 2026-08-25, says so in as many words:

> *The audit machine is Windows 11 / Python 3.11.9, so "Windows" here is the
> platform everything in generations 0–6 was actually measured on. The untested
> leg is **Linux**, which the CI matrix covers three times over and which has
> never run either.*

The source document had it correct on its date. What went stale was **a belief
about where the evidence lived** — that scoring these predictions required a
GitHub runner. `docs/OPERATOR_TASKS.md`'s `OT-1` entry, written yesterday and
committed at `157a785`, carries that belief in its own scoring table: five rows,
every one `no`, each reason given as *no test ran / no checkout happened / the
job did not start*. Every one of those reasons is about a **remote** machine, and
four of the five predictions never needed one.

This is `AGE-01` in a form the rule's own record does not name. `AGE-01` is
written about artefacts encoding *the rule set* of their date. This is an
artefact encoding **the instrument set** of its date — a claim about what could
be measured, made stale not by a rule change but by noticing that the measuring
device was already on the desk. The two halves of `OT-1`'s table are asymmetric
and only now visibly so: its *billing* findings are sound and remain the record,
its *scoring* findings were answering the wrong question.

`OT-1` is append-only and is not edited. This document supersedes its
`WINDOWS_RISK_g6.md` section forward.

---

## 2. What `outputs/ci_local_g7/` is, and what it is worth

**It was produced on this Windows host.** `docs/audit/AUDIT_g7.md` §27 records
it as the evidence for `SPEC-g0-3a`, and `docs/gen/DECISIONS.md` §240 describes
it as the 3.11 leg's local execution: ruff exit 0, suite exit 0, notebook
generator exit 0. It is the `run` steps of `.github/workflows/ci.yml` executed
by hand on Windows 11 / CPython 3.11.9.

**It is real Windows evidence and it is stale.** Its suite log reads
`509 passed`; the suite at this commit collects well over twice that. Eight
generations of guards were written after it. It evidences a tree that no longer
exists, which is exactly the condition `AGE-01` was enacted for.

So it is not used as the scoring instrument. **The same three steps were re-run
at this commit**, and `outputs/ci_local_g15/` is the result:

| step | command | exit | log |
|---|---|---|---|
| Lint | `python -m ruff check src tests scripts` | **0** | `lint_py311.log` |
| Test | `python -m pytest tests -q --tb=short` | **0** | `test_py311.log` |
| Notebook generator | `python scripts/build_notebooks.py` | **0** | `notebooks_py311.log` |

Environment, recorded rather than assumed (`environment.txt`): commit
`157a785`, CPython 3.11.9 MSC v.1938 64-bit, `Windows-10-10.0.26200-SP0`,
`sys.platform == win32`, **preferred encoding `cp1252`**, `core.autocrlf` **`true`
at system level** and `false` at repository level.

Those last two are not decoration. They are the live hazard conditions for
predictions 1 and 2, and their being present on this host is what makes passing
those guards here mean something.

**`outputs/ci_local_g7/` is retained unmodified.** It is the generation-7 record
and it stays that.

---

## 3. The five predictions, scored

| rank | prediction | verdict | what scored it |
|---|---|---|---|
| 1 | Text I/O using the platform encoding · *FOUND, FIXED, GUARDED* | **CONFIRMED — the fix holds under the live hazard** | §3.1 |
| 2 | Line-ending conversion altering file content · *FOUND, FIXED, GUARDED* | **CONFIRMED — and the hazard is still switched on** | §3.2 |
| 3 | **`NB-02`** — the notebook step destroys committed evidence, and CI is green only because the test step precedes it | **CONFIRMED, exactly and in full** | §3.3 |
| 4 | POSIX-only commands in the Makefile · *CRASH CLASS* | **CONFIRMED, including the half that mattered** | §3.4 |
| 5 | `/tmp` and `bin/` in the clean-install job · *SCOPED SAFE* | **NOT SCOREABLE, and correctly so** | §3.5 |

**Four of five scored. None refuted.** The document was right where it could be
checked. That is a result about `WINDOWS_RISK_g6.md`, and it is the first one it
has ever had.

### 3.1 Rank 1 — platform-encoding text I/O

The hazard condition is present: `locale.getpreferredencoding(False)` returns
**`cp1252`** on this host, so any text read without an explicit `encoding=` is
decoding as cp1252 right now.

`tests/test_line_endings_g6.py::TestNoTextIoUsesThePlatformEncoding` passes,
**and its non-vacuity control passes with it** —
`test_the_scan_is_not_vacuous` asserts the AST walk finds a real population of
such calls rather than passing by scanning nothing.

One honest limit, stated because it changes what the confirmation is worth: the
guard is an **AST scan**, and an AST scan returns the same answer on any
platform. What Windows execution adds is the runtime half — the full suite
executes here, under cp1252, without a single `UnicodeDecodeError`. The
prediction's claim was *offenders after the fix: 0*, and both the static and the
runtime reading agree with it on the platform the defect was native to.

### 3.2 Rank 2 — line-ending conversion

This is the strongest of the four, because the hazard is not hypothetical on
this host **today**: `git config --system --get core.autocrlf` returns **`true`**.
The exact configuration that would have rewritten 119 tracked files and
invalidated `PRESERVE_MANIFEST_g0.sha256` is still set at system level, and what
stands between it and the attestation is the repository-local `false` plus
`.gitattributes`' `* -text`.

All five relevant assertions pass, controls included:

* `test_unmodified_files_match_their_blob_byte_for_byte`
* `test_gitattributes_disables_conversion`
* `test_no_tracked_file_would_be_normalised`
* `test_there_are_tracked_files_to_check` *(control)*
* `test_the_repository_really_does_contain_crlf_files` *(control)*

The second control is the one that matters: it asserts the tree still contains
CRLF files, so the guard cannot pass by having nothing left to convert.

### 3.3 Rank 3 — `NB-02`, and it needed no runner at all

The prediction, in the g6 document's own words:

> *The CI job runs them in this order: 4. Lint · 5. Test ← asserts outputs exist
> · 6. Notebook generator must run ← removes them. **CI is green only because
> step 5 precedes step 6.** Nothing states that dependency; reordering the steps
> turns the matrix red for a reason no one will connect to the reorder.*

That is a claim about **step order**, and step order is not a property of the
runner. The experiment is to run step 6 before step 5, on any machine. It was
run here, at this commit, and it is recorded frame by frame in
`outputs/nb02_ordering_g15/`:

| # | action | result |
|---|---|---|
| 0 | sha256 of all twelve notebooks | `digests_before.txt` |
| 1 | **CI order** — `pytest tests/test_notebooks.py` | **green**, `step1_test_before_notebooks.log` |
| 2 | step 6 — `python scripts/build_notebooks.py` | exit 0, all twelve rewritten, `step2_notebook_generator.log` |
| 3 | **reversed order** — the same test command, unchanged | **RED**, `step3_test_after_notebooks.log` |
| 4 | `git checkout -- notebooks/`, re-digest | `digests_after_restore.txt`, **identical 12/12** |
| 5 | the same test command again | green |

The failure, verbatim:

> `TestNotebooksHaveExecutedOutputs::test_every_notebook_has_at_least_one_output`
> — *these notebooks ship with no executed outputs: 01_setup.ipynb,
> 02_physics_validation.ipynb, 03_sg_solver.ipynb, 04_forward_surrogate.ipynb,
> 05_inverse_design.ipynb, 06_mc_dropout.ipynb, 07_deep_ensemble.ipynb,
> 08_active_learning.ipynb, 09_calibration.ipynb, 10_benchmarking.ipynb,
> 11_visualization.ipynb, 12_demo.ipynb*

**All twelve. One test. Nothing changed but the order of two steps**, four
seconds apart, and the assertion that carries claim `U1` went from green to red.

The prediction is confirmed in every clause: the dependency is real, it is
undeclared, and the red it produces names notebooks rather than ordering — a
reader of that failure has no reason to suspect step order. `NB-02` is no longer
static analysis. It is a reproduced defect with a log.

**Restoration was verified, not assumed.** Step 4's digest file is byte-compared
against step 0's and the twelve hashes are identical, which is the same
discipline the g6 sweep used when it hit this by accident.

**The fix is still open and this document does not pick one.** The three options
`WINDOWS_RISK_g6.md` named remain the options — regenerate-with-outputs, a
`--check` mode that compares without writing, or reorder the CI steps and
document the dependency. The evidence added here bears on the choice: the
`--check` mode is the only one of the three that also fixes the *local* hazard,
where `make notebooks` silently destroys the executed outputs of all twelve
notebooks with no CI step ordering to protect anyone. That is a recommendation
and not a decision, and the decision is not this document's to make.

### 3.4 Rank 4 — the Makefile's POSIX commands

`make` is **still not installed on this host**, so `make clean` cannot be run.
The prediction's content is nevertheless testable, because it is a claim about
what the recipe lines do when a Windows shell runs them, and the `Makefile`
declares no `SHELL`, so `cmd.exe` is what would run them.

Both were run against a scratch directory containing one `.pyc` file:

| recipe line | result under `cmd.exe` | exit |
|---|---|---|
| `rm -rf sub` | `'rm' is not recognized as an internal or external command` | **1** |
| `find . -name "*.pyc" -delete` | `Access denied - .` / `File not found - -NAME` / `File not found - -DELETE` | **1** |

**The `.pyc` file and its directory both survived.** Nothing was deleted by
either line.

The prediction's classification is confirmed on both halves — it crashes, and
its silent-wrong-answer risk is genuinely **NONE**. The second line is the
interesting one and sharpens the original finding: `find` is **not** an
unrecognised command on Windows. `C:\Windows\System32\find.exe` exists, shadows
the POSIX tool, and takes entirely different arguments — so what runs is a
*different program*, which then fails on the arguments. It still fails loudly and
still deletes nothing, so the g6 ranking stands; but the failure mode is
argument rejection by the wrong binary, not command-not-found, and that is a
distinction worth having written down before someone reads the error.

**One consequence for the ruling's own suggestion.** §3 of the ruling proposes
`make check-install` as the instrument for real Windows evidence. It is not
available, and prediction 4 is the reason: `check-install`'s first recipe line
after `build` is `rm -rf .cleanenv`. Even with `make` installed, that target dies
on Windows at its first line, in exactly the class rank 4 describes. The
prediction blocks the instrument proposed for scoring it — which is itself a
small confirmation.

The clean-install *equivalent* was not run either, and the reason is unchanged
from generation 6 and not a portability one: it needs `pip install` from the
network, and `SK-09` prohibits network access. The close-out order lifted that
prohibition for one named `git push` / `gh` sequence only.

### 3.5 Rank 5 — `/tmp` and `bin/` in the clean-install job

**Not scoreable, and the reason is structural rather than a shortage of
machines.** The prediction is a conditional whose antecedent is false: *if* the
`clean-install` job were expanded to Windows, its POSIX paths would break
silently. No run can score a conditional whose antecedent nobody has made true.

What is checkable is the premise, and it was re-checked at this commit rather
than carried forward: `.github/workflows/ci.yml` line 54 pins
`clean-install` to `runs-on: ubuntu-latest`, and **all six** `/tmp` and `bin/`
occurrences are at lines 66–72, inside that job. The `test` job takes its runner
from the matrix and contains none of them. **`SCOPED SAFE` holds as written.**

---

## 4. `WINDOWS_RISK_g6.md`'s standing, restated

It was static analysis standing in for a run. It is now **static analysis with
four of its five predictions confirmed against execution on the platform it was
written about, and none refuted.**

That is a real change in what the document is, and it is a small one in what the
project knows. Confirming that a *found and fixed* defect stays fixed is worth
less than finding one. The two confirmations that carry weight are `NB-02` —
which moves from a predicted ordering dependency to a reproduced one with a log
— and rank 4's second half, which was never checked at all before today.

**The document's central framing is untouched and remains correct: the untested
leg is Linux.** Nothing here says anything about ubuntu, and the 3.12 leg has
still never executed anywhere.

---

## 5. Defects revealed by this exercise

**One, and it is in a record rather than in the code.** `OT-1`'s scoring table
gives *"no test ran"* as the reason five predictions were unscored, which is true
of the GitHub run and irrelevant to four of them. The defect is the reasoning
step that treated a remote runner as the only instrument, and §1 records it.

**No defect in `src/`.** The lint and test steps at this commit both exit 0 on
Windows. As `OT-1` says of its own null result, the absence of a finding is not
evidence of correctness — and here it is weaker still, because this is the
platform every generation was already measured on. A green suite on Windows is
the status quo, not news.

---

## 6. What this discharges, and what it does not

**Discharged.**

* `WINDOWS_RISK_g6.md` is scored: four confirmed, one correctly unscoreable,
  none refuted.
* `NB-02` is reproduced at the current commit with a restoration verified
  digest-by-digest, and its fix options are narrowed by evidence rather than by
  preference.
* The eight-generation claim that Windows evidence was unobtainable on this host
  is retired, and the reasoning error that produced it is recorded.
* `outputs/ci_local_g7/` is superseded forward by `outputs/ci_local_g15/` as the
  live local-execution evidence, and retained as the generation-7 record.

**Not discharged, and none of it is close.**

* **`SPEC-g0-3b` does not close.** It requires a *retrievable remote run log per
  matrix leg*. Local hand-execution of three `run` steps is not a clean-runner CI
  run: no fresh checkout, no dependency resolution, no isolated environment, and
  a machine whose state fifteen generations of work have shaped. This document
  does not weaken that requirement and does not want to.
* **`CI-01` does not close**, and its blocker is unchanged and unrelated to
  anything here — the Actions billing gate recorded in `OT-1`.
* **`SPEC-g0-3a`'s verdict is unchanged**: passes for the **3.11 leg only,
  locally**. The 3.12 and Windows-runner legs remain **unevaluated, not
  passing**.
* **The Linux legs remain entirely unevidenced.** Three of the four matrix legs
  are ubuntu and not one line of this repository has ever executed on Linux.
  That is the real portability exposure and today did nothing about it.
* **`NB-02` is not fixed.** It is reproduced.

The honest one-line summary: this converts a document of predictions into a
document of scored predictions, on the leg that was never the risk. It is worth
doing because it was free, and it is not worth mistaking for the run that is
still missing.
