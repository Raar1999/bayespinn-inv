"""G10: what *is* the rank a property of, and is the degeneracy's geometry chart-dependent?

Oracle-arbitrated throughout; the surrogate is never called (``SPEC-g6-5``,
``PH-22``). Every phase writes its own JSON so a later phase failing cannot cost
an earlier phase's measurement.

    PYTHONPATH=src python scripts/run_g10.py --out outputs/g10 --phases \
        preregister,localisation,ridge_basin,wit01,validity,negative_control

The gap this generation exists to aim at
----------------------------------------
Generation 9 recorded its own highest remaining scientific risk as a
mechanism-shaped hole: nine operating points establish that the relative
sensitivity of junction, dimension and interpolant is **not** a property of this
problem, and give no account of what it *is* a property of. The one axis that is
stable is the observation set, and generation 9 split it in two -- window
**width** sets the rank (1 -> 4), spacing moves only the spectrum.

``SPEC-g10-1`` tests the cheapest mechanism consistent with that split: if the
bias window sets which transport regimes the terminal current is sensitive to,
then the observable directions should **localise in space**, narrow low-bias
windows concentrating them near the junction and wide windows delocalising them.
Reported either way; a negative is a paragraph, not a generation.

``SPEC-g10-2`` removes a confound generation 9 introduced. Its ridge/basin split
compared chart G at ``d = 4`` against chart J at ``d = 16``, which differs in
*both* chart and dimension, so "the geometry of the degeneracy is chart-dependent"
was not measured. The 37 chart-L witnesses at ``d = 16`` sit unused in
``outputs/g8/reproduce.json``; barriers on them are matched-``d`` against chart J
and separate the two axes.

``SPEC-g10-3`` states a boundary rather than testing one, and ``WIT-01`` is
retro-applied to every witness count on the claim surface.

Reuse, deliberately
-------------------
``BarrierCriterion``, ``build_solver``, ``cell_spectrum`` and ``_barrier_between``
are **imported from** ``scripts/run_g9.py`` rather than restated. Three witness
sets compared through one barrier metric is only one ruler if it is literally one
function, and a criterion whose hash is *asserted* to match generation 9's is
weaker than one that cannot fail to. The import of a private helper is the point:
this file may not have its own copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_g9 import (
    ALPHAS,
    MIN_SNR,
    REL_STEP,
    WIDTH_CENTRE,
    WIDTHS,
    BarrierCriterion,
    _barrier_between,
    _spacing,
    build_solver,
    cell_spectrum,
    window_biases,
)

from bayespinn_inv.inverse.charts import (
    ChartG,
    ChartJ,
    ChartL,
)
from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
)
from bayespinn_inv.inverse.identifiability import (
    singular_vector_localisation,
)
from bayespinn_inv.inverse.witness_admissibility import (
    AdmissibilityRule,
    admissibility,
    apply_to_witness_set,
)
from bayespinn_inv.utils.provenance import RunManifest

G6_ARTEFACT = "outputs/global_identifiability_g6/global_identifiability.json"
G8_CHART_J = "outputs/g8/chart_j.json"
G8_REPRODUCE = "outputs/g8/reproduce.json"
G9_BASINS = "outputs/g9/basins.json"
G9_OP_POINTS = "outputs/g9/op_points.json"
G9_RANK_OBS = "outputs/g9/rank_obs.json"
G9_PREREGISTER = "outputs/g9/preregister.json"

#: The adopted observation set and where it comes from. Quoted, not chosen here.
SPEC_G6_CONVERGENCE = "docs/spec/SPEC_g6.md section 1b"


# ===========================================================================
# Pre-registration -- written and hashed BEFORE anything is measured
# ===========================================================================

@dataclass(frozen=True)
class LocalisationMeasure:
    """``SPEC-g10-1``: what "localised" means, fixed before the first SVD.

    The clause requires a *stated localisation measure fixed before looking*,
    because "the vectors localise" is the kind of claim that can be made true by
    choosing the statistic afterwards. Everything decisive is here.

    The primary statistic
        ``spread_fraction`` of the **leading** right singular vector: the
        participation ratio of ``v_1**2`` over the anchor coordinates, divided by
        ``d``. It runs from ``1/d`` (all weight on one anchor) to ``1`` (uniform),
        it is invariant to the sign gauge of a singular vector, and it does not
        depend on the number of Jacobian rows -- which matters, because the
        oracle certifies 13 to 16 biases depending on the window and a statistic
        that moved with the row count would be measuring the SNR gate.

    The decision
        The hypothesis predicts a **width** effect and no **spacing** effect. So
        it is supported only if, at *every* device measured, the leading vector's
        spread rises with window width at ``spearman >= min_rho`` and the range it
        covers over width is at least ``min_range_ratio`` times the range it
        covers over spacing. Both halves are required: a trend with no contrast
        against spacing would be consistent with any monotone artefact of window
        size, and a contrast with no trend is not the claim.

    Reported, and deliberately NOT decisive
        the centroid and its distance from the junction; the rms spread; the same
        statistics for ``v_2 .. v_4``; and the rank correlation between the
        window's rank and the leading vector's spread. The junction-distance is
        the most *interesting* of these and is exactly why it is not the primary:
        the hypothesis was stated in terms of it, and a statistic that a
        hypothesis names is the one most likely to be read generously.
    """

    primary: str = ("spread_fraction of the leading right singular vector = "
                    "participation ratio of v_1**2 over anchors, divided by d")
    primary_vector_index: int = 0
    n_vectors_reported: int = 4
    reference: str = ("the junction, which charts G and L pin at the device "
                      "midpoint")
    min_rho: float = 0.7
    min_range_ratio: float = 2.0
    decision: str = ("SUPPORTED iff at EVERY device: spearman(width, "
                     "spread_fraction of v_1) >= min_rho AND "
                     "range over width >= min_range_ratio * range over spacing. "
                     "FALSIFIED otherwise, and reported either way.")
    reliability: str = ("a right singular vector below the identifiable rank "
                        "spans a near-null subspace and its orientation there is "
                        "not determined by the data; such vectors are reported "
                        "and stamped unreliable, never used in the decision")
    secondary_reported: Tuple[str, ...] = (
        "centroid", "reference_distance", "rms_spread",
        "spearman(rank_at_operational_cutoff, spread_fraction of v_1)")
    cells: str = ("the same devices, widths and alphas as SPEC-g9-2's "
                  "rank(observation set), cell for cell, so the localisation "
                  "curve and the rank curve are the same experiment")

    def measure_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["measure_hash"] = self.measure_hash()
        return out


@dataclass(frozen=True)
class RidgeBasinDecision:
    """``SPEC-g10-2``: how a barrier set becomes "ridge" or "basin", fixed first.

    Generation 9 measured two sets and described them in words -- chart G at
    ``d = 4`` "at the instrument's own floor", chart J at ``d = 16`` "59x the
    floor". Adding a third set makes those words a classification, and a
    classification invented after the third number is not one.

    The classifier
        ``RIDGE`` if at least ``ridge_fraction`` of the witness pairs have a
        barrier at or below the floor barrier ``0.5 * B``; ``BASIN`` if **none**
        does; ``MIXED`` in between. On generation 9's numbers chart G gives 6/13
        = 0.46 -> RIDGE and chart J gives 0/13 -> BASIN, so the thresholds
        reproduce the existing reading rather than replacing it.

    What the third cell decides
        Chart L at ``d = 16`` is matched in ``d`` to chart J and matched in
        interpolant *family* to chart G, so it is the one cell that separates the
        two axes:

        ===========================  =========================================
        chart L, d=16 classifies as  the ridge/basin split is then a property of
        ===========================  =========================================
        RIDGE                        the **chart**: two charts at the same d
                                     disagree, and the odd one out is the chart
                                     with the free junction coordinate
        BASIN                        the **dimension**: both d=16 cells are
                                     basins and the only ridge is the d=4 one
        MIXED                        neither, and the honest answer is that one
                                     more cell was not enough
        ===========================  =========================================

    The ruling's own falsifier is inverted, and this is where that is recorded
    ------------------------------------------------------------------------
    The operator ruling of 2026-08-26 states the ``SPEC-g10-2`` falsifier as:
    *"chart L d=16 sits at the floor like chart G d=4, which would make the
    ridge/basin split a dimension effect rather than a chart effect"*. That is the
    wrong way round. If chart L at ``d = 16`` sits at the floor and chart J at
    ``d = 16`` does not, then two charts at **the same dimension** disagree, which
    is a chart effect; ``d = 4`` and ``d = 16`` would then appear on the same side
    of the split, which is precisely what a dimension effect cannot do. The
    outcome that makes it a dimension effect is the other one -- chart L behaving
    like chart J.

    This is written into the pre-registration, with its hash, **before the third
    set is measured**, so that the correction cannot be mistaken for a reading of
    the result.
    """

    floor_barrier: str = "0.5 * B_certified log-units, inherited unchanged from BarrierCriterion"
    ridge_fraction: float = 1.0 / 3.0
    classifier: str = ("RIDGE if at least ridge_fraction of witness pairs are at "
                       "or below the floor barrier; BASIN if none is; MIXED "
                       "otherwise")
    matched_cell: str = "chart L, d=16 -- matched in d to chart J, matched in interpolant family to chart G"
    if_matched_cell_is_ridge: str = "chart effect: two charts at one d disagree"
    if_matched_cell_is_basin: str = "dimension effect: both d=16 cells are basins and the only ridge is d=4"
    if_matched_cell_is_mixed: str = "neither; one more cell was not enough"
    rulings_stated_falsifier: str = (
        "chart L d=16 sits at the floor like chart G d=4, which would make the "
        "ridge/basin split a dimension effect rather than a chart effect")
    rulings_stated_falsifier_is_inverted: bool = True
    why_inverted: str = (
        "chart L at the floor while chart J at the same d is not means two "
        "charts at one dimension disagree, and d=4 and d=16 land on the same "
        "side; that is a chart effect. The dimension reading requires chart L to "
        "behave like chart J, not like chart G.")
    reproduction_control: str = (
        "chart G d=4 and chart J d=16 are re-measured here through the same "
        "imported function; their barrier medians must reproduce generation 9's")

    def decision_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["decision_hash"] = self.decision_hash()
        return out


def phase_preregister(root: Path, out: Path) -> Dict:
    print("=" * 74)
    print("PHASE 0  PRE-REGISTRATION (AH-14): the rules, before the numbers")
    print("=" * 74)
    loc, rb, adm, crit = (LocalisationMeasure(), RidgeBasinDecision(),
                          AdmissibilityRule(), BarrierCriterion())

    # The barrier criterion is generation 9's object, imported. Assert that the
    # hash on generation 9's own disk matches, so "one ruler" is checked rather
    # than claimed.
    g9_pre = json.loads((root / G9_PREREGISTER).read_text(encoding="utf-8"))
    g9_hash = g9_pre["barrier_criterion"]["criterion_hash"]
    if g9_hash != crit.criterion_hash():
        raise SystemExit(
            "the barrier criterion imported from run_g9 no longer hashes to the "
            f"value generation 9 registered.\n  g9 on disk: {g9_hash}\n"
            f"  imported:   {crit.criterion_hash()}\n"
            "SPEC-g10-2 compares three witness sets through one metric; if the "
            "metric moved, the comparison is between two rulers.")

    doc = {
        "written_before": ("any SVD, any barrier and any admissibility verdict "
                           "in this generation. Every later phase recomputes "
                           "these hashes and refuses to run on a mismatch."),
        "localisation_measure": loc.to_dict(),
        "ridge_basin_decision": rb.to_dict(),
        "witness_admissibility_rule": adm.to_dict(),
        "barrier_criterion": crit.to_dict(),
        "barrier_criterion_matches_generation_9": True,
        "barrier_criterion_g9_hash": g9_hash,
        "what_would_falsify_g10_1": (
            "the leading vector's spread does not track window width, or tracks "
            "spacing equally. Pre-registered as reportable either way (AH-04, "
            "AH-13): a negative closes the mechanism question as unanswered by "
            "this measurement and is a paragraph, not a further generation."),
        "what_would_falsify_g10_2": (
            "see ridge_basin_decision. The ruling's own statement of this "
            "falsifier is inverted and the correction is registered here, "
            "before the third set is measured."),
    }
    for k, h in (("localisation_measure", loc.measure_hash()),
                 ("ridge_basin_decision", rb.decision_hash()),
                 ("witness_admissibility_rule", adm.rule_hash()),
                 ("barrier_criterion (g9)", crit.criterion_hash())):
        print(f"  {k:32s} {h[:32]}...")
    return doc


def _check_preregistration(out: Path) -> Dict:
    """Refuse to measure against a pre-registration that has moved."""
    path = out / "preregister.json"
    if not path.exists():
        raise SystemExit(
            "no preregister.json: run the 'preregister' phase first. A rule "
            "written after the measurement is not a pre-registration.")
    doc = json.loads(path.read_text(encoding="utf-8"))
    for key, obj, attr in (
            ("localisation_measure", LocalisationMeasure(), "measure_hash"),
            ("ridge_basin_decision", RidgeBasinDecision(), "decision_hash"),
            ("witness_admissibility_rule", AdmissibilityRule(), "rule_hash"),
            ("barrier_criterion", BarrierCriterion(), "criterion_hash")):
        on_disk, now = doc[key][attr], getattr(obj, attr)()
        if on_disk != now:
            raise SystemExit(
                f"{key} has changed since it was registered.\n"
                f"  registered: {on_disk}\n  now:        {now}\n"
                "AH-14 forbids continuing.")
    return doc


# ===========================================================================
# Shared machinery
# ===========================================================================

def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank correlation with average ranks for ties. No new dependency.

    Ties matter here: ``rank_at_operational_cutoff`` is an integer that plateaus
    at 4 over most of the width sweep, and a tie-naive rank transform would turn
    that plateau into a spurious ordering.
    """
    x, y = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if x.size < 3 or x.size != y.size:
        return float("nan")

    def _rank(v):
        order = np.argsort(v, kind="stable")
        r = np.empty(v.size, dtype=np.float64)
        i = 0
        while i < v.size:
            j = i
            while j + 1 < v.size and v[order[j + 1]] == v[order[i]]:
                j += 1
            r[order[i:j + 1]] = 0.5 * (i + j) + 1.0
            i = j + 1
        return r

    rx, ry = _rank(x), _rank(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0.0 or sy == 0.0:
        return float("nan")
    return float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (sx * sy))


