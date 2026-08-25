# ADR-0006 — Provenance records the tree, not just the commit

- **Status** Accepted
- **Date** 2026-08-25
- **Generation** 0
- **Supersedes** nothing. **Superseded by** nothing.
- **Findings** AUDIT_g0 `PROV-02` (CRITICAL), `PROV-01`, `PROV-03`, `PROV-06`
- **Spec clause** `SPEC-g0-2`

## Context

`RunManifest` recorded two provenance facts: `git.commit` and `git.dirty`. The
dirty flag was computed as

```python
_git("status", "--porcelain", "--untracked-files=no")
```

which is blind to untracked files by construction.

At generation 0 that blindness was not hypothetical. The repository's only commit,
`6577f4b`, was the pre-audit project. Both audit cycles — 6 of 40 source modules,
204 of 246 collected tests, 7 experiment launchers, the CI workflow and the entire
audit corpus — existed solely as untracked files. Measured on a scratch repository,
the old function returns `False` for a tree missing three source modules:

```
clean repo                       -> git_is_dirty = False
3 untracked source/test modules  -> git_is_dirty = False
```

Every manifest under `outputs/` therefore named a commit that could not have
produced its results. `HEAD` has no `SGConfig(equilibrate=…)` option at all, a
built-in-potential relative error of `2.7558e-07` against the producing tree's
`7.243e-14`, and a mass-action residual of `6.1019e-03` against `2.934e-09`.
`git.dirty: true` was recorded, but it was true only because 70 *tracked* files
also differed — the flag could not distinguish that from a fixed typo.

A provenance record that cannot tell "one line changed" from "a different solver,
and 83% of the test suite, are missing" is not a provenance record.

## Decision

Provenance describes **the tree that ran**, not merely the commit it claims.

1. `git_is_dirty()` counts untracked files. A result produced by code that is not
   in the commit is exactly as unreproducible as one produced by edited code.
   Ignored files still do not count: regenerable build output is not divergence.

2. Two new public symbols, both `Optional` and both `None` outside a checkout:

   - **`git_status_counts()`** → `{"tracked_modified": int, "untracked": int}`.
     The two kinds of divergence are reported separately, because they mean
     different things. Tracked-modified says the commit is nearly right;
     untracked says the commit may be a different program.
   - **`git_tree_digest()`** → SHA-256 over the content of every non-ignored
     file, keyed by path. The commit SHA cannot detect a divergent tree and the
     dirty flag only reports *that* one exists. The digest says *which* tree ran,
     so two manifests can be compared directly. Measured cost on this repository
     (166 files, 4.1 MB): **28 ms**.

3. `RunManifest.create()` makes a single `git status` call and derives the flag
   from the counts, so `dirty` and the counts cannot disagree. The manifest's
   `git` block becomes:

   ```json
   "git": {
     "commit": "c115757…", "dirty": true,
     "tracked_modified": 1, "untracked": 1,
     "tree_digest": "8079c499…"
   }
   ```

4. All four git helpers take an optional `repo` argument. Previously they were
   hardwired to `Path(__file__).resolve().parents[3]`, so the behaviour could not
   be tested against a controlled repository — the defect survived two audit
   cycles partly because nothing could exercise it. `tests/test_provenance_g0.py`
   builds throwaway repositories and depends on no ambient state.

## Consequences

**Existing manifests are not rewritten.** They are protected (`R-3`) and they
remain wrong about their own provenance. `docs/PROVENANCE_BIFURCATION_g0.md`
records, per manifest, why `6577f4b` cannot have produced it and which commit can.

**`git.dirty` becomes true more often**, including for runs that were previously
reported clean. That is the point: it was under-reporting.

**A new field can be absent.** Manifests written before this ADR have no
`tracked_modified`, `untracked` or `tree_digest`. Readers must treat a missing key
as "unknown", not "zero" — the distinction that `Optional` preserves everywhere
else in this module.

**`PROV-03` does not close.** Recording the tree from here forward cannot attest
the past. The adoption commit `c115757` has no verifiable origin and no candidate
in any generation may mark that resolved.

## Alternatives rejected

- **Leave the flag and document the caveat.** The caveat already existed in the
  docstring — "A result produced from a dirty tree is not reproducible from the
  commit alone, so this must be recorded rather than assumed clean" — and the
  implementation defeated it. A comment that contradicts its code is worse than
  neither.
- **Record only the digest, drop the counts.** The digest detects divergence but
  does not characterise it. A reader seeing two digests differ still cannot tell
  whether to worry. The counts are what make the record actionable.
- **Hash only tracked files.** That reproduces the original defect in a new form.
- **Refuse to run from a divergent tree.** Too strict for a research repository
  where iterating before committing is normal, and it would have made the
  generation-0 audit itself impossible to perform.
