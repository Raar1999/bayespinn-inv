# BayesPINN-Inv: A Validated Drift–Diffusion Reference Solver and a Measured Identifiability Analysis for Inverse Semiconductor Design

**Target venue.** ML4PS-style workshop (reproducibility / negative-results track).

> **Revision note.** This draft was rewritten after a full adversarial audit of
> the codebase (`docs/AUDIT_MASTER.md`). The previous version presented a
> pure-physics PINN as the forward model — which `docs/forward_model_reframe.md`
> documents does not reproduce diode I–V — claimed first-ness without a
> prior-art review, and left `X`/`Y`/`Z` placeholders in the abstract. Those
> claims are withdrawn; see `docs/adr/ADR-0003-scope-of-the-research-claim.md`.

## Abstract

We present an audited, reproducible pipeline for inverse semiconductor doping
recovery from terminal current–voltage measurements, and use it to put numbers
on four things this area usually states qualitatively.

First, our Scharfetter–Gummel reference solver **reports its own numerical
trustworthy range**. Because `div(J_n + J_p) = 0` holds exactly in steady state,
the face-to-face spread of the total current is an assumption-free estimate of
the numerical error on the terminal current; we show this estimate is
*predictive*, tracking the solver's actual relative precision as `1/SNR` across
five decades.

Second, we measure the **local identifiability** of the doping profile from an
I–V sweep by taking the SVD of the forward Jacobian computed through that
solver. In **chart L** at `d=16` — 16 log-doping anchors, the parameterisation
this project uses — a 19-point forward-bias sweep over an 0–0.9 V observation
window at 2% relative measurement noise determines only **3–4 of 16** profile
degrees of freedom, for four device families (1–6, median 3, across 88
measurements spanning six robustness axes; the rank does not grow with the
parameterisation dimension). Improving the instrument by four orders of
magnitude roughly doubles it — the limit is the structure of the forward map,
not the noise — and we exhibit concrete *equivalence twins*: devices differing
by up to 1.26× in local doping whose I–V curves differ by 0.02–1.3%.

Third, that number is **a property of the measurement and not of the device**.
The observation set is the only one of four candidate sensitivities that is
large at all twelve operating points tested — ×1.17 end to end, against ×21–×39
for junction position, parameterisation dimension and interpolant, which permute
freely among themselves. Bias-window *width* sets the local rank in chart L at
`d=16` — 1 to 4 and 2 to 4 at two devices, at 2% noise, as the window widens
about a fixed centre — while the same number of points spaced differently
leaves it unmoved. The climb is the spectrum **flattening**, not the leading
direction broadening: `σ₁` moves by only ×1.148–1.195 and moves *downward*,
with 95.6%–97.9% of each trailing value's motion in the shape term. **Why it
flattens is open.** Three pre-registered methods failed to answer it and we
report the failure mechanism of each rather than a plausible story.

The degeneracy is also **global**, which no local analysis can detect.
Searches in **chart G** at `d=4` and in **chart J** and **chart L** at `d=16`
return witness pairs — profiles up to **8.18×** and **14.75×** apart in doping
whose I–V curves differ by about 1%, below the noise floor — and every one is
refined before it is counted (`WIT-02`), which costs all three sets members.
Their geometry depends on the dimension rather than the chart, and the `d=16`
results are **searches that found no connecting path below the floor along a
straight line**, not separation proofs.

Finally — and this is the observation that ties the pipeline together — the
identifiability spectrum **predicts where the learned surrogate's gradients can
be trusted**. A surrogate that reproduces I–V to 2.6% median relative error has
directional derivatives that agree with the reference solver only *inside* the
identifiable subspace (mean cosine +0.50) and are uncorrelated with it outside
(−0.00). A 33× increase in training budget cuts the value error 4.5× and leaves
the outside-subspace agreement at zero, excluding undertraining: there is no
signal to learn there. Since those derivatives are exactly what gradient-based
inverse design and Jacobian-based experiment design consume, "the surrogate is
accurate" and "the surrogate's gradients are usable" are different claims, and
the spectrum says which directions the second one covers.

Along the way, auditing the pipeline against these criteria uncovered fourteen
defects in its first two cycles, seven of which were critical and all of which
were present while the test suite of the day passed; two documented "physics
limitations" turned out to be solver bugs. Fourteen further audit generations
followed, and their most transferable output is not the defect list but the
habit: several of the claims above are weaker than the versions we first wrote,
and each was weakened by a falsifier we had registered against ourselves before
running it. In this problem class a plausible-looking result and a correct one
are hard to tell apart without invariants the code is forced to satisfy, and
harder still without a written-down statement, made in advance, of what would
count as being wrong.

