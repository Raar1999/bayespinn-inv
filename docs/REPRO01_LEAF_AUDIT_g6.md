# REPRO01_LEAF_AUDIT_g6 — all 41 differing leaves, checked against the claim surface

**Ordered by** operator ruling of generation 6, §3.1 · **Generation** 6
**Comparison** `outputs/identifiability/identifiability.json` (2026-08-19, retired)
vs `outputs/identifiability_g1/identifiability.json` (regenerated under `c115757`+)
**Blocking:** generation 6 did not proceed past Phase A until this was complete.

---

## 1. Why this exists

Generation 1 reported the 41 differing leaves as "diagnostics only". **That was an
assertion, not a measurement, and it was wrong.** Checked leaf by leaf, **7 of the
41 do back published numbers**:

| leaf class | count | published claim |
|---|---:|---|
| `analysis_convergence[*]/sigma_ratio_1_2` | 2 | `papers/draft.md:169` — "$\sigma_1/\sigma_2 = 6.11$–6.13" |
| `devices/ldd/equivalence_twin/iv_max_rel_change` | 1 | **C14** — `README.md:80`, `papers/draft.md:31,175` |
| `devices/ldd/linear_response_check[*]/ratio` | 4 | **C15** — `README.md:316`, `papers/draft.md:167` |
| everything else | 34 | none |

The correct statement is not "these are diagnostics" but: **the leaves that do back
published numbers do not move those numbers at their published precision.** That is
a weaker and more useful claim, and it is measured below.

## 2. The three published numbers, re-measured

Per §3.1, any of the 41 backing a published number is re-measured against the
regenerated artefact or withdrawn. All three were re-measured. **None is withdrawn.**

### C14 — "1.26× doping change → 0.02–1.3% I–V change"

`iv_max_rel_change`, per family:

| family | 2026-08-19 | regenerated | rel. diff |
|---|---:|---:|---:|
| step_symmetric | `1.274966e-02` | `1.274966e-02` | `0.00e+00` |
| step_asymmetric | `2.995805e-03` | `2.995805e-03` | `0.00e+00` |
| graded | `2.384736e-03` | `2.384736e-03` | `0.00e+00` |
| **ldd** | `2.400007e-04` | `2.399989e-04` | `7.42e-06` |

Published range **0.02–1.3 %**. Measured range, both artefacts: **0.0240 % – 1.2750 %**.
Identical to four significant figures. The only family that moved is LDD, which sets
the *lower* end at 0.0240 % either way. **Claim holds, unchanged.**

### C15 — "ratios 0.995–1.04"

`linear_response_check[*]/ratio`, n = 16 (4 directions × 4 families):

| | min | max |
|---|---:|---:|
| 2026-08-19 | `0.994986` | `1.039707` |
| regenerated | `0.994986` | `1.039707` |

**Identical to six decimal places.** The extrema are attained by families other than
LDD, so the four LDD ratios that moved do not touch the published interval.
**Claim holds, unchanged.**

### `papers/draft.md:169` — "$\sigma_1/\sigma_2 = 6.11$–6.13"

`analysis_convergence[*]/sigma_ratio_1_2`, the FD-step × SNR-threshold sweep:

| entry | 2026-08-19 | regenerated |
|---:|---:|---:|
| 0 | `6.123041076885311` | `6.122948804926297` |
| 1 | `6.108705683143668` | `6.108705799601458` |
| 2 | `6.111116782967749` | `6.111116782967749` |
| 3 | `6.106977521076808` | `6.106977521076808` |
| 4 | `6.113690398551547` | `6.113690398551547` |

Range: **6.1070–6.1230** → **6.1070–6.1229**. The published `6.11–6.13` is an
outward-rounded interval over that sweep and covers both artefacts.
**Claim holds, unchanged.**

## 3. The other 34 leaves

- **16 × `parameter_sensitivity[*]`** — never published as numbers anywhere.
- **8 × `singular_values[*]`** — no numeric singular value is published. They feed the
  **integer** identifiable rank, and `0 / 79` integer leaves moved, so the rank is
  identical. `papers/draft.md:141` invokes Weyl's inequality to justify refusing to
  report values below the floor; it publishes no value.
- **8 × `linear_response_check[*]/{actual,predicted}`** — inputs to the published
  ratio, not published themselves. The ratio is covered above.
- **1 × `spectral_floor`, 1 × `entry_noise`** — `README.md:313` and
  `papers/draft.md:143` describe the floor's *role* in the method. Neither publishes
  its value. These two are the same quantity propagated, which is why they share a
  relative difference of `5.840e-02` — the largest of the 41, and on a number nobody
  quotes.

