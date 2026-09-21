# Is the identifiability result robust?

Every number below is at **2% relative measurement noise**, the headline condition. Each axis varies one factor and holds the rest at the conditions the original result was measured at.

## Verdict

* Identifiable rank across **88 independent measurements**: **1-6** (median 3).
* Rank as a function of parameterisation dimension P: `{8: [4], 12: [3, 4], 16: [3, 4], 24: [2, 3, 4], 32: [3]}`.
* Rank saturates as P grows: **True**.

The rank does **not** grow in proportion to the number of profile parameters. The limit is therefore a property of the terminal I--V measurement, not of how finely the doping profile happens to be parameterised -- which is the stronger of the two possible readings, and the one that makes the result worth reporting.

## A_parameterisation (varying `P`)

| Family | P | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 8 | **4** | 4 | 15 | 3.92 |
| `step_symmetric` | 12 | **4** | 4 | 15 | 3.70 |
| `step_symmetric` | 16 | **3** | 3 | 15 | 3.57 |
| `step_symmetric` | 24 | **2** | 2 | 15 | 3.39 |
| `step_symmetric` | 32 | **3** | 3 | 15 | 3.26 |
| `step_asymmetric` | 8 | **4** | 4 | 16 | 4.91 |
| `step_asymmetric` | 12 | **4** | 4 | 16 | 5.67 |
| `step_asymmetric` | 16 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 24 | **4** | 4 | 16 | 7.52 |
| `step_asymmetric` | 32 | **3** | 3 | 16 | 8.55 |
| `graded` | 8 | **4** | 4 | 15 | 4.35 |
| `graded` | 12 | **3** | 3 | 15 | 4.10 |
| `graded` | 16 | **3** | 3 | 15 | 3.96 |
| `graded` | 24 | **3** | 3 | 15 | 3.77 |
| `graded` | 32 | **3** | 3 | 15 | 3.64 |
| `ldd` | 8 | **4** | 4 | 13 | 7.77 |
| `ldd` | 12 | **3** | 3 | 13 | 8.87 |
| `ldd` | 16 | **3** | 3 | 13 | 8.11 |
| `ldd` | 24 | **3** | 3 | 13 | 7.78 |
| `ldd` | 32 | **3** | 3 | 13 | 8.18 |

## B_n_bias (varying `n_bias`)

| Family | n_bias | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 7 | **4** | 5 | 5 | 2.80 |
| `step_symmetric` | 13 | **4** | 4 | 10 | 3.34 |
| `step_symmetric` | 19 | **3** | 3 | 15 | 3.57 |
| `step_symmetric` | 31 | **4** | 4 | 24 | 3.64 |
| `step_asymmetric` | 7 | **3** | 3 | 6 | 5.92 |
| `step_asymmetric` | 13 | **3** | 3 | 11 | 6.21 |
| `step_asymmetric` | 19 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 31 | **3** | 3 | 26 | 6.46 |
| `graded` | 7 | **4** | 5 | 5 | 3.12 |
| `graded` | 13 | **4** | 4 | 10 | 3.71 |
| `graded` | 19 | **3** | 3 | 15 | 3.96 |
| `graded` | 31 | **3** | 3 | 25 | 4.18 |
| `ldd` | 7 | **3** | 3 | 5 | 5.91 |
| `ldd` | 13 | **3** | 3 | 9 | 7.42 |
| `ldd` | 19 | **3** | 3 | 13 | 8.11 |
| `ldd` | 31 | **3** | 3 | 21 | 8.79 |

## B_v_max (varying `v_max`)

| Family | v_max | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 0.6 | **2** | 2 | 13 | 33.88 |
| `step_symmetric` | 0.75 | **2** | 2 | 14 | 10.00 |
| `step_symmetric` | 0.9 | **3** | 3 | 15 | 3.57 |
| `step_asymmetric` | 0.6 | **2** | 2 | 15 | 11.11 |
| `step_asymmetric` | 0.75 | **5** | 5 | 15 | 10.58 |
| `step_asymmetric` | 0.9 | **4** | 4 | 16 | 6.34 |
| `graded` | 0.6 | **1** | 1 | 13 | 51.87 |
| `graded` | 0.75 | **3** | 3 | 14 | 11.04 |
| `graded` | 0.9 | **3** | 3 | 15 | 3.96 |
| `ldd` | 0.6 | **2** | 2 | 10 | 56.26 |
| `ldd` | 0.75 | **2** | 2 | 12 | 31.11 |
| `ldd` | 0.9 | **3** | 3 | 13 | 8.11 |