**We claim no new method.** Every component is standard, and inverse doping
recovery is a mature field. The contribution is validation, measurement and
reproducibility.

## 1. Introduction

TCAD simulation is accurate but slow; terminal characterization underconstrains
device structure. Bayesian inverse design promises "what doping produced this
I–V, and how sure are we?" — but the value of the uncertainty depends entirely
on whether the forward model, the oracle that supervises it, and the evaluation
protocol are correct.

**Contributions.**

1. A Scharfetter–Gummel 1D drift–diffusion solver with an *honest* convergence
   contract: equilibrated continuity solves (1730× improvement in the
   equilibrium mass-action law), a convergence test on carriers rather than the
   potential alone, and a per-solve numerical error bar on the terminal
   current with a demonstrated predictive relationship to the solver's actual
   precision.
2. A quantitative local-identifiability analysis of the I–V → doping map,
   self-limited by its own estimated noise floor and validated against
   independent re-solves — together with the measurement that the resulting
   rank is a property of the *(device, observation set)* pair rather than of
   the device, and that the observation-set half of it is a curve.
3. Witness pairs establishing that the degeneracy is **global** as well as
   local — found in **chart G** at `d=4` and in **chart J** and **chart L** at
   `d=16` — each refined before it is counted, with their barrier geometry
   reported in the search form the measurement actually supports.
4. An evaluation protocol with disjoint interpolation / extrapolation /
   family-transfer splits, labels filtered by the oracle's trust flag, and `n`
   and confidence intervals on every reported statistic.
5. A negative result: uncertainty-driven bias acquisition does not beat random
   selection on this task at any measured budget.
6. A full audit ledger with a regression test for every defect, and an open
   question — why the spectrum flattens — left open, with the three methods
   that failed to close it characterised.

## 2. Background

### 2.1 Drift–diffusion

Steady-state PDD in SI units with `E = -∇φ`:
$$\nabla\!\cdot(\varepsilon\nabla\phi)=-q(p-n+C),\quad \nabla\!\cdot J_n = qR,\quad \nabla\!\cdot J_p = -qR$$
with $J_n=q\mu_n(nE + V_T\nabla n)$, $J_p=q\mu_p(pE - V_T\nabla p)$, SRH
recombination and ohmic Dirichlet contacts. De Mari scaling throughout.

### 2.2 Prior work on inverse doping

Identification of doping profiles in the stationary drift–diffusion system, its
identifiability and its ill-posedness, are established results
(Burger, Engl, Leitão & Markowich, *Inverse Problems* **17**, 1765, 2001;
*Milan J. Math.* **72**, 273, 2004). Bayesian inversion for this exact problem
(arXiv:2408.11485) and ML surrogates for doping reconstruction (2024) both
exist. Inverse device modelling for doping extraction dates to *Solid-State
Electronics* (1990–91). We add measurement, not method.

### 2.3 Forward model

The terminal current is directly supervised from the SG oracle rather than
derived from PINN field gradients. In a log-density formulation
$J_n=\mu n_s(\nabla\log n-\nabla\phi)$, the bracket is near zero while $n_s$
reaches $10^6$ in scaled bulk units, so the continuity loss is dominated by the
bulk and the diode signal stays in the numerical noise. This is precisely the
multiscale cancellation SG exponential fitting was invented to handle.

## 3. Method

### 3.1 An oracle that reports its trustworthy range

Two invariants make the solver self-checking:

- **Convergence.** The potential is nearly insensitive to minority carriers, so
  a `max|Δφ|` test declares success on states whose continuity residual equals
  the entire current scale. We require the relative carrier update to converge
  as well.
- **Error bar.** `div(J_n+J_p)=0` exactly ⇒ `J_total` is constant in space; its
  observed spread is `current_noise_floor`.

The second is not merely descriptive. Measured on a 1 µm Si diode, the relative
precision of the terminal current under a small input perturbation tracks
`1/SNR` with `SNR = |I|/current_noise_floor` across five decades — so the
diagnostic can be used *a priori* to choose finite-difference steps and to
reject data.

### 3.2 Identifiability

We analyse the SVD of
$J = \partial\,\mathrm{symlog}\,I(V_b)/\partial\log_{10}|C_i|$, computed by
central differences through the SG solver, so the result characterises the
physics rather than a trained surrogate. Singular values give the forward gain
per decade of doping; comparing against the measurement noise gives an
identifiable rank; the trailing right singular vectors are the profile changes
the measurement cannot see.

