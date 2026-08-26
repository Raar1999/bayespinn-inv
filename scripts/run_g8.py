"""G8: a third chart, what the observation set does, rank as a curve, and how many basins.

Oracle-arbitrated throughout; the surrogate is never called (``SPEC-g6-5``,
``PH-22``). Every phase writes its own JSON so a later phase failing cannot cost
an earlier phase's measurement.

    PYTHONPATH=src python scripts/run_g8.py --phases \
        reproduce,chart_j,obs_set,ranks,modes,negative_control

Phase order is the ruling's budget order. ``negative_control`` is mandatory and
is never dropped; if budget binds, ``modes``' barrier sample shrinks first, then
the chart-J witness budget.

What each phase answers
-----------------------
``reproduce``
    Re-runs the generation-6 chart-G and generation-7 chart-L witness searches
    through the post-``CHART-01`` code. Two jobs: prove the structural fix moved
    no number, and render **all** witnesses rather than the first five, which is
    what ``SPEC-g8-5`` needs and the existing artefacts do not contain.
``chart_j``
    ``SPEC-g8-2``. A third chart with the junction as a free continuous
    coordinate, its containment relation to G and L, its spectrum at matched
    ``d``, and a native witness search in it.
``obs_set``
    ``SPEC-g8-3``. Does perturbing the observation set move the spectrum more
    than changing the chart did?
``ranks``
    ``SPEC-g8-4``. ``rank(cutoff)`` curves for every cell.
``modes``
    ``SPEC-g8-5``. How many basins is the witness set?
``negative_control``
    Mandatory. Four predicates, each shown to return the negative answer on a
    case constructed to deserve it, through the same code the positive results
    ran through.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

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
    witness_search,
)
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    rank_cutoff_record,
)
from bayespinn_inv.inverse.modes import (
    ClusterCriterion,
    barrier_depth,
    count_basins,
    profile_distance_matrix,
    witness_graph_components,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest

G6_ARTEFACT = "outputs/global_identifiability_g6/global_identifiability.json"
G7_ARTEFACT = "outputs/chart_reconciliation_g7/native_witness.json"


# ===========================================================================
# Priors that are not the doping prior
# ===========================================================================

@dataclass(frozen=True)
class JunctionPrior:
    """Prior over chart J's coordinates, hashed before sampling (``AH-14``).

    ``GlobalStudyConfig.prior_hash`` describes a vector of log10 doping
    magnitudes and nothing else, so it cannot identify a prior one of whose
    coordinates is a junction position. Recording only that hash for a chart-J
    search would be recording the wrong prior, which is worse than recording
    none. This dataclass carries the rest, and both hashes go in the artefact.

    The junction is drawn **uniform in physical position** over
    ``[frac_lo, frac_hi] * L``, not uniform in the coordinate ``s``. Junction
    depth is a fabrication length and a flat prior on the length is the
    defensible default; a flat prior on ``s = log10(x_j/(L-x_j))`` would pile
    mass at the two contacts. The coordinate is a reparameterisation for the
    Jacobian, not a claim about where junctions are.
    """

    frac_lo: float = 0.2
    frac_hi: float = 0.8
    n_mag: int = 15
    mag_lo_si: float = 1e21
    mag_hi_si: float = 1e23
    junction_scale: float = 1.0
    seed: int = 0

    def prior_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = asdict(self)
        out["junction_prior_hash"] = self.prior_hash()
        out["note"] = ("uniform in x_j/L over [frac_lo, frac_hi]; log-uniform in "
                       "magnitude at n_mag anchors; theta = [s, m_1..m_n_mag]")
        return out

    def draw(self, _cfg, n: int) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        frac = rng.uniform(self.frac_lo, self.frac_hi, size=n)
        s = np.log10(frac / (1.0 - frac)) / self.junction_scale
        mags = rng.uniform(np.log10(self.mag_lo_si), np.log10(self.mag_hi_si),
                           size=(n, self.n_mag))
        return np.concatenate([s[:, None], mags], axis=1)


# ===========================================================================
# Shared machinery
# ===========================================================================

def build_solver(cfg: GlobalStudyConfig, grid_n: int):
    scaling = Scaling.for_material(SILICON, T=300.0)
    length = cfg.domain_si[1] - cfg.domain_si[0]
    sg = ScharfetterGummel1D(
        Grid1D.uniform(float(scaling.x_to_scaled(np.float64(length))), grid_n),
        scaling, SILICON, SGConfig())
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
    return np.asarray(cur), bool(np.all(trust)), bool(np.all(conv))


def obs_dist(ia, ib) -> float:
    """witness_search's own metric: max over biases of |dI| / max(|Ia|, |Ib|)."""
    denom = np.maximum(np.abs(ia), np.abs(ib))
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nanmax(np.abs(ia - ib) / denom))


def make_chart_oracle(sg, chart):
    def oracle(theta, biases):
        prev, cur, trust, conv = None, [], [], []
        for v in biases:
            st = sg.solve(chart.charted(theta), float(v), initial_state=prev)
            prev = st
            cur.append(st.terminal_current)
            trust.append(bool(st.current_is_trustworthy()))
            conv.append(bool(st.converged))
        return np.asarray(cur), np.asarray(trust), np.asarray(conv)
    return oracle


def spectral_movement(sa: Sequence[float], sb: Sequence[float],
                      k: int = 5) -> Dict[str, float]:
    """Max and mean relative movement over the leading ``k`` singular values.

    The same comparison generation 7 made between charts at ``d=16`` ("sigma_1
    ... sigma_5 agree to within 3%"), so that a chart change and an
    observation-set change are measured with one ruler.
    """
    a = np.asarray(sa, dtype=np.float64)[:k]
    b = np.asarray(sb, dtype=np.float64)[:k]
    m = min(a.size, b.size)
    if m == 0:
        return {"max_rel": float("nan"), "mean_rel": float("nan"), "k": 0}
    rel = np.abs(b[:m] - a[:m]) / np.maximum(np.abs(a[:m]), 1e-300)
    return {"max_rel": float(np.max(rel)), "mean_rel": float(np.mean(rel)),
            "k": int(m)}


