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

> **Generation-10 review.** Done, and it is a review rather than a restatement:
> `docs/AUDIT_MASTER.md` §`CI-01`, with the scanned file count carried in
> `LOOP_STATE_v7.json` beside its generation-7 and generation-9 values so the
> direction is visible. The task is still not withdrawn and the reversion
> condition is unchanged.

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

**Status** **DISCHARGED 2026-08-29** · closed `SCI-11`, its last instance
**What released it** the close ruling of 2026-08-29 §4 assigned the paper to the
loop, which lifted `R-3` over `papers/**`. COR-1 was applied the same day, the
parked-instance guard was replaced by putting `papers/draft.md` on the claim
surface, and `papers/CORRIGENDA_g6.md` records both. Nine cycles blocked.

The original entry follows, unedited.

**Status (as recorded while open)** `OPERATOR-BLOCKED` · **Blocks** the last
instance of `SCI-11`
**Why the loop could not do it** `R-3` makes `papers/**` reserved.

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

---

## OT-1 reversion — **the remote now exists** · generation 11, 2026-08-28

**Status of `CI-01`** `ACCEPTED-PERMANENT` → **`OPERATOR-BLOCKED`**, by the
reversion condition this file already carried.

Append-only, so nothing above is edited. What follows supersedes the
generation-9 resolution forward, which is the discipline that resolution itself
named:

> *If a remote is added later the status reverts and the cost statement is
> superseded forward, not deleted.*

**A remote was added.** `git remote -v` is no longer empty:

```
origin  https://github.com/Raar1999/bayespinn-inv.git (fetch)
origin  https://github.com/Raar1999/bayespinn-inv.git (push)
```

`.git/config` carries `[remote "origin"]`, and `refs/remotes/origin/main`
resolves to `6577f4b`, this repository's root commit — so the remote was not
only configured but fetched from. The mtime on `.git/config` is 2026-08-28
09:20, four minutes after the `git filter-repo` run at 09:16 that `HIST-01`
turns out to have been about (`docs/HIST01_REPAIR_g11.md`). Both were one
operator action on the morning of 2026-08-28, and the loop noticed neither until
generation 11 went looking.

**Three consequences, and only the third is the loop's to act on.**

1. **`CI-01` reverts to `OPERATOR-BLOCKED`.** It is no longer a permanent
   acceptance. The condition that made it permanent — *there will be no remote*
   — is false, and a status that outlived its own premise is exactly the defect
   this file exists to record.
