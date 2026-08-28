# `U-EMPIR` — `MECH-01`, three distinct methods, characterised

**Issued** generation 14, 2026-08-28, under the operator ruling of 2026-08-28 §4,
which fixed this terminal condition **before** pass 4 was run and before its
result was known.

**Written before the fallback work begins, per `U-0`.** Nothing in the
generation-14 write-up preceded this document. A verdict retrofitted to explain
where the loop ended up is void, so this one is dated ahead of the thing it
licenses.

**Class** `U-EMPIR`. Reversible. **Expires after two generations** — generation
16 must either re-test or re-issue. It is not a claim that `MECH-01` is
unanswerable; it is a claim that three distinct methods have been tried and
characterised, which is the standard the ladder sets for descending.

---

## The question

`MECH-01`: widening the bias window flattens the Jacobian's spectrum and lifts
the rank from 1 through 4. **Why?** Not *whether* — the effect is measured,
reproduced across generations, and bit-identical on re-measurement. The open
item is the mechanism.

---

## Method 1 — spatial localisation of the singular vectors (`SPEC-g10-1`, generation 10)

**What it proposed.** If widening admits new physics, the singular vectors should
**localise in space**: narrow low-bias windows giving vectors concentrated near
the junction, wider windows giving delocalised ones.

**Why it was expected to work.** It is the cheapest mechanism consistent with the
observation and it is directly measurable from vectors the loop already had. It
also had a clean falsifier, stated the right way round after `WIT-01`.

**Verdict: FALSIFIED**, at both devices, under a measure hashed before the first
SVD.

**Mechanism of failure.** The vectors become **more** localised as the window
widens — the opposite of the prediction — and the localisation measure tracks
*width* at `−0.433` rather than the predicted direction. The proposal was not
merely unsupported; the sign was inverted. Generation 10 stopped there and
recorded "do not chase a second localisation story", which held.

---

## Method 2 — the row side: which bias rows carry the trailing directions (generations 12 and 13)

**What it proposed.** If widening adds *information*, the trailing singular
directions `σ₂…σ₄` should be carried by the bias rows the widening **adds** —
those outside the narrowest reference core — rather than by rows already present.

**Why it was expected to work.** It is distinct in kind from method 1: method 1
asks where in *space* the directions live, method 2 asks which *measurements*
carry them. It was the natural second question and it used the same Jacobians.

**Verdict: FALSIFIED out of sample** at generation 13, after generation 12's
sign discriminator was voided by its own control axis.

**Mechanism of failure, measured.** The statistic is confounded with the split
ratio `b = n_out/n_rows`, and the two axes being contrasted **do not overlap in
it**: the width axis sweeps `b` over 0.0625–0.875 and peaks at 0.375–0.50, while
the spacing axis — the control — only ever visits 0.857–0.929. So the axes were
compared where they do not overlap. After standardising against the
`Beta(n_out/2, n_in/2)` null that `b` induces, and pre-registering an exact
one-sided Mann-Whitney requiring both held-out devices to clear:
`device_p10` clears at `p = 0.00062`, `device_p90` does not at `p = 0.30629`.
`DOES_NOT_SEPARATE`.

The post-hoc characterisation is unambiguous: `corr(dz, b)` runs **−0.95, −0.97,
−0.98, −0.71** along the width axis, and the device-to-device offset spread is
**1.572** against a largest axis difference at matched `b` of **0.22**. The
statistic measured the window and the device. A discriminator swamped sevenfold
by nuisance is not a weak discriminator; it is a different measurement.

---

## Method 3 — row-subset growth against a random-row null (generation 14)

**What it proposed.** Drop the contrast entirely. At one device and the widest
window, compare the **nested** bias sequence — the `k` biases nearest the window
centre, which is the order widening admits them — against **uniformly random
`k`-subsets of the same universe**. Matched on row count by construction. Does
widening flatten because of *which* biases arrive, or merely because *more*
arrive?

**Why it was expected to work.** It removes the exact defect that sank method 2.
Pass 3 proved the two axes do not span the same range of the nuisance; a null
matched on row count by construction cannot have that problem, so nothing needs
standardising because nothing is contrasted across incomparable ranges. And both
of its outcomes were answers: a departure from the null makes `MECH-01` a regime
question, and tracking the null is a complete deflationary answer.

