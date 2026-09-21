# Architecture & Design Decisions

This document captures **why** the code is structured the way it is, and the bugs we hit during development. It is intended for a new contributor (or future-you) who needs to understand non-obvious design choices.

> **Read this first: the forward model is the surrogate, not the PINN.**
> Much of the layout below dates from when `pinn/` held the forward model. It
> no longer does. The pure-physics PINN was measured at **100% median relative
> error** on terminal current and is retained as legacy infrastructure plus a
> documented negative result
> ([ADR-0004](adr/ADR-0004-pure-physics-pinn-is-legacy.md)). Everything the
> project claims about forward accuracy, inverse design, UQ, calibration and
> experiment design runs through `surrogate/` — the SG-supervised
> differentiable surrogate — and the UQ backends that matter live in
> `bayesian/surrogate_uq.py`, not in the `ForwardPINN`-based wrappers.

## High-level layout

```
src/bayespinn_inv/
├── physics/        Constants, De-Mari scaling — pure data + conversion functions
├── solvers/        Scharfetter–Gummel reference solver (deterministic oracle)
├── surrogate/      **The forward model.** SG-supervised differentiable I-V
│                   surrogate, symlog transform, ensemble, adapters
├── pinn/           LEGACY (ADR-0004): PINN network, residual losses,
│                   ForwardPINN wrapper. Not a working forward model.
├── training/       LEGACY: PINN training loop
├── data/           Doping profile families, TrainingExample factory, and
│                   `splits.py` — the single definition of the eval protocol
├── inverse/        Input-space autodiff inverse design + identifiability
├── bayesian/       UQ. `surrogate_uq.py` (ensemble/MC-dropout/SWAG over the
│                   surrogate) is the live path; the ForwardPINN-based
│                   DeepEnsemble/MCDropoutPINN/SWAG wrappers are legacy
├── calibration/    ECE, CRPS, reliability, temperature scaling
├── active_learning/ Acquisition strategies, AL loop driver, and `design.py`
│                   (D-/E-optimal + null-space experiment design)
├── benchmarks/     SG-vs-PINN quantitative comparison
└── visualization/  Publication-grade plots
```

## Cross-cutting invariants

1. **All solvers return a `DeviceState`** with the same field names and SI units. Downstream code is solver-agnostic.
2. **SI ↔ scaled conversions go through a single `Scaling` instance.** Never hardcode conversion factors.
3. **Doping convention:** $C(x) = N_D(x) - N_A(x)$ in m⁻³. Acceptors give negative $C$.
4. **Bias convention:** left contact (p-side) grounded; $V_a > 0$ applied at the right contact is **forward bias** for a P-on-left / N-on-right junction. Both SG and PINN use this. *This was wrong in early development; see "Bug history" below.*
5. **PINN outputs** are $(\phi_s, \log n, \log p)$ in scaled units. Conversions back to SI happen only at the solver boundary.
6. **Deterministic seeding:** every RNG (Python random, NumPy, PyTorch CPU, PyTorch CUDA) is seeded from a single `cfg.seed`. Ensemble members differ only by their `seed` field.

## Why each major design decision

### Why log-compressed doping latent?

Raw $C_s = C / n_i$ is $\sim 10^7$ for realistic doping (e.g. $10^{23}$ m⁻³). Feeding this directly into a tanh network saturates the first hidden layer at initialization, kills gradients, and the optimizer cannot recover. We use
$$\text{latent} = \operatorname{sign}(C) \cdot \log_{10}(1 + |C|/n_i)/10$$
which maps the typical doping range $[10^{21}, 10^{25}]$ m⁻³ into $[-0.9, +0.9]$. Bijective, smooth through zero, invertible.

### Why per-batch residual normalization?

The Poisson residual $r_\phi = d^2\phi_s/dx_s^2 - n_s + p_s + C_s$ has scale $\sim |C_s|_{\max} \sim 10^6$. The current residuals have scale $\sim \mu n_i \sim 10^{-3}$. Without normalization, the loss is dominated by Poisson, and the optimizer never learns the current physics. We divide each residual by its expected scale (per batch for Poisson, fixed for currents).

### Why ohmic boundary uses larger-root-first?

The naive formula $n_s = 0.5(C_s + \sqrt{C_s^2+4})$ catastrophically cancels for $C_s < 0$ when $|C_s|$ is large. For $C_s = -10^6$, float32 gives $n_s = 0$, then $\log(0) = -\infty$. Fix: compute the *larger* root first, then derive the smaller via $n_s p_s = 1$.

