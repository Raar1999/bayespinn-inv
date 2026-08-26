# Changelog

All notable changes to this project. Numbers here are measured, and each entry
names the command that reproduces it. Findings are tracked in
[`docs/AUDIT_MASTER.md`](docs/AUDIT_MASTER.md).

## [Unreleased] — close of the audit loop (2026-08-26)

No API changes. The closing ruling permits one arithmetic check over existing
artefacts and no further measurement. This entry is that check, one rule, and
the consequence of a bound direction carried through the claim surface.
`docs/CLOSE_RULING.md`.

**The rank climb is the spectrum flattening, not the head sliding.** Generation
10 killed the localisation mechanism and left the sharper question: why does the
leading observable direction stay put while the ones behind it cross the noise
floor? The answer is decidable from artefacts already on disk. The operational
cutoff is absolute, so the two candidate readings separate by sign alone. Over
the nine bias windows of `rank(observation set)`, `σ₁` moves by a factor of only
1.195 and 1.148 at the two devices and moves **downward** (`spearman` −1.000 and
−0.983) — the wrong direction to raise a count against a fixed cutoff — while
`σ₂`, `σ₃` and `σ₄` rise by ×20.9 to ×535 in the *normalised* spectrum. The
identity `Δlog σᵢ = Δlog σ₁ + Δlog(σᵢ/σ₁)` puts 95.6%–97.9% of each one's motion
in the shape term. The spectrum's log-decay slope halves (−1.265 → −0.552 and
−1.261 → −0.525) and the largest multiplicative gap behind the head collapses
from 230.6× to 4.99× and from 87.8× to 5.11×. Along the spacing axis, where the
rank does not move, the same slope moves 2.1% and 2.8%. Reproduce:
`PYTHONPATH=src python scripts/run_close.py`. **This is a description, not a
test** — the question was asked after the data existed, and no pre-registration
is claimed.

**A control the check failed on its own first draft.** Claiming five singular
values fails `C3` in 4 of 18 cells: `σ₅` sits at or below the estimator's
spectral floor at the widest windows. The claim was narrowed to `σ₁…σ₄` — the
indices the rank is made of, clearing the probe in all 18 cells at a worst
margin of 1.51× — rather than the control being loosened, and the excluded cells
stay named in the artefact.

**`WIT-02` enacted: every witness is refined before it is counted.** `WIT-01`
was ordered against a defect it does not reach — retro-applied it removes
nothing, admissibility ratio 1.000 in all three charts. What predicts refinement
survival is headroom against the floor, and the observed split is 1.4 percentage
points wide, too narrow for a threshold that would not be tuned (`PH-11`). So the
rule is refinement without a threshold, and its live consequence is a measured
register: **chart G 3 of 13, chart L 0 of 37, chart J 13 of 13**. One set of
three is compliant, and the uncovered one carries the dimension reading.
Refining it is new solving and the ruling orders a stop, so the gap is published
rather than closed. Four claim-surface documents quoted a witness count with no
coverage beside it; one said *"all tested pairs survive 4× grid refinement"* of a
set in which three of thirteen pairs had ever been tested.
`outputs/close/wit02_register.json`, `docs/RULES_ENACTED.md`.

**Both basin results are weakened to search statements.** The straight-line
barrier is an **upper** bound — a curved path can only be shallower — and that
direction is asymmetric. It strengthens the chart-G ridge, whose barrier is then
at most at the floor. It weakens chart J at `d=16` (median 468, 59× the floor)
and chart L at `d=16` (median 1696, 212× the floor) to *no connecting path below
the floor was found along the straight line*, which is not a demonstration that
the members are separated. The test that would settle it — a minimum-energy path,
string method or NEB against the same oracle — was **not run**. `AH-13`. The
dimension reading survives: both sides of that comparison are upper bounds.

**`DOC-03a` closed.** The README badge read *"tests-N passing"* while its guard
compared `N` against collection. Generation 10 recorded that the text could not
change without breaking the guard's regex; it could. The badge now reads
*collected*, and the guard asserts the word as well as the integer.

**Three ruling premises ratified**, all corrected and hashed in generation 10:
the `SPEC-g10-2` falsifier was inverted, refinement survival is predicted by
headroom rather than by sub-grid junctions, and `WIT-01` read literally rejects
almost every real witness.

