# CANDIDATES_g0 — generation 0 population, gate records and scores

**Base for every candidate** `4baccf6826ceed91f543adce9fed0d43800ee8c8`
**Spec** `docs/spec/SPEC_g0.md`, sha256 `28c853f0550adf023ed8e463f29a1a4af7af1f75a830955414280109553f4140`
**Promoted** `g0c2`

`R-4` prohibits `git checkout`, so candidates were evaluated in place with
file-level snapshots rather than branches. Every candidate was applied to the
same base, gated with the same commands, and restored before the next — `AH-03`.
Scores were compared only after all six had run.

An early run of g0c1/g0c2 was discarded and repeated: it was measured against a
working tree that still carried an uncommitted 110-line test file, which inflated
their diff metric relative to the structural candidates. Comparing candidates
under different protocols is exactly what `AH-03` forbids, so all five were
re-measured against a clean base. Likewise, the first attempt at g0c3/g0c4 failed
`ruff` on import ordering — a defect in the patch generator, not the design — and
was corrected and re-run rather than scored as a candidate failure.

---

## 1. Population

| id | kind | operator | change |
|---|---|---|---|
| g0c1 | conservative | defensive masking | mask the *inputs* to `torch.where` so the discarded branch can never reach `1/0` |
| g0c2 | conservative | `M-01` reformulate in stable variables | `log n = asinh(C/2)`, `log p = −asinh(C/2)` |
| g0c3 | structural | `M-14` merge | extract `physics/contacts.py::ohmic_log_densities`; both the solver and the loss delegate |
| g0c4 | structural | `M-14` merge | the solver imports `pinn.losses.ohmic_boundary_values` directly |
| g0c5 | falsifier | — | point the incumbent's own GRAD-02 scoping at float32 |
| g0c6 | negative control | — | clamp `C_s` to ±1e8 "to avoid the overflow" |

---

## 2. Gate records

Gates ran cheapest-first and killed on the first failure (§8), so a candidate that
fails `ruff` never reaches the suite.

| id | ruff | ohmic (41) | suite (307) | diff | files |
|---|---|---|---|---|---|
| base | pass | **22 passed / 17 failed** | 289 / 18 failed | — | — |
| g0c1 | pass | **39 / 39** | 306 / 1 failed | +20 / −9 | 1 |
| g0c2 | pass | **39 / 39** | 306 / 1 failed | +16 / −16 | 1 |
| g0c3 | pass | **39 / 39** | 306 / 1 failed | +76 / −37 | 3 |
| g0c4 | pass | **39 / 39** | 306 / 1 failed | +24 / −37 | 2 |
| g0c6 | pass | **29 passed / 10 FAILED** | not reached (killed early) | +5 / −2 | 1 |

The single remaining suite failure under all four real candidates is
`test_notebooks.py::TestDocumentedTestCountIsHonest` — the repository's own badge
guard, firing because the suite grew. It is a `G-DOC` obligation on the promoted
candidate, not a candidate defect, and was discharged by updating the badge to the
collected count. After promotion the suite is **309 passed, 0 failed**.

### Negative control (A-4, AH-11)

`g0c6` is a five-line clamp — the change an engineer under time pressure would
plausibly write, not a malformed straw man. It *does* remove every NaN. The
battery rejected it on **10 ohmic failures**: the clamp silently narrows the
solver's documented 1e21–1e25 m⁻³ envelope, so the gradient stops matching
`1/sqrt(4+C²)`, mass action stops holding, charge neutrality breaks, and the two
ohmic implementations stop agreeing. This is exactly the `AH-02` shortcut
`SPEC-g0-4` was written to forbid, and the battery caught it without special
casing. **The gate battery is not broken.**

---

## 3. Measured objectives

All values measured on 402 log-spaced points across the documented envelope
(`C_s = 1e5 … 1e9`), both signs.

| metric | base | g0c1 | g0c2 | g0c3 | g0c4 |
|---|---|---|---|---|---|
| non-finite gradients, float64 | **44 / 402** | 0 | 0 | 0 | 0 |
| non-finite gradients, float32 | **201 / 402** | 0 | 0 | 0 | 0 |
| grad rel. error, float64 | 4.393e-16 | 4.393e-16 | **0.000e+00** | **0.000e+00** | **0.000e+00** |
| grad rel. error, float32 | 1.629e-07 | 1.629e-07 | **8.190e-08** | **8.190e-08** | **8.190e-08** |
| mass-action deviation | 3.664e-15 | 3.664e-15 | **2.220e-16** | **2.220e-16** | **2.220e-16** |
| charge-neutrality deviation | 1.809e-15 | 1.809e-15 | 1.809e-15 | 1.809e-15 | 1.809e-15 |
| value vs solver, rel. | 1.820e-15 | 1.820e-15 | 1.963e-15 | 1.699e-16 | 0.000e+00 |
| net ΔLOC | — | +11 | **0** | +39 | −13 |
| files touched | — | 1 | 1 | 3 | 2 |
| new public symbols | — | 0 | 0 | 1 | 0 |
| oracle import graph | 8 | 8 | 8 | 9 | **10, imports `pinn`** |

