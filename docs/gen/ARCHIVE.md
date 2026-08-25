# Candidate archive — append-only

Every candidate ever evaluated by the audit loop, with its genome hash, gate
outcome and one line on why it failed. Re-proposing an archived genome is
prohibited; re-proposing an archived *approach* with new evidence must cite the
entry it supersedes (§5.7).

The genome hash is `sha256(target_finding | spec_clause | operators | patch)`,
truncated to 16 hex characters.

---

## Generation 0 — base `4baccf6`, spec `28c853f0…`

| id | genome | kind | operators | outcome | why |
|---|---|---|---|---|---|
| `g0c1` | `a1f4c8d2e07b3591` | conservative | defensive input masking | **archived — dominated** | Fixes the NaN (0/402 non-finite in both dtypes) but keeps the quadratic, so it inherits its accuracy: float64 gradient error 4.393e-16 against g0c2's exact 0.000e+00, float32 1.629e-07 against 8.190e-08, mass action 3.664e-15 against 2.220e-16. Same blast radius as g0c2, more net LOC (+11 vs 0). Dominated on f2 and f6 with nothing to offer in return. |
| `g0c2` | `7d3b019ac5e64f88` | conservative | `M-01` | **PROMOTED** | `log n = asinh(C/2)`. Branchless, exact in every dtype, derivative `1/sqrt(4+C²)` finite everywhere. Best f2 of the population, smallest f7 (1 file, 0 new public symbols, oracle import graph unchanged at 8), net ΔLOC 0. Won the front on tie-break (b), lower f7. |
| `g0c3` | `c2e8b47f1069da35` | structural | `M-14` | **archived — dominated** | Extracts `physics/contacts.py::ohmic_log_densities`; the solver and the loss both delegate. Physics identical to g0c2 to the last digit, but 3 files against 1, one new public symbol against none, and +39 net LOC against 0. Correct and clean; simply costs more for the same result. Worth reviving in a later generation if S-3 is given a Phase-A severity, which would move f1 and change the ordering. |
| `g0c4` | `f60a92c3d18e7b4d` | structural | `M-14` | **archived — front, not promoted** | Same physics; the solver imports `pinn.losses` directly. Measured: the oracle's import graph grows 8 → 10 modules and `pulls_in_pinn` flips to `True`, making the reference solver depend on the package `ADR-0004` declares legacy and `M-22` contemplates retiring. Reached the Pareto front on net ΔLOC (−13) but lost tie-break (b) on f7. |
| `g0c5` | `3ab7d5e9c40f2168` | falsifier | — | **SUCCEEDED** | Broke the incumbent audit's own scoping of GRAD-02. In float32 — the training dtype — 41 of 41 envelope points return NaN gradients, onset `C_s = 7.079e3`, *below* the envelope. Opened GRAD-03. Also bounded the damage: 0 of 26 PINN weight-gradient tensors affected, so D1/ADR-0004 stand. Product: the dtype-parametrised gate and the blast-radius pin. |
| `g0c6` | `9e04f7b2a63c85d1` | negative control | — | **CORRECTLY REJECTED** | Clamps `C_s` to ±1e8. Plausible (five lines, the change a hurried engineer writes) and it does remove every NaN — but it silently narrows the documented 1e21–1e25 m⁻³ envelope, which is the `AH-02` shortcut `SPEC-g0-4` exists to forbid. Battery rejected it on 10 ohmic failures: gradient stops matching `1/sqrt(4+C²)`, mass action and charge neutrality break, and the two ohmic implementations stop agreeing. Battery confirmed working. |

**Approaches not to re-propose without new evidence**

- Masking `torch.where` inputs while keeping the quadratic (`g0c1`) — strictly
  worse than the reformulation at equal cost.
- Any fix that narrows the doping envelope (`g0c6`) — `AH-02`, automatic discard.

**Approaches worth reviving**

- `g0c3`, if S-3 is assigned a Phase-A severity in a later audit. That would give
  the structural candidates f1 = 6 against g0c2's 4, and tie-break (a) — higher
  f1 — would then decide before f7 is consulted, reversing this generation's
  ordering. Cite this entry.
