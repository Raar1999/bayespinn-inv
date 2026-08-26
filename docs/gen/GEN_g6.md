# GEN_g6 — generation 6, and the terminal adversarial generation

**Date** 2026-08-25 · **Branch** `loop/champion` · **Champion** `a59255e`
**Spec** `SPEC_g6.md` · **Audit** `AUDIT_g6.md` · **ADR** `ADR-0007`

---

## 1. What ran

| phase | outcome |
|---|---|
| A §3.1 | REPRO-01 leaf audit — **generation 1 was wrong**; 7 of 41 leaves back published numbers, all three claims re-measured and held |
| A §3.5 | PH-22 retro-sweep — **negative result: no second GRAD-02** |
| A §3.4 | `.gitattributes` pins `* -text`; the guard caught three of this generation's own edits within the hour |
| A §3.2a | CI executed locally on 3.11; `NB-02` and a BUG-14 recurrence found |
| A §3.3 | `papers/CORRIGENDA_g6.md` written; `draft.md` untouched |
| B | `SPEC_g6` frozen with `n` pre-registered from a measured pilot |
| C | **S-1: global non-identifiability demonstrated by witness** |
| A-6 | terminal adversarial generation — 6 falsifiers |

## 2. `PROV-03` — cost statement (mandatory, `ACCEPTED-PERMANENT`)

**What it is.** The adopted tree has no attestable origin. Nothing in git records
who produced the code between `6577f4b` (the pre-audit project) and `c115757` (the
adoption commit), when, in what order, or against what evidence.

**Why it cannot close.** Closing it would require evidence that no longer exists.
The working tree that produced the 2026-08-19 artefacts was overwritten before
generation 0 preserved anything. No future measurement can recover it.

**What it costs, in what units, on every future result.**

1. **Per artefact predating `c115757`: unrecoverable provenance.** Seven of eleven
   pre-existing manifests remain marked *not re-verified* in
   `docs/PROVENANCE_BIFURCATION_g0.md`. They are not wrong; they are unverifiable.
   Anyone re-deriving them must re-run rather than trust.

2. **First quantified instance: `REPRO-01`, 41 numbers.** Re-running
   `run_identifiability.py` differs from its 2026-08-19 artefact in 41 of 375
   leaves — median drift 1.906e-08, maximum 5.840e-02. The cause is *not* runtime
   nondeterminism: the script is bit-identical to itself (375 leaves, 0 differing)
   and the Jacobian is bit-identical across six runs and two thread
   configurations. The difference lies in the producing tree, and **that tree is
   exactly what was lost**. 41 numbers that can never be explained. The
   generation-6 leaf audit established that 7 of them back published claims and
   that all three claims survive re-measurement — so the cost here is
   *explanatory*, not *evidential*.

3. **Ongoing cost: zero, going forward.** From `c115757` every manifest carries
   `tracked_modified`, `untracked` and a `tree_digest`, so the same loss cannot
   recur for any artefact produced from here. The cost is bounded to artefacts
   predating adoption and does not grow.

**Has the cost grown since it was assigned?** No. It was one instance
(`REPRO-01`) at assignment and remains one. Six of seven pre-adoption experiments
re-ran with **zero** non-timing differences, so no further instance surfaced.

## 3. S-1 — the scientific result

Full record: `docs/S1_GLOBAL_IDENTIFIABILITY_g6.md`.

**13 witness pairs** among 1,999,000 examined at d=4. The closest differs by
**8.18× in doping** at one anchor and **1.23% in I–V** — 61% of the 2%
distinguishability floor. All three pairs tested **survive** 4× grid refinement
and a tightened tolerance; pair 0's distance *falls* under refinement.

The project's central caveat changes. Before: *identifiability is local, global is
unmeasured.* Now: *global non-identifiability is measured, with exhibited
witnesses that survive falsification.*

Two limits stated rather than glossed: contraction at the instrument's own 2%
noise is **not measured** (the estimator collapses, ESS 1.0), and the d=8 point of
the dimension sweep is confounded with sampling density.