### Solve time does not discriminate — reported, not used

| candidate | n | median (s) | IQR |
|---|---|---|---|
| base | 25 | 9.4704e-03 | [8.9341e-03, 1.1046e-02] |
| g0c1 | 25 | 9.4114e-03 | [8.4884e-03, 1.0152e-02] |
| g0c2 | 25 | 8.2944e-03 | [7.9917e-03, 9.6404e-03] |
| g0c3 | 25 | 9.9846e-03 | [8.6023e-03, 1.0173e-02] |
| g0c4 | 25 | 1.0193e-02 | [9.4612e-03, 1.0675e-02] |

Every IQR overlaps every other. The decisive evidence that this measurement is
noise-dominated is **g0c2 at −12.4%**: g0c2 touches only `pinn/losses.py`, which
the solver never imports, so it *cannot* change solve time. A machine running
other work cannot resolve these differences at n = 25, so solve time was **not
used** as a discriminator. Quoting g0c3's +5.4% or g0c4's +7.6% as a real cost
would have been fabrication.

---

## 4. Selection

**Constraint dominance.** All four real candidates clear every hard gate. `g0c6`
is a control and is not scored.

**f1 (findings closed, severity-weighted) is 4 for all four.** Each closes
GRAD-02/GRAD-03 (`HIGH` = 4). It is tempting to credit g0c3 and g0c4 with also
closing S-3 (duplicate physics), but **S-3 carries no Phase-A severity** — it was
recorded in `AUDIT_g0` as a persisting *pattern* and as a non-finding on values,
never assigned a severity. `AH-09` forbids assigning one now, after the candidates
exist, to justify a promotion. f1 therefore ties at 4.

**Pareto front.**

- `g0c1` is **dominated by g0c2**: identical f1 and f7, strictly worse f2
  (4.393e-16 vs exact 0.000e+00 in float64; 1.629e-07 vs 8.190e-08 in float32;
  mass action 3.664e-15 vs 2.220e-16), and worse net ΔLOC (+11 vs 0). Out.
- `g0c3` is **dominated by g0c2**: identical f1 and f2, but 3 files against 1,
  one new public symbol against none, and +39 net LOC against 0. Out.
- Front = {`g0c2`, `g0c4`}. g0c4 has better net ΔLOC (−13 vs 0); g0c2 has lower
  blast radius (1 file vs 2, and an unchanged oracle import graph).

**Tie-break (§5.6):** (a) f1 equal at 4; (b) **lower f7 → `g0c2`**.

`g0c2` is promoted by the stated rule, not by preference.

### Why g0c4 was not promoted — measured, not asserted

`g0c4` makes `solvers/scharfetter_gummel.py` — the **oracle**, the reference every
other component is benchmarked against — import
`pinn.losses.ohmic_boundary_values`. Measured: importing the solver pulls **10**
`bayespinn_inv` modules instead of 8, and `pulls_in_pinn` flips from `False` to
`True`. `ADR-0004` declares `pinn/` legacy and `M-22` contemplates retiring it;
g0c4 would make the oracle depend on the package the project has already decided
is on its way out, and inverts the dependency direction between the thing being
benchmarked and the benchmark.

An attempt to measure this consequence directly — blocking `bayespinn_inv.pinn`
imports and re-importing the solver — returned "survives = True" for every
candidate including g0c4. That result is **discarded, not reported**: relative
imports inside a package bypass the `builtins.__import__` guard the probe relied
on, so the measurement was invalid. The module-count and `pulls_in_pinn` figures
above stand; the retirement-survival figure does not.

### g0c5 — falsifier: SUCCEEDED

Per §5.2 a successful falsifier outranks a successful improvement. `g0c5` was
pointed at the incumbent audit's own scoping of GRAD-02 ("NaN for |C_s| ≳ 3.2e8",
measured in float64) and broke it: in float32, the dtype the networks actually
train in, **41 of 41** sampled envelope points return NaN gradients. The onset is
`C_s = 7.079e3`, *below* the envelope's lower bound. GRAD-02 covered the top
21.4% of the envelope; GRAD-03 covers all of it.

It also bounded the damage honestly. The blast radius was **measured, not
inferred**: a float32 PINN boundary-loss backward at N = 1e21, 1e24 and 1e25 m⁻³
produced non-finite gradients in **0 of 26** weight tensors, because
`trainer.py:262` passes boundary doping as data with no `requires_grad_`. **D1 and
ADR-0004 are not confounded.** The defect fires only where doping itself carries a
gradient — inverse design, and the Jacobian underlying the identifiability
result — where float32 returns `grad = [1e-08, nan]` at N = 1e24 m⁻³.

Its product is `tests/test_ohmic_gradient_g0.py`'s dtype-parametrised gate and the
blast-radius pin, both additive: no existing test was edited, skipped, xfailed or
relaxed. The gate moved in the direction of strictness only.
