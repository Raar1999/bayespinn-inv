# `HIST-01` — the hashes were rewritten, not lost

**Generation 11, 2026-08-28.** `HIST-01` was carried for three generations as
`OPEN, PRE-EXISTING, UNREPAIRABLE FROM INSIDE THE TREE`. It was repairable from
inside the tree the whole time, by a file that was sitting in `.git/`. This
document is the repair and the account of why nobody found it.

**The artefacts.** `docs/COMMIT_HASH_MAP_g11.json` (the map, tracked),
`scripts/repair_hist01.py` (builds and verifies it),
`tests/test_hist01_repair_g11.py` (guards it), `tests/commit_map.py` (the one
definition of *resolve*, imported by every guard that needs it).

---

## 1. What the finding said, and what was actually true

> Every `LOOP_STATE` file from generation 8 onward records `champion_commit` and
> `machinery_commit` hashes that `git cat-file` cannot resolve in this working
> tree, and `champion_per_generation` names none that it can. Eight guards fail
> because of it.

Every clause of that is **correct as an observation**. The failure was the
diagnosis attached to it — that the objects were gone and could only be found in
an external copy, if anywhere.

**They were never gone.** On **2026-08-28 at 09:16**, before the close-addendum
session, someone ran `git filter-repo` on this branch. It rewrote every commit
from `c115757` — *"Adopt the post-audit working tree as attestable history"* —
forward, which is all but the root commit. A rewrite gives every affected commit
a **new hash**. Every hash a state file recorded before 09:16 therefore names an
object that no longer exists, while the commit it named is still present under a
different name.

`filter-repo` writes exactly the artefact needed to undo the renaming and leaves
it in `.git/filter-repo/`:

```
$ ls .git/filter-repo/
already_ran  changed-refs  commit-map  first-changed-commits  ref-map
             suboptimal-issues
$ head -3 .git/filter-repo/commit-map
old                                      new
01bb81342f91be36329f5af35279d9bfe430ece0 3793067257772ac00e0488a73ffe2344db3061b0
06eb32fa618f6b824493070adc3e7d4d719ba4a4 7ac7e7f4b44e019a6b11228d7540dc963cbacb56
```

The second row is generation 0's champion. `06eb32f` is what
`LOOP_STATE_v1.json` records; `7ac7e7f` is *"g0 promote candidate g0c2: asinh
reformulation closes GRAD-02 and GRAD-03"*, which is generation 0's champion.

**35 commits are in the table, and it resolves every hash any state file
records.**

## 2. Why three generations missed it

Because nobody ran `ls .git`. The finding's own words — *unrepairable from
inside the tree* — were an **inherited claim about the tree**, and
`docs/CLOSE_RULING.md` §5.1 had already named that exact failure mode, one
generation before this run found another instance of it:

> **Inherited obstructions were being carried as claims and never tested.**
> `DOC-03a` is the instance that made it visible … An obstruction inherited from
> an earlier generation is a claim about the tree, it is exactly as checkable as
> any other claim about the tree, and this loop found that they were not being
> checked.

`DOC-03a` was a badge regex that turned out to be changeable in one line.
`HIST-01` is the same class and a great deal more load-bearing: it is the
provenance of ten generations, and it was written off on an untested premise.

The operator directive §7 anticipated this, and its instruction is what
prompted the search:

> Before ruling this unrepairable, note that it is unrepairable *from inside
> this tree*. The objects the state files name may exist in the original working
> copy, in a preservation archive, or in a reflog elsewhere. `git fsck
> --lost-found`, the two external copies, and any other clone are all
> unexamined. An `U-INSTR` verdict here is premature until they are.

All four were examined. **All four were dead ends, and the repair was somewhere
none of them pointed:**

