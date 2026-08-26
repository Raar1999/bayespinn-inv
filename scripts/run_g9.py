"""G9: does the ordering hold anywhere but at the one operating point it was measured?

Oracle-arbitrated throughout; the surrogate is never called (``SPEC-g6-5``,
``PH-22``). Every phase writes its own JSON so a later phase failing cannot cost
an earlier phase's measurement.

    PYTHONPATH=src python scripts/run_g9.py --out outputs/g9 --phases \
        preregister,op_points,rank_obs,junction_refine,basins,negative_control

The risk this generation exists to retire
-----------------------------------------
Generation 8 established a four-way ordering of what moves the local
identifiability spectrum -- observation set, junction, dimension, interpolant --
and recorded, as its own highest remaining scientific risk, that **every cell in
it sits at witness pair 0 member a or a projection of it**. One device. One bias
window. The ordering is a claim about semiconductors only if it survives
somewhere else.

What each phase answers
-----------------------
``preregister``
    ``AH-14``. Writes the selection rule, the perturbation sets and the ordering
    statistic to disk **with their hashes, before anything is drawn or solved**.
    Every later phase re-reads that file and refuses to run if the hash it
    recomputes does not match. A rule chosen after seeing the spectra is
    ``AH-04`` under another name, and the only defence is a timestamped hash.
``op_points``
    ``SPEC-g9-1``. The full four-way ordering at nine further operating points --
    three devices spanning the doping prior, three bias windows spanning the
    observation range -- plus the generation-8 operating point re-measured
    through this same code as a reproduction control.
``rank_obs``
    ``SPEC-g9-2``. ``rank(observation set)``: rank against bias-window width and
    against spacing, at fixed device, as curves, each cell carrying its own
    ``rank(cutoff)`` curve.
``junction_refine``
    ``SPEC-g9-3``. The chart-J witness pairs through the generation-6 refinement
    falsifier the doping witnesses already survived. Does the observational
    distance rise or fall under ``N = 301 -> 601 -> 1201`` and
    ``tol_carrier = 1e-12``?
``basins``
    ``SPEC-g9-4``, pilot-gated. Cluster witness members by **barrier depth**
    rather than by profile distance, criterion hashed first, with the null
    control the clause makes mandatory. Dropped whole if the pilot says it does
    not fit; never part-run.
``negative_control``
    Mandatory. The clause names the case: *an ordering measured at one operating
    point, stated unqualified*. The battery must reject it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bayespinn_inv.inverse.charts import (
    ChartG,
    ChartJ,
    ChartL,
    chart_forward_jacobian,
    project_into_chart,
)
from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
)
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    rank_cutoff_record,
)
from bayespinn_inv.inverse.modes import barrier_depth
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest

G6_ARTEFACT = "outputs/global_identifiability_g6/global_identifiability.json"
G8_CHART_J = "outputs/g8/chart_j.json"
G8_REPRODUCE = "outputs/g8/reproduce.json"

#: Finite-difference step and SNR gate, inherited unchanged from
#: ``scripts/run_g8.py::cell_spectrum``. "Same metrics, same normalisation" is a
#: clause of ``SPEC-g9-1`` and it starts here: a different step would make every
#: number below incomparable with the ones it is meant to replicate.
REL_STEP = 0.05
MIN_SNR = 1e4

#: Leading singular values compared, inherited from generation 7's chart
#: comparison and generation 8's discriminators.
SPECTRAL_K = 5


# ===========================================================================
# Pre-registration -- written and hashed BEFORE anything is drawn
# ===========================================================================

@dataclass(frozen=True)
class OperatingPointRule:
    """How the further operating points are chosen, fixed before choosing them.

    ``SPEC-g9-1`` requires the operating points to be *genuinely distinct* from
    the generation-8 one and to *span the doping and bias ranges*, and it
    requires the method to be stated before it is applied. Both halves are here,
    and :meth:`rule_hash` is written to disk in the ``preregister`` phase so
    that a rule edited after seeing a spectrum fails the check rather than
    passing quietly.

    The device axis
        ``n_candidates`` draws from the study's own log-uniform doping prior in
        chart G at ``d = d_select``, under a seed that is **not** the study seed,
        so these are new devices rather than the generation-6 draws re-served.
        Candidates are ranked by ``rank_statistic`` and the draws nearest the
        stated ``percentiles`` are taken. That spans the prior by construction
        rather than by inspection.

    The bias axis
        ``bias_windows`` are three windows over the range the oracle's
        discretisation error was measured to converge on: the published one, its
        lower part and its upper part. Every operating point is a
        ``(device, window)`` pair, because a rank is a property of that pair and
        never of the device alone -- generation 8's own conclusion.

    Admission
        A candidate is admitted only if the oracle certifies every bias in the
        widest window (``PH-19``: refusals are counted, not skipped) and only if
        it is at least ``min_distance_from_g8_decades`` from the generation-8
        operating point in profile space. Otherwise the next candidate in rank
        order is taken and the substitution is recorded.
    """

    n_candidates: int = 400
    seed: int = 9
    d_select: int = 4
    rank_statistic: str = "mean_log10_magnitude"
    percentiles: Tuple[float, ...] = (10.0, 50.0, 90.0)
    prior_lo_si: float = 1e21
    prior_hi_si: float = 1e23
    min_distance_from_g8_decades: float = 0.3
    require_all_biases_certified: bool = True
    substitution: str = "next candidate in ascending rank order; each recorded"
    bias_windows: Tuple[Tuple[str, float, float], ...] = (
        ("wide_0.15_0.90", 0.15, 0.90),
        ("low_0.15_0.50", 0.15, 0.50),
        ("high_0.50_0.90", 0.50, 0.90),
    )
    n_biases: int = 16

    def rule_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["rule_hash"] = self.rule_hash()
        return out


@dataclass(frozen=True)
class OrderingStatistic:
    """What "the ordering" *is*, written down before it is measured.

    Generation 8 reported four families of movement and the state file
    summarised them as ``observation set > junction > dimension > interpolant``.
    That summary has no statistic attached, and the two obvious ones disagree
    even on generation 8's own numbers -- by the largest movement each axis
    produces the junction leads (219% against 98.4%), by the mildest
    perturbation each axis admits the observation set leads (19.8% against
    9.1%). An ordering that depends on an unstated choice is not a result.

    So both are computed at every operating point, and the ordering is called
    **stable** at a point only when the two agree there. ``AH-14``: this is
    fixed here, before the first spectrum.
    """

    metric: str = "max relative movement of the leading singular values"
    k: int = SPECTRAL_K
    statistics: Tuple[str, ...] = ("by_max", "by_mildest")
    stable_requires: str = "both statistics give the same order at that point"
    axes: Tuple[str, ...] = ("observation_set", "junction", "dimension",
                             "interpolant")
    #: Which perturbations belong to which axis. Fixed here so that an axis
    #: cannot be strengthened after the fact by admitting one more variant.
    axis_members: Dict[str, Tuple[str, ...]] = field(default_factory=lambda: {
        "interpolant": ("G_to_L_at_d16",),
        "dimension": ("G_d15_vs_G_d16",),
        "junction": ("xj_0.35", "xj_0.65"),
        "observation_set": ("geometric_same_window", "middle_half",
                            "upper_half", "stride2", "lower_half_count"),
    })
    #: Measured and reported, deliberately NOT in the ordering: a d=4 against
    #: d=16 comparison spans 12 coordinates and would let the dimension axis win
    #: by taking a bigger step than the other three are allowed.
    reported_outside_the_ordering: Tuple[str, ...] = ("G_d4_vs_G_d16",)

    def statistic_hash(self) -> str:
        payload = {"metric": self.metric, "k": self.k,
                   "statistics": list(self.statistics),
                   "stable_requires": self.stable_requires,
                   "axes": list(self.axes),
                   "axis_members": {k: list(v)
                                    for k, v in sorted(self.axis_members.items())},
                   "reported_outside_the_ordering":
                       list(self.reported_outside_the_ordering)}
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["statistic_hash"] = self.statistic_hash()
        return out


@dataclass(frozen=True)
class BarrierCriterion:
    """``SPEC-g9-4``: how a barrier becomes a basin, hashed before clustering.

    Generation 8 clustered witness members by **profile distance** and said in
    the same breath that the proxy was not the landscape: within-cluster pairs
    were still separated by barriers hundreds of log-units deep. This replaces
    the proxy with the thing itself -- two members are in one basin when the
    profile likelihood between them does not fall by more than ``threshold``
    log-units -- and states the reference the threshold is measured against.

    ``floor_reference`` is the barrier a pair sitting exactly on the
    distinguishability floor would produce: with independent relative Gaussian
    noise at ``noise_rel`` over ``B`` certified biases, a curve differing by
    exactly one noise unit at every bias costs ``0.5 * B`` log-units. Anything
    shallower than that is not resolvable by this instrument, which is the only
    non-arbitrary threshold available.
    """

    metric: str = "profile likelihood barrier depth, straight line in chart coordinates"
    n_points: int = 11
    noise_rel: float = 2.0e-2
    floor_reference: str = "0.5 * B_certified log-units, the cost of a curve one noise unit away at every bias"
    threshold_multiples_of_floor: Tuple[float, ...] = (
        0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 1000.0)
    null_control: str = (
        "the same criterion over the same number of ordinary prior draws that "
        "form no witness pair, taken in draw order")

    def criterion_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["criterion_hash"] = self.criterion_hash()
        return out


def phase_preregister(root: Path, out: Path) -> Dict:
    print("=" * 74)
    print("PHASE 0  PRE-REGISTRATION (AH-14): the rules, before the numbers")
    print("=" * 74)
    rule, stat, crit = OperatingPointRule(), OrderingStatistic(), BarrierCriterion()
    doc = {
        "written_before": ("any draw, any solve, any spectrum. Every later "
                           "phase recomputes these hashes and refuses to run "
                           "on a mismatch."),
        "operating_point_rule": rule.to_dict(),
        "ordering_statistic": stat.to_dict(),
        "barrier_criterion": crit.to_dict(),
        "generation_8_operating_point": (
            "witness pair 0 member a of " + G6_ARTEFACT + ", chart G d=4, "
            "collocated or projected into each chart; bias window "
            "0.15-0.90 V, 16 linear points. Re-measured here as a "
            "reproduction control, and excluded from the count of *further* "
            "operating points."),
        "what_would_falsify_g9_1": (
            "the ordering changes at any operating point. Pre-registered as "
            "reportable either way (AH-04, AH-13): a flip converts the "
            "headline to 'the ordering is itself operating-point dependent', "
            "which is weaker and still publishable."),
    }
    for k, h in (("operating_point_rule", rule.rule_hash()),
                 ("ordering_statistic", stat.statistic_hash()),
                 ("barrier_criterion", crit.criterion_hash())):
        print(f"  {k:24s} {h[:32]}...")
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
            ("operating_point_rule", OperatingPointRule(), "rule_hash"),
            ("ordering_statistic", OrderingStatistic(), "statistic_hash"),
            ("barrier_criterion", BarrierCriterion(), "criterion_hash")):
        on_disk = doc[key][attr]
        now = getattr(obj, attr)()
        if on_disk != now:
            raise SystemExit(
                f"{key} has changed since it was registered.\n"
                f"  registered: {on_disk}\n  now:        {now}\n"
                "AH-14 forbids continuing. Either restore the rule or start a "
                "new pre-registration and say in the result document that the "
                "rule moved.")
    return doc


# ===========================================================================
# Shared machinery -- identical to generation 8's, deliberately
# ===========================================================================

def build_solver(cfg: GlobalStudyConfig, grid_n: int,
                 sg_cfg: Optional[SGConfig] = None):
    scaling = Scaling.for_material(SILICON, T=300.0)
    length = cfg.domain_si[1] - cfg.domain_si[0]
    sg = ScharfetterGummel1D(
        Grid1D.uniform(float(scaling.x_to_scaled(np.float64(length))), grid_n),
        scaling, SILICON, sg_cfg or SGConfig())
    return sg, scaling.x_to_si(np.asarray(sg.grid.x))


def iv(sg, doping, biases):
    """Terminal currents plus whether the oracle certified every point."""
    prev, cur, trust, conv = None, [], [], []
    for v in biases:
        st = sg.solve(doping, float(v), initial_state=prev)
        prev = st
        cur.append(st.terminal_current)
        trust.append(bool(st.current_is_trustworthy()))
        conv.append(bool(st.converged))
    return np.asarray(cur), np.asarray(trust), np.asarray(conv)


def obs_dist(ia, ib, mask=None) -> float:
    """``witness_search``'s own metric: max over biases of |dI| / max(|Ia|,|Ib|)."""
    a, b = np.asarray(ia), np.asarray(ib)
    if mask is not None:
        a, b = a[mask], b[mask]
    if a.size == 0:
        return float("nan")
    denom = np.maximum(np.abs(a), np.abs(b))
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nanmax(np.abs(a - b) / denom))