def _devices(root: Path) -> Dict[str, List[float]]:
    """The same two devices SPEC-g9-2 used, read from the same artefacts."""
    ws = json.loads((root / G6_ARTEFACT).read_text(
        encoding="utf-8"))["witness_search"]
    devices = {"g8_operating_point": ws["witnesses"][0]["profile_a_log10"]}
    op_path = root / G9_OP_POINTS
    if op_path.exists():
        op = json.loads(op_path.read_text(encoding="utf-8"))
        for c in op["selection"]["chosen"]:
            if c["name"] == "device_p50":
                devices[c["name"]] = c["theta_chartG_d4"]
    return devices


# ===========================================================================
# Phase 1 -- SPEC-g10-1, singular-vector localisation
# ===========================================================================

def _localisation_cell(sg, chart, theta, biases, cfg, meas: LocalisationMeasure):
    cell, _, rep = cell_spectrum(sg, chart, theta, biases, cfg)
    loc = singular_vector_localisation(
        rep, chart.anchors, reference_position=chart.mid,
        n_vectors=meas.n_vectors_reported,
        rank=cell["rank_at_operational_cutoff"])
    return cell, loc


def phase_localisation(sg, x_si, cfg, root: Path, out: Path,
                       meas: LocalisationMeasure) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  SPEC-g10-1  do the right singular vectors localise in space?")
    print("=" * 74)
    print(f"  measure hashed before the first SVD: {meas.measure_hash()[:32]}...")
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    devices = _devices(root)
    k = meas.primary_vector_index

    doc: Dict = {
        "measure": meas.to_dict(),
        "hypothesis": (
            "the bias window sets which transport regimes the terminal current "
            "is sensitive to, so it sets the rank of the sensitivity operator; "
            "the parameterisation only sets which subspace of profile space that "
            "operator acts on. If so the right singular vectors localise in "
            "space: narrow low-bias windows concentrate them near the junction, "
            "wider windows delocalise them, and the rank 1 -> 4 climb tracks the "
            "number of distinct regimes the window spans."),
        "chart": G16.label(),
        "junction_position_si": float(G16.mid),
        "anchors_si": [float(a) for a in G16.anchors],
        "devices": {},
    }

    for dname, theta4 in devices.items():
        th4 = np.asarray(theta4, dtype=np.float64)
        m16 = np.interp(G16.anchors, G4.anchors, th4)
        rec: Dict = {"theta_chartG_d4": [float(v) for v in th4],
                     "width_curve": [], "spacing_curve": []}
        for w in WIDTHS:
            lo, hi = WIDTH_CENTRE - w / 2.0, WIDTH_CENTRE + w / 2.0
            b = window_biases(lo, hi, 16)
            try:
                cell, loc = _localisation_cell(sg, G16, m16, b, cfg, meas)
            except ValueError as exc:
                rec["width_curve"].append({"width_V": float(w),
                                           "error": str(exc)})
                continue
            rec["width_curve"].append({
                "width_V": float(w), "lo_V": float(lo), "hi_V": float(hi),
                "rows_used": cell["rows_used"],
                "rank_at_operational_cutoff":
                    cell["rank_at_operational_cutoff"],
                "singular_values": cell["singular_values"],
                "localisation": loc,
            })
        for a in ALPHAS:
            b = _spacing(0.15, 0.90, 16, a)
            try:
                cell, loc = _localisation_cell(sg, G16, m16, b, cfg, meas)
            except ValueError as exc:
                rec["spacing_curve"].append({"alpha": float(a),
                                             "error": str(exc)})
                continue
            rec["spacing_curve"].append({
                "alpha": float(a),
                "biases": [float(v) for v in b],
                "rows_used": cell["rows_used"],
                "rank_at_operational_cutoff":
                    cell["rank_at_operational_cutoff"],
                "singular_values": cell["singular_values"],
                "localisation": loc,
            })

        def _pull(curve, key, field_):
            xs, ys = [], []
            for c in curve:
                if "error" in c:
                    continue
                xs.append(float(c[key]))
                ys.append(float(c["localisation"]["vectors"][k][field_]))
            return xs, ys

        wx, wy = _pull(rec["width_curve"], "width_V", "spread_fraction")
        ax, ay = _pull(rec["spacing_curve"], "alpha", "spread_fraction")
        _, wjd = _pull(rec["width_curve"], "width_V",
                       "reference_distance_fraction_of_half_span")
        _, ajd = _pull(rec["spacing_curve"], "alpha",
                       "reference_distance_fraction_of_half_span")
        ranks = [c["rank_at_operational_cutoff"] for c in rec["width_curve"]
                 if "error" not in c]
        rng_w = (max(wy) - min(wy)) if wy else float("nan")
        rng_a = (max(ay) - min(ay)) if ay else float("nan")
        rho_w, rho_a = spearman(wx, wy), spearman(ax, ay)
        rec["summary"] = {
            "vector_index": k,
            "spread_fraction_over_width": wy,
            "spread_fraction_over_spacing": ay,
            "junction_distance_fraction_over_width": wjd,
            "junction_distance_fraction_over_spacing": ajd,
            "rho_width": rho_w,
            "rho_spacing": rho_a,
            "range_over_width": rng_w,
            "range_over_spacing": rng_a,
            "range_ratio": (rng_w / rng_a) if rng_a else float("inf"),
            "rho_junction_distance_vs_width": spearman(wx, wjd),
            "rho_rank_vs_spread": spearman(ranks, wy),
            "width_criterion_met": bool(rho_w >= meas.min_rho),
            "contrast_criterion_met": bool(
                rng_a > 0 and rng_w / rng_a >= meas.min_range_ratio),
        }
        s = rec["summary"]
        s["device_supports_hypothesis"] = bool(
            s["width_criterion_met"] and s["contrast_criterion_met"])
        doc["devices"][dname] = rec
        print(f"  {dname}")
        print(f"    spread(v_{k + 1}) over width   "
              + "  ".join(f"{x:.2f}->{y:.3f}" for x, y in zip(wx, wy)))
        print(f"    spread(v_{k + 1}) over spacing "
              + "  ".join(f"{x:.3f}->{y:.3f}" for x, y in zip(ax, ay)))
        print(f"    rho_width {rho_w:+.3f}   rho_spacing {rho_a:+.3f}   "
              f"range {rng_w:.4f} vs {rng_a:.4f} (ratio "
              f"{s['range_ratio']:.2f})")
        print(f"    -> device supports hypothesis: "
              f"{s['device_supports_hypothesis']}")

    per_device = [r["summary"]["device_supports_hypothesis"]
                  for r in doc["devices"].values()]
    supported = bool(per_device and all(per_device))
    doc["verdict"] = {
        "supported": supported,
        "n_devices": len(per_device),
        "criterion": meas.decision,
        "reading": (
            "the leading observable direction delocalises as the bias window "
            "widens, and does not move with spacing -- the same asymmetry "
            "SPEC-g9-2 found in the rank, now in the direction the rank counts"
            if supported else
            "localisation does not track window width in the pre-registered "
            "sense, so this measurement does not support the regime mechanism. "
            "The gap generation 9 recorded stays open and is reported as a gap; "
            "no second mechanism is chased here (SPEC-g10-1's own instruction)"),
    }
    doc["falsifier"] = (
        "SPEC-g10-1 fires if localisation does not track window width, or "
        "tracks spacing equally. The verdict above is that test, computed from "
        "the hashed criterion rather than from a reading of the curves.")
    print(f"\n  -> SPEC-g10-1 verdict: "
          f"{'SUPPORTED' if supported else 'FALSIFIED'}")
    return doc