### Why three Bayesian methods with the same API?

We want a fair comparison across methods that's not buried in API differences. `EnsemblePrediction(mean, std, samples, quantile_lo, quantile_hi)` is what every method returns; downstream plotting/calibration/AL code doesn't care which method produced it.

### Why curriculum on bias?

Without curriculum, the loss at $V_a = 0.6$ V is dominated by exponentially-large injected carrier densities that the network has no hope of fitting from random init. Starting at $V_a = 0$ (equilibrium, well-conditioned) and ramping over the first 30% of training works robustly.

### Why NTK-style adaptive weighting?

Even with normalization, loss component magnitudes drift during training as the network learns one component faster than another. NTK gradient-norm balancing equalizes the *gradient contributions* of each component, which is the quantity the optimizer actually sees.

## Bug history

These are the bugs we hit and fixed. They're listed so the regression tests guarding against each one make sense.

### 1. Scharfetter–Gummel sign errors (early Phase 0)

Two independent sign bugs in the SG continuity solve:
- SRH Picard linearization had wrong signs on both the decay term and the RHS for both species.
- SG flux Bernoulli arguments were swapped; hole-flux overall sign was wrong.

Symptoms: equilibrium current was non-zero (~$10^{-3}$ A/m²); converged but to a wrong solution.

Test: `TestSGEquilibrium.test_V_bi_uniform_PN`, `test_mass_action`.

### 2. Ohmic-boundary numerical cancellation

See "Why ohmic boundary uses larger-root-first" above.

Symptom: `log(n) = -inf` in boundary loss for any doping over $\sim 10^{16}$ m⁻³.

Test: `TestOhmicBoundary.test_stable_at_extreme_doping`.

### 3. Doping latent saturation (training NaN cascade)

Raw $C_s \sim 10^7$ saturated tanh; gradient becomes zero; optimizer moves into nonsense; NaN by epoch 10.

Fix: `Scaling.doping_to_net_input()` log compression. Used in both `data/datasets.py` and `pinn/forward_pinn.py::ForwardPINN.doping_to_latent`.

Test: `TestScalingInvariants.test_doping_net_input_O1`, `TestEndToEndSmoke.test_training_no_nan_in_5_epochs`.

### 4. Residual scale mismatch

Loss dominated by Poisson term ($\sim 10^{12}$); current physics never learned.

Fix: `PhysicsParams.poisson_scale` and `current_scale`, set per batch by the trainer.

### 5. **Bias sign convention** (most impactful)

Both SG and PINN had `phi_right = phi_right_eq + V_a`, meaning $V_a > 0$ was **reverse bias** (increased the barrier), not forward bias. The PINN was being trained on a reverse-biased device, and the I-V looked nearly linear instead of exponential.

Fix: flipped to `phi_right = phi_right_eq - V_a` in both `solvers/scharfetter_gummel.py` and `pinn/losses.py::ohmic_boundary_values`.

Symptoms: SG ideality factor was 24 (should be ~1); current grew only $4\times$ over the bias range $[0.05, 0.65]$ V (should grow by $\sim e^{0.6/V_T} \sim 10^{10}$).

Test: `TestSGEquilibrium.test_forward_bias_increases_current`.

### 6. Inverse design final-eval grad crash

`InverseDesigner.design` calls `forward.iv_curve` inside `torch.no_grad()` for the final evaluation. But `iv_curve` internally requires autograd to compute spatial derivatives — `torch.no_grad()` disabled the graph and `autograd.grad` failed.

Fix: wrap `ForwardPINN.iv_curve()` and `.solve()` in `torch.enable_grad()`, with the original implementation moved to `_iv_curve_impl` and `_solve_impl`.

### 7. Catastrophic cancellation diagnostic comment in losses.py

Initial documentation said "if C_s >= 0:  n_s = 0.5 * ( C_s + sqrt(C_s^2 + 4))" but the matching code used `torch.where` which evaluates *both* branches, including the cancelling one for the unmatched sign. The actual computation was correct because the comparison is between actual computed values, not the formulas; left in for clarity.

## Test coverage matrix