## [Unreleased] — generation 10 of the audit loop (2026-08-26)

No API changes. This generation tests one mechanism and kills it, removes a
confound from the generation-9 geometry result, and enacts a rule that turns out
not to reach the defect it was ordered against.

**The localisation mechanism is falsified.** Generation 9 established that bias
window *width* sets the identifiable rank while spacing does not, and left no
account of why. The cheapest mechanism consistent with that split — the window
selects which transport regimes the current is sensitive to, so the observable
directions should concentrate near the junction at narrow windows and delocalise
at wide ones — was tested under a measure hashed before the first SVD. It fails
at both devices. The leading right singular vector's spatial extent moves by
under 2.5% while the rank climbs from 1 to 4 over the same sweep, and at
`device_p50` it moves monotonically the *wrong* way (`spearman = −1.000`) with its
centroid receding from the junction (`+1.000`). At the generation-8 operating
point the trend against *spacing* (`−0.933`) is stronger than the one against
width (`−0.433`). Reproduce:
`PYTHONPATH=src python scripts/run_g10.py --phases preregister,localisation`.

**The ridge/basin split is a property of the dimension, not the chart.**
Generation 9 compared chart G at `d=4` against chart J at `d=16` — differing in
both chart and dimension — and read the difference as chart-dependence. Barriers
on the 37 chart-L witness pairs at `d=16` make the comparison matched in `d`, and
chart L is a **basin**: not one of its 37 pairs is within the floor barrier, and
its median is 212 floor units against chart J's 58.5. Both `d=16` cells are
basins; the only ridge is `d=4`, and it survives normalisation by path length.
Generation 9's two sets re-measure bit for bit through the same imported
function. Reproduce:
`PYTHONPATH=src python scripts/run_g10.py --phases preregister,ridge_basin`.

**What the chart moves at matched `d` is the depth, not the kind.** Charts L and
J at `d=16` have matched path lengths for both their witness pairs (2.979 against
2.872) and their null controls (3.230 against 3.246), and differ by 13× in
witness-to-null barrier ratio — 0.661 against 0.049. Read as connectivity
relative to ordinary prior pairs the three cells order cleanly across both axes:
1/1100 in chart G at `d=4`, 1/20 in chart J at `d=16`, 1/1.5 in chart L at `d=16`.

**`WIT-01` removes nothing, and that is the result.** Every witness pair in this
repository qualifies on a doping magnitude, and magnitude coordinates reach the
solver grid exactly, so the admissibility ratio is 1.000 in all three charts. The
rule does catch one reported *quantity* — a chart-J pair whose junctions sit
0.425 nm apart on a 3.333 nm grid — which is withdrawn as a junction separation.
Reproduce: `PYTHONPATH=src python scripts/run_g10.py --phases preregister,wit01`.

**The two ends of the validated bias range do not have the same status, and nine
generations wrote them as if they did.** Below 0.15 V the oracle was tested and
found unconverged; above 0.90 V it was never tested, because the convergence
sweep's own upper end *is* 0.9 V. Every bias list in every artefact under
`outputs/` was read to check it — 74 files — and the largest bias any artefact was
ever evaluated at is 0.9 V. The upper boundary is labelled `PH-15` untested rather than treated
as a limit.

### Added

- `scripts/run_g10.py` — the `SPEC-g10-1..3` battery plus `WIT-01`. Pre-registers
  the localisation measure, the ridge/basin decision table and the admissibility
  rule with their hashes before anything is measured, and refuses to run against
  a pre-registration that has moved. Imports the barrier metric from
  `scripts/run_g9.py` rather than restating it, and refuses to run unless the
  criterion hash generation 9 wrote to disk equals the one it recomputes.
- `bayespinn_inv.inverse.witness_admissibility` — `WIT-01` as a hashable rule and
  a predicate, with the reading it takes and the scope it has stated in full.
- `Chart.coordinate_resolution` and `Chart.separation_is_resolved`, plus
  `ChartJ.node_spacing_si` and `ChartJ.junction_node_index` — the representation's
  resolution as a property of the chart. Zero for every magnitude coordinate;
  an exact node-index test for chart J's junction; infinite for a pinned one.
- `identifiability.singular_vector_localisation` — participation ratio, centroid,
  spread and junction distance of a right singular vector, all computed from
  `v_j**2` so the sign gauge cannot enter, with vectors below the identifiable
  rank reported and stamped unreliable rather than mixed in.
