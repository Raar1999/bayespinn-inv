"""``MECH-01`` pass 3: the magnitude statistic, standardised, pre-registered, and
tested out of sample.

    PYTHONPATH=src python scripts/run_mech01_pass3.py

Authorised by the operator ruling of 2026-08-28 §5.

Why a third pass, and what went wrong in the second
---------------------------------------------------
Pass 2 (``scripts/run_mech01_rows.py``) pre-registered a **sign** and the sign
came out ``NEW_ROWS`` at 16 of 16 width cells -- and at 16 of 18 cells of the
control axis, where the rank does not move. A discriminator that fires on the
control is not discriminating. ``scripts/mech01_discriminator.py`` then reported
the **magnitude** of the same gap, 3.1--3.5x larger on the width axis, and was
explicit that it was a description and not a test, chosen after seeing the data.

The ruling's instruction is to pre-register that magnitude and test it out of
sample, because validating it on the cells that suggested it is ``AH-06`` -- the
same error as ratifying headroom at concordance 1.000 on the sample that
generated it, which then read 0.479 on a set it had never seen.

The defect pass 3 found in the pass-2 statistic, before pre-registering
--------------------------------------------------------------------
Reading the pass-2 cells as a discovery sample -- which is what they are -- the
gap is **confounded with the split ratio**. Write ``b = n_out/n_rows``, the share
of bias rows lying outside the reference core:

* the **width** axis sweeps ``b`` from 0.0625 to 0.875, and its maximum gap sits
  at ``b = 0.375``--``0.50``;
* the **spacing** axis only ever visits ``b`` in ``[0.857, 0.929]``.

So the two axes are compared at values of ``b`` that do not overlap, and the
width axis's peak sits in a region the control axis never samples at all. At
*matched* ``b`` the width cells fall inside the spread of the spacing cells. The
3.1--3.5x ratio is therefore not evidence about rank; it is substantially a
statement about ``b``, and the control axis was never a control for it.

That is the thing to fix before any threshold is written down, and it is fixed
here by standardising against the null that ``b`` induces, rather than by
subtracting a baseline that leaves the scale ``b``-dependent.

The null, and the standardisation it forces
-------------------------------------------
Under ``H0`` -- the singular direction has no preference among bias rows --
``U[:, k]`` is a uniformly random unit vector in ``R**n_rows``, so the squared
coordinates are ``Dirichlet(1/2, ..., 1/2)`` and the mass on any fixed set of
``n_out`` of them is::

    w_out ~ Beta(n_out/2, n_in/2)         n_in = n_rows - n_out

with::

    E[w_out]   = n_out/n_rows = b                      (pass 2's uniform baseline)
    Var[w_out] = 2 b (1 - b) / (n_rows + 2)

Pass 2 subtracted the mean and stopped. The variance is the part that carries
``b``, and it is why cells at different ``b`` were not comparable. Dividing by it
gives a quantity that is mean 0 and variance 1 under ``H0`` at **every** cell::

    z(k) = (w_out(k) - b) / sqrt(2 b (1 - b) / (n_rows + 2))

and the cell statistic is the same contrast pass 2 formed, in those units::

    dz = mean(z(2), z(3), z(4)) - z(1)

Both the standardisation and the admissibility rule below are *derived from the
null*, not selected for what they do to the discovery sample. That is the whole
of their defence.

Admissibility -- the ruling's degeneracy, fixed structurally
------------------------------------------------------------
``Beta(n_out/2, n_in/2)`` has a finite, non-U-shaped density only when both shape
parameters are at least 1, which is ``n_out >= 2`` and ``n_in >= 2``. A cell that
fails it has no null to standardise against.

Stated in advance: at the ``SPEC-g9-2`` geometry this excludes **exactly the
narrowest width cell**, where ``n_out = 1`` of 16 and the core and measurement
windows coincide -- the degeneracy the ruling names. It is excluded here because
the null is degenerate there, not because it is inconvenient, and the rule is
written over ``n_out`` and ``n_in`` rather than over the width so that it cannot
be tuned by moving a window.

The test, the threshold, and where it is run
--------------------------------------------
One-sided exact Mann-Whitney U per device, width cells against spacing cells,
alternative "width is larger", ``alpha = 0.05``. Rank-based, so no scale is
assumed; exact, so no asymptotic approximation is claimed at ``n < 10``; the
threshold is the conventional 0.05 rather than a number chosen to clear the
observed separation (``PH-11``).

**Out of sample means devices the row side has never seen.** ``device_p10`` and
``device_p90`` were selected at generation 9 by ``SPEC-g9-1``'s pre-registered
percentile rule and have never had a row weight computed on them: pass 2 used
``g8_operating_point`` and ``device_p50`` and nothing else. They are also the
*far* devices -- 1.22 and 1.41 decades of profile distance from the generation-8
device against ``device_p50``'s 0.64 -- so this is an extrapolation, not a
neighbour.

``new_solves``
--------------
Not zero here, and the reason is the same one pass 2 gave: ``outputs/g9`` stores
singular **values**, never the left singular vectors, so ``U`` has to be
recomputed. The ruling's ``new_solves = 0`` guard was conditional on the
Jacobians existing and they do not. What *is* held at zero, and AST-guarded by
``tests/test_mech01_pass3_g13.py``, is the **analysis**: phase ``insample`` and
phase ``verdict`` are arithmetic over stored ``w_out`` and touch no solver.
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
from scipy.stats import mannwhitneyu

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
G9_OP_POINTS = "outputs/g9/op_points.json"
G12_ROWS = "outputs/g12/mech01_rows/rows.json"

#: Inherited from the close and from pass 2, not re-litigated here.
INDICES = (1, 2, 3, 4)

#: The cell the two axes share -- generation 9's ``C4``. ``alpha = 0`` and
#: ``width = 0.75`` are one observation set reached by two code paths, so it is
#: dropped from the spacing side rather than counted on both.
SHARED_ALPHA = 0.0
SHARED_WIDTH = 0.75

#: Held out. Never used by pass 2, selected by ``SPEC-g9-1`` a generation before
#: this statistic existed.
HELD_OUT = ("device_p10", "device_p90")

#: The discovery sample. Re-analysed for contrast, never as evidence.
DISCOVERY = ("g8_operating_point", "device_p50")

ALPHA_LEVEL = 0.05


# ===========================================================================
# The pre-registration
# ===========================================================================


@dataclass(frozen=True)
class Pass3Measure:
    """The statistic, the admissibility rule and the test. Hashed before any
    held-out device is touched."""

    quantity: str = (
        "dz(cell) = mean(z(2), z(3), z(4)) - z(1), where "
        "z(k) = (w_out(k) - b) / sqrt(2 b (1 - b) / (n_rows + 2)), "
        "b = n_out/n_rows, and w_out(k) is the share of |U[:, k]|**2 on bias "
        "rows outside the reference core window")
    null_model: str = (
        "under H0 the direction has no row preference, so U[:, k] is uniform on "
        "the unit sphere in R**n_rows, the squared coordinates are "
        "Dirichlet(1/2, ..., 1/2), and w_out ~ Beta(n_out/2, n_in/2) with mean b "
        "and variance 2 b (1 - b) / (n_rows + 2). z is therefore mean 0 and "
        "variance 1 under H0 at every cell, whatever b is")
    why_not_pass_2s_statistic: str = (
        "pass 2 subtracted the mean and kept the raw scale, which is "
        "b-dependent. The width axis sweeps b over 0.0625..0.875 and peaks at "
        "b = 0.375..0.50; the spacing axis only ever visits b in 0.857..0.929. "
        "The axes were compared where they do not overlap, and the reported "
        "3.1-3.5x is substantially a statement about b rather than about rank")
    admissibility: str = (
        "a cell enters iff n_out >= 2 AND n_in >= 2, i.e. both Beta shape "
        "parameters are at least 1 and the null has a finite non-U-shaped "
        "density. Derived from the null, not chosen. At the SPEC-g9-2 geometry "
        "this excludes exactly the narrowest width cell (n_out = 1 of 16), "
        "which is the degeneracy the ruling of 2026-08-28 identified")
    reference_core_V: Tuple[float, float] = (
        WIDTH_CENTRE - WIDTHS[0] / 2.0, WIDTH_CENTRE + WIDTHS[0] / 2.0)
    reference_core_is_not_chosen_here: str = (
        "the narrowest window of SPEC-g9-2's width axis, whose centre, widths "
        "and bias count were fixed at generation 9, two generations before this "
        "question was asked")
    shared_cell_handling: str = (
        "alpha = 0 and width = 0.75 are one observation set reached by two code "
        "paths (generation 9's C4). Dropped from the spacing side; kept on the "
        "width side; never counted twice")
    test: str = (
        "one-sided exact Mann-Whitney U per device, width cells vs spacing "
        "cells, alternative 'width greater', alpha = 0.05. Rank-based so no "
        "scale is assumed, exact so nothing asymptotic is claimed at n < 10")
    decision_rule: str = (
        "SEPARATES iff p <= 0.05 at BOTH held-out devices. Any other result, "
        "including one device clearing and the other not, is "
        "DOES_NOT_SEPARATE. Requiring both is what stops a single device from "
        "carrying the claim")
    held_out_devices: Tuple[str, ...] = HELD_OUT
    why_these_are_out_of_sample: str = (
        "pass 2 measured row weights at g8_operating_point and device_p50 only. "
        "device_p10 and device_p90 were selected by SPEC-g9-1's pre-registered "
        "percentile rule at generation 9 and have never had a row weight "
        "computed on them. They are also the far devices: 1.22 and 1.41 decades "
        "of profile distance from the generation-8 device, against device_p50's "
        "0.64")
    indices: Tuple[int, ...] = INDICES
    minimum_cells: int = 4
    minimum_cells_why: str = (
        "below four admissible cells on either axis the exact test cannot reach "
        "p = 0.05 one-sided, so the measurement would be incapable of the "
        "outcome it is run to look for. Fewer than four is UNDETERMINED, "
        "reported as a failure to measure rather than as a negative")

    def measure_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["measure_hash"] = self.measure_hash()
        return out


OUTCOMES: Dict[str, str] = {
    "SEPARATES": (
        "the standardised gap is larger along the axis where the rank climbs "
        "than along the axis where it does not, at both held-out devices, at "
        "alpha = 0.05. The pass-2 description survives standardisation and "
        "survives devices it was not built on. MECH-01 narrows from an open "
        "question to a measured claim -- the trailing directions are carried by "
        "the bias rows the widening adds, and the mechanism is about COVERAGE "
        "rather than about conditioning. L0 becomes reachable"),
    "DOES_NOT_SEPARATE": (
        "the standardised gap does not separate the axes out of sample. The "
        "3.1-3.5x of pass 2 was a description of the discovery sample and of "
        "the split ratio it confounded, not a property of the system. This is "
        "the row-side method FAILING, characterised -- not inconclusive as pass "
        "2 was. U-EMPIR then stands at two distinct falsified methods, and a "
        "third distinct method or a U-INSTR verdict naming the missing "
        "instrument is what MECH-01 needs next"),
    "UNDETERMINED": (
        "the reproduction control failed, or fewer than four admissible cells "
        "were available on an axis at a held-out device. Reported as a failure "
        "to measure. It is not a negative result and may not be read as one"),
}

OUTCOMES_NOTE = (
    "pre-registered under the operator ruling of 2026-08-28 §5, which required "
    "the exact form, the threshold and both outcomes stated and hashed before "
    "the held-out data is touched. Neither outcome is the good outcome "
    "(AH-04, AH-13). DOES_NOT_SEPARATE is the more useful of the two for "
    "U-EMPIR, which is a reason to be careful of it, not a reason to want it")


def _hash_outcomes() -> str:
    return hashlib.sha256(
        json.dumps({"outcomes": OUTCOMES, "note": OUTCOMES_NOTE},
                   sort_keys=True).encode("utf-8")).hexdigest()


def _read(rel: str) -> Any:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _write(path: Path, doc: Any) -> None:
    """``EOL-02``: every text-mode write states its line ending."""
    path.write_text(json.dumps(doc, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


# ===========================================================================
# The statistic -- arithmetic only, no solver on this path
# ===========================================================================


def admissible(n_rows: int, n_out: int) -> bool:
    """Both Beta shape parameters at least 1. See ``Pass3Measure.admissibility``."""
    return n_out >= 2 and (n_rows - n_out) >= 2


def null_sd(n_rows: int, n_out: int) -> float:
    """``sqrt(Var[w_out])`` under ``H0``, from ``Beta(n_out/2, n_in/2)``."""
    b = n_out / float(n_rows)
    return float(np.sqrt(2.0 * b * (1.0 - b) / (n_rows + 2.0)))


def dz_from_w_out(w_out: Sequence[float], n_rows: int, n_out: int) -> float:
    """The cell statistic from stored ``w_out`` values. ``new_solves = 0``."""
    b = n_out / float(n_rows)
    sd = null_sd(n_rows, n_out)
    z = [(float(w) - b) / sd for w in w_out]
    return float(np.mean(z[1:4]) - z[0])


def cell_dz(cell: Dict[str, Any]) -> Optional[float]:
    """``dz`` for one measured cell, or ``None`` if it is inadmissible."""
    n_rows, n_out = int(cell["n_rows"]), int(cell["n_outside_core"])
    if not admissible(n_rows, n_out):
        return None
    w = []
    for k in INDICES:
        rec = next((r for r in cell["indices"] if r["index"] == k), None)
        if rec is None or not rec.get("available"):
            return None
        w.append(float(rec["w_out"]))
    return dz_from_w_out(w, n_rows, n_out)


def axis_dz(cells: List[Dict[str, Any]], key: str,
            drop: Optional[float] = None) -> List[Dict[str, Any]]:
    out = []
    for c in cells:
        param = float(c[key])
        if drop is not None and abs(param - drop) < 1e-12:
            continue
        d = cell_dz(c)
        out.append({
            "param": param,
            "n_rows": int(c["n_rows"]),
            "n_out": int(c["n_outside_core"]),
            "b": int(c["n_outside_core"]) / float(c["n_rows"]),
            "admissible": d is not None,
            "dz": d,
        })
    return out


def device_test(width: List[Dict[str, Any]],
                spacing: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The pre-registered test at one device."""
    wv = [r["dz"] for r in width if r["admissible"]]
    sv = [r["dz"] for r in spacing if r["admissible"]]
    rec: Dict[str, Any] = {
        "n_width_admissible": len(wv),
        "n_spacing_admissible": len(sv),
        "width_dz": wv,
        "spacing_dz": sv,
        "width_median": float(np.median(wv)) if wv else None,
        "spacing_median": float(np.median(sv)) if sv else None,
        "b_overlap": {
            "width_b_range": [min(r["b"] for r in width if r["admissible"]),
                              max(r["b"] for r in width if r["admissible"])]
            if wv else None,
            "spacing_b_range": [min(r["b"] for r in spacing if r["admissible"]),
                                max(r["b"] for r in spacing if r["admissible"])]
            if sv else None,
        },
    }
    if len(wv) < Pass3Measure.minimum_cells or len(sv) < Pass3Measure.minimum_cells:
        rec.update({"test_ran": False, "p_value": None, "u_statistic": None,
                    "clears_alpha": False,
                    "why": "fewer than the pre-registered minimum of admissible "
                           "cells on an axis"})
        return rec
    res = mannwhitneyu(wv, sv, alternative="greater", method="exact")
    rec.update({
        "test_ran": True,
        "u_statistic": float(res.statistic),
        "p_value": float(res.pvalue),
        "alpha": ALPHA_LEVEL,
        "clears_alpha": bool(res.pvalue <= ALPHA_LEVEL),
    })
    return rec