**Verdict: INCONCLUSIVE.** The pre-registered rule returned `GENERIC_ROW_COUNT`
— it required both held-out devices to clear and `device_p10` did not, at
`p = 0.1485` against `device_p90`'s `p < 0.0001`. **But the registered *meaning*
of that outcome is contradicted by the measurement that produced it.**
`GENERIC_ROW_COUNT` was registered to mean "the nested windows track the null …
nothing device-specific or regime-specific in it", and they do not track it: all
four devices sit above the chain null in the same direction, three at
`p ≤ 0.005`, with the nested windows consistently **less flat** than random
subsets of equal size.

So the instrument returned a label whose registered meaning is false. Neither
registered outcome describes what happened, and the loop may not relabel after
the fact.

**Mechanism of failure, measured.** The departure is mostly **bias spread**, a
property of any smooth response rather than of this device or any transport
regime. `corr(gap, spread)` runs **−0.31 to −0.59**: sets spanning a wider bias
range have a smaller gap behind the head. The nested sequence is contiguous by
construction, so it is narrow-spread at every `k`, and closely spaced biases give
nearly collinear rows. Regressing the gap on the subset's bias range and placing
the nested set's **residual** among the null residuals:

| device | | raw percentile | residual percentile |
|---|---|---|---|
| `device_p10` | held out | 0.810 | **0.492** |
| `device_p90` | held out | 0.989 | **0.947** |
| `g8_control` | contrast | 0.967 | 0.880 |
| `device_p50` | contrast | 0.968 | 0.892 |

At `device_p10` the departure is **entirely** a spread effect — residual
percentile 0.492, which is exactly ordinary. At the other three a residual
survives. **The two held-out devices disagree**, 0.492 against 0.947, which is
why nothing can be concluded: the part of the departure that is not generic
smoothness is not reproducible across the devices the rule was written to
require.

**A second defect, in the pre-registration itself, and it is mine.** The
threshold clause states that flattening *less* than random "would equally refute
genericity" — which is why the test is two-sided — while the decision rule maps
everything short of `IDENTITY_MATTERS` onto `GENERIC_ROW_COUNT`. Those two
sentences are inconsistent, and the observed pattern fell exactly in the gap
between them. It is hashed and it stays hashed; a pre-registration corrected
after reading the result is not a pre-registration. It is recorded here and in
`docs/G14_RESULT.md` instead.

---

## The verdict

Three attempts by **distinct** methods — a spatial-localisation test, an
information-attribution contrast, and a matched-count null — each pre-registered,
each with its failure characterised by measurement rather than by adjective. Two
falsified, one inconclusive with the inconclusiveness itself measured.

`U-EMPIR` is issued for `MECH-01`.

**What this does not say.** It does not say the mechanism does not exist, nor
that it is unmeasurable in principle. `MECH-01` is not withdrawn and its status
stays `OPEN`. The effect it asks about is real and reproduces bit-for-bit.

**What it licenses.** The descent `L0 → L1` under `LD-3`, and nothing else.

---

## Reachability condition (`LD-4`)

`L0` becomes attainable again when **any one** of these is true. They are written
now, before the write-up, so that a later generation is not free to invent an
easier one.

1. **A device set that does not disagree.** Pass 4's residual percentiles split
   0.492 against 0.947 across two held-out devices. A pre-registered measurement
   over **more than two** devices — enough to say whether the surviving residual
   is a property of devices or of noise — would settle what pass 4 could not.
   `SPEC-g9-1` selected three from a candidate pool; the pool is still there and
   the selection rule is already pre-registered.

2. **A fourth method that is distinct in kind from all three.** Not a fourth
   statistic over these Jacobians. All three methods so far read the *same*
   objects — the chart-G `d=16` Jacobians at `SPEC-g9-2`'s windows. A method that
   perturbs the physics rather than re-reading the spectrum — for instance
   holding the transport regime fixed while varying the window, so that "which
   regimes the added biases sample" becomes a manipulated variable rather than an
   inferred one — would not share their common failure mode.

3. **An instrument that separates spread from identity.** Every method so far is
   defeated by the same thing in a different costume: the quantity of interest is
   entangled with a nuisance that the available design cannot hold fixed —
   spatial extent in method 1, the split ratio in method 2, bias spread in method
   3. An experimental design in which bias **spread** and bias **identity** are
   independently variable would break that pattern. This repository's observation
   sets cannot do it, which is why this is a reachability condition and not a
   work item.

**`LD-5` obliges every future Phase A to re-evaluate all three.** If one is
satisfied, the loop climbs and says so.
