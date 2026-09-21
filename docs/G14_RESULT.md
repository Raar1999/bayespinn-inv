# Generation 14 — the archive is durable, and `MECH-01` ends at `U-EMPIR`

**Status** run under the operator ruling of 2026-08-28 (the pass-4 ruling). That
ruling resolved the archive question with an accession/derivative split, ordered
one last `MECH-01` method, enacted `DIFF-01`, and — decisively — **fixed the
terminal condition before the method ran**.

**Ladder: `L0 → L1`, descended.** Licensed by the `U-EMPIR` verdict in
`docs/UEMPIR_MECH01_g14.md`. This is the ladder doing the job it was built for,
not a retreat: `L1` was already satisfied on everything except the verdict
itself.

**The headline.** Pass 4's pre-registered rule returned `GENERIC_ROW_COUNT`, and
**the registered meaning of that outcome is contradicted by the measurement that
produced it**. The loop may not relabel after the fact, so pass 4 is
inconclusive, that is method three, and `U-EMPIR` is issued.

---

## 1. The archive — accession, derivative, bundle

The ruling's three-role split resolves what generation 13 left as a binary.

**Accession** — `F:\backups\extgit-20260828\`. All **854 files set read-only** at
the filesystem level. Verified after locking: every repository still resolves its
full survivor count under read-only commands. No write command has been run in
these copies and none ever will be. *Disclosure:* they are not pristine copies of
the originals — generation 13's ruling ordered `fsck --lost-found`, which
materialised `.git/lost-found/` inside them. That is the accession's state as
accessioned, and it is recorded rather than glossed.

**Derivative** — `F:\backups\extgit-20260828-derivative\`. File-count parity with
the accession confirmed before anything was written. Then the rescue refs:

| | refs written | survivors | now reachable | dangling left |
|---|---|---|---|---|
| `AIEF` | 1 | 63 | 63 | **0** |
| `fabkg-bench` | 7 | 393 | 393 | **0** |
| `invspec` | 3 | 80 | 80 | **0** |
| `EXT-04` | 60 | 1,073 | 1,073 | **0** |

The eleven refs across the three rewritten trees pin all 536 of their dangling
survivors, exactly as the tip analysis predicted. `EXT-04`'s 60 are its own
separate danglers; its 1,073 mapped survivors were already reachable, which is
the property that made its freeze sufficient.

**Bundle** — `F:\backups\extgit-20260828-bundles\`. Each cloned back into a fresh
bare repository and re-counted against the census:

| bundle | census | carried | `git bundle verify` |
|---|---|---|---|
| `AIEF` | 63 | **63** | okay |
| `fabkg-bench` | 393 | **393** | okay |
| `invspec` | 80 | **80** | okay |
| `EXT-04` | 1,073 | **1,073** | okay |

**Every bundle carries its full census and nothing in it can be pruned, because
nothing in it is unreachable.** 91 MB accession, 92 MB derivative, 83 MB bundles.

---

## 2. `MECH-01` pass 4 — the method, and what it returned

`scripts/run_mech01_pass4.py`. Pre-registration hashed before the first subset
was drawn:

```
measure   61ce9ac936e469a30be5ce1aad04e724ff4ff91586b1b3067763505b0eaf4e86
outcomes  898c28f0e8a250aea5020c246c7917acfbf23033fbefe5ce3a62932517b90546
```

`PILOT-01`: 15.35 s per cell × 4 = 61.4 s projected before the run was decided
on.

### 2.1 Why it was distinct in kind

Passes 2 and 3 were both **contrasts between two axes**. Pass 3 proved that
design unsalvageable: the axes do not span the same range of the nuisance
`b = n_out/n_rows`. Pass 4 is **a null matched on row count by construction** —
at one device and the widest window, the nested bias sequence against uniformly
random subsets of the same size drawn from the same universe. Nothing needs
standardising because nothing is contrasted across incomparable ranges. That
property is asserted structurally in the guard, not assumed.

`R1''`, the reproduction control: **8 of 8** singular values bit-identical to
generation 9's `wide_0.15_0.90` cell. The Jacobians are the objects `SPEC-g9-1`
measured. The Jacobians are now **stored** — the thing passes 2 and 3 each had to
recompute because nobody had written it down.

### 2.2 What it returned

| device | | `T` | two-sided *p* | |
|---|---|---|---|---|
| `device_p10` | held out | 0.8095 | **0.1485** | does not clear |
| `device_p90` | held out | 0.9892 | **< 0.0001** | clears |
| `g8_control` | contrast | 0.9669 | 0.0040 | clears |
| `device_p50` | contrast | 0.9684 | 0.0040 | clears |

The chain null's mean `T` sits at 0.4946–0.5019 at every device, so the
percentile machinery is calibrated and the p-values mean what they say. That is
asserted by the guard, because a drifting null would have made every number here
void while still looking like a result.

**The pre-registered rule required both held-out devices to clear. `device_p10`
did not. The verdict is `GENERIC_ROW_COUNT`.**

### 2.3 Why that verdict cannot be written as the answer

`GENERIC_ROW_COUNT` was registered to mean: *"the nested windows track the null …
flattening is a consequence of row count alone, with nothing device-specific or
regime-specific in it."*

**They do not track the null.** All four devices sit above the chain null, in the
same direction, three of them at *p* ≤ 0.005. The nested windows are consistently
**less** flat than random subsets of equal size — which is neither of the two
things the ruling enumerated, and which the two-sided test was written to be able
to see.

So the instrument returned a label whose registered meaning is false. Writing the
deflationary answer would put a claim in the spine that this loop's own
measurement contradicts. Claiming `IDENTITY_MATTERS` would be changing the rule
after reading the result. **Neither registered outcome describes what happened**,
and that is the definition of inconclusive for the registered instrument.

### 2.4 The mechanism of that inconclusiveness, measured

`scripts/mech01_pass4_mechanism.py`, `new_solves = 0`, a description and not a
test.

The nested sequence is **contiguous** by construction; a random subset of the
same size is **scattered**. Closely spaced biases sample nearly the same
operating condition, so their rows are nearly collinear and the head dominates —
a property of any smooth response, not of a device or a transport regime.
`corr(gap, spread)` runs **−0.31, −0.59, −0.49, −0.45**: wider bias range, smaller
gap.

Regressing the gap on the subset's bias range and placing the nested set's
**residual** among the null residuals:

| device | | raw percentile | residual percentile |
|---|---|---|---|
| `device_p10` | held out | 0.810 | **0.492** |
| `device_p90` | held out | 0.989 | **0.947** |
| `g8_control` | contrast | 0.967 | 0.880 |
| `device_p50` | contrast | 0.968 | 0.892 |

At `device_p10` the departure is **entirely** a spread effect — 0.492 is exactly
ordinary. At the other three a residual survives. **The two held-out devices
disagree, 0.492 against 0.947**, and that is the whole finding: the part of the
departure that is not generic smoothness is not reproducible across the devices
the rule was written to require.

### 2.5 A defect in the pre-registration, and it is mine

The threshold clause states that flattening *less* than random "would equally
refute genericity" — which is why the test is two-sided — while the decision rule
maps everything short of `IDENTITY_MATTERS` onto `GENERIC_ROW_COUNT`. **Those two
sentences are inconsistent, and the observed pattern fell exactly in the gap
between them.**

It is hashed and it stays hashed. A pre-registration corrected after reading the
result is not a pre-registration. This is the second such defect in two
generations — pass 3's `minimum_cells = 4` justification was also wrong and also
left in — and the pattern is worth naming: **the prose around a pre-registered
statistic is not itself pre-registered by being hashed with it.** Hashing fixes
the text; it does not make the text correct.

---

## 3. `U-EMPIR`, and the descent

`docs/UEMPIR_MECH01_g14.md`, sha256
`e34c812fe7401ca3f1efe164e521455b376850445781f9004a4d6ada81b9cd40`.

**Written before the fallback work began**, per `U-0`. Three distinct methods,
each named with why it was expected to work and the measured mechanism of its
failure:

1. **Spatial localisation** (`SPEC-g10-1`, generation 10) — FALSIFIED. The
   vectors localise *more* as the window widens, the opposite of the prediction,
   tracking width at −0.433.
2. **The row side** (generations 12–13) — FALSIFIED out of sample. Confounded with
   the split ratio at −0.95 to −0.98; device offset 1.572 against an axis
   difference of 0.22.
3. **The matched-count null** (generation 14) — INCONCLUSIVE, as above.

**The ladder descended `L0 → L1`.** `LD-1` is satisfied and shown rather than
asserted: the rungs block hashes `fdc1b0e7…` before and after the append, byte
for byte. The file hash moves `a2596365…` → `184e1ef0…`, an authorised append to
the log the file itself declares append-only, and exactly one line changed.

**`LD-4`'s reachability condition** is recorded in the verdict: a device set that
does not disagree; or a fourth method distinct in kind from all three — every
method so far reads the *same* Jacobians, so a design that perturbs the physics
rather than re-reading the spectrum would not share their failure mode; or an
instrument in which bias **spread** and bias **identity** are independently
variable, which this repository's observation sets cannot provide. `LD-5` obliges
every future Phase A to re-evaluate all three.

`U-EMPIR` **expires after two generations**. Generation 16 must re-test or
re-issue.

---

## 4. `DIFF-01` enacted

`docs/RULES_ENACTED.md`, `docs/SWEEP_REGISTER.json`, guarded by
`tests/test_diff01_blast_radius_g14.py`.

The rule is self-enforcing rather than declarative, which is `SKIP-01`'s lesson
applied: a register nobody updates guards nothing. There is no natural signal for
"a sweep happened", so the guard manufactures one from git — **a commit touching
at least ten files is sweep-shaped and must appear in the register by subject.**
Hand edits are deep and narrow; codemods are shallow and wide, and the file count
is that signature.

Three controls: a planted overrun that did not halt is caught; a sweep that
stayed within its estimate is not flagged, because a guard that rejects
everything also looks correct; and the threshold is shown to be a **ratio** and
not a line count, by exhibiting a three-line edit that touches forty (an
incident) beside a four-thousand-line edit that touches four thousand two hundred
(not one).

Scope is the enactment commit forward, following `DOC-07`'s design. The
generation-13 `EOL-02` sweep is the founding register entry and doubles as the
guard's positive control from history.

---

## 5. Limitations

* **The pre-registered binary was mis-specified for the pattern that occurred**,
  and the loop had to decline both of its own labels. That is the honest reading
  and it is also an admission that pass 4's decision rule was not thought through
  as carefully as its construction was. The construction is sound; the readout
  was not.
* **The held-out devices are not naive.** `device_p10` and `device_p90` were
  measured by pass 3. The ruling specified them and pass 4's design came from
  pass 3's failure mechanism rather than from these devices' values, but they are
  held out from the *construction*, not unseen.
* **Two held-out devices is thin**, and pass 4's result is precisely a
  disagreement between two devices. This is the first reachability condition and
  it is the cheapest of the three.
* **The `DIFF-01` file-count trigger is a proxy.** A mechanical edit confined to
  nine files is invisible to it. Stated rather than papered over: the rule reaches
  the *shape* of a sweep, not its intent, because intent is not visible to a test.
* **The accession is not pristine**, per §1.
* **`EXT-02` and `EXT-03` are still broken** in their own repositories, on their
  own schedule, by whoever owns them.
* **`CI-01`/`CI-02` remain open.** The pull request is the operator's and was not
  opened here.