# ===========================================================================
# Phases
# ===========================================================================


def phase_pilot(grid_n: int, n_cells_required: int) -> Dict[str, Any]:
    """``PILOT-01``: price it before deciding to run it."""
    print("=" * 74)
    print("PHASE 0  PILOT (PILOT-01): price the run before committing to it")
    print("=" * 74)
    cfg = GlobalStudyConfig(n_anchor=4)
    t0 = time.perf_counter()
    sg, x_si = build_solver(cfg, grid_n)
    build_s = time.perf_counter() - t0
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    op = _read(G9_OP_POINTS)
    sel = {c["name"]: c for c in op["selection"]["chosen"]}
    th4 = np.asarray(sel[HELD_OUT[0]]["theta_chartG_d4"], dtype=np.float64)
    m16 = np.interp(chart16.anchors, chart4.anchors, th4)
    core = Pass3Measure().reference_core_V

    t0 = time.perf_counter()
    _ = _measure_cell(sg, chart16, m16, window_biases(0.15, 0.90, 16), cfg, core)
    per_cell = time.perf_counter() - t0

    doc = {
        "solver_build_s": build_s,
        "per_cell_s": per_cell,
        "n_cells_required": n_cells_required,
        "projected_s": build_s + per_cell * n_cells_required,
        "measured_not_estimated": True,
        "rule": ("PILOT-01: a measurement is priced by a measured pilot before "
                 "it is decided on, never by an estimate"),
    }
    print(f"  solver build      {build_s:8.2f} s")
    print(f"  one cell          {per_cell:8.2f} s")
    print(f"  {n_cells_required} cells projected {doc['projected_s']:8.2f} s")
    return doc


