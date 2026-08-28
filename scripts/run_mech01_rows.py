"""``MECH-01``, second method: where in the bias sweep the new directions live.

    PYTHONPATH=src python scripts/run_mech01_rows.py --out outputs/g12/mech01_rows

What this is
------------
Generation 10 tested the **column** side of the flattening -- whether the
leading right singular *vector* localises over the doping parameters -- and
falsified it under a criterion hashed before the measurement. One method, one
failure.

This is the **row** side, and it is distinct in kind rather than a second guess
at the same thing. The columns of ``J`` are parameters; the rows are **bias
points**. The left singular vectors say where in the bias sweep a sensitivity
direction lives. The question the operator ruling of 2026-08-28 §5 sets:

    when the window widens and ``sigma_2..sigma_4`` climb, are those directions
    carried by the bias points the widening **adds**, or by bias points that
    were already in the narrow window?

Both outcomes are stated before measuring because both are informative
------------------------------------------------------------------------
``NEW_ROWS``
    ``sigma_2..sigma_4`` are carried by the added biases. Flattening is then
    straightforwardly new independent measurements entering the problem, and
    the mechanism reduces to which transport regimes those biases sample.

``CONDITIONING``
    the new directions are carried across biases already present in the narrow
    window. Widening is then not adding information so much as changing how
    well-conditioned the existing rows are, and the mechanism is about
    collinearity rather than coverage.

Neither is the "good" outcome. :data:`OUTCOMES` is hashed to disk before the
first SVD.

The measure, fixed before the first SVD
---------------------------------------
For a window of width ``w`` the Jacobian ``J(w)`` has one row per certified
bias. Its SVD gives ``U``, whose column ``k`` is the left singular vector of
direction ``k``; ``|U[:, k]|**2`` is a **probability distribution over bias
rows** and sums to one. Define

    ``w_out(k, w)`` = the share of ``|U[:, k]|**2`` on biases lying OUTSIDE the
    reference core window.

The **reference core** is the narrowest window on the axis, 0.10 V about a
0.525 V centre. It is not chosen here: ``SPEC-g9-2`` fixed this axis, its
centre and its widths a generation ago, and the narrowest window is its first
point.

``w_out`` alone is not interpretable, because a wider window simply has more
rows outside the core. Two baselines remove that:

``excess(k, w) = w_out(k, w) - n_out(w) / n_rows(w)``
    against a **uniform** direction, which spreads its weight evenly over rows
    and so scores exactly ``n_out / n_rows``. Positive means the direction
    prefers the added biases.

``excess(k) - excess(1)``
    against ``sigma_1`` **measured on the same matrix**. This is the stronger
    of the two because it cancels the row count, the certification mask and the
    window entirely: both numbers come from one SVD of one ``J``.

The verdict is a **sign**, not a threshold (``PH-11`` has no cutoff to forbid):
``NEW_ROWS`` iff ``mean(excess(2..4)) > excess(1)`` at **every** width wider
than the narrowest, ``CONDITIONING`` iff it is never greater, and ``MIXED``
otherwise, in which case the widths that go each way are named.

Controls
--------
``R1`` reproduction
    every recomputed ``sigma_1..sigma_4`` must reproduce
    ``outputs/g9/rank_obs.json``'s stored ``singular_values``. If the Jacobian
    is not the one generation 9 measured, none of this is about the same
    object.
``N1`` negative
    Haar-random unit directions scored by the same statistic, one per width.
    The width axis carries no information about them by construction, so a
    statistic that reports a trend there is reporting its own gullibility --
    generation 10's control, reused because it caught nothing then either and
    that is what a control is for.
``P1`` positive
    a **planted** Jacobian whose trailing directions live entirely on the added
    rows. It must be classified ``NEW_ROWS``. Without it a verdict of
    ``CONDITIONING`` could mean the statistic cannot see concentration at all.
``C1`` the axis that does not move the rank
    the spacing axis, where ``SPEC-g9-2`` measured the rank as fixed. The same
    statistic is computed along it. A row-side signal that appears just as
    strongly along the axis where nothing happens is not about width.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_g9 import (
    ALPHAS,
    WIDTH_CENTRE,
    WIDTHS,
    _spacing,
    build_solver,
    cell_spectrum,
    window_biases,
)

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig

ROOT = Path(__file__).resolve().parents[1]
G9_RANK_OBS = "outputs/g9/rank_obs.json"

#: Directions the rank is actually made of. The close stopped its claims at
#: four because sigma_5 sits at or below the estimator's spectral floor in
#: four of eighteen width cells; that limit is inherited, not re-litigated.
INDICES = (1, 2, 3, 4)


@dataclass(frozen=True)
class RowMeasure:
    """The statistic, hashed before the first SVD."""

    quantity: str = (
        "w_out(k, w): the share of |U[:, k]|**2 lying on bias rows OUTSIDE the "
        "reference core window, where U is the left singular basis of the "
        "chart-G d=16 Jacobian at window width w")
    reference_core_V: Tuple[float, float] = (
        WIDTH_CENTRE - WIDTHS[0] / 2.0, WIDTH_CENTRE + WIDTHS[0] / 2.0)
    reference_core_is_not_chosen_here: str = (
        "it is the narrowest window of SPEC-g9-2's width axis, whose centre, "
        "widths and bias count were fixed at generation 9. Choosing a core "
        "here would be choosing the answer")
    baseline_uniform: str = (
        "excess(k, w) = w_out(k, w) - n_out(w)/n_rows(w). A direction that "
        "spreads evenly over rows scores exactly n_out/n_rows, so excess is "
        "signed against 'no preference'")
    baseline_head: str = (
        "excess(k, w) - excess(1, w). The stronger baseline: both terms come "
        "from one SVD of one J, so the row count, the certification mask and "
        "the window all cancel")
    indices: Tuple[int, ...] = INDICES
    why_four: str = (
        "the close stopped at sigma_1..sigma_4 because sigma_5 sits at or "
        "below the estimator's spectral floor in 4 of 18 width cells. "
        "Inherited, not re-litigated")
    verdict_is_a_sign: str = (
        "NEW_ROWS iff mean(excess(2..4)) > excess(1) at EVERY width wider than "
        "the narrowest; CONDITIONING iff never; MIXED otherwise with the "
        "widths named. A sign, so PH-11 has no cutoff to forbid")
    rows_used_may_vary: str = (
        "SNR certification drops rows at some widths -- 16 at 0.10 V and 15 at "
        "0.75 V at the generation-8 device. This is why every statistic is "
        "normalised per matrix and why the head baseline is the one the "
        "verdict rests on; rows_used is reported at every cell")

    def measure_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["measure_hash"] = self.measure_hash()
        return out


OUTCOMES: Dict[str, str] = {
    "NEW_ROWS": (
        "sigma_2..sigma_4 are carried by the bias points the widening adds. "
        "Flattening is new independent measurements entering the problem, and "
        "MECH-01 narrows to: which transport regimes do the added biases "
        "sample that the core window does not? The mechanism is about "
        "COVERAGE"),
    "CONDITIONING": (
        "the new directions are carried across biases already present in the "
        "narrow window. Widening is not adding information so much as "
        "improving the conditioning of rows already there, and MECH-01 "
        "narrows to: what makes the existing rows less collinear when the "
        "window is wider? The mechanism is about COLLINEARITY"),
    "MIXED": (
        "the sign changes across widths. Reported with the widths that go each "
        "way named, and MECH-01 stays open with the crossover as the new "
        "object of study rather than with a mechanism named"),
    "UNDETERMINED": (
        "the reproduction control failed, so the Jacobian is not the one "
        "generation 9 measured and nothing here is about the same object. "
        "Reported as a failure to measure"),
}

OUTCOMES_NOTE = (
    "pre-registered before the first SVD, under the operator ruling of "
    "2026-08-28 §5, which required both outcomes stated before measuring "
    "because both are informative. Neither is the good outcome (AH-04, AH-13)")


def _hash_outcomes() -> str:
    return hashlib.sha256(
        json.dumps({"outcomes": OUTCOMES, "note": OUTCOMES_NOTE},
                   sort_keys=True).encode("utf-8")).hexdigest()


def _read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ===========================================================================
# The statistic
# ===========================================================================


def row_weights(jac: np.ndarray, biases_used: Any,
                core: Tuple[float, float]) -> Dict[str, Any]:
    """``w_out`` and ``excess`` for every index, from one Jacobian."""
    u_mat, s_vals, _ = np.linalg.svd(np.asarray(jac, dtype=np.float64),
                                     full_matrices=False)
    b = np.asarray(biases_used, dtype=np.float64)
    outside = (b < core[0]) | (b > core[1])
    n_rows = int(b.size)
    n_out = int(outside.sum())
    uniform = n_out / float(n_rows) if n_rows else float("nan")

    rows: List[Dict[str, Any]] = []
    for k in INDICES:
        if k - 1 >= u_mat.shape[1]:
            rows.append({"index": k, "available": False})
            continue
        weight = np.abs(u_mat[:, k - 1]) ** 2
        weight = weight / weight.sum()
        w_out = float(weight[outside].sum())
        rows.append({
            "index": k,
            "available": True,
            "singular_value": float(s_vals[k - 1]),
            "w_out": w_out,
            "excess_vs_uniform": w_out - uniform,
        })
    head = next((r for r in rows if r["index"] == 1 and r["available"]), None)
    for r in rows:
        r["excess_vs_head"] = (
            r["excess_vs_uniform"] - head["excess_vs_uniform"]
            if head and r.get("available") else None)
    trailing = [r["excess_vs_uniform"] for r in rows
                if r["index"] in (2, 3, 4) and r.get("available")]
    return {
        "n_rows": n_rows,
        "n_outside_core": n_out,
        "uniform_baseline": uniform,
        "indices": rows,
        "mean_excess_trailing": float(np.mean(trailing)) if trailing else None,
        "excess_head": head["excess_vs_uniform"] if head else None,
        "trailing_exceeds_head": bool(
            trailing and head is not None
            and float(np.mean(trailing)) > head["excess_vs_uniform"]),
    }


def _cell(sg, chart, theta, biases, cfg, core) -> Dict[str, Any]:
    rec, jac, _ = cell_spectrum(sg, chart, theta, biases, cfg)
    stats = row_weights(jac, rec["biases_used"], core)
    stats.update({
        "rows_used": rec["rows_used"],
        "biases_offered": rec["biases_offered"],
        "biases_used": rec["biases_used"],
        "singular_values": rec["singular_values"],
        "wall_clock_s": rec["wall_clock_s"],
    })
    return stats


# ===========================================================================
# Phases
# ===========================================================================


def phase_preregister(out: Path, pilot: Optional[Dict[str, Any]]) -> Dict:
    print("=" * 74)
    print("PHASE 0  PRE-REGISTRATION (AH-14): the measure and both outcomes")
    print("=" * 74)
    measure = RowMeasure()
    doc = {
        "what_this_is": (
            "MECH-01 second method, the row side. Generation 10 tested the "
            "column side and falsified it; this is distinct in kind, not a "
            "second guess"),
        "authorised_by": "operator ruling of 2026-08-28 §5",
        "pilot": pilot,
        "pilot_rule": (
            "PILOT-01, enacted by the same ruling: a measurement is never "
            "declined on a plausibility argument. Either it is priced by pilot "
            "and declined on U-BUDGET with the number, or it is run. This one "
            "was priced and run"),
        "measure": measure.to_dict(),
        "outcomes": OUTCOMES,
        "outcomes_note": OUTCOMES_NOTE,
        "outcomes_hash": _hash_outcomes(),
        "new_solves": (
            "NOT zero. outputs/g9/rank_obs.json stores singular VALUES only, "
            "not the left singular vectors, so the Jacobians must be "
            "recomputed. The ruling's new_solves=0 guard was conditional on "
            "them already existing; they do not, and saying so is cheaper "
            "than a guard that would have to lie"),
        "reproduction_control_is_what_makes_that_safe": (
            "R1 requires every recomputed sigma_1..sigma_4 to reproduce "
            "generation 9's stored values, so a recomputed Jacobian is held to "
            "being the same object rather than assumed to be"),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "preregister.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  measure   {measure.measure_hash()[:32]}...")
    print(f"  outcomes  {_hash_outcomes()[:32]}...")
    print(f"  core window (not chosen here) {measure.reference_core_V}")
    if pilot:
        print(f"  pilot: {pilot['per_cell_mean_s']:.1f} s/cell x "
              f"{pilot['cells_required']} = "
              f"{pilot['projected_total_s']:.0f} s -> {pilot['verdict']}")
    print(f"  wrote {out / 'preregister.json'}")
    return doc


def phase_measure(out: Path, grid_n: int) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  the row-side weight, along width and along spacing")
    print("=" * 74)
    measure = RowMeasure()
    core = measure.reference_core_V
    cfg = GlobalStudyConfig(n_anchor=4)
    sg, x_si = build_solver(cfg, grid_n)
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    g9 = _read(G9_RANK_OBS)

    doc: Dict[str, Any] = {"devices": {}, "core_window_V": list(core)}
    repro_rows: List[Dict[str, Any]] = []
    t_all = time.perf_counter()

    for dname, dev in g9["devices"].items():
        th4 = np.asarray(dev["theta_chartG_d4"], dtype=np.float64)
        m16 = np.interp(chart16.anchors, chart4.anchors, th4)
        rec: Dict[str, Any] = {"width_curve": [], "spacing_curve": []}
        print(f"\n  device {dname}")

        for i, w in enumerate(WIDTHS):
            lo, hi = WIDTH_CENTRE - w / 2.0, WIDTH_CENTRE + w / 2.0
            cell = _cell(sg, chart16, m16, window_biases(lo, hi, 16), cfg, core)
            cell["width_V"] = float(w)
            rec["width_curve"].append(cell)
            stored = dev["width_curve"][i].get("singular_values") or []
            for k in INDICES:
                if k - 1 < len(stored) and k - 1 < len(cell["singular_values"]):
                    repro_rows.append({
                        "device": dname, "axis": "width", "width_V": float(w),
                        "index": k,
                        "generation_9": stored[k - 1],
                        "here": cell["singular_values"][k - 1],
                        "identical": bool(
                            stored[k - 1] == cell["singular_values"][k - 1]),
                    })
            print(f"    width {w:.2f}  rows {cell['rows_used']:2d}  "
                  f"out/rows {cell['n_outside_core']:2d}/{cell['n_rows']:2d}  "
                  f"excess head {cell['excess_head']:+.4f}  "
                  f"trailing {cell['mean_excess_trailing']:+.4f}  "
                  f"{'trailing>head' if cell['trailing_exceeds_head'] else 'head>=trailing'}")

        for a in ALPHAS:
            cell = _cell(sg, chart16, m16, _spacing(0.15, 0.90, 16, a),
                         cfg, core)
            cell["alpha"] = float(a)
            rec["spacing_curve"].append(cell)
        doc["devices"][dname] = rec

    doc["reproduction_control_R1"] = {
        "rows": repro_rows,
        "n_identical": sum(1 for r in repro_rows if r["identical"]),
        "of": len(repro_rows),
        "all_identical": bool(repro_rows
                              and all(r["identical"] for r in repro_rows)),
        "why": (
            "the singular values recomputed here must equal generation 9's "
            "stored ones. If they do not, the Jacobian is not the one "
            "generation 9 measured and nothing here is about the same object"),
    }
    doc["wall_clock_s"] = time.perf_counter() - t_all
    r1 = doc["reproduction_control_R1"]
    print(f"\n  R1 reproduction: {r1['n_identical']} of {r1['of']} "
          f"singular values identical to generation 9 -> "
          f"{'PASS' if r1['all_identical'] else 'FAIL'}")
    (out / "rows.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out / 'rows.json'}")
    return doc


def phase_controls(out: Path, seed: int = 20260828) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  CONTROLS")
    print("=" * 74)
    measure = RowMeasure()
    core = measure.reference_core_V
    rng = np.random.default_rng(seed)
    doc = _read_out(out, "rows.json")

    # -- N1: Haar-random directions carry no width trend -------------------
    n1_rows = []
    for cell in doc["devices"]["g8_operating_point"]["width_curve"]:
        n_rows = cell["n_rows"]
        b = np.asarray(cell["biases_used"], dtype=np.float64)
        outside = (b < core[0]) | (b > core[1])
        vec = rng.normal(size=n_rows)
        weight = (vec ** 2) / (vec ** 2).sum()
        n1_rows.append({
            "width_V": cell["width_V"],
            "w_out": float(weight[outside].sum()),
            "excess_vs_uniform": float(weight[outside].sum()
                                       - outside.sum() / n_rows),
        })
    xs = np.array([r["width_V"] for r in n1_rows])
    ys = np.array([r["excess_vs_uniform"] for r in n1_rows])
    rho = float(np.corrcoef(np.argsort(np.argsort(xs)),
                            np.argsort(np.argsort(ys)))[0, 1])
    n1 = {
        "construction": (
            "one Haar-random unit direction per width, scored by the same "
            "statistic. The width axis carries no information about them by "
            "construction"),
        "rows": n1_rows, "spearman_vs_width": rho, "threshold": 0.7,
        "passes": bool(abs(rho) < 0.7),
        "note": (
            "a single draw per width, so this bounds the statistic's "
            "gullibility rather than estimating a null distribution -- "
            "generation 10's wording, and its limit"),
    }
    print(f"  N1 random directions vs width: rho {rho:+.3f} (<0.7) -> "
          f"{'PASS' if n1['passes'] else 'FAIL'}")

    # -- P1: a planted Jacobian whose trailing directions live outside ------
    biases = np.linspace(0.15, 0.90, 16)
    outside = (biases < core[0]) | (biases > core[1])
    planted = np.zeros((16, 16))
    planted[:, 0] = 1.0                      # head: flat over every row
    for j in range(1, 4):
        col = np.zeros(16)
        col[outside] = rng.normal(size=int(outside.sum()))
        planted[:, j] = col * 1e-2           # trailing: added rows only
    planted[:, 4:] = rng.normal(size=(16, 12)) * 1e-8
    p1_stats = row_weights(planted, biases, core)
    p1 = {
        "construction": (
            "a Jacobian whose head is flat over every row and whose trailing "
            "directions are supported ONLY on rows outside the core window"),
        "stats": p1_stats,
        "passes": bool(p1_stats["trailing_exceeds_head"]),
        "why_it_is_the_positive_control": (
            "IA-1 requires a control that fails if the rule does nothing. "
            "Without it a CONDITIONING verdict could mean the statistic cannot "
            "see row concentration at all, rather than that there is none"),
    }
    print(f"  P1 planted new-row Jacobian -> trailing exceeds head: "
          f"{p1_stats['trailing_exceeds_head']} -> "
          f"{'PASS' if p1['passes'] else 'FAIL'}")

    # -- C1: the axis that does not move the rank ---------------------------
    c1_dev = {}
    for dname, dev in doc["devices"].items():
        flags = [c["trailing_exceeds_head"] for c in dev["spacing_curve"]]
        c1_dev[dname] = {
            "n_cells": len(flags),
            "n_trailing_exceeds_head": int(sum(flags)),
            "fraction": (sum(flags) / len(flags)) if flags else None,
        }
    c1 = {
        "construction": (
            "the same statistic along SPEC-g9-2's spacing axis, where the rank "
            "does not move at all"),
        "devices": c1_dev,
        "why": (
            "a row-side signal that appears just as strongly along the axis "
            "where nothing happens is not about width"),
    }
    for dname, v in c1_dev.items():
        print(f"  C1 spacing axis, {dname}: trailing exceeds head in "
              f"{v['n_trailing_exceeds_head']} of {v['n_cells']} cells")

    controls = {"N1_negative": n1, "P1_positive": p1, "C1_control_axis": c1,
                "seed": seed}
    (out / "controls.json").write_text(
        json.dumps(controls, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out / 'controls.json'}")
    return controls


def _read_out(out: Path, name: str) -> Dict:
    return json.loads((out / name).read_text(encoding="utf-8"))


def phase_verdict(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  THE VERDICT, against the pre-registered outcome table")
    print("=" * 74)
    doc = _read_out(out, "rows.json")
    controls = _read_out(out, "controls.json")
    r1 = doc["reproduction_control_R1"]

    per_device = {}
    for dname, dev in doc["devices"].items():
        wider = [c for c in dev["width_curve"] if c["width_V"] > WIDTHS[0]]
        flags = [c["trailing_exceeds_head"] for c in wider]
        per_device[dname] = {
            "n_widths_beyond_the_narrowest": len(wider),
            "n_trailing_exceeds_head": int(sum(flags)),
            "widths_where_trailing_exceeds_head": [
                c["width_V"] for c in wider if c["trailing_exceeds_head"]],
            "widths_where_it_does_not": [
                c["width_V"] for c in wider if not c["trailing_exceeds_head"]],
            "all": bool(flags and all(flags)),
            "none": bool(flags and not any(flags)),
        }

    if not r1["all_identical"]:
        cls = "UNDETERMINED"
    elif all(v["all"] for v in per_device.values()):
        cls = "NEW_ROWS"
    elif all(v["none"] for v in per_device.values()):
        cls = "CONDITIONING"
    else:
        cls = "MIXED"

    verdict = {
        "classification": cls,
        "reading": OUTCOMES[cls],
        "reading_was_registered_before_the_first_svd": True,
        "outcomes_hash": _hash_outcomes(),
        "measure_hash": RowMeasure().measure_hash(),
        "per_device": per_device,
        "controls": {
            "R1_reproduction": (
                f"{'PASS' if r1['all_identical'] else 'FAIL'}, "
                f"{r1['n_identical']} of {r1['of']}"),
            "N1_negative": "PASS" if controls["N1_negative"]["passes"] else "FAIL",
            "P1_positive": "PASS" if controls["P1_positive"]["passes"] else "FAIL",
            "C1_control_axis": controls["C1_control_axis"]["devices"],
        },
        "all_controls_pass": bool(
            r1["all_identical"] and controls["N1_negative"]["passes"]
            and controls["P1_positive"]["passes"]),
        "what_it_does_not_say": (
            "it does not say WHY the added biases carry what they carry, nor "
            "does it convert MECH-01 from open to answered. It narrows the "
            "question by one step, which is what a second method is for. It "
            "also says nothing about any window wider than 0.75 V or any bias "
            "above 0.90 V (PH-15)"),
        "if_this_method_failed": (
            "two distinct methods would have failed -- generation 10's column "
            "side and this row side. U-EMPIR needs three, so a third would be "
            "required before MECH-01 could be ruled unreachable, or an "
            "U-INSTR verdict naming the missing instrument"),
    }
    (out / "verdict.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  classification: {cls}")
    for dname, v in per_device.items():
        print(f"    {dname}: trailing exceeds head at "
              f"{v['n_trailing_exceeds_head']} of "
              f"{v['n_widths_beyond_the_narrowest']} widths")
    print(f"  all controls pass: {verdict['all_controls_pass']}")
    print(f"  wrote {out / 'verdict.json'}")
    return verdict


def run_pilot(grid_n: int, n_cells_required: int) -> Dict[str, Any]:
    """``PILOT-01``. Price the experiment before deciding anything about it."""
    print("=" * 74)
    print("PILOT (PILOT-01): pricing the row-side measurement")
    print("=" * 74)
    cfg = GlobalStudyConfig(n_anchor=4)
    sg, x_si = build_solver(cfg, grid_n)
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    g9 = _read(G9_RANK_OBS)
    th4 = np.asarray(
        g9["devices"]["g8_operating_point"]["theta_chartG_d4"],
        dtype=np.float64)
    m16 = np.interp(chart16.anchors, chart4.anchors, th4)
    core = RowMeasure().reference_core_V

    times = []
    for w in (WIDTHS[0], WIDTHS[-1]):
        lo, hi = WIDTH_CENTRE - w / 2.0, WIDTH_CENTRE + w / 2.0
        t0 = time.perf_counter()
        _cell(sg, chart16, m16, window_biases(lo, hi, 16), cfg, core)
        times.append(time.perf_counter() - t0)
        print(f"  width {w:.2f}: {times[-1]:.1f} s")
    mean = float(np.mean(times))
    doc = {
        "cells_piloted": len(times),
        "per_cell_s": times,
        "per_cell_mean_s": mean,
        "per_cell_spread_factor": float(max(times) / min(times)),
        "cells_required": n_cells_required,
        "projected_total_s": mean * n_cells_required,
        "basis": (
            "the narrowest and widest windows, which bracket the cost: the "
            "widest is the slowest because more of its biases converge "
            "slowly. Every other cell lies between them"),
        "verdict": "AFFORDABLE" if mean * n_cells_required < 1800 else "EXPENSIVE",
        "note": (
            "PILOT-01: a measurement is never declined on a plausibility "
            "argument. This prices it so that a U-BUDGET verdict would have a "
            "number behind it"),
    }
    print(f"  mean {mean:.1f} s/cell x {n_cells_required} cells = "
          f"{doc['projected_total_s']:.0f} s -> {doc['verdict']}")
    return doc


ALL_PHASES = ["pilot", "preregister", "measure", "controls", "verdict"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g12/mech01_rows")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    n_devices = len(_read(G9_RANK_OBS)["devices"])
    cells = n_devices * (len(WIDTHS) + len(ALPHAS))

    pilot = run_pilot(args.grid, cells) if "pilot" in phases else None
    if "preregister" in phases:
        phase_preregister(out, pilot)
    if "measure" in phases:
        phase_measure(out, args.grid)
    if "controls" in phases:
        phase_controls(out)
    if "verdict" in phases:
        phase_verdict(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