- `tests/test_witness_admissibility_g10.py`, `tests/test_localisation_g10.py`,
  `tests/test_loop_state_g10.py`.
- `docs/G10_RESULT.md`, `docs/audit/AUDIT_g10.md`, and the `WIT-01` section of
  `docs/RULES_ENACTED.md`.

### Changed

- Every claim-surface document quoting a witness count now carries its
  admissibility ratio, and a guard fails if one stops doing so.
- `README.md`'s test-suite row pointed at a hand-maintained total that had
  drifted badly; it now points at the badge, which a guard maintains against live
  collection.

### Withdrawn

- *"The geometry of the degeneracy is chart-dependent — a ridge at the instrument
  floor in one chart, isolated basins in another."* The comparison behind it was
  confounded in chart and dimension together. At matched `d=16` both charts are
  basins.
- *"These two devices have junctions 0.425 nm apart and are indistinguishable."*
  The grid node is 3.333 nm; the representation does not carry that difference.

### Fixed

- Five coordinate annotations narrower than every caller, which cost findings
  under the tracked-tree `mypy` scan; now the `Coords` alias `charts.py` already
  used.
- Working-tree line endings on documents and a module edited this session,
  restored to match their blobs (`EOL-01`'s guard caught them).

## [Unreleased] — generation 9 of the audit loop (2026-08-26)

No API changes. This generation is a **replication**, and it falsifies the
headline of the one before it.

**The four-way ordering of what moves the local identifiability spectrum —
observation set, junction, dimension, interpolant — is operating-point
dependent.** Generation 8 measured it at one operating point and recorded, as its
own highest remaining scientific risk, that every cell in it sat there.
Generation 9 measured it at nine further operating points: three devices spanning
the doping prior crossed with three bias windows spanning the observation range,
under a selection rule hashed before the first device was drawn. Five distinct
orderings appear. The generation-8 order is recovered at 2 of 9 points under one
statistic and 0 of 9 under the other, and the two statistics agree at only 2 of
the 12 points measured — they already disagreed at generation 8's own operating
point, which means the published summary never named one object.
Reproduce: `PYTHONPATH=src python scripts/run_g9.py --phases preregister,op_points`.

**What survives is one-against-three.** The observation set's largest movement
spans 0.925–1.080 across all twelve operating points, a factor of 1.17 end to
end, while the junction spans ×26, the dimension ×21 and the interpolant ×39, and
those three trade places depending on the device and the window. *What you
measure* dominates the local spectrum everywhere tested; how you parameterise it
does not have a stable rank at all.

**The generation-7 chart-invariance result is narrowed again.** Chart G against
chart L at matched `d` moves the spectrum by 2.6% at best and by 101.5% at one of
the nine points. At generation 8's own device, merely narrowing the bias window
takes it from 2.8% to 30.7%.

### Added

- `scripts/run_g9.py` — the `SPEC-g9-1..4` battery. Pre-registers the
  operating-point selection rule, the ordering statistic and the barrier
  criterion, writes their SHA-256 hashes before anything is drawn, and refuses to
  measure against a pre-registration that has moved.
  Reproduce: `PYTHONPATH=src python scripts/run_g9.py --phases preregister`.
- `outputs/g9/` — seven artefacts and a manifest recording machinery commit
  `a6728fe` with `dirty = false`.
- `docs/G9_RESULT.md`, `docs/audit/AUDIT_g9.md`, `LOOP_STATE_v6.json`.
- `tests/test_claim_surface_g9.py` — `SPEC-g9-2`'s falsifier, which is about
  prose: a rank fraction may not appear in a passage that does not say what was
  measured, and a document quoting a rank must point at a rank curve. Found 18
  live passages across six documents on its first run.
- `tests/test_lint_scope_g9.py` — asserts `ruff check .` and
  `ruff check src tests scripts` return the same verdict, that the notebook
  ignore block is not a blanket amnesty, and that the scopes do not agree by
  exclusion.
- `tests/test_loop_state_g9.py` — `REP-01` applied forward: every number in the
  state file's baseline block carries the command that produced it, and the
  rerunnable ones are re-run and compared.

### Changed

- `pyproject.toml` — `[tool.ruff.lint.per-file-ignores]` now covers
  `notebooks/*.ipynb`, naming `scripts/build_notebooks.py` as the generator and
  each suppressed code with its reason. Both lint invocations now exit 0 over the
  tracked tree; before this they disagreed, and the state file recorded one of
  the two verdicts with no scope attached.
  Reproduce: `python -m ruff check .` and `python -m ruff check src tests scripts`.
- The support-floor comment in `pyproject.toml` now records 110 files, the
  current scan, with the generation-7 figure of 96 beside it. A larger clean
  static scan is a larger unevidenced surface, not a stronger claim.
- Eighteen passages across `README.md`, `docs/RELEASE_READINESS.md`,
  `docs/CLAIM_EVIDENCE_MATRIX.md`, `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`,
  `docs/CHART_RECONCILIATION_g7.md` and `docs/NOVELTY_AUDIT.md` now carry the
  observation set their rank was measured over. Every one already carried its
  cutoff.
- `docs/OPERATOR_TASKS.md` — `CI-01` is reclassified `ACCEPTED-PERMANENT` by the
  default the generation-8 ruling set, after three cycles without a decision. The
  task stands, the reversion condition is written down, and the cost statement is
  in `docs/G9_RESULT.md` §1.4.
- `docs/G8_RESULT.md` carries a pointer block naming what generation 9 moved. Its
  body is unchanged: it is what was measured at that operating point.

### Fixed

- Nothing in the library. Two bookkeeping defects in the loop's own records: a
  promoted figure that carried no invocation and could not be re-derived
  (`AUDIT_g9` §1.1), and a baseline whose stated scope was wrong — `25` is
  `mypy src` over 44 files, not the tracked tree, which gives 150 over 112
  (`AUDIT_g9` §1.2).

### Measured, and not to be quoted without their conditions

- The chart-J witness count of 13 does not survive grid refinement: **7 of 13**
  pairs stay below the 2.0e-02 floor at `N = 301/601/1201` and
  `tol_carrier = 1e-12`. The 694 nm / 271 nm headline pair does survive, its
  distance falling 1.7%.
  Reproduce: `PYTHONPATH=src python scripts/run_g9.py --phases junction_refine`.
- A local rank is a curve in the observation set as well as in the cutoff: at the
  generation-8 device in chart G at `d = 16`, the identifiable count at a 2%
  cutoff runs from 1 to 4 as the bias window widens from 0.10 V to 0.75 V about a
  fixed 0.525 V centre, and does not move at all as spacing runs from linear to
  geometric over a fixed 0.15–0.90 V window.
  Reproduce: `PYTHONPATH=src python scripts/run_g9.py --phases rank_obs`.
- The chart-G witness pairs are a ridge, not two isolated points: median
  likelihood barrier 8.31 log-units against a floor barrier of 8.0, against a
  null control whose minimum is 339.
  Reproduce: `PYTHONPATH=src python scripts/run_g9.py --phases basins`.

---

## [Superseded] — generation 8 of the audit loop (2026-08-26)

Generations 1–7 are recorded in `docs/gen/` and `docs/audit/` rather than here;
this entry resumes the changelog because generation 8 changes a solver contract
that anything depending on this package will notice.

**Breaking, deliberately.** `ScharfetterGummel1D.solve` no longer interpolates a
doping array onto its own grid. Four lines of convenience had been selecting a
**parameterisation chart** from an array length, in a solver that never mentions
charts, and six generations of identifiability results were published in that
chart without recording it (`CHART-01`). A census taken by patching `solve` and
running the suite found the implicit reconstruction load-bearing at five call
sites in `src/` and nine in `tests/`, across three grid resolutions — including
the Jacobian that produced the published local rank, and the generator that
produced the surrogate's entire training set.

Callers now pass grid values, or a `ChartedDoping` that carries the chart it is a
vector in, or get `DopingChartError`. Nothing about the numbers changed: 24
profiles captured from the old code path before deletion reproduce byte for byte
(`tests/data/chart_l_resampler_golden_g8.json`), and both the generation-6 and
generation-7 witness searches reproduce their witness counts exactly.
Reproduce: `PYTHONPATH=src python -m pytest tests/test_one_reconstruction_g8.py`.

### Added

- `bayespinn_inv.inverse.charts.ChartJ` — a third parameterisation with the
  junction position as a free continuous coordinate. At `s = 0` it is `ChartG` at
  `d-1` bit for bit, which is its positive control; `junction_scale` exposes the
  mixed-unit problem in its Jacobian rather than hiding it.
  Reproduce: `PYTHONPATH=src python -m pytest tests/test_charts_g8.py`.
- `bayespinn_inv.inverse.charts.ChartedDoping`, `anchor_signed_to_grid`,
  `regrid_signed` — the chart-carrying type and the two named forms of the one
  reconstruction operator.
- `bayespinn_inv.inverse.identifiability.rank_cutoff_record` — reports a rank as
  a curve over cutoffs with the spectrum, the largest multiplicative gap and
  whether the operational cutoff falls inside it (`SPEC-11`).
- `bayespinn_inv.inverse.modes` — basin counting by profile distance against a
  criterion that hashes itself before clustering (`AH-14`), with the count
  reported as a curve over thresholds and stated as a lower bound, plus
  `barrier_depth` as the check on the parameter-space proxy.
- `scripts/run_g8.py` and the artefacts under `outputs/g8/`.
- `docs/G8_RESULT.md`, `docs/audit/AUDIT_g8.md`, `LOOP_STATE_v5.json`.
- Guards: `tests/test_one_reconstruction_g8.py`, `tests/test_charts_g8.py`,
  `tests/test_modes_g8.py`, `tests/test_rank_curve_g8.py`,
  `tests/test_rep01_g8.py`, `tests/test_rules_enacted_g8.py`,
  `tests/test_loop_state_g8.py`.

### Changed

- `docs/RULES_ENACTED.md` gains `REP-01`, `SPEC-11`'s rank-curve rule, `OPS-01`
  and a **marked-as-reconstructed** `PH-22`, each with a guard and both
  controls. `tests/test_rules_enacted_g8.py` asserts that transitively: a rule
  whose guard does not exist, or whose guard ships no controls, fails the suite.
- The claim surface learns about a third chart, and `docs/G8_RESULT.md` joins it.
- `docs/OPERATOR_TASKS.md` OT-1 now states that a remote must be added before the
  command block can run, and no longer asserts an expected test count.
- `README.md` retires *the dimension moves the rank and the chart does not* to
  the interpolant family it was measured in, and states the multimodality result
  as the headline it is.

### Fixed

- **`DOC-07`'s guard was too narrow to catch the commit that enacted `OPS-01`.**
  The generation-8 machinery commit asserts a measured count of this tree that
  the census contradicts, spelled out in words, and the guard matched only digits
  beside "passed"/"tests". Under `R-4` the message stands; the guard is widened
  to catch a cardinal — digit or word — in front of a noun naming something a run
  counts, with that commit as its positive control.
  Reproduce: `PYTHONPATH=src python -m pytest tests/test_commit_messages_g7.py`.
- **`EOL-01` amended.** Writing with `newline=''` is only half the rule: reading a
  CRLF file in text mode normalises too, so a read-modify-write round trip
  rewrites the whole file even when the write is careful. Generation 8 did that
  to 20 tracked files; `tests/test_line_endings_g6.py` caught it before the
  commit, which is what the guard is for.

## [Unreleased] — generation 0 of the audit loop (2026-08-25)

An adversarial audit loop was run over the repository. Its first finding was that
**the repository's only commit was the pre-audit project**: both audit cycles —
6 of 40 source modules, 204 of 246 collected tests, 7 experiment launchers, the CI
workflow and the entire audit corpus — existed only as uncommitted working-tree
state. `git archive 6577f4b` and re-running the physics gives `SGConfig` with no
`equilibrate` option, a built-in-potential relative error of `2.7558e-07` against
the working tree's `7.243e-14`, and a mass-action residual of `6.1019e-03` against
`2.934e-09`. Every manifest in `outputs/` named that commit as its provenance.

### Added

- **Adoption commit `c115757`** on branch `loop/champion`, parent `6577f4b`
  (untouched). Before any git operation the tree was copied to two paths outside
  the repository and both verified 212/212 against
  `PRESERVE_MANIFEST_g0.sha256` (digest-of-digests
  `9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd`). The commit
  was then attested by extracting it and digest-comparing: **164/164 byte-identical,
  0 mismatched, 0 missing.**
- `outputs/` is now tracked — all 42 files including every `manifest.json`, so a
  clone ships the evidence with the claims (`PROV-01`).
- `git_status_counts()` and `git_tree_digest()` in `utils.provenance`
  (`ADR-0006`), and an optional `repo` argument on all four git helpers so the
  behaviour can be tested against a controlled repository.
- `docs/PROVENANCE_BIFURCATION_g0.md` — per-manifest record of which commit each
  result claims, why `6577f4b` cannot have produced it, and whether the numbers
  reproduce. Existing manifests are **not** edited.
- `docs/audit/AUDIT_g0.md`, `docs/spec/SPEC_g0.md`, `docs/gen/DECISIONS.md`.
- 34 regression tests across `tests/test_provenance_g0.py`,
  `tests/test_claim_surface_g0.py`, `tests/test_ohmic_gradient_g0.py`.

### Fixed

- **PROV-02 (CRITICAL) — dirty detection was blind to untracked files.**
  `git_is_dirty()` ran `git status --porcelain --untracked-files=no`. Measured on
  a scratch repository, a tree missing three source modules returned `False`. A
  manifest could therefore report a tree missing six source modules and 83% of the
  test suite as clean, indistinguishable from a fixed typo. Untracked files now
  count; `tracked_modified`, `untracked` and `tree_digest` are recorded as separate
  manifest fields; the flag is derived from the counts so the two cannot disagree.
  Digest cost measured at 28 ms over 166 files / 4.1 MB.
  Reproduce: `pytest tests/test_provenance_g0.py` (16 tests).

### Changed — claims corrected or withdrawn

- **Built-in potential `2.8e-7` → `7.24e-14` (withdrawn, not corrected).** The
  published figure measured the *pre-audit* solver: `git archive 6577f4b` and
  re-running reproduces `2.7558e-07` exactly. It described a program the project
  no longer ships. `CLAIM_EVIDENCE_MATRIX` X15.
- **Mass action `7.6e-6` → `2.93e-9`**, same cause. X16.
- **Equilibration gain `1.32e-2 → 7.62e-6` (1730×) → `6.77e-3 → 9.7e-10` (7.0e6×).**
  The starting point was sound (1.95× from measured); the endpoint understated the
  improvement by ~4000×. X17.
- **`RELEASE_READINESS` "Reference solver validated ✅"** cited exactly the two
  withdrawn figures. The gate was green on evidence from a superseded program.
- **Identifiability is now labelled `local` wherever it is stated** (README rows
  51, 70, 267, 340; `RELEASE_READINESS` 72, 189), with its operating point, noise
  level, parameterisation dimension and observation count (PH-21). Global,
  sampling-based non-identifiability remains **unmeasured**. X18.
  One instance in `papers/draft.md:255` is **parked**, not fixed — that path is
  operator-protected; it is pinned by a test that fails if the count moves in
  either direction.

### Verified — no change required

- A full re-run of `scripts/run_results.py` (2500 epochs, M=5, no `--quick`)
  reproduced **all 174 numeric leaves bit-identically**: C1 interpolation
  `0.027834281028660313`, C2 extrapolation `0.3818233071446869`, C3 family
  transfer `0.8423089146208244`, C4 `9.961050987243652` decades. The headline
  science is exactly reproducible; only its provenance chain was broken.
- `outputs/results/manifest.json` agrees with its `results.json` on all 102 shared
  numeric leaves — 0 mismatches. Nothing was fabricated.

### Fixed — GRAD-02 / GRAD-03, promoted candidate g0c2

- **`ohmic_boundary_values` returned NaN gradients across the documented doping
  envelope.** `torch.where` evaluates both branches; for large positive `C_s`,
  `-C + sqrt(C²+4)` underflows to exactly `0.0`, the discarded branch is `inf`,
  and backward computes `0 × inf = NaN` in the *selected* branch. Bisected onset
  `C_s = 1.3922e8` (N = 1.3922e24 m⁻³) in float64 — the top **21.4%** of the
  solver's own 1e21–1e25 m⁻³ range.

  The generation-0 **falsifier** then broke that scoping: networks here train in
  float32, where cancellation arrives at `C_s = 7.079e3` — *below* the envelope.
  Sampling the envelope in float32, **41 of 41** points returned NaN. 100%, not
  21.4%. Filed as GRAD-03.

  Fixed by reformulation (`M-01`): `log n = asinh(C/2)`, `log p = −asinh(C/2)`.
  Branchless, exact in every dtype, derivative `1/sqrt(4+C²)` finite everywhere.
  Measured after the fix, over 402 envelope points in both dtypes:

  | | before | after |
  |---|---|---|
  | non-finite gradients, float64 | 44 / 402 | **0** |
  | non-finite gradients, float32 | 201 / 402 | **0** |
  | gradient rel. error, float64 | 4.393e-16 | **0.000e+00** |
  | gradient rel. error, float32 | 1.629e-07 | **8.190e-08** |
  | mass-action deviation | 3.664e-15 | **2.220e-16** |

  **No published number changes.** Measured, not inferred: `losses.boundary_residuals`
  receives boundary doping as data with no `requires_grad_` (`trainer.py:262`), so a
  float32 PINN backward at N = 1e21, 1e24 and 1e25 m⁻³ produced non-finite gradients
  in **0 of 26** weight tensors. `D1` and `ADR-0004` are **not** confounded. The
  defect fired only where doping itself carries a gradient — inverse design, and the
  Jacobian the identifiability result is built on.

  Reproduce: `pytest tests/test_ohmic_gradient_g0.py` (41 tests).
  AH-08 pre-fix outcome recorded: 17 failed / 22 passed.
  Three competing candidates were built and measured; see `docs/gen/CANDIDATES_g0.md`.

### Known open
- **CI-01 reopened** — `.github/workflows/ci.yml` had never been committed, so CI
  has never run, yet `AUDIT_MASTER` recorded the finding as VERIFIED.
- **PROV-03 (permanent)** — the adopted tree has no attestable origin. Nothing in
  git records who produced this code or against what evidence. This does not close.

## [Unreleased] — second audit cycle (2026-08-19)

The first audit cycle closed 40 findings and left the project at "release
ready with documented limitations", with three areas explicitly not
release-grade. This cycle re-ran the evidence instead of inheriting it. It
found one CRITICAL solver defect that had survived the first cycle's 161-test
suite, closed all three not-release-grade areas, and produced four new
measured results — three of them negative.

### Fixed

- **BUG-13 (CRITICAL) — round-off stagnation was reported as divergence,
  which silently aborted bias continuation.** The Gummel carrier-convergence
  test was *relative*, applied to an array spanning 16 decades; entries far
  below the array maximum can never reach a 1e-8 relative tolerance, so the
  solver reported failure on states whose potential had converged to 1e-12.
  Because `auto_continuation` breaks on the first ramp step that reports
  failure, `solve()` then returned the **cold-start** state — currents wrong
  by 3–5 orders of magnitude at 1e24–1e25 m⁻³, and **wrong in sign** under
  reverse bias. Fixed by distinguishing round-off stagnation from divergence
  using a threshold that separates the two measured populations by *eleven
  orders of magnitude* (so it is not tuned — any value in [1e5, 1e13] gives an
  identical verdict). After the fix, 90/90 solves converge across doping
  1e21–1e25 m⁻³ × N ∈ {201,401,801} × bias ∈ {0, 0.3, 0.6, 0.9, −2, −5} V, and
  every point the oracle certifies is grid-converged to ≤0.35%.
  *This did not change any published number* — the headline experiment's
  envelope (doping ≤ 8e22, bias ≤ 0.6 V) sits outside the affected band, and
  H1/H3/H5 are bit-identical before and after.
- **BUG-14 — all text I/O used the platform default encoding.**
  `scripts/build_notebooks.py` could not run at all on Windows (it died on the
  first `φ` and truncated the notebook it was writing), so "regenerate the
  notebooks" was an impossible procedure on the platform the project's own
  manifests record. Swept and fixed across 15 files: 24 `open(..., mode)`
  calls, 10 `open(path)` calls (the form the first sweep missed), 2
  `read_text()`, 1 `write_text()`.
- **`current_is_trustworthy()` ignored the convergence flag.** At +100 V a
  non-converged state carrying `I = 3.0e10 A/m²` had a high SNR and was
  reported trustworthy. Every in-tree caller already wrote
  `converged and current_is_trustworthy()`, so folding the check in cannot
  loosen any result — it removes a footgun for callers who did not.
- `make check-install` hard-coded the POSIX `venv/bin/` path and could not run
  on Windows.

### Added

- `bayespinn_inv.bayesian.surrogate_uq` — `MCDropoutSurrogate` and
  `SWAGSurrogate` over the **surrogate**. The reason MC-dropout and SWAG had
  never been benchmarked is that both wrapped `ForwardPINN`, the superseded
  forward model. All three backends now return the same `SurrogatePrediction`.
- `bayespinn_inv.data.splits` — the single definition of the experimental
  protocol (five disjoint level splits, SG label generation, trust filtering),
  so `run_results.py` and every new experiment build data one way.
- `bayespinn_inv.active_learning.design` — D-optimal, E-optimal and
  null-space experiment design. Textbook criteria (Fedorov 1972; Atkinson &
  Donev 1992); **no novelty claimed**.
- Six new experiments, each writing a provenance manifest:
  `run_uq_benchmark.py`, `run_uq_tuning.py`, `run_experiment_design.py`,
  `run_gradient_fidelity.py`, `run_identifiability_robustness.py`,
  `run_pinn_vs_surrogate.py`. All wired into the `Makefile`.
- **79 new tests** (161 → 240), including regression coverage for BUG-13,
  BUG-14, the trust-flag fix, the UQ backend interface contract, split
  leakage invariants, the design criteria against analytically-known answers,
  and a GaAs PN junction.
- CI now runs a **Windows** job (BUG-14 was Windows-only and a Linux-only
  matrix could not see it), lints `scripts/`, and smoke-runs the notebook
  generator.
- `ADR-0004` (the PINN is legacy), `ADR-0005` (the ensemble is the UQ
  backend).

### Measured — new results

- **GRAD-01: surrogate accuracy does not imply surrogate gradients.** A
  surrogate that fits I–V to 2.6% median relative error has directional
  derivatives agreeing with the SG Jacobian **only inside the identifiable
  subspace**: mean cosine **+0.504 inside vs −0.001 outside**, across four
  device families. A 33× increase in training budget cuts the value error 4.5×
  and leaves the outside-subspace agreement at zero — so this is ill-posedness,
  not undertraining. `make gradient-fidelity`
- **DES-01: uncertainty-driven acquisition is *worse* than random.** Over 4
  device families × 5 budgets × 12 seeds, scored on identifiable rank:
  `max_std` **−0.31** (2 wins / 9 losses), `d_optimal` and `null_space`
  **+0.39** (5 wins / **0 losses**). Supersedes the earlier "no
  distinguishable advantage" framing. `make experiment-design`
- **UQ-01: the deep ensemble wins after a fair hyperparameter search.** σ
  inflates **21.3×** off-distribution against a 12.1× error inflation; tuned
  MC-dropout manages 1.4× and tuned SWAG 2.5× against ~12–13×. A
  budget-matched ensemble, trained *faster* than either, still beats both.
  `make uq-benchmark`, `make uq-tuning`
- **PINN-01: the pure-physics PINN predicts essentially zero current** —
  100.00% median *and* p90 relative error at 27× the surrogate's training
  cost, while its own self-consistency diagnostic reads 0.03. Converged, and
  wrong. `make pinn-vs-surrogate`
- **IDENT-02: the identifiability result survives, and the rank does not grow
  with the parameterisation.** 88 measurements across six axes plus a
  bootstrap: rank 1–6, median 3; **3–4** at the reference conditions.
  P = 8 → 32 leaves it at 3–4, so it is a property of the measurement rather
  than of the discretisation. `make identifiability-robustness`

### Changed

- **The headline identifiability claim is corrected from "3–5 of 16" to "3–4
  of 16" (reference conditions), with the full range 1–6 (median 3) reported.**
  The previous value came from a single run against the pre-BUG-13 solver.
- All twelve notebooks regenerated and **re-executed**; the stale narrative
  numbers ("13 orders of magnitude", "~4% error", "~500× speed") corrected *in
  the generator*, so they cannot drift back.
- The project no longer describes its forward model as a PINN. See ADR-0004.
- `docs/architecture.md` carries a banner saying which packages are legacy.

### Known limitations

See [`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md). The largest open
scientific risk is unchanged: the identifiability analysis is **local** (a
Jacobian at an operating point); global, sampling-based non-identifiability is
not addressed.

---

## [0.1.0-dev] — first audit cycle

40 findings; 12 numbered solver defects, six CRITICAL, all present while the
pre-existing 42-test suite passed. Two documented "physics limitations" turned
out to be solver bugs. See `docs/AUDIT_MASTER.md` §1–6c.