**A rank is measured in a chart, at a dimension, over an observation set.**
"The identifiable rank" is not well defined until three things are fixed: the
parameterisation (which we call a *chart*), its dimension `d`, and the set of
biases measured. Chart L at `d=16` places log-doping anchors on the grid and
interpolates the signed doping arithmetically; chart G at `d=4` and chart J at
`d=16` are the two used for the global search of §4.3. Numbers from different
charts are over different manifolds and are not comparable term by term; where
we put two beside each other we say what licenses it.

**Inherited obstructions are re-tested, not carried.** One habit is worth a
sentence in the methods because it changed results. Where an earlier round of
this work recorded that something could not be done, later rounds re-tested the
obstruction rather than inheriting it — and at least one turned out to be false
on the first attempt, having never been tried. An obstruction inherited from an
earlier round is a claim about the code, exactly as checkable as any other, and
we found they were not being checked.

**The analysis is self-limiting.** A Jacobian estimated with per-entry noise
$\eta$ has, by Weyl's inequality, no resolvable singular value below
$\eta\sqrt{BP}$. We estimate $\eta$ from the oracle's own reported noise floor
and report anything below the induced spectral floor as unresolvable.

This matters: our *first* version of this analysis used a 1e-3-decade step and
accepted any bias point with SNR > 10. It produced a clean spectrum decaying
over six orders of magnitude and an identifiable rank of 6. It was entirely
noise — an independent re-solve showed the measured response along the *exact
null space* was the same size as along the most observable direction. An SVD
will always return a plausible spectrum, including from pure noise.

## 4. Experiments

### 4.1 Local identifiability (main result)

Chart L at `d=16`: a 19-point forward-bias observation window (0–0.9 V), 16
profile nodes, 2% relative measurement noise, Jacobian through the SG solver.
The prior is the chart's own uniform prior over log-doping anchors; the noise
model is relative Gaussian on the terminal current; the distinguishability
floor is the solver's reported `current_noise_floor` and the discretisation
floor is 1.5e-3 log-units.

| Device (chart L, `d=16`, local) | Bias points used | Identifiable dof (of 16) |
|---|---:|---:|
| step, symmetric (1e22 / 1e22 m⁻³) | 10 | **4** |
| step, asymmetric (1e21 / 5e22) | 11 | **5** |
| graded (tanh, $L_g$ = 150 nm) | 10 | **3** |
| LDD (three-segment) | 8 | **4** |

*Validation.* Predicted response $\|Jv\|$ vs an independent re-solve: ratios
**0.995–1.04** for all resolved directions across all four families. Conclusion
stable across finite-difference steps (0.01–0.05 decades) and SNR thresholds
(1e4–1e8): identifiable rank 4, $\sigma_1/\sigma_2 = 6.11$–6.13.

*Rank vs instrument quality* (symmetric step, chart L, `d=16`, local): 2 dof at
20% noise, 4 at 2%, 6 at 0.1%, 9 at 1e-4%. Four orders of magnitude of
instrument improvement buys roughly a doubling. The rank is a **threshold
count** at this denominator, not a boundary between two populations of singular
values, which is why every figure here travels with the noise level that set
it; §4.2 shows the gap that would license a bare integer collapsing from 230.6×
to 4.99× as the window widens.

*Equivalence twins.* For every family, a profile differing by up to 1.26×
locally changes the I–V by 0.02–1.3% — below a 2% noise floor. Two physically
distinct devices, one measurement.

### 4.2 The rank is a property of the measurement, not of the device

The number in §4.1 is a property of a *pair* — the device and the observation
set — and the observation-set half is a curve rather than a constant. Two
measurements make that concrete, both in **chart L** at `d=16` and both at 2%
relative noise.

**The observation set dominates three other candidate sensitivities.** We
compared four axes — which biases are measured, where the junction sits, the
parameterisation dimension, and the interpolant family — at twelve operating
points (three devices × three bias windows, plus the reference point). Only one
is large at all twelve. The observation set's effect spans **0.925–1.080** from
end to end, a factor of **1.17**; junction position spans ×26, dimension ×21 and
interpolant ×39. So the picture is not a four-way ordering but
**one-against-three**: at 12 of 12 operating points tested, what you measure
dominates the local spectrum, while the other three trade places among
themselves depending on the device and the window.