## 4. Verdict

- 7 of 41 leaves back a published number; **all three affected claims survive
  re-measurement at their published precision. Nothing is withdrawn.**
- 34 of 41 back nothing.
- Zero integer-valued leaves moved (`0 / 79`), so every rank — which is what the
  identifiability claim actually rests on — is identical.
- Generation 1's "diagnostics only" wording is **superseded** by this document. It
  reached the right conclusion by a route that had not been checked.

`REPRO-01` remains `UNRESOLVABLE-BY-CONSTRUCTION`.
**What was lost, and when:** the working tree that produced
`outputs/identifiability/identifiability.json` at 2026-08-19T12:03:43Z. Its manifest
names `6577f4b`, dirty — and `git_is_dirty()` was, at that time, computed with
`--untracked-files=no`, so the flag could not record the 33 untracked paths that
made the tree what it was. The evidence needed to explain these 41 numbers ceased to
exist the moment that tree was overwritten, before generation 0 preserved anything.

## 5. Retirement of the 2026-08-19 artefact

Per §3.1 the artefact is **retired, not cited**. `outputs/identifiability/` remains
on disk (`R-3`: superseded, never mutated), and no claim points at it. Every
identifiability claim now points at `outputs/identifiability_g1/`, produced under
`c115757`+ with a manifest carrying `tracked_modified`, `untracked` and a
`tree_digest`, and confirmed bit-identical on an independent re-run
(`outputs/identifiability_g1b/`, 375 leaves, 0 differing).

---

## Appendix — all 41 leaves

