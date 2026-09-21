# MANIFEST_REDACTION_IMPACT_g16 — what the manifest hashes certify, and what redaction would and would not achieve

**Pass type** read-only impact analysis. No writes to the tracked tree, no
commits, no visibility change. **Tree at** `82f5d90`, branch `loop/champion`.
**Date** 2026-09-20. Companion to `docs/RELEASE_HOLD_g16.md`.

**Headline, before the detail, because it inverts the question:** all eight
manifests are **redactable and hash-preserving** — the disclosure sits in three
JSON paths that no hash in the repository covers. **And redacting them would not
remove the disclosure from a public repository**, because 52 of the 72 commits on
`loop/champion` carry it in their trees and publication publishes all of them.
The question the prompt poses has a clean answer; the answer does not buy what it
looks like it buys.

---

## 1. What does the manifest hash actually certify?

### 1.1 There is no manifest self-hash

`src/bayespinn_inv/utils/provenance.py:283–300`, `RunManifest.write()`: `[OBS]`

```python
path = out_dir / "manifest.json"
path.write_text(json.dumps(self.to_dict(), indent=2, default=str),
                encoding="utf-8", newline="\n")
```

That is the whole of it. **No digest is computed over the manifest, and no
digest field over the manifest is written.** The premise in the task — *"the hash
the manifest currently carries"*, singular, over the file — does not correspond to
anything in the code. Nothing certifies the manifest as a file; the manifest is
the certificate, not the thing certified.

This is the load-bearing fact for the whole analysis, so it is stated first and
sourced to the line.

### 1.2 What hash fields do exist — four classes, none covering the file

Enumerated across the eight affected manifests by walking every string value
matching `^[0-9a-f]{64}$` or `^[0-9a-f]{40}$`: `[OBS]`

| class | fields | what it is a hash *of* | covers the manifest? |
|---|---|---|---|
| **commit** | `git.commit` | SHA-1 of `HEAD` at run time | no — external, historical |
| **tree** | `git.tree_digest` | SHA-256 over every non-ignored file in the repo at run time (`provenance.py:131–156`) | no — external, historical |
| **pre-registration** | `prior_hash`, `criterion_hash`, `rule_hash`, `measure_hash`, `decision_hash`, `scope_hash`, `outcomes_hash`, `statistic_hash`, `junction_prior_hash`, and the `inherited_hashes` block | a hash of a *decision or config object*, computed before the measurement so the criterion cannot move afterwards | no |
| **input** | `config.input_sha256[<path>]`, `results…provenance.inputs_sha256[<path>]` | SHA-256 of a named *input file* under `outputs/` | no |

Counts are dense in places — `outputs/g10/manifest.json` carries 19 hash-shaped
values, `outputs/wit02_chartG/manifest.json` 18 — and not one of them is taken
over the manifest, over `loaded_code`, or over any path string.

### 1.3 So the answer to the question as posed

**Scoped, not whole-file.** Every hash in a manifest certifies something *outside*
the manifest: a commit, a tree, a pre-registered decision object, or an input
file. **The environment/path block where the disclosure lives is covered by no
hash at all.** Redacting a path string there is out-of-scope of everything the
manifest certifies, in the strict sense that no certified value is a function of
it.

### 1.4 `git.tree_digest` is the one that looks like an exception, and is not

`git_tree_digest()` hashes every non-ignored file in the tree, which **does**
include the eight manifests. So editing a manifest changes what that function
returns today. But the recorded values are historical — taken at run time,
against the tree as it then stood — and the current working tree already returns
something different from all eight: `[OBS]`

```
current working-tree digest:  7751b81498985104c828f3291633b89ac59b758e60a3b532c93fb1bcfc6eb05a
recorded, outputs/g9:         1788e47d189df88620c2d82c…      (and seven others, all distinct)
```

A recorded `tree_digest` is verified by checking out the commit it names and
recomputing there. **A forward redaction commit does not alter any historical
commit**, so every recorded digest stays verifiable exactly as it is now. This is
the same property that makes the redaction useless for a public repository, and
it is developed in §4.