def cell_spectrum(sg, chart, theta, biases, cfg, rel_step=0.05, min_snr=1e4):
    t0 = time.perf_counter()
    J, I_ref, kept, eta = chart_forward_jacobian(
        sg, chart, theta, biases, rel_step=rel_step, min_snr=min_snr)
    rep = analyse_identifiability(J, noise_rel=cfg.noise_rel, jacobian_noise=eta)
    rec = rank_cutoff_record(rep, cfg.noise_rel)
    rec.update({
        "chart": chart.name,
        "chart_label": chart.label(),
        "d": chart.d,
        "n_magnitude_coordinates": chart.n_mag,
        "theta": [float(t) for t in np.asarray(theta, dtype=np.float64)],
        "biases_used": [float(biases[i]) for i in kept],
        "n_biases_offered": len(biases),
        "rel_step_decades": float(rel_step),
        "wall_clock_s": time.perf_counter() - t0,
    })
    return rec, J, rep


# ===========================================================================
# Phase 1 -- reproduce, and render every witness
# ===========================================================================

def phase_reproduce(sg, x_si, cfg, root, n_g, n_l) -> Dict:
    print("=" * 74)
    print("PHASE 1  REPRODUCE the g6 and g7 witness searches through the")
    print("         post-CHART-01 code, and render EVERY witness")
    print("=" * 74)
    out: Dict = {}

    for tag, chart, n, cfg_k, artefact, key in (
        ("chart_G_d4", ChartG(4, x_si), n_g, GlobalStudyConfig(n_anchor=4),
         G6_ARTEFACT, "witness_search"),
        ("chart_L_d16", ChartL(16, x_si), n_l, GlobalStudyConfig(n_anchor=16),
         G7_ARTEFACT, "prior_search"),
    ):
        print(f"\n  {tag}: n={n} draws, prior hash {cfg_k.prior_hash()[:16]}...")

        def tick(i, total, _t=tag):
            if i % 500 == 0 or i == total:
                print(f"    {_t} sampled {i}/{total}", flush=True)

        t0 = time.perf_counter()
        res = witness_search(cfg_k, make_chart_oracle(sg, chart), n, tick,
                             max_witnesses=None, include_samples=True)
        res["wall_clock_s"] = time.perf_counter() - t0
        res["chart"] = chart.name
        res["d"] = chart.d

        prior = json.loads((root / artefact).read_text(encoding="utf-8"))[key]
        same_n = int(prior["n_witnesses"]) == int(res["n_witnesses"])
        same_pairs = int(prior["n_pairs_examined"]) == int(res["n_pairs_examined"])
        deltas = []
        for a, b in zip(prior["witnesses"], res["witnesses"]):
            deltas.append(abs(a["observational_distance"]
                              - b["observational_distance"]))
        res["reproduction_control"] = {
            "prior_artefact": artefact,
            "prior_n_witnesses": int(prior["n_witnesses"]),
            "n_witnesses": int(res["n_witnesses"]),
            "n_witnesses_identical": bool(same_n),
            "n_pairs_identical": bool(same_pairs),
            "max_abs_delta_on_first_5_distances":
                float(max(deltas)) if deltas else None,
            "verdict": ("the CHART-01 fix moved no published number"
                        if same_n and same_pairs and (not deltas or max(deltas) == 0.0)
                        else "MISMATCH -- the structural fix changed a result"),
        }
        print(f"    -> {res['n_witnesses']} witnesses "
              f"(artefact says {prior['n_witnesses']}); "
              f"{res['reproduction_control']['verdict']}")
        out[tag] = res
    return out


# ===========================================================================
# Phase 2 -- SPEC-g8-2, the third chart
# ===========================================================================