## 4. A-6 — terminal adversarial generation

Six falsifiers, aimed at what this loop promoted. **One new finding, MEDIUM. No
new HIGH or above.**

| # | target | attack | outcome |
|---|---|---|---|
| F1 | `g0c2` asinh ohmic fix | 4 dtypes × 6 extreme inputs, 2nd derivatives, batched shapes | **no finding.** 3 non-finite cases, all float16 at \|C_s\| ≥ 1e12 — 1e12 exceeds float16's 65504 maximum, so the *input* is unrepresentable before any arithmetic. float32/float64 clean; 2nd derivative finite (−1.0e-18 at C_s=1e9); batched gradients finite |
| F2 | S-1 conclusion | narrower prior (1e21–1e22) + seed 7; stricter separation (0.6 dec) + seed 3 | **no finding.** A witness still appears under the narrower prior (2.08×, 1.92e-02). The stricter-separation run found none at n=400 and says so — "no witness found at this budget", not "identifiable" (`AH-13`) |
| F3 | `PROV-02` provenance fix | hide a source module inside a `.gitignore`'d directory | **`PROV-07`, MEDIUM — see below** |
| F4 | `PKG-04` loader move | import from a freshly built wheel with `parents[3]/scripts` absent | **no finding.** Both loaders import; the branch that once needed the checkout no longer does |
| F5 | claim surface | re-measure the three generation-0 withdrawals cold | **no finding.** V_bi 7.2428e-14 vs published 7.24e-14; mass action 2.9345e-09 vs 2.93e-9 |
| F6 | `.gitattributes` | force `core.autocrlf=true`, the exact setting that nearly broke the attestation | **no finding.** 0 files disagree between index and working tree |

### `PROV-07` — ignored directories are invisible to all three provenance fields
| **Severity** | MEDIUM | **Status** | OPEN |

Constructed a repository, committed it clean, then placed a source module inside a
`.gitignore`'d directory. The result:

```
dirty = False    tracked_modified = 0    untracked = 0    tree_digest unchanged
```

All three fields added by the `PROV-02` fix report a clean tree while it carries
code absent from the commit — the same *shape* of failure `PROV-02` was opened for.

**Why it is MEDIUM and not a repeat CRITICAL.** The exclusion is deliberate and
documented: ignored files are regenerable build output, and counting them would
make every manifest permanently dirty. The original `PROV-02` was CRITICAL because
it silently hid **6 source modules and 83% of the test suite**, and that actually
happened. This variant requires code to be deliberately placed in an ignored path,
which is not this repository's structure and has not occurred. It is a correctness
risk without a current wrong number.

**Not fixed here.** `SW-08`: one candidate, one concern, and A-6 is a
falsification generation rather than a repair one. Recorded for a later
generation. The candidate fix is to hash the *ignore rules themselves* into the
tree digest, so a change to what is hidden is at least visible.

---

## 5. Termination assessment against the amended `T-1`

| condition | status |
|---|---|
| all mandatory spec clauses `PASS` | ✅ `SPEC-g0-1,2,4,5,6,7` pass; `SPEC-g0-3a` passes for every leg available in the environment; `SPEC-g6-1…6` pass |
| no open `CRITICAL` | ✅ none |
| no open `HIGH` without one of the three statuses | ✅ the only open HIGH is `PROV-03`, `ACCEPTED-PERMANENT`, cost statement in §2 |
| A-6 produces no new `HIGH` or above | ✅ one new MEDIUM (`PROV-07`) |

**`T-1` is satisfied. The loop terminates here.**

`SPEC-g0-3b` (`OPERATOR-BLOCKED`) does not block `T-1` under §1 of the ruling. Its
exact commands are in `docs/OPERATOR_TASKS.md`.

## 6. Gates at the champion

ruff exit 0 · **438 passed, 0 failed** · selftest PASS · mypy **25** over the package only and never the tracked tree, unchanged
from the generation-0 baseline · fresh wheel imports and runs.
