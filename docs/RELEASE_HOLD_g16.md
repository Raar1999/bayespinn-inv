# RELEASE_HOLD_g16 — the public-release prompt checked against the rules in force, and held

**Pass type** read-only. Not a generation; `LOOP_STATE` not incremented; the loop
stays closed. **Tree at** `82f5d90`, branch `loop/champion`.
**Date** 2026-09-20.

**Verdict in one line: the repository was not made public. Nothing in §4 of the
release prompt was executed.** The prompt's §3 was not answered, and the `AGE-01`
check the prompt itself ordered returned two findings that change what §3 is
asking.

---

## 1. What was actually done in this pass

Read-only throughout. No file in the tracked tree was created, modified or
deleted by this pass; this document is new and untracked. No git operation beyond
`log`, `status`, `grep`, `ls-files`, `branch`, `remote`, `config --get`. No `gh`
call of any kind — **PR #1 was not read**, because reading it is §4.3 and §4 is
gated on §3.

---

## 2. `AGE-01` applied to the release prompt — two findings

The prompt directs: *"`AGE-01` applies to this prompt — check it against those
documents before acting."* It does, and it fires twice. Both are the
frozen-enumeration half of the rule: each statement below was correct when it was
written and is incomplete against the tree as it stands.

### 2.1 A standing operator ruling says the repository stays private, permanently

`docs/OPERATOR_TASKS.md`, final entry, recorded under the operator close-out
ruling of 2026-08-29 §2, under the heading **"The visibility question is closed,
permanently"**: `[ART]`

> **The repository stays private.** Making it public would make Actions minutes
> free and clear the blocker, and it is refused. […] **Recorded as permanent so
> it is not re-proposed each time the blocker is met.**

The release prompt describes the repository as *"currently private"* and orders
the flip at §4.4. **It nowhere cites, distinguishes or supersedes that ruling.**

This is not a refusal of the operator's authority — the operator may reverse
their own ruling, and a ruling recorded as permanent is reversed by saying so,
not by being routed around. It is a report that the instruction and the record
disagree, and that the disagreement is the operator's to close. Under `SR-4`, a
ruling is a claim and gets the same treatment as a measurement: it is superseded
on the record, not silently overtaken.

### 2.2 The ruling's own premise has grown, and so has the prompt's §2

