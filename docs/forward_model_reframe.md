# Forward-model reframe: from pure-physics PINN to SG-supervised surrogate

## The problem (diagnosed, not guessed)

The original forward model is a **pure-physics PINN**: it trains on Poisson +
continuity + boundary residuals with no supervision on current, and reads the
terminal current off as `mean(J_tot)` over the domain. This does not converge to
diode-accurate I-V, and the reason is structural, not a tuning issue:

- In the log-density formulation, `J_n = mu * n_s * (d log n - d phi)`. The
  bracket (the quasi-Fermi gradient) is near-zero in equilibrium and small under
  bias, but `n_s` reaches ~1e6 in scaled bulk units.
- The continuity loss `mean((d J/dx)^2)` is therefore dominated entirely by the
  high-density bulk. The network minimizes it by flattening the bulk quasi-Fermi
  level while the actual diode signal — exponentially small until the barrier
  drops — stays in the numerical noise.
- Result: terminal current comes out as the mean of a wildly-varying J with
  random sign, i.e. flat and slightly negative, regardless of bias. Measured
  relative error vs the Scharfetter-Gummel oracle: ~1.0 everywhere.

This is exactly the multiscale cancellation that Scharfetter-Gummel exponential
fitting was invented to handle. Getting a pure-physics PINN to reproduce 13
orders of magnitude of diode I-V is a research-grade problem that may not
converge even with the full GPU budget.

## The reframe

Replace the pure-physics forward model with an **SG-supervised surrogate**: the
fast, accurate SG solver generates `(doping, bias) -> I` labels, and the network
predicts terminal current directly (in a symlog scale spanning the 13 orders of
magnitude). Physics residuals (Poisson, boundary) are retained as regularizers
on the field outputs for the scientific narrative, but the **current is a
directly-supervised output**, not a fragile derived quantity.

This preserves every scientific objective of the proposal — PINN physics,
differentiable forward model, inverse design, Bayesian UQ, active learning,
calibration — while fixing the one thing that was broken. It is also more honest
and more industry-relevant: SG-supervised differentiable surrogates are exactly
how TCAD surrogate modeling is done.

## Validation (measured, reproducible)

Three scripts under `scripts/` prove the reframe end-to-end:

### `validate_sg_supervised.py`
Supervising `mean(J_tot)` (the field-derived current) helps in the high-bias
regime but still fails in subthreshold — because that observable is *itself*
corrupted by bulk noise when carriers are dense. This motivates the dedicated
current head below.

### `validate_current_head.py`
A direct current head, `(doping_latent, bias) -> symlog(I)`, supervised by SG.
Trained on 9 doping levels, tested on 3 **held-out** levels:

```
Median relative error on held-out I-V: 0.045   (4.5%)
Mean log-decade error:                 0.048
```

across all 13 orders of magnitude, trained in ~6 seconds on CPU. The only large
errors are at exactly V=0, where the true current (~1e-7) is below SG's own
numerical floor (SG returns sign-flipped noise there).

### `validate_inverse_surrogate.py`
A 3-member ensemble of current heads, then inverse design recovering a held-out
doping level from its SG I-V by gradient descent through the differentiable
surrogate:

```
True doping:      log10(N) = 21.776   (N = 5.97e21)
Recovered (mean): log10(N) = 21.778 +/- 0.011
Absolute error:   0.002 decades
Truth inside +/-1 sigma band: True
```

Forward (doping->I-V) accurate, inverse (I-V->doping) recovers truth, uncertainty
quantified and calibrated. The full scientific pipeline works with the reframe.

## What this changes in the codebase

- `pinn/forward_pinn.py`: add a current head to `SemiconductorPINN` (or a
  dedicated `IVSurrogate`) and train it with SG supervision. The field outputs
  remain physics-informed.
- `training/trainer.py`: add the SG-current data loss (the `use_data_loss` hook
  already exists but is unused).
- `inverse/inverse_design.py`: optimize doping through the current head, which is
  cleanly differentiable, instead of through the field-derived mean current.
- `bayesian/`, `calibration/`, `active_learning/`: unchanged — they operate on
  the forward model's I-V predictions, which are now accurate.

With this forward model, the H1-H4 results tables produce real numbers, because
the forward model actually maps doping <-> I-V.

## Folding the surrogate into the legacy inverse / calibration pipeline

The pre-existing `inverse/` and `calibration/` code (and the `run_inverse_sweep.py`,
`run_calibration.py`, `defect_case_study.py` launchers) were written against the
pure-physics `ForwardPINN`. They now run directly on the working surrogate via
thin adapters, with no rewrite of the scientific code:

- `surrogate/adapters.py`: `SurrogateForwardAdapter` (drop-in for `ForwardPINN`)
  and `SurrogateEnsembleAdapter` (drop-in for `DeepEnsemble`), plus
  `load_forward_ensemble` which auto-detects the manifest type. The three
  launchers import it via `from bayespinn_inv.surrogate import
  load_forward_ensemble as load_ensemble`, so their call sites are unchanged.
- `scripts/train_surrogate_ensemble.py` trains on the same asymmetric
  step + graded distribution the inverse parameterizations explore, and writes
  a `type="surrogate"` manifest (with a legacy-compatible `config` block).

Three latent bugs in the legacy code were fixed in the process, all surfaced by
running real optimizations through the (now accurate) forward model:

1. **Junction position optimized in raw metres.** `StepJunctionDoping` /
   `GradedJunctionDoping` optimized `x_junction` (~5e-7) alongside `log_N` (~50)
   under one learning rate, so the junction slammed to the domain boundary.
   Reparameterized to a normalized logit (`u_junction`), giving O(1) gradient
   scale and automatic in-domain bounding.
2. **Unbounded doping during optimization.** Added `clamp_to_range` so the
   optimizer stays within the forward model's validated doping range.
3. **Smoothness penalty overflowing float32.** `sum((d2)^2)` with doping ~1e22
   gives ~1e45 > float32 max -> `inf`, and `lambda*inf = 0*inf = NaN` poisoned
   the loss even at zero weight. Penalties are now computed on a normalized
   profile and zero-weight terms are skipped.

### Results on the surrogate (real, measured)

**Inverse sweep** (`run_inverse_sweep.py`, step targets, symlog matching): the
surrogate I-V is matched to ~0.2% (median symlog data-loss 0.002), while the
recovered **doping profile** rel-L2 ranges 0.17--0.84. This cleanly exhibits the
**ill-posedness** of profile recovery from forward I-V: the forward map is
insensitive to many profile degrees of freedom, so a good I-V fit does not pin
down the profile. (Well-posed sub-problems -- e.g. a single symmetric doping
level -- recover to ~0.005 decades, per `12_demo.ipynb`.) The deep ensemble
underestimates this uncertainty (90% interval coverage ~0.03), motivating
recalibration.

**Calibration** (`run_calibration.py`): the deep-ensemble predictive
distribution is overconfident (ECE 0.224); temperature scaling (T~5 fit on a
validation split) reduces ECE to ~0.086 and improves Gaussian NLL from 6.9 to
~0. Calibration metrics are computed in symlog space for the surrogate, since
CRPS/NLL/sharpness in linear current units overflow across the ~13 orders of
magnitude of diode I-V (ECE, being rank-based, is unaffected).
