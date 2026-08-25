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

---

## DEC-g7-1 — run `G7-R` against one commit under a recorded CI waiver

**WHAT** Execute every `G7-R` measurement **and** Phase A's audit against a single
commit, without waiting for a CI result, and record the waiver here with the
command that reverses it.

**EVIDENCE** The `§7` precondition ("on receipt of the CI result … run `G7-R`") is
not satisfiable on this host and not satisfiable soon:

```
$ git remote -v
                       # empty
$ git ls-remote --heads origin
fatal: 'origin' does not appear to be a git repository
```

`docs/OPERATOR_TASKS.md` `OT-1` gives `git push -u origin loop/champion`, which
assumes a remote that does not exist. `R-4` forbids the loop creating one and
`SK-09` forbids the network access it would need.

**OPTIONS CONSIDERED**
1. Hold `G7-R` until a remote exists. — Blocks the entire generation on an
   operator action of unknown latency, and CI protects none of `SPEC-g7-1…-4`.
2. Run the scientific clauses now against tree X, audit later against tree Y. —
   Refused by the operator, and correctly: measuring on one tree and auditing
   another is the bifurcation pathology at smaller scale.
3. Run everything against one commit under a recorded waiver. — Chosen.

**CHOSEN** Option 3, per the operator ruling of 2026-08-26 §"G7-R SEQUENCING",
which withdrew the `§7` CI precondition as over-scoped. `SPEC-g0-3` is decomposed:
`3a` unchanged; `3b-local` requires every interpreter obtainable *on this host* to
execute with a retrievable log; `3b-windows` stays `OPERATOR-BLOCKED` hard, with
`docs/WINDOWS_RISK_g6.md` as standing substitute evidence.

`CI-01` and `SPEC-g0-3b` remain **OPERATOR-BLOCKED**. The waiver buys sequencing,
not closure.

**REVERSAL** When CI executes, re-run Phase A's `G-CODE` clause against the tree
that CI ran on and compare it to `docs/audit/AUDIT_g7.md`:

```bash
git remote add origin <url> && git push -u origin loop/champion
gh workflow run ci.yml --ref loop/champion && gh run watch
# then re-run the G-CODE clause and diff against AUDIT_g7 §G-CODE
```

**FORCED DEFAULT FOLLOWED?** Yes — one tree, one commit.

---

## DEC-g7-2 — move the support floor to 3.11 and withdraw the 3.9/3.10/3.12 claims

**WHAT** Set `requires-python = ">=3.11"`, reduce the version classifiers to 3.11
alone, remove 3.9 from the CI matrix, and correct the false statement in
`[tool.mypy]`. Hold `ruff`/`black` at `target-version = "py39"` deliberately.

**EVIDENCE** Three measurements, in order of what they settle.

*Which interpreters are obtainable here* — `SPEC-g0-3b-local`:

| leg | obtainable | method tried |
|---|---|---|
| 3.9 | **no** | `py -0p`; `where python`; `C:\Python*`, `AppData\Local\Programs\Python`, conda/miniconda/anaconda roots, `.pyenv`; `uv python list` lists `cpython-3.9.25` as `<download available>` only, and fetching it needs the network (`SK-09`); `hatch`/`tox`/`nox` absent |
| 3.11 | **yes** | `C:\Program Files\Python311\python.exe`, 3.11.9 |
| 3.12 | **no** | as 3.9 — `cpython-3.12.13` is `<download available>` only |
| 3.14 | interpreter yes, **unusable** | present at `pythoncore-3.14-64`, but numpy, scipy, pytest, torch and matplotlib are all absent and installing them needs the network (`SK-09`) |

*What the 3.11 leg actually does* — `outputs/ci_local_g7/`: ruff exit 0;
**470 passed, 0 failed**; notebook generator exits 0.

*What can be said about 3.9 without a 3.9 interpreter* —
`scripts/check_python_support_floor.py`, 96 files: **0** syntax rejections under
`ast.parse(feature_version=(3,9))`, **0** post-3.9 stdlib or typing uses, **0**
runtime PEP 604 unions. Every dependency floor (`numpy>=1.22`, `scipy>=1.10`,
`torch>=2.0`, `matplotlib>=3.7`) admits 3.9.

That last result is the one that must not be over-read. It can only **falsify**
the floor, never confirm it: it cannot see dependency *resolution*, which is what
actually breaks old interpreters, and only a CI leg settles that.

The `[tool.mypy]` comment asserted the 3.9 claim "is backed by the CI matrix
(which actually runs the suite on 3.9)". False in both halves — `CI-01` records
that the matrix has never executed.

**OPTIONS CONSIDERED**
1. Keep `>=3.9` and mark it unevidenced in prose. — This is `S-4` exactly: an
   advertised API surface nobody has run. Packaging metadata is a promise to an
   installer, not prose, and a reader of `pyproject.toml` never sees the caveat.
2. Keep `>=3.9` because static analysis found no obstruction. — Confuses "no
   obstruction found by a method that cannot see resolution" with "works".
3. Move the floor to 3.11 and withdraw the unevidenced classifiers. — Chosen.

**CHOSEN** Option 3. The operator ruling of 2026-08-25 §3.2 allowed exactly two
outcomes and no third: a green leg, or the floor moves and the claim is
withdrawn. The leg cannot run here, so the floor moves.

`ruff` and `black` stay at `py39`, **below** the declared floor, on purpose: the
tree is measured 3.9-clean today, and holding the linter there keeps it that way,
so restoring the classifier later costs one CI leg instead of a port. A withdrawn
claim should be cheap to re-earn.

**REVERSAL** Restore `requires-python = ">=3.9"`, the 3.9/3.10/3.12 classifiers
and the 3.9 CI leg **only** on a retrievable green run log for that leg:

```bash
gh workflow run ci.yml --ref <branch> && gh run watch     # 3.9 leg green
git revert <this commit> --no-commit -- pyproject.toml .github/workflows/ci.yml
```

**FORCED DEFAULT FOLLOWED?** Yes — measurement over assertion; an unevidenced
claim is withdrawn, not annotated.