def phase_preregister(out: Path, pilot: Optional[Dict[str, Any]]) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  PRE-REGISTRATION (AH-14): hashed before a held-out device")
    print("=" * 74)
    measure = Pass3Measure()
    doc = {
        "what_this_is": (
            "MECH-01 pass 3. The pass-2 magnitude statistic, standardised "
            "against the null that the split ratio induces, pre-registered with "
            "a threshold and both outcomes, and tested on devices the row side "
            "has never seen"),
        "authorised_by": "operator ruling of 2026-08-28 §5",
        "pilot": pilot,
        "same_method_not_a_third": (
            "this is the row-side method with a sharper statistic. It is NOT a "
            "third distinct method, and it may not be counted as one for "
            "U-EMPIR whatever it returns"),
        "ah_06": (
            "the statistic was suggested by the pass-2 cells, so those cells "
            "cannot test it. They are re-analysed in phase 'insample' for "
            "contrast and that re-analysis is not evidence for or against the "
            "hypothesis"),
        "new_solves": (
            "not zero. outputs/g9 stores singular values, never U, so the "
            "Jacobian is recomputed at the held-out devices. The ANALYSIS "
            "phases -- insample and verdict -- are arithmetic over stored "
            "w_out at new_solves = 0, and that is AST-guarded by "
            "tests/test_mech01_pass3_g13.py"),
        "measure": measure.to_dict(),
        "outcomes": OUTCOMES,
        "outcomes_note": OUTCOMES_NOTE,
        "outcomes_hash": _hash_outcomes(),
    }
    _write(out / "preregister.json", doc)
    print(f"  measure hash  {measure.measure_hash()}")
    print(f"  outcomes hash {_hash_outcomes()}")
    print(f"  wrote {out / 'preregister.json'}")
    return doc