def spectral_movement(sa: Sequence[float], sb: Sequence[float],
                      k: int = SPECTRAL_K) -> Dict[str, float]:
    a = np.asarray(sa, dtype=np.float64)[:k]
    b = np.asarray(sb, dtype=np.float64)[:k]
    m = min(a.size, b.size)
    if m == 0:
        return {"max_rel": float("nan"), "mean_rel": float("nan"), "k": 0}
    rel = np.abs(b[:m] - a[:m]) / np.maximum(np.abs(a[:m]), 1e-300)
    return {"max_rel": float(np.max(rel)), "mean_rel": float(np.mean(rel)),
            "k": int(m)}


def cell_spectrum(sg, chart, theta, biases, cfg):
    t0 = time.perf_counter()
    J, I_ref, kept, eta = chart_forward_jacobian(
        sg, chart, theta, biases, rel_step=REL_STEP, min_snr=MIN_SNR)
    rep = analyse_identifiability(J, noise_rel=cfg.noise_rel, jacobian_noise=eta)
    rec = rank_cutoff_record(rep, cfg.noise_rel)
    rec.update({
        "chart": chart.name,
        "chart_label": chart.label(),
        "d": chart.d,
        "n_magnitude_coordinates": chart.n_mag,
        "theta": [float(t) for t in np.asarray(theta, dtype=np.float64)],
        "biases_offered": [float(b) for b in biases],
        "biases_used": [float(biases[i]) for i in kept],
        "rows_used": len(kept),
        "rel_step_decades": REL_STEP,
        "min_snr": MIN_SNR,
        "wall_clock_s": time.perf_counter() - t0,
    })
    return rec, J, rep


def window_biases(lo: float, hi: float, n: int) -> np.ndarray:
    return np.round(np.linspace(lo, hi, n), 4)


