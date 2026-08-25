# SPEC_g0 — generation 0, frozen

**Generation** 0 · **Date** 2026-08-25 · **Champion branch** `loop/champion`
**Adoption commit** `c115757f3e9829cd1feb8bb86d739bfd74ff2dcf`
**Audit** `docs/audit/AUDIT_g0.md` · **Ruling** operator amendment of 2026-08-25 §7

Clauses `SPEC-g0-1` … `SPEC-g0-6` are mandatory and may not be dropped. Every
clause carries a `FALSIFIER`; a clause without one is not a clause. Once this file
is hashed into `LOOP_STATE_v1.json` it is immutable for this generation — a spec
defect is fixed by writing `SPEC_g1.md` that cites and supersedes it (§8.4).

---

## SPEC-g0-1 — one commit reproduces the entire claim surface

**CLAUSE** Every quantitative claim in the claim surface is reproducible from a
single commit, by the command the claim itself names.

**BASELINE** No commit reproduced the claim surface. `6577f4b` produced
`2.7558e-07` for the built-in potential (the published figure) but has 42 tests,
34 modules and no `equilibrate` option; the working tree produced the 240-test
badge and every D-series number but was not in git. Measured split: 204 of 246
collected tests (83%) and 6 of 40 source modules were untracked.
Manifest coverage at baseline: 11 of 13 README headline rows named an experiment
with a `manifest.json`; the remaining 2 (`bayespinn selftest`, `make test`) name
directly-executable commands that produce no manifest and are test-guarded instead.

**TARGET** All 13 headline rows reproduce from `loop/champion` HEAD. Direction:
0 unreproducible rows. `n` = 13 (the full population — no sampling, so no
detection threshold is needed).

**REGIME** `loop/champion` HEAD, Python 3.11.9, NumPy 2.4.4, SciPy 1.17.1,
PyTorch 2.11.0+cu128, Windows 11, CPU, seed 0.

**FALSIFIER** Any claim whose reproducing command, run at the adoption commit,
returns a value outside its stated interval.

**GATE** `G-REPRO`, `G-DOC`.

**COST CEILING** Bounded by the seven experiment launchers. `run_results.py`
measured at 17 min wall-clock; the other six are unmeasured this generation and
are explicitly *not* claimed to have been re-run.

**RISK** If wrong, the repository looks reproducible while some headline number
still traces to a tree nobody has. That is the generation-0 defect returning in a
quieter form.

---

## SPEC-g0-2 — provenance detects tree divergence

**CLAUSE** A manifest records enough to tell whether the tree that produced it
matches the commit it names, including divergence caused by files absent from git.

**BASELINE** `git_is_dirty()` ran `git status --porcelain --untracked-files=no`.
Measured on a scratch repository: a tree missing three source modules returns
`False`. `n` = 1 controlled repository, deterministic — no interval applies to a
boolean that is categorically wrong.

**TARGET** `dirty` is `True` whenever any non-ignored file differs from HEAD or is
absent from it; `tracked_modified`, `untracked` and `tree_digest` are recorded as
separate fields; the flag is derived from the counts so the two cannot disagree.

**REGIME** Any git checkout. Ignored files (build output, caches) are excluded by
design — regenerable output is not divergence.

**FALSIFIER** A manifest produced from a tree carrying untracked source or test
files that does not record them.

**GATE** `G-REPRO`, `G-SEC` (no secrets or absolute home paths added).

**COST CEILING** Measured 28 ms for `git_tree_digest()` over 166 files / 4.1 MB.
Ceiling: 2 s, above which the digest would be reconsidered.

**RISK** If the digest is too coarse it gives false confidence; if too slow it gets
disabled. Both fail worse than the original defect, because they look fixed.

---

## SPEC-g0-3 — CI has executed

**CLAUSE** `CI-01` closes only against a retrievable run log for every matrix leg.

**BASELINE** `.github/workflows/ci.yml` was untracked at generation 0 and had
therefore never been committed, never pushed and never run. `AUDIT_MASTER` §6b
nevertheless recorded `CI-01` as **VERIFIED**. Measured: `git ls-files
--error-unmatch .github/workflows/ci.yml` → not in git. Run count: **0**.

**TARGET** ≥ 1 retrievable run log per matrix leg: Ubuntu × {3.9, 3.11, 3.12},
Windows × 3.11, and the `clean-install` job. `n` = 5 legs.

**REGIME** GitHub Actions on the repository's own remote.

**FALSIFIER** `CI-01` marked closed without a retrievable run log for every leg,
Windows included.

**GATE** `G-CODE`.

**COST CEILING** Zero local compute; the workflow is committed as of `c115757`.

**RISK** **This clause is expected to remain open.** `R-4` prohibits `git push`,
and no remote can be reached under `SK-09`. It is written so the gap is recorded
as unevaluable rather than quietly assumed green — which is exactly how `CI-01`
became a false closure the first time.

---

## SPEC-g0-4 — no non-finite gradient inside the documented doping envelope

**CLAUSE** For every finite input in the documented 1e21–1e25 m⁻³ doping envelope,
`ohmic_boundary_values` returns finite gradients.

**BASELINE** NaN gradients from `C_s = 1.3922e+08` upward, i.e. **N ≥ 1.3922e24
m⁻³** — **21.4% of the documented envelope by decades**. Bracketed by 40 bisection
steps; the last finite and first NaN inputs agree to 7 significant figures.
Mechanism: `torch.where` evaluates both branches, `-C + sqrt(C²+4)` underflows to
exactly `0.0`, the discarded branch becomes `inf`, and backward computes
`0 × inf = NaN`. Measured `-C + sqrt(C²+4)`: `1.490116e-08` at `C_s=1e8`,
`0.0` at `C_s=1e9`.