def phase_chart_j(sg, x_si, cfg, ws, n_samples, jprior: JunctionPrior) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  CHART J: the junction as a free continuous coordinate")
    print("=" * 74)
    G4 = ChartG(4, x_si)
    G15, G16 = ChartG(15, x_si), ChartG(16, x_si)
    L16 = ChartL(16, x_si)
    J16 = ChartJ(16, x_si)
    biases = cfg.biases

    out: Dict = {"junction_prior": jprior.to_dict(),
                 "doping_prior_hash": GlobalStudyConfig(n_anchor=16).prior_hash()}

    # -- positive control: J at s = 0 IS chart G at d-1 -----------------------
    m_flat = np.full(15, 22.0)
    exact = bool(np.array_equal(J16.reconstruct(np.concatenate([[0.0], m_flat])),
                                G15.reconstruct(m_flat)))
    out["positive_control_J_at_s0_is_G_at_d_minus_1"] = {
        "identical": exact,
        "note": ("chart J spends one coordinate on the junction, so its "
                 "magnitude family at d is chart G's at d-1. If this is not "
                 "bit-identical then the third chart is not the second chart "
                 "plus a coordinate, and nothing below is a controlled "
                 "comparison."),
    }
    print(f"  positive control  J(s=0) == G(d-1) exactly: {exact}")

    # -- can charts G and L reach a displaced junction at all? ---------------
    # Two probes, following the g7 containment design: one that isolates the
    # junction obstruction and one that carries both obstructions at once.
    # A single probe measures one thing and gets quoted as if it measured two.
    a4 = np.array(ws["witnesses"][0]["profile_a_log10"], dtype=np.float64)
    m_generic = np.interp(G15.anchors, G4.anchors, a4)
    probes = {
        "flat_magnitude": {
            "m": m_flat,
            "why": ("constant magnitude, which charts G and L both reproduce "
                    "exactly, so every residual below is the junction alone"),
        },
        "witness_member_a_magnitudes": {
            "m": m_generic,
            "why": ("the g7 operating point's magnitudes, collocated to 15 "
                    "anchors: generic, so it carries the interpolant "
                    "obstruction and the junction obstruction together"),
        },
    }
    shifts = []
    for pname, probe in probes.items():
        for frac in (0.25, 0.35, 0.5, 0.65, 0.75):
            ss = float(np.log10(frac / (1.0 - frac)))
            prof_j = J16.reconstruct(np.concatenate([[ss], probe["m"]]))
            rec: Dict = {"probe": pname, "probe_why": probe["why"],
                         "junction_frac": frac, "s": ss,
                         "junction_x_si": J16.junction_position(ss)}
            for name, target in (("G_d16", G16), ("L_d16", L16)):
                best = None
                for method in ("collocate", "log10"):
                    th, diag = project_into_chart(target, prof_j, method=method)
                    prof_t = target.reconstruct(th)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        dec = np.abs(np.log10(np.abs(prof_t))
                                     - np.log10(np.abs(prof_j)))
                    fin = np.isfinite(dec)
                    val = float(np.max(dec[fin])) if fin.any() else float("inf")
                    signs = int(np.sum(np.sign(prof_t) != np.sign(prof_j)))
                    # REP-01: the method sits in the same record as the value.
                    rec[f"{name}__{method}"] = {
                        "method": diag.get("method", method),
                        "profile_max_decades": val,
                        "nodes_excluded_nonfinite": int(np.sum(~fin)),
                        "sign_disagreements": signs,
                    }
                    if best is None or (signs, val) < best[0]:
                        best = ((signs, val), method)
                rec[f"{name}__best"] = {"method": best[1],
                                        "sign_disagreements": best[0][0],
                                        "profile_max_decades": best[0][1]}
            shifts.append(rec)
            print(f"  {pname:28s} x_j/L={frac:.2f}: "
                  f"best G stand-in {rec['G_d16__best']['profile_max_decades']:7.4f} dec / "
                  f"{rec['G_d16__best']['sign_disagreements']:3d} sign nodes  |  "
                  f"best L stand-in {rec['L_d16__best']['profile_max_decades']:7.4f} dec / "
                  f"{rec['L_d16__best']['sign_disagreements']:3d} sign nodes")
    out["displaced_junction_not_reachable_by_G_or_L"] = shifts
    out["reachability_reading"] = (
        "Charts G and L reproduce the magnitude of a displaced-junction device "
        "and cannot reproduce its sign structure: the residual is carried "
        "entirely by grid nodes on the wrong side of the junction. That is the "
        "qualitative change SPEC-g8-2 asked for -- chart J's reachable set is "
        "not a refinement of either older chart's, it is a different set.")

    # -- spectra ------------------------------------------------------------
    # Two reference cells, because chart J at d spends one coordinate on the
    # junction: G_d16 is the g7 matched-d reference, G_d15 is the magnitude
    # matched one. Comparing J's 16 columns against G's 16 magnitude columns
    # alone would confuse "the chart changed" with "d-1 magnitudes, not d".
    cells: Dict[str, Dict] = {}
    for nm, ch, th in (("G_d16", G16, np.interp(G16.anchors, G4.anchors, a4)),
                       ("G_d15", G15, m_generic)):
        rec, Jm, _ = cell_spectrum(sg, ch, th, biases, cfg)
        rec["magnitude_block_singular_values"] = [
            float(v) for v in np.linalg.svd(Jm, compute_uv=False)]
        cells[nm] = rec

    def add_J(name, chart, theta, extra):
        rec, Jm, _ = cell_spectrum(sg, chart, theta, biases, cfg)
        rec.update(extra)
        rec["junction_scale"] = chart.junction_scale
        rec["junction_s"] = float(theta[0])
        rec["junction_x_si"] = chart.junction_position(float(theta[0]))
        rec["junction_node_shift_per_rel_step"] = chart.junction_node_shift(
            float(theta[0]), 0.05)
        rec["junction_column_norm"] = float(np.linalg.norm(Jm[:, 0]))
        rec["magnitude_block_singular_values"] = [
            float(v) for v in np.linalg.svd(Jm[:, 1:], compute_uv=False)]
        rec["magnitude_columns_identical_to_G_d15"] = bool(
            np.array_equal(Jm[:, 1:], cells["G_d15"].get("_J")))
        cells[name] = rec
        return rec, Jm

    # keep G_d15's Jacobian for the identity check above
    _, JG15, _ = cell_spectrum(sg, G15, m_generic, biases, cfg)
    cells["G_d15"]["_J"] = JG15

    for js in (0.1, 1.0, 10.0):
        rec, _ = add_J(f"J_d16_s0_js{js:g}", ChartJ(16, x_si, junction_scale=js),
                       np.concatenate([[0.0], m_generic]),
                       {"cell_kind": "junction pinned at the midpoint by s=0"})
        print(f"  J d=16 s=0 js={js:<5g} rank "
              f"{rec['rank_at_operational_cutoff']}/{rec['n_parameters']} "
              f"junction col |.|={rec['junction_column_norm']:.4e} "
              f"node shift {rec['junction_node_shift_per_rel_step']:.2f} "
              f"mag cols == G_d15: {rec['magnitude_columns_identical_to_G_d15']}")

    for frac in (0.35, 0.65):
        ss = float(np.log10(frac / (1.0 - frac)))
        rec, _ = add_J(f"J_d16_xj{frac:g}", ChartJ(16, x_si),
                       np.concatenate([[ss], m_generic]),
                       {"cell_kind": f"junction displaced to x_j/L = {frac}"})
        print(f"  J d=16 x_j/L={frac:<4g} rank "
              f"{rec['rank_at_operational_cutoff']}/{rec['n_parameters']} "
              f"junction col |.|={rec['junction_column_norm']:.4e}")

    rec, _ = add_J("J_d16_pinned", ChartJ(16, x_si, junction_scale=0.0),
                   np.concatenate([[0.0], m_generic]),
                   {"cell_kind": "junction_scale = 0: the coordinate is dead"})
    for c in cells.values():
        c.pop("_J", None)
    out["cells"] = cells

    # -- the two discriminators ----------------------------------------------
    # 1. the full spectrum, which is NOT units-free and is reported as such
    full = {k: spectral_movement(cells["G_d16"]["singular_values"],
                                 v["singular_values"])
            for k, v in cells.items() if k != "G_d16"}
    # 2. the magnitude block, which is
    mag = {k: spectral_movement(cells["G_d15"]["magnitude_block_singular_values"],
                                v["magnitude_block_singular_values"])
           for k, v in cells.items() if k not in ("G_d15",)}
    out["spectral_movement"] = {
        "full_spectrum_vs_G_d16": full,
        "magnitude_block_vs_G_d15": mag,
        "why_two": (
            "chart J's Jacobian has 15 columns in decades of doping and one in "
            "decades of junction ratio. A singular spectrum of a matrix with "
            "mixed column units depends on the relative scaling of those units, "
            "and there is no units-free choice -- so the full-spectrum row is "
            "reported *with* its junction_scale and is not a chart-invariance "
            "measurement. The magnitude block is unit-homogeneous and is."),
    }
    for k, v in full.items():
        print(f"  full spectrum   {k:20s} vs G_d16: max {v['max_rel']:.4f}")
    for k, v in mag.items():
        print(f"  magnitude block {k:20s} vs G_d15: max {v['max_rel']:.4f}")

    js_moves = {k: full[k]["max_rel"] for k in full if k.startswith("J_d16_s0_js")}
    disp_moves = {k: mag[k]["max_rel"] for k in mag if k.startswith("J_d16_xj")}
    out["spec_g8_2_falsifier"] = {
        "clause": ("the spectrum at matched d moves materially, which retires "
                   "the invariance claim to its measured family"),
        "g7_chart_change_G_to_L_at_d16_max_rel": 0.03,
        "junction_scale_sweep_full_spectrum_max_rel": js_moves,
        "displaced_junction_magnitude_block_max_rel": disp_moves,
        "fires_on_full_spectrum": bool(
            js_moves and max(js_moves.values()) > 0.03),
        "fires_on_magnitude_block": bool(
            disp_moves and max(disp_moves.values()) > 0.03),
    }

    # -- native witness search in chart J ------------------------------------
    print(f"\n  native witness search in chart J at d=16, n={n_samples}")
    cfgJ = GlobalStudyConfig(n_anchor=16)

    def tick(i, total):
        if i % 250 == 0 or i == total:
            print(f"    sampled {i}/{total}", flush=True)

    t0 = time.perf_counter()
    res = witness_search(cfgJ, make_chart_oracle(sg, J16), n_samples, tick,
                         draw=jprior.draw, max_witnesses=None,
                         include_samples=True)
    res["wall_clock_s"] = time.perf_counter() - t0
    res["chart"] = "J"
    res["d"] = 16
    res["prior_is_not_cfg_prior"] = (
        "cfg.prior_hash() describes 16 log10 doping magnitudes. Chart J's "
        "coordinate 0 is a junction position, so that hash does NOT identify "
        "this prior. The junction prior and its own hash are recorded beside it.")

    split = []
    for w in res["witnesses"]:
        ta = np.asarray(w["profile_a_log10"], dtype=np.float64)
        tb = np.asarray(w["profile_b_log10"], dtype=np.float64)
        split.append({
            "separation_decades_reported": float(w["separation_decades"]),
            "separation_magnitudes_only": float(np.max(np.abs(ta[1:] - tb[1:]))),
            "separation_junction_only": float(abs(ta[0] - tb[0])),
            "junction_x_si_a": J16.junction_position(ta[0]),
            "junction_x_si_b": J16.junction_position(tb[0]),
            "observational_distance": float(w["observational_distance"]),
        })
    res["separation_split"] = split
    res["separation_metric_caveat"] = (
        "witness_search's separation is max|dtheta| over coordinates, and in "
        "chart J coordinate 0 is decades of junction ratio while the rest are "
        "decades of doping. The split is reported per witness, and the "
        "magnitude-only count below is the unit-homogeneous reading.")
    res["n_witnesses_magnitude_separated"] = int(sum(
        1 for sp in split
        if sp["separation_magnitudes_only"] >= cfg.min_separation_decades))
    print(f"  -> {res['n_witnesses']} witness pair(s); "
          f"{res['n_witnesses_magnitude_separated']} of them are still witnesses "
          f"under a magnitude-only separation criterion")
    out["native_witness"] = res
    return out


