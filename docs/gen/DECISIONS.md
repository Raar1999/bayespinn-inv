# Decision ledger — autonomous decisions under the operator ruling of 2026-08-25

Append-only (A-1). One entry per autonomous decision. A decision without a
reversal command is a reserved decision and does not appear here — it appears as
an `ESCALATE` block in the generation report.

---

## DEC-g0-1 — set `core.autocrlf=false` in the local repository config

**WHAT** Before any staging, set `core.autocrlf` to `false` for this repository only.

**EVIDENCE** `git config --system core.autocrlf` → `true`; no `.gitattributes`
exists; `file $(git ls-files | head -200)` reports **39 CRLF files**, `Makefile`
among them. With `autocrlf=true` and no attributes file, `git add` rewrites CRLF to
LF in the object store, so `git archive <sha>` would emit LF where the working tree
has CRLF and the §6 Step 2 attestation would fail on every CRLF file.

**OPTIONS CONSIDERED**
1. Stage as-is, let Step 2 fail, halt. — Correct by the letter of the ruling and
   useless: the halt would report a git configuration default, not a defect in the
   project.
2. Add `.gitattributes` with `* text=auto` and re-normalise the tree. — This is
   "normalising past it", explicitly forbidden by §6 Step 1, and it would alter the
   bytes being adopted.
3. Set `core.autocrlf=false` locally so staging preserves bytes exactly. — Chosen.

**CHOSEN** Option 3. The ruling forbids normalising past a line-ending rewrite; it
does not require permitting the rewrite. Preserving bytes is what the attestation
is *for*. `SK-08` bans changing **global** git config; this is local. `R-4` does not
list config among the prohibited operations.

**VERIFIED** All 166 indexed files byte-identical to their working-tree
counterparts before the commit was written; Step 2 attestation then passed
164/164.

**REVERSAL** `git config --local --unset core.autocrlf`

**FORCED DEFAULT FOLLOWED?** n/a — no forced default covers this class.

---

## DEC-g0-2 — adopt `outputs/` past `.gitignore`; exclude build artefacts

**WHAT** Stage the 42 files under `outputs/` with `git add -f`, and do **not** adopt
the 48 files under `build/`, `dist/` and `src/bayespinn_inv.egg-info/`.

**EVIDENCE** `PRESERVE_MANIFEST_g0.sha256` covers 212 files. `git check-ignore`
reports 90 ignored: 42 in `outputs/` (1,900,048 bytes — manifests, result JSON,
summaries, figures, checkpoints) and 48 regenerable build artefacts (464,111
bytes). `git ls-files outputs/` before adoption returned only `results.json` and
`results_summary.md`; `outputs/results/manifest.json` was ignored, which is
AUDIT_g0 `PROV-01` — a fresh clone shipped the headline results with no provenance
record at all.

**OPTIONS CONSIDERED**
1. Adopt all 212 including `build/`+`dist/`. — Satisfies a literal reading of Step 2
   but commits byte-copies of `src/` and a wheel, which `make clean` deletes and
   `.gitignore` excludes by design.
2. Adopt only the 122 non-ignored files. — Leaves `PROV-01` open: the evidence base
   for every published claim stays outside the repository.
3. Adopt 122 + 42 `outputs/`, exclude the 48 build artefacts, and attest over that
   set while enumerating the exclusions with their digests. — Chosen.

**CHOSEN** Option 3. `outputs/` is evidence; `build/` is output. The exclusion is
enumerated rather than silent: all 48 paths and digests are listed in
`docs/PROVENANCE_BIFURCATION_g0.md`, and both preserved copies retain them.
`git add -f` was preferred over editing `.gitignore` because `.gitignore` is
outside the standing write grant and force-adding is sufficient and durable — once
tracked, the ignore rule no longer applies to these paths.

**REVERSAL** `git rm --cached -r outputs/` (content on disk untouched; both
preserved copies retain all 212 files)

**FORCED DEFAULT FOLLOWED?** Yes — `E-3`: supersede, never mutate. No existing
`outputs/**` file was modified; they were recorded as-is.

---

## DEC-g0-3 — two new public symbols in `utils.provenance`

**WHAT** Add `git_status_counts()` and `git_tree_digest()` to the public API, and
add an optional `repo` argument to all four git helpers.

