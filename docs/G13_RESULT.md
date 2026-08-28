# Generation 13 — the objects are saved, and the row side failed out of sample

**Status** run under the operator ruling of 2026-08-28 (the `PROV-08` / `CI-02` /
`MECH-01` pass 3 ruling). That ruling ordered the pre-rewrite objects copied
before anything else, froze `EXT-04`, reserved the pull request and `EXT-05` to
the operator, and required `MECH-01`'s magnitude statistic to be de-confounded,
pre-registered and tested out of sample.

**Ladder: `L1` held.** Not climbed, not descended. `L0` still needs `MECH-01`
answered, and `MECH-01` is still open — but it is open in a more useful way than
it was, because the row side is now a *characterised failure* rather than an
inconclusive result.

**The headline.** The pre-registered statistic cleared its threshold at one
held-out device and missed it at the other, and the rule written before the data
was touched required both. `DOES_NOT_SEPARATE`. The mechanism of the failure was
then measured: `dz` correlates with the split ratio at **−0.95 to −0.98** on the
width axis, and the device-to-device offset is **1.57** against an axis
difference of at most **0.22**. The statistic was measuring the window and the
device, not the rank.

---

## 1. `PROV-08` — done first, and the census is bigger than the sample said

Four `.git` directories copied to `F:\backups\extgit-20260828\`, read-only from
the surveyed repositories' perspective. **1,216 distinct pre-rewrite commits are
now preserved off the tree that holds them.** `git fsck` reports zero errors and
zero corruption in all four copies, and every copy resolves exactly what its
original resolves.

The full record, including the per-repository census, the reachability table and
the tip analysis, is in `docs/AUDIT_MASTER.md` under **`PROV-08` rescue**. Three
things there are worth lifting out.

**`EXT-04` is a superset, not a second opinion.** It holds 1,073 of
fabkg-bench's 1,106 mapped pre-rewrite commits; the rewritten sibling holds 393,
**every one of them also in `EXT-04`**, and contributes **nothing** of its own.
For **680** commits `EXT-04` is the only surviving record on this machine. The
ruling froze it to preserve a redundancy; the measurement says it is not
redundancy but the primary. The freeze was right and is now load-bearing.

**`EXT-04` is also the only one of the four that is structurally safe.** Its
survivors are reachable from refs — it was never rewritten — where the other
three hold theirs as dangling objects that a `gc` ends. That is why the freeze is
sufficient for `EXT-04` and why a copy was necessary for the others.

**33 commits are in the fabkg map and in none of the four repositories.** Lost,
and recorded as lost rather than as unexamined. `EXT-05` was not surveyed for
them, because the ruling reserves `EXT-05` to the operator and §1 did not ask.

**One thing is preserved but not yet durable, and it is left as a
recommendation.** The three copies of rewritten repositories are byte-faithful
archives *of dangling objects*: a `git` command run inside one that triggers
`gc --auto` would prune them there exactly as in the original. `fsck
--lost-found` shows the survivors hang off very few tips — 1, 7 and 3 — and
walking parents from those tips reaches every survivor (63 of 63, 393 of 393,
80 of 80). **Eleven refs would pin all 536 permanently.** That was not done here:
writing refs into an archive changes evidence this loop was told to copy, not to
edit. It is the operator's call.

---

## 2. `CI-02` — not acted on, by the ruling's own allocation

The ruling diagnoses the closed route correctly: `workflow_dispatch` requires the
workflow on the default branch, `main` is `6577f4b`, and `ci.yml` was untracked
until this loop committed it, so there is nothing on `main` to dispatch. The
same-repository pull request is the route that works.

**The ruling says "Mine to open."** No pull request was opened here and no
remote was touched. `CI-01` stays open on evidence not yet in hand, and the 3.9
question stays unresolved.

---

## 3. `MECH-01` pass 3 — the work

`scripts/run_mech01_pass3.py`. Pre-registration hashed before either held-out
device was touched:

```
measure   1627cf4d7dc109a12c5d7f8fe2734f78f4c98fd97f4d7144764ddc227af153f4
outcomes  f51f8d0c66a205e06cdea8a01b12020502291a4d711039b4e596aad8688548e7
```

`PILOT-01`: priced at 24.29 s per cell × 36 = 874 s projected before the run was
decided on. Affordable, so it ran.

### 3.1 The defect found in the pass-2 statistic, before pre-registering

The ruling named a degeneracy at the narrowest width, where the core and
measurement windows coincide and `n_out = 1` of 16. Reading the pass-2 cells as
what they are — a discovery sample — found a larger version of the same problem
across the whole axis.

Write `b = n_out/n_rows`. The **width** axis sweeps `b` from 0.0625 to 0.875 and
its maximum sits at `b = 0.375`–`0.50`. The **spacing** axis, the control, only
ever visits `b` in `[0.857, 0.929]`. **The two axes were compared at values of
`b` that do not overlap, and the width peak sits in a region the control never
samples at all.** At matched `b` the width cells fall inside the spread of the
spacing cells.

So the 3.1–3.5× of pass 2 was not evidence about rank. The control axis was never
a control for that statistic.

### 3.2 The fix, derived from the null rather than chosen

Under `H0` — the direction has no row preference — `U[:, k]` is uniform on the
unit sphere, the squared coordinates are `Dirichlet(1/2, …, 1/2)`, and

```
w_out ~ Beta(n_out/2, n_in/2)
E[w_out]   = b
Var[w_out] = 2 b (1 - b) / (n_rows + 2)
```

Pass 2 subtracted the mean and stopped; the **variance** is the part that carries
`b`. Dividing by it gives a quantity that is mean 0 and variance 1 under `H0` at
every cell whatever `b` is:

```
z(k) = (w_out(k) - b) / sqrt(2 b (1 - b) / (n_rows + 2))
dz   = mean(z(2), z(3), z(4)) - z(1)
```

**The degeneracy is fixed structurally, not by a threshold.** `Beta(n_out/2,
n_in/2)` has a finite, non-U-shaped density only when both shape parameters are
at least 1, i.e. `n_out ≥ 2` **and** `n_in ≥ 2`. A cell failing it has no null to
standardise against. Stated in the pre-registration in advance: at the
`SPEC-g9-2` geometry this excludes **exactly the narrowest width cell**. It did,
at all four devices, and it also excluded one spacing cell at `n_in = 1` that
nobody had noticed.

Both the standardisation and the admissibility rule are derived from the null.
That is the whole of their defence, and it is why they are not `PH-11` tuning.

### 3.3 The test, and where it was run

One-sided exact Mann-Whitney U per device, width against spacing, `α = 0.05`,
`SEPARATES` iff **both** held-out devices clear. Rank-based, exact, conventional
threshold.

Out of sample means **`device_p10` and `device_p90`** — selected by `SPEC-g9-1`'s
pre-registered percentile rule at generation 9, never given a row weight by pass
2, and the *far* devices at 1.22 and 1.41 decades of profile distance from the
generation-8 device against `device_p50`'s 0.64.

`R1'`, the reproduction control: the width `= 0.75` window **is** generation 9's
`wide_0.15_0.90` window, so its singular values must reproduce `op_points.json`
bit for bit. **8 of 8 identical.** The Jacobians are the objects `SPEC-g9-1`
measured, so this is not a measurement failure.