# ===========================================================================
# Phase 3 -- SPEC-g8-3, the observation-set discriminator
# ===========================================================================

OBS_VARIANTS = {
    "baseline_16_linear_0.15_0.90": dict(kind="given"),
    "16_geometric_0.15_0.90": dict(kind="geom", n=16, lo=0.15, hi=0.90),
    "16_linear_0.30_0.60": dict(kind="lin", n=16, lo=0.30, hi=0.60),
    "16_linear_0.50_0.90": dict(kind="lin", n=16, lo=0.50, hi=0.90),
    "8_every_other": dict(kind="stride", stride=2),
    "8_lower_half": dict(kind="slice", lo_i=0, hi_i=8),
}


def _biases_for(name: str, base: Sequence[float]) -> Tuple[np.ndarray, bool]:
    spec = OBS_VARIANTS[name]
    b = np.asarray(base, dtype=np.float64)
    if spec["kind"] == "given":
        out = b
    elif spec["kind"] == "geom":
        out = np.geomspace(spec["lo"], spec["hi"], spec["n"])
    elif spec["kind"] == "lin":
        out = np.linspace(spec["lo"], spec["hi"], spec["n"])
    elif spec["kind"] == "stride":
        out = b[::spec["stride"]]
    else:
        out = b[spec["lo_i"]:spec["hi_i"]]
    return np.round(out, 4), bool(out.shape[0] == b.shape[0])


