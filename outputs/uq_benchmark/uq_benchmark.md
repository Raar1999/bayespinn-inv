# Uncertainty backends compared under one protocol

Every method sees identical splits, identical SG labels, identical filtering, identical metrics. Temperature is fitted on the disjoint calibration split; pre/post are measured on the same test set.

Labels: 144 used, 12 of 156 dropped below the oracle's noise floor.

## Forward accuracy (median relative error, 95% CI)

| Method | Interpolation | Extrapolation | Family transfer | n |
|---|---:|---:|---:|---:|
| `deterministic` | 2.4% (1.8%-3.2%) | 76.2% (28.4%-115.7%) | 171.9% (93.1%-252.4%) | 72 |
| `deep_ensemble` | 2.6% (2.0%-3.6%) | 37.9% (22.8%-98.2%) | 80.6% (56.8%-94.9%) | 72 |
| `deep_ensemble_budget_matched` | 7.5% (5.6%-9.5%) | 50.7% (25.1%-86.8%) | 72.2% (59.8%-90.7%) | 72 |
| `mc_dropout` | 10.6% (8.3%-14.5%) | 38.6% (27.7%-58.2%) | 34.3% (28.9%-40.2%) | 72 |
| `swag` | 2.4% (2.1%-3.0%) | 86.0% (32.3%-110.0%) | 171.0% (90.8%-245.7%) | 72 |

## Uncertainty quality

| Method | rho(sigma,\|err\|) | NLL raw | NLL calib | CRPS | ECE raw | ECE calib | Sharpness | T |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `deep_ensemble` | +0.798 | -0.579 | -1.452 | 0.1324 | 0.240 | 0.118 | 0.0920 | 2.10 |
| `deep_ensemble_budget_matched` | +0.731 | 0.189 | -0.565 | 0.1411 | 0.143 | 0.056 | 0.1488 | 2.46 |
| `mc_dropout` | +0.367 | -0.215 | 1.175 | 0.1128 | 0.104 | 0.163 | 0.2742 | 0.27 |
| `swag` | +0.486 | 196.408 | 2.779 | 0.1764 | 0.280 | 0.200 | 0.0085 | 6.33 |

## Interval coverage (pre -> post temperature scaling)

| Method | +/-1σ | +/-1.64σ | +/-2σ | n |
|---|---:|---:|---:|---:|
| `deep_ensemble` | 30% -> 65% (nom 68%) | 49% -> 91% (nom 90%) | 59% -> 99% (nom 95%) | 141 |
| `deep_ensemble_budget_matched` | 52% -> 82% (nom 68%) | 68% -> 94% (nom 90%) | 76% -> 96% (nom 95%) | 141 |
| `mc_dropout` | 85% -> 45% (nom 68%) | 96% -> 68% (nom 90%) | 99% -> 74% (nom 95%) | 141 |
| `swag` | 11% -> 52% (nom 68%) | 18% -> 61% (nom 90%) | 22% -> 64% (nom 95%) | 141 |

## Out-of-distribution awareness

Ratio of median sigma / median |error| on each set, relative to interpolation. A backend that *knows* it is extrapolating inflates sigma at least as fast as the error grows.

| Method | sigma inflation (extrap) | error inflation (extrap) | sigma inflation (family) | error inflation (family) |
|---|---:|---:|---:|---:|
| `deep_ensemble` | 21.3x | 12.1x | 110.5x | 22.4x |
| `deep_ensemble_budget_matched` | 12.9x | 5.6x | 33.4x | 7.4x |
| `mc_dropout` | 1.1x | 2.9x | 1.2x | 3.5x |
| `swag` | 2.6x | 25.7x | 1.0x | 41.2x |

## Cost

| Method | Networks | Train (s) | Forward passes / prediction | Eval (s) |
|---|---:|---:|---:|---:|
| `deterministic` | 1 | 7.2 | 1 | 4.7 |
| `deep_ensemble` | 5 | 31.4 | 5 | 0.2 |
| `deep_ensemble_budget_matched` | 5 | 6.7 | 5 | 0.2 |
| `mc_dropout` | 1 | 9.2 | 30 | 0.4 |
| `swag` | 1 | 6.3 | 30 | 1.0 |

ECE estimator floor at M=5: 0.088; at T=30: 0.017. An ECE at the floor is not evidence of miscalibration.