The permanent ruling rests on a count: *"**67 absolute home paths** under
`C:\Users\abhis\` in the manifests"*. That number came from `docs/G12_RESULT.md`
§1.6 at generation 12 (38 commits). Re-measured at `82f5d90` (47 commits): `[OBS]`

| pattern | occurrences | files |
|---|---|---|
| `C:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+` | **102** | **23** |
| `/(home\|Users)/[a-zA-Z0-9_.-]+` | 15 | 11 |
| union of the two | — | **26** |
| Windows pattern, `outputs/` subtree only | 85 | 10 |

Commands: `git grep -InE <pattern> -- .` and `git grep -lE <pattern> -- .` at
`82f5d90`.

So the ruling that closed the visibility question was weighing 67 occurrences in
12 files; the tree now carries **102 in 23 files** by the same regex, 85 of them
inside the `outputs/` subtree where `R-3` reserves mutation. The ruling is not
wrong about any occurrence it counted. It has simply never been asked whether its
count is still complete — which is the exact shape `AGE-01` names.

---

## 3. §3 is under-scoped, and this is the finding that matters

§3 poses one decision: is `fab-ops-analytics-complete` — a second private
project's name — acceptable to disclose, given it survives **16 times inside the
`outputs/` manifests** that `R-3` makes unscrubbable, while the
`AUDIT_MASTER.md` scrub does not reach it?

The 16 is correct. `[OBS]` `git grep -In "fab-ops-analytics-complete" -- .`
returns 17 lines: 16 across 8 manifests under `outputs/`, plus 1 in
`docs/AUDIT_MASTER.md` that the scrub does reach. Context, from
`outputs/g9/manifest.json:167`:

```
"entry": "D:\\fab-ops-analytics-complete\\fab-ops-analytics-complete\\project5-fab-operations-analytics\\src"
```

**But `fab-ops-analytics-complete` is not the only private project name that
survives the scrub, and the `outputs/` subtree is not the only place such a name
survives.** The scrub draft de-identifies nine `EXT-*` trees inside
`docs/AUDIT_MASTER.md` and is clean of every one of them — verified: `[OBS]` zero
residual hits in `AUDIT_MASTER.scrubbed_v4.md` for all ten names checked, and
zero residual `C:\Users\abhis`. The document it does not reach is the rest of the
tree.

Occurrences **outside** `docs/AUDIT_MASTER.md` at `82f5d90`: `[OBS]`

| private name | occurrences | surfaces it survives on |
|---|---|---|
| `fabkg-bench` | **34** | `CHANGELOG.md`, `LOOP_STATE_v12`–`v15.json`, `docs/G13_RESULT.md`, `docs/G14_RESULT.md`, `scripts/write_loop_state_{g13,g14,close}.py` |
| `invspec` | **28** | `CHANGELOG.md`, `LOOP_STATE_v12`–`v15.json`, `docs/G14_RESULT.md`, the same three scripts |
| `AIEF` (bare) | **23** | `CHANGELOG.md`, `LOOP_STATE_v12`–`v15.json`, `docs/G14_RESULT.md`, the same three scripts |
| `fab-ops-analytics-complete` | **16** | the `outputs/` manifests (8 files) — the one §3 names |
| `FabKG_LoopLogs` | 3 | `LOOP_STATE_v14`–`v15.json`, `scripts/write_loop_state_close.py` |
| `AIEF_Product_Development` | 2 | `LOOP_STATE_v12.json`, `scripts/write_loop_state_g13.py` |
| the `EXT-01`, `EXT-06`, `EXT-07` and `EXT-09` names | 0 | reached by the scrub |

`CHANGELOG.md` lines 315–318, 325, 368 and 436–441 name `AIEF`, `fabkg-bench` and
`invspec` in running prose alongside their object-survival counts.
**`CHANGELOG.md` is append-only under the standing rules**, which puts those
occurrences in the same unscrubbable class as the `R-3` manifests — arguably a
harder class, since `R-3` at least contemplates a supersede route.

So the accurate statement of the decision is not *one name, one location class,
reserved*. It is: **four private project names across five surface classes — the
`outputs/` manifests, `CHANGELOG.md`, four `LOOP_STATE_v*.json`, three
`scripts/write_loop_state_*.py`, and two `G*_RESULT.md` — totalling 106
occurrences outside the scrub's reach.** Two of those classes are append-only or
reserved; three (`LOOP_STATE_v*.json`, the scripts, the result documents) are
neither, and none has been assessed.

Answering §3 as written would have authorised the disclosure of one name and
silently carried three others.

---

## 4. What is confirmed, and what is not

**Confirmed this session, re-measured:**

* `[OBS]` **Credentials clean at `82f5d90`.** Zero hits across the tracked tree
  for `ghp_`, `gho_`, `ghs_`, `github_pat_`, `sk-`, `AKIA…`, `xox[baprs]-`,
  `AIza…`, and the private-key header.
* `[OBS]` **No personal email address.** The only non-`noreply` matches are five
  `noreply@anthropic.com` literals inside `tests/test_commit_hook_tracked.py`,
  which are the hook guard's own fixtures. Author and committer identity on all
  47 commits is `Raar1999@users.noreply.github.com`, GitHub's privacy-preserving
  form.
* `[OBS]` **The scrub draft exists and is well-formed.** 47 changed lines against
  `docs/AUDIT_MASTER.md`, de-identifying nine `EXT-*` trees, six private remote
  names, three backup volume paths, one cloud-sync folder and one storage-device
  serial, with every finding ID, count, severity and verdict preserved.
* `[OBS]` **`docs/COMMIT_HASH_MAP_g11.json` is tracked** and would go public with
  the tree.
* `[OBS]` **Nine commits are unpushed**; `origin/loop/champion` is at `65bef05`,
  local `HEAD` at `82f5d90`.
* `[OBS]` **`core.hooksPath` is `C:\Users\abhis/.git-hooks`** — the machine-wide
  hook location. Whether the attribution-stripping hook still fires was **not**
  tested, because testing it means making a commit.

**Not confirmed, and inherited rather than measured — flagged under the claim
law's status-inheritance rule:**

* `[UNK]` **"No pre-rewrite object exposure", the 34 rewritten SHAs, and the push
  timeline.** §2 of the prompt asserts these from two prior read-only passes. No
  artefact in this tree records those passes. They may well be right; they are
  not `[OBS]` for this session and this pass did not re-derive them.
* `[UNK]` **The map-off-machine precondition (pre-push runbook step 1).** The
  prompt says *"confirm it is still satisfied; do not re-check from scratch if
  already verified this session"* — nothing was verified this session. The last
  artefact on it is `docs/G12_RESULT.md` §1.7, which records step 1 as **"human
  action, not done"**. If a later session satisfied it, no record of that is in
  the tree.
* `[UNK]` **PR #1's content.** Not read; see §1.

---

## 5. The decision, restated for the operator

Two things are now open where the prompt had one.

**(a) Does the permanent private ruling of 2026-08-29 stand?** If it is being
reversed, the reversal is an operator ruling and belongs on the record — in
`RULINGS.md` or as an appended `docs/OPERATOR_TASKS.md` entry — before the flip,
not after it. The ruling's stated premise (67 paths in 12 files) should be
replaced with the measured 102 in 23 in the same act, so the reversal is made
against what is actually there.

**(b) With the disclosure scoped correctly**, is it acceptable? The surface is
four private project names, 106 occurrences outside the `AUDIT_MASTER.md` scrub,
across the `outputs/` manifests (reserved), `CHANGELOG.md` (append-only), four
`LOOP_STATE_v*.json`, three `scripts/write_loop_state_*.py` and two
`G*_RESULT.md` — plus 102 home-path occurrences naming the username, plus the
directory layouts those paths and names carry.

The three unreserved classes — the `LOOP_STATE` files, the scripts, the result
documents — are the only part of this that a second scrub could reach. Whether
that is worth doing depends entirely on (b), which is why it is not proposed
here as work.

**Nothing in §4 was executed. No commit, no push, no visibility change, no DOI,
no Zenodo.**

---

## 6. `EOL-02`

Written by the editor tool at platform default; `.gitattributes` governs on
commit if this file is ever tracked.

## 7. Integrity

No files created, modified, deleted or renamed in the tracked tree; no installs;
no git write operations; no config, data, network or external-system changes; no
`gh` invocation. One new untracked file was created: `docs/RELEASE_HOLD_g16.md`,
this document. Workspace verified unchanged at `82f5d90` — `git status` reports
only the two untracked documents (`docs/PAPER_PACKAGE_STATUS_g16.md` from the
prior pass, and this one).

---

## 8. Correction, 2026-09-21

The table in §3 originally spelled out four project names in its final row —
the row recording that the scrub had reduced them to zero. Writing them there
put them back into the tracked tree, and those four sit **outside** the
disclosure the operator accepted, which covers `fab-ops-analytics-complete`,
`fabkg-bench`, `invspec` and `AIEF` only. They are now referred to by the
`EXT-*` identifiers the scrub itself uses. Corrected before publication, so no
reader outside this machine ever saw them.

The defect is worth naming rather than quietly patching: a document written to
report a disclosure surface enlarged it, in the one line asserting the surface
was clear.
