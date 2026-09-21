# AUDIT g9 — what the process got wrong, and what the guards caught

Companion to `docs/G9_RESULT.md`, which carries the science. This carries the
findings about the loop itself: where a number could not be reproduced, where a
guard fired on its own author, and where a ruling's premise did not survive
contact with the tree.

---

## 1. `REP-01` caught its author, twice, in the same generation

### 1.1 A promoted number that could not be re-derived

The ruling of 2026-08-26 §2 instructed the loop to promote a figure from its own
verification report: *chart G and chart L return currents 44% apart on the same
coordinate vector — `1.790241e-04` against `2.576097e-04`* — into the table
carrying the 2.8% spectral agreement, on the ground that it supplies the
denominator making the invariance result meaningful.

**The figure could not be reproduced.** It was reported without its invocation:
no device, no bias, no grid, no chart pair, no projection. The construction that
produced it lived only in the verification session that produced it. Searching
the defensible constructions — same coordinate vector at `d = 4` and `d = 16`,
projected and collocated, over the published window and below it — reaches
distances of the right order at low bias (the closest, 1.931522e-04 against
2.676787e-04 at 0.075 V in chart G at `d = 4`, a 38.6% difference) and reproduces
those digits nowhere.

This is the exact defect §3 of the same ruling is about, committed by the same
party, one section earlier. It is recorded rather than quietly replaced because a
loop that only finds this class of error in its counterpart is not auditing, it
is scoring.

**What replaced it.** The observable-space distance between *exactly the two
cells whose spectra are compared*, over *exactly the window they are compared
in*, measured at all twelve operating points and written into
`outputs/g9/op_points.json` with its projection method beside it. It is **0.82%**
at the generation-8 operating point and at most **2.67%** anywhere. See
`docs/G9_RESULT.md` §2.6, which also records that the inference the ruling drew
from 44% inverts under the measured value.

### 1.2 A scope that was stated and wrong

The same ruling contrasts `ruff_exit: 0`, which "carries neither scope nor
method", with `mypy_findings: 25`, which "carries scope and method". The second
half does not hold. The generation-8 note reads *"25 over the tracked tree"*.
Measured:

| invocation | files checked | findings |
|---|---|---|
| `mypy src` | 44 | **25** |
| `mypy src tests scripts` | 112 | **150** |

25 is `mypy src`. The tracked tree gives 150. A stated-but-wrong scope is a
slightly worse failure than a missing one, because it reads as authoritative and
invites no check. Both fields are now records carrying their command, and
`tests/test_loop_state_g9.py` re-runs them.

---

## 2. `DOC-07`'s widened guard fired on a live message for the first time

The generation-9 machinery commit's first draft asserted *"the three findings
which are real untidiness"*. `tests/test_commit_messages_g7.py` — widened at
generation 8 with `1a090f0` as its positive control, precisely because that
generation's message spelled a count out in words — rejected it before the commit
was built on.

Two things follow, and the second is the one worth keeping.

* The guard is not vacuous outside its positive control. It has now caught a
  message written by someone who knew the rule, was thinking about the rule, and
  wrote the message anyway.
* The message was corrected by amending an unpublished commit. `R-4` makes a
  commit message uncorrectable *once it is history somebody else can hold*; it is
  not a prohibition on fixing a draft before anything references it, and treating
  it as one would have made a permanent false-shaped message out of a guard
  working as designed. The commit records that this happened, because a
  correction that erases its own trace is not verifiable.

---

## 3. What the new guards found on their first run

A guard's first run is the only unbiased one it ever gets, so what it found is
recorded here rather than silently repaired.

### 3.1 `tests/test_claim_surface_g9.py` — ranks without their observation set

`SPEC-g9-2`'s falsifier is *a rank appears anywhere on the claim surface at a
single window without its curve*. On its first run the guard found **18 passages
across six documents**:

| document | passages |
|---|---|
| `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md` | 10 (two table headers covering eight rows, one result row, one sentence) |
| `docs/CLAIM_EVIDENCE_MATRIX.md` | 4 |
| `README.md` | 1 |
| `docs/RELEASE_READINESS.md` | 1 |
| `docs/CHART_RECONCILIATION_g7.md` | 1 |
| `docs/NOVELTY_AUDIT.md` | 1 |

Every one carried its **cutoff** — `SPEC-11` had already been enforced — and none
carried what was measured. That is the shape of the defect: a rule that makes a
number carry one of its two conditions produces prose that looks fully qualified
and is not. All eighteen now name their observation set.

The document-level half found the same six documents quoting a rank and pointing
at no rank curve.

### 3.2 `tests/test_lint_scope_g9.py` — the coupling nobody would have predicted

