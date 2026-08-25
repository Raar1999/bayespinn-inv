# Identifiability-aware experiment design vs uncertainty acquisition

Sequential bias selection at 2% measurement noise. Acquisition sees the **surrogate** Jacobian and sigma only; scoring uses the **SG** Jacobian, which no strategy had access to. `random` is averaged over 12 seeds.

## Verdict

* `max_std`: mean identifiable-rank delta vs random **-0.31** (win/tie/loss 2/9/9 over 20 device x budget comparisons)
* `d_optimal`: mean identifiable-rank delta vs random **+0.39** (win/tie/loss 5/15/0 over 20 device x budget comparisons)
* `e_optimal`: mean identifiable-rank delta vs random **-0.06** (win/tie/loss 2/13/5 over 20 device x budget comparisons)
* `null_space`: mean identifiable-rank delta vs random **+0.39** (win/tie/loss 5/15/0 over 20 device x budget comparisons)
* `std_x_nullspace`: mean identifiable-rank delta vs random **+0.24** (win/tie/loss 4/14/2 over 20 device x budget comparisons)

**Best non-random strategy: `d_optimal` — beats random.**

## Identifiable rank by budget (mean over reps)

| Device | Strategy | k=2 | k=3 | k=4 | k=6 | k=8 |
|---|---|---:|---:|---:|---:|---:|
| `step_symmetric` | `random` | 1.67 | 1.58 | 2.00 | 2.42 | 2.17 |
| `step_symmetric` | `max_std` | 1.00 | 2.00 | 2.00 | 3.00 | 3.00 |
| `step_symmetric` | `d_optimal` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `step_symmetric` | `e_optimal` | 2.00 | 2.00 | 2.00 | 2.00 | 2.00 |
| `step_symmetric` | `null_space` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `step_symmetric` | `std_x_nullspace` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `step_asymmetric` | `random` | 2.00 | 2.83 | 3.42 | 3.67 | 4.00 |
| `step_asymmetric` | `max_std` | 2.00 | 2.00 | 2.00 | 3.00 | 4.00 |
| `step_asymmetric` | `d_optimal` | 2.00 | 3.00 | 4.00 | 4.00 | 4.00 |
| `step_asymmetric` | `e_optimal` | 2.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| `step_asymmetric` | `null_space` | 2.00 | 3.00 | 4.00 | 4.00 | 4.00 |
| `step_asymmetric` | `std_x_nullspace` | 2.00 | 3.00 | 4.00 | 4.00 | 4.00 |
| `graded` | `random` | 1.67 | 1.83 | 2.08 | 2.67 | 2.67 |
| `graded` | `max_std` | 1.00 | 1.00 | 1.00 | 1.00 | 2.00 |
| `graded` | `d_optimal` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `graded` | `e_optimal` | 2.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| `graded` | `null_space` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `graded` | `std_x_nullspace` | 2.00 | 2.00 | 2.00 | 2.00 | 2.00 |
| `ldd` | `random` | 1.75 | 2.25 | 2.75 | 2.75 | 3.00 |
| `ldd` | `max_std` | 2.00 | 2.00 | 3.00 | 3.00 | 3.00 |
| `ldd` | `d_optimal` | 2.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| `ldd` | `e_optimal` | 1.00 | 1.00 | 2.00 | 3.00 | 3.00 |
| `ldd` | `null_space` | 2.00 | 3.00 | 3.00 | 3.00 | 3.00 |
| `ldd` | `std_x_nullspace` | 2.00 | 3.00 | 3.00 | 3.00 | 3.00 |

## Surrogate-vs-SG Jacobian agreement

The acquisition is only as good as the Jacobian it plans with. A low correlation here bounds how well *any* Jacobian-based strategy can possibly do.

| Device | Pearson r (surrogate J vs SG J) | Trustworthy biases |
|---|---:|---:|
| `step_symmetric` | +0.329 | 15 |
| `step_asymmetric` | +0.010 | 16 |
| `graded` | +0.318 | 15 |
| `ldd` | +0.399 | 13 |