## D_grid (varying `grid_n`)

| Family | grid_n | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 201 | **4** | 4 | 15 | 3.57 |
| `step_symmetric` | 301 | **3** | 3 | 15 | 3.57 |
| `step_symmetric` | 601 | **4** | 4 | 14 | 3.35 |
| `step_asymmetric` | 201 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 301 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 601 | **4** | 4 | 15 | 5.91 |
| `graded` | 201 | **3** | 3 | 15 | 3.96 |
| `graded` | 301 | **3** | 3 | 15 | 3.96 |
| `graded` | 601 | **4** | 4 | 14 | 3.72 |
| `ldd` | 201 | **4** | 4 | 13 | 8.11 |
| `ldd` | 301 | **3** | 3 | 13 | 8.11 |
| `ldd` | 601 | **3** | 3 | 12 | 7.43 |

## E_level (varying `level`)

| Family | level | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 1e+21 | **5** | 5 | 18 | 3.31 |
| `step_symmetric` | 1e+22 | **3** | 3 | 15 | 3.57 |
| `step_symmetric` | 5e+22 | **2** | 2 | 13 | 5.08 |
| `step_asymmetric` | 1e+21 | **3** | 3 | 18 | 5.62 |
| `step_asymmetric` | 1e+22 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 5e+22 | **5** | 5 | 13 | 6.11 |
| `graded` | 1e+21 | **5** | 5 | 18 | 3.48 |
| `graded` | 1e+22 | **3** | 3 | 15 | 3.96 |
| `graded` | 5e+22 | **3** | 3 | 13 | 5.72 |
| `ldd` | 1e+21 | **3** | 3 | 16 | 6.43 |
| `ldd` | 1e+22 | **3** | 3 | 13 | 8.11 |
| `ldd` | 5e+22 | **3** | 3 | 11 | 17.57 |

## F_rel_step (varying `rel_step`)

| Family | rel_step | Identifiable rank | Resolvable rank | Bias points kept | sigma1/sigma2 |
|---|---:|---:|---:|---:|---:|
| `step_symmetric` | 0.01 | **3** | 3 | 15 | 3.57 |
| `step_symmetric` | 0.02 | **4** | 4 | 15 | 3.57 |
| `step_symmetric` | 0.03 | **4** | 4 | 15 | 3.57 |
| `step_symmetric` | 0.05 | **4** | 4 | 15 | 3.57 |
| `step_asymmetric` | 0.01 | **4** | 4 | 16 | 6.34 |
| `step_asymmetric` | 0.02 | **5** | 5 | 16 | 6.34 |
| `step_asymmetric` | 0.03 | **6** | 6 | 16 | 6.34 |
| `step_asymmetric` | 0.05 | **6** | 6 | 16 | 6.34 |
| `graded` | 0.01 | **3** | 3 | 15 | 3.96 |
| `graded` | 0.02 | **4** | 4 | 15 | 3.96 |
| `graded` | 0.03 | **4** | 4 | 15 | 3.96 |
| `graded` | 0.05 | **4** | 4 | 15 | 3.96 |
| `ldd` | 0.01 | **3** | 3 | 13 | 8.11 |
| `ldd` | 0.02 | **4** | 4 | 13 | 8.11 |
| `ldd` | 0.03 | **4** | 4 | 13 | 8.11 |
| `ldd` | 0.05 | **4** | 5 | 13 | 8.12 |

## C. Bootstrap over which bias points were measured

Resampling the measured bias points gives the sampling distribution of the rank rather than one number.

| Family | median | p05 | p95 | min | max | histogram |
|---|---:|---:|---:|---:|---:|---|
| `step_symmetric` | 2 | 2 | 3 | 1 | 3 | `{1: 1, 2: 207, 3: 192}` |
| `step_asymmetric` | 4 | 4 | 4 | 3 | 4 | `{3: 16, 4: 384}` |
| `graded` | 3 | 2 | 3 | 1 | 3 | `{1: 1, 2: 39, 3: 360}` |
| `ldd` | 3 | 2 | 3 | 2 | 3 | `{2: 26, 3: 374}` |