This was pre-registered the other way round. Generation 8 of the audit reported a
*ranking* of the four axes from a single operating point; `SPEC-g9-1` registered
the falsifier that the ranking must reproduce at further points, and it fired —
**2 of 12** points reproduce the original order under one statistic and **0 of
12** under the other. The surviving claim is the weaker and more useful one
above. We report it this way because the stronger version was ours.

**Bias-window *width* sets the rank; spacing does not.** Over 16 bias points at
2% noise in chart L at `d=16`, widening the window from 0.10 V to 0.75 V about a
fixed 0.525 V centre takes the identifiable count from **1 to 4** at one device
and **2 to 4** at a second. Redistributing the same number of points at a
different spacing moves the log-decay slope by **2.1% and 2.8%** at those two
devices, against **56% and 58%** along the width axis, and moves the rank not at
all (`rank(observation set)`, `outputs/g9/rank_obs.json`).

**The climb is the spectrum flattening, not the leading direction broadening.**
The identifiable count is the number of singular values above an *absolute*
cutoff fixed by the noise, so a rigid spectrum sliding upward would also raise
it. That is not what happens. Across the widths `σ₁` moves by a factor of only
1.148–1.195 and moves **downward**, which is the wrong direction to raise a count
against a fixed cutoff, while `σ₂…σ₄` rise by ×21–×535 in the normalised
spectrum. Decomposing each trailing value's motion into a scale term and a shape
term puts **95.6%–97.9%** of it in the shape term, at every device and every
index. Nor is it the leading right singular vector broadening to cover more of
the profile: `v₁`'s spatial extent moves under 2.5% on a 0.0625–1.000 scale, and
where it moves at all it *recedes* from the junction.

**Why the spectrum flattens is open, and we say so rather than supplying a
plausible story.** Three methods were tried across four generations of the audit,
each pre-registered before it ran, and none answered it:

1. *Spatial localisation of the singular vectors.* Falsified — the vectors
   localise **more** as the window widens, the opposite of the prediction,
   tracking width at −0.433.
2. *The row side — which bias rows carry the trailing directions.* Falsified out
   of sample. The statistic is confounded with the split ratio `b = n_out/n_rows`
   and the two axes being contrasted do not overlap in it: `corr(dz, b)` runs
   −0.95 to −0.98, and the device-to-device offset spread is 1.572 against a
   largest axis difference of 0.22 at matched `b`.
3. *Row-subset growth against a random-row null matched on row count.*
   Inconclusive, for a reason worth stating exactly. The pre-registered decision
   rule returned its deflationary label, but the registered *meaning* of that
   label — that the nested windows track the null — is contradicted by the
   measurement that produced it: all four devices sit **above** the chain null in
   the same direction, three at *p* ≤ 0.005, consistently *less* flat than random
   row-subsets of equal size. Neither registered outcome describes what happened,
   and relabelling after reading the result is not available.

Characterising that third result narrows the question without closing it. The
departure from the null tracks the *spread* of the biases in the subset —
`corr(gap, spread)` of −0.31, −0.59, −0.49, −0.45 — which is a smoothness
property of any smooth response rather than a property of a device or a transport
regime. Regressing the spread out leaves a residual at the 0.880 and 0.892
percentiles at two contrast devices, but **0.492 — exactly ordinary — at one
held-out device against 0.947 at the other**. The two held-out devices disagree,
so the part of the departure that is not generic smoothness does not reproduce.

The paragraph we are willing to put our name to is therefore this one:

> The rank climb is spectrum flattening rather than the leading direction
> broadening. The flattening exceeds what row count alone produces — nested
> windows are consistently *less* flat than random row-subsets of equal size —
> but the excess is largely attributable to the spread of the biases in the
> window, a smoothness property, and the residual after removing it does not
> reproduce across held-out devices. **The mechanism remains open.**

One hypothesis survives and we name it as future work without claiming it.
Contiguous bias windows have more collinear Jacobian rows than scattered ones, so
a contiguous window spans less and decays more steeply — which would explain both
why nested windows come out less flat than random subsets and why bias spread
accounts for most of the departure. That is a statement about **conditioning**
rather than about new information arriving with new rows. It is consistent with
everything measured here and established by none of it, and testing it needs
devices this analysis never touched.

### 4.3 The degeneracy is global as well as local, and its geometry depends on the dimension