def phase_insample(out: Path) -> Dict:
    """Re-analyse the discovery sample. ``new_solves = 0``. Not evidence."""
    print()
    print("=" * 74)
    print("PHASE 2  the DISCOVERY sample under the new statistic (AH-06)")
    print("=" * 74)
    print("  Arithmetic over stored w_out. new_solves = 0.")
    print("  This is CONTRAST, not evidence: these cells suggested the")
    print("  statistic, so they cannot test it.")
    rows = _read(G12_ROWS)
    devices: Dict[str, Any] = {}
    for dname, rec in rows["devices"].items():
        w = axis_dz(rec["width_curve"], "width_V")
        s = axis_dz(rec["spacing_curve"], "alpha", drop=SHARED_ALPHA)
        devices[dname] = {"width": w, "spacing": s, "test": device_test(w, s)}
        t = devices[dname]["test"]
        excluded = [r["param"] for r in w if not r["admissible"]]
        print(f"\n  {dname}")
        print(f"    width cells admissible   {t['n_width_admissible']} of {len(w)}"
              f"   excluded widths: {excluded}")
        print(f"    spacing cells admissible {t['n_spacing_admissible']} of {len(s)}")
        print(f"    median dz  width {t['width_median']:+.3f}   "
              f"spacing {t['spacing_median']:+.3f}")
        if t["test_ran"]:
            print(f"    exact one-sided p = {t['p_value']:.5f}  "
                  f"{'clears' if t['clears_alpha'] else 'does not clear'} 0.05")
    doc = {
        "devices": devices,
        "new_solves": 0,
        "is_evidence": False,
        "why_not_evidence": (
            "AH-06. The statistic was chosen after seeing these cells. Reported "
            "so that the out-of-sample result can be read against it, and for "
            "no other purpose"),
    }
    _write(out / "insample.json", doc)
    print(f"\n  wrote {out / 'insample.json'}")
    return doc


