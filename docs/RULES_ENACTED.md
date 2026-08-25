# Rules enacted by operator ruling

Append-only. Rules referenced throughout this repository — `PH-*`, `SW-*`, `DOC-*`,
`AH-*`, `R-*`, `SK-*` — originate in operator rulings, which are not files in this
tree. Most were absorbed as behaviour and cited at their point of use.

That worked until generation 7 wrote `SW-20` into three source files and a reader
had nowhere to look it up. A rule that exists only in a message is unenforceable
and, once the message scrolls away, unrecoverable. This file is where enacted
rules land from now on, with the defect that motivated each one and how it is
enforced.

Rules enacted **before** generation 7 are not backfilled here: reconstructing them
from citations would be inventing text and attributing it to the operator. They
remain cited at their points of use, and `RULE-01` in `docs/audit/AUDIT_g7.md`
records the gap.

---

## `SW-20` — a guard over source code is written over the AST

**Enacted** operator ruling, 2026-08-25 §3.5.

> A guard whose subject is source code is implemented over the AST, never over
> characters, and excludes its own source and the documentation describing it
> from its search scope. Every guard ships with **both** controls: a planted
> violation it must catch, and prose describing the violation it must not fire
> on.

**The defect that forced it.** Generation 6 shipped four guards that could not
fire. `docs/audit/AUDIT_g6.md` §5 generalises them as one class rather than four
slips. The clearest instance: a guard searching for the string `def bernoulli`
matched *its own pattern literal* the moment it was committed, so it reported a
violation of itself forever and its authors learned to ignore it.

A character scan cannot distinguish code from prose *about* code. An AST walk can,
because prose is not in the AST.

**Enforced by**

| guard | subject | AST? | controls |
|---|---|---|---|
| `scripts/check_python_support_floor.py` | source code | yes — `ast.parse` and a `NodeVisitor` | `tests/test_python_support_floor_g7.py`: one planted violation per detector, plus a module whose *text* contains every pattern it searches for and whose *code* uses none of them |
| `tests/test_claim_surface_g7.py` | prose | n/a — there is no AST for prose | the letter does not apply; the purpose does. Both controls implemented, own source and explanatory documents excluded from scope, and the exclusion asserted rather than trusted |

The second row is the honest reading: `SW-20`'s mechanism is specific to code, its
*purpose* — a guard must be shown to fire, and shown not to fire on descriptions
of what it forbids — is not.

---

## `DOC-07` — a commit message never asserts a measured count or metric

**Enacted** operator ruling, 2026-08-25 §3.5.

> Commit messages never assert a measured count or metric. They reference the
> manifest or artefact that carries it. A count in a commit message is a claim on
> an unguardable surface.

**The defect that forced it.** Commit `1a090f0` asserts `420 passed` in its
message. The tree it committed produced 437 passed and 1 failed. Under `R-4` a
commit message cannot be corrected, so the false claim is permanent; `d3b7693`
corrects it forward, and `docs/gen/DECISIONS.md` records why that is the only
available remedy.

A commit message is the one surface in this repository that no test can fix after
the fact. The rule removes the class of claim that would need fixing.

**Enforced by** `tests/test_commit_messages_g7.py`. The guard scans commit
messages created after the rule was enacted and rejects assertions of the form
"N passed", "N tests", "N of M passing". Its positive control is `1a090f0` itself:
the guard must flag that message, and the test fails if it does not — which also
proves the guard is not vacuous. History before the enactment commit is out of
scope, because `R-4` makes it uncorrectable and a guard that fails on
uncorrectable history is a guard people disable.