# ===========================================================================
# Phase 2 -- SPEC-g10-2, ridge or basin at matched d
# ===========================================================================

def _barrier_set(sg, chart, cfg, biases, kept, pairs, crit: BarrierCriterion,
                 tag: str) -> Dict:
    """Barriers over one witness set and its null control. g9's phase, verbatim."""
    witness_edges, depths = [], []
    for (a, b) in pairs:
        bd = _barrier_between(sg, chart, cfg, biases, kept[a], kept[b], crit)
        witness_edges.append({"pair": [int(a), int(b)], **bd})
        if bd.get("barrier_depth") is not None:
            depths.append(bd["barrier_depth"])

    witness_set = {tuple(sorted(p)) for p in pairs}
    null_pairs: List[Tuple[int, int]] = []
    i = 0
    while len(null_pairs) < len(pairs) and i + 1 < len(kept):
        cand = (i, i + 1)
        if tuple(sorted(cand)) not in witness_set:
            null_pairs.append(cand)
        i += 2
    null_edges, null_depths = [], []
    for (a, b) in null_pairs:
        bd = _barrier_between(sg, chart, cfg, biases, kept[a], kept[b], crit)
        null_edges.append({"pair": [int(a), int(b)], **bd})
        if bd.get("barrier_depth") is not None:
            null_depths.append(bd["barrier_depth"])

    floor = 0.5 * len(biases)
    n_below = sum(1 for e in witness_edges
                  if e.get("barrier_depth") is not None
                  and e["barrier_depth"] <= floor)

    # Descriptive, and NOT part of the registered decision. The barrier walks a
    # straight line in coordinates, so a set whose pairs are further apart has
    # longer lines and, all else equal, deeper barriers. If chart L's witnesses
    # are more separated than chart G's, part of any barrier difference is path
    # length rather than geometry, and the reader needs the number to see that.
    # Added before the third set was measured; used to qualify the reading, never
    # to decide it.
    def _paths(ps):
        return [float(np.linalg.norm(kept[a] - kept[b])) for a, b in ps]

    def _maxsep(ps):
        return [float(np.max(np.abs(kept[a] - kept[b]))) for a, b in ps]

    wpaths, wseps = _paths(pairs), _maxsep(pairs)
    npaths = _paths(null_pairs) if null_pairs else []
    # Zipped over the EDGES rather than over ``depths``: a pair the oracle
    # refused has no depth, and pairing a truncated depth list against the full
    # path list would silently attribute one pair's barrier to another's line.
    _per_unit = [e["barrier_depth"] / L
                 for e, L in zip(witness_edges, wpaths)
                 if e.get("barrier_depth") is not None and L > 0]
    return {
        "tag": tag,
        "chart": chart.name,
        "chart_label": chart.label(),
        "d": int(chart.d),
        "n_witness_pairs": len(pairs),
        "floor_barrier_log_units": floor,
        "witness_pair_barriers": witness_edges,
        "null_control_pair_barriers": null_edges,
        "witness_depth_median": float(np.median(depths)) if depths else None,
        "witness_depth_min": float(np.min(depths)) if depths else None,
        "witness_depth_max": float(np.max(depths)) if depths else None,
        "witness_median_in_floor_units": (float(np.median(depths)) / floor)
        if depths else None,
        "null_depth_median": float(np.median(null_depths)) if null_depths else None,
        "null_depth_min": float(np.min(null_depths)) if null_depths else None,
        "null_median_in_floor_units": (float(np.median(null_depths)) / floor)
        if null_depths else None,
        "witness_pairs_below_the_floor_barrier": n_below,
        "fraction_below_the_floor_barrier": (n_below / len(pairs))
        if pairs else None,
        "path_lengths": {
            "note": ("descriptive context for the barrier depths, not part of "
                     "the registered classifier: the barrier walks a straight "
                     "line in this chart's coordinates, so a set whose pairs "
                     "are further apart has longer lines"),
            "witness_l2_median": float(np.median(wpaths)) if wpaths else None,
            "witness_l2_min": float(np.min(wpaths)) if wpaths else None,
            "witness_l2_max": float(np.max(wpaths)) if wpaths else None,
            "witness_max_coordinate_separation_median":
                float(np.median(wseps)) if wseps else None,
            "null_l2_median": float(np.median(npaths)) if npaths else None,
            "witness_depth_per_unit_path_median": (
                float(np.median(_per_unit)) if _per_unit else None),
        },
    }