A local Jacobian rank is a statement about an infinitesimal neighbourhood. It is
structurally incapable of detecting whether two *far apart* profiles produce the
same measurement, so we searched for such pairs directly. An oracle-arbitrated
search over 1,999,000 candidate pairs in **chart G** at `d=4` returned **13
witness pairs**: profiles up to **8.18×** apart in doping whose I–V curves differ
by **1.23%**, below the 2% noise floor. A second search in **chart J** at `d=16`
returned **13 witness pairs** at up to **14.75×**, and a third in **chart L** at
`d=16` returned **37**. Two of the headline pair's members have junction depths
of **694 nm and 271 nm** — a difference that survives grid refinement, moving
1.7% under `N = 301 → 1201`.

Existence transfers between searches; frequency does not. Three searches at three
budgets over three priors are existence proofs, and we do not compare how *often*
degeneracy occurs in one chart against another.

**Every witness is refined before it is counted** (`WIT-02`), because a witness
pair that is an artefact of the grid is not a witness. All three committed sets
have now been through the battery, and **all three lost members**: chart G at
`d=4`, **13 of 13 refined and 12 surviving**; chart J at `d=16`, **13 of 13
refined and 7 surviving**; chart L at `d=16`, **37 of 37 refined and 26
surviving**. The live register is `outputs/close/wit02_register_v3.json`. Under
`WIT-01` the admissibility ratio is **1.000** in all three charts — every pair
qualifies on a doping magnitude, and magnitudes reach the grid exactly — which is
a result worth stating rather than assuming, because *"the rule does not bite
here"* and *"the rule was never applied here"* are different sentences and only
one of them is checkable.

**Full coverage buys less than it sounds like it does.** `WIT-02` tests
witnesses, not connectivity. It converts no `d=16` result into a separation, and
that distinction is the next paragraph.

**What the barrier measurement does and does not establish.** For each pair we
compute the profile-likelihood barrier along the straight line between its
members in that chart's own coordinates, against a null control of ordinary prior
draws at the same path length. In chart G at `d=4` the median barrier over the
twelve surviving pairs is **0.81 floor units** with 6 of 12 at or below the floor
barrier — a *ridge*. At `d=16` both charts sit far above it: chart J at **59**
floor units and chart L at **222.8** over its twenty-six survivors, with **0 of
26** at the floor barrier — *basins*. What the chart moves at matched `d` is the
**depth**: 13× in witness-to-null ratio between two charts with matched path
lengths.

**These are search statements, not separation proofs**, and the direction of the
inequality is unfavourable. A straight-line barrier is an **upper bound** on the
true barrier, so a shallower connecting path may exist; we did not compute the
minimum-energy path. A basin claim rests on finding *no* connecting path below
the floor, and an upper bound cannot establish that none exists. So the honest
form is: **no connecting path below the floor was found along the straight
line.** Refinement does not repair this and we do not claim it does.

The reading that survives is about the **dimension**, not the chart: pairs sit at
the instrument floor at `d=4` and do not at `d=16` in either chart tested. An
earlier version of this section said the opposite — *a ridge in one chart and
isolated basins in another* — and that chart-dependent reading was withdrawn when
the third chart was measured at matched `d`.

**What predicts survival is not known.** The two 13-pair sets suggested that
headroom against the distinguishability floor predicts which pairs survive
refinement, with the split at 93.65% of the floor in chart J against 98.9% in
chart G. On chart L — the 37-pair set, the largest, and the only one that did not
help form the rule — concordance is **0.479** against 0.500 for a coin, and the
surviving and separating bands overlap from 0.53 to 1.00 floor units. No margin
band was adopted and none is defensible. This strengthens rather than weakens the
refusal to adopt one: the observed split in the two forming sets was 1.4
percentage points wide, which is narrow enough that any threshold inside it would
be tuned.

### 4.4 Forward accuracy

| Test set | Median rel. error (95% CI) | p90 | n |
|---|---:|---:|---:|
| Interpolation (within training band) | 2.8% (2.0–3.9%) | 7.0% | 72 |
| **Extrapolation** (outside the band) | 38.2% (23.1–89.7%) | 861% | 68 |
| Family transfer (graded; trained on steps) | 84.2% (75.0–106.4%) | 151% | 60 |

Measured current dynamic range of the training labels: **9.96 decades**
(8.9e-5 → 8.1e5 A/m²), after dropping 13 of 169 candidate (profile, bias) pairs
whose SG current lay below the solver's own noise floor.

### 4.5 Inverse recovery and calibration

Single-level recovery (the well-posed sub-problem): 0.0018 decades at 0% noise
rising to 0.0072 at 10% (n=40 per row). 1σ coverage falls 75% → 28% as noise
grows, showing the ensemble spread captures epistemic uncertainty only and does
not absorb measurement noise.

