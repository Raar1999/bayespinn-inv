# BayesPINN-Inv: quantitative results (SG-supervised surrogate)

All errors measured against the Scharfetter-Gummel oracle. Ensemble M=5, 35,457 params/member.

## H1 Forward accuracy (held-out profiles, V>=0.1V)

- Step junctions: median rel. I-V error **4.1%**, p90 9.4%
- Graded junctions: median rel. I-V error **4.6%**, p90 10.7%

## H2 Inverse recovery vs measurement noise

| Noise | Median recovery error (decades) | 1σ coverage |
|---|---:|---:|
| 0% | 0.004 | 100% |
| 2% | 0.003 | 80% |
| 5% | 0.003 | 60% |
| 10% | 0.009 | 40% |

## H3 UQ calibration (interval coverage on held-out I-V)

| Interval | Empirical (raw) | Recalibrated | Nominal |
|---|---:|---:|---:|
| ±1.0σ | 30% | 71% | 68% |
| ±1.64σ | 57% | 92% | 90% |
| ±2.0σ | 67% | 96% | 95% |

*Variance-inflation temperature T=2.19 fit on a validation split (standard fix for ensemble overconfidence).*

## H4 Active-learning gain

| Bias subset | # biases | Median recovery error (decades) |
|---|---:|---:|
| low 3 biases | 3 | 0.008 |
| high 3 biases | 3 | 0.006 |
| all 13 | 13 | 0.004 |