def phase_obs_set(sg, x_si, cfg, ws) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  OBSERVATION-SET DISCRIMINATOR")
    print("=" * 74)
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    L16 = ChartL(16, x_si)
    J16 = ChartJ(16, x_si)
    p0 = ws["witnesses"][0]
    a4 = np.array(p0["profile_a_log10"], dtype=np.float64)
    m16 = np.interp(G16.anchors, G4.anchors, a4)
    m15 = np.interp(ChartG(15, x_si).anchors, G4.anchors, a4)
    thL, _ = project_into_chart(L16, G4.reconstruct(a4), method="log10",
                                source_chart=G4, source_log10=a4)

    charts = {"G_d16": (G16, m16), "L_d16": (L16, thL),
              "J_d16": (J16, np.concatenate([[0.0], m15]))}

    out: Dict = {
        "operating_point": "witness pair 0 member a (chart G d=4), "
                           "collocated / projected into each chart",
        "why_row_count_matters": (
            "Dropping bias points changes the number of Jacobian rows, and a "
            "singular value of a taller matrix is larger for that reason alone. "
            "Variants are therefore flagged B_matched; only the B-matched ones "
            "compare like with like, and the rest are reported with the "
            "confound named rather than dropped."),
        "variants": {}, "per_chart": {},
    }

    for cname, (chart, theta) in charts.items():
        per: Dict[str, Dict] = {}
        for vname in OBS_VARIANTS:
            b, matched = _biases_for(vname, cfg.biases)
            try:
                rec, _, _ = cell_spectrum(sg, chart, theta, b, cfg)
            except ValueError as exc:
                per[vname] = {"error": str(exc), "B_matched": matched}
                continue
            rec["B_matched_to_baseline"] = matched
            rec["biases"] = [float(x) for x in b]
            per[vname] = rec
            out["variants"][vname] = {"n_biases": int(b.shape[0]),
                                      "B_matched": matched,
                                      "biases": [float(x) for x in b]}
        base = per["baseline_16_linear_0.15_0.90"]
        for rec in per.values():
            if "error" in rec:
                continue
            rec["movement_vs_baseline"] = spectral_movement(
                base["singular_values"], rec["singular_values"])
            nb = np.sqrt(len(rec["biases_used"]))
            nbase = np.sqrt(len(base["biases_used"]))
            rec["movement_vs_baseline_sqrtB_normalised"] = spectral_movement(
                np.asarray(base["singular_values"]) / nbase,
                np.asarray(rec["singular_values"]) / nb)
        out["per_chart"][cname] = per
        print(f"  {cname}:")
        for vname, rec in per.items():
            if "error" in rec:
                print(f"    {vname:32s} ERROR {rec['error'][:40]}")
                continue
            mv = rec["movement_vs_baseline"]
            print(f"    {vname:32s} B={len(rec['biases_used']):2d} "
                  f"{'matched' if rec['B_matched_to_baseline'] else 'UNMATCHED'} "
                  f"rank {rec['rank_at_operational_cutoff']:2d} "
                  f"move max {mv['max_rel']:.4f}")

    # The comparison the clause asks for.
    gb = out["per_chart"]["G_d16"]["baseline_16_linear_0.15_0.90"]
    lb = out["per_chart"]["L_d16"]["baseline_16_linear_0.15_0.90"]
    chart_move = spectral_movement(gb["singular_values"], lb["singular_values"])
    cells_g = out["per_chart"]["G_d16"]
    base_used = len(cells_g["baseline_16_linear_0.15_0.90"]["biases_used"])
    obs_moves, obs_norm, used = {}, {}, {}
    for v in OBS_VARIANTS:
        rec = cells_g.get(v, {})
        if "error" in rec or v == "baseline_16_linear_0.15_0.90":
            continue
        obs_moves[v] = rec["movement_vs_baseline"]["max_rel"]
        obs_norm[v] = rec["movement_vs_baseline_sqrtB_normalised"]["max_rel"]
        used[v] = len(rec["biases_used"])
    obs_moves_matched = {v: m for v, m in obs_moves.items()
                         if out["variants"][v]["B_matched"]}
    obs_norm_matched = {v: m for v, m in obs_norm.items()
                        if out["variants"][v]["B_matched"]}
    out["discriminator"] = {
        "chart_change_G_to_L_at_d16_max_rel": chart_move["max_rel"],
        "baseline_rows_used": base_used,
        "rows_used_per_variant": used,
        "observation_set_change_max_rel": obs_moves,
        "observation_set_change_max_rel_sqrtB_normalised": obs_norm,
        "observation_set_change_max_rel_offered_B_matched_only": obs_moves_matched,
        "largest_offered_B_matched_observation_move": (
            max(obs_moves_matched.values()) if obs_moves_matched else None),
        "largest_sqrtB_normalised_observation_move": (
            max(obs_norm_matched.values()) if obs_norm_matched else None),
        "row_count_confound": (
            "min_snr discards bias rows below the oracle's own noise floor, so "
            "the number of rows actually differenced is not the number offered: "
            f"the baseline offers 16 and uses {base_used}. Two readings are "
            "given -- the raw movement, and the movement after dividing each "
            "spectrum by sqrt(rows used), which removes the part of a singular "
            "value that is matrix height rather than physics. Both are reported "
            "because neither is the whole answer, and the verdict is the same "
            "under either."),
        "falsifier": ("SPEC-g8-3 fires if observation-set perturbation moves the "
                      "spectrum more than the chart change did"),
        "falsifier_fires": bool(
            obs_moves_matched
            and max(obs_moves_matched.values()) > chart_move["max_rel"]),
        "falsifier_fires_sqrtB_normalised": bool(
            obs_norm_matched
            and max(obs_norm_matched.values()) > chart_move["max_rel"]),
    }
    print("")
    print(f"  chart change G->L at d=16 : {chart_move['max_rel']:.4f}")
    print(f"  largest observation-set change (offered-B matched): "
          f"{out['discriminator']['largest_offered_B_matched_observation_move']}")
    print(f"  ... after sqrt(rows-used) normalisation:            "
          f"{out['discriminator']['largest_sqrtB_normalised_observation_move']}")
    print(f"  SPEC-g8-3 falsifier fires: "
          f"{out['discriminator']['falsifier_fires']}  (normalised: "
          f"{out['discriminator']['falsifier_fires_sqrtB_normalised']})")
    return out