---

## 2. Per-manifest verdict

The disclosure in all eight files is confined to **three JSON paths**, all under
`/loaded_code`, all written by `loaded_code_provenance()`
(`src/bayespinn_inv/utils/loaded_code.py:176–210`): `[OBS]`

* `/loaded_code/sys_path[]/entry`
* `/loaded_code/sys_path[]/resolved`
* `/loaded_code/editable_install_markers[]`

Census by decoded string value, not raw bytes:

| manifest | project-name occ. | home-path occ. | verdict |
|---|---|---|---|
| `outputs/chart_reconciliation_g7/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/figures_g15/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/floor_sensitivity_g15/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/g10/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/g11/wit02_chartL/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/g8/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/g9/manifest.json` | 4 | 10 | **redactable, hash-preserving** |
| `outputs/wit02_chartG/manifest.json` | 4 | 10 | **redactable, hash-preserving** |

Uniform, which is expected: every one records the same developer machine's
`sys.path`.

**Verified by simulation, in the scratchpad, against copies — nothing in the tree
was written.** `[OBS]` For each manifest, `loaded_code` was redacted and the
`git`, `results`, `config`, `artifacts` and `environment` blocks were re-hashed
and compared:

```
manifest                                       git      results  config   artifacts  env      residual
outputs/chart_reconciliation_g7/manifest.json  SAME     SAME     SAME     SAME       SAME     0
…  (all eight)
every hash-carrying block byte-identical: True
```

A whole-file redaction — not confined to `loaded_code` — was run as a control and
**also** moves no hash-carrying block, because no hash-carrying value contains a
path or a project name.

### 2.1 A second spelling the task's search does not reach

`/loaded_code/editable_install_markers[]` carries, in every one of the eight:
`[OBS]`

```
C:\Users\abhis\AppData\Roaming\Python\Python311\site-packages\__editable__.fab_ops_analytics-0.1.0.pth
```

That is `fab_ops_analytics`, **underscored**. A search for
`fab-ops-analytics-complete` does not match it — 8 further lines, one per
manifest, naming the same private project in the form pip gave it. Any redaction
script must carry both spellings, and the standing count of "16 occurrences"
should be read as 16 *lines* of the hyphenated form; the census above finds 32
occurrences of that form plus 8 of the underscored one.

### 2.2 Four more manifests carry it and are not published

`outputs/g11/archive_rerun/{g8,g9,g10,wit02_chartG}/manifest.json` also carry the
disclosure. All four are **untracked and gitignored** `[OBS]`, so they are neither
published nor covered by `git_tree_digest()`. They need no action. The task's
figure of eight is the right one for the tracked tree.

---

## 3. What `R-3` actually forbids

### 3.1 The citation is wrong, and it is worth correcting before it is relied on

`docs/OPERATOR_TASKS.md:446` says the manifests *"cannot be scrubbed because
mutating a manifest is reserved under `R-3`"*. Checked against the record: `[ART]`

* **`R-3` is the `papers/**` reservation.** `LOOP_STATE_v1.json`
  `escalations_open[0]`: `{"id": "R-3", "where": "papers/draft.md:255", "status":
  "parked", "ref": "DEC-g0-4"}`. Every other citation agrees —
  `docs/CLOSE_RULING.md:11` and `:332`, `docs/G9_RESULT.md:59`,
  `docs/G10_RESULT.md:503`, `docs/G11_RESULT.md:286`, and the `LOOP_STATE`
  series, all read *"`R-3` reserves `papers/**`"*. `LOOP_STATE_v15.json:771`
  records `R-3` as **lifted** on 2026-08-29 when the close ruling assigned the
  paper to the loop.