2. **The correction paragraph above is now wrong in one sentence.** *"`git
   remote -v` is empty on this host, so the command block below — written as
   though `origin` existed — describes something that cannot run."* It is not
   empty and the block can run, unedited, from `git push -u origin
   loop/champion` onward. The `git remote add origin <url>` line it begins with
   is the only line that is now redundant.
3. **The push is still reserved and still not done.** `R-4` prohibits
   `git push`; the operator directive of 2026-08-28 §6 reserves it again by
   name, along with anything needing credentials. **A remote existing is not
   CI having run.** `.github/workflows/ci.yml` has still never executed, the
   3.9 floor is still a static scan, and `PROV-07` is still validated on
   `win32` only. Nothing about this entry closes anything.

**What is now newly true is only this: the action is available.** For nine
generations `OT-1` named a command that could not be run because its
precondition did not exist. It exists. The command block above is unchanged and
is now executable as written.

**`PROV-07` is reclassified with it**, from `MITIGATED-PENDING-CI` to
`OPERATOR-BLOCKED`. *Pending* was the wrong word for nine generations and is
still the wrong word: nothing was pending, because nothing was going to happen
without a reserved action. Naming the reservation is what makes the status
describe the world.

---

## OT-3 — `EXT-05` attribution trailers · **RULED: LEAVE IT ALONE, PERMANENTLY**

**Status** **CLOSED — DECLINED ON COST, 2026-08-29** · **Delegated** to the loop
by the operator close-out order of 2026-08-29 §T2, which reserved the decision
and then made it
**What was reserved** `D:\Fable built Fabkg Final\FabKG-Application`, surveyed as
`EXT-05` in `docs/AUDIT_MASTER.md` §`PROV-08`, was held back from every earlier
sweep. `docs/G13_RESULT.md` §1 declined to survey it, and `AUDIT_MASTER` records
it twice as *unexamined and reserved to the operator*. This entry discharges the
reservation by declining the action, not by performing it.

**The action declined.** Rewriting `EXT-05`'s history with `git filter-repo` to
strip `Co-Authored-By` trailers from the 138 of its 169 commits that carry one.

**Why it is declined, and the reasoning is a cost comparison rather than a
principle.** Four facts decide it, and all four are already measured:

1. **It was never rewritten.** The survey table classes it `CLEAN of rewrite
   damage`: no `filter-repo` run, no commit-map, no force-pushed remote. There
   are no pre-rewrite objects at risk in it, because nothing has put any at
   risk. A rewrite would *create* the exposure that every other entry in that
   table is a record of somebody else having already created.
2. **It has no remote.** The `remote` column reads `none`. Nothing downstream
   holds its object identities, so nothing downstream breaks — and equally,
   nothing downstream reads it. The trailers are visible to whoever opens that
   directory on this machine and to nobody else.
3. **It has no recovery role.** It resolved none of the 150 sampled pre-rewrite
   commits of `EXT-02` — a different history that happens to share a branch
   name. `EXT-04`, which resolved 146 of the same 150, is the tree that carries
   the fabkg lineage's surviving object graph, and it is frozen under a separate
   record for exactly that reason. `EXT-05` is not a backup of anything.
4. **The cost is known, because this repository paid it.** The 2026-08-28
   `filter-repo` run at 09:16:38 produced `HIST-01`, eight failing guards, three
   more that silently skipped, and a full generation of repair
   (`docs/HIST01_REPAIR_g11.md`, `docs/G13_RESULT.md`). That is the price of a
   history rewrite in a tree that is watched. `EXT-05` is not watched, so the
   same rewrite would buy less and could only be discovered later.

**What the trade actually is.** Spend a generation of repair risk on a local
directory nobody reads, to remove lines that stop being generated anyway. The
`commit-msg` hook at `C:\Users\abhis\.git-hooks\commit-msg` was installed
2026-08-28 09:06:36 and is machine-wide via `core.hooksPath`; from that moment
forward no new trailer is written in any tree on this host, `EXT-05` included.
The rewrite would address only commits already made, in the one place where
their being addressed changes nothing.

**The standing prohibition, stated once so it does not have to be re-derived.**
`git filter-repo` is **not run again in any of these trees** — not `EXT-01`
through `EXT-09`, not this repository, not any tree reached from them. Neither
is `git gc --prune`, `git remote remove`, or any force-push. The rewrite that
has already happened is a fact to be recorded and worked around, and the
recording is done. Nothing is gained by a second one and `HIST-01` is what is
lost.

**`OT-2` was discharged separately** on 2026-08-29 by the close ruling §4, which
assigned the paper to the loop and lifted `R-3` over `papers/**`; `COR-1` was
applied the same day and `papers/CORRIGENDA_g6.md` records it. Its entry above
carries that status and is not edited here.

**This is a record, not an operation.** No command was run against `EXT-05` to
produce it. Every number in it is read from `docs/AUDIT_MASTER.md`'s survey
table, which was taken at a commit that document names. `EXT-05` remains
unexamined in the sense generation 13 meant — the 33 absent pre-rewrite objects
were never looked for in it — and it now stays that way by decision rather than
by deferral.

---

## OT-1 executed — **the run exists and no job started** · close-out, 2026-08-29

**Status of `CI-01`** `OPERATOR-BLOCKED`, **unchanged — and the blocker is now a
different one.** `SPEC-g0-3b` unchanged.
**What was delegated** the close-out order of 2026-08-29 §T1 delegated `OT-1` to
the loop by name, lifting `R-4`'s prohibition on `git push` and `SK-09`'s on
network access for this one command sequence.

Append-only, so nothing above is edited. This entry supersedes forward.

### What was run

```
git push origin loop/champion          # 8a74b7a..65bef05, fast-forward, no force
gh pr create --base main --head loop/champion \
  --title "Audit loop: generations 0-14" --body "CI trigger. Not for merge."
```

Fast-forward was verified before pushing (`git merge-base --is-ancestor
origin/loop/champion HEAD`). **No merge, no force-push, no history rewriting.**
The pull request is open and is **not** for merge.

* Pull request: https://github.com/Raar1999/bayespinn-inv/pull/1
* Run: https://github.com/Raar1999/bayespinn-inv/actions/runs/33235695610
* Head: `65bef0598a0c5fdc4528878ccd861122d6591af1` — the current champion
* Duration: **5 seconds**

### Every leg

| leg | conclusion | steps executed | job |
|---|---|---:|---|
| tests (py3.11, ubuntu-latest) | **failure** | **0** | [99056176181](https://github.com/Raar1999/bayespinn-inv/actions/runs/33235695610/job/99056176181) |
| tests (py3.12, ubuntu-latest) | **failure** | **0** | [99056176161](https://github.com/Raar1999/bayespinn-inv/actions/runs/33235695610/job/99056176161) |
| **tests (py3.11, windows-latest)** | **failure** | **0** | [99056176138](https://github.com/Raar1999/bayespinn-inv/actions/runs/33235695610/job/99056176138) |
| clean-environment install + selftest | **failure** | **0** | [99056176075](https://github.com/Raar1999/bayespinn-inv/actions/runs/33235695610/job/99056176075) |

**Zero steps ran on any leg.** Every job carries the same annotation:

> *The job was not started because recent account payments have failed or your
> spending limit needs to be increased. Please check the 'Billing & plans'
> section in your settings*

`gh api …/jobs` confirms `steps: 0` on all four. **No checkout happened, no
interpreter was installed, and not one line of this repository was executed on
any machine.** `failure` here is a billing state, not a test result, and reading
these four reds as evidence about the code would be the same class of false
closure that created this file.

### Why, and it is an account-level fact rather than a repository one

`Raar1999/bayespinn-inv` is **private**. Private repositories draw Actions
minutes from the account's quota; the quota is exhausted or the payment method
has failed. Nothing in `.github/workflows/ci.yml`, in the tree, or in the push
caused this, and no change to any of them can clear it.

**Two operator actions would clear it, and both are reserved.** Restore the
billing method or raise the spending limit; or make the repository public, for
which Actions minutes are free. The second is an irreversible disclosure of the
whole tree and its history to the internet and **is not taken by the loop under
any delegation short of one that names it**.

### `CI-01` and `SPEC-g0-3b`

**Neither closes.** `CI-01` closes only with a retrievable log for every leg; the
logs are retrievable and they record that nothing ran. `SPEC-g0-3b` requires a
retrievable run log **per matrix leg**, and a job that never started produces no
such log.

**The exact failure that blocks them** is now recorded and it is not the one that
blocked them for eleven generations. The sequence has moved:

| generation | blocker |
|---|---|
| 0–7 | no remote existed |
| 8–10 | remote decision unanswered; `ACCEPTED-PERMANENT` by default trigger |
| 11–14 | remote existed, push reserved to the operator |
| **close-out** | **push done, PR open, run triggered — Actions billing at the account level** |

`CI-01`'s generation-9 `ACCEPTED-PERMANENT` cost statement is **superseded
forward, not deleted**, exactly as the generation-11 reversion required. It
remains in `docs/G9_RESULT.md` §1 as what was true on its date.

### The 3.9 leg — the order's premise is stale, and so is this file's own table

The close-out order directs attention to *"the 3.9 leg specifically"*, green or
red. **There is no 3.9 leg.** `.github/workflows/ci.yml` at `65bef05` runs
`python-version: ["3.11", "3.12"]` on ubuntu plus one windows 3.11 job. 3.9 was
removed at `AUDIT_g7` together with the support claim it existed to evidence, and
`requires-python = ">=3.11"` now makes a 3.9 leg fail at *install* rather than at
test — which would be noise, not evidence.

**So neither branch of the order's disjunction can fire, and the floor does not
move.** `pyproject.toml`'s `>=3.11` stays where it is, and it stays there on the
reasoning already recorded at `DEC-g7-2`: only versions the suite has actually
run on are declared. That is neither of the two outcomes the order anticipated —
it is not *green, floor moves back* and it is not *red, floor stays on evidence*.
It is *the experiment the order describes is not in the matrix*.

**The leg table in this file, above, is stale in the same way.** Its first row
reads *"ubuntu × 3.9 — the `requires-python >=3.9` floor is real"*, and both the
leg and the `>=3.9` floor it names were removed at generation 7. The table has
described a matrix that does not exist for eight generations. Append-only, so the
row is not edited; this paragraph supersedes it. **The live leg list is the four
rows of the table in this entry.**

This is `AGE-01` twice over — the operator's own order and this file's own table
each written against a rule set that had already moved. Neither was wrong on its
date. Both stopped describing the tree.

**What the 3.12 leg would have settled.** 3.12 is the analogue: it installs under
the current floor, it has still never executed anywhere, and a green 3.12 leg is
what restores its classifier. It did not start either, so the classifier stays
withdrawn and the reason is unchanged.

### `WINDOWS_RISK_g6.md` — first opportunity to score it, and it scores nothing

That document was static analysis standing in for a run that had never happened.
The Windows job started no steps, so **none of its five ranked predictions is
confirmed or refuted**, and it remains static analysis.

| rank | prediction | scored? |
|---|---|---|
| 1 | Text I/O using the platform encoding · FOUND, FIXED, GUARDED | **no** — no test ran |
| 2 | Line-ending conversion altering file content · FOUND, FIXED, GUARDED | **no** — no checkout happened |
| 3 | **`NB-02`: the notebook step destroys committed evidence, and CI is green only because the test step precedes it** | **no**, and it is the one that only a real run could ever score. Steps 5 and 6 both did not execute, so the ordering dependency the document predicts is untested. |
| 4 | POSIX-only commands in the Makefile · CRASH CLASS | **no** — CI does not invoke the Makefile |
| 5 | `/tmp` and `bin/` in the clean-install job · SCOPED SAFE | **no** — the clean-install job did not start |

`SPEC-g0-3a`'s standing verdict — *passes for the 3.11 leg only, locally* — is
unchanged. The 3.12 and Windows legs remain **unevaluated, not passing**, which
is the distinction this file exists to protect.

### Defects revealed

**None.** No repository code executed. The order directs that a real defect be
reported and not fixed here; there is nothing to report, and the absence of a
finding is not evidence of correctness. The local suite on Windows / CPython
3.11.9 remains the only evidence that exists, and `PROV-07` is still validated on
`win32` only.

### What is now newly true

Only this: **the workflow has been triggered.** For fifteen generations
`.github/workflows/ci.yml` had never been reached by any trigger. It has now been
reached, a run object exists at a retrievable URL, and the matrix expanded to the
four legs the workflow declares. The run then stopped at the billing gate before
a single step. That is a smaller step than closing `CI-01` and it is a real one:
the failure mode has moved from *nobody has tried* to *one named account setting*.