| where | examined | result |
|---|---|---|
| `git fsck --lost-found` | yes | two dangling commits, both `On loop/champion: tmp-baseline` stashes. Neither is a recorded hash. |
| `D:\bayespinn-inv\_preserve_g0_B` | yes | file copy, **no `.git`**. Cannot carry commits. |
| the scratchpad `preserve_A` copy | yes | file copy, **no `.git`**. Same. |
| `D:\bayespinn-inv\bayespinn-inv.zip` | yes | contains a `.git`, but it is the **pre-loop** repository: 102 loose objects, `refs/heads/main` at `6577f4b`, dated before generation 0. None of the 26 recorded hashes is in it. |
| `origin` (a remote now exists) | yes | `origin/main` is `6577f4b`, the root commit. The loop's commits were never pushed. |
| **`.git/filter-repo/commit-map`** | **not until now** | **the repair.** |

Two further pieces of evidence say the tree itself is intact and was rewritten
exactly once:

* **author date equals committer date on all 37 commits.** A rebase or an amend
  leaves those different. The commits are original; only their names changed.
* `.git/logs/HEAD` begins on 2026-08-28, and `.git/logs`, `.git/info` and
  `.git/packed-refs` all carry an mtime of 09:16 — `filter-repo` expires the
  reflog, which is why the loop's own history appeared to start that morning.

## 3. The verification, which is the part that matters

A map that produces *some* existing commit for every input is worthless. It has
to produce the *right* one. Three checks, in `scripts/repair_hist01.py`:

| | check | result |
|---|---|---|
| `V1` | every mapped target resolves under `git cat-file -t` as a commit | **PASS**, 26 of 26 |
| `V2` | the mapped commit's **own message** names the generation the state file recorded it under | **PASS**, 16 of 16 |
| `V3` | the commit that **last wrote** each state file has that file's recorded champion as its parent, once mapped | **PASS**, 9 of 9 |

`V2` is the one that makes this evidence rather than restatement. The commit
messages were written *before* the rewrite; the map came out of `filter-repo`.
They are independent sources, and they agree on all sixteen:

| | recorded | resolves to | the commit's own message |
|---|---|---|---|
| `g0` | `06eb32f` | `7ac7e7f` | g0 promote candidate g0c2: asinh reformulation closes GRAD-02 and GRAD-03 |
| `g1` | `9670bec` | `6df00aa` | g1 promote: SEC-02 — library code never executes code from a checkpoint |
| `g2` | `aff9195` | `798a9be` | g2 promote: PKG-04 — the library no longer execs a file from the checkout |
| `g3` | `3302817` | `fa5cdb8` | g3 promote: API-05 — minibatch sampling no longer reads the global RNG |
| `g4` | `de1b6f6` | `39fff5d` | g4 promote: SW-04a — the environment probe no longer fails silently |
| `g5` | `b5218b1` | `e8f0db2` | g5 promote: DOC-05, DOC-06 — documentation that measurement contradicts |
| `g6` | `a59255e` | `a8bf371` | g6 S-1 RESULT: global non-identifiability demonstrated by witness … |
| `g7` | `922c2cc` | `c657502` | g7 RULE-01: the rules the operator enacts now live in the tree … |
| `g8` | `0f22ecc` | `2e5da84` | g8 RESULT: the observation set and a free junction both move the spectrum … |
| `g9` | `68f3d5d4` | `ae09e49` | g9 RESULT: the ordering was a property of one operating point … |
| `g10` | `5424d99a` | `4dd047f` | g10 RESULT: the mechanism is not localisation … |
| `close` | `6b3f4c0a` | `94213e7` | close: the rank climb is the spectrum flattening … |
| `close_addendum` | `608cc83d` | `608cc83` | addendum: the chart-G witness set is refined in full … (resolves directly; written after the rewrite) |

### 3.1 `V3`'s first draft was wrong, and the correction is recorded rather than tidied away

`V3` initially anchored on the commit that **added** each state file and reported
`LOOP_STATE_v4` and `v5` as violations. They are not violations. Both files were
**amended after being added**, by commits whose own messages say exactly that —
*"g7 state: point the champion at the tip, and record the results commit
separately"* and *"g8 state: the champion pointer is repointed at the results
commit, by definition"*. The champion in a file's current content is written by
the commit that last wrote it, so that is the anchor.

Recorded here because the failure was a defect in the **check**, not in the
history, and a verification that reports two false violations is a verification
that will be ignored the third time. The map now marks which files were amended
instead of hiding that they were.