Calibration, **pre and post on the identical test set** (n=140), variance
inflation $T=2.08$ fitted on a disjoint split:

| Interval | Raw | Recalibrated | Nominal |
|---|---:|---:|---:|
| ±1.0σ | 29% (22–37%) | 62% (54–70%) | 68% |
| ±1.64σ | 46% (38–54%) | 90% (84–94%) | 90% |
| ±2.0σ | 59% (50–66%) | 98% (94–99%) | 95% |

### 4.6 Experiment design: uncertainty acquisition is worse than random

An earlier version of this section reported that `max_std` acquisition showed
"no distinguishable advantage" over random. Re-measured against the quantity
the inverse problem actually cares about — how many doping degrees of freedom
the chosen measurements determine — it is not neutral but **actively harmful**.

Four device families × five budgets × twelve random seeds. Every strategy
draws from the same candidate pool; acquisition may consult only the
*surrogate* Jacobian and the *surrogate* σ, while scoring uses the SG Jacobian
that no strategy could see.

| Strategy | mean Δ identifiable rank vs random | win / tie / loss |
|---|---:|---|
| `max_std` (predictive uncertainty) | **−0.31** | 2 / 9 / 9 |
| `d_optimal` (log det Fisher information) | **+0.39** | 5 / 15 / 0 |
| `null_space` (signal along unresolved directions) | **+0.39** | 5 / 15 / 0 |
| `std_x_nullspace` | +0.24 | 4 / 14 / 2 |
| `e_optimal` | −0.06 | 2 / 13 / 5 |

The interpretation is that predictive uncertainty and inverse identifiability
ask different questions. Uncertainty asks *where is the forward model unsure?*;
the inverse problem needs *which measurement constrains a direction I currently
cannot see?* A bias the surrogate predicts confidently can still be the only
one that resolves a given profile direction.

The design criteria used are textbook (Fedorov, 1972; Atkinson & Donev, 1992;
Alexanderian et al., 2014) and **no methodological novelty is claimed**. Two
bounds are stated rather than hidden: the gain is modest (≈0.4 of a rank unit
on a base of 3–4), and it is obtained despite planning with a surrogate
Jacobian that correlates only +0.01…+0.40 with the truth — which §4.8
explains.

### 4.7 Is the uncertainty useful?

A predictive standard deviation is only worth reporting if it tracks the error.
Spearman ρ(σ, |error|) = **+0.824** (n=200), and going from interpolation to
extrapolation σ inflates **15.7×** against an error inflation of 11.8× — the
ensemble does detect that it is extrapolating.

It is not, however, a calibrated error estimate out of distribution. Median
|error| across ascending σ quartiles is 0.008, 0.031, 0.373, 0.254 — *not*
monotone: on the unseen graded family the ensemble reports σ = 0.67 against an
actual error of 0.27. It errs toward caution, which is the safe direction, but
σ over-states the error where the model is least familiar.

### 4.8 Surrogate accuracy does not imply surrogate gradients

If terminal I–V determines only 3–4 of 16 doping directions in **chart L** at
`d=16` **at a given operating point**, over the 0–0.9 V bias window and at 2%
measurement noise — a *local* Jacobian rank, not a global claim, and one that
`rank(observation set)` shows moving with the window — then a surrogate trained
only on I–V is constrained only in that subspace. Along the remaining
11–13 directions no training signal distinguishes one behaviour from another,
so its *derivatives* there are unconstrained — even where its *values* are
excellent. Those derivatives are precisely what gradient-based inverse design
and Jacobian-based experiment design consume.

We state the prediction first and then test it. Decomposing the true Jacobian
$J = U\Sigma V^{\mathsf T}$, we compare the directional derivatives
$J v_j$ and $\hat J v_j$ of the SG solver and the surrogate along each right
singular direction, over four device families:

| Training budget | mean cosine, $j <$ identifiable rank | mean cosine, $j \ge$ rank | mean value error (symlog) |
|---:|---:|---:|---:|
| 300 | +0.47 | +0.003 | 1.133 |
| 10 000 | **+0.504** | **−0.001** | **0.252** |

The control excludes the obvious alternative explanation. Over a 33×
increase in training budget the surrogate's *value* error falls 4.5×, while
its agreement outside the identifiable subspace stays pinned at zero. There is
nothing to learn there, so more training does not help — which is what
ill-posedness predicts.

