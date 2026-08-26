# OPERATOR_TASKS — actions reserved to the operator

Append-only. Each entry is an action the loop is forbidden to take, with the exact
command and the finding it closes. The loop does not perform these and does not
mark the corresponding finding closed.

---

## OT-1 — push `loop/champion` so CI executes · closes `SPEC-g0-3b` / `CI-01`

**Status** `OPERATOR-BLOCKED` · **Blocks** `CI-01` — **reclassified
`ACCEPTED-PERMANENT` at generation 9 by default trigger**, see below
**Why the loop cannot do it** `R-4` prohibits `git push`; `SK-09` prohibits network
access.

> **Resolution, generation 9, ruling of 2026-08-26 §4 — the default fired.** The
> generation-8 ruling put a decision ahead of this command: remote, or no
> remote. It went unanswered for three cycles, outliving its own deadline, so
> the stated default applies rather than the wait continuing.
>
> **`CI-01` is `ACCEPTED-PERMANENT`.** The task below is *not* withdrawn — it
> remains the action that would close `SPEC-g0-3b` — but the finding is no
> longer carried as a thing about to be fixed, because a status that says
> "blocked" for nine generations is a status that has stopped describing
> anything. The cost statement the status owes is in `docs/G9_RESULT.md` §1 and
> is reviewed each generation for growth.
>
> **If a remote is added later the status reverts** and the cost statement is
> superseded forward, not deleted. That is the same discipline `R-4` applies to
> commit messages: a withdrawn statement leaves its trace.

> **Correction, generation 8, per the ruling of 2026-08-26 §10.** *This task
> requires adding a remote first.* `git remote -v` is empty on this host, so the
> command block below — written as though `origin` existed — describes something
> that cannot run. Generation 7 recorded that as the reason `CI-01` could not be
> actioned; the file itself still said otherwise, which is the same class of
> defect as a rule that lives only in a ruling. The block now begins with the
> `git remote add` that has to precede it.
>
> The ruling also puts a **decision** ahead of the command: if a remote will
> exist, `CI-01` stays `OPERATOR-BLOCKED`; if it will not, `CI-01` becomes
> `ACCEPTED-PERMANENT` and owes a cost statement. The mislabel is what corrupts
> the status system, not the missing CI. That decision is the operator's and is
> unanswered as of the generation-8 champion.

`.github/workflows/ci.yml` has existed since before generation 0 and has **never
executed** — it was untracked until commit `c115757`, so it was never pushed and
never ran, while `AUDIT_MASTER` recorded `CI-01` as VERIFIED against it. That false
closure is the reason this file exists.

Generation 6 executed everything that can be executed locally (`SPEC-g0-3a`, see
`docs/WINDOWS_RISK_g6.md`): the workflow is valid YAML, and its `Lint`, `Test` and
notebook-generator steps all exit 0 on Python 3.11.9 / Windows. What cannot be
produced locally is a **retrievable run log per matrix leg**, which is what
`SPEC-g0-3b` requires.

```bash
cd /d/bayespinn-inv/bayespinn-inv
git switch loop/champion            # confirm you are on the champion branch
git log --oneline -1                # expect the current champion

# THIS FIRST. There is no remote on this host; `git remote -v` prints nothing,
# so every command below fails until one exists.
git remote add origin <url>

# Push. The workflow triggers on push to main and on pull_request, so a branch
# push alone will NOT start it -- use workflow_dispatch, or open a PR:
git push -u origin loop/champion

# then either
gh workflow run ci.yml --ref loop/champion
gh run watch

# or open a pull request, which the `pull_request` trigger does fire on
gh pr create --base main --head loop/champion \
  --title "Audit loop generations 0-6" --body-file docs/gen/FINAL_REPORT_v1.md
```

**Note before pushing:** the workflow's triggers are `push: branches: [main]`,
`pull_request`, and `workflow_dispatch`. Pushing `loop/champion` on its own fires
none of them. Use `workflow_dispatch` or a PR.

**What to check in the logs, and what closes the finding.** `CI-01` closes only
with a retrievable log for **every** leg:

| leg | what it proves |
|---|---|
| ubuntu × 3.9 | the `requires-python >=3.9` floor is real. **Never executed anywhere** — this repository has only ever run on 3.11. |
| ubuntu × 3.11 | the baseline |
| ubuntu × 3.12 | the top of the declared classifier range, also never executed |
| **windows × 3.11** | the BUG-14 leg. See `docs/WINDOWS_RISK_g6.md` for what to look for. |
| clean-install | the wheel path, with dependency resolution — the one thing the offline substitute could not verify |

Expect the suite to pass on each leg. The count is **not** written here: it moves
every generation, a number in a document nobody re-measures is a claim on an
unguardable surface, and `DOC-07` exists because of exactly that. The count for a
given tree is in `README.md`'s badge, which
`tests/test_notebooks.py::TestDocumentedTestCountIsHonest` checks against what
pytest actually collects. A leg that disagrees with the badge is a finding, not a
rounding difference.

**Watch specifically for:** the 3.9 leg. `pyproject.toml` claims it and
`[tool.mypy]` carries a comment saying the 3.9 support claim "is backed by the CI
matrix (which actually runs the suite on 3.9)". The CI matrix has never run. That
sentence is currently unsupported, and the 3.9 leg is the only thing that can
support it.

---

## OT-2 — apply `papers/CORRIGENDA_g6.md` · closes the standing `R-3` escalation

**Status** `OPERATOR-BLOCKED` · **Blocks** the last instance of `SCI-11`
**Why the loop cannot do it** `R-3` makes `papers/**` reserved.

One line in `papers/draft.md` states the identifiable-rank result without its
local/global qualifier, which `PH-21` forbids. Six other instances were corrected
in generation 0; this one is protected.

The corrigendum gives the exact line, its current text, the measured replacement,
the evidence command and the manifest path. Apply it, or decline it and record the
decision — either resolves the escalation.

```bash
cat papers/CORRIGENDA_g6.md
# apply the replacement given there, then:
PYTHONPATH=src python -m pytest tests/test_claim_surface_g0.py -q
```

`tests/test_claim_surface_g0.py::TestParkedPapersInstance` pins the count of
unqualified passages at **1** and fails in **both** directions. When the
corrigendum is applied the count drops to 0 and that test fails **by design** —
that failure is the signal to move `papers/draft.md` into `CLAIM_SURFACE` and
delete the parked-instance test.
