"""``MECH-01`` pass 4: row-subset growth against a random-row null.

    PYTHONPATH=src python scripts/run_mech01_pass4.py

Authorised by the operator ruling of 2026-08-28 §3 (pass 4). **The last pass**:
§4 of that ruling fixes the terminal condition in advance — this answers, or it
is method three and ``U-EMPIR`` is issued.

Why this is not a third guess at the same thing
------------------------------------------------
Passes 2 and 3 were both **contrasts between two axes**, width against spacing.
Pass 3 established why that design could not work, whatever statistic was hung
on it: the axes do not span the same range of the nuisance parameter
``b = n_out/n_rows``. Width sweeps ``b`` over 0.0625--0.875 and peaks where the
control axis never goes, because spacing only ever visits 0.857--0.929.
Standardising against the ``Beta(n_out/2, n_in/2)`` null was the right repair to
a design that was already unsalvageable, and the measured mechanism of the
failure said so: ``corr(dz, b)`` at -0.95 to -0.98, with a device offset spread
of 1.572 against a largest axis difference of 0.22.

So pass 4 is **not a contrast**. It is a **null, matched on the nuisance by
construction**: the null draws random subsets of exactly the same size as the
thing it is compared against, so row count cannot differ between them. Nothing
needs standardising because nothing is compared across incomparable ranges.

The question, stated so that both answers are answers
------------------------------------------------------
Widening the bias window flattens the spectrum. Does it flatten *because of
which* biases arrive, or merely because *more rows* arrive?

* ``IDENTITY_MATTERS`` — the nested windows depart from the random-subset null.
  The identity of the added biases carries the effect. ``MECH-01`` becomes a
  regime question, and *which* biases is answerable from the same artefact.
* ``GENERIC_ROW_COUNT`` — the nested windows track the null. Flattening is a
  row-count effect with nothing device- or regime-specific in it. That is a
  complete and deflationary answer to ``MECH-01``, and the ruling is explicit
  that it is to be written as one rather than treated as a failure.

The construction
----------------
At one device, at the **widest** window, one Jacobian ``J`` with ``n`` certified
bias rows.

* **The universe** is those ``n`` rows.
* **The nested sequence** ``N_k`` is the ``k`` rows closest to the window centre
  (``WIDTH_CENTRE``), ties to the lower bias. That is precisely the order in
  which widening the window admits biases, so the nested sequence *is* the width
  axis, re-expressed as subsets of one matrix rather than as separate solves.
* **The null** at each ``k`` is uniformly random ``k``-subsets of the universe.
  Matched on row count by construction — the property pass 3 proved the spacing
  axis lacks.

**The per-subset statistic** is the gap behind the head,
``gap = log10(sigma_1) - log10(sigma_2)``. Flatter means smaller. The decay slope
over ``i = 1..min(4, k)`` is computed and reported beside it as a pre-registered
**secondary**; the decision rests on the gap alone, so there is no multiplicity
to exploit.

**The test.** ``P_k`` is the nested set's percentile in the null at ``k``. Under
the hypothesis that only row count matters, the order in which rows arrive is
exchangeable, so ``P_k`` is uniform. The test statistic is ``T = mean_k P_k``,
and its null distribution is obtained by **scoring random chains** — a random
permutation of the universe, its prefixes taken as a pseudo-nested sequence —
against the same per-``k`` null draws. That handles the dependence between
nested sets at different ``k`` by construction rather than by assumption, which
an independence-assuming combination of per-``k`` p-values would not.

Two-sided at ``alpha = 0.05``. The ruling frames the interesting direction as
"flattens *more* than random", and it is the hypothesised one; flattening
*less* than random would equally refute genericity, so refusing to see it would
be choosing which way the evidence may point. The direction is reported.

``new_solves``
--------------
The Jacobian is not stored anywhere in this tree — ``outputs/g9`` keeps singular
values only, and pass 3 kept ``w_out`` — so it is recomputed once per device and
**written to disk this time**, so that any later pass over these rows is
arithmetic. The subset sampling, every sub-spectrum, the percentiles and the
verdict are arithmetic over that stored matrix at ``new_solves = 0``, AST-guarded
by ``tests/test_mech01_pass4_g14.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from math import comb
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_g9 import (
    WIDTH_CENTRE,
    WIDTHS,
    build_solver,
    cell_spectrum,
    window_biases,
)

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig

ROOT = Path(__file__).resolve().parents[1]
G9_OP_POINTS = "outputs/g9/op_points.json"

WIDEST = WIDTHS[-1]                      # 0.75 V -- g9's wide_0.15_0.90 window
INDICES = (1, 2, 3, 4)

HELD_OUT = ("device_p10", "device_p90")
CONTRAST = ("g8_control", "device_p50")

ALPHA_LEVEL = 0.05
N_NULL = 4000                            # random k-subsets per k
N_CHAIN = 4000                           # random chains for T's null
SEED = 20260828


# ===========================================================================
# The pre-registration
# ===========================================================================


@dataclass(frozen=True)
class Pass4Measure:
    """The construction, the statistic and the test. Hashed before the first draw."""

    universe: str = (
        "the n certified bias rows of the WIDEST window (width 0.75 V = "
        "[0.15, 0.90]), which is generation 9's wide_0.15_0.90 window, at one "
        "device. One Jacobian; every subset below is a row selection from it")
    nested_sequence: str = (
        "N_k = the k rows whose bias is closest to WIDTH_CENTRE = 0.525, ties "
        "to the lower bias. This is the order in which widening the window "
        "admits biases, so the nested sequence IS the width axis expressed as "
        "subsets of one matrix")
    null: str = (
        "uniformly random k-subsets of the same universe, so row count is "
        "matched by construction. This is the property pass 3 proved the "
        "spacing axis lacks, and it is why nothing here needs standardising")
    statistic: str = (
        "gap(S) = log10(sigma_1) - log10(sigma_2) of J[S, :]. Flatter is "
        "smaller. This is the gap behind the head")
    secondary: str = (
        "slope(S) = OLS slope of log10(sigma_i) against i for i = 1..min(4, k), "
        "computed for k >= 4 and REPORTED ONLY. The decision rests on gap "
        "alone, so there is no multiplicity to exploit")
    k_range: str = (
        "k from 2 to n-2 inclusive, and additionally C(n, k) >= 50 so the null "
        "has enough distinct subsets to place a percentile. k = n-1 and k = n "
        "are excluded because the nested set is then all but one row or the "
        "whole universe, where the null is nearly or exactly degenerate")
    percentile: str = (
        "P_k = fraction of null draws at k whose gap is <= the nested set's "
        "gap. Under the hypothesis that only row COUNT matters, arrival order "
        "is exchangeable and P_k is uniform")
    test_statistic: str = "T = mean over admissible k of P_k"
    null_of_T: str = (
        "random chains: a uniform permutation of the universe, its prefixes "
        "taken as a pseudo-nested sequence, scored against the SAME per-k null "
        "draws. p = the two-sided empirical position of T among chain values. "
        "This handles the dependence between nested sets at different k by "
        "construction, which combining per-k p-values under an independence "
        "assumption would not")
    threshold: str = (
        "two-sided, alpha = 0.05. 'Flattens more than random' is the "
        "hypothesised direction and the direction is reported; flattening LESS "
        "than random would equally refute genericity, and a one-sided test "
        "would be choosing in advance which way the evidence is allowed to "
        "point")
    decision_rule: str = (
        "IDENTITY_MATTERS iff p <= 0.05 at BOTH held-out devices, as in pass 3. "
        "Any other result, including one device clearing and the other not, is "
        "GENERIC_ROW_COUNT")
    held_out_devices: Tuple[str, ...] = HELD_OUT
    held_out_caveat: str = (
        "device_p10 and device_p90 were naive to the row side before pass 3 and "
        "are not naive now. The ruling specifies them, and pass 4's statistic "
        "was derived from pass 3's FAILURE MECHANISM -- the nuisance confound -- "
        "not from these devices' values. Stated rather than glossed: they are "
        "held out from pass 4's construction, not unseen")
    n_null_draws: int = N_NULL
    n_chain_draws: int = N_CHAIN
    seed: int = SEED
    indices: Tuple[int, ...] = INDICES
    minimum_k: int = 4
    minimum_k_why: str = (
        "fewer than four admissible k leaves T averaging over too little to "
        "place against the chain null. Reported as UNDETERMINED, which is a "
        "failure to measure and NOT a negative result. The threshold is a "
        "floor chosen to be conservative and is not claimed to be derived")
    why_not_a_contrast: str = (
        "passes 2 and 3 contrasted two axes that do not overlap in the nuisance "
        "parameter b. Pass 4 compares one sequence against a null matched on "
        "row count by construction, so the defect that sank both is absent by "
        "design rather than corrected after the fact")

    def measure_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["measure_hash"] = self.measure_hash()
        return out


OUTCOMES: Dict[str, str] = {
    "IDENTITY_MATTERS": (
        "the nested windows depart from the random-subset null at both "
        "held-out devices. Which biases arrive carries the flattening, not "
        "merely how many. MECH-01 closes as a regime question with its next "
        "step named -- which biases, answerable from this same artefact -- and "
        "L0 is reached"),
    "GENERIC_ROW_COUNT": (
        "the nested windows track the null. Flattening the spectrum is a "
        "consequence of row count alone, with nothing device-specific or "
        "regime-specific in it. This is a COMPLETE answer to MECH-01's "
        "question and the ruling of 2026-08-28 §3 requires it to be written as "
        "one: a deflationary answer is still an answer, not a failure"),
    "UNDETERMINED": (
        "the reproduction control failed, or fewer than the pre-registered "
        "minimum of admissible k was available at a held-out device. A failure "
        "to measure. It is not a negative result and may not be read as one"),
}

OUTCOMES_NOTE = (
    "pre-registered under the operator ruling of 2026-08-28 §3, hashed before "
    "the first subset was drawn. Neither outcome is the good outcome (AH-04, "
    "AH-13). Under that ruling's §4 both IDENTITY_MATTERS and GENERIC_ROW_COUNT "
    "CLOSE MECH-01; only UNDETERMINED counts as method three and triggers the "
    "U-EMPIR verdict")


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


def gap_behind_head(sv: np.ndarray) -> Optional[float]:
    """``log10(sigma_1) - log10(sigma_2)``, or ``None`` if degenerate."""
    if sv.size < 2 or sv[0] <= 0.0 or sv[1] <= 0.0:
        return None
    return float(np.log10(sv[0]) - np.log10(sv[1]))


def decay_slope(sv: np.ndarray) -> Optional[float]:
    """OLS slope of ``log10(sigma_i)`` on ``i``, ``i = 1..min(4, k)``."""
    m = min(4, int(sv.size))
    if m < 4:
        return None
    head = sv[:m]
    if np.any(head <= 0.0):
        return None
    i = np.arange(1, m + 1, dtype=np.float64)
    y = np.log10(head)
    return float(np.polyfit(i, y, 1)[0])


def subset_stats(jac: np.ndarray, rows: Any) -> Dict[str, Any]:
    """``rows`` is any integer index sequence -- a list or an ndarray of
    indices, since the null draws come straight from ``rng.choice``."""
    sv = np.linalg.svd(jac[np.asarray(rows, dtype=int), :],
                       compute_uv=False)
    return {"gap": gap_behind_head(sv), "slope": decay_slope(sv)}


def nested_order(biases: Sequence[float]) -> List[int]:
    """Row indices ordered as widening admits them: nearest the centre first."""
    b = np.asarray(biases, dtype=np.float64)
    return sorted(range(b.size),
                  key=lambda i: (abs(b[i] - WIDTH_CENTRE), b[i]))


def admissible_k(n: int) -> List[int]:
    return [k for k in range(2, n - 1) if comb(n, k) >= 50]


def analyse_device(jac: np.ndarray, biases: Sequence[float],
                   rng: np.random.Generator) -> Dict[str, Any]:
    """The whole test at one device. ``new_solves = 0``."""
    n = int(jac.shape[0])
    order = nested_order(biases)
    ks = admissible_k(n)

    per_k: List[Dict[str, Any]] = []
    null_gaps: Dict[int, np.ndarray] = {}
    for k in ks:
        draws = np.empty(N_NULL, dtype=np.float64)
        ok = 0
        for _ in range(N_NULL):
            rows = rng.choice(n, size=k, replace=False)
            g = subset_stats(jac, rows)["gap"]
            if g is not None:
                draws[ok] = g
                ok += 1
        null_gaps[k] = draws[:ok]
        nested_rows = order[:k]
        st = subset_stats(jac, nested_rows)
        p_k = (float(np.mean(null_gaps[k] <= st["gap"]))
               if st["gap"] is not None and ok else None)
        per_k.append({
            "k": k, "n_null_usable": ok,
            "nested_gap": st["gap"], "nested_slope": st["slope"],
            "null_gap_median": float(np.median(null_gaps[k])) if ok else None,
            "percentile": p_k,
            "nested_biases": [float(biases[i]) for i in nested_rows],
        })

    usable = [r for r in per_k if r["percentile"] is not None]
    if len(usable) < Pass4Measure.minimum_k:
        return {"n_rows": n, "k_admissible": ks, "per_k": per_k,
                "test_ran": False, "p_value": None, "T": None,
                "why": "fewer than the pre-registered minimum of admissible k"}

    T = float(np.mean([r["percentile"] for r in usable]))

    # The chain null: prefixes of a random permutation, same per-k null draws.
    chain_T = np.empty(N_CHAIN, dtype=np.float64)
    for c in range(N_CHAIN):
        perm = rng.permutation(n)
        vals = []
        for r in usable:
            k = r["k"]
            g = subset_stats(jac, perm[:k])["gap"]
            if g is not None and null_gaps[k].size:
                vals.append(float(np.mean(null_gaps[k] <= g)))
        chain_T[c] = float(np.mean(vals)) if vals else np.nan
    chain_T = chain_T[~np.isnan(chain_T)]

    mean_chain = float(np.mean(chain_T))
    lo = float(np.mean(chain_T <= T))
    hi = float(np.mean(chain_T >= T))
    p_two = float(min(1.0, 2.0 * min(lo, hi)))
    return {
        "n_rows": n,
        "k_admissible": ks,
        "per_k": per_k,
        "test_ran": True,
        "T": T,
        "chain_null_mean_T": mean_chain,
        "chain_null_n": int(chain_T.size),
        "p_lower": lo, "p_upper": hi, "p_value": p_two,
        "alpha": ALPHA_LEVEL,
        "clears_alpha": bool(p_two <= ALPHA_LEVEL),
        "direction": ("less flat than the null" if mean_chain < T
                      else "flatter than the null"),
    }


# ===========================================================================
# Phases
# ===========================================================================


def _theta16(sel: Dict[str, Any], dname: str, chart4, chart16) -> np.ndarray:
    if dname == "g8_control":
        th4 = np.asarray(_read("outputs/g9/rank_obs.json")["devices"]
                         ["g8_operating_point"]["theta_chartG_d4"],
                         dtype=np.float64)
    else:
        th4 = np.asarray(sel[dname]["theta_chartG_d4"], dtype=np.float64)
    return np.interp(chart16.anchors, chart4.anchors, th4)


def phase_pilot(grid_n: int, n_cells: int) -> Dict[str, Any]:
    print("=" * 74)
    print("PHASE 0  PILOT (PILOT-01): price the Jacobian capture before running")
    print("=" * 74)
    cfg = GlobalStudyConfig(n_anchor=4)
    t0 = time.perf_counter()
    sg, x_si = build_solver(cfg, grid_n)
    build_s = time.perf_counter() - t0
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    sel = {c["name"]: c for c in _read(G9_OP_POINTS)["selection"]["chosen"]}
    lo, hi = WIDTH_CENTRE - WIDEST / 2.0, WIDTH_CENTRE + WIDEST / 2.0
    t0 = time.perf_counter()
    cell_spectrum(sg, chart16, _theta16(sel, HELD_OUT[0], chart4, chart16),
                  window_biases(lo, hi, 16), cfg)
    per_cell = time.perf_counter() - t0
    doc = {"solver_build_s": build_s, "per_cell_s": per_cell,
           "n_cells_required": n_cells,
           "projected_s": build_s + per_cell * n_cells,
           "measured_not_estimated": True,
           "rule": "PILOT-01: priced by a measured pilot, never by an estimate"}
    print(f"  solver build   {build_s:8.2f} s")
    print(f"  one cell       {per_cell:8.2f} s")
    print(f"  {n_cells} cells        {doc['projected_s']:8.2f} s projected")
    return doc


def phase_preregister(out: Path, pilot: Optional[Dict[str, Any]]) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  PRE-REGISTRATION (AH-14): hashed before the first subset")
    print("=" * 74)
    m = Pass4Measure()
    doc = {
        "what_this_is": (
            "MECH-01 pass 4, the third distinct method. Row-subset growth "
            "against a random-row null, matched on row count by construction"),
        "authorised_by": "operator ruling of 2026-08-28 §3 (pass 4)",
        "terminal_condition": (
            "ruling §4: if this answers, MECH-01 closes and L0 is reached. If "
            "it is falsified or inconclusive it is method three, U-EMPIR is "
            "issued with all three methods and their mechanisms, the ladder "
            "descends to L1 with its reachability condition recorded, and the "
            "loop stops. No fourth method. Stated here, before the result"),
        "pilot": pilot,
        "distinct_from_passes_2_and_3": m.why_not_a_contrast,
        "new_solves": (
            "the Jacobian is recomputed once per device because nothing in the "
            "tree stores it, and is WRITTEN TO DISK so no later pass needs a "
            "solve. The analysis -- subsets, sub-spectra, percentiles, chains, "
            "verdict -- is arithmetic at new_solves = 0, AST-guarded by "
            "tests/test_mech01_pass4_g14.py"),
        "measure": m.to_dict(),
        "outcomes": OUTCOMES,
        "outcomes_note": OUTCOMES_NOTE,
        "outcomes_hash": _hash_outcomes(),
    }
    _write(out / "preregister.json", doc)
    print(f"  measure hash  {m.measure_hash()}")
    print(f"  outcomes hash {_hash_outcomes()}")
    print(f"  wrote {out / 'preregister.json'}")
    return doc


def phase_capture(out: Path, grid_n: int) -> Dict:
    """The only phase that solves. Writes the Jacobians so nothing else has to."""
    print()
    print("=" * 74)
    print("PHASE 2  CAPTURE the Jacobians at the widest window (the only solves)")
    print("=" * 74)
    cfg = GlobalStudyConfig(n_anchor=4)
    sg, x_si = build_solver(cfg, grid_n)
    chart4, chart16 = ChartG(4, x_si), ChartG(16, x_si)
    op = _read(G9_OP_POINTS)
    sel = {c["name"]: c for c in op["selection"]["chosen"]}
    lo, hi = WIDTH_CENTRE - WIDEST / 2.0, WIDTH_CENTRE + WIDEST / 2.0

    doc: Dict[str, Any] = {"devices": {}, "window_V": [lo, hi],
                           "width_V": float(WIDEST)}
    repro: List[Dict[str, Any]] = []
    t0 = time.perf_counter()
    for dname in list(HELD_OUT) + list(CONTRAST):
        m16 = _theta16(sel, dname, chart4, chart16)
        rec, jac, _ = cell_spectrum(sg, chart16, m16,
                                    window_biases(lo, hi, 16), cfg)
        jac = np.asarray(jac, dtype=np.float64)
        doc["devices"][dname] = {
            "jacobian": jac.tolist(),
            "shape": list(jac.shape),
            "biases_used": rec["biases_used"],
            "rows_used": rec["rows_used"],
            "singular_values": rec["singular_values"],
        }
        key = ("g8_control" if dname == "g8_control" else dname)
        stored = (op["operating_points"][f"{key}__wide_0.15_0.90"]
                  ["cells"]["G_d16"]["singular_values"])
        for k in INDICES:
            if k - 1 < len(stored):
                repro.append({
                    "device": dname, "index": k,
                    "generation_9": stored[k - 1],
                    "here": rec["singular_values"][k - 1],
                    "identical": bool(
                        stored[k - 1] == rec["singular_values"][k - 1]),
                })
        print(f"  {dname:<20s} J {jac.shape[0]:2d} x {jac.shape[1]:2d}  "
              f"rows_used {rec['rows_used']}")

    doc["reproduction_control_R1"] = {
        "rows": repro,
        "n_identical": sum(1 for r in repro if r["identical"]),
        "of": len(repro),
        "all_identical": bool(repro and all(r["identical"] for r in repro)),
        "why": ("this window IS generation 9's wide_0.15_0.90 window, so its "
                "singular values must reproduce op_points.json bit for bit or "
                "the Jacobian is not the object SPEC-g9-1 measured"),
    }
    doc["wall_clock_s"] = time.perf_counter() - t0
    r1 = doc["reproduction_control_R1"]
    print(f"\n  R1'' reproduction: {r1['n_identical']} of {r1['of']} "
          f"bit-identical -> {'PASS' if r1['all_identical'] else 'FAIL'}")
    _write(out / "jacobians.json", doc)
    print(f"  wrote {out / 'jacobians.json'}")
    return doc


def phase_analyse(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  the null. Arithmetic over the stored Jacobians, new_solves = 0")
    print("=" * 74)
    cap = json.loads((out / "jacobians.json").read_text(encoding="utf-8"))
    devices: Dict[str, Any] = {}
    for dname, rec in cap["devices"].items():
        rng = np.random.default_rng(SEED)
        jac = np.asarray(rec["jacobian"], dtype=np.float64)
        res = analyse_device(jac, rec["biases_used"], rng)
        devices[dname] = res
        role = "HELD OUT" if dname in HELD_OUT else "contrast"
        print(f"\n  {dname}  ({role})  n = {res['n_rows']}  "
              f"k in {res['k_admissible'][0]}..{res['k_admissible'][-1]}")
        for r in res["per_k"]:
            if r["percentile"] is None:
                continue
            print(f"    k={r['k']:2d}  nested gap {r['nested_gap']:+.4f}  "
                  f"null median {r['null_gap_median']:+.4f}  "
                  f"percentile {r['percentile']:.4f}")
        if res["test_ran"]:
            print(f"    T = {res['T']:.4f}   chain null mean "
                  f"{res['chain_null_mean_T']:.4f}   "
                  f"two-sided p = {res['p_value']:.5f}  "
                  f"{'CLEARS' if res['clears_alpha'] else 'does NOT clear'} "
                  f"0.05  ({res['direction']})")
    doc = {"devices": devices, "new_solves": 0, "seed": SEED,
           "n_null": N_NULL, "n_chain": N_CHAIN}
    _write(out / "null_test.json", doc)
    print(f"\n  wrote {out / 'null_test.json'}")
    return doc


def phase_verdict(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 4  VERDICT against the pre-registration")
    print("=" * 74)
    pre = json.loads((out / "preregister.json").read_text(encoding="utf-8"))
    cap = json.loads((out / "jacobians.json").read_text(encoding="utf-8"))
    res = json.loads((out / "null_test.json").read_text(encoding="utf-8"))

    r1_ok = bool(cap["reproduction_control_R1"]["all_identical"])
    held = {d: res["devices"][d] for d in HELD_OUT}
    ran = all(h["test_ran"] for h in held.values())
    if not r1_ok or not ran:
        outcome = "UNDETERMINED"
    elif all(h["clears_alpha"] for h in held.values()):
        outcome = "IDENTITY_MATTERS"
    else:
        outcome = "GENERIC_ROW_COUNT"

    doc = {
        "outcome": outcome,
        "meaning": OUTCOMES[outcome],
        "measure_hash": pre["measure"]["measure_hash"],
        "outcomes_hash": pre["outcomes_hash"],
        "hashes_match_preregistration": bool(
            pre["measure"]["measure_hash"] == Pass4Measure().measure_hash()
            and pre["outcomes_hash"] == _hash_outcomes()),
        "reproduction_control_R1": {
            "pass": r1_ok,
            "n_identical": cap["reproduction_control_R1"]["n_identical"],
            "of": cap["reproduction_control_R1"]["of"]},
        "held_out": {d: {"T": h["T"], "p_value": h["p_value"],
                         "clears_alpha": h["clears_alpha"],
                         "direction": h.get("direction")}
                     for d, h in held.items()},
        "contrast_devices": {
            d: {"T": res["devices"][d]["T"],
                "p_value": res["devices"][d]["p_value"],
                "clears_alpha": res["devices"][d]["clears_alpha"]}
            for d in CONTRAST if d in res["devices"]},
        "decision_rule": Pass4Measure.decision_rule,
        "closes_mech01": outcome in ("IDENTITY_MATTERS", "GENERIC_ROW_COUNT"),
        "new_solves": 0,
        "arithmetic_only": True,
    }
    for d, h in doc["held_out"].items():
        print(f"  {d:<20s} T = {h['T']:.4f}   p = {h['p_value']:.5f}   "
              f"{'CLEARS' if h['clears_alpha'] else 'does NOT clear'}")
    for d, h in doc["contrast_devices"].items():
        print(f"  {d:<20s} T = {h['T']:.4f}   p = {h['p_value']:.5f}   "
              f"(contrast, not part of the rule)")
    print(f"\n  R1'' reproduction: {'PASS' if r1_ok else 'FAIL'}")
    print(f"  OUTCOME: {outcome}")
    print(f"  closes MECH-01: {doc['closes_mech01']}")
    _write(out / "verdict.json", doc)
    print(f"  wrote {out / 'verdict.json'}")
    return doc


ALL_PHASES = ["pilot", "preregister", "capture", "analyse", "verdict"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g14/mech01_pass4")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    pilot = None
    n_cells = len(HELD_OUT) + len(CONTRAST)
    if "pilot" in phases:
        pilot = phase_pilot(args.grid, n_cells)
        _write(out / "pilot.json", pilot)
    if "preregister" in phases:
        phase_preregister(out, pilot)
    if "capture" in phases:
        phase_capture(out, args.grid)
    if "analyse" in phases:
        phase_analyse(out)
    if "verdict" in phases:
        phase_verdict(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
