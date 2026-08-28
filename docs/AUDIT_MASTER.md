# BayesPINN-Inv — Master Audit Ledger

Every finding from the full-spectrum engineering / physics / ML / reproducibility
audit. Findings are never deleted; superseded ones are marked REJECTED with a
reason.

**47 findings total**, of which 14 are numbered `BUG-xx` (numerical/solver
defects). Seven are CRITICAL: BUG-03, BUG-05, BUG-06, BUG-07, BUG-10, BUG-11
and **BUG-13**. Every one of them was present while the test suite of the day
passed — BUG-13 survived all 161 tests of the first audit cycle.

Findings 1-40 are the first cycle (sections 1-6c). Findings 41-47 are the
**second cycle** (section 8), which re-ran the evidence instead of inheriting
it: BUG-13, BUG-14, PINN-01, UQ-01, GRAD-01, DES-01, IDENT-02.

Also note NB-01 is now closed: all twelve notebooks were regenerated and
re-executed against the current solver.

**Status vocabulary:** OPEN · INVESTIGATING · IMPLEMENTED · VERIFIED · ACCEPTED
(known limitation, documented) · DEFERRED · REJECTED

**Severity:** CRITICAL (wrong science shipped) · HIGH (wrong results in some
regime) · MEDIUM (correctness risk / misleading) · LOW (hygiene)

---

## 1. Numerical physics — 1D Scharfetter–Gummel oracle

### BUG-01 — `bernoulli` returns `inf`/`NaN` for x ≤ −709
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | HIGH |
| **Status** | VERIFIED |

**Finding.** `B(x) = x/(exp(x)−1)` was evaluated on the negative branch as
`x·exp(−x)/(1−exp(−x))`. For `x < −709`, `exp(−x)` overflows to `+inf`, giving
`−inf/−inf = NaN`. Measured: `B(−709) = inf`, `B(−710) = NaN`. The true value is
finite (`B(x) → −x`).

**Evidence.** Direct evaluation; the pre-existing tests only probed `|x| ≤ 50`
and so never entered the failure region.

**Blast radius.** `bernoulli` is called on every face of the continuity matrix.
A single face potential drop beyond ~709 V_T (≈18.3 V at 300 K) poisons the
whole linear system with `NaN`. Reachable under large reverse bias, coarse
meshes, or any transient excursion during Gummel iteration.

**Fix.** Use `x/expm1(x)` on both sides (`expm1` is *designed* for this
cancellation and saturates cleanly at `−1` as `x → −∞`), the Taylor series near
0, and `x·exp(−x)` for large positive `x` (underflows to 0 instead of
overflowing). Finite over the entire double range; the exact identity
`B(x) − B(−x) = −x` now holds to 8e−17.

**Test.** `tests/test_sg_numerics.py::TestBernoulliExtremes`

---

### BUG-02 — `Grid1D.junction_refined` coarsened the junction; `refine_width` ignored
| | |
|---|---|
| **Category** | numerical physics / API |
| **Severity** | MEDIUM (latent — the function was dead code) |
| **Status** | VERIFIED |

**Finding.** The grid mapped equispaced points through `tanh`. Cell spacing is
proportional to the *derivative* of that map, and `tanh` is steepest at its
centre — so the construction placed the **coarsest** cells at the junction.
Measured for the default arguments: 599× coarser at the junction than at the
contacts, i.e. it de-refined precisely the depletion region it was named for.
The `refine_width` argument was never read at all, and for an off-centre
junction the extremum did not even land on `x_junction` (max spacing at x=37.7
for `x_junction=20`).

**Blast radius.** None on published results — `junction_refined` is never
called anywhere in the repository (all code uses `Grid1D.uniform(L, 301)`). It
is an exported, documented API landmine.

**Fix.** Integrate a positive node-density function
`rho(x) = 1 + (f−1)·sech²((x−x_j)/w)` and invert its CDF. Spacing ∝ 1/rho, so
cells are `refine_factor` times finer at the junction. Verified: ratio 5.99 for
a requested factor of 6, minimum correctly centred, `refine_width` respected,
strictly increasing, endpoints exact. Invalid arguments now raise `ValueError`.

**Test.** `tests/test_sg_numerics.py::TestJunctionRefinedGrid`

---

### BUG-03 — Gummel reported `converged=True` on a state with ~1% carrier error
| | |
|---|---|
| **Category** | numerical physics |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** Two compounding defects in the project's ground-truth oracle.

1. **Incomplete convergence test.** The loop exited when `max|Δφ| < tol_outer`
   and nothing else. The potential is almost insensitive to the minority
   carriers (12 decades below the majority density), so φ converged to 1e−12 by
   sweep 3 while the carrier densities were still ~1% from self-consistent. The
   solver returned `converged=True` on a state whose **electron-continuity
   residual equalled 100% of the current scale** (‖r‖∞ = 7.4e−4 vs max|Jₙ| =
   7.4e−4).
2. **Unequilibrated linear solves.** The SG continuity matrix inherits the
   carrier dynamic range (12 decades). Its row ∞-norms span 1 → 2.5e4 even
   though `cond ≈ 5.2e5`, so plain `spsolve` commits a large relative error on
   the small minority-carrier components. Monitoring the iteration showed
   `max|np−1|` **stagnating in a limit cycle** at ~1e−2 forever, never
   converging; tightening `tol_outer` made the answer *worse*.

**Evidence.** Instrumented Gummel sweeps; independent recomputation of the
discrete Poisson and continuity residuals at the returned state; condition
number and row-norm measurement.

**Fix.**
- Two-sided (row + column) ∞-norm equilibration of both continuity systems
  before `spsolve` (`solve_equilibrated`). Exact — a similarity transform, no
  approximation. **Mass-action violation 1.32e−2 → 7.62e−6, a 1730× gain.**
- Convergence now additionally requires the relative carrier update to fall
  below `tol_carrier`. The unequilibrated path now honestly reports
  `converged=False`.
- Best-iterate tracking + stagnation detection, because past the round-off
  floor extra sweeps *degrade* the answer (I_eq drifted −7.2e−7 → −2.2e−6
  between 3 and 800 sweeps).

**Cost.** 13-bias continuation sweep 119 ms → 164 ms (+38%) for 1730× accuracy.

**Test.** `tests/test_sg_numerics.py::TestGummelConvergenceIsHonest`;
`test_core_invariants.py::test_mass_action` tolerance tightened 5e−2 → 1e−4.

---

### BUG-04 — terminal current destroyed by cancellation in the SG flux difference
| | |
|---|---|
| **Category** | numerical physics |
| **Severity** | HIGH |
| **Status** | VERIFIED (residual floor ACCEPTED, see ADR-0002) |

**Finding.** `J = (μ/h)[B(+Δ)n_{i+1} − B(−Δ)n_i]` is a difference of two large,
nearly-equal numbers: at equilibrium they cancel *exactly*, and near
equilibrium they cancel down to the exponentially small true current. With
scaled densities reaching 1e6 and 1/h ~ 1e4, each term is ~1e10, leaving an
absolute error ~2e−6 in scaled units.

**Fix.** Using `B(+Δ)/B(−Δ) = exp(−Δ)` the bracket factors exactly as
`B(−Δ)·n_i·expm1(u)` with `u = log(n_{i+1}/n_i) − Δ` — that is, `expm1` of the
**quasi-Fermi potential drop across the face**, which is identically zero in
equilibrium. An exact algebraic identity, not an approximation.

**Measured.** On an exact Boltzmann state the direct form gives max|Jₙ| =
5.86e−7 A/m²; the `expm1` form gives 1.39e−13 A/m² — **4.2 million× less
cancellation**. Away from equilibrium the two forms agree to 1.9e−11 relative,
confirming the identity.

**Residual floor (ACCEPTED).** The remaining equilibrium current (~7e−7 A/m²)
is *not* removed by this fix, because the cancellation simply moves into the
log-difference: `log n_{i+1} − log n_i − Δ` differences O(14)-magnitude numbers
and so carries ~3e−15 absolute round-off, amplified by the majority density
(1e6) and 1/h (1.2e4). Eliminating it requires reformulating the solver in
quasi-Fermi/Slotboom variables — see ADR-0002 for why we did not.

**Consequence, and the useful part.** `DeviceState.current_noise_floor` now
reports the face-to-face standard deviation of `J_total`. Since `div(Jₙ+Jₚ) = 0`
exactly in steady state, `J_total` must be constant, so its spread is an
assumption-free estimate of the error on the terminal current — the oracle
measuring its own error bar. `current_is_trustworthy(snr=10)` is the honest
boundary of the oracle's validated range. Measured on the reference diode: V=0
untrustworthy (SNR 0.4); V ≥ 0.05 trustworthy (SNR ≥ 86).