* **The manifest reservation is directive §6**, not `R-3`. `docs/G12_RESULT.md:130`:
  *"It is not repaired by editing the manifests. **Directive §6** reserves any
  mutation of an existing manifest."* `docs/OPERATOR_RULINGS_INDEX.md:150`
  summarises the 2026-08-28 directive's §6 as reserving *"`git push` and anything
  needing credentials by name"* — which does not, in that summary, mention
  manifests at all.

So the sentence that has been carrying this decision for three weeks cites a rule
that governs a different path and that was lifted a day after it was written. The
reservation it means is real and lives elsewhere. **This is a citation defect, not
a licence** — directive §6 as quoted at `G12_RESULT.md:130` does reserve manifest
mutation, and that is the rule in force.

### 3.2 (a) or (b)?

Directive §6 **as quoted** is (a): *"any mutation of an existing manifest"*, with
no purpose clause and no carve-out. On the text, blanket.

The precedent points the other way and is worth putting on the record, because it
is the only evidence of what the reservation was protecting. `PROV-04` at
generation 0 found manifests *naming a commit that cannot have produced them* —
a provenance falsehood, in the field that matters most — and the disposition was
**"SUPERSEDED — recorded, manifests not edited"** (`docs/gen/GEN_g0.md:67`), with
`CHANGELOG.md:918` confirming *"Existing manifests are **not** edited."* The
repair went into a new document, `docs/PROVENANCE_BIFURCATION_g0.md`. So when the
loop had the strongest imaginable reason to edit a manifest — the record was
wrong — it superseded forward instead.

**My reading, and I am labelling it a reading rather than a finding:** the
purpose visible in that precedent is *the provenance record is never rewritten,
even to correct it*, which is `R-4`'s logic applied to artefacts. A redaction of
`loaded_code.sys_path` is not a correction of a provenance claim; it removes an
incidental fact about the developer's machine that no finding, no hash and no
measurement rests on. Under a purpose reading it is outside what the reservation
protects.

**It is a stretch, and here is why I think so.** The precedent shows the
reservation surviving a case where editing would have made the record *more*
true. That is a strong prior that the rule is about the artefact's immutability
as such, not about the truth-value of particular fields. Reading (b) into a text
that says "any mutation" requires the operator's say-so, and `OPS-01` is the
relevant discipline: a rule that lives only in a reading does not exist. **This
is a ruling to make, not an interpretation to act on.**

---

## 4. Blast radius — and why the answer to §1–§3 does not settle the question

### 4.1 The work, if it were done

Small, and fully specified by §2:

1. One script over the eight tracked manifests: load JSON, rewrite the three
   `/loaded_code` paths, dump with `indent=2` and `newline="\n"` to match
   `RunManifest.write()` byte-for-byte in every untouched region.
2. **No hash to recompute.** There is none over the file (§1.1), and every hash
   *in* the file is byte-identical after the edit (§2), verified.
3. Downstream dependency check — **already run, and it is clean.** `[OBS]`
   * No test reads `loaded_code` from a committed manifest.
     `tests/test_loaded_code_g7.py:161–192` asserts the *mechanism* against a
     manifest it generates into `tmp_path`, deliberately — its own docstring says
     pinning today's tree state is what it is avoiding.
   * The only test touching an affected manifest is `tests/test_rep01_g8.py:121`,
     and it reads `results.containment.*` and `results.spectra.*` only.
   * `PRESERVE_MANIFEST_g0.sha256` pins 212 generation-0 files and covers **none**
     of the eight — all eight postdate it.
   * `git grep` for the literal path strings across `tests/`, `scripts/`, `src/`
     and `papers/` returns **nothing**. The single documentary reference is
     `docs/AUDIT_MASTER.md:1606`, the `EXT-07` row, which the existing scrub
     already reaches.
4. `EOL-02` applies: the write states LF, as the original does.

Cost: under an hour, including the controls. Risk to provenance: none that I can
find, measured rather than argued.

### 4.2 And it would not achieve the purpose

The disclosure is not only at `HEAD`. It is in the committed history, and
publication publishes the history: `[OBS]`