The nearest prior work we found is Yu, Cai & Liu (arXiv:2604.04107), who
compare autodiff gradients of a neural surrogate against theoretical
sensitivity kernels for surface-wave dispersion and report that the main
structure *is* recovered, with artefacts traceable to structure in the
training data. Our contribution is narrower and more specific: the
identifiability spectrum of the forward map **predicts, direction by
direction, where a learned surrogate's gradients can be trusted.**

### 4.9 Three uncertainty backends under one protocol

The three UQ backends had never been compared, because MC-dropout and SWAG
wrapped the superseded pure-physics PINN rather than the surrogate under
evaluation. With all three attached to the surrogate and returning the same
prediction type, and after a hyperparameter search for each selected on the
calibration split (never on test):

| Method | ρ(σ,\|err\|) | NLL calibrated | σ inflation (extrap) | error inflation (extrap) |
|---|---:|---:|---:|---:|
| Deep ensemble (M=5) | **+0.798** | **−1.452** | **21.3×** | 12.1× |
| MC-dropout (tuned) | +0.299 | 18.737 | 1.4× | 12.4× |
| SWAG (tuned) | +0.486 | 1.814 | 2.5× | 13.2× |

The mechanism is in the last two columns. Under distribution shift the error
grows ~12–13× for all three, but MC-dropout's and SWAG's σ is governed by
their own hyperparameters — the dropout rate, the width of the SWA trajectory
— which are properties of the model rather than of distance from the data. The
ensemble's σ is functional disagreement between independently trained members,
and that does grow. A budget-matched ensemble, trained *faster* than either
single-network method, still beats both, so this is not a compute advantage.

A secondary observation worth recording: selecting UQ hyperparameters by
in-distribution NLL systematically prefers small σ, and small σ is exactly
what fails out of distribution.

### 4.10 What the audit found

Fourteen defects across two audit cycles. Four produced silently wrong physics
while the test suite of the day passed:

- **The most recent one survived a 161-test suite that had itself been written
  by an audit.** The Gummel carrier-convergence test was *relative*, applied to
  an array spanning 16 decades; entries far below the array maximum can never
  reach it, so the solver reported failure on states whose potential had
  converged to 1e-12. Because the bias-continuation loop aborts on the first
  step that reports failure, `solve()` then returned the *cold-start* state:
  currents wrong by three to five orders of magnitude, and of the wrong sign
  under reverse bias, across the top two decades of the claimed doping range.
  The fix distinguishes round-off stagnation from divergence using a threshold
  that separates the two populations by eleven orders of magnitude, so it is
  not tuned.


- The Gummel loop reported `converged=True` on states whose continuity residual
  equalled the entire current scale, because it tested only the potential.
- The 2D MOS-cap Newton Jacobian had the **wrong sign** on the charge
  derivative, so the solver diverged for every $|V_g| \gtrsim 1$ V. The
  documented "strong-inversion stiffness" limitation was this bug; with the sign
  corrected, the solver converges from −2 V to +5 V with relative residuals
  ~1e-12 and reproduces textbook inversion pinning near $2\phi_F$.
- The ohmic boundary condition computed the minority carrier as a difference of
  two numbers equal to machine precision, giving a 0.35% mass-action error at an
  ordinary $10^{23}$ m⁻³ and exactly zero (hence NaN) at $10^{25}$ m⁻³ — the top
  two decades of the range the project claimed to support. The correct stable
  formulation already existed in a sibling module whose docstring claimed to
  "match the SG solver convention".

## 5. Limitations

- Terminal-current noise floor ~2e-6 A/m² near equilibrium; irreducible in a
  density-based formulation at float64. Measured and reported, not removed.
- Surrogate extrapolation and family transfer are poor (38%, 84% median error).
- The rank in §4.1 is *local* — a Jacobian at one operating point, in one
  chart, at one dimension, over one observation set. It is robust to the
  parameterisation dimension (P = 8 → 32 leaves it at 2–4), so it is a property
  of the measurement and not of the discretisation; it is **not** robust to the
  observation set, which is the subject of §4.2 and the reason every figure here
  travels with its window.
- **The mechanism behind the rank climb is unexplained.** §4.2 converts *"the
  rank climb is unexplained"* into a measured description of *what* moves. It
  does not say why widening the bias window compresses the spectrum, and the
  three methods that tried are characterised rather than counted.
- **Both `d=16` barrier results are searches, not separations.** No connecting
  path below the floor was found along the straight line; the minimum-energy
  path was not computed. A straight-line barrier is an upper bound, and for a
  basin claim that is the unfavourable direction.