def _measure_cell(sg, chart, theta, biases, cfg, core) -> Dict[str, Any]:
    """One Jacobian, one SVD, one cell. This is the only path that solves."""
    rec, jac, _ = cell_spectrum(sg, chart, theta, biases, cfg)
    u_mat, s_vals, _ = np.linalg.svd(np.asarray(jac, dtype=np.float64),
                                     full_matrices=False)
    b_arr = np.asarray(rec["biases_used"], dtype=np.float64)
    outside = (b_arr < core[0]) | (b_arr > core[1])
    n_rows, n_out = int(b_arr.size), int(outside.sum())
    idx: List[Dict[str, Any]] = []
    for k in INDICES:
        if k - 1 >= u_mat.shape[1]:
            idx.append({"index": k, "available": False})
            continue
        weight = np.abs(u_mat[:, k - 1]) ** 2
        weight = weight / weight.sum()
        idx.append({
            "index": k, "available": True,
            "singular_value": float(s_vals[k - 1]),
            "w_out": float(weight[outside].sum()),
        })
    return {
        "n_rows": n_rows,
        "n_outside_core": n_out,
        "uniform_baseline": n_out / float(n_rows) if n_rows else float("nan"),
        "null_sd": null_sd(n_rows, n_out) if admissible(n_rows, n_out) else None,
        "indices": idx,
        "rows_used": rec["rows_used"],
        "biases_offered": rec["biases_offered"],
        "biases_used": rec["biases_used"],
        "singular_values": rec["singular_values"],
        "wall_clock_s": rec["wall_clock_s"],
    }