**Test.** `tests/test_sg_numerics.py::TestFluxCancellation`,
`::TestNoiseFloorDiagnostics`

---

### BUG-10 — Poisson-Newton had no step limiting: `inf` -> singular Jacobian -> `NaN`
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** The nonlinear Poisson equation with Boltzmann carriers is
exponentially stiff, and the Newton update was applied undamped and unchecked.
`n0 * np.exp(dphi_local)` overflowed to `inf`, the Jacobian became *exactly
singular*, `spsolve` returned `NaN`, and the entire solve was poisoned.

**Measured, on device families the repository explicitly claims to support:**

| Profile | Before | After |
|---|---|---|
| LDD (−1e22 / 5e21 / 5e23 m⁻³) | `NaN` at every bias | converges, I(0.6 V) = 2.11e5 A/m² |
| step, asymmetric (1e21 / 5e22) | I ≈ 1e9 A/m² at every bias, SNR < 1, `converged=False` | converges, I(0.6 V) = 1.45e6 A/m² |

Both families are generated by `data/datasets.py` and both are named in the
README's device list.

**Fix.** Two standard globalisations, both required: cap each Newton potential
update at `cfg.max_dphi` thermal voltages (the classical remedy for this
nonlinearity, and what production TCAD does), and backtrack until the residual
actually decreases. Exponents are additionally clipped at ±700 so a
pathological iterate yields a large finite number rather than `inf`, keeping
the failure visible in `converged` instead of silently NaN.

**Note.** This bug was only *findable* after BUG-03 made `converged` honest —
previously these solves reported success.

**Test.** `tests/test_robustness.py::TestDeviceFamilyRobustness`

---

### BUG-11 — ohmic boundary condition destroyed the minority carrier by cancellation
| | |
|---|---|
| **Category** | numerical physics |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** `_ohmic_bc` evaluated *both* roots of the neutrality/mass-action
quadratic:

    n = (C + sqrt(C² + 4))/2 ,   p = (−C + sqrt(C² + 4))/2

For `C > 0` the second expression subtracts two numbers that agree to machine
precision once `C² >> 4`. Measured violation of `n·p = 1`:

| C_s | equivalent N | n·p | error |
|---|---|---|---|
| 1e6 | 1e22 m⁻³ | 1.000 | ok |
| 1e7 | **1e23 m⁻³** | 0.9965 | 0.35% |
| 1e8 | 1e24 m⁻³ | 0.745 | 25% |
| 1e9 | 1e25 m⁻³ | **0.000** | total — then `log(0) = −inf` → NaN |

The README and paper both claim support for 1e21–1e25 m⁻³, i.e. `C_s` up to
1e9. The top two decades of the claimed range were unusable and the boundary
condition was quietly wrong at an *ordinary* 1e23 m⁻³.

**Fix.** Take the majority carrier from the quadratic (where the terms add, no
cancellation) and the minority from `n·p = 1`. Mass action now holds to
*exactly* zero for `|C_s|` up to at least 1e12.

**Aggravating detail.** `pinn/losses.py::ohmic_boundary_values` **already had
the correct stable formulation**, and its docstring explains this precise
cancellation and states that it "matches the SG solver convention". The fix
existed in one module and had never been propagated to the oracle — a
divergent duplicate implementation of the same physics.

**Test.** `tests/test_robustness.py::TestExtremeInputs::test_doping_magnitude_sweep`

---

### BUG-12 — Gummel diverges at high injection; no continuation on a cold start
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | HIGH |
| **Status** | VERIFIED |

**Finding.** The decoupled Gummel scheme is not unconditionally convergent, and
fails at high injection for strongly asymmetric multi-segment profiles. On the
LDD profile at 0.9 V from a cold start, `max|Δφ|` oscillates between 2 and
87 V_T indefinitely and the reported current is grid-dependent nonsense:

| Grid | Cold-start I (A/m²) |
|---|---|
| 201 | +6.98e10 |
| 301 | +1.78e11 |
| 601 | **−6.45e12** |

**Fix.** Automatic bias continuation: a non-converged cold solve is retried as
a ramp from zero bias in `continuation_step_V` increments, each step
warm-started from the last, and the retry is kept only if it converges. This
mirrors what `MOSCap2DSolver` already did in 2D.

**After:** converges on every grid, I = 3.5976e8–3.5986e8 A/m² — **grid-converged
to four significant figures**. The failure was in the iteration path, not the
discretisation. Cost: hard cases take 0.4–0.8 s instead of failing fast; the
easy path is unchanged (158 ms for a 13-bias sweep).

**Test.** `tests/test_sg_numerics.py::TestAutomaticContinuation`

---

### DOC-01 — SG module docstring stated the opposite sign convention
| | |
|---|---|
| **Category** | documentation / physics |
| **Severity** | MEDIUM |
| **Status** | VERIFIED |

**Finding.** The module header declared `J_n = μ_n(n·dφ/dx + dn/dx)` and the SG
flux `(μ/h)[B(−Δ)n_{i+1} − B(+Δ)n_i]` — an internally consistent pair, but
using `E = +∇φ`, which contradicts the Poisson equation `−φ'' = p − n + C`
printed three lines above and contradicts the implementation.

**Evidence.** Continuum limit of the *implemented* flux: expanding
`B(±Δ) ≈ 1 ∓ Δ/2` gives `J_n → μ_n(dn/dx − n dφ/dx)`, i.e. `E = −∇φ`. The
implementation is correct; the docstring was wrong.

**Fix.** Docstring corrected and pinned by a test that takes the continuum
limit numerically.

**Test.** `tests/test_sg_numerics.py::TestSignConventions::test_drift_diffusion_continuum_limit`

---

### BUG-13 — round-off stagnation reported as divergence, silently aborting bias continuation
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** `tol_carrier` is a *relative* test, `max_i |Δc_i| / |c_i|`, applied
to an array whose entries span up to 16 decades. At 1e24 m⁻³ the electron
density at the junction node sits ~9 decades below `max|n|`, so its update
floors at the round-off of the linear solve (measured: `|Δc| ≈ 26 · ε · max|c|`)
and can never reach 1e-8 *relative*. The Gummel loop therefore stalled and
reported `converged=False` on a state whose potential had converged to
`max|dφ| = 1.6e-12` and whose built-in potential was exact to 0.0.

**Blast radius — this is the serious part.** `auto_continuation`'s ramp loop
`break`s on the first step that reports `converged=False`. At high doping that
is *step 1* (V = 0.05 V), so the ramp aborted immediately and `solve()`
returned the **cold-start** state. Measured against a converged 0.02 V ramp:

| case | returned | truth | error |
|---|---:|---:|---|
| 1e24 m⁻³, 0.9 V | 2.37e11 A/m² | 1.64e8 A/m² | ×1400 |
| 1e25 m⁻³, 0.9 V | 6.67e12 A/m² | 2.00e7 A/m² | ×333000 |
| 1e24 m⁻³, −2.0 V | +3.00e9 A/m² | −4.25e-5 A/m² | **wrong sign** |

`datasets.py` samples LDD source/drain doping as `10**U(24, 25)` — squarely in
the affected band — and `run_results.py:126` filters labels on `.converged`, so
the flag was also dropping valid high-doping labels non-reproducibly (its value
flipped with grid size while the physics was unchanged).

All 161 pre-existing tests passed with this present.

**Root cause.** One defect with two faces: a relative convergence test that is
unsatisfiable in the presence of a large dynamic range, and a continuation loop
that treats "not converged" as "diverged".

**Fix.** The potential test is never relaxed. The carrier test is additionally
satisfied when the *absolute* update reaches the linear-solve round-off floor,
`max|Δc| ≤ carrier_roundoff_factor · ε · max|c|`. Measured over doping 1e21–1e25
m⁻³ × N ∈ {201, 401} × bias ∈ {0, 0.3, 0.6, 0.9, −2} V:

| population | `max|Δc|/(ε·max|c|)` | `max|dφ|` |
|---|---|---|
| round-off stagnation | 4.9e2 – 1.1e4 | ≤ 3.6e-12 |
| genuine divergence | 2.1e15 – 1.2e18 | ≥ 6.7e-01 |

The two are separated by **eleven orders of magnitude**, so the threshold is not
tuned: every value in [1e5, 1e13] yields an identical verdict on every case
(asserted by `test_roundoff_threshold_is_not_tuned`). The default 1e5 sits at
the bottom of that plateau so a BUG-03-style 1% error on a deep-minority node is
still rejected. `DeviceState.stalled_at_roundoff` and `.final_carrier_update`
record *why* a solve was accepted — nothing is hidden.