- **What predicts refinement survival is not known.** The headroom rule that the
  two 13-pair sets suggested carries no information on the 37-pair set
  (concordance 0.479 against 0.500 for a coin). No margin band is adopted.
- **The ridge/basin classifier is binary over three cells.** The numbers beneath
  it are not, and only the chart-L-against-chart-J contrast is matched in both
  path length and dimension.
- **Everything here is bounded above by 0.9 V.** That is the top of the
  convergence sweep and it has never been validated as a limit. *Unvalidated
  above* is not *fails above*, and we make no claim about either.
- **No result in this paper has been evidenced on any interpreter but CPython
  3.11 or any operating system but the development one.** The CI matrix that was
  supposed to evidence portability has never executed; the 3.9 support floor is
  a static scan, and Linux and macOS are unvalidated and say so in every
  manifest.
- The gradient-fidelity result (§4.8) is measured on four device families in
  1D with one surrogate architecture. Whether the inside/outside separation is
  as sharp for other architectures or in 2D is untested.
- The experiment-design gain (§4.6) is modest (≈0.4 rank) and is obtained with
  a surrogate Jacobian that correlates only +0.01…+0.40 with the truth. A
  better forward model would plausibly change the size of the effect.
- The pure-physics PINN is retained but not developed; it predicts essentially
  zero current (§4.10).
- 1D transport only; the 2D solver handles Poisson without continuity.
- Boltzmann statistics, constant mobility, no interface traps.

## 6. Conclusion

The scientifically useful outputs of this project are a reference solver that
knows where it stops being reliable, a measured statement of how little of a
doping profile terminal I–V can determine — and of how much that statement
depends on which biases you measure rather than on the device — witness pairs
showing the degeneracy is global and not only local, the observation that the
local limit propagates into the *gradients* of any surrogate trained on those
measurements, and an audit trail showing how easily plausible numbers survive a
passing test suite. Three results are negative — the pure-physics PINN does not
work as a forward model, uncertainty-driven acquisition is worse than random,
and neither MC-dropout nor SWAG is competitive with a deep ensemble here — and
each is reported with the mechanism that explains it. One question is left
**open**: why the spectrum flattens as the bias window widens. We report the
three pre-registered methods that failed to answer it, each with its measured
failure mechanism, because a characterised failure is more useful to the next
person than a plausible mechanism we could not test. None of it is a new
method, and
the paper does not claim one.

## References

- Burger, Engl, Leitão & Markowich (2001). Identification of doping profiles in semiconductor devices. *Inverse Problems* **17**, 1765.
- Burger, Engl, Leitão & Markowich (2004). On inverse problems for semiconductor equations. *Milan J. Math.* **72**, 273.
- Scharfetter & Gummel (1969). Large-signal analysis of a silicon Read diode oscillator. *IEEE Trans. Electron Devices* **16**, 64.
- De Mari (1968). An accurate numerical steady-state one-dimensional solution of the P-N junction. *Solid-State Electron.* **11**, 33.
- Aster, Borchers & Thurber (2018). *Parameter Estimation and Inverse Problems*, 3rd ed.
- Higham (2002). *Accuracy and Stability of Numerical Algorithms*, 2nd ed.
- Lakshminarayanan, Pritzel & Blundell (2017). Deep ensembles. *NeurIPS*.
- Maddox et al. (2019). SWAG. *NeurIPS*.
- Fedorov (1972). *Theory of Optimal Experiments*. Academic Press.
- Atkinson & Donev (1992). *Optimum Experimental Designs*. Oxford.
- Alexanderian, Petra, Stadler & Ghattas (2014). A-optimal design of experiments for infinite-dimensional Bayesian linear inverse problems with regularized ℓ0-sparsification. *SIAM J. Sci. Comput.* **36**(5), A2122–A2148.
- Yu, Cai & Liu (2026). Physical sensitivity kernels can emerge in data-driven forward models: evidence from surface-wave dispersion. arXiv:2604.04107.
- Gal & Ghahramani (2016). Dropout as a Bayesian approximation. *ICML*.
- Kuleshov, Fenner & Ermon (2018). Accurate uncertainties for deep learning using calibrated regression. *ICML*.
- Gneiting & Raftery (2007). Strictly proper scoring rules. *JASA* **102**.
- Raissi, Perdikaris & Karniadakis (2019). Physics-informed neural networks. *JCP* **378**, 686.
- Rudin, Osher & Fatemi (1992). Nonlinear total variation based noise removal. *Physica D* **60**, 259.
- Sze & Ng (2007). *Physics of Semiconductor Devices*, 3rd ed.
