# BayesPINN-Inv: quantitative results (SG-supervised surrogate)

Ensemble M=5, 35,457 params/member. All errors are against the Scharfetter-Gummel oracle.

Every statistic reports `n` and a 95% interval (bootstrap for continuous quantities, Wilson score for coverages). Labels are used only where the oracle's own noise-floor check passes: 13 of 169 candidate (profile, bias) pairs were dropped as numerically untrustworthy.

Measured current dynamic range of the training labels: **10.0 decades** (8.89e-05 to 8.13e+05 A/m^2).

## H1 Forward accuracy

Three disjoint test sets. Interpolation lies between training doping levels; **extrapolation lies outside the training band on both sides**; family transfer uses graded junctions, a profile shape absent from training.

| Test set | Median rel. error (95% CI) | p90 | max | n |
|---|---:|---:|---:|---:|
| Interpolation | 2.8% (2.0%–3.9%) | 7.0% | 33.9% | 72 |
| **Extrapolation** | 38.2% (23.1%–89.7%) | 860.6% | 6894.6% | 68 |
| Family transfer (graded) | 84.2% (75.0%–106.4%) | 151.5% | 179.4% | 60 |

## H2 Inverse recovery vs measurement noise

Single symmetric doping level recovered from the I-V curve — the *well-posed* sub-problem. This is a one-parameter identification, not profile recovery; see `docs/NOVELTY_AUDIT.md` for the identifiability of the full profile problem.

| Noise | Median error (decades, 95% CI) | 1σ coverage (95% CI) | n |
|---|---:|---:|---:|
| 0% | 0.0018 (0.0013–0.0024) | 75% (60%–86%) | 40 |
| 2% | 0.0020 (0.0012–0.0024) | 78% (62%–88%) | 40 |
| 5% | 0.0033 (0.0019–0.0054) | 48% (33%–63%) | 40 |
| 10% | 0.0072 (0.0047–0.0101) | 28% (16%–43%) | 40 |

## H3 UQ calibration

Variance-inflation factor T = 2.09, fitted on a disjoint calibration split (n=48). **Pre and post are measured on the identical test set** (n=140) — the previous version of this table compared two different sets.

| Interval | Empirical (raw) | Recalibrated | Nominal |
|---|---:|---:|---:|
| ±1.0σ | 29% (22%–37%) | 62% (54%–70%) | 68% |
| ±1.64σ | 46% (38%–54%) | 90% (84%–94%) | 90% |
| ±2.0σ | 59% (50%–66%) | 98% (94%–99%) | 95% |

## H4a Bias-subset ablation (not active learning)

| Bias subset | # biases | Median recovery error (decades) | n |
|---|---:|---:|---:|
| low 3 | 3 | 0.0047 (0.0020–0.0068) | 8 |
| mid 3 | 3 | 0.0065 (0.0045–0.0158) | 8 |
| high 3 | 3 | 0.0095 (0.0022–0.0263) | 8 |
| all 13 | 13 | 0.0018 (0.0012–0.0026) | 8 |

## H4b Active learning vs random baseline

Sequential acquisition: at each round pick the next bias to measure, then re-invert. `max_std` picks the bias of greatest ensemble disagreement (model uncertainty only — no test labels); `random` picks uniformly among trustworthy biases.

| Budget | Random (decades) | Max-std (decades) | Distinguishable? |
|---|---:|---:|---|
| 2 | 0.0064 | 0.0110 | no |
| 3 | 0.0048 | 0.0092 | no |
| 4 | 0.0039 | 0.0042 | no |
| 6 | 0.0034 | 0.0037 | no |

**Conclusion:** NO budget shows a statistically distinguishable advantage for uncertainty-driven acquisition over random selection.

## H5 Is the uncertainty useful?

A predictive standard deviation is only worth reporting if it tracks the actual error.

Spearman rank correlation between predicted sigma and |error|: **+0.824** (n=200). Median |error| across ascending sigma quartiles: 0.0080, 0.0307, 0.3732, 0.2538 (monotone: False).

Out-of-distribution awareness — does the ensemble know when it is extrapolating?

| Test set | Median sigma | Median \|error\| | n |
|---|---:|---:|---:|
| interpolation | 0.0072 | 0.0119 | 72 |
| extrapolation | 0.1134 | 0.1404 | 68 |
| family_graded | 0.6661 | 0.2654 | 60 |

Going from interpolation to extrapolation, sigma inflates **15.7x** while the error inflates **11.8x**. sigma tracks the extrapolation error.
