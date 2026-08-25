# AUDIT — generation 7 (`G7-R`, bounded reconciliation)

One tree, one commit. Every measurement in this generation and this audit run
against the same commit; the machinery landed first at `3e05c9d` and the
manifests record it. The `§7` CI precondition was withdrawn by the operator as
over-scoped and the waiver is `DEC-g7-1`, with its reversal.

Scope: reconciliation only, per the ruling of 2026-08-26. No new scientific scope
was opened. Three of the ruling's own premises were falsified by measurement and
are recorded in `§5` rather than absorbed.

---

## 1. Spec clause status

| clause | status | evidence |
|---|---|---|
| `SPEC-g7-1` nesting determination | **PASS** | `docs/CHART_RECONCILIATION_g7.md` §1; read from `run_global_identifiability.py::make_oracle` L60-62 and `scharfetter_gummel.py::solve` L767-774, not from a basis name. Answer: **neither chart contains the other**, at every finite `d` |
| `SPEC-g7-2` embedding test | **PASS, falsifier did not fire** | §2. Best chart-L stand-ins reach 0.70% and 2.2% of the distinguishability floor; the embedded pair distance is 1.207e-02 against a 2.0e-02 floor |
| `SPEC-g7-3` matched-`d` statement | **PASS** | §3. Four cells, one operating point, one noise level, one observation set. Full spectra reported; ranks second |
| `SPEC-g7-3e` native chart-L witness | **PASS — found** | §4. 37 witnesses from 1200 prior draws (719,400 pairs); 3 of 3 seeded refinements |
| `SPEC-g7-4` profile likelihood | **PASS** | §5. Path, endpoints and parameterisation stated; control direction included |
| `SPEC-g7-5` PROV-07 mitigation | **PASS** | §3 below; `tests/test_loaded_code_g7.py`, 6 controls including the live `build/lib` shadow |
| `DOC-07` now guarded | **PASS** | `tests/test_commit_messages_g7.py`; positive control is `1a090f0`, the message that forced the rule |
| `SPEC-g7-6` claim-surface sync | **PASS with a recorded deviation** | `tests/test_claim_surface_g7.py`, 27 assertions; field split recorded as `DEC-g7-3` |
| `§4.2` negative control | **REJECTED as required** | `TestRulingNegativeControl::test_the_battery_rejects_it`, run through the same predicate the real documents are judged by |
| `SPEC-g0-3a` | **PASS** | `outputs/ci_local_g7/` — lint, suite and notebook generator all exit 0 on 3.11.9 |
| `SPEC-g0-3b-local` | **PARTIAL — reported** | §2 below. Only 3.11 is obtainable on this host |
| `SPEC-g0-3b-windows` | **OPERATOR-BLOCKED, hard** | standing substitute evidence `docs/WINDOWS_RISK_g6.md` |

---

## 2. `SPEC-g0-3b-local` — which legs were obtainable, and by what method

Attempted all three. Reported rather than assumed.

| leg | obtainable | method tried |
|---|---|---|
| **3.9** | **no** | `py -0p`; `where python`; `C:\Python*`, `AppData\Local\Programs\Python`, conda / miniconda / anaconda roots, `.pyenv`; `uv python list` (lists `cpython-3.9.25` as `<download available>` only — fetching needs the network, `SK-09`); `hatch`, `tox`, `nox` all absent |
| **3.11** | **yes** | `C:\Program Files\Python311\python.exe`, 3.11.9. Executed, log retained |
| **3.12** | **no** | as 3.9; `cpython-3.12.13` is `<download available>` only |
| 3.14 | interpreter yes, **unusable** | present at `pythoncore-3.14-64`; numpy, scipy, pytest, torch, matplotlib all absent, and installing needs the network (`SK-09`) |

**3.11 leg, retrievable logs in `outputs/ci_local_g7/`:** ruff exit 0; suite exit 0;
notebook generator exit 0.