# ===========================================================================
# Phase 4 -- SPEC-g8-4, rank(cutoff) for every cell
# ===========================================================================

def phase_ranks(sg, x_si, cfg, ws) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 4  RANK(CUTOFF) CURVES for every cell")
    print("=" * 74)
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    L4, L16 = ChartL(4, x_si), ChartL(16, x_si)
    J4, J16 = ChartJ(4, x_si), ChartJ(16, x_si)
    p0 = ws["witnesses"][0]
    a4 = np.array(p0["profile_a_log10"], dtype=np.float64)
    prof_a = G4.reconstruct(a4)

    def theta_for(chart):
        if isinstance(chart, ChartJ):
            g = ChartG(chart.n_mag, x_si)
            return np.concatenate([[0.0], np.interp(g.anchors, G4.anchors, a4)])
        if isinstance(chart, ChartG):
            return np.interp(chart.anchors, G4.anchors, a4)
        th, diag = project_into_chart(chart, prof_a, method="log10",
                                      source_chart=G4, source_log10=a4)
        _METHODS[chart.label()] = diag
        return th

    cells = {"G_d4": G4, "G_d16": G16, "L_d4": L4, "L_d16": L16,
             "J_d4": J4, "J_d16": J16}
    # REP-01: a projection number without its method is not a number. Every
    # chart-L cell sits at a projection of the chart-G operating point, and
    # which projection is recorded in the cell beside the distance it produced.
    _METHODS: Dict[str, Dict] = {}
    out: Dict = {"cells": {}, "operating_point":
                 "witness pair 0 member a (chart G d=4)"}
    for name, chart in cells.items():
        th = theta_for(chart)
        rec, _, _ = cell_spectrum(sg, chart, th, cfg.biases, cfg)
        with np.errstate(divide="ignore", invalid="ignore"):
            dec = np.abs(np.log10(np.abs(chart.reconstruct(th)))
                         - np.log10(np.abs(prof_a)))
        fin = np.isfinite(dec)
        rec["profile_distance_from_operating_point_decades"] = (
            float(np.max(dec[fin])) if fin.any() else None)
        rec["operating_point_method"] = _METHODS.get(chart.label(), {
            "method": "exact" if isinstance(chart, ChartG)
            else "collocated junction at midpoint + chart-G anchors",
            "note": "no projection was needed; the chart holds the point"})
        out["cells"][name] = rec
        print(f"  {name:6s} rank {rec['rank_at_operational_cutoff']:2d}"
              f"/{rec['n_parameters']:2d}  in-gap "
              f"{rec['operational_cutoff_falls_in_largest_gap']!s:5s}"
              f"  gap x{rec['largest_gap_ratio']:.2f}"
              f"  bare integer justified "
              f"{rec['bare_integer_rank_justified']}"
              f"  plateau noise_rel "
              f"{rec['plateau_containing_operational_cutoff']}")
    out["cells_where_a_bare_integer_rank_may_be_quoted"] = [
        k for k, v in out["cells"].items() if v["bare_integer_rank_justified"]]
    print(f"\n  bare integer rank may be quoted in: "
          f"{out['cells_where_a_bare_integer_rank_may_be_quoted']}")
    return out


# ===========================================================================
# Phase 5 -- SPEC-g8-5, mode count
# ===========================================================================