**Validation.** After the fix, 90/90 solves over doping 1e21–1e25 × N ∈
{201,401,801} × bias ∈ {0, 0.3, 0.6, 0.9, −2, −5} V converge, and every point
the oracle certifies as trustworthy is **grid-converged to ≤ 0.35 %** across
N = 201/401/801. The two corners that are *not* grid-converged (1e24 and 1e25 at
0.3 V, spreads 22 % and 274 %) are exactly the two that
`current_is_trustworthy()` already rejects — the noise-floor mechanism of
ADR-0002 catching them independently.

**Tests.** `tests/test_sg_numerics.py::TestRoundoffStagnationIsNotDivergence`
(7 tests): equilibrium convergence at high doping with exact V_bi; grid
convergence of I(0.9 V) at 1e24/1e25; the invariant that non-convergence is
*only* ever reported for a large `max|dφ|`; BUG-12's LDD case still rejected on
a cold start; threshold-plateau invariance; acceptance is reported not hidden;
untrustworthy corners flagged rather than silently wrong.

**Consequence for the claimed envelope.** The 1e21–1e25 m⁻³ doping range is now
actually delivered. Before this fix the top two decades returned grid-dependent
nonsense at forward bias and the wrong sign in reverse.

---


## 2. Numerical physics — 2D MOS-capacitor solver

### BUG-05 — Newton line search was dead code (absolute threshold on an unnormalized residual)
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** `_newton_solve` skipped the Armijo line search entirely whenever
`r_norm < 1e-4`, and declared convergence at `r_norm < 1e-6`. But `r` carries
the units of the finite-volume charge integral: for the project's default
MOS-cap its natural magnitude is ~1e−5, and on another mesh it moves by orders
of magnitude. Both constants were therefore meaningless — the line search never
ran, and every iteration took an **unguarded full Newton step** into a stiff
exponential.

**Evidence.** Residual trace at V_g = +1 V: `1.68e−11 → 2.84e−3` in one step,
then monotone growth. The relative residual at the initial guess was 1.0 (100%)
while `r_norm` read 6.2e−6.

**Fix.** Normalise by a *fixed* characteristic scale (the ionised dopant charge
in the largest control volume, floored by the initial residual magnitude) so
`tol_rel` is a genuine relative error; always run the line search (α = 1 is
tried first, so a healthy Newton step costs one extra residual evaluation).

---

### BUG-06 — bias continuation never executed on a cold start
| | |
|---|---|
| **Category** | numerical stability |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** `solve()` pinned the boundary rows to the **target** bias and only
then measured `phi_top_now` from those same rows. The continuation therefore
always computed a travel distance of exactly zero, `n_steps = 1`, and jumped
straight to full bias — the machinery that exists precisely to keep Newton out
of the stiff regime never ran except on a warm start.

**Fix.** Measure the starting potential before pinning; pin inside the
continuation loop only. Cold start is now local charge neutrality (`phi_F`),
the standard TCAD initial guess and the exact flat-band solution.

---

### BUG-07 — Newton Jacobian had the wrong sign on the charge derivative
| | |
|---|---|
| **Category** | mathematics |
| **Severity** | CRITICAL |
| **Status** | VERIFIED |

**Finding.** `_L @ phi` assembles `+∇·(ε∇φ)` (positive off-diagonals, negative
diagonal). With `r = L φ + qV(p − n + C)`, `n = n_i e^{+φ/V_T}`,
`p = n_i e^{−φ/V_T}`:

    dr/dφ = L + qV(dp/dφ − dn/dφ) = L − (qV/V_T)(n + p)

The code used `J = L **+** diags(d_charge)`. Newton was solving a linearisation
whose charge block pointed the wrong way, so no descent direction existed.

**Combined effect of BUG-05/06/07.** The 2D solver **diverged for every
|V_gate| ≳ 1 V** — the residual grew by up to 16 orders of magnitude — while
all nine pre-existing MOS tests passed, because they exercised only
V_gate ∈ [−0.3, +1.0] and never checked the residual.

**After the fix.** Converges over the whole operating range −2 V → +5 V with
relative residuals ~1e−12, no carrier clipping, and faster than before
(122 ms at V_g = 5 V vs 430 ms while diverging). φ_s now shows textbook
behaviour: flat band at V_g = 0, accumulation below, inversion pinning near
2|φ_F| above.

**This retires a documented limitation.** The README's "strong-inversion
stiffness" caveat was this bug, not physics.

**Test.** `tests/test_mos_cap_physics.py::TestConvergenceAcrossBias`

---

### BUG-08 — non-conservative finite volumes at the Neumann side walls
| | |
|---|---|
| **Category** | numerical physics |
| **Severity** | HIGH |
| **Status** | VERIFIED |

**Finding.** A node on the `x = 0 / x = Lx` Neumann boundary owns a half
control volume, so `cell_volume` halves its charge integral — but the assembly
used the **full** `hx` for that node's north/south face areas. The boundary
columns therefore received twice the vertical conductance they should per unit
charge. On a problem that is exactly 1D (uniform doping, no lateral structure)
the potential bowed by ~1.5 mV toward the side walls, decaying only as O(1/Nx),
and φ_s depended on `Nx`.

**Fix.** Face areas now use the same half-cell weights as `cell_volume`
(`ax = wy_j/hx`, `ay = wx_i/hy`). Lateral variation is now **machine zero**
(~1e−15) for every `Nx`, and φ_s is exactly `Nx`-independent.

**Test.** `tests/test_mos_cap_physics.py::TestLateralInvariance`

---

### BUG-09 — `test_zero_doping_linear_poisson` asserted non-physics
| | |
|---|---|
| **Category** | testing |
| **Severity** | MEDIUM |
| **Status** | VERIFIED |

**Finding.** The test set `C = 0` at `V_gate = 1.0 V` and compared against the
pure capacitor divider, calling it "pure Laplace". With `C = 0` the body is
*intrinsic*, not charge-free: carriers still respond as `n = n_i e^{φ/V_T}`,
which at 1 V is 6e32 m⁻³ — an enormous space charge that screens the field
completely. The divider is simply the wrong reference; the assertion only
passed because the solver was not converging (BUG-07).

**Fix.** Test moved to `V_gate = 1 mV`, deep in the linear-screening limit
(intrinsic Debye length ~41 µm ≫ 300 nm body), where the divider *is* exact.
Per the source-of-truth hierarchy, the test was fixed rather than the code.

---

### PERF-01 — `_row_to_identity` round-tripped the whole matrix through LIL per boundary node per Newton iteration
| | |
|---|---|
| **Category** | performance |
| **Severity** | LOW |
| **Status** | VERIFIED |

Replaced by a vectorised `_apply_dirichlet_rows` (`diag(keep) @ A + diag(1−keep)`).
Contributed to the 430 ms → ~70 ms improvement.

---

## 3. Claims, splits and evaluation methodology

### SCI-01 — headline calibration table compared two *different* test sets
| | |
|---|---|
| **Category** | experimental validity |
| **Severity** | HIGH |
| **Status** | VERIFIED (see §5) |

`outputs/results/results_summary.md` presented "Empirical (raw)" from
`H3_calibration` (evaluated on `test_levels`) beside "Recalibrated" from
`H3_recalibrated` (evaluated on `test_profiles_c`) as if they were before/after
on one set. The correct paired comparison exists in the JSON (`pre` vs `post`)
but was not the number shown.

### SCI-02 — "H4 Active-learning gain" contained no active learning
| | |
|---|---|
| **Category** | claim integrity |
| **Severity** | HIGH |
| **Status** | VERIFIED |

H4 compared three *fixed* bias subsets (first 3, last 3, all 13). No acquisition
function, no iterative loop, no retraining. Its own numbers also contradicted
the stated hypothesis ("few well-chosen biases recover doping as well as many"):
all-13 (0.004) beat high-3 (0.006) beat low-3 (0.008) — more data was simply
better. Renamed to what it measures: a bias-informativeness ablation.

### SCI-03 — coverage percentages reported from n = 5
| | |
|---|---|
| **Category** | experimental validity |
| **Severity** | HIGH |
| **Status** | VERIFIED |

H2's "1σ coverage 100% / 80% / 60% / 40%" is 5/5, 4/5, 3/5, 2/5 over five truth
levels, presented without `n`. The apparent monotone decline is within binomial
noise, and the same RNG seed was reused across noise levels so the four rows are
perfectly correlated rather than independent.

### SCI-04 — "13 orders of magnitude" overstated
| | |
|---|---|
| **Category** | claim integrity |
| **Severity** | MEDIUM |
| **Status** | VERIFIED |

The reference diode's I–V spans 1.4e−6 → 2.0e5 A/m² = **11.2 decades**, and the
*evaluated* points (V ≥ 0.1) span 8.2 decades. The trustworthy range — above the
oracle's own noise floor — is what the surrogate can legitimately claim.

### SCI-05 — `V < 0.1` silently dropped the V = 0.1 point
| | |
|---|---|
| **Category** | reproducibility |
| **Severity** | LOW |
| **Status** | VERIFIED |