def classify(rec: Dict, dec: RidgeBasinDecision) -> Dict:
    frac = rec["fraction_below_the_floor_barrier"]
    if frac is None:
        return {"class": "UNDETERMINED", "fraction_below_floor": None}
    if frac >= dec.ridge_fraction:
        cls = "RIDGE"
    elif frac == 0.0:
        cls = "BASIN"
    else:
        cls = "MIXED"
    return {"class": cls, "fraction_below_floor": float(frac),
            "threshold": dec.ridge_fraction}


def phase_ridge_basin(sg, x_si, cfg, root: Path, out: Path,
                      dec: RidgeBasinDecision, budget_s: float) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  SPEC-g10-2  ridge or basin, at MATCHED d")
    print("=" * 74)
    crit = BarrierCriterion()
    print(f"  barrier criterion (generation 9's, imported): "
          f"{crit.criterion_hash()[:32]}...")
    print(f"  decision registered before the third set:      "
          f"{dec.decision_hash()[:32]}...")
    biases = list(cfg.biases)

    rep = json.loads((root / G8_REPRODUCE).read_text(encoding="utf-8"))
    cj = json.loads((root / G8_CHART_J).read_text(encoding="utf-8"))
    sets = [
        ("chart_G_d4", ChartG(4, x_si), rep["chart_G_d4"]),
        ("chart_L_d16", ChartL(16, x_si), rep["chart_L_d16"]),
        ("chart_J_d16", ChartJ(16, x_si), cj["native_witness"]),
    ]

    # -- the pilot, on the set that is new -----------------------------------
    tagL, chartL, resL = sets[1]
    keptL = np.asarray(resL["kept_log10"], dtype=np.float64)
    ia, ib = resL["witness_pair_indices"][0]
    t0 = time.perf_counter()
    _ = _barrier_between(sg, chartL, cfg, biases, keptL[ia], keptL[ib], crit)
    per_path = time.perf_counter() - t0
    n_paths = sum(2 * len(s[2]["witness_pair_indices"]) for s in sets)
    projected = per_path * n_paths
    pilot = {"seconds_per_path": per_path, "paths_required": n_paths,
             "projected_seconds": projected, "budget_seconds": budget_s,
             "fits": bool(projected <= budget_s),
             "paths_note": ("one path per witness pair plus one per "
                            "null-control pair, in each of the three sets")}
    print(f"  pilot: {per_path:.1f} s/path x {n_paths} paths = "
          f"{projected:.0f} s against a {budget_s:.0f} s budget -> "
          f"{'FITS' if pilot['fits'] else 'DOES NOT FIT'}")
    if not pilot["fits"]:
        print("  dropping SPEC-g10-2 WHOLE: a part-run comparison across three "
              "sets is worse than none")
        return {"criterion": crit.to_dict(), "decision": dec.to_dict(),
                "pilot": pilot, "dropped_whole": True,
                "kept_instead": ("generation 9's two-set reading stands, with "
                                 "its confound stated and unresolved")}

    doc: Dict = {"criterion": crit.to_dict(), "decision": dec.to_dict(),
                 "pilot": pilot, "dropped_whole": False, "sets": {}}
    for tag, chart, res in sets:
        kept = np.asarray(res["kept_log10"], dtype=np.float64)
        pairs = [tuple(p) for p in res["witness_pair_indices"]]
        rec = _barrier_set(sg, chart, cfg, biases, kept, pairs, crit, tag)
        rec["classification"] = classify(rec, dec)
        doc["sets"][tag] = rec
        print(f"  {tag:12s} {rec['n_witness_pairs']:3d} pairs   median "
              f"{rec['witness_depth_median']:10.2f} "
              f"({rec['witness_median_in_floor_units']:7.2f} floor units)   "
              f"min {rec['witness_depth_min']:8.2f}")
        print(f"               null median {rec['null_depth_median']:10.2f} "
              f"({rec['null_median_in_floor_units']:7.2f} floor units)   "
              f"null min {rec['null_depth_min']:.2f}")
        print(f"               at or below the floor: "
              f"{rec['witness_pairs_below_the_floor_barrier']}"
              f"/{rec['n_witness_pairs']} -> "
              f"{rec['classification']['class']}")

    # -- the reproduction control -------------------------------------------
    g9 = json.loads((root / G9_BASINS).read_text(encoding="utf-8"))
    repro = {}
    for tag in ("chart_G_d4", "chart_J_d16"):
        a = g9["sets"][tag]["witness_depth_median"]
        b = doc["sets"][tag]["witness_depth_median"]
        rel = abs(b - a) / max(abs(a), 1e-300)
        repro[tag] = {
            "generation_9_median": a, "generation_10_median": b,
            "relative_change": float(rel),
            "reproduces": bool(rel < 1e-9),
            "generation_9_below_floor":
                g9["sets"][tag]["witness_pairs_below_the_floor_barrier"],
            "generation_10_below_floor":
                doc["sets"][tag]["witness_pairs_below_the_floor_barrier"],
        }
    doc["reproduction_control"] = {
        "rows": repro,
        "all_reproduce": bool(all(v["reproduces"] for v in repro.values())),
        "why": ("the two sets generation 9 measured are re-measured here "
                "through the same imported function against the same "
                "artefacts. If they moved, the third set is not comparable to "
                "them and the whole clause is void."),
    }
    print(f"  reproduction of generation 9's two sets: "
          f"{doc['reproduction_control']['all_reproduce']}")

    # -- the decision --------------------------------------------------------
    matched = doc["sets"]["chart_L_d16"]["classification"]["class"]
    reading = {"RIDGE": dec.if_matched_cell_is_ridge,
               "BASIN": dec.if_matched_cell_is_basin,
               "MIXED": dec.if_matched_cell_is_mixed}.get(matched, "undetermined")
    doc["verdict"] = {
        "chart_L_d16_classification": matched,
        "chart_J_d16_classification":
            doc["sets"]["chart_J_d16"]["classification"]["class"],
        "chart_G_d4_classification":
            doc["sets"]["chart_G_d4"]["classification"]["class"],
        "the_split_is_a_property_of": reading,
        "decided_by": ("the classifier and the table registered in "
                       "preregister.json before this phase ran"),
        "rulings_stated_falsifier_is_inverted":
            dec.rulings_stated_falsifier_is_inverted,
        "confound_that_remains": (
            "the barrier walks a STRAIGHT LINE in each chart's own coordinates, "
            "so every depth is an upper bound and the three sets walk lines of "
            "different lengths through different coordinate systems. Chart J "
            "additionally spends one coordinate on a junction ratio, which is "
            "not commensurate with a decade of doping. The null control bounds "
            "how much this can matter for the comparison within a set; nothing "
            "here bounds it across sets."),
    }
    doc["falsifier"] = (
        "SPEC-g10-2 fires if chart L at d=16 does not sit at the floor -- see "
        "ridge_basin_decision for why that is the inverse of the ruling's own "
        "statement of it. Every count above carries its null control, as "
        "SPEC-g9-4 requires.")
    print(f"\n  -> the ridge/basin split is a property of: {reading}")
    return doc