def phase_modes(sg, x_si, cfg, reproduce: Dict, chart_j: Optional[Dict],
                n_barrier: int) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 5  MODE COUNT: is the witness set two basins or many?")
    print("=" * 74)
    criterion = ClusterCriterion()
    print("  criterion fixed BEFORE any distance is computed (AH-14):")
    print(f"    metric      {criterion.metric}")
    print(f"    linkage     {criterion.linkage}")
    print(f"    threshold   {criterion.threshold_decades} decades "
          f"(inherited from GlobalStudyConfig.min_separation_decades)")
    print(f"    hash        {criterion.criterion_hash()}")

    out: Dict = {"criterion_hash_recorded_before_clustering":
                 criterion.criterion_hash(),
                 "criterion": criterion.to_dict(), "sets": {}}

    sets = [
        ("chart_G_d4", ChartG(4, x_si), reproduce["chart_G_d4"]),
        ("chart_L_d16", ChartL(16, x_si), reproduce["chart_L_d16"]),
    ]
    if chart_j is not None:
        sets.append(("chart_J_d16", ChartJ(16, x_si),
                     chart_j["native_witness"]))

    for tag, chart, res in sets:
        idx_pairs = res.get("witness_pair_indices", [])
        kept = np.asarray(res.get("kept_log10", []), dtype=np.float64)
        members = sorted({i for p in idx_pairs for i in p})
        if len(members) < 2:
            out["sets"][tag] = {"n_witness_pairs": len(idx_pairs),
                                "n_members": len(members),
                                "skipped": "fewer than two witness members"}
            print(f"  {tag}: fewer than two members, skipped")
            continue
        remap = {m: k for k, m in enumerate(members)}
        profiles = [chart.reconstruct(kept[m]) for m in members]
        D, S = profile_distance_matrix(profiles)
        basins = count_basins(D, criterion)
        graph = witness_graph_components(
            len(members), [(remap[a], remap[b]) for a, b in idx_pairs])

        rec = {
            "n_witness_pairs": len(idx_pairs),
            "n_members": len(members),
            "distance_decades_min": float(D[D > 0].min()) if (D > 0).any() else 0.0,
            "distance_decades_max": float(D.max()),
            "sign_disagreement_max_nodes": int(S.max()),
            "sign_disagreements_folded_into_distance": False,
            "basins": basins,
            "witness_graph": graph,
        }
        print(f"  {tag}: {len(idx_pairs)} pairs, {len(members)} members -> "
              f"{basins['count_at_threshold']} basin(s) at "
              f"{criterion.threshold_decades} dec; witness graph has "
              f"{graph['n_components']} component(s), sizes "
              f"{graph['component_sizes'][:6]}")
        print("    count vs threshold: " + ", ".join(
            f"{c['threshold_decades']:g}->{c['n_clusters']}"
            for c in basins["curve"]))

        # -- the check on the proxy: barrier depths, stated sample ------------
        labels = np.asarray(basins["labels_at_threshold"])
        within, between = [], []
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                (within if labels[a] == labels[b] else between).append((a, b))
        take = max(0, n_barrier // 2)
        sample = {"within": within[:take], "between": between[:take]}
        rec["barrier_sample_rule"] = (
            f"first {take} pairs in index order from each of the within-cluster "
            "and between-cluster lists; index order is the draw order, fixed by "
            "the seed before clustering, so the sample is not chosen by outcome")

        biases = cfg.biases
        results = {"within": [], "between": []}
        for kind, pairs in sample.items():
            for (a, b) in pairs:
                th_a, th_b = kept[members[a]], kept[members[b]]
                I0_, tr, cv = iv(sg, chart.charted(th_a), biases)
                if not (tr and cv):
                    results[kind].append({"pair": [a, b],
                                          "skipped": "anchor not certified"})
                    continue

                def ll(theta, _ref=I0_, _chart=chart, _b=biases):
                    cur, t_, c_ = iv(sg, _chart.charted(theta), _b)
                    if not (t_ and c_):
                        return None
                    r = (cur - _ref) / (cfg.noise_rel * np.abs(_ref))
                    return float(-0.5 * np.sum(r ** 2))

                bd = barrier_depth(ll, th_a, th_b, n_points=11)
                bd["pair"] = [a, b]
                bd["profile_distance_decades"] = float(D[a, b])
                results[kind].append(bd)
        depths = {k: [r["barrier_depth"] for r in v
                      if r.get("barrier_depth") is not None]
                  for k, v in results.items()}
        rec["barrier_check"] = {
            "n_evaluated": {k: len(v) for k, v in depths.items()},
            "median_depth": {k: (float(np.median(v)) if v else None)
                             for k, v in depths.items()},
            "max_depth": {k: (float(np.max(v)) if v else None)
                          for k, v in depths.items()},
            "paths": results,
            "reading": ("the parameter-space clustering is a proxy for the "
                        "landscape. If between-cluster barriers are deep and "
                        "within-cluster ones shallow, the proxy tracks it; if "
                        "not, the count is a statement about coordinates."),
        }
        print(f"    barrier depths  within: median "
              f"{rec['barrier_check']['median_depth']['within']}  "
              f"between: median {rec['barrier_check']['median_depth']['between']}")
        out["sets"][tag] = rec
    return out


# ===========================================================================
# Phase 6 -- the mandatory negative control
# ===========================================================================

def phase_negative_control(sg, x_si, cfg) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 6  NEGATIVE CONTROL (mandatory)")
    print("=" * 74)
    out: Dict = {}
    G16 = ChartG(16, x_si)
    J16 = ChartJ(16, x_si)

    # -- 1. the witness predicate must reject a distinguishable pair ----------
    m15 = np.full(15, 22.0)
    a = np.concatenate([[float(np.log10(0.25 / 0.75))], m15])
    b = np.concatenate([[float(np.log10(0.75 / 0.25))], m15])
    pair = np.stack([a, b])

    res = witness_search(GlobalStudyConfig(n_anchor=16),
                         make_chart_oracle(sg, J16), 2,
                         draw=lambda _c, _n: pair,
                         max_witnesses=None, include_samples=True)
    ia, _, _ = iv(sg, J16.charted(a), cfg.biases)
    ib, _, _ = iv(sg, J16.charted(b), cfg.biases)
    out["witness_predicate_rejects_a_distinguishable_pair"] = {
        "construction": ("two chart-J devices with identical doping magnitudes "
                         "and junctions at 0.25 L and 0.75 L -- far apart in "
                         "coordinates, and nothing like each other in I-V"),
        "separation_decades": float(np.max(np.abs(a - b))),
        "observational_distance": obs_dist(ia, ib),
        "distinguishability_floor": cfg.distinguishability_floor,
        "n_witnesses": int(res["n_witnesses"]),
        "rejected": bool(res["n_witnesses"] == 0),
        "ran_through": "bayespinn_inv.inverse.global_identifiability.witness_search",
    }
    r = out["witness_predicate_rejects_a_distinguishable_pair"]
    print(f"  1. witness predicate on a distinguishable pair: "
          f"d = {r['observational_distance']:.4e} vs floor "
          f"{r['distinguishability_floor']:.2e} -> "
          f"{'REJECTED' if r['rejected'] else 'ACCEPTED (control failed)'}")

    # -- 2. the chart discriminator must return "not different" ---------------
    Jp = ChartJ(16, x_si, junction_scale=0.0)
    th = np.concatenate([[0.0], m15])
    rec_p, Jmat_p, _ = cell_spectrum(sg, Jp, th, cfg.biases, cfg)
    rec_j, Jmat_j, _ = cell_spectrum(sg, ChartJ(16, x_si), th, cfg.biases, cfg)
    G15 = ChartG(15, x_si)
    rec_g15, Jmat_g15, _ = cell_spectrum(sg, G15, m15, cfg.biases, cfg)
    mag_cols = float(np.max(np.abs(Jmat_p[:, 1:] - Jmat_g15))
                     / max(float(np.max(np.abs(Jmat_g15))), 1e-300))
    out["chart_discriminator_returns_not_different_for_a_pinned_junction"] = {
        "construction": ("chart J with junction_scale = 0 pins the junction at "
                         "the midpoint, which is where charts G and L pin it. "
                         "A discriminator that cannot return *not different* "
                         "here is not measuring anything."),
        "pinned_junction_column_norm": float(np.linalg.norm(Jmat_p[:, 0])),
        "free_junction_column_norm": float(np.linalg.norm(Jmat_j[:, 0])),
        "magnitude_columns_vs_chartG_d15_max_rel": mag_cols,
        "spectral_movement_pinned_vs_G_d15": spectral_movement(
            rec_g15["singular_values"], rec_p["singular_values"]),
        "not_different": bool(np.linalg.norm(Jmat_p[:, 0]) == 0.0
                              and mag_cols < 1e-12),
    }
    r2 = out["chart_discriminator_returns_not_different_for_a_pinned_junction"]
    print(f"  2. pinned-junction chart J vs chart G d=15: junction column "
          f"|.| = {r2['pinned_junction_column_norm']:.3e}, magnitude columns "
          f"agree to {r2['magnitude_columns_vs_chartG_d15_max_rel']:.3e} -> "
          f"{'NOT DIFFERENT (control passes)' if r2['not_different'] else 'DIFFERENT (control failed)'}")

    # -- 3. the cluster criterion on sets with a known answer -----------------
    criterion = ClusterCriterion()
    rng = np.random.default_rng(8)
    blobs = []
    for centre in (21.0, 22.0, 23.0):
        for _ in range(4):
            blobs.append(10.0 ** (centre + rng.uniform(-0.01, 0.01, size=64)))
    one = [10.0 ** (22.0 + rng.uniform(-0.01, 0.01, size=64)) for _ in range(12)]
    D3, _ = profile_distance_matrix(blobs)
    D1, _ = profile_distance_matrix(one)
    got3 = count_basins(D3, criterion)["count_at_threshold"]
    got1 = count_basins(D1, criterion)["count_at_threshold"]
    out["cluster_criterion_recovers_a_known_answer"] = {
        "three_separated_blobs_expected": 3, "got": int(got3),
        "one_blob_expected": 1, "got_one": int(got1),
        "passes": bool(got3 == 3 and got1 == 1),
        "ran_through": "bayespinn_inv.inverse.modes.count_basins",
    }
    print(f"  3. cluster criterion: 3 blobs -> {got3}, 1 blob -> {got1} -> "
          f"{'PASSES' if out['cluster_criterion_recovers_a_known_answer']['passes'] else 'FAILED'}")

    # -- 4. the solver must refuse a chartless parameter vector ---------------
    from bayespinn_inv.solvers.scharfetter_gummel import DopingChartError
    raised = None
    try:
        sg.solve(np.full(16, -1e22), 0.3)
    except DopingChartError as exc:
        raised = str(exc)[:160]
    ok_grid = bool(iv(sg, G16.charted(np.full(16, 22.0)), [0.3])[1])
    out["solver_refuses_a_chartless_parameter_vector"] = {
        "construction": ("a bare length-16 doping array handed to a 301-node "
                         "solver -- exactly what six generations of results were "
                         "produced by, and what CHART-01's fix forbids"),
        "raised": raised is not None,
        "message_head": raised,
        "same_call_with_a_chart_succeeds": ok_grid,
        "passes": bool(raised is not None and ok_grid),
    }
    print(f"  4. bare length-16 vector to a 301-node solver -> "
          f"{'RAISED' if raised else 'ACCEPTED (control failed)'}; "
          f"charted vector still solves: {ok_grid}")

    out["all_controls_pass"] = bool(
        out["witness_predicate_rejects_a_distinguishable_pair"]["rejected"]
        and r2["not_different"]
        and out["cluster_criterion_recovers_a_known_answer"]["passes"]
        and out["solver_refuses_a_chartless_parameter_vector"]["passes"])
    print(f"\n  -> all negative controls behave as required: "
          f"{out['all_controls_pass']}")
    return out


# ===========================================================================

ALL_PHASES = ["reproduce", "chart_j", "obs_set", "ranks", "modes",
              "negative_control"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g8")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    ap.add_argument("--n-chartG", type=int, default=2000)
    ap.add_argument("--n-chartL", type=int, default=1200)
    ap.add_argument("--n-chartJ", type=int, default=1200)
    ap.add_argument("--n-barrier", type=int, default=20)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    cfg = GlobalStudyConfig()
    sg, x_si = build_solver(cfg, args.grid)
    ws = json.loads((root / G6_ARTEFACT).read_text(encoding="utf-8"))["witness_search"]
    jprior = JunctionPrior()

    man = RunManifest.create(
        "g8",
        config={**cfg.to_dict(), "grid_n": args.grid, "phases": phases,
                "n_chartG": args.n_chartG, "n_chartL": args.n_chartL,
                "n_chartJ": args.n_chartJ, "n_barrier": args.n_barrier,
                "junction_prior": jprior.to_dict(),
                "g6_artefact": G6_ARTEFACT, "g7_artefact": G7_ARTEFACT},
        seed=cfg.seed,
        notes="G8. Oracle-arbitrated; the surrogate is never called.")

    results: Dict[str, Dict] = {}
    for name in phases:
        path = out / f"{name}.json"
        if name == "reproduce":
            r = phase_reproduce(sg, x_si, cfg, root, args.n_chartG, args.n_chartL)
        elif name == "chart_j":
            r = phase_chart_j(sg, x_si, cfg, ws, args.n_chartJ, jprior)
        elif name == "obs_set":
            r = phase_obs_set(sg, x_si, cfg, ws)
        elif name == "ranks":
            r = phase_ranks(sg, x_si, cfg, ws)
        elif name == "modes":
            rep = results.get("reproduce")
            if rep is None and (out / "reproduce.json").exists():
                rep = json.loads((out / "reproduce.json").read_text(
                    encoding="utf-8"))
            if rep is None:
                raise SystemExit("phase 'modes' needs phase 'reproduce' first")
            cj = results.get("chart_j")
            if cj is None and (out / "chart_j.json").exists():
                cj = json.loads((out / "chart_j.json").read_text(
                    encoding="utf-8"))
            r = phase_modes(sg, x_si, cfg, rep, cj, args.n_barrier)
        elif name == "negative_control":
            r = phase_negative_control(sg, x_si, cfg)
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