**TARGET** 0 non-finite gradients over a sweep of the full envelope. `n` ≥ 200
log-spaced points spanning `C_s = 1e5 … 1e9`, both signs of `C_s`, which resolves
the envelope to better than 0.02 decades — far finer than the 0.5-decade feature
being detected.

**REGIME** float64, both `C_s ≥ 0` and `C_s < 0`, gradients taken through
`phi_s_left`, `phi_s_right`, `log_n_*` and `log_p_*`.

**FALSIFIER** Any input in the envelope producing a non-finite gradient.

**GATE** `G-PHYS`, `G-CODE` (SW-07: both sides of the sign branch covered).

**COST CEILING** ≤ 400 changed lines across ≤ 8 files; seconds of wall-clock.

**RISK** **`AH-02` applies with force.** Narrowing the envelope to put `GRAD-02`
out of scope is an automatic discard, not a fix. The envelope is the solver's own
documented claim (`scharfetter_gummel.py`, BUG-11 comment: "The claimed doping
range is 1e21-1e25 m^-3"); the gradient must meet it.

**NOTE** No current published number is affected: the protocol bands are
`train [1e21, 2e22]` (`C_s ≤ 2.0e6`) and `extrap [2e20, 8e22]` (`C_s ≤ 8.0e6`),
roughly two decades below onset. This is a latent defect in exported public API,
and `D1`/`ADR-0004` are **not** confounded by it.

---

## SPEC-g0-5 — the identifiability result always carries its regime

**CLAUSE** Every statement of the identifiable-rank result carries its local/global
label and its regime, in every claim-surface document.

**BASELINE** Measured by a passage-level guard (`local` within ±6 lines of a rank
claim): `README.md` 4 unqualified statements (rows 51, 70, 267, 340),
`docs/RELEASE_READINESS.md` 2 (rows 72, 189), `papers/draft.md` 1 (row 255),
`docs/CLAIM_EVIDENCE_MATRIX.md` 0. Total **7**. `inverse/identifiability.py`
itself is correct throughout ("the **local** Jacobian", "at one operating point").

**TARGET** 0 unqualified statements in every document this loop may edit; the
`papers/**` instance pinned at exactly 1 and escalated, not silently excluded.
`n` = every rank-claim line in the claim surface (full population).

**REGIME** The label must name: local or global, the operating point, the noise
level, the parameterisation dimension, and the observation count (PH-21).

**FALSIFIER** A grep finds one unqualified statement in an editable document; or
the `papers/**` count moves off 1 in either direction.

**GATE** `G-STAT`, `G-DOC`.

**COST CEILING** Documentation only; no compute.

**RISK** Under-labelling invites a local Jacobian rank to be read as global
non-identifiability, which is a materially stronger claim than anything measured.
Over-labelling costs nothing.

---

## SPEC-g0-6 — asserted counts and figures in `README.md` are guarded

**CLAUSE** Every asserted count or figure in `README.md` is either generated or
guarded by a test that fails when it drifts.

**BASELINE** The test-count badge is guarded by
`test_notebooks.py::TestDocumentedTestCountIsHonest`, which collects the suite in a
subprocess and compares. It fired correctly during generation 0 (`badge 240 vs
collected 246`). The built-in-potential and mass-action figures were **unguarded**
and had drifted by 6.6 and 3.4 decades respectively — that is `SCI-08`. Measured
baseline: 1 guarded figure, ≥ 3 unguarded.

**TARGET** Every solver-quality figure in the headline table guarded by a test that
re-measures rather than hard-codes. Direction: 0 unguarded solver-quality figures.

**REGIME** `README.md` headline table and the claim-surface documents it links.

**FALSIFIER** A badge or figure that can drift without a test failing.

**GATE** `G-DOC`, `G-CODE`.

**COST CEILING** Test-only; the guards must stay inside the fast suite (< 5 s
total, so they run on every gate pass rather than being deferred).

**RISK** A guard that hard-codes the expected value converts a documentation defect
into a test that must be edited whenever the solver improves — which is how
`AH-01` violations start. Guards therefore re-measure and compare within a stated
band.

---

## Non-mandatory clause added this generation

## SPEC-g0-7 — duplicate physics is removed, not merely documented

**CLAUSE** The two ohmic boundary-condition implementations are reduced to one
definition, or their equivalence is enforced by a test over the full envelope.

**BASELINE** `solvers/scharfetter_gummel.py::_ohmic_bc` and
`pinn/losses.py::ohmic_boundary_values` are independent implementations of the same
physics — the duplication that caused `BUG-11`. Measured: their **values** agree to
full precision across `C_s = 1e0 … 1e11`; their **gradients** do not (`GRAD-02`).
Seed item `S-3`, open across two audit cycles.

**TARGET** One definition, or a property test asserting agreement of both value and
gradient at `n` ≥ 200 points across `C_s = 1e5 … 1e9`, both signs.

**REGIME** As `SPEC-g0-4`.

**FALSIFIER** A change to one implementation that does not change the other and
that no test catches.

**GATE** `G-PHYS`, `G-CODE`.

**COST CEILING** ≤ 400 changed lines across ≤ 8 files.

**RISK** `SW-02` names duplicate physics a defect class, not a style issue.
Merging carries its own risk: `pinn/` is legacy (`ADR-0004`) while `solvers/` is
the oracle, so a careless merge could couple a legacy path to the reference solver.
`f7` (blast radius) is expected to disfavour the structural option; the fitness
vector decides, not preference.