Suppressing `F401` for `notebooks/*.ipynb` made all twelve of the generator's
deliberate `noqa: F401` directives unused, which `RUF100` then reported. So the
first attempt at "both scopes exit 0" exited 1 with twelve new findings of a rule
nobody had thought about.

That is not a nuisance, it is the configuration telling the truth: silencing a
rule while keeping its suppressions is incoherent. `RUF100` is listed beside
`F401` with the entailment named, and the guard asserts that every listed code
except that one is actually doing work — an ignore list padded with codes nothing
produces is how a narrow exemption becomes a wide one without anyone deciding to
widen it.

### 3.3 The notebook regeneration that was not done, and why

Three of the seven suppressed codes are real untidiness in
`scripts/build_notebooks.py`'s source strings rather than layout. Fixing them
means regenerating, and regenerating was measured: it produces a **3,097-line
deletion** across the twelve notebooks, because the generator emits clean cells
and the tracked notebooks ship executed outputs (`NB-01`).

Deleting the evidence that the notebooks ran, to remove three lint findings, is
the wrong trade. The three are enumerated in the guard so that repairing the
generator fails a test by design and the failure is the instruction — the same
shape as `TestParkedPapersInstance`.

---

## 4. Findings against the generation-8 record

Stated here rather than by editing `docs/G8_RESULT.md`'s body, which stands as
what was measured. A pointer block was added to its head.

1. **The ordering summary was under-specified before it was unreplicated.** Its
   two natural statistics disagree at generation 8's own operating point. This
   would have been true had `SPEC-g9-1` never run, and it is prior to the
   replication question.
2. **`SPEC-g8-5`'s barrier reading is the wrong way round for chart G.**
   Generation 8 sampled within- and between-cluster pairs in index order and
   concluded the likelihood basins outnumber the profile-distance clusters.
   Measured on the *witness pairs themselves*, chart G's median barrier is 8.31
   log-units against a floor barrier of 8.0 — six of thirteen at or below the
   floor. The conclusion holds for chart J at `d = 16` and inverts for chart G at
   `d = 4`. The difference is which pairs were walked, and the generation-8 text
   named that as the obvious next measurement.
3. **`SPEC-g8-2`'s chart-J witness count is grid-dependent.** Seven of thirteen
   pairs survive `N = 301 → 1201` at `tol_carrier = 1e-12`. The pairs that
   separate are those whose junctions were nearly coincident — one of them by
   0.4 nm, less than a grid spacing at `N = 301`, which separates by 195%. Those
   were never junction degeneracies. Generation 8 ran no refinement falsifier on
   this search, and the generation-6 clause that mandated one for the doping
   witnesses did not travel to it.
4. **`SPEC-11`'s licensed set is narrower than `(chart, d)`.** Chart G at `d = 4`
   is in-gap at 4 of the 12 operating points measured and out of gap at 8, and
   chart J at `d = 16` is in-gap at one of them. `outputs/g8/ranks.json` remains
   the source `tests/test_claim_surface_g7.py` reads, because that guard's
   licence is per-denominator and the generation-8 artefact is not rewritten;
   the finding is that a per-denominator licence is the wrong granularity and a
   later generation should key it on the cell.

---

## 5. Process notes

**One tree, one commit, honoured.** Every generation-9 measurement ran against
`a6728fe` with `dirty = false`, recorded in `outputs/g9/manifest.json`. The state
file is written in a third commit for the reason generation 8 documented: a state
file cannot name the commit that writes it.

**The pilot gate was not needed and was still run.** `SPEC-g9-4` projected 183 s
against a 900 s budget. The gate is reported anyway, because a gate that is only
reported when it bites is a gate whose non-binding cases nobody can audit.

**Nothing was part-run.** All twelve operating points produced a spectrum; the
`n_operating_points_without_a_spectrum` field exists and is zero. `PH-19`'s
discipline — refusals counted, not dropped — had nothing to count this time, and
the field records that rather than being omitted.

**Two devices, not four, for `SPEC-g9-2`.** Which two, and the reason, is stated
in `docs/G9_RESULT.md` §3 and in the code that selects them. The other two
devices' ranks appear in §2's cells at three windows each.

---

## 6. Still the operator's

Unchanged, and neither blocks anything the loop can do:

* **`papers/CORRIGENDA_g6.md`** — `R-3` reserves `papers/**`.
  `tests/test_claim_surface_g0.py::TestParkedPapersInstance` still pins the count
  of unqualified passages at one and still fails in both directions, so applying
  the corrigendum breaks it by design and the breakage is the instruction.
* **Preservation** — two copies on one disk. `PRESERVE_MANIFEST_g0.sha256` covers
  the generation-0 adoption and has not been extended to nine generations of
  results.