**The 3.9 question is resolved, in the negative.** No 3.9 interpreter is
obtainable, so no green leg is obtainable, and the ruling of 2026-08-25 §3.2
allows no third outcome: the floor moves to 3.11 and the claim is withdrawn.
`DEC-g7-2` carries the evidence, the reversal, and the deliberate decision to hold
`ruff`/`black` at `py39` — below the declared floor — so the withdrawn classifier
costs one CI leg to re-earn rather than a port.

Static evidence, `scripts/check_python_support_floor.py`, 96 files: 0 syntax
rejections under `ast.parse(feature_version=(3,9))`, 0 post-3.9 stdlib or typing
uses, 0 runtime PEP 604 unions. **This does not support the claim** and is not
used to. It can only falsify a floor; it cannot see dependency resolution, which
is what actually breaks old interpreters. `CI-01` stays open regardless.

---

## 3. `SPEC-g7-5` — PROV-07, with its platform assumptions stated

`src/bayespinn_inv/utils/loaded_code.py`, wired into `RunManifest.write` so the
record describes what the run *imported*, not merely what was on disk.

**The accidental case is already present in this repository.** `build/lib/bayespinn_inv/`
is gitignored, older than `src/`, and contains both `inverse/identifiability.py`
and `inverse/global_identifiability.py` — the two modules that produce the
published identifiability numbers. `git status` is clean while it sits there. It
is used as a positive control rather than a hypothetical.

| control | result |
|---|---|
| negative control — ordinary source checkout | not flagged |
| planted shadow package outside the tree | flagged, `outside_tree` |
| **live `build/lib` copy** | flagged |
| in-tree but untracked module (the bifurcation shape) | flagged, `inside_tree_untracked` |
| manifest actually carries the record | asserted, and self-consistency checked against `git ls-files` |

**Platform assumptions, stated not assumed.** Path comparison is on
`Path.resolve()` output — symlinks, Windows junctions and substituted drives are
followed, so a module reached through a link landing outside the tree is reported
outside, deliberately. Case comparison is `os.path.normcase`, and the filesystem's
case sensitivity is **probed at run time** rather than inferred from
`sys.platform`. Editable-install markers on `sys.path` are recorded verbatim; this
host has two.

| | |
|---|---|
| **validated on** | `win32` / Python 3.11.9 |
| **unvalidated** | `linux`, `darwin` |

The POSIX path is unvalidated. It is stated here and in every manifest the check
writes, not assumed to work.

Live result on this generation's measurement run
(`outputs/chart_reconciliation_g7/manifest.json`): commit `3e05c9d`,
`dirty: false`, `flagged: false` across 15 imported modules.

**`PROV-07` is mitigated, not closed.** The check sees what a run imported; it
cannot see what a *future* run will import, and `CI-01` remains the only evidence
that the check behaves on a non-Windows host.

---

## 4. Findings opened this generation

| id | severity | finding |
|---|---|---|
| `CHART-01` | **HIGH** | Six generations of identifiability results were published without recording which of two non-nested parameterisation charts each was measured in. The local rank and the global witness were never comparable as stated, and nothing in the claim surface said so. Mitigated: `bayespinn_inv.inverse.charts` names both, `tests/test_claim_surface_g7.py` enforces the label, and the whole claim surface is relabelled |
| `CHART-02` | **MEDIUM** | `ScharfetterGummel1D.solve` silently resamples a doping array whose length differs from the grid, interpolating **arithmetically in `C`**. That convenience defines a parameterisation chart, and no analysis script that relies on it says so. The resampler is undocumented at the call sites that depend on it |
| `SPEC-11` | **MEDIUM** | At `d = 16` the identifiable rank is a **threshold count, not a population boundary**: the noise cutoff does not fall in the spectrum's largest gap in either chart (`×4.99` chart G, `×5.12` chart L, both after index 1). Every "of 16" number this repository has published inherits this. At `d = 4` the cutoff *is* a population boundary |
| `RULE-01` | **MEDIUM** | The rules operator rulings enact -- `SW-20` and `DOC-07` among them -- existed only in the ruling text. Generation 7 cited `SW-20` in three source files while a reader had nowhere to look it up, and `DOC-07` was cited nowhere and guarded by nothing. A rule that lives only in a message is unenforceable and, once the message is gone, unrecoverable. Mitigated: `docs/RULES_ENACTED.md` records both with the defect that forced them, and `tests/test_commit_messages_g7.py` gives `DOC-07` the guard it never had, with `1a090f0` as its positive control. Rules enacted before generation 7 are **not** backfilled -- reconstructing them from citations would be inventing text and attributing it to the operator |
| `EOL-01` | **LOW** | `pathlib.Path.write_text` opens in text mode, so on Windows it rewrites `\n` as `\r\n` and silently changes the bytes of any LF-committed file a tool touches. Three tracked files were converted this generation and `tests/test_line_endings_g6.py` caught all three. Any future tool that rewrites tracked files must open with `newline=""` |
| `NB-03` | **LOW** | `scripts/build_notebooks.py`, run as the CI `BUG-14` guard does, **strips execution outputs and reshuffles cell ids** in all 12 committed notebooks — 3082 deletions against 229 insertions. Harmless in CI, where the tree is discarded; locally it destroys committed outputs with no warning. `tests/test_notebooks.py` passes either way because it compares code cells only |