# ===========================================================================
# Phase 3 -- WIT-01, retro-applied to every witness count
# ===========================================================================

def phase_wit01(x_si, root: Path, out: Path, rule: AdmissibilityRule) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  WIT-01  admissibility, retro-applied to every witness count")
    print("=" * 74)
    print(f"  rule hashed before the first verdict: {rule.rule_hash()[:32]}...")
    rep = json.loads((root / G8_REPRODUCE).read_text(encoding="utf-8"))
    cj = json.loads((root / G8_CHART_J).read_text(encoding="utf-8"))
    chartJ = ChartJ(16, x_si)
    sets = [
        ("chart_G_d4", ChartG(4, x_si), rep["chart_G_d4"]),
        ("chart_L_d16", ChartL(16, x_si), rep["chart_L_d16"]),
        ("chart_J_d16", chartJ, cj["native_witness"]),
    ]
    doc: Dict = {"rule": rule.to_dict(), "sets": {},
                 "node_spacing_si": chartJ.node_spacing_si()}
    for tag, chart, res in sets:
        rec = apply_to_witness_set(chart, res["kept_log10"],
                                   res["witness_pair_indices"], rule, tag)
        doc["sets"][tag] = rec
        print(f"  {tag:12s} {rec['n_pairs_offered']:3d} offered -> "
              f"{rec['n_admissible']:3d} admissible   ratio "
              f"{rec['admissibility_ratio']:.3f}   vacuous for this chart: "
              f"{rec['rule_is_vacuous_for_this_chart']}")

    # -- what the rule actually catches, which is not a witness count --------
    ref = json.loads((root / "outputs/g9/junction_refine.json").read_text(
        encoding="utf-8"))
    node_nm = chartJ.node_spacing_si() * 1e9
    rows = []
    for r in ref["records"]:
        sep_nm = float(r["junction_separation_nm"])
        rows.append({
            "pair_index": r["pair_index"],
            "member_indices": r["member_indices"],
            "junction_separation_nm": sep_nm,
            "junction_separation_in_nodes": sep_nm / node_nm,
            "junction_separation_is_resolved": bool(sep_nm >= node_nm),
            "separation_magnitudes_only": r["separation_magnitudes_only"],
            "survives_refinement": bool(r["survives_refinement"]),
            "distance_at_301_default": r["distance_at_301_default"],
            "relative_change": r["relative_change"],
        })
    surv = [r for r in rows if r["survives_refinement"]]
    sepd = [r for r in rows if not r["survives_refinement"]]
    unres = [r for r in rows if not r["junction_separation_is_resolved"]]
    doc["what_the_rule_catches"] = {
        "node_spacing_nm": node_nm,
        "rows": rows,
        "n_pairs_with_an_unresolved_junction_separation": len(unres),
        "unresolved_pairs": [r["pair_index"] for r in unres],
        "junction_separation_nm_surviving_refinement":
            sorted(r["junction_separation_nm"] for r in surv),
        "junction_separation_nm_separated_by_refinement":
            sorted(r["junction_separation_nm"] for r in sepd),
        "reading": (
            "WIT-01 removes NO pair from any count. Every chart-J witness pair "
            "qualifies on a MAGNITUDE coordinate, and magnitude coordinates are "
            "carried to the grid exactly, so the rule is vacuous on the "
            "admissibility question in all three charts. What it does catch is a "
            "reported QUANTITY: one chart-J pair's junction separation is "
            "0.425 nm against a 3.333 nm node, which is a difference the "
            "representation does not carry and which should never have been "
            "quoted as a junction separation at all."),
    }
    print(f"  pairs whose junction separation is below one node: "
          f"{len(unres)} of {len(rows)}  (node = {node_nm:.3f} nm)")

    # -- and the premise it was ordered on, checked --------------------------
    doc["rulings_premise_checked"] = {
        "premise": ("the ruling of 2026-08-26 section 2 states that the "
                    "chart-J pairs that separate under refinement 'are those "
                    "whose junctions were nearly coincident -- 0.4 nm apart, "
                    "rising 195% -- which is sub-grid and was never a witness'"),
        "holds": bool(len(sepd) > 0 and all(
            not r["junction_separation_is_resolved"] for r in sepd)),
        "measured": (
            f"of the {len(sepd)} pairs that separate under refinement, "
            f"{sum(1 for r in sepd if not r['junction_separation_is_resolved'])}"
            f" has a sub-node junction separation. The others separate with "
            f"junctions "
            + ", ".join(f"{r['junction_separation_nm']:.0f} nm"
                        for r in sorted(sepd, key=lambda z:
                                        z['junction_separation_nm'])
                        if r["junction_separation_is_resolved"])
            + " apart, which is 59 to 124 nodes. Pairs that SURVIVE refinement "
              "include junction separations of "
            + ", ".join(f"{r['junction_separation_nm']:.1f} nm"
                        for r in sorted(surv, key=lambda z:
                                        z['junction_separation_nm'])[:2])
            + ". Junction separation does not predict refinement survival."),
        "what_does_predict_it": (
            "headroom below the floor. Sorted by observational distance at "
            "N=301, the 7 pairs that survive are exactly the 7 smallest and the "
            "6 that separate are exactly the 6 largest; the largest surviving "
            "distance is 0.01844 and the smallest separating one is 0.01873, "
            "against a floor of 0.02. Four of the six cross it on a relative "
            "move of 1.2 to 7.9 per cent, which is the same size as moves seen "
            "in pairs that survive (+4.8, +5.6 per cent). Only two show a rise "
            "that is large on its own terms: +195 per cent at a 0.4 nm junction "
            "separation and +29 per cent at 9.0 nm -- both within three nodes, "
            "and those two are the genuine discretisation artefacts."),
    }
    print(f"  ruling's premise (separating pairs are the sub-grid ones) holds: "
          f"{doc['rulings_premise_checked']['holds']}")
    doc["falsifier"] = (
        "WIT-01 fires on a witness count published without its admissibility "
        "ratio. Enforced on the prose by tests/test_witness_admissibility_g10.py, "
        "not by this artefact.")
    return doc