### 3.4 The verdict

| device | admissible w / s | median `dz` width | median `dz` spacing | exact one-sided *p* | |
|---|---|---|---|---|---|
| `device_p10` | 8 / 7 | +0.113 | −0.573 | **0.00062** | clears |
| `device_p90` | 8 / 7 | +1.217 | +1.200 | **0.30629** | does not clear |

**`DOES_NOT_SEPARATE`.**

The discovery sample, re-analysed under the same statistic and reported as
contrast rather than evidence (`AH-06`), clears at both devices — *p* = 0.0019
and 0.0047. **That is exactly the shape of the trap the ruling named**: the
headroom concordance read 1.000 on the sample that generated it and 0.479 on the
set it had never seen. Here it reads 0.002 in sample and 0.31 at one of two
held-out devices.

Had the rule been "either device", or had only `device_p10` been measured, this
would have been reported as a confirmation.

### 3.5 The mechanism of the failure, measured

`scripts/mech01_pass3_mechanism.py`, `new_solves = 0`. A description, not a test,
and it does not revise the verdict. `U-EMPIR` requires the mechanism of a
method's failure to be named, and a mechanism is a measurement.

| device | median `dz` | width | spacing | corr(`dz`, `b`) on width |
|---|---|---|---|---|
| `g8_operating_point` | +0.545 | +0.931 | +0.329 | **−0.951** |
| `device_p50` | +0.664 | +0.927 | +0.432 | **−0.969** |
| `device_p10` | −0.373 | +0.113 | −0.573 | **−0.984** |
| `device_p90` | +1.200 | +1.217 | +1.200 | **−0.711** |