`EOL-01` and `NB-03` were both found by running the CI steps locally rather than
by reading them.

---

## 5. Premises of the ruling that measurement falsified

Recorded because a ruling silently reinterpreted is worse than one contradicted in
writing.

1. **"Chart L cannot represent either witness member to within the instrument
   floor."** False. The best chart-L stand-ins reach 0.70% and 2.2% of the floor.
   The claim came from a **collocation-only** embedding in the pre-`G7-R` scouting
   report — my own first pass, and the error was mine, not the operator's: the
   ruling reasoned correctly from a number I had given it. Collocation puts member
   b at 146% of the floor; the fitted stand-in puts it at 2.2%, a factor of 67.
   `tests/test_charts_g7.py::test_projection_is_at_least_as_good_as_collocation`
   pins the ordering so this cannot recur silently.

2. **`SPEC-g7-2`'s falsifier does not fire.** It reads "the embedded pair's
   distance exceeds the distinguishability floor". Under collocation it does
   (2.446e-02); under the best embedding it does not (1.207e-02). A falsifier of
   this shape is only meaningful against a *best* embedding.

3. **The `§3.3` posterior geometry.** The 2%-noise ESS collapse was attributed to a
   posterior "diffuse along the degenerate manifold". There is no manifold: the
   profile likelihood between the two witness members is **bimodal**, two isolated
   maxima separated by a 242-log-unit barrier, with only 5 of 61 path points inside
   the floor. Importance sampling collapses because it must land inside a narrow
   mode. The remedy follows the corrected diagnosis — mode-hopping or tempered
   sampling, not more samples.

The operator also corrected two of its own clauses in the same ruling (the `§7` CI
precondition as over-scoped, and `SPEC-g7-2`'s interpretation clause). Those are
recorded in `DEC-g7-1` and honoured here.

---

## 6. Carried forward unchanged

* `PROV-03` — `ACCEPTED-PERMANENT`, cost statement `docs/gen/GEN_g6.md` §2, cost
  has not grown.
* `CI-01`, `SPEC-g0-3b` — `OPERATOR-BLOCKED`. Not closed by the waiver; the waiver
  bought sequencing only. **A remote does not exist on this host**, so `OT-1` as
  written in `docs/OPERATOR_TASKS.md` cannot be run: `git remote -v` is empty.
* `REPRO-01` — `UNRESOLVABLE-BY-CONSTRUCTION`.
* `NB-02`, `PROV-05`, `SW-18a` — open, untouched, out of scope for a bounded
  reconciliation.
* **The 2%-noise contraction number stays withheld.** §5.3 explains why more
  samples will not produce it.
* **The `d=8` dimension-sweep point stays confounded** with sampling density. The
  witness *existence* metric is density-insensitive and is reported with its
  budget; the contraction metric is not, and carries its confound in the same row.
