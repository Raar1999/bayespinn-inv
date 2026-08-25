# Surrogate accuracy does not imply surrogate gradients

A surrogate trained only on terminal I--V is constrained only in the directions that measurement can see. Along the rest its derivatives are unconstrained -- and those derivatives are exactly what gradient-based inverse design and Jacobian-based experiment design consume.

## Verdict

* at 10000 epochs: mean |cos| inside identifiable subspace +0.504, outside -0.001
* value error improved 1.1327 -> 0.2518 symlog (300 -> 10000 epochs)
* outside-subspace agreement moved +0.003 -> -0.001 (flat => not an undertraining artefact)
* HYPOTHESIS SUPPORTED: gradients are trustworthy only inside the identifiable subspace

## Directional agreement at 10000 epochs

`cos` is the cosine between the true and surrogate directional derivatives along each right singular vector of the **true** Jacobian, ordered by singular value. Directions at or below the identifiable rank are the ones the measurement determines.

| Device | Identifiable rank | Value error (symlog) | mean cos inside | mean cos outside | overall Pearson r |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 3 / 16 | 0.0040 | +0.556 | +0.031 | +0.350 |
| `step_asymmetric` | 4 / 16 | 0.3372 | +0.377 | -0.004 | -0.004 |
| `graded` | 3 / 16 | 0.1799 | +0.552 | -0.003 | +0.339 |
| `ldd` | 3 / 16 | 0.4862 | +0.532 | -0.028 | +0.379 |

## Is it just undertraining?

If the out-of-subspace disagreement were an optimisation failure it would shrink with training budget. It does not.

| Epochs | mean value error (symlog) | mean cos inside | mean cos outside |
|---:|---:|---:|---:|
| 300 | 1.1327 | +0.513 | +0.003 |
| 1000 | 0.9557 | +0.507 | +0.002 |
| 2500 | 0.8273 | +0.496 | +0.001 |
| 10000 | 0.2518 | +0.504 | -0.001 |

## Per-direction detail at 10000 epochs

### `step_symmetric` (identifiable rank 3)

| Direction | sigma (true) | cosine | ||J_surr v|| / ||J_true v|| |
|---:|---:|---:|---:|
| 0 **(identifiable)** | 1.048 | +0.858 | 1.88 |
| 1 **(identifiable)** | 0.2937 | +0.718 | 8.31 |
| 2 **(identifiable)** | 0.04796 | +0.092 | 27.5 |
| 3 | 0.03017 | +0.419 | 15.3 |
| 4 | 0.006251 | +0.021 | 144 |
| 5 | 0.002284 | +0.096 | 192 |
| 6 | 0.001055 | +0.005 | 822 |
| 7 | 0.0002807 | -0.000 | 5.74e+03 |
| 8 | 0.0001053 | -0.002 | 1.76e+04 |
| 9 | 3.27e-05 | -0.000 | 4.43e+04 |
| 10 | 1.397e-05 | +0.002 | 2.71e+04 |
| 11 | 1.107e-05 | +0.001 | 1.05e+05 |
| 12 | 6.548e-07 | +0.000 | 1.8e+06 |
| 13 | 7.931e-08 | +0.001 | 1.09e+07 |
| 14 | 3.37e-08 | -0.000 | 7.77e+07 |
| 15 | 0 | -0.139 | 1.42e+16 |

### `step_asymmetric` (identifiable rank 4)

| Direction | sigma (true) | cosine | ||J_surr v|| / ||J_true v|| |
|---:|---:|---:|---:|
| 0 **(identifiable)** | 2.498 | +0.677 | 0.159 |
| 1 **(identifiable)** | 0.3941 | +0.930 | 0.918 |
| 2 **(identifiable)** | 0.1851 | -0.075 | 11.3 |
| 3 **(identifiable)** | 0.02749 | -0.023 | 9.34 |
| 4 | 0.01228 | -0.011 | 118 |
| 5 | 0.008695 | -0.020 | 72.4 |
| 6 | 0.002482 | -0.010 | 265 |
| 7 | 0.0007104 | +0.002 | 1.92e+03 |
| 8 | 0.0005237 | -0.001 | 3.01e+03 |
| 9 | 5.998e-05 | +0.000 | 3.34e+04 |
| 10 | 5.16e-05 | -0.003 | 6.72e+03 |
| 11 | 4.494e-05 | -0.001 | 5.91e+04 |
| 12 | 6.063e-06 | +0.000 | 8.47e+04 |
| 13 | 3.008e-06 | -0.001 | 8.21e+04 |
| 14 | 1.277e-06 | +0.000 | 5.46e+05 |
| 15 | 1.303e-08 | +0.000 | 3.58e+07 |

### `graded` (identifiable rank 3)

| Direction | sigma (true) | cosine | ||J_surr v|| / ||J_true v|| |
|---:|---:|---:|---:|
| 0 **(identifiable)** | 1.065 | +0.862 | 2.08 |
| 1 **(identifiable)** | 0.2688 | +0.694 | 8.39 |
| 2 **(identifiable)** | 0.0478 | +0.102 | 37.7 |
| 3 | 0.01811 | +0.078 | 69.8 |
| 4 | 0.005049 | +0.116 | 123 |
| 5 | 0.002277 | -0.002 | 432 |
| 6 | 0.0004334 | +0.012 | 1.78e+03 |
| 7 | 0.0002652 | +0.001 | 3.21e+03 |
| 8 | 5.535e-05 | +0.009 | 1.98e+04 |
| 9 | 1.931e-05 | +0.008 | 1.55e+04 |
| 10 | 4.94e-06 | -0.008 | 1.18e+05 |
| 11 | 3.645e-06 | -0.004 | 3.68e+05 |
| 12 | 4.456e-07 | -0.000 | 1.72e+06 |
| 13 | 2.663e-07 | +0.001 | 5.8e+06 |
| 14 | 2.056e-08 | +0.001 | 1.64e+08 |
| 15 | 0 | -0.254 | 1.76e+16 |

### `ldd` (identifiable rank 3)

| Direction | sigma (true) | cosine | ||J_surr v|| / ||J_true v|| |
|---:|---:|---:|---:|
| 0 **(identifiable)** | 1.471 | +0.829 | 1.62 |
| 1 **(identifiable)** | 0.1812 | +0.473 | 7.06 |
| 2 **(identifiable)** | 0.06447 | +0.295 | 21 |
| 3 | 0.02131 | +0.145 | 32.6 |
| 4 | 0.008219 | +0.072 | 93.3 |
| 5 | 0.002195 | +0.008 | 248 |
| 6 | 0.001325 | -0.012 | 414 |
| 7 | 0.0008828 | -0.002 | 493 |
| 8 | 0.0002616 | +0.011 | 3.21e+03 |
| 9 | 0.0001133 | -0.006 | 1.45e+03 |
| 10 | 2.163e-05 | +0.002 | 6.3e+04 |
| 11 | 9.513e-06 | -0.002 | 1.14e+05 |
| 12 | 1.936e-06 | +0.000 | 1.59e+06 |
| 13 | 0 | -0.736 | 1.43e+16 |
| 14 | 0 | +0.058 | 6.09e+15 |
| 15 | 0 | +0.103 | 1.32e+17 |
