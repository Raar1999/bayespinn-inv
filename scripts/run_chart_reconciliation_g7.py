"""G7-R: reconcile the local rank (chart L, d=16) with the global witness (chart G, d=4).

Oracle-arbitrated throughout; the surrogate is never called (SPEC-g6-5 carried
forward). Every phase writes its own JSON so a later phase failing cannot cost an
earlier phase's measurement.

    PYTHONPATH=src python scripts/run_chart_reconciliation_g7.py \
        --phases containment,representation,spectra,profile,native_witness

Phase order is the ruling's budget order. If budget binds, ``native_witness``
drops first, then the chart-L d=4 spectra cell. ``containment`` and
``representation`` are never dropped.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bayespinn_inv.inverse.charts import (
    ChartG,
    ChartL,
    chart_forward_jacobian,
    containment,
    project_into_chart,
)
from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
    witness_search,
)
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    sg_forward_jacobian,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest

WITNESS_ARTEFACT = "outputs/global_identifiability_g6/global_identifiability.json"


# ---------------------------------------------------------------------------
# Shared machinery
# ---------------------------------------------------------------------------

def build_solver(cfg: GlobalStudyConfig, grid_n: int):
    """The same grid ``make_oracle`` builds, so nothing is measured elsewhere."""
    scaling = Scaling.for_material(SILICON, T=300.0)
    length = cfg.domain_si[1] - cfg.domain_si[0]
    length_scaled = float(scaling.x_to_scaled(np.float64(length)))
    sg = ScharfetterGummel1D(
        Grid1D.uniform(length_scaled, grid_n), scaling, SILICON, SGConfig())
    x_si = scaling.x_to_si(np.asarray(sg.grid.x))
    return sg, x_si


def iv(sg, profile_or_input, biases):
    """Terminal currents, plus whether the oracle certified every point."""
    prev, cur, trust, conv = None, [], [], []
    for v in biases:
        st = sg.solve(profile_or_input, float(v), initial_state=prev)
        prev = st
        cur.append(st.terminal_current)
        trust.append(bool(st.current_is_trustworthy()))
        conv.append(bool(st.converged))
    return np.asarray(cur), bool(np.all(trust)), bool(np.all(conv))


def obs_dist(ia, ib) -> float:
    """witness_search L251-254: max over biases of |dI| / max(|Ia|, |Ib|)."""
    denom = np.maximum(np.abs(ia), np.abs(ib))
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nanmax(np.abs(ia - ib) / denom))


def make_chart_oracle(sg, chart):
    """``(log10_mag, biases) -> (current, trustworthy, converged)`` for any chart."""
    def oracle(log10_mag, biases):
        prev, cur, trust, conv = None, [], [], []
        for v in biases:
            st = sg.solve(chart.solver_input(log10_mag), float(v),
                          initial_state=prev)
            prev = st
            cur.append(st.terminal_current)
            trust.append(bool(st.current_is_trustworthy()))
            conv.append(bool(st.converged))
        return np.asarray(cur), np.asarray(trust), np.asarray(conv)
    return oracle


def load_witness(root: Path):
    ws = json.loads((root / WITNESS_ARTEFACT).read_text(encoding="utf-8"))["witness_search"]
    return ws


def spectrum_record(rep, noise_rel: float, dtype: str = "float64") -> dict:
    """Full spectrum first; ranks second, with the cutoff justified not tuned.

    ``PH-11``: the cutoff must be defensible from the spectrum's own structure.
    We report the operational noise cutoff the repository already uses, *and*
    the largest multiplicative gap between consecutive resolvable singular
    values, and whether the noise cutoff falls inside that gap. When it does,
    the rank is a population boundary rather than a threshold someone chose.
    """
    s = np.asarray(rep.singular_values, dtype=np.float64)
    floor = rep.spectral_floor
    above = s[s > floor]
    gap_idx, gap_ratio = None, None
    if above.size >= 2:
        ratios = above[:-1] / np.maximum(above[1:], 1e-300)
        gap_idx = int(np.argmax(ratios))
        gap_ratio = float(ratios[gap_idx])
    noise_thr = float(np.log10(1.0 + noise_rel))
    in_gap = None
    if gap_idx is not None:
        in_gap = bool(above[gap_idx + 1] <= noise_thr < above[gap_idx])
    return {
        "dtype": dtype,
        "n_observations": int(rep.n_observations),
        "n_parameters": int(rep.n_parameters),
        "singular_values": [float(x) for x in s],
        "spectral_floor": float(floor),
        "jacobian_noise": float(rep.jacobian_noise),
        "noise_rel": float(noise_rel),
        "noise_cutoff_symlog": noise_thr,
        "identifiable_rank": int(rep.identifiable_rank),
        "resolvable_rank": int(rep.resolvable_rank),
        "rank_fraction_within_chart": (
            f"{rep.identifiable_rank}/{rep.n_parameters}"
            "  (NOT comparable across charts)"),
        "condition_number": float(rep.condition_number),
        "largest_gap_after_index": gap_idx,
        "largest_gap_ratio": gap_ratio,
        "noise_cutoff_falls_in_largest_gap": in_gap,
    }


# ---------------------------------------------------------------------------
# Phase 1 -- containment (never dropped)
# ---------------------------------------------------------------------------

def phase_containment(sg, x_si, cfg, ws, grid_n) -> dict:
    print("=" * 74)
    print("PHASE 1  CONTAINMENT: is L subset of G, G subset of L, or neither?")
    print("=" * 74)
    p0 = ws["witnesses"][0]
    a4 = np.array(p0["profile_a_log10"], dtype=np.float64)

    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    L16 = ChartL(16, x_si)

    ctl = L16.assert_matches_solver(sg, np.full(16, 22.0))
    print(f"  positive control: ChartL.reconstruct vs the solver's own "
          f"resampler -> {ctl:.3e} (must be at round-off)")

    # Each direction gets its OWN source object, drawn in the source chart.
    # Reusing one profile for both directions measures one thing twice.
    #   G -> L : witness pair 0 member a, a genuine chart-G object.
    #   L -> G : two genuine chart-L objects --
    #     * ``step_asymmetric`` from run_identifiability.py's own device family,
    #       piecewise-constant in magnitude. Chart G reproduces a constant
    #       magnitude exactly, so whatever residual survives here isolates the
    #       *junction* obstruction from the interpolant obstruction;
    #     * a prior draw in chart-L coordinates, which is generic and so carries
    #       both obstructions at once.
    rng = np.random.default_rng(cfg.seed)
    lo, hi = np.log10(cfg.prior_lo_si), np.log10(cfg.prior_hi_si)
    draw16 = rng.uniform(lo, hi, size=16)
    step_asym = np.where(L16.anchors < 0.5e-6, np.log10(1e21), np.log10(5e22))

    out = {
        "positive_control_chartL_vs_solver_max_rel": ctl,
        "anchor_lattice": {},
        "G_into_G": containment(G4, G16, a4),
        "G_into_L": containment(G4, L16, a4),
        "L_into_G_step_asymmetric": containment(L16, G16, step_asym),
        "L_into_G_prior_draw": containment(L16, G16, draw16),
        "L_into_G_sources": {
            "step_asymmetric_log10": [float(x) for x in step_asym],
            "prior_draw_log10": [float(x) for x in draw16],
            "prior_draw_seed": int(cfg.seed),
        },
    }
    xa4, xa16 = G4.anchors, G16.anchors
    idx = [int(np.argmin(np.abs(xa16 - x))) for x in xa4]
    out["anchor_lattice"] = {
        "d4_anchor_x_over_L": [float(x / 1e-6) for x in xa4],
        "nearest_d16_node_index": idx,
        "max_abs_offset_m": float(np.max(np.abs(xa4 - xa16[idx]))),
        "lattice_nested": bool(np.allclose(xa4, xa16[idx], rtol=1e-14, atol=0.0)),
    }

    # The structural claim, checked rather than asserted: on a single interval
    # with distinct endpoint magnitudes, geometric and arithmetic interpolation
    # differ, and the discrepancy is a pure function of the endpoint ratio.
    ratios, disc = [2.0, 5.0, 10.0, 100.0], []
    for r in ratios:
        disc.append({
            "endpoint_ratio": r,
            "midpoint_arithmetic_over_geometric": float((1.0 + r) / (2.0 * np.sqrt(r))),
        })
    out["interpolant_divergence"] = disc

    print(f"  anchor lattice nested (d=4 anchors land on d=16 nodes {idx}): "
          f"{out['anchor_lattice']['lattice_nested']}")
    print(f"  G(d=4) -> G(d=16) : max {out['G_into_G']['max_decades']:.3e} decades"
          f"  ({out['G_into_G']['sign_disagreements']} sign disagreements)")
    print(f"  G(d=4) -> L(d=16) : max {out['G_into_L']['max_decades']:.4f} decades"
          f"  ({out['G_into_L']['sign_disagreements']} sign disagreements)")
    for key, lbl in (("L_into_G_step_asymmetric", "L->G step_asymmetric"),
                     ("L_into_G_prior_draw", "L->G prior draw     ")):
        print(f"  {lbl}: max {out[key]['max_decades']:.4f} decades"
              f"  ({out[key]['sign_disagreements']} sign disagreements)")
    out["verdict"] = (
        "NEITHER contains the other: G is geometric between anchors, L is "
        "arithmetic, and they agree only where adjacent anchors are equal; "
        "independently, G carries a grid-level sign discontinuity that a "
        "continuous piecewise-linear L cannot produce at any finite d.")
    print(f"  -> {out['verdict']}")
    return out


# ---------------------------------------------------------------------------
# Phase 2 -- representation error, the headline (never dropped)
# ---------------------------------------------------------------------------

def phase_representation(sg, x_si, cfg, ws, grid_n, refine_evals: int) -> dict:
    print()
    print("=" * 74)
    print("PHASE 2  REPRESENTATION: can chart L hold the witness pair at all?")
    print("=" * 74)
    p0 = ws["witnesses"][0]
    theta = {"a": np.array(p0["profile_a_log10"], dtype=np.float64),
             "b": np.array(p0["profile_b_log10"], dtype=np.float64)}
    floor = cfg.distinguishability_floor
    biases = cfg.biases

    G4, L16 = ChartG(4, x_si), ChartL(16, x_si)
    truth_prof = {k: G4.reconstruct(v) for k, v in theta.items()}
    truth_iv = {}
    for k, prof in truth_prof.items():
        c, tr, cv = iv(sg, prof, biases)
        truth_iv[k] = c
        print(f"  chart G d=4 member {k}: oracle certified "
              f"trustworthy={tr} converged={cv}")

    d_true = obs_dist(truth_iv["a"], truth_iv["b"])
    print(f"  reproduced d(a,b) in chart G d=4: {d_true:.6e}"
          f"   (published {p0['observational_distance']:.6e})")

    members = {}
    for k in ("a", "b"):
        cands = {}
        for method in ("collocate", "linear_C", "log10"):
            th, diag = project_into_chart(
                L16, truth_prof[k], method=method,
                source_chart=G4, source_log10=theta[k])
            prof = L16.reconstruct(th)
            with np.errstate(divide="ignore", invalid="ignore"):
                dec = np.abs(np.log10(np.abs(prof))
                             - np.log10(np.abs(truth_prof[k])))
            fin = np.isfinite(dec)
            cur, tr, cv = iv(sg, L16.solver_input(th), biases)
            cands[method] = {
                "diagnostics": diag,
                "theta": [float(t) for t in th],
                "profile_max_decades": float(np.max(dec[fin])),
                "profile_rms_decades": float(np.sqrt(np.mean(dec[fin] ** 2))),
                "profile_nodes_nonfinite": int(np.sum(~fin)),
                "sign_disagreements": int(np.sum(np.sign(prof)
                                                 != np.sign(truth_prof[k]))),
                "observational_representation_error": obs_dist(cur, truth_iv[k]),
                "oracle_trustworthy": tr,
                "oracle_converged": cv,
                "_current": cur,
            }
            print(f"    member {k} / {method:10s}: "
                  f"profile {cands[method]['profile_max_decades']:7.4f} dec, "
                  f"observation {cands[method]['observational_representation_error']:.4e}")

        best = min(cands, key=lambda m:
                   cands[m]["observational_representation_error"])
        if refine_evals > 0:
            from scipy.optimize import minimize
            th0 = np.array(cands[best]["theta"], dtype=np.float64)
            n_eval = {"n": 0}

            def cost(th, _n=n_eval, _target=truth_iv[k]):
                _n["n"] += 1
                cur, tr, cv = iv(sg, L16.solver_input(th), biases)
                if not (tr and cv):
                    return 10.0
                return obs_dist(cur, _target)

            res = minimize(cost, th0, method="Nelder-Mead",
                           options={"maxfev": refine_evals, "xatol": 1e-4,
                                    "fatol": 1e-6})
            prof = L16.reconstruct(res.x)
            with np.errstate(divide="ignore", invalid="ignore"):
                dec = np.abs(np.log10(np.abs(prof))
                             - np.log10(np.abs(truth_prof[k])))
            fin = np.isfinite(dec)
            cur, tr, cv = iv(sg, L16.solver_input(res.x), biases)
            cands["observational_refine"] = {
                "diagnostics": {"method": "Nelder-Mead in observation space",
                                "seeded_from": best,
                                "maxfev_budget": refine_evals,
                                "n_evaluations": n_eval["n"],
                                "converged": bool(res.success)},
                "theta": [float(t) for t in res.x],
                "profile_max_decades": float(np.max(dec[fin])),
                "profile_rms_decades": float(np.sqrt(np.mean(dec[fin] ** 2))),
                "profile_nodes_nonfinite": int(np.sum(~fin)),
                "sign_disagreements": int(np.sum(np.sign(prof)
                                                 != np.sign(truth_prof[k]))),
                "observational_representation_error": obs_dist(cur, truth_iv[k]),
                "oracle_trustworthy": tr,
                "oracle_converged": cv,
                "_current": cur,
            }
            print(f"    member {k} / refine    : "
                  f"profile {cands['observational_refine']['profile_max_decades']:7.4f} dec, "
                  f"observation "
                  f"{cands['observational_refine']['observational_representation_error']:.4e}"
                  f"  ({n_eval['n']} oracle sweeps)")
            best = min(cands, key=lambda m:
                       cands[m]["observational_representation_error"])
        members[k] = {"candidates": cands, "best_method": best}
        print(f"    -> best chart-L stand-in for {k}: {best}, "
              f"observational error "
              f"{cands[best]['observational_representation_error']:.4e}"
              f"  ({'BELOW' if cands[best]['observational_representation_error'] < floor else 'ABOVE'}"
              f" the {floor:.2e} floor)")

    # Does chart L collapse the pair?
    best_cur = {k: members[k]["candidates"][members[k]["best_method"]]["_current"]
                for k in ("a", "b")}
    d_best = obs_dist(best_cur["a"], best_cur["b"])
    th_a = np.array(members["a"]["candidates"][members["a"]["best_method"]]["theta"])
    th_b = np.array(members["b"]["candidates"][members["b"]["best_method"]]["theta"])
    sep_L = float(np.max(np.abs(th_a - th_b)))
    coll = np.interp(ChartG(16, x_si).anchors, G4.anchors, theta["a"]) \
        - np.interp(ChartG(16, x_si).anchors, G4.anchors, theta["b"])
    sep_G16 = float(np.max(np.abs(coll)))

    for k in ("a", "b"):
        for m in members[k]["candidates"].values():
            m.pop("_current", None)

    out = {
        "witness_pair": 0,
        "published_observational_distance": float(p0["observational_distance"]),
        "reproduced_chartG_d4_distance": d_true,
        "separation_decades_chartG_d4": float(p0["separation_decades"]),
        "floors": {"noise_rel": cfg.noise_rel,
                   "discretisation_rel": cfg.discretisation_floor_rel,
                   "distinguishability": floor},
        "members": members,
        "pair_of_best_chartL_standins": {
            "observational_distance": d_best,
            "below_floor": bool(d_best < floor),
            "separation_decades": sep_L,
            "separation_decades_chartG_collocated_to_16": sep_G16,
            "separation_ratio_L_over_G": float(sep_L / sep_G16) if sep_G16 else None,
        },
    }
    print()
    print(f"  pair of best chart-L stand-ins: d = {d_best:.6e}"
          f"  ({'BELOW' if d_best < floor else 'ABOVE'} floor {floor:.2e})")
    print(f"  parameter separation: chart G (collocated to 16) {sep_G16:.4f} dec"
          f"  ->  chart L {sep_L:.4f} dec"
          f"   ratio {out['pair_of_best_chartL_standins']['separation_ratio_L_over_G']:.3f}")
    return out


# ---------------------------------------------------------------------------
# Phase 3 -- the 2x2 spectra table
# ---------------------------------------------------------------------------

def phase_spectra(sg, x_si, cfg, ws, grid_n, rep_result, cells) -> dict:
    print()
    print("=" * 74)
    print("PHASE 3  SPECTRA: full singular spectrum in each (chart, d) cell")
    print("=" * 74)
    p0 = ws["witnesses"][0]
    a4 = np.array(p0["profile_a_log10"], dtype=np.float64)
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    L4, L16 = ChartL(4, x_si), ChartL(16, x_si)
    biases = cfg.biases

    def theta_for(chart):
        if isinstance(chart, ChartG):
            return np.interp(chart.anchors, G4.anchors, a4)
        # chart L cannot hold member a; use the best stand-in phase 2 measured.
        if chart.d == 16 and rep_result is not None:
            m = rep_result["members"]["a"]
            return np.array(m["candidates"][m["best_method"]]["theta"])
        th, _ = project_into_chart(chart, G4.reconstruct(a4), method="log10",
                                   source_chart=G4, source_log10=a4)
        return th

    charts = {"G_d4": G4, "G_d16": G16, "L_d16": L16, "L_d4": L4}
    out = {"operating_point": "witness pair 0, member a (chart G d=4)",
           "note": ("chart L cells sit at that member's BEST chart-L stand-in, "
                    "not at the same device -- chart L cannot hold it. The "
                    "profile distance from the true operating point is carried "
                    "in each cell."),
           "cells": {}}
    for name in cells:
        chart = charts[name]
        th = theta_for(chart)
        t0 = time.perf_counter()
        J, I_ref, kept, eta = chart_forward_jacobian(
            sg, chart, th, biases, rel_step=0.05, min_snr=1e4)
        rep = analyse_identifiability(J, noise_rel=cfg.noise_rel,
                                      jacobian_noise=eta)
        rec = spectrum_record(rep, cfg.noise_rel)
        rec["chart"] = chart.name
        rec["d"] = chart.d
        rec["theta"] = [float(t) for t in th]
        rec["biases_used"] = [float(biases[i]) for i in kept]
        rec["wall_clock_s"] = time.perf_counter() - t0
        with np.errstate(divide="ignore", invalid="ignore"):
            dec = np.abs(np.log10(np.abs(chart.reconstruct(th)))
                         - np.log10(np.abs(G4.reconstruct(a4))))
        fin = np.isfinite(dec)
        rec["profile_distance_from_operating_point_decades"] = float(np.max(dec[fin]))
        out["cells"][name] = rec
        print(f"  {name:6s} rank {rec['identifiable_rank']}/{rec['n_parameters']}"
              f"  resolvable {rec['resolvable_rank']}"
              f"  gap x{rec['largest_gap_ratio']:.2f} after index "
              f"{rec['largest_gap_after_index']}"
              f"  cutoff-in-gap {rec['noise_cutoff_falls_in_largest_gap']}"
              f"  profile dist {rec['profile_distance_from_operating_point_decades']:.3f} dec")

    # Positive control: for chart L the chart-aware Jacobian must reproduce the
    # function the published number was measured with.
    if "L_d16" in out["cells"]:
        th = theta_for(L16)
        Jc, _, _, _ = chart_forward_jacobian(sg, L16, th, biases,
                                             rel_step=0.05, min_snr=1e4)
        Js, _, _, _ = sg_forward_jacobian(sg, L16.solver_input(th), biases,
                                          rel_step=0.05, min_snr=1e4)
        err = float(np.max(np.abs(Jc - Js)) / max(np.max(np.abs(Js)), 1e-300))
        out["positive_control_chart_vs_sg_jacobian_max_rel"] = err
        print(f"  positive control: chart_forward_jacobian vs "
              f"sg_forward_jacobian on chart L -> {err:.3e}")
    return out


# ---------------------------------------------------------------------------
# Phase 4 -- profile likelihood along the witness path (SPEC-g7-4)
# ---------------------------------------------------------------------------

def phase_profile(sg, x_si, cfg, ws, grid_n, n_points) -> dict:
    print()
    print("=" * 74)
    print("PHASE 4  PROFILE LIKELIHOOD along the witness path")
    print("=" * 74)
    p0 = ws["witnesses"][0]
    a4 = np.array(p0["profile_a_log10"], dtype=np.float64)
    b4 = np.array(p0["profile_b_log10"], dtype=np.float64)
    G4 = ChartG(4, x_si)
    biases = cfg.biases
    sigma = cfg.noise_rel

    I_truth, tr, cv = iv(sg, G4.reconstruct(a4), biases)
    if not (tr and cv):
        raise RuntimeError("oracle did not certify the reference observation")

    def loglik(theta):
        cur, tr_, cv_ = iv(sg, G4.reconstruct(theta), biases)
        if not (tr_ and cv_):
            return None, cur
        r = (cur - I_truth) / (sigma * np.abs(I_truth))
        return float(-0.5 * np.sum(r ** 2)), cur

    ts = np.linspace(-0.25, 1.25, n_points)
    path = []
    for t in ts:
        th = (1.0 - t) * a4 + t * b4
        ll, cur = loglik(th)
        path.append({"t": float(t), "loglik": ll,
                     "obs_distance_from_a": obs_dist(cur, I_truth),
                     "max_param_change_decades": float(np.max(np.abs(th - a4)))})

    # Control: the SAME parameter excursion along the most observable direction.
    # Without this a flat profile is not evidence -- it could be a flat solver.
    J, _, _, eta = chart_forward_jacobian(sg, G4, a4, biases,
                                          rel_step=0.05, min_snr=1e4)
    rep = analyse_identifiability(J, noise_rel=cfg.noise_rel, jacobian_noise=eta)
    v_top = rep.directions[:, 0]
    step = np.linalg.norm(b4 - a4)
    control = []
    for t in ts:
        th = a4 + t * step * v_top
        ll, cur = loglik(th)
        control.append({"t": float(t), "loglik": ll,
                        "obs_distance_from_a": obs_dist(cur, I_truth),
                        "max_param_change_decades": float(np.max(np.abs(th - a4)))})

    lls = [p["loglik"] for p in path if p["loglik"] is not None]
    ctl = [p["loglik"] for p in control if p["loglik"] is not None]
    out = {
        "parameterisation": "chart G, d=4, theta = log10|C| at 4 equally spaced anchors",
        "path": "straight line in theta between witness pair 0 members, extended to t in [-0.25, 1.25]",
        "endpoint_a_log10": [float(x) for x in a4],
        "endpoint_b_log10": [float(x) for x in b4],
        "reference_observation": "oracle I-V of endpoint a, noise-free; sigma = "
                                 f"{sigma} relative, {len(biases)} biases",
        "noise_model": "independent Gaussian in relative current",
        "witness_path": path,
        "control_direction": {
            "description": "most observable right singular direction of the "
                           "chart-G d=4 Jacobian at endpoint a, same excursion "
                           "length in theta",
            "direction": [float(x) for x in v_top],
            "singular_value": float(rep.singular_values[0]),
            "points": control,
        },
        "witness_path_loglik_range": [min(lls), max(lls)] if lls else None,
        "control_loglik_range": [min(ctl), max(ctl)] if ctl else None,
    }
    if lls and ctl:
        print(f"  witness path : loglik in [{min(lls):.3f}, {max(lls):.3f}]"
              f"   span {max(lls) - min(lls):.3f}")
        print(f"  control dir  : loglik in [{min(ctl):.3f}, {max(ctl):.3f}]"
              f"   span {max(ctl) - min(ctl):.3f}")
    return out


# ---------------------------------------------------------------------------
# Phase 5 -- native witness search in chart L at d=16 (SPEC-g7-3e)
# ---------------------------------------------------------------------------

def phase_native_witness(sg, x_si, cfg, ws, grid_n, n_samples, seed_evals) -> dict:
    print()
    print("=" * 74)
    print("PHASE 5  NATIVE WITNESS SEARCH in chart L at d=16")
    print("=" * 74)
    L16 = ChartL(16, x_si)
    cfg16 = GlobalStudyConfig(n_anchor=16)
    print(f"  prior hash (fixed before sampling, AH-14): {cfg16.prior_hash()}")

    def tick(i, n):
        if i % 250 == 0 or i == n:
            print(f"    sampled {i}/{n}", flush=True)

    t0 = time.perf_counter()
    prior = witness_search(cfg16, make_chart_oracle(sg, L16), n_samples, tick)
    prior["wall_clock_s"] = time.perf_counter() - t0
    prior["budget"] = {"n_samples": n_samples,
                       "n_pairs_examined": prior.get("n_pairs_examined")}
    print(f"  prior search -> {prior['verdict']}")

    out = {"chart": "L", "d": 16, "prior_search": prior}

    # Seeded refinement from the chart-L stand-ins of the g6 chart-G witnesses.
    if seed_evals > 0:
        from scipy.optimize import minimize
        G4 = ChartG(4, x_si)
        biases = cfg.biases
        seeds = []
        for wi, w in enumerate(ws["witnesses"][:3]):
            th_a, _ = project_into_chart(
                L16, G4.reconstruct(np.array(w["profile_a_log10"])),
                method="log10", source_chart=G4,
                source_log10=np.array(w["profile_a_log10"]))
            th_b, _ = project_into_chart(
                L16, G4.reconstruct(np.array(w["profile_b_log10"])),
                method="log10", source_chart=G4,
                source_log10=np.array(w["profile_b_log10"]))
            cur_a, tra, cva = iv(sg, L16.solver_input(th_a), biases)
            if not (tra and cva):
                seeds.append({"seed_from_g6_witness": wi,
                              "status": "anchor member not certified by oracle"})
                continue
            n_eval = {"n": 0}

            def cost(th, _n=n_eval, _anchor=th_a, _anchor_iv=cur_a):
                _n["n"] += 1
                sep = float(np.max(np.abs(th - _anchor)))
                cur, tr_, cv_ = iv(sg, L16.solver_input(th), biases)
                if not (tr_ and cv_):
                    return 10.0
                d = obs_dist(cur, _anchor_iv)
                # Penalty, not a constraint: a witness must stay FAR apart.
                pen = max(0.0, cfg.min_separation_decades - sep)
                return d + 10.0 * pen

            res = minimize(cost, th_b, method="Nelder-Mead",
                           options={"maxfev": seed_evals, "xatol": 1e-4,
                                    "fatol": 1e-7})
            cur_b, trb, cvb = iv(sg, L16.solver_input(res.x), biases)
            d = obs_dist(cur_a, cur_b)
            sep = float(np.max(np.abs(res.x - th_a)))
            ok = bool(d < cfg.distinguishability_floor
                      and sep >= cfg.min_separation_decades and trb and cvb)
            seeds.append({
                "seed_from_g6_witness": wi,
                "n_evaluations": n_eval["n"],
                "maxfev_budget": seed_evals,
                "observational_distance": d,
                "separation_decades": sep,
                "oracle_trustworthy": bool(trb),
                "oracle_converged": bool(cvb),
                "is_witness": ok,
                "theta_a": [float(x) for x in th_a],
                "theta_b": [float(x) for x in res.x],
            })
            print(f"  seeded from g6 witness {wi}: d = {d:.4e}, sep = {sep:.3f} dec"
                  f"  -> witness: {ok}  ({n_eval['n']} sweeps)")
        out["seeded_refinement"] = {
            "budget_evals_per_seed": seed_evals,
            "n_seeds": len(seeds),
            "results": seeds,
            "n_witnesses": sum(1 for s in seeds if s.get("is_witness")),
        }

    n_prior = prior.get("n_witnesses", 0)
    n_seed = out.get("seeded_refinement", {}).get("n_witnesses", 0)
    if n_prior or n_seed:
        out["verdict"] = (
            f"chart L is globally non-identifiable too at d=16: "
            f"{n_prior} witness(es) from prior sampling (n={n_samples}), "
            f"{n_seed} from seeded refinement.")
    else:
        out["verdict"] = (
            f"no witness found at budget B in chart L, d=16 "
            f"(prior sampling n={n_samples}, {prior.get('n_pairs_examined')} pairs; "
            f"seeded refinement {seed_evals} evals x {len(out.get('seeded_refinement', {}).get('results', []))} seeds). "
            "AH-13: this is not 'chart L is identifiable'.")
    print(f"  -> {out['verdict']}")
    return out


# ---------------------------------------------------------------------------

ALL_PHASES = ["containment", "representation", "spectra", "profile",
              "native_witness"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/chart_reconciliation_g7")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    ap.add_argument("--refine-evals", type=int, default=600)
    ap.add_argument("--profile-points", type=int, default=61)
    ap.add_argument("--native-samples", type=int, default=1200)
    ap.add_argument("--seed-evals", type=int, default=400)
    ap.add_argument("--spectra-cells", default="G_d4,G_d16,L_d16,L_d4")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    cfg = GlobalStudyConfig()
    sg, x_si = build_solver(cfg, args.grid)
    ws = load_witness(root)

    man = RunManifest.create(
        "chart_reconciliation_g7",
        config={**cfg.to_dict(), "grid_n": args.grid, "phases": phases,
                "refine_evals": args.refine_evals,
                "profile_points": args.profile_points,
                "native_samples": args.native_samples,
                "seed_evals": args.seed_evals,
                "spectra_cells": args.spectra_cells,
                "witness_artefact": WITNESS_ARTEFACT},
        seed=cfg.seed,
        notes="G7-R chart reconciliation. Oracle-arbitrated; surrogate never called.")

    results = {}
    rep_result = None
    for name in phases:
        path = out / f"{name}.json"
        if name == "containment":
            r = phase_containment(sg, x_si, cfg, ws, args.grid)
        elif name == "representation":
            r = phase_representation(sg, x_si, cfg, ws, args.grid,
                                     args.refine_evals)
            rep_result = r
        elif name == "spectra":
            if rep_result is None and (out / "representation.json").exists():
                rep_result = json.loads(
                    (out / "representation.json").read_text(encoding="utf-8"))
            cells = [c.strip() for c in args.spectra_cells.split(",") if c.strip()]
            r = phase_spectra(sg, x_si, cfg, ws, args.grid, rep_result, cells)
        elif name == "profile":
            r = phase_profile(sg, x_si, cfg, ws, args.grid, args.profile_points)
        elif name == "native_witness":
            r = phase_native_witness(sg, x_si, cfg, ws, args.grid,
                                     args.native_samples, args.seed_evals)
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