## 4. What the repair is, and what it deliberately is not

**It is the map being in the tree.** `.git/` is not tracked.
`.git/filter-repo/commit-map` existed in exactly one place, on one disk, in a
directory a fresh clone does not carry and `git gc` has no obligation to
preserve. It cannot be derived again once gone — the old hashes are not
recoverable from the new objects. **Copying it into `docs/` is the repair**, and
`tests/test_hist01_repair_g11.py::test_the_map_is_tracked_by_git` is what stops
it drifting back out. This is `OT-3`'s warning applied to the one artefact that
makes ten generations of history readable, and it was one `rm -rf .git` away
from being permanent.

**It is not an edit to any `LOOP_STATE` file.** The operator directive §6
reserves *any mutation — as opposed to supersession — of an existing manifest,
ADR, or ledger entry*, and a state file is a ledger entry. Every recorded hash
stays exactly as recorded. The map is a **forward correction**, and
`test_no_loop_state_file_was_edited_by_the_repair` checks that no state file
quietly lost a hash the map lists as rewritten.

**It is not a loosening of the guards.** This is the part that could go wrong
without anyone noticing, so it is built to fail closed. `resolve_commit` tries
the recorded hash directly first; only if that fails does it consult the map,
and **only if the map carries all three of its own passing verifications**. A
guard that passes through it now asserts strictly more than it did before the
rewrite: not merely *this hash names a commit*, but *this hash names a commit,
and the renaming that makes it do so is itself verified against the commit
messages and the parent chain*. An absent map, a malformed map, an unverified
map, or a hash the map does not cover all return `None`, and the guard fails
exactly as it did.

`tests/test_hist01_repair_g11.py` exercises that refusal rather than asserting
it: it plants a map with one verification flipped to `false` and requires the
resolver to refuse it.

## 5. What it costs, measured

**Eight guards were failing.** All eight pass, and none of them was weakened:

```
tests/test_loop_state_close.py::…::test_the_champion_is_a_real_reachable_commit
tests/test_loop_state_close.py::…::test_the_machinery_commit_is_real
tests/test_loop_state_g10.py::…::test_the_champion_is_a_real_reachable_commit
tests/test_loop_state_g10.py::…::test_the_machinery_commit_is_real_and_is_not_the_champion
tests/test_loop_state_g8.py::…::test_the_champion_is_a_real_reachable_commit
tests/test_loop_state_g8.py::…::test_the_per_generation_champions_are_all_real
tests/test_loop_state_g9.py::…::test_the_champion_is_a_real_reachable_commit
tests/test_loop_state_g9.py::…::test_the_machinery_commit_is_real_and_is_not_the_champion
```

**Three guards were silently skipping**, which is worse than failing because
nothing reports it. Two in `tests/test_commit_messages_g7.py`, whose helper turns
a non-zero `git` exit into `pytest.skip`, so `git log … 3e05c9da…^..HEAD` and
`git log -1 1a090f0` both became skips; and one in
`tests/test_loop_state_g8.py` (`champion commit not available`). The commit
message guard `DOC-07` was therefore **not running over the range it was written
to police**, and no one would have learned that from a green suite.

**All three now run**, and restoring them is why the tracked map carries the
**complete** rewrite table — all 35 rewritten commits — rather than only the 26
hashes a state file cites. `1a090f0` appears in no `LOOP_STATE` file. A subset
map would have resolved the eight loud failures and left the quiet ones exactly
as they were, which is the shape of repair this finding is a warning about.

## 6. Status

`HIST-01` moves from `OPEN, PRE-EXISTING, UNREPAIRABLE FROM INSIDE THE TREE` to
**`RESOLVED-BY-MEASUREMENT`**, with the mechanism identified, the map tracked
and verified, and the guards restored to asking their original question.

**What it does not resolve.** `REPRO-01` is untouched: the *working tree* that
produced `outputs/identifiability/` on 2026-08-19 is still not recoverable, and
that is a different object from a commit hash. `OT-3` is untouched and is now
sharper — the same argument that says the commit map had to be copied out of
`.git/` says the repository still lives on one disk.