`np.linspace(0, 0.6, 13)[2]` is `0.09999999999999999`, so the "V ≥ 0.1 V" filter
actually excluded V = 0.1 (n = 60, not 66). A fragile float comparison in the
headline metric definition.

### SCI-06 — "held-out" profiles are interpolation on a 1-parameter family
| | |
|---|---|
| **Category** | leakage / experimental validity |
| **Severity** | MEDIUM |
| **Status** | VERIFIED |

Train levels `geomspace(5e20, 5e22, 11)`; test levels `geomspace(7e20, 4e22, 6)`
— strictly *inside* the training range, on the same symmetric fixed-junction
one-parameter curve. Not leakage in the strict sense, but "held-out profiles"
overstates it: it is dense interpolation. Extrapolation was never measured.

### SCI-07 — inverse recovery is a 1-parameter identification, not profile recovery
| | |
|---|---|
| **Category** | claim integrity |
| **Severity** | MEDIUM |
| **Status** | ACCEPTED (documented) |

`encode_level` builds a symmetric step with the junction fixed at the midpoint
and optimises a single scalar `logL` against 13 observations, inside the
training range. Recovering it to 0.004 decades is unsurprising and is the
best-posed possible case. The README already flags this honestly; the
ill-posedness of true profile recovery is the scientifically interesting result
and is now quantified directly (see §6, IDENT-01).

---

## 4. Software / API / packaging

### PKG-01 — `[project.scripts]` point at a package that does not exist
| **Severity** | HIGH | **Status** | VERIFIED |

`pyproject.toml` declares `bayespinn-train = "bayespinn_inv.scripts.train:main"`
(and two more), but there is no `src/bayespinn_inv/scripts/` package — the
launchers live in a top-level `scripts/` directory that is not packaged. Every
console entry point fails on a clean install.

### PKG-02 — `load_forward_ensemble` execs a file from the source checkout
| **Severity** | MEDIUM | **Status** | VERIFIED |

The legacy branch resolves `Path(__file__).resolve().parents[3]/"scripts"`,
which is the repo root in a dev checkout and nonsense in `site-packages`.

### API-01 — two incompatible definitions of "ensemble mean current"
| **Severity** | MEDIUM | **Status** | VERIFIED |

`SurrogateEnsemble.predict` returns `mean_current = symlog⁻¹(mean(symlog))` (a
median-like estimator), while `SurrogateEnsembleAdapter.iv_curve` returns
`mean(I)` in linear space. Over 11 decades these differ substantially. Both are
called "mean".

### API-02 — duplicate, non-equivalent temperature-scaling implementations
| **Severity** | MEDIUM | **Status** | VERIFIED |

`calibration/metrics.py::fit_temperature_regression` minimises Gaussian NLL
(T = RMS(z)); `scripts/run_results.py` independently fits
`T = quantile(|z|, 0.6827)` targeting 1σ coverage. The headline results use the
script's version and never call the library.

### API-03 — `torch.manual_seed` called inside `IVSurrogate.__init__`
| **Severity** | MEDIUM | **Status** | VERIFIED |

Constructing a model mutates global RNG state, silently reseeding anything
downstream. A reproducibility hazard; with a shared default seed it would make
"independent" ensemble members identical.

### API-04 — ECE estimated from the raw M = 5 ensemble ECDF is biased
| **Severity** | MEDIUM | **Status** | VERIFIED |

`reliability_diagram_regression` evaluates `np.quantile(samples, q, axis=0)`
over 5 members. A *perfectly* calibrated 5-member ensemble has
P(y ≤ min of 5) ≈ 1/6, not 0, so the reported ECE has a floor of roughly 0.03
even for a flawless model. ECE differences below that floor are not meaningful.

### SEC-01 — `torch.load(..., weights_only=False)`
| **Severity** | LOW | **Status** | VERIFIED |

Explicitly disables PyTorch ≥ 2.6's safe-loading default; a malicious checkpoint
or manifest executes arbitrary code.

### DOC-02 — README quick-start halves the current
| **Severity** | MEDIUM | **Status** | VERIFIED |

The README example computes `0.5*(s.Jn.mean() + s.Jp.mean())`, but
`terminal_current` is `mean(Jn + Jp)` — a factor-of-2 discrepancy in
user-facing example code. The same expression appears as a fallback in
`active_learning/loop.py::simulate_measurement`.

### DOC-03 — README self-contradicts on test count
| **Severity** | LOW | **Status** | VERIFIED |

Badge and results table say 42; the roadmap table says "Unit tests (38) … 23
core + 9 MOS-cap + 6 surrogate" (which is 38, and omits `test_adapters.py`).

### DOC-04 — `papers/draft.md` describes a superseded architecture
| **Severity** | HIGH | **Status** | VERIFIED |