def phase_measure(out: Path, grid_n: int) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  the HELD-OUT devices -- never used by the row side before")
    print("=" * 74)
    measure = Pass3Measure()
    core = measure.reference_core_V
    cfg = GlobalStudyConfig(n_anchor=4)
    sg, x_si = build_solver(cfg, grid_n)
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    op = _read(G9_OP_POINTS)
    sel = {c["name"]: c for c in op["selection"]["chosen"]}

    doc: Dict[str, Any] = {"devices": {}, "core_window_V": list(core)}
    repro: List[Dict[str, Any]] = []
    t_all = time.perf_counter()

    for dname in HELD_OUT:
        th4 = np.asarray(sel[dname]["theta_chartG_d4"], dtype=np.float64)
        m16 = np.interp(chart16.anchors, chart4.anchors, th4)
        rec: Dict[str, Any] = {"width_curve": [], "spacing_curve": [],
                               "theta_chartG_d4": list(map(float, th4))}
        print(f"\n  device {dname}")
        for w in WIDTHS:
            lo, hi = WIDTH_CENTRE - w / 2.0, WIDTH_CENTRE + w / 2.0
            cell = _measure_cell(sg, chart16, m16,
                                 window_biases(lo, hi, 16), cfg, core)
            cell["width_V"] = float(w)
            rec["width_curve"].append(cell)
            d = cell_dz(cell)
            print(f"    width {w:.2f}  out/rows {cell['n_outside_core']:2d}/"
                  f"{cell['n_rows']:2d}  b {cell['uniform_baseline']:.3f}  "
                  + (f"dz {d:+.3f}" if d is not None
                     else "INADMISSIBLE (null degenerate)"))
            # R1': the widest window IS g9's wide_0.15_0.90 cell.
            if abs(w - SHARED_WIDTH) < 1e-12:
                stored = (op["operating_points"]
                          [f"{dname}__wide_0.15_0.90"]["cells"]["G_d16"]
                          ["singular_values"])
                for k in INDICES:
                    if k - 1 < len(stored):
                        repro.append({
                            "device": dname, "index": k,
                            "generation_9": stored[k - 1],
                            "here": cell["singular_values"][k - 1],
                            "identical": bool(
                                stored[k - 1] == cell["singular_values"][k - 1]),
                        })
        for a in ALPHAS:
            cell = _measure_cell(sg, chart16, m16,
                                 _spacing(0.15, 0.90, 16, a), cfg, core)
            cell["alpha"] = float(a)
            rec["spacing_curve"].append(cell)
        doc["devices"][dname] = rec

    doc["reproduction_control_R1"] = {
        "rows": repro,
        "n_identical": sum(1 for r in repro if r["identical"]),
        "of": len(repro),
        "all_identical": bool(repro and all(r["identical"] for r in repro)),
        "why": (
            "the width = 0.75 window IS generation 9's wide_0.15_0.90 window. "
            "Its singular values must reproduce op_points.json bit for bit, or "
            "the Jacobian is not the object SPEC-g9-1 measured and nothing here "
            "is about the same device"),
    }
    doc["wall_clock_s"] = time.perf_counter() - t_all
    r1 = doc["reproduction_control_R1"]
    print(f"\n  R1' reproduction: {r1['n_identical']} of {r1['of']} singular "
          f"values bit-identical to generation 9 -> "
          f"{'PASS' if r1['all_identical'] else 'FAIL'}")
    _write(out / "heldout.json", doc)
    print(f"  wrote {out / 'heldout.json'}")
    return doc


