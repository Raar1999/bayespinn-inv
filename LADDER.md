# `LADDER.md` — the condition ladder

**Instantiated** 2026-08-28, before generation 11 Phase A, from the operator
directive §7. **Hashed before the first generation under this governance**, per
`LD-1`. The hash of this file at instantiation is recorded in `RULINGS.md` and
in `LOOP_STATE_v10.json`; it is recomputed at the head of every generation and a
mismatch that is not an authorised insertion is an `IA-4` discard.

This file replaces the two-party arrangement in which an operator supplied the
target and the executor supplied the measurements. Under the fused authority the
target is written down **first**, hashed, and thereafter not edited — that is
the whole of what stops the target from being redefined as whatever was
achieved.

---

## The rungs

```
L0  TARGET
    Every spine item on full refinement coverage, MECH-01 answered,
    no open HIGH outside ACCEPTED-PERMANENT / OPERATOR-BLOCKED.

L1  Every spine item on full coverage; MECH-01 stated as an open question
    with its narrowing measured.

L2  Spine items with coverage stated per DOC-08 wherever it is partial;
    every gap published with what would close it.

L3  FLOOR
    The claim surface is true and every limitation is stated.
    Below this the work is not publishable.
```

**The spine** is `docs/CLOSE_RULING.md` §5 as it stands at the head of each
generation, six items. **Full refinement coverage** means `WIT-02` satisfied on
every committed witness set a spine item rests on: chart G `d=4` (13 of 13,
satisfied at the 2026-08-28 addendum), chart J `d=16` (13 of 13, satisfied at
generation 9), chart L `d=16` (**0 of 37**, unmet). **Open HIGH** is read off
`open_findings` in the current `LOOP_STATE`.

## Where the loop stands at instantiation, stated before any generation-11 measurement

**`L2`, held.** Coverage is stated per `DOC-08` on all three witness sets, and
`docs/CLOSE_RULING.md` §6 publishes each gap with what would close it. `L1` is
not held: chart L is at 0 of 37 and spine items 3 and 4 rest on it. `L0` is not
held: `MECH-01` is `OPEN, DESCRIBED BUT NOT EXPLAINED`, and `PROV-03` and
`PROV-07` are open HIGH — `PROV-03` `ACCEPTED-PERMANENT` and therefore exempt by
the rung's own words, `PROV-07` `MITIGATED-PENDING-CI` and therefore **not**
exempt unless it is `OPERATOR-BLOCKED`, which is a question generation 11 has to
answer rather than assume.

This paragraph is written **before** generation 11 measures anything, so that the
starting rung cannot later be back-dated to flatter the finish.

---

## The rules that govern movement on it

* **`LD-1`** Rungs are not edited. A rung may be *inserted* mid-run only with a
  written justification recording its timestamp and the generation that added
  it, so that it is visible the insertion postdates the data.
* **`LD-2`** Descent is one rung at a time. Never skip. Never two in one
  generation.
* **`LD-3`** Descent requires a signed unreachability verdict under §2 of the
  directive for the rung above. Failure to reach is not unreachability. Three
  failed attempts is not unreachability. Only a verdict is.
* **`LD-4`** Every descent records its **reachability condition** — the specific
  change in the world that would make the abandoned rung attainable again.
* **`LD-5`** At every Phase A, re-evaluate the reachability conditions of all
  abandoned rungs. If one is satisfied, **climb**, and say so.
* **`LD-6`** Terminating at `L3` is reported as a failure to reach `L0`, in
  those words, with the descent chain and every unreachability verdict attached.

## The unreachability classes, and what each one owes

| class | what it asserts | obligation | permanence |
|---|---|---|---|
| `U-STRUCT` | the condition contradicts itself or a kernel rule | exhibit the contradiction as a derivation | permanent |
| `U-INSTR` | the measurement needs an instrument that does not exist and cannot be built in scope | name the instrument, its build cost, and what would have to be true for it to exist | reversible |
| `U-BUDGET` | the cheapest sufficient experiment exceeds remaining budget | a **measured pilot**, not an estimate, and the overrun factor. *A budget verdict without a pilot is void.* | reversible |
| `U-EMPIR` | k ≥ 3 attempts by **distinct methods** failed, characterised | name each method, why it was expected to work, and the mechanism of its failure. Three runs of one method is one attempt. | **expires after two generations** |

`U-0`: a verdict is written *before* the fallback work begins and hashed with the
generation's spec. A verdict retrofitted to explain where the loop ended up is
void.

---

## Descent / climb log

Append-only. One row per movement, with the generation, the direction, and the
verdict or the satisfied reachability condition that licensed it.

| generation | from | to | licensed by |
|---|---|---|---|
| — | — | `L2` (held at instantiation) | not a movement; the starting position, recorded before generation 11 |
| 14 | `L0` (the target, under attempt since generation 11) | `L1` (terminal) | `U-EMPIR` on `MECH-01` — `docs/UEMPIR_MECH01_g14.md`, sha256 `e34c812fe7401ca3f1efe164e521455b376850445781f9004a4d6ada81b9cd40`. Three distinct methods, two falsified and one inconclusive, each characterised by measurement. `LD-3` satisfied; the reachability condition is `LD-4` §3 of that document |