Two numbers settle it. **`dz` is very nearly a function of `b`**: the correlation
along the width axis is −0.95, −0.97, −0.98 and −0.71. And **the device offset
dominates everything**: the spread in median `dz` across devices is **1.572**,
where the largest axis difference at matched `b` is **0.22**.

The statistic varies with the window and with which device it is. The axis — the
thing the hypothesis was about — is the smallest of the three effects.

**The post-hoc `b`-matched comparison, reported as a limitation and not as a
second verdict.** Restricted to `b ∈ [0.818, 0.875]`, the range both axes reach,
width exceeds spacing at all four devices, by +0.22, +0.22, +0.20 and +0.08. The
sign is consistent, and it is not rescued by that: three width cells per device,
margins an order of magnitude under the device spread, and — decisively — those
matched cells are the **widest** windows, where the rank has already saturated at
4. A residual that lives where the rank is *not* climbing is not the mechanism
the hypothesis proposed.

### 3.6 What it means for `U-EMPIR`

Pass 3 is **the same method with a sharper statistic**, not a third one, and the
pre-registration says so in the hashed text so it cannot be re-counted later.

* method 1 — the column side, generation 10: **falsified**
* method 2 — the row side, generations 10/12/13: **falsified**, out of sample,
  with its mechanism measured

`U-EMPIR` requires `k ≥ 3` attempts by **distinct** methods. It stands at **two**.
**No unreachability verdict is written, and none may be.** `MECH-01` stays open.

What pass 3 changes is that the row side is now closed as a *characterised*
failure rather than left as pass 2's inconclusive. That is a real narrowing, and
it is what holds `L1` rather than merely failing to reach `L0`.

---

## 4. `EOL-02` enacted

Recorded in `docs/RULES_ENACTED.md`, guarded by
`tests/test_eol02_line_endings_g13.py` over the AST with both `SW-20` controls.
**68 call sites fixed across 41 files** in `src/`, `scripts/` and `tests/`; none
was a csv writer, and the two csv sites that already relied on `newline=""` are
now protected by a test against a future mechanical rewrite.

**The enactment tripped its own rule twice, and both are recorded rather than
tidied away.**

The first mechanical pass added the keyword correctly and wrote every file back
through Python's text mode, turning 25 CRLF files into LF — **9,832 lines changed
to fix 68**. `.gitattributes` is `* -text`, so that mixture is the committed
truth and `test_line_endings_g6.py` records it deliberately. It was redone over
bytes, asserting per file that CRLF and LF counts are unchanged. **The guard went
green either way**; what caught it was reading the diffstat.