**EVIDENCE** Measured pre-fix behaviour on a scratch repository: a tree missing
three source modules returns `git_is_dirty() == False`. The old helpers were
hardwired to `Path(__file__).resolve().parents[3]`, so no test could exercise them
against a controlled repository — which is part of why the defect survived two
audit cycles.

**OPTIONS CONSIDERED**
1. Fix `git_is_dirty()` only. — Restores the boolean but still cannot distinguish
   an edited line from a missing solver, which is the actual `PROV-02` failure.
2. Add the counts only. — Detects the two kinds of divergence but still cannot tell
   two runs apart when both claim the same commit.
3. Counts plus a content digest, all with an injectable `repo`. — Chosen.

**CHOSEN** Option 3. `E-4` permits up to 3 new public symbols per generation with
an ADR and a test; this uses 2, with `ADR-0006` and `tests/test_provenance_g0.py`
(16 tests). The `repo` argument is a parameter addition, not a new symbol.
Measured cost of the digest on this repository: 28 ms. mypy findings unchanged at
25; ruff exit 0.

**REVERSAL** `git revert <commit>` on the `loop/champion` branch; or
`git checkout c115757 -- src/bayespinn_inv/utils/provenance.py` to restore the
adopted version.

**FORCED DEFAULT FOLLOWED?** Yes — `E-4`: allowed, with an ADR and a test.

---

## DEC-g0-4 — park the `papers/draft.md` identifiability instance under R-3

**WHAT** Correct the identifiability label (`PH-21`, AUDIT_g0 `SCI-11`) in `README.md`,
`docs/RELEASE_READINESS.md` and `docs/CLAIM_EVIDENCE_MATRIX.md`; leave the one
unqualified passage in `papers/draft.md` untouched and pin it with a test.

**EVIDENCE** A passage-level guard over the claim surface finds exactly one
unqualified rank claim in the protected document:

```
papers/draft.md:255: If terminal I-V determines only 3-4 of 16 doping directions,
                     then a surrogate ...
```

`papers/draft.md` does label the result `local` three times (lines 23, 73, and an
explicit limitation at 349), so a reader of the whole paper is not misled; the
passage is unqualified within its own paragraph, which is what PH-21 addresses.

**OPTIONS CONSIDERED**
1. Edit `papers/draft.md`. — Forbidden: `R-3` makes `papers/**` reserved.
2. Drop `papers/**` from the guard. — Hides the finding; the next audit would have
   to rediscover it.
3. Mark the parametrised case `xfail`. — Reads as "known-broken, ignore", and
   `AH-01` treats xfail as a way of making a red test green.
4. Exclude it from the sweep but assert on it separately, pinning the count at the
   measured value of 1. — Chosen.

**CHOSEN** Option 4. `TestParkedPapersInstance` fails in **both** directions: if the
count rises a new unqualified claim entered the protected document; if it falls to
zero the passage was fixed or `R-3` released, and the document should move into
`CLAIM_SURFACE` and the test be deleted. A second test asserts the document still
labels the result somewhere, so a passage-level defect cannot silently become a
document-level one. Strictness is preserved; only the guard's *reach* is narrowed,
and the excluded instance is asserted on rather than skipped.

**REVERSAL** Add `"papers/draft.md"` back to `CLAIM_SURFACE` and delete
`TestParkedPapersInstance` in `tests/test_claim_surface_g0.py`.

**FORCED DEFAULT FOLLOWED?** Yes — `E-3`: supersede, never mutate; and §4's "park
that clause and continue".

**ESCALATE**
```
ESCALATE R-3 @ generation 0, phase A/Step 6
WHAT:      papers/draft.md:255 states the identifiable-rank result with no
           local/global qualifier in its own paragraph. PH-21 forbids this;
           R-3 forbids me editing papers/**.
EVIDENCE:  tests/test_claim_surface_g0.py::TestParkedPapersInstance pins the
           count at 1. The same defect was corrected at README.md rows 51, 70,
           267, 340 and RELEASE_READINESS rows 72, 189.
OPTIONS:   1) Operator edits line 255 to read "determines only 3-4 of 16 doping
              directions *at a given operating point*". 2) Operator releases R-3
              for this one line. 3) Do nothing -- the paper keeps one passage a
              reader can quote as a global claim, mitigated by the explicit
              limitation at line 349.
BLOCKED:   SPEC-g0-5 cannot reach 100% of the claim surface; it passes for every
           document this loop may edit.
```