| Invariant | Test |
|---|---|
| Scaling round-trip | `test_scaling_round_trip` |
| Doping latent bijection | `test_doping_net_input_invertible` |
| Latent magnitude O(1) | `test_doping_net_input_O1` |
| Bernoulli numerical stability | `test_bernoulli_*` (5 tests) |
| Equilibrium V_bi | `test_V_bi_uniform_PN` |
| Mass-action law | `test_mass_action` |
| Forward bias sign + ideality | `test_forward_bias_increases_current` |
| Ohmic boundary `n*p = 1` | `test_log_np_zero` |
| Ohmic boundary at extreme C | `test_stable_at_extreme_doping` |
| Network forward shapes | `test_forward_shapes` |
| Seed determinism | `test_seed_reproducibility`, `test_different_seed_differs` |
| ECE calibration | `test_ece_perfect`, `test_ece_overconfident` |
| CRPS Gaussian vs empirical | `test_crps_gaussian_vs_empirical` |
| NLL under correct model | `test_nll_under_correct_model` |
| End-to-end training (no NaN) | `test_training_no_nan_in_5_epochs` |

## 2D MOS-capacitor extension (stretch goal, §6.1 of proposal)

The `solvers/grid_2d.py` and `solvers/mos_cap_2d.py` modules implement the
2D MOS-capacitor test case from the proposal's §6.1. This was explicitly a
*stretch goal*; what's delivered and what's out of scope:

**Delivered and validated:**
- `Grid2D`: 2D rectangular finite-volume grid with a stacked
  semiconductor + gate-oxide geometry, harmonic-mean permittivity faces
  (the standard FV treatment for dielectric interfaces), and per-cell
  control volumes with correct boundary/corner weighting.
- `MOSCap2DSolver`: 2D nonlinear-Poisson solver with Maxwell-Boltzmann
  carrier statistics, Newton-Raphson with Armijo backtracking line search
  in the stiff regime and full Newton steps in the near-linear regime,
  Dirichlet contacts (substrate + gate) and zero-flux Neumann sides.
- Validation (9 unit tests in `tests/test_mos_cap_2d.py`):
  - Linear Poisson (zero doping) matches the analytical capacitor-divider
    surface potential within 5%.
  - Flat-band bulk potential sits at the bulk Fermi level.
  - Surface potential is monotonic in gate bias.
  - Carrier densities are exactly zero in the oxide.
  - The solution is x-invariant for a laterally-uniform device.
- `scripts/mos_cap_demo.py`: produces a C-V sweep, surface-potential-vs-bias
  comparison against the depletion approximation, and 2D field maps showing
  the inversion layer forming at the Si/SiO2 interface. The field maps are a
  clean textbook MOS-cap picture (inversion electrons at the interface,
  depleted holes, band bending concentrated near the surface).

**Out of scope (documented limitations):**
- **No current flow.** The solver is *quasi-equilibrium* Poisson +
  Boltzmann only. It models accumulation, depletion, and inversion-onset
  but not lateral current transport (MOSFET on-state). Adding 2D
  Scharfetter-Gummel continuity would be ~600 more lines.
- **Strong-inversion stiffness at heavy doping.** For N_A >= 1e22 m^-3 and
  large forward gate bias, the carrier exponential is numerically stiff and
  the damped-Newton solver does not robustly converge. The validated range
  is N_A <= 1e21 m^-3 across accumulation through inversion-onset. Proper
  strong-inversion handling needs nonlinear-Poisson Gummel iteration with
  carrier-density parameterization, which is a known TCAD technique not
  implemented here.
- **Bias continuation chaining is disabled in the demo.** Warm-starting
  each bias from the previous converged solution was found to corrupt the
  Newton state across the full accumulation->inversion range; fresh solves
  from the analytical linear initial guess converge reliably in ~3
  iterations, so the demo uses those instead.
- **Boltzmann, not Fermi-Dirac.** Degenerate doping (>~5e25 m^-3) is out of
  validity range. No quantum confinement, no interface traps.

**Why no 2D PINN.** The proposal envisioned a 2D PINN for the MOS-cap. The
1D PINN architecture in `pinn/network.py` is dimensionality-agnostic in
principle (the Fourier embedding and gated MLP generalize to 2D inputs by
expanding `in_dim` from 2 to 3 for (x, y, V_gate)). However, training a 2D
PINN to the accuracy needed for a meaningful inverse-design demonstration
requires substantially more compute than the 1D case, and the 2D SG
reference for *current*-based inverse problems isn't available (see above).
The 2D Poisson reference solver is provided as the foundation; the 2D PINN
forward/inverse pipeline is the natural next increment.