# ===========================================================================
# Phase 4 -- SPEC-g10-3, the validity boundary, STATED not tested
# ===========================================================================

def phase_validity(root: Path, out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 4  SPEC-g10-3  the validity boundary, stated and not tested")
    print("=" * 74)

    # Evidence, not assertion: what is the largest bias any artefact in this
    # line of work was ever evaluated at? Reading files is not extending the
    # range, which the clause forbids.
    scanned, mx, where = 0, float("-inf"), None
    for p in sorted((root / "outputs").rglob("*.json")):
        try:
            blob = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        scanned += 1
        stack = [blob]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                for k, v in o.items():
                    if (k in ("biases", "biases_offered", "biases_used",
                              "bias_points")
                            and isinstance(v, list) and v
                            and all(isinstance(z, (int, float)) for z in v)):
                        if max(v) > mx:
                            mx, where = float(max(v)), f"{p.name}:{k}"
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(o, list):
                stack.extend(z for z in o if isinstance(z, (dict, list)))

    doc = {
        "adopted_observation_set": {"lo_V": 0.15, "hi_V": 0.90, "n": 16,
                                    "source": SPEC_G6_CONVERGENCE},
        "the_claim_this_bounds": (
            "the observation set dominates the other three axes at every "
            "operating point measured -- 0.925 to 1.080 across twelve points, "
            "against x21 to x39 for junction, dimension and interpolant. That "
            "stability is measured over three bias windows, and all three sit "
            "INSIDE [0.15, 0.90] V."),
        "the_three_windows": [{"name": "wide_0.15_0.90", "lo": 0.15, "hi": 0.90},
                              {"name": "low_0.15_0.50", "lo": 0.15, "hi": 0.50},
                              {"name": "high_0.50_0.90", "lo": 0.50, "hi": 0.90}],
        "all_three_inside_the_converged_range": True,
        "the_two_boundaries_do_not_have_the_same_status": {
            "lower_0.15_V": {
                "status": "MEASURED AND REJECTED BELOW",
                "evidence": (SPEC_G6_CONVERGENCE + ": the convergence sweep ran "
                             "19 biases over 0-0.9 V. For V >= 0.15 the "
                             "N=301/601/1201 differences halve under refinement "
                             "(1.47e-3 -> 1.20e-3 at 0.15 V). The non-monotone "
                             "maximum comes entirely from V = 0.10, where "
                             "I ~ 1.3e-3 A/m^2 and the solver's own current "
                             "noise floor competes with discretisation."),
                "reading": ("below 0.15 V the oracle was tested and found "
                            "unconverged. That is a measurement.")},
            "upper_0.90_V": {
                "status": "UNTESTED (PH-15)",
                "evidence": ("the convergence sweep's own upper end is 0.9 V. "
                             "Above it there is no evidence in either "
                             "direction, because nothing was ever solved there "
                             "in this line of work."),
                "reading": ("above 0.90 V the oracle was never tested. That is "
                            "not a measurement, and 'the solver is unvalidated "
                            "there' must never be written as 'the solver fails "
                            "there'.")},
        },
        "largest_bias_any_artefact_was_evaluated_at": {
            "value_V": mx if np.isfinite(mx) else None,
            "found_in": where,
            "json_files_scanned": scanned,
            "method": ("every bias list in every artefact under outputs/, read "
                       "not re-run. Reading files is not extending the range."),
        },
        "PH-15_labels": [
            "the observation-set dominance is bounded to V in [0.15, 0.90]; "
            "outside that range it is UNTESTED, not weaker",
            "rank(window width) 1 -> 4 is measured over widths 0.10-0.75 V "
            "centred at 0.525 V, all inside the converged range; the rank "
            "outside it is UNTESTED",
            "every witness search, every barrier and every spectrum in this "
            "repository uses the same 16 biases over 0.15-0.90 V, so the "
            "boundary is common to the whole claim surface and is not a "
            "property of any one result",
        ],
        "not_tested_here_and_why": (
            "SPEC-g10-3 says state the range, not extend it. Extending it is a "
            "different study: a bias above 0.90 V carries its own convergence "
            "burden -- the discretisation floor would have to be re-measured "
            "there before any identifiability number taken there meant "
            "anything -- and running one without the other would produce a "
            "number with no floor beneath it."),
    }
    print("  adopted range 0.15-0.90 V; lower bound MEASURED, upper bound "
          "UNTESTED (PH-15)")
    print(f"  largest bias in any artefact under outputs/: {mx} V "
          f"({where}), over {scanned} JSON files")
    return doc


# ===========================================================================
# Phase 5 -- the mandatory negative control
# ===========================================================================

def phase_negative_control(sg, x_si, cfg, root: Path, out: Path,
                           meas: LocalisationMeasure,
                           dec: RidgeBasinDecision,
                           rule: AdmissibilityRule) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 5  NEGATIVE CONTROL (mandatory)")
    print("=" * 74)
    from bayespinn_inv.inverse.identifiability import analyse_identifiability

    doc: Dict = {}
    d = 16
    G16 = ChartG(d, x_si)
    pos = G16.anchors

    # -- 1. the localisation measure separates localised from delocalised -----
    Jd = np.zeros((4, d))
    Jd[0, d // 2] = 1.0
    Ju = np.zeros((4, d))
    Ju[0, :] = 1.0 / np.sqrt(d)
    sd = singular_vector_localisation(
        analyse_identifiability(Jd, noise_rel=cfg.noise_rel), pos,
        reference_position=G16.mid, n_vectors=1,
        rank=1)["vectors"][0]["spread_fraction"]
    su = singular_vector_localisation(
        analyse_identifiability(Ju, noise_rel=cfg.noise_rel), pos,
        reference_position=G16.mid, n_vectors=1,
        rank=1)["vectors"][0]["spread_fraction"]
    doc["localisation_measure_separates_planted_extremes"] = {
        "construction": ("a Jacobian whose leading direction is a single anchor, "
                         "against one whose leading direction is uniform"),
        "delta_spread_fraction": sd, "uniform_spread_fraction": su,
        "expected_delta": 1.0 / d, "expected_uniform": 1.0,
        "passes": bool(abs(sd - 1.0 / d) < 1e-9 and abs(su - 1.0) < 1e-9),
    }
    print(f"  1. planted delta {sd:.4f} (expect {1 / d:.4f}) vs uniform "
          f"{su:.4f} (expect 1.0) -> "
          f"{'control passes' if doc['localisation_measure_separates_planted_extremes']['passes'] else 'CONTROL FAILED'}")

    # -- 2. the null: random directions must show no width trend -------------
    # If Haar-random vectors produced a trend against the width axis, the
    # statistic would be measuring the axis and not the physics.
    rng = np.random.default_rng(10)
    ys = []
    for _ in WIDTHS:
        v = rng.normal(size=d)
        w = (v / np.linalg.norm(v)) ** 2
        ys.append(float(1.0 / np.sum(w ** 2)) / d)
    rho_null = spearman(list(WIDTHS), ys)
    doc["random_directions_show_no_width_trend"] = {
        "construction": ("one Haar-random unit vector per width, scored by the "
                         "same statistic; the width axis carries no information "
                         "about them by construction"),
        "spread_fractions": ys, "rho": rho_null,
        "threshold": meas.min_rho,
        "passes": bool(not (rho_null >= meas.min_rho)),
        "note": ("a single draw per width, so this bounds the statistic's "
                 "gullibility rather than estimating a null distribution"),
    }
    print(f"  2. Haar-random directions against the width axis: rho "
          f"{rho_null:+.3f} (< {meas.min_rho}) -> "
          f"{'control passes' if doc['random_directions_show_no_width_trend']['passes'] else 'CONTROL FAILED'}")

    # -- 3. WIT-01 must reject a sub-node junction pair and admit a real one --
    # The planted pair has to be rejected FOR THE STATED REASON, which
    # constrains how it is built. Two devices whose junction coordinates differ
    # by less than min_separation_decades are thrown out by the witness
    # criterion before WIT-01 is consulted, so such a pair tests nothing -- it
    # would report "rejected" whatever the rule did. The construction that does
    # test it uses the logistic's saturated tail: at s ~ 4 the junction sits
    # 0.1 nm from the contact and dx_j/ds has collapsed, so a 0.4-decade move --
    # comfortably qualifying -- shifts the junction by 0.06 nm and leaves it
    # inside the same node interval.
    chartJ = ChartJ(16, x_si)
    mags = np.full(15, 22.0)
    node = chartJ.node_spacing_si()
    planted_a = np.concatenate([[4.0], mags])
    planted_b = np.concatenate([[4.4], mags])
    v_bad = admissibility(chartJ, planted_a, planted_b, rule)
    # and the headline pair, which must be admitted
    cjw = json.loads((root / G8_CHART_J).read_text(
        encoding="utf-8"))["native_witness"]
    keptJ = np.asarray(cjw["kept_log10"], dtype=np.float64)
    ha, hb = cjw["witness_pair_indices"][3]           # the 694 nm / 271 nm pair
    v_good = admissibility(chartJ, keptJ[ha], keptJ[hb], rule)
    doc["wit01_rejects_a_sub_node_pair_and_admits_the_headline_pair"] = {
        "planted": {
            "construction": ("two chart-J devices with identical doping "
                             "magnitudes, junction coordinates 0.4 decades "
                             "apart -- comfortably past the separation "
                             "criterion -- placed in the logistic's saturated "
                             "tail so the junctions themselves stay inside one "
                             "node interval and the two profiles are identical "
                             "bit for bit"),
            "junction_coordinate_separation": float(abs(planted_b[0]
                                                        - planted_a[0])),
            "reaches_the_separation_criterion": bool(
                abs(planted_b[0] - planted_a[0])
                >= rule.min_separation_decades),
            "junction_separation_nm": float(abs(
                chartJ.junction_position(planted_b[0])
                - chartJ.junction_position(planted_a[0])) * 1e9),
            "node_spacing_nm": node * 1e9,
            "same_node_index": bool(
                chartJ.junction_node_index(float(planted_a[0]))
                == chartJ.junction_node_index(float(planted_b[0]))),
            "verdict": v_bad,
            "rejected": bool(not v_bad["admissible"]),
            "rejected_by_WIT_01_rather_than_by_the_separation_criterion": bool(
                "unresolved" in v_bad["reason"])},
        "headline": {
            "construction": ("the chart-J pair whose junctions are 694 nm and "
                             "271 nm apart, which every junction claim in this "
                             "repository rests on"),
            "pair": [int(ha), int(hb)],
            "verdict": v_good, "admitted": bool(v_good["admissible"])},
        "passes": bool(not v_bad["admissible"] and v_good["admissible"]
                       and "unresolved" in v_bad["reason"]),
    }
    r3 = doc["wit01_rejects_a_sub_node_pair_and_admits_the_headline_pair"]
    print(f"  3. WIT-01 on a planted sub-node pair -> "
          f"{'REJECTED' if r3['planted']['rejected'] else 'ADMITTED (control failed)'}"
          f"; on the headline pair -> "
          f"{'ADMITTED' if r3['headline']['admitted'] else 'REJECTED (control failed)'}")

    # -- 4. the ridge/basin classifier must return both answers --------------
    crit = BarrierCriterion()
    biases = list(cfg.biases)
    same = np.tile(np.full(16, 22.0), (2, 1))
    same_rec = _barrier_set(sg, ChartL(16, x_si), cfg, biases, same,
                            [(0, 1)], crit, "planted_identical_pair")
    same_rec["classification"] = classify(same_rec, dec)
    far_a = np.full(16, 21.2)
    far_b = np.full(16, 22.8)
    far_rec = _barrier_set(sg, ChartL(16, x_si), cfg, biases,
                           np.stack([far_a, far_b]), [(0, 1)], crit,
                           "planted_distinguishable_pair")
    far_rec["classification"] = classify(far_rec, dec)
    # A BASIN verdict reached because the oracle refused a point on the path is
    # not a BASIN verdict; it is a missing measurement wearing one. So the
    # control requires the deep path to be certified end to end, not merely to
    # produce no barrier below the floor.
    far_edge = far_rec["witness_pair_barriers"][0]
    doc["classifier_returns_both_answers"] = {
        "identical_pair": {"construction": "one device against itself; the "
                                           "barrier is zero by construction",
                           "barrier": same_rec["witness_depth_median"],
                           "class": same_rec["classification"]["class"]},
        "distinguishable_pair": {"construction": "two chart-L devices 1.6 "
                                                 "decades apart at every anchor",
                                 "barrier": far_rec["witness_depth_median"],
                                 "certified": bool(far_edge.get("certified")),
                                 "class": far_rec["classification"]["class"]},
        "passes": bool(same_rec["classification"]["class"] == "RIDGE"
                       and far_rec["classification"]["class"] == "BASIN"
                       and far_edge.get("certified")
                       and far_edge.get("barrier_depth") is not None),
    }
    r4 = doc["classifier_returns_both_answers"]
    print(f"  4. classifier on an identical pair -> "
          f"{r4['identical_pair']['class']}; on a 1.6-decade pair -> "
          f"{r4['distinguishable_pair']['class']} -> "
          f"{'control passes' if r4['passes'] else 'CONTROL FAILED'}")

    # -- 5. retained from generation 9: the pinned junction ------------------
    G15 = ChartG(15, x_si)
    Jp = ChartJ(16, x_si, junction_scale=0.0)
    th = np.concatenate([[0.0], np.full(15, 22.0)])
    _, Jm_p, _ = cell_spectrum(sg, Jp, th, cfg.biases, cfg)
    _, Jm_g, _ = cell_spectrum(sg, G15, np.full(15, 22.0), cfg.biases, cfg)
    mag_cols = float(np.max(np.abs(Jm_p[:, 1:] - Jm_g))
                     / max(float(np.max(np.abs(Jm_g))), 1e-300))
    pinned_res = float(Jp.coordinate_resolution(th)[0])
    doc["pinned_junction_is_still_not_different"] = {
        "construction": ("retained from generation 9 because every junction "
                         "number in this repository rests on it; extended with "
                         "the WIT-01 resolution, which must be infinite for a "
                         "pinned junction"),
        "pinned_junction_column_norm": float(np.linalg.norm(Jm_p[:, 0])),
        "magnitude_columns_vs_chartG_d15_max_rel": mag_cols,
        "wit01_resolution_of_the_pinned_junction": pinned_res,
        "not_different": bool(np.linalg.norm(Jm_p[:, 0]) == 0.0
                              and mag_cols < 1e-12
                              and not np.isfinite(pinned_res)),
    }
    r5 = doc["pinned_junction_is_still_not_different"]
    print(f"  5. pinned-junction chart J vs chart G d=15 -> "
          f"{'NOT DIFFERENT (control passes)' if r5['not_different'] else 'DIFFERENT (control failed)'}"
          f"; WIT-01 resolution there is {pinned_res}")

    doc["all_controls_pass"] = bool(
        doc["localisation_measure_separates_planted_extremes"]["passes"]
        and doc["random_directions_show_no_width_trend"]["passes"]
        and r3["passes"] and r4["passes"] and r5["not_different"])
    print(f"\n  -> all negative controls behave as required: "
          f"{doc['all_controls_pass']}")
    return doc


# ===========================================================================

ALL_PHASES = ["preregister", "localisation", "ridge_basin", "wit01",
              "validity", "negative_control"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g10")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    ap.add_argument("--barrier-budget-s", type=float, default=1200.0,
                    help="SPEC-g10-2 is dropped WHOLE if the pilot projects "
                         "more than this; it is never part-run")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    cfg = GlobalStudyConfig()
    sg, x_si = build_solver(cfg, args.grid)
    meas, dec, rule = (LocalisationMeasure(), RidgeBasinDecision(),
                       AdmissibilityRule())

    man = RunManifest.create(
        "g10",
        config={**cfg.to_dict(), "grid_n": args.grid, "phases": phases,
                "rel_step": REL_STEP, "min_snr": MIN_SNR,
                "barrier_budget_s": args.barrier_budget_s,
                "localisation_measure": meas.to_dict(),
                "ridge_basin_decision": dec.to_dict(),
                "witness_admissibility_rule": rule.to_dict(),
                "barrier_criterion": BarrierCriterion().to_dict(),
                "g6_artefact": G6_ARTEFACT, "g8_chart_j": G8_CHART_J,
                "g8_reproduce": G8_REPRODUCE, "g9_basins": G9_BASINS},
        seed=cfg.seed,
        notes="G10. Oracle-arbitrated; the surrogate is never called.")

    results: Dict[str, Dict] = {}
    for name in phases:
        path = out / f"{name}.json"
        if name == "preregister":
            r = phase_preregister(root, out)
        elif name == "localisation":
            _check_preregistration(out)
            r = phase_localisation(sg, x_si, cfg, root, out, meas)
        elif name == "ridge_basin":
            _check_preregistration(out)
            r = phase_ridge_basin(sg, x_si, cfg, root, out, dec,
                                  args.barrier_budget_s)
        elif name == "wit01":
            _check_preregistration(out)
            r = phase_wit01(x_si, root, out, rule)
        elif name == "validity":
            r = phase_validity(root, out)
        elif name == "negative_control":
            _check_preregistration(out)
            r = phase_negative_control(sg, x_si, cfg, root, out, meas, dec, rule)
        else:
            raise SystemExit(f"unknown phase {name!r}")
        path.write_text(json.dumps(r, indent=2), encoding="utf-8")
        results[name] = r
        man.add_artifact(name, path)
        print(f"  wrote {path}")

    for k, v in results.items():
        man.add_result(k, v)
    man.write(out)
    print(f"\nwrote {out}/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