| | commits on `loop/champion` |
|---|---|
| total | **72** |
| whose tree contains `fab-ops-analytics` (either spelling) | **52** |
| whose tree contains an absolute home path | **71** |

`git log -S` names seven commits that introduced it — `affbcce`, `2e5da84`,
`ae09e49`, `4dd047f`, `608cc83`, `b251755`, `e39cb60` — one per generation from
g7 to g15, which is exactly what one expects when every generation writes a
manifest from the same machine.

A forward redaction commit changes the file at `HEAD` and leaves all 52 trees
intact and fetchable by anyone who clones. The only operations that would remove
them are `filter-repo` and a force-push, **both unconditionally forbidden** by the
standing rules, without exception and not subject to this analysis.

So redaction buys exactly one thing: the disclosure is absent from the
`HEAD` snapshot — from a zip download, from the GitHub file browser, from a
shallow clone. It is present in the full history for anyone who runs
`git log -S` or clones normally. **That is a cosmetic improvement, and calling it
anything more would be false.** Whether it is worth doing depends on whether the
threat model is a casual reader of the repository page or someone who clones it,
and that is not a technical question.

---

## 5. Verdict

**Per manifest — all eight identical:**

| manifest | verdict |
|---|---|
| `outputs/chart_reconciliation_g7/manifest.json` | **redactable, hash-preserving** |
| `outputs/figures_g15/manifest.json` | **redactable, hash-preserving** |
| `outputs/floor_sensitivity_g15/manifest.json` | **redactable, hash-preserving** |
| `outputs/g10/manifest.json` | **redactable, hash-preserving** |
| `outputs/g11/wit02_chartL/manifest.json` | **redactable, hash-preserving** |
| `outputs/g8/manifest.json` | **redactable, hash-preserving** |
| `outputs/g9/manifest.json` | **redactable, hash-preserving** |
| `outputs/wit02_chartG/manifest.json` | **redactable, hash-preserving** |

**Summary line.** Full redaction of all 106 occurrences **at `HEAD`** is
achievable, cheaply, with no hash or provenance breakage — the disclosure lives in
three uncertified JSON paths plus, in the other classes, in ordinary prose and
JSON that nothing pins. Full redaction **of the repository as published** is
**not achievable**, because 52 of 72 commits carry the project name and 71 of 72
carry a home path in their trees, and the only tools that reach committed history
are forbidden. The cost of the achievable part is under an hour plus one operator
ruling on directive §6; the cost of the unachievable part is the standing
prohibition on history rewriting, which is not for sale.

---

## 6. One defect in this pass, reported rather than buried

The first run of the census returned **zero** home-path occurrences in all twelve
manifests, and the residual assertion in the first redaction simulation passed on
that basis. The cause was mechanical: the analysis script was written through a
shell heredoc that collapsed `\\` to `\`, turning the character class `[\\/]`
into `[\/]` — slash only. The detector could not fire, and the check it guarded
reported success.

This is `FILL-01`'s shape one level up: a check that passes on something other
than what it was for. It was caught by cross-reading the script's output against
`git grep -c`, which said 10 per file, and the two disagreeing is the only reason
it surfaced. The corrected script (`redact_sim_v2.py`) carries a **positive
control** — it asserts the detector fires on a known-positive string before it is
trusted — which is what `SW-20` requires of a guard and what the first version
lacked. Every count in this document comes from the corrected run.

## 7. Integrity

No files created, modified, deleted or renamed in the tracked tree; no installs;
no git write operations; no config, data, network or external-system changes; no
`gh` invocation; no visibility change. Analysis scripts and manifest copies were
written to the session scratchpad only. `python -c` imports of
`bayespinn_inv.utils.provenance` created `__pycache__` entries under
`src/bayespinn_inv/utils/`, which is gitignored — stated rather than omitted.
Two new untracked documents exist in `docs/`: `RELEASE_HOLD_g16.md` from the
prior pass and this one. Workspace verified at `82f5d90`.