def phase_verdict(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 4  VERDICT against the pre-registration")
    print("=" * 74)
    pre = json.loads((out / "preregister.json").read_text(encoding="utf-8"))
    held = json.loads((out / "heldout.json").read_text(encoding="utf-8"))

    devices: Dict[str, Any] = {}
    for dname, rec in held["devices"].items():
        w = axis_dz(rec["width_curve"], "width_V")
        s = axis_dz(rec["spacing_curve"], "alpha", drop=SHARED_ALPHA)
        devices[dname] = {"width": w, "spacing": s, "test": device_test(w, s)}

    r1_ok = bool(held["reproduction_control_R1"]["all_identical"])
    ran = all(d["test"]["test_ran"] for d in devices.values())
    if not r1_ok or not ran:
        outcome = "UNDETERMINED"
    elif all(d["test"]["clears_alpha"] for d in devices.values()):
        outcome = "SEPARATES"
    else:
        outcome = "DOES_NOT_SEPARATE"

    doc = {
        "outcome": outcome,
        "meaning": OUTCOMES[outcome],
        "measure_hash": pre["measure"]["measure_hash"],
        "outcomes_hash": pre["outcomes_hash"],
        "hashes_match_preregistration": bool(
            pre["measure"]["measure_hash"] == Pass3Measure().measure_hash()
            and pre["outcomes_hash"] == _hash_outcomes()),
        "reproduction_control_R1": {
            "pass": r1_ok,
            "n_identical": held["reproduction_control_R1"]["n_identical"],
            "of": held["reproduction_control_R1"]["of"],
        },
        "devices": devices,
        "decision_rule": Pass3Measure.decision_rule,
        "new_solves": 0,
        "arithmetic_only": True,
    }
    for dname, d in devices.items():
        t = d["test"]
        print(f"\n  {dname}")
        print(f"    admissible  width {t['n_width_admissible']}  "
              f"spacing {t['n_spacing_admissible']}")
        print(f"    median dz   width {t['width_median']:+.3f}  "
              f"spacing {t['spacing_median']:+.3f}")
        if t["test_ran"]:
            print(f"    exact one-sided p = {t['p_value']:.5f}  vs alpha 0.05 "
                  f"-> {'CLEARS' if t['clears_alpha'] else 'does NOT clear'}")
    print()
    print(f"  R1' reproduction: {'PASS' if r1_ok else 'FAIL'}")
    print(f"  OUTCOME: {outcome}")
    _write(out / "verdict.json", doc)
    print(f"  wrote {out / 'verdict.json'}")
    return doc


ALL_PHASES = ["pilot", "preregister", "insample", "measure", "verdict"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g13/mech01_pass3")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    pilot = None
    n_cells = len(HELD_OUT) * (len(WIDTHS) + len(ALPHAS))
    if "pilot" in phases:
        pilot = phase_pilot(args.grid, n_cells)
        _write(out / "pilot.json", pilot)
    if "preregister" in phases:
        phase_preregister(out, pilot)
    if "insample" in phases:
        phase_insample(out)
    if "measure" in phases:
        phase_measure(out, args.grid)
    if "verdict" in phases:
        phase_verdict(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