The draft still presents the pure-physics PINN as the forward model and claims
"the forward PINN converges on realistic doping ranges", directly contradicting
`docs/forward_model_reframe.md`, which documents that it does not reproduce
diode I–V at all. It also cites "23 unit tests", leaves `X`/`Y`/`Z` placeholders
in the abstract, references a `references.bib` that does not exist, and asserts
first-ness ("first to evaluate Bayesian PINN calibration quantitatively for
semiconductor inverse problems") with no prior-art review.

### CITE-01 — unverifiable citation
| **Severity** | MEDIUM | **Status** | OPEN |

`inverse/inverse_design.py` cites *Beucler et al., "Constraining neural networks
for the inverse design of semiconductor devices" (2022)* as the source of the
TV + positivity scheme. Beucler et al.'s known work is on enforcing analytic
constraints in climate emulators, not semiconductor inverse design. The title
could not be located. The co-cited Chen et al., Opt. Express 28, 11618 (2020) is
genuine.

---

## 5. Active learning

### AL-01 — noise model contradicts its own docstring
| **Severity** | MEDIUM | **Status** | VERIFIED |

`simulate_measurement` documents "Gaussian in log-current space when current is
significant, additive when near zero" but implements
`I*(1 + σ·ε) + σ·1e-3·ε` — multiplicative and additive terms driven by the
**same** draw `ε` (perfectly correlated), with an arbitrary 1e−3 A/m² floor.

### AL-02 — `max_std` acquisition can march along adjacent biases
| **Severity** | MEDIUM | **Status** | VERIFIED |

The acquisition is deterministic given the current doping estimate; the
duplicate guard moves the choice by exactly one grid step. Repeated selection
therefore degenerates into a walk along neighbouring biases rather than
exploration.

### AL-03 — no leakage found
| **Severity** | — | **Status** | VERIFIED (clean) |

Checked: the oracle is queried only on the true device (that *is* the
experiment), `max_std` uses model uncertainty alone, and `ucb` regresses on the
data-fit loss over acquired measurements. No test labels enter selection.

---

## 6. Novelty / research contribution

### IDENT-01 — identifiability of the inverse problem was asserted, never measured
| **Severity** | — (opportunity) | **Status** | IMPLEMENTED |

The repository states that profile recovery from terminal I–V is ill-posed and
reports a symptom (I–V matched to 0.2% while profile rel-L2 stays 0.17–0.84),
but never quantifies *which* directions in profile space are unobservable. This
is the one place where the project can make a defensible, measurable
contribution rather than a combination-of-methods claim. See
`docs/NOVELTY_AUDIT.md` and `src/bayespinn_inv/inverse/identifiability.py`.

---

## 6b. Release engineering

### CI-01 — no continuous integration
| **Severity** | MEDIUM | **Status** | VERIFIED |

There was no `.github/` directory and no CI of any kind, so nothing prevented a
regression from being committed. Added `.github/workflows/ci.yml`: lint + tests
on Python 3.9/3.11/3.12, plus a separate job that builds the wheel, installs it
into a clean virtualenv, runs `bayespinn selftest`, and executes the whole test
suite **against the installed package** rather than the source tree.

### NB-01 — twelve notebooks ship stale executed outputs
| **Severity** | MEDIUM | **Status** | ACCEPTED (documented) |

All twelve notebooks carry embedded outputs generated before this audit, i.e.
against a solver with twelve defects. They still *run* (they use only
API-compatible calls: `SGConfig()` and `terminal_current`), but their numbers
are wrong in the specific ways listed in `notebooks/README.md`, which now
carries a prominent staleness banner. Re-executing them was out of scope for
this cycle and is the top recommendation in `docs/RELEASE_READINESS.md`.

### VER-01 — package version drifted from the package metadata
| **Severity** | LOW | **Status** | VERIFIED |

`pyproject.toml` declared `version = "0.1.0"` while
`bayespinn_inv.__version__` was `"0.1.0-dev"`. Made structurally impossible:
the version is now `dynamic` and read from the package attribute.

### PKG-03 — `py.typed` declared in package-data but absent
| **Severity** | LOW | **Status** | VERIFIED |

`[tool.setuptools.package-data]` listed `py.typed`, but the file did not exist,
so the package silently shipped without a PEP 561 typing marker. File created.

---

## 6c. Physics capability recovered by the fixes

Not defects — consequences worth recording, because they change what the
project can honestly claim.

| ID | Capability | Before | After |
|---|---|---|---|
| CAP-01 | 2D MOS-cap operating range | diverged for \|V_g\| ≳ 1 V; "strong-inversion stiffness" documented as a limitation | converges −2 V → +5 V, rel. residual ~1e−12; textbook inversion pinning near 2\|φ_F\| |
| CAP-02 | 2D MOS C–V curve | unobtainable (the sweep could not converge across the range) | full curve: accumulation → depletion minimum (C/C_ox = 0.001) → inversion recovery, C/C_ox ≤ 0.87 |
| CAP-03 | 1D device families | LDD returned NaN; asymmetric steps returned ~1e9 A/m² | all eight families converge, 0–0.9 V, physically plausible currents |
| CAP-04 | Doping range | fatal above 1e24 m⁻³; 0.35% BC error at 1e23 | exact to 1e25 m⁻³ and beyond (mass action to 0.0) |
| CAP-05 | 2D mesh independence | φ_s depended on `Nx`; ~1.5 mV spurious lateral bowing | φ_s exactly `Nx`-independent; lateral variation ~1e−15 |

---

## 8. Second audit cycle — re-execution, fair benchmarking, robustness

The first cycle closed 40 findings. This cycle re-ran the evidence rather than
inheriting it. It found one CRITICAL solver defect (BUG-13, §1), one
portability defect, and four scientific results — two of them negative.

### BUG-14 — every text write used the platform encoding; the notebook builder could not run on Windows
| | |
|---|---|
| **Category** | reproducibility / portability |
| **Severity** | HIGH |
| **Status** | VERIFIED |

**Finding.** `scripts/build_notebooks.py` called `Path.write_text(...)` with no
`encoding`, so on Windows it used cp1252 and died with `UnicodeEncodeError` on
the first physics symbol (φ) — **the notebook generator could not run at all on
the platform the project's own manifests record as the one the results were
produced on** — and it truncated the notebook it was midway through writing. A
sweep found the same defect throughout: 24 `open(..., "w")` calls, 2
`read_text()` and 1 `write_text()` across 15 files, including the `.tex`/`.md`
writers in `freeze_results.py` and the CSV writers in the sweep scripts.

**Why it mattered.** "Regenerate the notebooks" was a documented maintenance
procedure that was impossible to perform.

**Fix.** Explicit `encoding="utf-8"` on every text read and write in `src/` and
`scripts/`. Verified: no unencoded text IO remains, and `newline=""` is
preserved on the CSV writers.

---

### PINN-01 — the pure-physics PINN predicts essentially zero current
| | |
|---|---|
| **Category** | scientific claim |
| **Severity** | — (measurement) |
| **Status** | VERIFIED · see ADR-0004 |

Measured rather than inherited: 8000 epochs, 27× the surrogate's wall-clock,
scored on identical devices, biases and trust filter
(`scripts/run_pinn_vs_surrogate.py`).

| Model | Median rel. err | p90 | Within 50% | Train |
|---|---:|---:|---:|---:|
| SG-supervised surrogate | 2.64% | 6.64% | 100% | 22.5 s |
| Pure-physics PINN | **100.00%** | 100.00% | 6% | 210.6 s |

A median *and* p90 of exactly 100.00% is the signature of predicting `I ≈ 0`:
`|0 − I| / |I| = 1` for any `I`. Crucially this is not an optimisation
failure — the PINN's own self-consistency diagnostic `std(J)/|mean(J)|` is
**0.03**, so it converged to a smooth, internally consistent, current-free
solution. That is the multiscale-cancellation mechanism
`forward_model_reframe.md` diagnosed, now measured against the post-audit
solver. Reclassified as legacy infrastructure and a documented negative
result; the project's terminology corrected (ADR-0004).

---

### UQ-01 — MC-dropout and SWAG were wired to the wrong model, and lose once wired to the right one
| | |
|---|---|
| **Category** | Bayesian / UQ correctness |
| **Severity** | MEDIUM |
| **Status** | VERIFIED · see ADR-0005 |

**Root cause of Gate D's "not demonstrated".** Both wrapped `ForwardPINN`, not
the `IVSurrogate` under evaluation, so they were never comparable to the
ensemble. `bayesian/surrogate_uq.py` closes the gap: all three now return the
same `SurrogatePrediction`, pinned by 21 interface tests.

Under one protocol, after a fair hyperparameter search selected on the
calibration split (never on test):

| Method | rho(sigma,\|err\|) | NLL calib | sigma inflation (extrap) | error inflation (extrap) |
|---|---:|---:|---:|---:|
| deep ensemble | **+0.798** | **−1.452** | **21.3×** | 12.1× |
| MC-dropout (tuned, p=0.01) | +0.299 | 18.737 | 1.4× | 12.4× |
| SWAG (tuned, lr=5e-4) | +0.486 | 1.814 | 2.5× | 13.2× |

**Mechanism.** Under distribution shift the error grows ~12–13× for all three,
but MC-dropout's and SWAG's sigma grows 1.4× and 2.5× — their predictive
spread is set by their own hyperparameters (dropout rate, SWA trajectory
width), which are properties of the model rather than of distance from the
data. The ensemble's sigma is functional disagreement between independently
trained members, which does grow. A **budget-matched** ensemble, trained
*faster* than either single-network method, still beats both — so this is not
a compute advantage.

Also recorded because it generalises: selecting UQ hyperparameters on
in-distribution NLL systematically prefers small sigma, and small sigma is
exactly what fails out-of-distribution.

---

### GRAD-01 — a surrogate that fits I–V to 2.6% has gradients that are correct only inside the identifiable subspace
| | |
|---|---|
| **Category** | scientific result (new) |
| **Severity** | — (finding) |
| **Status** | VERIFIED |

**Prediction stated first, then tested.** If terminal I–V determines only ~3–5
of 16 doping directions, a surrogate trained only on I–V is constrained only
there. Along the remaining 11–13 directions no training signal distinguishes
one behaviour from another, so its *derivatives* should be arbitrary even
where its *values* are excellent. Those derivatives are exactly what
gradient-based inverse design and Jacobian-based experiment design consume.

Measured by projecting the SG and surrogate Jacobians onto each right singular
direction of the true Jacobian and taking the cosine of the directional
derivatives, over four device families (`scripts/run_gradient_fidelity.py`):

| Training budget | mean cos inside identifiable rank | mean cos outside | mean value error (symlog) |
|---:|---:|---:|---:|
| 300 | +0.47 | +0.003 | 1.133 |
| 10000 | **+0.504** | **−0.001** | **0.252** |

**The control that makes this a finding rather than an artefact.** The obvious
alternative explanation is undertraining. It is excluded: over a 33× increase
in training budget the *value* error falls 4.5× while the outside-subspace
agreement stays pinned at zero. There is nothing to learn there, so more
training does not help — which is what the ill-posedness predicts.

**Consequence.** "The surrogate is accurate" and "the surrogate's gradients are
usable" are different claims, and the identifiability spectrum states exactly
which directions the second one covers. This is the finding that ties the
project's forward-model, inverse-problem and experiment-design threads
together.

---

### DES-01 — the incumbent uncertainty acquisition is *worse* than random for identifiability
| | |
|---|---|
| **Category** | active learning |
| **Severity** | HIGH (supersedes the H4b framing) |
| **Status** | VERIFIED |

SCI-02 / H4b reported that `max_std` showed "no distinguishable advantage over
random". Measured properly — 4 device families × 5 budgets × 12 random seeds,
scored on identifiable rank against the SG Jacobian, with acquisition allowed
to see only the surrogate — it is actively worse, while information-based
design is consistently better (`scripts/run_experiment_design.py`):

| Strategy | mean rank Δ vs random | win / tie / loss |
|---|---:|---|
| `max_std` (incumbent) | **−0.31** | 2 / 9 / 9 |
| `d_optimal` | **+0.39** | 5 / 15 / 0 |
| `null_space` | **+0.39** | 5 / 15 / 0 |
| `std_x_nullspace` | +0.24 | 4 / 14 / 2 |
| `e_optimal` | −0.06 | 2 / 13 / 5 |

**Why.** Predictive uncertainty answers "where is the forward model unsure?".
The inverse problem needs "which measurement constrains a direction I cannot
currently see?". Here those questions point in different directions.

The information criteria are textbook (Fedorov 1972; Atkinson & Donev 1992) —
**no novelty is claimed for the method**. What is new is the measurement that
it helps on this map and that uncertainty does not. The gain is real but
modest (~0.4 of a rank unit on a base of 3–4), and it is obtained *despite*
planning with a surrogate Jacobian correlating only +0.01 … +0.40 with truth
(GRAD-01). Both bounds are stated rather than hidden.

---

### IDENT-02 — the result survives, but the honest headline is 3–4, not 3–5
| | |
|---|---|
| **Category** | scientific claim |
| **Severity** | — (verification) |
| **Status** | VERIFIED |

Stress-tested across parameterisation dimension, bias count, bias range,
solver grid, doping level, finite-difference step, and a bootstrap over which
biases were measured (`scripts/run_identifiability_robustness.py`,
`outputs/identifiability_robustness/`).

**88 measurements. Identifiable rank 1–6, median 3.**

At the reference conditions (P = 16, 19 biases to 0.9 V, grid 301, FD step
0.01 decades, level 1e22) the four families give **3, 4, 3, 3** — so the
headline is **3–4 of 16**, not 3–5. Every "3–5" in the README, paper draft,
novelty audit and release gates has been corrected. The previous value came
from a single run against the pre-BUG-13 solver; the LDD family in particular
uses 5e23 m⁻³ source/drain doping, inside the band BUG-13 corrupted.

Where the extremes come from, so the range is not mistaken for scatter:

* **rank 1** occurs only at a *reduced bias range* (v_max = 0.6, graded
  family) — fewer trustworthy biases, less information. Expected.
* **rank 5–6** occurs only at *larger finite-difference steps* (0.02–0.05
  decades). A larger step lifts the differencing signal above the analysis
  noise floor, so it resolves more directions of the *estimator* — it does not
  reveal more physics. Reported as an estimator effect, not as a better result.

Bootstrap over which biases were measured (400 replicates, reference
conditions):

| Family | median | p05 | p95 | range |
|---|---:|---:|---:|---:|
| step symmetric | 2 | 2 | 3 | 1–3 |
| step asymmetric | 4 | 4 | 4 | 3–4 |
| graded | 3 | 2 | 3 | 1–3 |
| LDD | 3 | 2 | 3 | 2–3 |

**The decisive axis is the parameterisation dimension: the identifiable rank
does not grow with P.** Quadrupling the number of profile parameters from
P = 8 to P = 32 leaves the rank at 3–4. "N of 16" is therefore not a statement
about the parameterisation — it is a property of what a terminal I–V
measurement can determine. That is the stronger of the two possible readings,
it is the one the evidence supports, and it is what makes GRAD-01 follow.

---

## 7. Accepted limitations (not defects)

| ID | Limitation | Why accepted |
|---|---|---|
| LIM-01 | Terminal-current noise floor ~2e−6 A/m² near equilibrium | Irreducible in a density-based formulation at float64; now *measured and reported* per solve rather than assumed away. ADR-0002. |
| LIM-02 | 2D MOS-cap solves Poisson only (no continuity/current) | Explicitly scoped; unchanged by this audit. |
| LIM-03 | Boltzmann statistics; degenerate doping (>~5e25 m⁻³) out of range | Documented; `carrier_clipping_active` now flags saturation per solve. |
| LIM-04 | No interface traps, no quantum confinement | Documented. |
| LIM-05 | Constant mobility (no field- or doping-dependence) | Hook exists in `ScharfetterGummel1D.__init__`; not implemented. |

---

## 9. Generation 0 of the audit loop (2026-08-25)

Run under the operator ruling of 2026-08-25. The loop's first finding was that
the repository's only commit was the **pre-audit** project: both prior audit
cycles existed solely as uncommitted working-tree state. Adoption commit
`c115757f3e9829cd1feb8bb86d739bfd74ff2dcf` on `loop/champion`, parent `6577f4b`
(untouched). Full ledger: `docs/audit/AUDIT_g0.md`. Decisions:
`docs/gen/DECISIONS.md`. Supersession record:
`docs/PROVENANCE_BIFURCATION_g0.md`.

### PROV-06 — the repository had bifurcated; `HEAD` was the pre-audit project
| **Severity** | CRITICAL | **Status** | VERIFIED (adopted) |

`git archive 6577f4b src | tar -x` and re-running the same physics:

| | `6577f4b` | working tree |
|---|---|---|
| `src` modules | 34 | 40 |
| tests collected | 42, in 4 files | 246, in 13 files |
| `SGConfig(equilibrate=…)` | **`TypeError` — absent** | present |
| built-in potential rel. error | 2.7558e-07 | 7.243e-14 |
| mass action max\|np−1\| | 6.1019e-03 | 2.934e-09 |

`6577f4b`'s 42-test suite is exactly the "42-test suite" `README.md` describes as
pre-audit. 204 of 246 collected tests (83%) and 6 of 40 source modules were
untracked, including `test_sg_numerics.py` — the 58-test regression suite for
BUG-01 … BUG-13. Every manifest in `outputs/` named that commit as its provenance.

Closed by adopting the tree, after preserving it to two external paths (212 files,
digest-of-digests `9cd95213c1a7979f358743865dc133e998897705e55ae5c622eecd333a204cdd`,
both copies verified 212/212) and attesting the commit against that manifest
(**164/164 byte-identical, 0 mismatched, 0 missing**).

### PROV-02 — `git_is_dirty()` was blind to untracked files
| **Severity** | CRITICAL | **Status** | VERIFIED |

`git status --porcelain --untracked-files=no`. Measured on a scratch repository:
a tree missing three source modules returns `False`. A manifest could therefore
report a tree missing 6 source modules and 83% of the test suite as clean —
indistinguishable from a fixed typo. Untracked files now count;
`tracked_modified`, `untracked` and `tree_digest` are separate manifest fields;
the flag is derived from the counts so the two cannot disagree. Digest measured
at 28 ms over 166 files / 4.1 MB. `ADR-0006`.
Regression: `tests/test_provenance_g0.py` (16 tests). AH-08 pre-fix outcome
recorded: `git_is_dirty() == False` on a tree missing three modules.

### PROV-01 — every manifest was gitignored
| **Severity** | HIGH | **Status** | VERIFIED |

`git ls-files outputs/` returned only `results.json` and `results_summary.md`;
`outputs/results/manifest.json` was matched by the `outputs/*` ignore rule, so a
fresh clone shipped the headline results with **no provenance record at all**.
All 42 files under `outputs/` are now tracked.

### PROV-03 — the adopted tree has no attestable origin
| **Severity** | HIGH | **Status** | **OPEN — PERMANENT** |

Nothing in git records who produced the adopted code, when, in what order, or
against what evidence. The adoption commit makes the tree attestable *from here
forward*; it cannot make its past attestable. **No candidate in any generation
may mark this closed.**

### PROV-04 — manifests naming a commit that cannot have produced them
| **Severity** | HIGH | **Status** | SUPERSEDED (recorded, not edited) |

Nine of eleven manifests name `6577f4b`; two (`smoke`, `surrogate_ensemble`)
carry no `git` block at all, and `surrogate_ensemble` records artefact paths under
`/home/claude/…` — a different machine from every other manifest. The manifests
are protected (`R-3`) and were **not** edited; `docs/PROVENANCE_BIFURCATION_g0.md`
records per manifest why `6577f4b` cannot have produced it. Seven rows are marked
*not re-verified* rather than assumed — `AH-07`.

### SCI-08 — the claim surface mixed two mutually exclusive code states
| **Severity** | CRITICAL | **Status** | VERIFIED |

The published solver-quality figures were **not** stale guesses: they reproduce
exactly on `6577f4b` (`2.7558e-07` measured against a published `2.8e-7`). They
described the pre-audit solver, while the *same* documents quoted the working
tree for the 240-test badge and all of D1–D20. No single code state reproduced
the whole claim surface. `RELEASE_READINESS` marked "Reference solver validated
✅" citing precisely these two figures.

Withdrawn: `2.8e-7` → `7.24e-14` (X15); `7.6e-6` → `2.93e-9` (X16);
`1.32e-2 → 7.62e-6` (1730×) → `6.77e-3 → 9.7e-10` (7.0e6×) (X17).
Regression: `tests/test_claim_surface_g0.py`, which re-measures rather than
hard-coding, so it keeps working as the solver improves. AH-08 pre-fix: 5 failed
/ 1 passed.

### SCI-11 — identifiability stated without its regime
| **Severity** | HIGH | **Status** | VERIFIED (one instance parked) |

`inverse/identifiability.py` is scrupulous ("the **local** Jacobian", "at one
operating point") and `papers/draft.md` labels it three times, but `README.md`
used the word `local` exactly once — about *local doping*, unrelated. Seven
unqualified statements were measured across the claim surface; six were corrected
(README 51, 70, 267, 340; `RELEASE_READINESS` 72, 189) and now carry the operating
point, noise level, parameterisation dimension and observation count (PH-21).
`papers/draft.md:255` is **parked** under `R-3` and pinned by a test that fails if
the count moves in either direction (`DEC-g0-4`).

### GRAD-02 — NaN gradients in the ohmic boundary condition
| **Severity** | HIGH | **Status** | VERIFIED |

`torch.where` evaluates both branches. For large positive `C_s`,
`-C + sqrt(C²+4)` underflows to exactly `0.0`, the discarded branch is `inf`, and
backward computes `0 × inf = NaN` in the *selected* branch. Bisected onset
(40 steps): `C_s = 1.3922e8`, i.e. **N = 1.3922e24 m⁻³** — the top **21.4%** of
the solver's own documented 1e21–1e25 m⁻³ range.

### GRAD-03 — …and in float32 it covers the *whole* envelope
| **Severity** | HIGH | **Status** | VERIFIED |

Found by the generation-0 **falsifier** candidate (g0c5), pointed at the audit's
own scoping of GRAD-02. Networks here train in float32, which cancels far
earlier: first NaN at `C_s = 7.079e3` (**N = 7.08e19 m⁻³**, *below* the envelope).
Sampling the documented envelope in float32: **41 of 41 points** return NaN
gradients — 100%, not 21.4%.

**Blast radius, measured rather than assumed: no published number is affected.**
The only caller, `losses.boundary_residuals`, receives `C_s_bdy` as data with no
`requires_grad_` (`trainer.py:262`), so autograd never walks the `d/dC_s` path. A
float32 PINN boundary-loss backward at N = 1e21, 1e24 and 1e25 m⁻³ produced
non-finite gradients in **0 of 26** weight tensors. **D1 and ADR-0004 are not
confounded.** The defect fires only where doping itself carries a gradient —
inverse design, and the Jacobian the identifiability analysis is built on, where
float32 returns `grad = [1e-08, nan]` at N = 1e24 m⁻³.

Closed by candidate **g0c2**: `log n = asinh(C/2)`, `log p = −asinh(C/2)`.
Branchless, exact in every dtype, derivative `1/sqrt(4+C²)` finite everywhere.
Measured after the fix: 0 non-finite of 402 points in both dtypes; gradient
relative error **0.000e+00** in float64 (was 4.39e-16) and 8.19e-08 in float32
(was 1.63e-07); mass-action deviation 2.22e-16 (was 3.66e-15).
Regression: `tests/test_ohmic_gradient_g0.py` (41 tests). AH-08 pre-fix: 17
failed / 22 passed.

### CI-01 — **REOPENED**, then **ACCEPTED-PERMANENT** at generation 9
| **Severity** | MEDIUM | **Status** | **ACCEPTED-PERMANENT** (was OPEN) |

§6b recorded CI-01 as VERIFIED against `.github/workflows/ci.yml`. That file was
**untracked**: never committed, never pushed, never executed. The gate clause
"CI matrix green including the Windows job" was therefore unevaluable, which §6 of
the loop specification scores as FAIL, not skip. The workflow is now committed
(`c115757`) but `R-4` prohibits `git push`, so it still has not run. `SPEC-g0-3`
records this as expected-to-remain-open rather than quietly green.

> **Status correction, generation 9.** The generation-8 ruling put a decision
> ahead of the command — remote, or no remote — and it went unanswered for three
> cycles. The stated default fired: `CI-01` is **`ACCEPTED-PERMANENT`**, and the
> cost statement the status owes is `docs/G9_RESULT.md` §1.4. The cost is
> reviewed each generation for growth and has grown: the static support-floor
> scan the declared floor rests on covered 96 files at generation 7 and covers
> 110 now, so the *unevidenced* surface is larger, not the claim stronger.
> `docs/OPERATOR_TASKS.md` OT-1 stands unwithdrawn and records the reversion
> condition — if a remote is added, the status reverts and the cost statement is
> superseded forward rather than deleted. A status that read "OPEN" for nine
> generations had stopped describing anything, which is the defect this ledger
> exists to catch.

> **Cost review, generation 10.** The status requires the cost to be reviewed for
> growth each generation rather than remembered, so this is that review rather
> than a restatement. Generation 10 adds source modules and test modules, so the
> statically-scanned surface the declared floor rests on grows again; the file
> count is recorded in `LOOP_STATE_v7.json` under `python_support_floor_scan`
> with the generation-7 and generation-9 values beside it, so the direction is
> visible without re-reading three state files. The scan can only *falsify* a
> floor, never confirm one, and it cannot see dependency resolution at all;
> nothing in this repository has ever run on linux or darwin. `OT-1` stands and
> the reversion condition is unchanged.

### DOC-03a — the test-count badge is checked against collection, not passes
| **Severity** | LOW | **Status** | **RESOLVED at close (2026-08-26)** |

> **Resolution.** The premise below — *"the guard cannot be tightened without
> breaking its own regex against the badge text"* — does not hold. The regex now
> accepts either word and the check asserts the one it actually measures, so the
> badge reads `tests-N%20collected` and guard and badge agree on *what* is being
> counted rather than only on the integer. Two lines in
> `tests/test_notebooks.py::TestDocumentedTestCountIsHonest`. Recorded because
> the generation-10 entry stated an obstruction it had not tried, which is a
> smaller version of the defect this file exists for: an untested claim written
> in the same voice as a measured one.

`README.md` carries a badge reading `tests-N%20passing`, and
`tests/test_notebooks.py::TestDocumentedTestCountIsHonest` asserts that `N`
equals what `pytest --collect-only` **collects**. The suite collects more than it
passes, because some tests skip with a stated reason. The number is therefore
honest as a *collected* count and loose as a *passing* one, and the guard cannot
be tightened without breaking its own regex against the badge text.

Found at generation 10 while repairing a separate instance of the same class: the
capability table in the same file restated the total by hand and had drifted by
more than a hundred tests. That row now points at the badge rather than carrying
its own number, on the same argument `DOC-07` makes about commit messages —
removing an unguardable number beats updating one. The badge's own wording is
left alone and recorded here, because changing it silently breaks the only guard
that maintains it.

### S-3 — duplicate ohmic implementations
| **Severity** | (no Phase-A severity assigned) | **Status** | OPEN, equivalence pinned |

Two implementations remain (`solvers/_ohmic_bc`, `pinn/ohmic_boundary_values`).
Generation 0 promoted the reformulation rather than a merge, so `SPEC-g0-7` is
satisfied by its property-test route: their equivalence is now pinned in **both
value and gradient** over 402 points across the envelope, both signs, against a
central finite difference of the NumPy implementation (max relative difference
asserted < 1e-6). Structural merges were built and measured as candidates g0c3
and g0c4; see `docs/gen/CANDIDATES_g0.md` for why neither was promoted.

---

## 10. Generations 1-5 of the audit loop (2026-08-25)

Champion `b5218b1`. Full account: `docs/gen/FINAL_REPORT_v1.md`.
Re-verification evidence: `docs/CLAIM_EVIDENCE_MATRIX.md` section 6.

### SEC-02 - library code executed code from checkpoints
| **Severity** | MEDIUM | **Status** | VERIFIED (generation 1) |

`trainer.py:386` used `weights_only=False` unconditionally; `adapters.py:237`
fell back to it behind a `warnings.warn`, which `SW-03` rejects (a warning is not
a status flag the caller is forced to read, and it fires only once the unsafe
load is underway). Removal was made safe by measurement: **all seven** checkpoints
shipped in `outputs/` load cleanly under `weights_only=True`, so the fallback
guarded nothing. Guard is an AST walk, not a substring search, with two controls.

### PKG-04 - library `exec_module`d a file from the source checkout
| **Severity** | MEDIUM | **Status** | VERIFIED (generation 2) |

`adapters.py` reached `parents[3]/"scripts"/run_benchmark_sweep.py` and executed
it at runtime (`SW-17`). `PKG-02` had "closed" this in the first cycle by
improving the error message; the `exec_module` call survived. Measured reachable:
`outputs/smoke/manifest.json` has `type: None` and takes that branch, so the fix
is a move rather than a deletion. `load_deep_ensemble` now lives in
`bayesian/ensembles.py`; the script delegates to it, leaving one definition
(`SW-02`).

### API-05 - minibatch sampling read the global RNG
| **Severity** | MEDIUM | **Status** | VERIFIED (generation 3) |

`train_surrogate` drew batch indices from the global torch RNG, so two identical
calls gave different models (`091450bf7c0965bb` vs `cc67824aa4e606ff`) and
ensemble members differed by ambient state as well as by seed (`SW-09`). Now a
local generator seeded from `cfg.seed`. **The full-batch path every experiment
actually uses is bit-identical pre- and post-fix** (`c3aa71f10f7f8172`, same loss
to every digit), so no published number can shift.

### SW-04a - the environment probe failed silently
| **Severity** | MEDIUM | **Status** | VERIFIED (generation 4) |

`environment_info()` ended in `except Exception: pass`, so a failed CUDA probe
silently removed the `cuda_*` keys - a reader could not tell "no GPU" from "probe
raised". Keys are now always present and the failure is recorded.

### DOC-05, DOC-06 - prose contradicted by measurement
| **Severity** | LOW | **Status** | VERIFIED (generation 5) |

The GaAs constants comment still said "not exercised in M1-M2" after four tests
began exercising them; the README suite timing had drifted twice in one session
and is now measured with n and a range (64.0 s, n=3, 61-65 s).

### REPRO-01 - `run_identifiability.py` vs its 2026-08-19 artefact
| **Severity** | MEDIUM | **Status** | **OPEN - UNRESOLVABLE** |

41 of 375 leaves differ; median relative drift `1.906e-08`, max `5.840e-02`.
**No claim is affected**: zero integer leaves changed, so all four identifiable
ranks and all four `rank_vs_noise` tables are identical.

Runtime nondeterminism was ruled out in two stages. The forward Jacobian is
bit-identical across six runs and two thread configurations. The script itself,
re-run twice on the current tree, is **bit-identical to itself (375 leaves, 0
differing)**, and `run_identifiability_robustness.py` reproduced bit-identically
across 3287 leaves.

The difference therefore lies in the tree that produced the 2026-08-19 artefact,
which cannot be identified - its manifest says `6577f4b`, dirty. That explanation
cannot be confirmed, because confirming it would require the tree that was lost.
This is the first quantified cost of `PROV-03`: 41 numbers that can never be
explained. Recorded as unresolvable rather than closed.

---

## 11. Generation 6 and the terminal adversarial generation (2026-08-25)

Champion `a59255e`. Full record: `docs/gen/GEN_g6.md`,
`docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`, `docs/audit/AUDIT_g6.md`.

### S-1 - global non-identifiability, demonstrated by witness
| **Severity** | (seed item, not a defect) | **Status** | MEASURED |

13 witness pairs among 1,999,000 examined at d=4, log-uniform prior 1e21-1e23
m^-3, 16 biases over 0.15-0.90 V, distinguishability floor 2.0e-02 = max(noise
2.0e-02, solver discretisation 1.5e-03). The closest differs by **8.18x in doping**
at one anchor and **1.23% in I-V**. All three pairs tested survive 4x grid
refinement (N=301/601/1201) and `tol_carrier=1e-12`; pair 0's distance FALLS under
refinement. Oracle-arbitrated throughout (`ADR-0007`).

For scale, `C14`'s equivalence twins were *constructed* along locally flat
directions and differ by 1.26x. These were *found by search* and differ by 8.18x.

Contraction at the instrument's own 2% noise is **not measured**: prior importance
sampling collapses (ESS 1.0 of 2000, all variance ratios 0.000), which would report
as "4 of 4 directions contract". That is the estimator dying, not the device
speaking, and it is marked unsupported rather than published.

### PH-22 retro-sweep - no second GRAD-02
| **Severity** | n/a | **Status** | NEGATIVE RESULT |

Two quantities cross the solver/network dtype boundary and both degrade gracefully:
SI<->scaled doping round trip 1.678e-16 (float64) vs 8.714e-08 (float32); symlog
2.030e-15 vs 8.823e-07. `bernoulli` has one NumPy definition in a module that does
not import torch. Envelopes now annotated per dtype and pinned by tests.

### NB-02 - the CI notebook step destroys committed evidence
| **Severity** | MEDIUM | **Status** | OPEN |

`scripts/build_notebooks.py` regenerates the twelve notebooks WITHOUT executed
outputs; `test_notebooks.py` asserts they HAVE outputs, which is the evidence for
claim `U1`. CI is green only because `Test` (step 5) precedes the generator
(step 6), and nothing states that dependency. Running the step verbatim destroyed
all twelve notebooks' outputs; restored from HEAD via `git archive` and
digest-verified 12/12.

### PROV-07 - ignored directories are invisible to all three provenance fields
| **Severity** | MEDIUM | **Status** | OPEN |

Found by the terminal adversarial generation (A-6, F3). A source module placed
inside a `.gitignore`'d directory leaves `dirty=False`, both counts zero, and the
`tree_digest` unchanged - the same shape of failure `PROV-02` was opened for.

MEDIUM rather than a repeat CRITICAL: the exclusion is deliberate and documented
(regenerable build output is not divergence), and the attack requires code to be
deliberately placed in an ignored path, which is not this repository's structure
and has not occurred. Candidate fix for a later generation: hash the ignore rules
themselves into the tree digest.

### BUG-14 recurrence - fixed and made permanent
| **Severity** | LOW | **Status** | VERIFIED |

`tests/test_robustness.py:278` read a UTF-8 manifest with the platform encoding.
Fixed, and the file-by-file part of BUG-14 removed: an AST guard now fails on any
text `open`/`read_text`/`write_text` without `encoding=` in `src/`, `scripts/` or
`tests/`.

### A recurring defect in this loop's own output
| **Severity** | (process) | **Status** | RECORDED |

Four times a guard whose subject is source code was implemented by matching
characters, and tripped on prose describing the very thing it guards:
`weights_only=False` (g1), `"scripts"` (g2), `torch` (g6), and `def bernoulli` via
`git grep` (g6 - the test matched its own search pattern once committed). All four
were fixed by reading the syntax tree. Recorded as a defect class rather than four
slips.

Also: commit `1a090f0` carried a message stating "420 passed" when the suite was
437 passed / 1 failed. `R-4` forbids amending, so the error stands in history and
is corrected in `d3b7693`.

---

## 12. Close addendum (2026-08-28) — the one bounded refinement

Authorised by the operator ruling of 2026-08-28 §2 after the loop had closed:
chart G's ten untested witness pairs, the barriers recounted over what survives,
the register updated, chart L excluded by name. `docs/CLOSE_ADDENDUM.md`.

### WITNESS-04 - narrowed to chart L, not resolved
| **Severity** | MEDIUM | **Status** | OPEN, LOAD-BEARING, NARROWED |

`WIT-02` was enacted at close over a corpus in which two of the three committed
witness sets had never been fully refined. Chart G is now 13 of 13 refined with
12 surviving, so the finding no longer covers it. **Chart L remains at 0 of 37
and has never been through the battery**, and it is the set the dimension
reading rests on. Both sets that have been refined lost members - 1 of 13 in
chart G and 6 of 13 in chart J - so the base rate of loss is not zero and what
chart L would lose is unknown.

### DOC-08 - a quantifier or metric without its denominator or scope
| **Severity** | LOW | **Status** | ENACTED AND GUARDED |

Third instance of one family, after the bare `ruff_exit: 0` and the wrongly
scoped mypy count: a statement that is true as written and reads as its
opposite. The flagship was *"all tested pairs survive 4x grid refinement"* over
a set in which 3 of 13 pairs had been tested. The sweep found three live
instances, every one of them in a spine item or a headline, which is where the
family concentrates - the sentence that compresses a result is the sentence that
drops the denominator. Rule and guard: `docs/RULES_ENACTED.md`,
`tests/test_quantifier_scope_doc08.py`.

### HIST-01 - the recorded champion commits are not in this clone's history
| **Severity** | MEDIUM | **Status** | OPEN |

Every `LOOP_STATE` file from generation 8 onward records `champion_commit` and
`machinery_commit` hashes that `git cat-file` cannot resolve in this working
tree, and `champion_per_generation` names none that it can. Eight guards fail
because of it, and they failed **before** any change in this session - measured
by stashing the working tree and running the suite against the tree as
committed: 894 collected, 878 passed, 8 failed, 8 skipped.

The baselines those files carry record `failed: 0`, which was true where they
were taken and is not true here. Nothing in the tree can repair it: the objects
are absent, `R-4` forbids rewriting the commits that would have contained them,
and inventing hashes that resolve would be worse than the gap. What is done
instead is to state it - `LOOP_STATE_v9.json`'s pytest baseline carries the
failure count with its cause, and `tests/test_loop_state_addendum.py` fails if a
future state file claims zero failures without saying which are pre-existing.

Adjacent to `REPRO-01` and distinct from it: `REPRO-01` lost a *working tree*,
this loses the *object graph* the state files point into.

### The recount did not weaken anything, and that is checkable
| **Severity** | (process) | **Status** | RECORDED |

The barrier criterion and the ridge/basin classifier were imported with their
hashes checked against `outputs/g9/preregister.json` and
`outputs/g10/preregister.json`, and the run refuses to start on a mismatch. All
thirteen depths reproduce generation 10's bit for bit before the subset is
taken, so the recount is a recount rather than a re-measurement. The outcome
table was hashed to disk before the first solve, keyed on the classifier's own
output, so no reading was available that the classifier does not produce.