| # | leaf | 2026-08-19 | regenerated | rel. diff | backs a published number? | which |
|---:|---|---:|---:|---:|:---:|---|
| 1 | `/devices/ldd/spectral_floor` | `4.728864e-07` | `4.452683e-07` | `5.84e-02` | no | `papers/draft.md:143` and `README.md:313` describe the floor's *role*; no value is published |
| 2 | `/devices/ldd/entry_noise` | `4.179764e-08` | `3.935653e-08` | `5.84e-02` | no | same — the estimator is described, the number is not published |
| 3 | `/analysis_convergence[0]/sigma_ratio_1_2` | `6.123041e+00` | `6.122949e+00` | `1.51e-05` | **YES** | `papers/draft.md:169` — "$\sigma_1/\sigma_2 = 6.11$–6.13" |
| 4 | `/devices/ldd/singular_values[7]` | `4.048372e-05` | `4.048319e-05` | `1.31e-05` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 5 | `/devices/ldd/equivalence_twin/iv_max_rel_change` | `2.400007e-04` | `2.399989e-04` | `7.42e-06` | **YES** | C14; `README.md:80`, `papers/draft.md:31,175` |
| 6 | `/devices/ldd/singular_values[4]` | `1.786007e-03` | `1.786017e-03` | `5.36e-06` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 7 | `/devices/ldd/singular_values[6]` | `2.524135e-04` | `2.524129e-04` | `2.46e-06` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 8 | `/devices/ldd/singular_values[5]` | `1.317100e-03` | `1.317098e-03` | `1.88e-06` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 9 | `/devices/ldd/linear_response_check[2]/ratio` | `1.000078e+00` | `1.000077e+00` | `9.78e-07` | **YES** | C15; `README.md:316`, `papers/draft.md:167` — "ratios 0.995–1.04" |
| 10 | `/devices/ldd/linear_response_check[2]/actual` | `6.299726e-04` | `6.299720e-04` | `9.67e-07` | no | an *input* to the published ratio, not published itself |
| 11 | `/devices/ldd/parameter_sensitivity[7]` | `3.390518e-02` | `3.390518e-02` | `1.32e-07` | no | never published as a number in any document |
| 12 | `/devices/ldd/parameter_sensitivity[8]` | `8.393394e-03` | `8.393395e-03` | `1.26e-07` | no | never published as a number in any document |
| 13 | `/devices/ldd/linear_response_check[3]/ratio` | `1.039707e+00` | `1.039707e+00` | `1.14e-07` | **YES** | C15; `README.md:316`, `papers/draft.md:167` — "ratios 0.995–1.04" |
| 14 | `/devices/ldd/parameter_sensitivity[6]` | `8.170746e-02` | `8.170747e-02` | `9.46e-08` | no | never published as a number in any document |
| 15 | `/devices/ldd/linear_response_check[3]/actual` | `1.153853e-04` | `1.153853e-04` | `8.01e-08` | no | an *input* to the published ratio, not published itself |
| 16 | `/devices/ldd/linear_response_check[3]/predicted` | `1.109787e-04` | `1.109787e-04` | `3.43e-08` | no | an *input* to the published ratio, not published itself |
| 17 | `/devices/ldd/singular_values[3]` | `1.109787e-02` | `1.109787e-02` | `3.43e-08` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 18 | `/devices/ldd/parameter_sensitivity[3]` | `3.658059e-01` | `3.658059e-01` | `3.19e-08` | no | never published as a number in any document |
| 19 | `/devices/ldd/linear_response_check[0]/ratio` | `9.989530e-01` | `9.989529e-01` | `2.99e-08` | **YES** | C15; `README.md:316`, `papers/draft.md:167` — "ratios 0.995–1.04" |
| 20 | `/devices/ldd/linear_response_check[0]/actual` | `8.114111e-03` | `8.114110e-03` | `2.12e-08` | no | an *input* to the published ratio, not published itself |
| 21 | `/analysis_convergence[1]/sigma_ratio_1_2` | `6.108706e+00` | `6.108706e+00` | `1.91e-08` | **YES** | `papers/draft.md:169` — "$\sigma_1/\sigma_2 = 6.11$–6.13" |
| 22 | `/devices/ldd/parameter_sensitivity[0]` | `3.362357e-01` | `3.362357e-01` | `1.46e-08` | no | never published as a number in any document |
| 23 | `/devices/ldd/singular_values[2]` | `6.299236e-02` | `6.299236e-02` | `1.10e-08` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 24 | `/devices/ldd/linear_response_check[2]/predicted` | `6.299236e-04` | `6.299236e-04` | `1.10e-08` | no | an *input* to the published ratio, not published itself |
| 25 | `/devices/ldd/parameter_sensitivity[2]` | `3.643338e-01` | `3.643337e-01` | `9.51e-09` | no | never published as a number in any document |
| 26 | `/devices/ldd/singular_values[0]` | `8.122615e-01` | `8.122615e-01` | `8.71e-09` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 27 | `/devices/ldd/linear_response_check[0]/predicted` | `8.122615e-03` | `8.122615e-03` | `8.71e-09` | no | an *input* to the published ratio, not published itself |
| 28 | `/devices/ldd/parameter_sensitivity[1]` | `2.983774e-01` | `2.983774e-01` | `7.51e-09` | no | never published as a number in any document |
| 29 | `/devices/ldd/parameter_sensitivity[4]` | `3.423456e-01` | `3.423456e-01` | `6.75e-09` | no | never published as a number in any document |
| 30 | `/devices/ldd/parameter_sensitivity[5]` | `2.754261e-01` | `2.754261e-01` | `6.41e-09` | no | never published as a number in any document |
| 31 | `/devices/ldd/parameter_sensitivity[9]` | `9.462605e-02` | `9.462605e-02` | `5.91e-09` | no | never published as a number in any document |
| 32 | `/devices/ldd/parameter_sensitivity[15]` | `2.809443e-02` | `2.809443e-02` | `4.76e-09` | no | never published as a number in any document |
| 33 | `/devices/ldd/parameter_sensitivity[11]` | `6.047428e-02` | `6.047428e-02` | `4.07e-09` | no | never published as a number in any document |
| 34 | `/devices/ldd/linear_response_check[1]/actual` | `1.816780e-03` | `1.816780e-03` | `4.02e-09` | no | an *input* to the published ratio, not published itself |
| 35 | `/devices/ldd/linear_response_check[1]/ratio` | `1.002111e+00` | `1.002111e+00` | `3.30e-09` | **YES** | C15; `README.md:316`, `papers/draft.md:167` — "ratios 0.995–1.04" |
| 36 | `/devices/ldd/parameter_sensitivity[12]` | `5.890428e-02` | `5.890428e-02` | `3.19e-09` | no | never published as a number in any document |
| 37 | `/devices/ldd/parameter_sensitivity[10]` | `6.219898e-02` | `6.219898e-02` | `2.37e-09` | no | never published as a number in any document |
| 38 | `/devices/ldd/parameter_sensitivity[14]` | `5.569084e-02` | `5.569084e-02` | `1.38e-09` | no | never published as a number in any document |
| 39 | `/devices/ldd/singular_values[1]` | `1.812954e-01` | `1.812954e-01` | `7.14e-10` | no | no numeric singular value is published; they feed the *integer* rank, which did not move |
| 40 | `/devices/ldd/linear_response_check[1]/predicted` | `1.812954e-03` | `1.812954e-03` | `7.14e-10` | no | an *input* to the published ratio, not published itself |
| 41 | `/devices/ldd/parameter_sensitivity[13]` | `5.744432e-02` | `5.744432e-02` | `1.47e-10` | no | never published as a number in any document |