def obs_variants(lo: float, hi: float, n: int) -> Dict[str, Tuple[np.ndarray, bool]]:
    """The observation-set perturbations, built the same way at every window.

    ``B_matched`` says whether the variant offers the same number of bias points
    as its baseline. Dropping points changes the number of Jacobian rows, and a
    singular value of a taller matrix is larger for that reason alone, so the
    unmatched variants are reported with the confound named rather than dropped
    -- generation 8's treatment, unchanged.
    """
    base = window_biases(lo, hi, n)
    w = hi - lo
    return {
        "geometric_same_window": (np.round(np.geomspace(lo, hi, n), 4), True),
        "middle_half": (window_biases(lo + 0.25 * w, hi - 0.25 * w, n), True),
        "upper_half": (window_biases(lo + 0.5 * w, hi, n), True),
        "stride2": (base[::2], False),
        "lower_half_count": (base[: n // 2], False),
    }


# ===========================================================================
# Phase 1 -- SPEC-g9-1, the ordering at further operating points
# ===========================================================================

def _select_devices(sg, x_si, cfg, rule: OperatingPointRule,
                    g8_profile: np.ndarray) -> Dict:
    """Apply the pre-registered rule. Nothing here looks at a spectrum."""
    rng = np.random.default_rng(rule.seed)
    cand = rng.uniform(np.log10(rule.prior_lo_si), np.log10(rule.prior_hi_si),
                       size=(rule.n_candidates, rule.d_select))
    stat = cand.mean(axis=1)
    order = np.argsort(stat)                      # ascending, the stated order
    G = ChartG(rule.d_select, x_si)
    widest = window_biases(rule.bias_windows[0][1], rule.bias_windows[0][2],
                           rule.n_biases)

    def profile_distance(th) -> float:
        with np.errstate(divide="ignore", invalid="ignore"):
            dec = np.abs(np.log10(np.abs(G.reconstruct(th)))
                         - np.log10(np.abs(g8_profile)))
        fin = np.isfinite(dec)
        return float(np.max(dec[fin])) if fin.any() else float("inf")

    chosen: List[Dict] = []
    rejected: List[Dict] = []
    for pct in rule.percentiles:
        start = round((pct / 100.0) * (rule.n_candidates - 1))
        for step in range(rule.n_candidates):
            k = start + step
            if k >= rule.n_candidates:
                break
            idx = int(order[k])
            if any(c["candidate_index"] == idx for c in chosen):
                continue
            th = cand[idx]
            dist = profile_distance(th)
            if dist < rule.min_distance_from_g8_decades:
                rejected.append({"percentile": pct, "candidate_index": idx,
                                 "reason": "within "
                                 f"{rule.min_distance_from_g8_decades} decades "
                                 "of the generation-8 operating point",
                                 "profile_distance_from_g8_decades": dist})
                continue
            _, trust, conv = iv(sg, G.charted(th), widest)
            if rule.require_all_biases_certified and not (
                    bool(np.all(trust)) and bool(np.all(conv))):
                rejected.append({"percentile": pct, "candidate_index": idx,
                                 "reason": "oracle did not certify every bias "
                                 "in the widest window",
                                 "n_untrustworthy": int(np.sum(~trust)),
                                 "n_unconverged": int(np.sum(~conv))})
                continue
            chosen.append({
                "name": f"device_p{int(pct)}",
                "percentile": pct,
                "candidate_index": idx,
                "rank_in_candidates": k,
                "substitutions_before_admission": step,
                "mean_log10_magnitude": float(stat[idx]),
                "theta_chartG_d4": [float(t) for t in th],
                "profile_distance_from_g8_decades": dist,
            })
            break
    return {"chosen": chosen, "rejected": rejected,
            "candidate_statistic_percentiles": {
                str(p): float(np.percentile(stat, p))
                for p in (0, 10, 25, 50, 75, 90, 100)},
            "note": ("ranking, admission and substitution all ran before any "
                     "Jacobian was formed; nothing here can see a spectrum")}


def _one_operating_point(sg, x_si, cfg, theta4: np.ndarray, window,
                         stat: OrderingStatistic) -> Dict:
    """The full four-way contrast at one (device, bias window)."""
    wname, lo, hi = window
    n = 16
    base_b = window_biases(lo, hi, n)
    G4 = ChartG(4, x_si)
    G15, G16 = ChartG(15, x_si), ChartG(16, x_si)
    L16 = ChartL(16, x_si)
    prof = G4.reconstruct(theta4)
    m15 = np.interp(G15.anchors, G4.anchors, theta4)
    m16 = np.interp(G16.anchors, G4.anchors, theta4)
    thL, projdiag = project_into_chart(L16, prof, method="log10",
                                       source_chart=G4, source_log10=theta4)

    cells: Dict[str, Dict] = {}
    movements: Dict[str, Dict] = {}

    # -- the reference cell, and the two magnitude-matched references ---------
    cells["G_d16"], JG16, _ = cell_spectrum(sg, G16, m16, base_b, cfg)
    cells["G_d15"], JG15, _ = cell_spectrum(sg, G15, m15, base_b, cfg)
    cells["G_d4"], _, _ = cell_spectrum(sg, G4, theta4, base_b, cfg)
    cells["L_d16"], _, _ = cell_spectrum(sg, L16, thL, base_b, cfg)
    # REP-01: the projection that produced the chart-L cell travels with it.
    cells["L_d16"]["operating_point_method"] = {
        "method": projdiag.get("method", "log10"),
        "note": ("chart L cannot hold the chart-G device exactly; this is the "
                 "best admissible projection, and the residual it leaves is "
                 "reported as profile_distance_from_operating_point_decades"),
    }
    with np.errstate(divide="ignore", invalid="ignore"):
        dec = np.abs(np.log10(np.abs(L16.reconstruct(thL)))
                     - np.log10(np.abs(prof)))
    fin = np.isfinite(dec)
    cells["L_d16"]["profile_distance_from_operating_point_decades"] = (
        float(np.max(dec[fin])) if fin.any() else None)
    cells["L_d16"]["nodes_excluded_nonfinite"] = int(np.sum(~fin))

    # -- interpolant and dimension -------------------------------------------
    movements["G_to_L_at_d16"] = spectral_movement(
        cells["G_d16"]["singular_values"], cells["L_d16"]["singular_values"])
    movements["G_d15_vs_G_d16"] = spectral_movement(
        cells["G_d15"]["singular_values"], cells["G_d16"]["singular_values"])
    movements["G_d4_vs_G_d16"] = spectral_movement(
        cells["G_d4"]["singular_values"], cells["G_d16"]["singular_values"])

    # -- junction, on the unit-homogeneous magnitude block --------------------
    # Chart J's Jacobian has one column in decades of junction ratio and the
    # rest in decades of doping; the full spectrum of a mixed-unit matrix is not
    # units-free (g8 measured it moving by a factor of ten across defensible
    # scalings). The magnitude sub-block is, and it is what the ordering uses.
    mag_ref = [float(v) for v in np.linalg.svd(JG15, compute_uv=False)]
    J16 = ChartJ(16, x_si)
    cells["J_d16_s0"], JJ0, _ = cell_spectrum(
        sg, J16, np.concatenate([[0.0], m15]), base_b, cfg)
    cells["J_d16_s0"]["magnitude_block_singular_values"] = [
        float(v) for v in np.linalg.svd(JJ0[:, 1:], compute_uv=False)]
    cells["J_d16_s0"]["magnitude_columns_identical_to_G_d15"] = bool(
        np.array_equal(JJ0[:, 1:], JG15))
    cells["J_d16_s0"]["containment_note"] = (
        "chart J at s=0 is chart G at d-1, bit for bit: chart J CONTAINS chart "
        "G rather than sitting beside it, so every junction movement below is "
        "measured within one family")
    cells["J_d16_s0"]["junction_scale"] = J16.junction_scale
    for frac in (0.35, 0.65):
        s = float(np.log10(frac / (1.0 - frac)))
        key = f"xj_{frac:g}"
        rec, JJ, _ = cell_spectrum(sg, J16, np.concatenate([[s], m15]),
                                   base_b, cfg)
        rec["magnitude_block_singular_values"] = [
            float(v) for v in np.linalg.svd(JJ[:, 1:], compute_uv=False)]
        rec["junction_scale"] = J16.junction_scale
        rec["junction_s"] = s
        rec["junction_x_si"] = J16.junction_position(s)
        rec["junction_column_norm"] = float(np.linalg.norm(JJ[:, 0]))
        cells[f"J_d16_{key}"] = rec
        movements[key] = spectral_movement(
            mag_ref, rec["magnitude_block_singular_values"])

    # -- observation set, perturbed around THIS window's own baseline ---------
    obs_cells: Dict[str, Dict] = {}
    for vname, (b, matched) in obs_variants(lo, hi, n).items():
        try:
            rec, _, _ = cell_spectrum(sg, G16, m16, b, cfg)
        except ValueError as exc:
            obs_cells[vname] = {"error": str(exc), "B_matched": bool(matched)}
            movements[vname] = {"max_rel": float("nan"), "mean_rel": float("nan"),
                                "k": 0, "error": str(exc)}
            continue
        rec["B_matched_to_baseline"] = bool(matched)
        mv = spectral_movement(cells["G_d16"]["singular_values"],
                               rec["singular_values"])
        nb, n0 = np.sqrt(rec["rows_used"]), np.sqrt(cells["G_d16"]["rows_used"])
        rec["movement_vs_baseline"] = mv
        rec["movement_vs_baseline_sqrtB_normalised"] = spectral_movement(
            np.asarray(cells["G_d16"]["singular_values"]) / n0,
            np.asarray(rec["singular_values"]) / nb)
        obs_cells[vname] = rec
        movements[vname] = mv

    # -- the observable-space distance between the two compared chart cells ---
    # The denominator the chart-invariance result needs. Generation 8 reported
    # that the two cells sit 1.24 decades apart in PROFILE space and that their
    # spectra agree to 2.8%, and left the reader to supply the missing middle
    # term. This is that term, measured on exactly the two cells whose spectra
    # are compared, over exactly the window they are compared in.
    Ig, tg, cg = iv(sg, G16.charted(m16), base_b)
    Il, tl, cl = iv(sg, L16.charted(thL), base_b)
    both = (tg & cg & tl & cl)
    chart_obs = {
        "max_rel_current_difference": obs_dist(Ig, Il, both),
        "mean_rel_current_difference": float(np.mean(
            np.abs(Ig[both] - Il[both])
            / np.maximum(np.abs(Ig[both]), np.abs(Il[both]))))
        if both.any() else float("nan"),
        "n_biases_both_certified": int(np.sum(both)),
        "n_biases_offered": int(base_b.size),
        "profile_distance_decades":
            cells["L_d16"]["profile_distance_from_operating_point_decades"],
        "projection_method": projdiag.get("method", "log10"),
        "spectral_movement_max_rel": movements["G_to_L_at_d16"]["max_rel"],
        "reading": ("how far apart the two charts put the device in the "
                    "OBSERVABLE, over the same window their spectra are "
                    "compared in. Read beside profile_distance_decades: the "
                    "charts can be far apart in profile space and close in "
                    "current, and it is the current the Jacobian differentiates"),
    }

    # -- the ordering ---------------------------------------------------------
    per_axis: Dict[str, Dict] = {}
    for axis, members in stat.axis_members.items():
        vals = {m: movements[m]["max_rel"] for m in members
                if m in movements and np.isfinite(movements[m]["max_rel"])}
        per_axis[axis] = {
            "members": list(members),
            "values": vals,
            "by_max": max(vals.values()) if vals else float("nan"),
            "by_mildest": min(vals.values()) if vals else float("nan"),
        }
    orders: Dict[str, List[str]] = {}
    for statname in stat.statistics:
        scored = [(float(per_axis[a][statname]), a) for a in stat.axes
                  if np.isfinite(per_axis[a][statname])]
        orders[statname] = [a for _, a in sorted(scored, reverse=True)]
    stable = len({tuple(v) for v in orders.values()}) == 1

    return {
        "bias_window": {"name": wname, "lo": lo, "hi": hi,
                        "n_offered": n,
                        "baseline_biases": [float(b) for b in base_b]},
        "cells": cells,
        "observation_set_cells": obs_cells,
        "movements": movements,
        "chart_distance_in_the_observable": chart_obs,
        "per_axis": per_axis,
        "order": orders,
        "order_is_stable_under_both_statistics": bool(stable),
    }


def phase_op_points(sg, x_si, cfg, root: Path, out: Path, pre: Dict) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  SPEC-g9-1  the ordering at further operating points")
    print("=" * 74)
    rule, stat = OperatingPointRule(), OrderingStatistic()
    ws = json.loads((root / G6_ARTEFACT).read_text(
        encoding="utf-8"))["witness_search"]
    a4 = np.array(ws["witnesses"][0]["profile_a_log10"], dtype=np.float64)
    g8_profile = ChartG(4, x_si).reconstruct(a4)

    sel = _select_devices(sg, x_si, cfg, rule, g8_profile)
    print(f"  selection rule {rule.rule_hash()[:16]}...  "
          f"{len(sel['chosen'])} devices admitted, "
          f"{len(sel['rejected'])} candidates rejected")
    for c in sel["chosen"]:
        print(f"    {c['name']:12s} p{c['percentile']:<5g} "
              f"mean log10|C| = {c['mean_log10_magnitude']:.3f}  "
              f"{c['profile_distance_from_g8_decades']:.3f} decades from the "
              f"g8 operating point")

    results: Dict[str, Dict] = {}
    devices = [{"name": "g8_control", "theta_chartG_d4": [float(v) for v in a4],
                "is_reproduction_control": True,
                "note": ("the generation-8 operating point, re-measured through "
                         "this generation's code. Not one of the *further* "
                         "points; it is the ruler check")}] + sel["chosen"]

    for dev in devices:
        th = np.asarray(dev["theta_chartG_d4"], dtype=np.float64)
        for window in rule.bias_windows:
            key = f"{dev['name']}__{window[0]}"
            t0 = time.perf_counter()
            try:
                rec = _one_operating_point(sg, x_si, cfg, th, window, stat)
            except ValueError as exc:
                # PH-19: a cell the oracle cannot certify is COUNTED, not
                # dropped. A low-doped device in a narrow high-bias window can
                # leave no row above the SNR gate, and the honest record of
                # that is the operating point appearing here with its reason,
                # excluded from the ordering tallies rather than from the file.
                results[key] = {"device": dev, "error": str(exc),
                                "bias_window": {"name": window[0],
                                                "lo": window[1],
                                                "hi": window[2]},
                                "wall_clock_s": time.perf_counter() - t0}
                print(f"  {key:34s} NO SPECTRUM: {str(exc)[:70]}")
                continue
            rec["device"] = dev
            rec["wall_clock_s"] = time.perf_counter() - t0
            results[key] = rec
            pa = rec["per_axis"]
            print(f"  {key:34s} "
                  f"obs {pa['observation_set']['by_max']:7.3f} "
                  f"jun {pa['junction']['by_max']:7.3f} "
                  f"dim {pa['dimension']['by_max']:7.3f} "
                  f"int {pa['interpolant']['by_max']:7.3f}  "
                  f"| by_max {'>'.join(a[:3] for a in rec['order']['by_max'])}"
                  f"  stable={rec['order_is_stable_under_both_statistics']}"
                  f"  ({rec['wall_clock_s']:.0f}s)")

    measured = {k: v for k, v in results.items() if "error" not in v}
    unmeasurable = {k: v["error"] for k, v in results.items() if "error" in v}
    further = {k: v for k, v in measured.items()
               if not v["device"].get("is_reproduction_control")}
    ctrl = {k: v for k, v in measured.items()
            if v["device"].get("is_reproduction_control")}
    if "g8_control__wide_0.15_0.90" not in ctrl:
        raise SystemExit(
            "the reproduction control did not produce a spectrum, so nothing "
            "below can be compared with generation 8; refusing to report")

    by_max_orders = {k: tuple(v["order"]["by_max"]) for k, v in further.items()}
    by_mild_orders = {k: tuple(v["order"]["by_mildest"])
                      for k, v in further.items()}
    g8_by_max = tuple(ctrl["g8_control__wide_0.15_0.90"]["order"]["by_max"])
    g8_by_mild = tuple(
        ctrl["g8_control__wide_0.15_0.90"]["order"]["by_mildest"])

    def _tally(d):
        out_: Dict[str, int] = {}
        for v in d.values():
            out_[" > ".join(v)] = out_.get(" > ".join(v), 0) + 1
        return dict(sorted(out_.items(), key=lambda kv: -kv[1]))

    verdict = {
        "n_further_operating_points": len(further),
        "n_operating_points_without_a_spectrum": len(unmeasurable),
        "operating_points_without_a_spectrum": unmeasurable,
        "n_devices": len({v["device"]["name"] for v in further.values()}),
        "n_bias_windows": len(rule.bias_windows),
        "generation_8_point_by_max": list(g8_by_max),
        "generation_8_point_by_mildest": list(g8_by_mild),
        "orders_by_max": _tally(by_max_orders),
        "orders_by_mildest": _tally(by_mild_orders),
        "same_as_g8_by_max": sum(1 for v in by_max_orders.values()
                                 if v == g8_by_max),
        "same_as_g8_by_mildest": sum(1 for v in by_mild_orders.values()
                                     if v == g8_by_mild),
        "n_points_where_the_two_statistics_agree": sum(
            1 for v in further.values()
            if v["order_is_stable_under_both_statistics"]),
        "falsifier": ("SPEC-g9-1 fires if the ordering changes at ANY further "
                      "operating point. Both outcomes are pre-registered as "
                      "reportable (AH-04, AH-13)."),
        "falsifier_fires_by_max": bool(
            any(v != g8_by_max for v in by_max_orders.values())),
        "falsifier_fires_by_mildest": bool(
            any(v != g8_by_mild for v in by_mild_orders.values())),
    }
    print()
    print(f"  generation-8 point, by_max     : {' > '.join(g8_by_max)}")
    print(f"  generation-8 point, by_mildest : {' > '.join(g8_by_mild)}")
    for k, v in verdict["orders_by_max"].items():
        print(f"  by_max     {v:2d}/{len(further)}  {k}")
    for k, v in verdict["orders_by_mildest"].items():
        print(f"  by_mildest {v:2d}/{len(further)}  {k}")
    print(f"  SPEC-g9-1 falsifier fires: by_max="
          f"{verdict['falsifier_fires_by_max']}  "
          f"by_mildest={verdict['falsifier_fires_by_mildest']}")

    return {"preregistration_hash": pre["operating_point_rule"]["rule_hash"],
            "selection": sel, "operating_points": results, "verdict": verdict}


# ===========================================================================
# Phase 2 -- SPEC-g9-2, rank against the observation set, as a curve
# ===========================================================================

WIDTH_CENTRE = 0.525
WIDTHS = (0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75)
ALPHAS = (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)


def _spacing(lo: float, hi: float, n: int, alpha: float) -> np.ndarray:
    """Linear at ``alpha=0``, geometric at ``alpha=1``, continuous between.

    Spacing was a two-valued knob in generation 8 -- linear or geometric -- and
    a two-valued knob cannot produce a curve. This is the one-parameter family
    joining them, so ``rank(spacing)`` is a curve in the same sense
    ``rank(cutoff)`` is.
    """
    lin = np.linspace(lo, hi, n)
    geo = np.geomspace(lo, hi, n)
    return np.round((1.0 - alpha) * lin + alpha * geo, 4)


def phase_rank_obs(sg, x_si, cfg, root: Path, out: Path, devices: Dict) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  SPEC-g9-2  rank(observation set): width and spacing curves")
    print("=" * 74)
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    out_doc: Dict = {"devices": {}, "axes": {
        "width": {"centre_V": WIDTH_CENTRE, "widths_V": list(WIDTHS),
                  "n_biases": 16, "spacing": "linear",
                  "why": ("the window is widened about a fixed centre so that "
                          "width is the only thing that moves; centring it "
                          "elsewhere would confound width with which part of "
                          "the I-V is being looked at")},
        "spacing": {"window_V": [0.15, 0.90], "alphas": list(ALPHAS),
                    "n_biases": 16,
                    "why": ("alpha interpolates linear (0) to geometric (1) "
                            "spacing over one fixed window, so the endpoints "
                            "and the count never move and only the interior "
                            "placement does")}}}

    for dname, theta4 in devices.items():
        th4 = np.asarray(theta4, dtype=np.float64)
        m16 = np.interp(G16.anchors, G4.anchors, th4)
        rec: Dict = {"theta_chartG_d4": [float(v) for v in th4],
                     "width_curve": [], "spacing_curve": []}
        for w in WIDTHS:
            lo, hi = WIDTH_CENTRE - w / 2.0, WIDTH_CENTRE + w / 2.0
            b = window_biases(lo, hi, 16)
            try:
                cell, _, _ = cell_spectrum(sg, G16, m16, b, cfg)
            except ValueError as exc:
                rec["width_curve"].append({"width_V": w, "error": str(exc)})
                continue
            rec["width_curve"].append({
                "width_V": float(w), "lo_V": float(lo), "hi_V": float(hi),
                "rows_used": cell["rows_used"],
                "rank_at_operational_cutoff": cell["rank_at_operational_cutoff"],
                "bare_integer_rank_justified": cell["bare_integer_rank_justified"],
                "largest_gap_ratio": cell["largest_gap_ratio"],
                "operational_cutoff_falls_in_largest_gap":
                    cell["operational_cutoff_falls_in_largest_gap"],
                "rank_cutoff_curve": cell["rank_curve"],
                "singular_values": cell["singular_values"],
            })
        for a in ALPHAS:
            b = _spacing(0.15, 0.90, 16, a)
            try:
                cell, _, _ = cell_spectrum(sg, G16, m16, b, cfg)
            except ValueError as exc:
                rec["spacing_curve"].append({"alpha": a, "error": str(exc)})
                continue
            rec["spacing_curve"].append({
                "alpha": float(a),
                "biases": [float(v) for v in b],
                "rows_used": cell["rows_used"],
                "rank_at_operational_cutoff": cell["rank_at_operational_cutoff"],
                "bare_integer_rank_justified": cell["bare_integer_rank_justified"],
                "largest_gap_ratio": cell["largest_gap_ratio"],
                "operational_cutoff_falls_in_largest_gap":
                    cell["operational_cutoff_falls_in_largest_gap"],
                "rank_cutoff_curve": cell["rank_curve"],
                "singular_values": cell["singular_values"],
            })
        ranks_w = [c["rank_at_operational_cutoff"] for c in rec["width_curve"]
                   if "error" not in c]
        ranks_a = [c["rank_at_operational_cutoff"] for c in rec["spacing_curve"]
                   if "error" not in c]
        rec["summary"] = {
            "rank_range_over_width": [int(min(ranks_w)), int(max(ranks_w))]
            if ranks_w else None,
            "rank_range_over_spacing": [int(min(ranks_a)), int(max(ranks_a))]
            if ranks_a else None,
            "rank_moves_with_width": bool(ranks_w and min(ranks_w) != max(ranks_w)),
            "rank_moves_with_spacing": bool(
                ranks_a and min(ranks_a) != max(ranks_a)),
        }
        out_doc["devices"][dname] = rec
        print(f"  {dname:14s} rank over width   {rec['summary']['rank_range_over_width']}"
              f"   over spacing {rec['summary']['rank_range_over_spacing']}")
        print("    width  " + "  ".join(
            f"{c['width_V']:.2f}->{c['rank_at_operational_cutoff']}"
            for c in rec["width_curve"] if "error" not in c))
        print("    alpha  " + "  ".join(
            f"{c['alpha']:.3f}->{c['rank_at_operational_cutoff']}"
            for c in rec["spacing_curve"] if "error" not in c))

    out_doc["falsifier"] = (
        "SPEC-g9-2 fires if a rank appears anywhere on the claim surface at a "
        "single window without its curve. Guarded on the prose by "
        "tests/test_claim_surface_g9.py, not by this artefact.")
    return out_doc


# ===========================================================================
# Phase 3 -- SPEC-g9-3, the junction witnesses through the refinement falsifier
# ===========================================================================

REFINEMENT_GRIDS = (301, 601, 1201)
REFINEMENT_TOLS = (("default", SGConfig()),
                   ("tight", SGConfig(tol_carrier=1e-12, max_outer=200)))


def phase_junction_refine(cfg, root: Path, out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  SPEC-g9-3  chart-J witnesses through the refinement falsifier")
    print("=" * 74)
    nw = json.loads((root / G8_CHART_J).read_text(
        encoding="utf-8"))["native_witness"]
    kept = np.asarray(nw["kept_log10"], dtype=np.float64)
    pairs = nw["witness_pair_indices"]
    floor = cfg.distinguishability_floor
    biases = list(cfg.biases)

    print(f"  {len(pairs)} chart-J witness pairs, floor {floor:.2e}")
    print("  the doping witnesses survived this exact battery at generation 6; "
          "these never faced it")

    records: List[Dict] = []
    for pi, (ia, ib) in enumerate(pairs):
        ta, tb = kept[ia], kept[ib]
        rows: List[Dict] = []
        for grid in REFINEMENT_GRIDS:
            for tname, sg_cfg in REFINEMENT_TOLS:
                sg_r, x_r = build_solver(cfg, grid, sg_cfg)
                Jr = ChartJ(16, x_r)
                Ia, tra, cva = iv(sg_r, Jr.charted(ta), biases)
                Ib, trb, cvb = iv(sg_r, Jr.charted(tb), biases)
                mask = tra & cva & trb & cvb
                rows.append({
                    "grid_n": grid, "tolerance": tname,
                    "tol_carrier": float(sg_cfg.tol_carrier),
                    "observational_distance": obs_dist(Ia, Ib, mask),
                    "n_biases_certified": int(np.sum(mask)),
                    "n_biases": len(biases),
                    "junction_x_si_a": Jr.junction_position(float(ta[0])),
                    "junction_x_si_b": Jr.junction_position(float(tb[0])),
                    "below_floor": bool(obs_dist(Ia, Ib, mask) < floor),
                })
        base = float(rows[0]["observational_distance"])
        finest = float(rows[-1]["observational_distance"])
        rel_change = float((finest - base) / base) if base else 0.0
        rec = {
            "pair_index": pi,
            "member_indices": [int(ia), int(ib)],
            "g8_observational_distance": float(nw["witness_pair_distance"][pi]),
            "separation_magnitudes_only": float(
                np.max(np.abs(ta[1:] - tb[1:]))),
            "junction_separation_nm": abs(
                float(rows[0]["junction_x_si_a"])
                - float(rows[0]["junction_x_si_b"])) * 1e9,
            "refinements": rows,
            "distance_at_301_default": base,
            "distance_at_1201_tight": finest,
            "distance_rose": bool(finest > base),
            "relative_change": rel_change,
            "survives_refinement": bool(all(r["below_floor"] for r in rows)),
        }
        records.append(rec)
        print(f"    pair {pi:2d}  junctions {rec['junction_separation_nm']:6.1f} nm apart  "
              f"d: {base:.4e} -> {finest:.4e}  "
              f"({'ROSE' if rec['distance_rose'] else 'fell'} "
              f"{100.0 * rel_change:+.1f}%)  "
              f"survives={rec['survives_refinement']}")

    widest = max(records, key=lambda r: r["junction_separation_nm"])
    n_survive = sum(1 for r in records if r["survives_refinement"])
    verdict = {
        "n_pairs": len(records),
        "n_surviving": n_survive,
        "n_separated_by_refinement": len(records) - n_survive,
        "widest_junction_pair": {
            "pair_index": widest["pair_index"],
            "junction_separation_nm": widest["junction_separation_nm"],
            "junction_x_si_a": widest["refinements"][0]["junction_x_si_a"],
            "junction_x_si_b": widest["refinements"][0]["junction_x_si_b"],
            "distance_at_301_default": widest["distance_at_301_default"],
            "distance_at_1201_tight": widest["distance_at_1201_tight"],
            "survives_refinement": widest["survives_refinement"],
        },
        "falsifier": ("SPEC-g9-3 fires if the observational distance RISES -- "
                      "the junction degeneracy would then be a discretisation "
                      "artefact and comes straight out of the headline"),
        "falsifier_fires": bool(any(not r["survives_refinement"]
                                    for r in records)),
        "n_pairs_whose_distance_rose_without_crossing_the_floor": sum(
            1 for r in records if r["distance_rose"] and r["survives_refinement"]),
        "floor": floor,
    }
    print(f"\n  {n_survive}/{len(records)} pairs stay below the floor at every "
          f"refinement; SPEC-g9-3 falsifier fires: {verdict['falsifier_fires']}")
    return {"records": records, "verdict": verdict,
            "battery": {"grids": list(REFINEMENT_GRIDS),
                        "tolerances": [t[0] for t in REFINEMENT_TOLS],
                        "tol_carrier_tight": 1e-12,
                        "inherited_from": "scripts/run_witness_falsifier.py"}}


# ===========================================================================
# Phase 4 -- SPEC-g9-4, basins by barrier depth (pilot-gated)
# ===========================================================================

def _components(n: int, edges: Sequence[Tuple[int, int]]) -> List[int]:
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    return [find(i) for i in range(n)]


def _barrier_between(sg, chart, cfg, biases, th_a, th_b, crit: BarrierCriterion):
    I0_, tr, cv = iv(sg, chart.charted(th_a), biases)
    if not (bool(np.all(tr)) and bool(np.all(cv))):
        return {"skipped": "anchor not certified", "barrier_depth": None,
                "certified": False}

    def ll(theta):
        cur, t_, c_ = iv(sg, chart.charted(theta), biases)
        if not (bool(np.all(t_)) and bool(np.all(c_))):
            return None
        r = (cur - I0_) / (crit.noise_rel * np.abs(I0_))
        return float(-0.5 * np.sum(r ** 2))

    bd = barrier_depth(ll, th_a, th_b, n_points=crit.n_points)
    bd["floor_barrier_log_units"] = 0.5 * len(biases)
    if bd.get("barrier_depth") is not None:
        bd["depth_in_floor_units"] = float(
            bd["barrier_depth"] / (0.5 * len(biases)))
    return bd


def phase_basins(sg, x_si, cfg, root: Path, out: Path,
                 budget_s: float) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 4  SPEC-g9-4  basins by BARRIER DEPTH, pilot-gated")
    print("=" * 74)
    crit = BarrierCriterion()
    print(f"  criterion hashed before any barrier: {crit.criterion_hash()[:32]}...")
    biases = list(cfg.biases)

    rep = json.loads((root / G8_REPRODUCE).read_text(encoding="utf-8"))
    cj = json.loads((root / G8_CHART_J).read_text(encoding="utf-8"))
    sets = [
        ("chart_G_d4", ChartG(4, x_si), rep["chart_G_d4"]),
        ("chart_J_d16", ChartJ(16, x_si), cj["native_witness"]),
    ]

    # -- the pilot -----------------------------------------------------------
    tag0, chart0, res0 = sets[0]
    kept0 = np.asarray(res0["kept_log10"], dtype=np.float64)
    ia, ib = res0["witness_pair_indices"][0]
    t0 = time.perf_counter()
    _ = _barrier_between(sg, chart0, cfg, biases, kept0[ia], kept0[ib], crit)
    per_path = time.perf_counter() - t0
    n_paths = sum(2 * len(s[2]["witness_pair_indices"]) for s in sets)
    projected = per_path * n_paths
    pilot = {
        "seconds_per_path": per_path,
        "paths_required": n_paths,
        "paths_note": ("one path per witness pair plus one per null-control "
                       "pair, in each of the two sets"),
        "projected_seconds": projected,
        "budget_seconds": budget_s,
        "fits": bool(projected <= budget_s),
    }
    print(f"  pilot: {per_path:.1f} s/path x {n_paths} paths = "
          f"{projected:.0f} s against a {budget_s:.0f} s budget -> "
          f"{'FITS' if pilot['fits'] else 'DOES NOT FIT'}")
    if not pilot["fits"]:
        print("  dropping SPEC-g9-4 WHOLE, per the clause: a part-run basin "
              "measurement is worse than none")
        return {"criterion": crit.to_dict(), "pilot": pilot,
                "dropped_whole": True,
                "kept_instead": ("the generation-8 qualitative answer -- the "
                                 "witness set is more than two devices -- "
                                 "stands unchanged and unstrengthened")}

    # -- the measurement -----------------------------------------------------
    doc: Dict = {"criterion": crit.to_dict(), "pilot": pilot,
                 "dropped_whole": False, "sets": {}}
    for tag, chart, res in sets:
        kept = np.asarray(res["kept_log10"], dtype=np.float64)
        pairs = [tuple(p) for p in res["witness_pair_indices"]]
        members = sorted({i for p in pairs for i in p})
        remap = {m: k for k, m in enumerate(members)}

        witness_edges, depths = [], []
        for (a, b) in pairs:
            bd = _barrier_between(sg, chart, cfg, biases, kept[a], kept[b], crit)
            witness_edges.append({"pair": [int(a), int(b)], **bd})
            if bd.get("barrier_depth") is not None:
                depths.append(bd["barrier_depth"])

        # Null control: the same criterion over the same number of ordinary
        # prior draws that form no witness pair, taken in draw order. Without
        # it a basin count is a statement about the criterion.
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

        floor_barrier = 0.5 * len(biases)
        curve = []
        for mult in crit.threshold_multiples_of_floor:
            thr = mult * floor_barrier
            edges = [(remap[e["pair"][0]], remap[e["pair"][1]])
                     for e in witness_edges
                     if e.get("barrier_depth") is not None
                     and e["barrier_depth"] <= thr]
            labels = _components(len(members), edges)
            curve.append({"threshold_multiple_of_floor": float(mult),
                          "threshold_log_units": float(thr),
                          "n_edges_admitted": len(edges),
                          "n_basins": len(set(labels))})
        rec = {
            "n_witness_pairs": len(pairs),
            "n_members": len(members),
            "floor_barrier_log_units": floor_barrier,
            "witness_pair_barriers": witness_edges,
            "null_control_pair_barriers": null_edges,
            "witness_depth_median": float(np.median(depths)) if depths else None,
            "witness_depth_min": float(np.min(depths)) if depths else None,
            "witness_depth_max": float(np.max(depths)) if depths else None,
            "null_depth_median": (float(np.median(null_depths))
                                  if null_depths else None),
            "null_depth_min": float(np.min(null_depths)) if null_depths else None,
            "basin_curve": curve,
            "n_basins_at_the_floor": next(
                c["n_basins"] for c in curve
                if c["threshold_multiple_of_floor"] == 1.0),
            "witness_pairs_below_the_floor_barrier": sum(
                1 for e in witness_edges
                if e.get("barrier_depth") is not None
                and e["barrier_depth"] <= floor_barrier),
        }
        doc["sets"][tag] = rec
        print(f"  {tag}: {len(pairs)} witness pairs, {len(members)} members")
        print(f"    witness barrier depths  median "
              f"{rec['witness_depth_median']}  min {rec['witness_depth_min']}")
        print(f"    null control            median "
              f"{rec['null_depth_median']}  min {rec['null_depth_min']}")
        print(f"    floor barrier {floor_barrier:.1f} log-units; basins at the "
              f"floor: {rec['n_basins_at_the_floor']} of {len(members)}")
        print("    basins vs threshold: " + ", ".join(
            f"{c['threshold_multiple_of_floor']:g}x->{c['n_basins']}"
            for c in curve))
    doc["reading"] = (
        "A witness pair is by construction indistinguishable in the observable, "
        "yet the likelihood barrier BETWEEN its two members is measured here in "
        "units of the barrier a pair sitting exactly on the distinguishability "
        "floor would produce. Two members joined below that reference are one "
        "basin by any reading; two members separated by hundreds of floor units "
        "are two basins whatever a profile-distance metric says about them.")
    doc["falsifier"] = ("SPEC-g9-4 fires if any basin count is reported "
                        "without its null control. The null control is in the "
                        "same record as every count above.")
    return doc


# ===========================================================================
# Phase 5 -- the mandatory negative control
# ===========================================================================

def ordering_is_supported_as_general(points: Dict) -> Dict:
    """The predicate the whole generation turns on, applied to its own inputs.

    Returns the verdict *and* the reason, so that a rejection can be shown to
    have been made for the stated reason rather than by accident.
    """
    n = len(points)
    orders = {tuple(v["order"]["by_max"]) for v in points.values()}
    mild = {tuple(v["order"]["by_mildest"]) for v in points.values()}
    if n < 2:
        return {"supported": False,
                "reason": ("an ordering measured at one operating point is a "
                           "measurement of that point; generality is a claim "
                           "about the others, and none were measured"),
                "n_operating_points": n}
    if len(orders) > 1 or len(mild) > 1:
        return {"supported": False,
                "reason": "the ordering is not the same at every point measured",
                "n_operating_points": n,
                "distinct_orders_by_max": [list(o) for o in orders],
                "distinct_orders_by_mildest": [list(o) for o in mild]}
    if orders != mild:
        return {"supported": False,
                "reason": ("the two ordering statistics disagree, so 'the "
                           "ordering' does not name one object"),
                "n_operating_points": n}
    return {"supported": True,
            "reason": f"the same order under both statistics at all {n} points",
            "n_operating_points": n}


def phase_negative_control(sg, x_si, cfg, op_points: Optional[Dict]) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 5  NEGATIVE CONTROL (mandatory)")
    print("=" * 74)
    out: Dict = {}

    # -- 1. the control the clause names -------------------------------------
    # "An ordering measured at one operating point, stated unqualified. The
    # battery rejects it on SPEC-g9-1."
    single = {}
    if op_points is not None:
        for k, v in op_points["operating_points"].items():
            if v["device"].get("is_reproduction_control"):
                single = {k: v}
                break
    verdict = ordering_is_supported_as_general(single)
    out["an_ordering_from_one_operating_point_is_rejected"] = {
        "construction": ("exactly the generation-8 evidence -- the four-way "
                         "ordering at witness pair 0 member a, 16 biases over "
                         "0.15-0.90 V -- offered to the battery as a general "
                         "claim"),
        "claim_offered": "observation set > junction > dimension > interpolant, "
                         "unqualified",
        "verdict": verdict,
        "rejected": bool(not verdict["supported"]),
        "ran_through": "scripts/run_g9.py::ordering_is_supported_as_general, "
                       "the same predicate that judges the positive result",
    }
    r1 = out["an_ordering_from_one_operating_point_is_rejected"]
    print(f"  1. one-operating-point ordering offered as general -> "
          f"{'REJECTED' if r1['rejected'] else 'ACCEPTED (control failed)'}")
    print(f"     reason: {verdict['reason']}")

    # -- 2. and the same predicate must ACCEPT when it should -----------------
    # A predicate that only ever rejects is not a predicate. Three synthetic
    # points carrying one order under both statistics must be accepted.
    same = {f"synthetic_{i}": {"order": {
        "by_max": ["observation_set", "junction", "dimension", "interpolant"],
        "by_mildest": ["observation_set", "junction", "dimension",
                       "interpolant"]}} for i in range(3)}
    acc = ordering_is_supported_as_general(same)
    out["the_same_predicate_accepts_a_consistent_ordering"] = {
        "construction": "three synthetic points carrying one order under both "
                        "statistics",
        "verdict": acc, "accepted": bool(acc["supported"]),
    }
    print(f"  2. three consistent synthetic points -> "
          f"{'ACCEPTED (control passes)' if acc['supported'] else 'REJECTED (control failed)'}")

    # -- 3. the refinement battery must be able to SEPARATE a pair ------------
    # SPEC-g9-3 is only informative if the battery can detect separation. A
    # distinguishable pair must come out above the floor at every refinement.
    m15 = np.full(15, 22.0)
    ta = np.concatenate([[float(np.log10(0.25 / 0.75))], m15])
    tb = np.concatenate([[float(np.log10(0.75 / 0.25))], m15])
    rows: List[Dict] = []
    for grid in (301, 1201):
        sg_r, x_r = build_solver(cfg, grid, SGConfig(tol_carrier=1e-12,
                                                     max_outer=200))
        Jr = ChartJ(16, x_r)
        Ia, tra, cva = iv(sg_r, Jr.charted(ta), cfg.biases)
        Ib, trb, cvb = iv(sg_r, Jr.charted(tb), cfg.biases)
        mask = tra & cva & trb & cvb
        rows.append({"grid_n": grid, "observational_distance":
                     obs_dist(Ia, Ib, mask),
                     "above_floor": bool(obs_dist(Ia, Ib, mask)
                                         >= cfg.distinguishability_floor)})
    out["the_refinement_battery_can_separate_a_distinguishable_pair"] = {
        "construction": ("two chart-J devices with identical doping magnitudes "
                         "and junctions at 0.25 L and 0.75 L, through the same "
                         "refinement battery SPEC-g9-3 uses"),
        "rows": rows,
        "passes": bool(all(r["above_floor"] for r in rows)),
    }
    r3 = out["the_refinement_battery_can_separate_a_distinguishable_pair"]
    print(f"  3. distinguishable chart-J pair through the refinement battery -> "
          f"{'ABOVE FLOOR at every refinement (control passes)' if r3['passes'] else 'FAILED'}")

    # -- 4. the chart discriminator must return "not different" ---------------
    G15 = ChartG(15, x_si)
    Jp = ChartJ(16, x_si, junction_scale=0.0)
    th = np.concatenate([[0.0], m15])
    _, Jmat_p, _ = cell_spectrum(sg, Jp, th, cfg.biases, cfg)
    _, Jmat_g, _ = cell_spectrum(sg, G15, m15, cfg.biases, cfg)
    mag_cols = float(np.max(np.abs(Jmat_p[:, 1:] - Jmat_g))
                     / max(float(np.max(np.abs(Jmat_g))), 1e-300))
    out["chart_discriminator_returns_not_different_for_a_pinned_junction"] = {
        "construction": ("chart J with junction_scale = 0 pins the junction "
                         "where charts G and L pin it; retained from "
                         "generation 8 because every junction number in "
                         "phase 1 rests on it"),
        "pinned_junction_column_norm": float(np.linalg.norm(Jmat_p[:, 0])),
        "magnitude_columns_vs_chartG_d15_max_rel": mag_cols,
        "not_different": bool(np.linalg.norm(Jmat_p[:, 0]) == 0.0
                              and mag_cols < 1e-12),
    }
    r4 = out["chart_discriminator_returns_not_different_for_a_pinned_junction"]
    print(f"  4. pinned-junction chart J vs chart G d=15 -> "
          f"{'NOT DIFFERENT (control passes)' if r4['not_different'] else 'DIFFERENT (control failed)'}")

    out["all_controls_pass"] = bool(
        r1["rejected"] and acc["supported"] and r3["passes"]
        and r4["not_different"])
    print(f"\n  -> all negative controls behave as required: "
          f"{out['all_controls_pass']}")
    return out


# ===========================================================================

ALL_PHASES = ["preregister", "op_points", "rank_obs", "junction_refine",
              "basins", "negative_control"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g9")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    ap.add_argument("--basin-budget-s", type=float, default=900.0,
                    help="SPEC-g9-4 is dropped WHOLE if the pilot projects "
                         "more than this; it is never part-run")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    cfg = GlobalStudyConfig()
    sg, x_si = build_solver(cfg, args.grid)

    man = RunManifest.create(
        "g9",
        config={**cfg.to_dict(), "grid_n": args.grid, "phases": phases,
                "rel_step": REL_STEP, "min_snr": MIN_SNR,
                "spectral_k": SPECTRAL_K,
                "basin_budget_s": args.basin_budget_s,
                "operating_point_rule": OperatingPointRule().to_dict(),
                "ordering_statistic": OrderingStatistic().to_dict(),
                "barrier_criterion": BarrierCriterion().to_dict(),
                "g6_artefact": G6_ARTEFACT, "g8_chart_j": G8_CHART_J,
                "g8_reproduce": G8_REPRODUCE},
        seed=cfg.seed,
        notes="G9. Oracle-arbitrated; the surrogate is never called.")

    results: Dict[str, Dict] = {}

    def _load(name):
        if name in results:
            return results[name]
        p = out / f"{name}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    for name in phases:
        path = out / f"{name}.json"
        if name == "preregister":
            r = phase_preregister(root, out)
        elif name == "op_points":
            r = phase_op_points(sg, x_si, cfg, root, out,
                                _check_preregistration(out))
        elif name == "rank_obs":
            _check_preregistration(out)
            ws = json.loads((root / G6_ARTEFACT).read_text(
                encoding="utf-8"))["witness_search"]
            # Two devices, not all four. SPEC-g9-2 says "at fixed device";
            # one satisfies the clause and a second says whether the curve's
            # SHAPE is a property of the device or of the instrument. Running
            # all four would spend a third of the generation's budget
            # re-answering a question two already answer. Which two is stated
            # rather than chosen by outcome: the generation-8 operating point,
            # because that is the point every published rank sits at, and the
            # median-doping device, because it is the one the selection rule
            # puts at the centre of the prior.
            devices = {"g8_operating_point":
                       ws["witnesses"][0]["profile_a_log10"]}
            op = _load("op_points")
            if op is not None:
                for c in op["selection"]["chosen"]:
                    if c["name"] == "device_p50":
                        devices[c["name"]] = c["theta_chartG_d4"]
            r = phase_rank_obs(sg, x_si, cfg, root, out, devices)
        elif name == "junction_refine":
            r = phase_junction_refine(cfg, root, out)
        elif name == "basins":
            _check_preregistration(out)
            r = phase_basins(sg, x_si, cfg, root, out, args.basin_budget_s)
        elif name == "negative_control":
            r = phase_negative_control(sg, x_si, cfg, _load("op_points"))
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
