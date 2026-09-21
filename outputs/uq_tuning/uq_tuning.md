# Were MC-dropout and SWAG simply mistuned?

Each method gets a grid over the hyperparameters that drive its uncertainty. The winner is selected by calibrated NLL on the **calibration split** -- never on the test set -- and only then evaluated against the deep ensemble on the held-out sets.

## MC-dropout: dropout-rate grid

| dropout p | val NLL | median sigma | val median rel err |
|---:|---:|---:|---:|
| 0.01 | -1.930 | 0.1083 | 5.77% |
| 0.02 | -1.847 | 0.1317 | 5.44% |
| 0.05 | -1.502 | 0.1870 | 5.73% |
| 0.1 | -1.371 | 0.2398 | 10.51% |
| 0.2 | -0.958 | 0.3442 | 19.39% |

## SWAG: SWA learning rate x posterior scale

| SWA lr | scale | val NLL | median sigma | val median rel err |
|---:|---:|---:|---:|---:|
| 0.0002 | 0.25 | -2.118 | 0.0033 | 2.37% |
| 0.0002 | 0.5 | -2.117 | 0.0047 | 2.43% |
| 0.0002 | 1.0 | -2.115 | 0.0066 | 2.52% |
| 0.0005 | 0.25 | -2.162 | 0.0174 | 2.26% |
| 0.0005 | 0.5 | -2.140 | 0.0247 | 2.63% |
| 0.0005 | 1.0 | -2.097 | 0.0349 | 3.31% |
| 0.001 | 0.25 | -1.858 | 0.0261 | 3.45% |
| 0.001 | 0.5 | -1.827 | 0.0372 | 3.25% |
| 0.001 | 1.0 | -1.749 | 0.0535 | 3.96% |
| 0.002 | 0.25 | -1.044 | 0.0489 | 11.73% |
| 0.002 | 0.5 | -1.108 | 0.0731 | 10.61% |
| 0.002 | 1.0 | -1.160 | 0.1130 | 12.70% |

## Best of each, against the untuned ensemble

| Method | Interp rel err | rho(sigma,\|err\|) | NLL calibrated | CRPS | sigma inflation (extrap) | error inflation (extrap) | Train (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deep_ensemble` | 2.64% | +0.798 | -1.452 | 0.1324 | 21.3x | 12.1x | 23.1 |
| `mc_dropout_tuned` | 5.91% | +0.299 | 18.737 | 0.1631 | 1.4x | 12.4x | 7.3 |
| `swag_tuned` | 2.90% | +0.486 | 1.814 | 0.1269 | 2.5x | 13.2x | 4.4 |

Selected: MC-dropout `{'dropout_p': 0.01, 'train_seconds': 7.2671802043914795, 'n_networks': 1, 'params': 35457, 'forward_passes_per_prediction': 30}`, SWAG `{'swa_lr': 0.0005, 'scale': 0.25, 'train_seconds': 4.413067579269409, 'n_networks': 1, 'params': 35457, 'forward_passes_per_prediction': 30, 'snapshots': 20}`.
