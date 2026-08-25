# ADR-0002 — Report the terminal-current noise floor rather than remove it

**Status:** Accepted · **Date:** 2026-08-19 · **Relates to:** AUDIT_MASTER BUG-04, LIM-01

## Context

The SG terminal current is a difference of two large, nearly-equal numbers. At
equilibrium `B(+Δ)n_{i+1}` and `B(−Δ)n_i` cancel *exactly*; near equilibrium
they cancel down to the exponentially small true current. With scaled densities
reaching 1e6 and 1/h ~ 1e4, each term is ~1e10, so double precision leaves an
absolute error ~2e−6 in scaled units — a floor of ~1e−6 A/m² on a quantity whose
true value at V = 0 is exactly zero.

The project's headline claim is accuracy "across 13 orders of magnitude of
diode I–V". Where that range ends is therefore a first-order scientific
question, not an implementation detail.

## What was fixed for free

Using `B(+Δ)/B(−Δ) = exp(−Δ)`, the flux bracket factors *exactly* as
`B(−Δ)·n_i·expm1(u)` with `u = log(n_{i+1}/n_i) − Δ`, i.e. `expm1` of the
**quasi-Fermi potential drop across the face**, which is identically zero in
equilibrium. This is an algebraic identity, not an approximation.

Measured: on an exact Boltzmann state the direct difference gives
max|Jₙ| = 5.86e−7 A/m²; the `expm1` form gives 1.39e−13 A/m² — **4.2 million×
less cancellation**. Away from equilibrium the two agree to 1.9e−11 relative.
Adopted unconditionally: strictly better, no cost.

## The problem that remains

The rewrite does not remove the *observed* equilibrium current (~7e−7 A/m²),
because the cancellation simply moves into the log-difference:
`log n_{i+1} − log n_i − Δ` differences numbers of magnitude ~14 and so carries
~3e−15 of round-off, amplified by the majority density (1e6) and 1/h (1.2e4).

Eliminating it requires carrying `log n` (or the quasi-Fermi potential) as the
solver's primary unknown throughout — a full reformulation.

## Options considered

| Option | Assessment |
|---|---|
| **A. Reformulate the whole solver in quasi-Fermi / Slotboom variables** | Rejected for this cycle. It is the correct long-term answer, but it is a rewrite of the continuity assembly, the boundary conditions and the SRH linearisation, on a solver that is accurate everywhere the project actually operates (V ≥ 0.05 V). High regression risk for a regime whose true answer is *known to be zero*. |
| **B. Iterate harder near equilibrium** | Rejected — measured to make things worse (ADR-0001). |
| **C. Quietly clip small currents to zero** | Rejected outright. This is exactly the "fix by masking" the audit charter forbids; it would also hard-code an assumption about where the floor is. |
| **D. Keep the density formulation, adopt the free `expm1` improvement, and make the floor a measured, reported, first-class quantity** | **Chosen.** |

## Decision

`DeviceState` gains two members:

- `current_noise_floor` — the face-to-face standard deviation of `Jₙ + Jₚ`.
  Since `div(Jₙ + Jₚ) = 0` holds *exactly* in steady state, the total current
  must be constant across the device; any observed spread is pure numerical
  error. This is an assumption-free error bar that costs nothing to compute:
  the oracle measuring its own precision.
- `current_is_trustworthy(snr=10)` — the honest boundary of the validated
  range.

Downstream code must respect the flag. `build_sg_dataset` consumers,
`run_results.py` and `sg_forward_jacobian` all filter on it and *report how
many points were dropped*.

## Why this is more than a workaround

The floor turned out to be **predictive**, not merely descriptive. Measured
independently: the relative precision of the terminal current under a tiny
input perturbation tracks `1/SNR` where `SNR = |I| / current_noise_floor`,
across five decades of SNR. That makes the diagnostic usable as an *a priori*
step-size and data-quality criterion, and it immediately caught a real error:
the first version of the identifiability analysis differenced oracle outputs at
SNR ≈ 10 and produced a plausible-looking singular spectrum that was entirely
noise (see NOVELTY_AUDIT §3).

## Consequences

- The claim "13 orders of magnitude" is replaced by a **measured** dynamic
  range, reported per run, with untrustworthy points excluded and counted.
- Near-equilibrium bias points are excluded from training labels rather than
  fitted. This is a real reduction in the advertised range and is stated as
  such.
- LIM-01 is recorded as an accepted, bounded limitation with a known cure
  (option A) should the low-bias regime ever become scientifically necessary.

## Validation

`tests/test_sg_numerics.py::TestFluxCancellation` (exact-equilibrium state
gives < 1e−10; identity with the direct form to 1e−8 away from equilibrium) and
`::TestNoiseFloorDiagnostics` (current conserved to 1e−4 where trusted;
equilibrium flagged untrustworthy; forward bias flagged trustworthy).