Then writing the rule's own documentation through a shell heredoc collapsed four
backslash escapes into real line breaks, one of which put a literal CR into a
pure-LF file. `git ls-files --eol` reported `w/mixed` and
`test_line_endings_g6.py` failed **on the document describing the line-ending
rule**. That is `OPS-03`'s shape for the fourth time: a guard whose subject is
text will eventually match the text that discusses it, and here the artefact
describing a line-ending rule was unusually good at violating it.

### 4.1 The sweep found a character scan over source code, which is what `SW-20` forbids

`tests/test_notebooks.py` guarded `BUG-14` — a `write_text` with no `encoding` —
by testing whether the exact substring

```
write_text(nbf.writes(nb), encoding="utf-8")
```

appears in `scripts/build_notebooks.py`. `EOL-02` appended `newline="\n"` to that
very call. **The write was still correct and the guard failed anyway**, because
the guard was matching a spelling rather than a property.

That is `SW-20`'s failure mode in its plainest form, and it had been sitting in
the tree since generation 7 in a module nobody had reason to re-read. It is
rewritten over the AST: every `write_text` call in the generator must pass
`encoding`, whatever else it passes and in whatever order. It also now fails
loudly if the generator stops calling `write_text` at all, which the substring
version could not distinguish from a rename.

**Three other guards fired on the sweep, and all three were right to.** The
interpolation allowlist demanded a reason for pass 3's anchor-to-anchor
collocation, and got the same one generations 9, 10 and 12 gave. `mypy` refused
to accept new findings as baseline drift, which is exactly what its recorded
invocation says it will do — the new module was made clean rather than the
baseline moved. And the README badge guard caught the collected count going
stale. None of those is a defect in the guard; they are the tree noticing it had
changed.
---

## 5. Limitations

* **The pre-registered test still pools across `b`.** The axes do not span the
  same split ratios, and standardising makes cells comparable *under the null*
  without making the comparison `b`-matched. The verdict is `DOES_NOT_SEPARATE`,
  so this does not flatter the result — but had it come out `SEPARATES`, this
  limitation would have been load-bearing, and it is recorded for that reason.
* **The pre-registration contains a justification that is not correct, and it
  is hashed in.** `minimum_cells = 4` is defended in the hashed text as "below
  four admissible cells on either axis the exact test cannot reach *p* = 0.05
  one-sided". That is false: at 3 against 3 the minimum achievable one-sided
  *p* is exactly 0.05, and at 2 against 5 it is 0.048. The **rule** is still a
  sound conservative floor — it is stricter than necessary, never looser — and
  it was **inert here**, because every device came in at 8 admissible width
  cells and 7 spacing cells. But it is a sentence that reads like a derivation
  and is not one, written by the same hand that spent §3.1 objecting to a
  statistic defended the same way. Recorded rather than corrected: the text was
  hashed before the measurement and editing it now would defeat the point of
  hashing it. Reproduce the table with `scipy.stats.mannwhitneyu(...,
  method="exact")` over perfectly separated samples.
* **Two held-out devices, not nine.** The ruling offered the nine `g9-1`
  operating points or a held-out subset of width cells. Neither was used:
  `device_p10` and `device_p90` carry the same width/spacing axis design, so the
  pre-registered statistic and its control transfer exactly, which the `g9-1`
  windows do not. The cost is a test on two devices.
* **`new_solves` is not zero for the measurement**, for the reason pass 2 gave —
  `outputs/g9` stores singular values and never `U`. Only the analysis is held at
  zero, and that is AST-guarded and shown non-vacuous by scanning the measurement
  path with the same predicate.
* **The `PROV-08` copies are preserved, not durable.** See §1.
* **`EXT-02` and `EXT-03` are still broken**, in their own repositories, on their
  own schedule, by whoever owns them. This loop has no authority there and did
  not acquire any by copying them.
* **The `EOL-02` scan reaches call sites only.** `DataFrame.to_csv`,
  `numpy.savetxt` and `Figure.savefig` own their handles and are out of scope; a
  runtime-computed `mode=` would also be invisible, and there is none today.
