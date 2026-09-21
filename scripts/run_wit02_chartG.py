"""``WIT-02`` for chart G: the ten witness pairs that were never refined.

    PYTHONPATH=src python scripts/run_wit02_chartG.py --out outputs/wit02_chartG

What this is, and what authorises it
------------------------------------
The closing ruling of 2026-08-26 ended the technical work and permitted
arithmetic on existing artefacts only. This step is **new solving**, and it runs
under one narrow later authorisation -- the operator ruling of 2026-08-28 §2:

    Authorised, narrowly: refine chart G's remaining ten pairs, recompute
    barriers, update the register. No new witnesses, no new charts, no new
    windows, no chart L.

The scope is enforced here rather than promised. This module reads one witness
set, ``chart_G_d4`` from ``outputs/g8/reproduce.json``, and constructs no others;
:class:`RefinementScope` names it and is hashed before anything is solved.

Why chart G and not chart L, when chart L is the uncovered one
--------------------------------------------------------------
``WIT-02``'s register at close reported chart G at 3 of 13, chart L at 0 of 37
and chart J at 13 of 13, and assigned the exposure to chart L because chart L
carries the dimension reading. The ruling reassigns it on the margins:

* chart L is uncovered and its median barrier is **212 floor units**. A basin
  that deep does not become a ridge because some of its members separate under
  refinement; the classification survives losing members.
* chart G is at **3 of 13** and its median barrier is **8.31 log-units against a
  floor barrier of 8.0** -- a **3.9% margin**, and the ridge is precisely the
  claim that lives at the floor, which is where generation 9 measured refinement
  to bite. Ten of its thirteen pairs had never been tested.

So the fragile claim is the ridge, and the cost of having enacted ``WIT-02`` is
closing its tightest margin.

The phases
----------
``preregister``
    ``AH-14``. The scope, the battery and the recount rule, hashed to disk
    **before any solve**. Every later phase recomputes the hashes and refuses to
    run on a mismatch. It also refuses to run if generation 9's
    ``BarrierCriterion`` or generation 10's ``RidgeBasinDecision`` has moved
    since they were registered, because a recount under a changed criterion is a
    new measurement wearing the old one's name.
``refine``
    All thirteen chart-G witness pairs through generation 6's battery -- three
    grids, two tolerances. The three generation 6 already did are a
    **reproduction control**; the ten it never did are the measurement. One
    null-control pair goes through the same battery as the **negative control**:
    a battery that cannot separate two ordinary draws cannot evidence that a
    witness pair is inseparable.
``recount``
    Barriers over the surviving set, through ``run_g10._barrier_set`` -- the
    same imported function that produced ``outputs/g10/ridge_basin.json`` -- and
    the same registered classifier. The full thirteen are re-measured first and
    must reproduce generation 10's depths exactly.
``register``
    ``outputs/close/wit02_register_v2.json``: the close register with chart G's
    row remeasured. Version 1 is left on disk unchanged; it is the record of
    what the coverage was when the rule was enacted.

Pre-registered, before the run, by the ruling itself
----------------------------------------------------
    *If it flips the ridge, that is the result.* Spine item 4 changes, the ridge
    becomes a fourth basin or a provisional finding, and it is reported that way
    in the same paragraph as the flip.

:data:`OUTCOMES` carries that as a table keyed by the classifier's own output,
written into ``preregister.json`` with its hash before the first solve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_g9 import (
    REFINEMENT_GRIDS,
    REFINEMENT_TOLS,
    BarrierCriterion,
    build_solver,
    iv,
    obs_dist,
)
from run_g10 import RidgeBasinDecision, _barrier_set, classify

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.utils.provenance import RunManifest

ROOT = Path(__file__).resolve().parents[1]

G8_REPRODUCE = "outputs/g8/reproduce.json"
G6_FALSIFIER = "outputs/witness_falsifier_g6/witness_falsifier.json"
G9_PREREGISTER = "outputs/g9/preregister.json"
G10_PREREGISTER = "outputs/g10/preregister.json"
G10_RIDGE_BASIN = "outputs/g10/ridge_basin.json"
WIT01 = "outputs/g10/wit01.json"
REGISTER_V1 = "outputs/close/wit02_register.json"
REGISTER_V2 = "outputs/close/wit02_register_v2.json"

#: The one set this step is authorised to touch.
SET_LABEL = "chart_G_d4"


# ===========================================================================
# Pre-registration -- written and hashed BEFORE anything is solved
# ===========================================================================

@dataclass(frozen=True)
class RefinementScope:
    """Which pairs go through which battery, and what counts as survival.

    Nothing here is new. The battery is generation 6's, inherited through
    generation 9 unchanged, and the point of stating it as a hashed object is
    that a battery quietly loosened for the ten new pairs would make them
    incomparable with the three old ones while every number still looked fine.
    """

    set_label: str = SET_LABEL
    source_artefact: str = G8_REPRODUCE
    charts_touched: Tuple[str, ...] = ("G",)
    n_pairs_offered: int = 13
    refined_at_generation_6: Tuple[int, ...] = (0, 1, 2)
    battery_grids: Tuple[int, ...] = REFINEMENT_GRIDS
    battery_tolerances: Tuple[str, ...] = tuple(t[0] for t in REFINEMENT_TOLS)
    tol_carrier_tight: float = 1e-12
    max_outer_tight: int = 200
    survives_iff: str = (
        "the observational distance is below the distinguishability floor at "
        "every one of the six refinement rows -- three grids by two tolerances")
    battery_inherited_from: str = (
        "run_g9.REFINEMENT_GRIDS and run_g9.REFINEMENT_TOLS, imported rather "
        "than restated; generation 9 inherited them from "
        "scripts/run_witness_falsifier.py, which is the battery generation 6 "
        "ran on the three pairs")
    reproduction_control: str = (
        "the three pairs generation 6 refined are re-run here through "
        "generation 9's code path. Their N=301 default distances must "
        "reproduce outputs/witness_falsifier_g6/witness_falsifier.json "
        "exactly. If they do not, the ten new pairs are not commensurate with "
        "the three old ones and the coverage figure would be summing two "
        "different measurements")
    negative_control: str = (
        "one chart-G null-control pair -- consecutive ordinary prior draws in "
        "draw order that form no witness pair, the same construction "
        "run_g10._barrier_set uses for its null -- through the same battery. "
        "It must NOT survive. A battery that reports two distinguishable "
        "devices as inseparable cannot evidence that a witness pair is")
    negative_control_if_it_survives: str = (
        "reported as measured and NOT swapped for another pair. A null pair "
        "below the floor is not a broken battery, it is a witness the "
        "generation-6 search missed, and re-picking until the control behaves "
        "is the tuning PH-11 forbids")
    scope_note: str = (
        "no new witnesses, no new charts, no new windows, no chart L. The "
        "pairs are read from the committed set; none is constructed here")

    def scope_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["scope_hash"] = self.scope_hash()
        return out


@dataclass(frozen=True)
class RecountRule:
    """How the barriers are recounted once survival is known.

    The refinement decides **which pairs are counted**. It does not change the
    criterion, the grid, or any depth: a pair that survives has exactly the
    barrier generation 10 measured for it, because it is the same pair walked by
    the same function on the same grid.

    That is the whole content of the rule, and it is worth hashing because the
    tempting alternative -- recomputing barriers on the *refined* grid, where
    the surviving pairs would have new and probably deeper depths -- would
    silently replace ``SPEC-g10-2``'s measurement with a different one and
    compare it against generation 10's other two sets, which were not measured
    that way.
    """

    barriers_are: str = (
        "generation 9's BarrierCriterion, imported unchanged, at the "
        "production grid N=301 -- the criterion outputs/g10/ridge_basin.json "
        "was measured under")
    recompute_through: str = (
        "run_g10._barrier_set, imported; the same function that produced "
        "outputs/g10/ridge_basin.json")
    refinement_changes: str = "which pairs are counted, and nothing else"
    reproduction_control: str = (
        "the full thirteen-pair set is re-measured first and every per-pair "
        "depth must reproduce outputs/g10/ridge_basin.json bit-identically. A "
        "recount over depths that do not reproduce is a new measurement "
        "wearing the old one's name")
    counted_set: str = (
        "the pairs that survive the battery, in their committed order")
    null_control: str = (
        "as in run_g10._barrier_set: consecutive non-witness draws taken in "
        "draw order, one per counted witness pair. A smaller counted set takes "
        "a prefix of the same ordered list, so the null is not re-drawn")
    classifier: str = (
        "run_g10.classify against RidgeBasinDecision, unchanged: RIDGE if at "
        "least ridge_fraction of counted pairs are at or below the floor "
        "barrier, BASIN if none is, MIXED otherwise")
    ridge_fraction: float = RidgeBasinDecision().ridge_fraction
    what_is_not_recomputed: str = (
        "chart L and chart J. Their sets are untouched, so generation 10's "
        "numbers for them stand and the three-set comparison stays one "
        "measurement rather than two spliced together")

    def rule_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["rule_hash"] = self.rule_hash()
        return out


#: What each classifier output means, fixed before the first solve.
#:
#: The ruling pre-registered the reporting itself -- *"if it flips the ridge,
#: that is the result"* -- which is the half that usually goes missing. These
#: are keyed on ``run_g10.classify``'s own output so that no reading is
#: available that the classifier does not produce.
OUTCOMES: Dict[str, str] = {
    "RIDGE": (
        "the ridge stands and is no longer a claim about three pairs. Spine "
        "item 4 keeps its classification and gains its coverage: 13 of 13 "
        "refined, n surviving, at the recounted margin. The 3.9% margin the "
        "ruling flagged is either confirmed or moves, and the moved value is "
        "the one reported"),
    "BASIN": (
        "the ridge flips. Chart G at d=4 becomes a fourth cell in which no "
        "path below the floor barrier was found, the ridge/basin contrast has "
        "no ridge left in it, and the dimension reading -- which rests on d=4 "
        "being the only cell at the floor -- loses its only positive case. "
        "Spine item 4 is rewritten and the flip is stated in the same "
        "paragraph as the classification, not in a limitations list"),
    "MIXED": (
        "the ridge becomes provisional at the recounted fraction: some pairs "
        "sit at the floor and fewer than ridge_fraction of them do. Spine item "
        "4 reports the fraction and the coverage, and the word ridge is "
        "retired from it as a classification"),
    "UNDETERMINED": (
        "no counted pair has a certified barrier. Reported as a failure to "
        "measure, and generation 10's classification stands with its 3-of-13 "
        "coverage unchanged"),
}

OUTCOMES_NOTE = (
    "pre-registered by the operator ruling of 2026-08-28 section 2, before "
    "this run: 'If it flips the ridge, that is the result.' Reported either "
    "way (AH-04, AH-13)")


def _hash_outcomes() -> str:
    return hashlib.sha256(
        json.dumps({"outcomes": OUTCOMES, "note": OUTCOMES_NOTE},
                   sort_keys=True).encode("utf-8")).hexdigest()


def _read(rel: str) -> Dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def phase_preregister(out: Path) -> Dict:
    print("=" * 74)
    print("PHASE 0  PRE-REGISTRATION (AH-14): the scope and the rules, first")
    print("=" * 74)
    scope, rule, crit, dec = (RefinementScope(), RecountRule(),
                              BarrierCriterion(), RidgeBasinDecision())

    # The two objects this recount inherits are checked against the generations
    # that registered them. A criterion that moved would make the recount
    # incomparable with the numbers it is recounting, and the failure would be
    # invisible in every downstream number.
    inherited = {
        "barrier_criterion_hash": crit.criterion_hash(),
        "registered_at_generation_9":
            _read(G9_PREREGISTER)["barrier_criterion"]["criterion_hash"],
        "registered_at_generation_10":
            _read(G10_PREREGISTER)["barrier_criterion"]["criterion_hash"],
        "ridge_basin_decision_hash": dec.decision_hash(),
        "ridge_basin_registered_at_generation_10":
            _read(G10_PREREGISTER)["ridge_basin_decision"]["decision_hash"],
    }
    if inherited["barrier_criterion_hash"] != inherited[
            "registered_at_generation_9"]:
        raise SystemExit(
            "the barrier criterion has moved since generation 9 registered it. "
            "A recount under a changed criterion is a new measurement wearing "
            "the old one's name; AH-14 forbids continuing.")
    if inherited["ridge_basin_decision_hash"] != inherited[
            "ridge_basin_registered_at_generation_10"]:
        raise SystemExit(
            "the ridge/basin decision has moved since generation 10 registered "
            "it. The classification would not be the one the result reports.")

    doc = {
        "written_before": ("any solve in this step. The refine and recount "
                           "phases recompute these hashes and refuse to run on "
                           "a mismatch."),
        "authorisation": (
            "operator ruling of 2026-08-28 section 2, narrow: refine chart G's "
            "remaining ten pairs, recompute barriers, update the register. No "
            "new witnesses, no new charts, no new windows, no chart L. This is "
            "the only solving step authorised after the close of 2026-08-26, "
            "and it exists because WIT-02 -- the operator's own rule -- opened "
            "a gap under the one claim the closing ruling declared safe."),
        "why_this_set": (
            "chart G carries the ridge, its median barrier is 8.31 log-units "
            "against a floor barrier of 8.0 (a 3.9% margin), and 10 of its 13 "
            "pairs had never been refined. Chart L is uncovered but its median "
            "is 212 floor units: a basin that deep does not become a ridge by "
            "losing members. The exposed claim is the one at the floor."),
        "refinement_scope": scope.to_dict(),
        "recount_rule": rule.to_dict(),
        "inherited_hashes": inherited,
        "outcomes": {"table": OUTCOMES, "note": OUTCOMES_NOTE,
                     "outcomes_hash": _hash_outcomes()},
        "what_would_falsify_the_ridge": (
            "fewer than ridge_fraction = 1/3 of the surviving pairs at or "
            "below the floor barrier. Generation 10 measured 6 of 13 = 0.462; "
            "the ridge survives losing at most three of those six if nothing "
            "else changes, and the arithmetic is stated here rather than after "
            "the fact."),
    }
    for k, h in (("refinement_scope", scope.scope_hash()),
                 ("recount_rule", rule.rule_hash()),
                 ("outcomes", _hash_outcomes()),
                 ("barrier_criterion (inherited)", crit.criterion_hash()),
                 ("ridge_basin_decision (inherited)", dec.decision_hash())):
        print(f"  {k:34s} {h[:32]}...")
    return doc


def _check_preregistration(out: Path) -> Dict:
    """Refuse to measure against a pre-registration that has moved."""
    path = out / "preregister.json"
    if not path.exists():
        raise SystemExit(
            "no preregister.json: run the 'preregister' phase first. A rule "
            "written after the measurement is not a pre-registration.")
    doc = json.loads(path.read_text(encoding="utf-8"))
    for key, on_disk, now in (
            ("refinement_scope", doc["refinement_scope"]["scope_hash"],
             RefinementScope().scope_hash()),
            ("recount_rule", doc["recount_rule"]["rule_hash"],
             RecountRule().rule_hash()),
            ("outcomes", doc["outcomes"]["outcomes_hash"], _hash_outcomes()),
            ("barrier_criterion",
             doc["inherited_hashes"]["barrier_criterion_hash"],
             BarrierCriterion().criterion_hash()),
            ("ridge_basin_decision",
             doc["inherited_hashes"]["ridge_basin_decision_hash"],
             RidgeBasinDecision().decision_hash())):
        if on_disk != now:
            raise SystemExit(
                f"{key} has changed since it was registered.\n"
                f"  registered: {on_disk}\n  now:        {now}\n"
                "AH-14 forbids continuing.")
    return doc


# ===========================================================================
# Phase 1 -- the battery
# ===========================================================================

def _battery(cfg, kept: np.ndarray, ia: int, ib: int,
             floor: float) -> List[Dict]:
    """Generation 6's battery on one pair: three grids, two tolerances."""
    biases = list(cfg.biases)
    rows: List[Dict] = []
    for grid in REFINEMENT_GRIDS:
        for tname, sg_cfg in REFINEMENT_TOLS:
            sg_r, x_r = build_solver(cfg, grid, sg_cfg)
            Gr = ChartG(4, x_r)
            Ia, tra, cva = iv(sg_r, Gr.charted(kept[ia]), biases)
            Ib, trb, cvb = iv(sg_r, Gr.charted(kept[ib]), biases)
            mask = tra & cva & trb & cvb
            d = obs_dist(Ia, Ib, mask)
            rows.append({
                "grid_n": grid, "tolerance": tname,
                "tol_carrier": float(sg_cfg.tol_carrier),
                "observational_distance": d,
                "n_biases_certified": int(np.sum(mask)),
                "n_biases": len(biases),
                "below_floor": bool(d < floor),
            })
    return rows


def phase_refine(cfg, out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  WIT-02  all thirteen chart-G witness pairs, one battery")
    print("=" * 74)
    scope = RefinementScope()
    rep = _read(G8_REPRODUCE)[SET_LABEL]
    kept = np.asarray(rep["kept_log10"], dtype=np.float64)
    pairs = [tuple(p) for p in rep["witness_pair_indices"]]
    dists = rep["witness_pair_distance"]
    seps = rep["witness_pair_separation"]
    floor = cfg.distinguishability_floor
    if len(pairs) != scope.n_pairs_offered:
        raise SystemExit(
            f"the committed chart-G set has {len(pairs)} pairs and the "
            f"pre-registered scope names {scope.n_pairs_offered}")

    # Which pairs generation 6 already put through this battery, established by
    # the same exact-equality match the WIT-02 register uses -- not by position
    # and not by the ``pairs[:3]`` slice that produced them.
    g6 = _read(G6_FALSIFIER)
    g6_by_sep = {float(r["separation_decades"]): r for r in g6["pairs"]}
    prior = [i for i, s in enumerate(seps) if float(s) in g6_by_sep]

    print(f"  {len(pairs)} pairs, floor {floor:.2e}, "
          f"battery N={list(REFINEMENT_GRIDS)} x "
          f"{[t[0] for t in REFINEMENT_TOLS]}")
    print(f"  generation 6 refined pairs {prior} (matched by separation, not "
          f"by position); the other {len(pairs) - len(prior)} are the "
          f"measurement")

    records: List[Dict] = []
    for pi, (ia, ib) in enumerate(pairs):
        t0 = time.perf_counter()
        rows = _battery(cfg, kept, ia, ib, floor)
        base = float(rows[0]["observational_distance"])
        finest = float(rows[-1]["observational_distance"])
        rec = {
            "pair_index": pi,
            "member_indices": [int(ia), int(ib)],
            "separation_decades": float(seps[pi]),
            "g8_observational_distance": float(dists[pi]),
            "headroom_fraction_of_floor": float(dists[pi]) / floor,
            "previously_refined_at_generation_6": pi in prior,
            "refinements": rows,
            "distance_at_301_default": base,
            "distance_at_1201_tight": finest,
            "distance_rose": bool(finest > base),
            "relative_change": float((finest - base) / base) if base else 0.0,
            "survives_refinement": bool(all(r["below_floor"] for r in rows)),
            "wall_clock_s": time.perf_counter() - t0,
        }
        records.append(rec)
        flag = "  [g6]" if rec["previously_refined_at_generation_6"] else ""
        print(f"    pair {pi:2d}  d(N=301) {base:.4e} "
              f"({100.0 * rec['headroom_fraction_of_floor']:5.1f}% of floor)  "
              f"-> {finest:.4e} "
              f"({'ROSE' if rec['distance_rose'] else 'fell'} "
              f"{100.0 * rec['relative_change']:+.1f}%)  "
              f"survives={rec['survives_refinement']}{flag}")

    # -- the reproduction control -------------------------------------------
    repro_rows = []
    for pi in prior:
        rec = records[pi]
        g6rec = g6_by_sep[rec["separation_decades"]]
        g6_301 = float(g6rec["refinements"][0]["observational_distance"])
        here = rec["distance_at_301_default"]
        repro_rows.append({
            "pair_index": pi,
            "separation_decades": rec["separation_decades"],
            "generation_6_distance_at_301_default": g6_301,
            "here": here,
            "identical": bool(here == g6_301),
            "relative_difference": (abs(here - g6_301) / g6_301) if g6_301 else None,
            "generation_6_survives": bool(g6rec["survives_refinement"]),
            "here_survives": rec["survives_refinement"],
            "verdict_agrees": bool(
                bool(g6rec["survives_refinement"]) == rec["survives_refinement"]),
        })
    repro = {
        "rows": repro_rows,
        "n": len(repro_rows),
        "all_identical": bool(repro_rows and all(r["identical"] for r in repro_rows)),
        "all_verdicts_agree": bool(
            repro_rows and all(r["verdict_agrees"] for r in repro_rows)),
        "why": scope.reproduction_control,
        "what_it_controls_for": (
            "two code paths. Generation 6 solved through "
            "run_witness_falsifier.solve_profile; this runs through "
            "run_g9.build_solver and run_g9.iv. Bit-identical distances mean "
            "the ten new pairs and the three old ones are one measurement."),
    }
    print(f"\n  reproduction control: {repro['n']} pairs re-run through the "
          f"generation-9 path, bit-identical: {repro['all_identical']}, "
          f"verdicts agree: {repro['all_verdicts_agree']}")

    # -- the negative control ------------------------------------------------
    witness_set = {tuple(sorted(p)) for p in pairs}
    null_pair: Optional[Tuple[int, int]] = None
    i = 0
    while i + 1 < len(kept):
        cand = (i, i + 1)
        if tuple(sorted(cand)) not in witness_set:
            null_pair = cand
            break
        i += 2
    if null_pair is None:
        raise SystemExit("no null-control pair available")
    nrows = _battery(cfg, kept, null_pair[0], null_pair[1], floor)
    neg = {
        "pair": [int(null_pair[0]), int(null_pair[1])],
        "construction": scope.negative_control,
        "refinements": nrows,
        "distance_at_301_default": float(nrows[0]["observational_distance"]),
        "distance_at_1201_tight": float(nrows[-1]["observational_distance"]),
        "n_rows_below_floor": sum(1 for r in nrows if r["below_floor"]),
        "survives_refinement": bool(all(r["below_floor"] for r in nrows)),
        "floor": floor,
        "if_it_survives": scope.negative_control_if_it_survives,
    }
    neg["passes"] = bool(not neg["survives_refinement"])
    print(f"  negative control: null pair {neg['pair']} distance "
          f"{neg['distance_at_301_default']:.4e} against floor {floor:.2e}, "
          f"{neg['n_rows_below_floor']}/6 rows below floor -> "
          f"{'PASS' if neg['passes'] else 'FAIL'}")

    n_survive = sum(1 for r in records if r["survives_refinement"])
    surviving = [r["pair_index"] for r in records if r["survives_refinement"]]
    separated = [r["pair_index"] for r in records
                 if not r["survives_refinement"]]

    # The generation-10 reading of what predicts survival, tested rather than
    # assumed on a second set. It was measured on chart J and stated there as a
    # property of that set; whether it transfers is a question this run can
    # answer for free, and it is reported either way.
    surv_d = [records[i]["g8_observational_distance"] for i in surviving]
    sep_d = [records[i]["g8_observational_distance"] for i in separated]
    headroom = {
        "generation_10_reading": (
            "on chart J, survival was predicted exactly by headroom against "
            "the floor: the 7 survivors were the 7 smallest distances at "
            "N=301 (max 0.01844) and the 6 that separated were the 6 largest "
            "(min 0.01873)"),
        "max_distance_among_survivors": max(surv_d) if surv_d else None,
        "min_distance_among_separated": min(sep_d) if sep_d else None,
        "perfectly_ordered": bool(
            surv_d and sep_d and max(surv_d) < min(sep_d)),
        "n_survivors": len(surviving),
        "n_separated": len(separated),
        "status": ("a free check on an existing artefact set, reported either "
                   "way; it is not what this run was authorised to establish"),
    }

    print(f"\n  {n_survive}/{len(records)} pairs stay below the floor at every "
          f"refinement")
    print(f"  separated: {separated}")
    return {
        "records": records,
        "reproduction_control": repro,
        "negative_control": neg,
        "headroom_check": headroom,
        "battery": {"grids": list(REFINEMENT_GRIDS),
                    "tolerances": [t[0] for t in REFINEMENT_TOLS],
                    "tol_carrier_tight": 1e-12,
                    "inherited_from": scope.battery_inherited_from},
        "verdict": {
            "set": SET_LABEL,
            "n_pairs": len(records),
            "n_refined_here": len(records),
            "n_surviving": n_survive,
            "n_separated_by_refinement": len(records) - n_survive,
            "surviving_pair_indices": surviving,
            "separated_pair_indices": separated,
            "coverage_after_this_run": 1.0,
            "floor": floor,
        },
    }


# ===========================================================================
# Phase 2 -- the recount
# ===========================================================================

def phase_recount(cfg, out: Path, grid_n: int) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  the barriers, recounted over the surviving set")
    print("=" * 74)
    refine = json.loads((out / "refine.json").read_text(encoding="utf-8"))
    crit, dec = BarrierCriterion(), RidgeBasinDecision()
    rep = _read(G8_REPRODUCE)[SET_LABEL]
    kept = np.asarray(rep["kept_log10"], dtype=np.float64)
    pairs = [tuple(p) for p in rep["witness_pair_indices"]]
    biases = list(cfg.biases)
    sg, x_si = build_solver(cfg, grid_n)
    chart = ChartG(4, x_si)
    print(f"  criterion {crit.criterion_hash()[:32]}...  (generation 9's)")
    print(f"  decision  {dec.decision_hash()[:32]}...  (generation 10's)")

    # -- the full set, as a reproduction control -----------------------------
    t0 = time.perf_counter()
    full = _barrier_set(sg, chart, cfg, biases, kept, pairs, crit,
                        SET_LABEL + "__all_13")
    full["classification"] = classify(full, dec)
    g10 = _read(G10_RIDGE_BASIN)["sets"][SET_LABEL]
    rows = []
    for here, there in zip(full["witness_pair_barriers"],
                           g10["witness_pair_barriers"]):
        a, b = here.get("barrier_depth"), there.get("barrier_depth")
        rows.append({
            "pair": here["pair"],
            "generation_10_depth": b,
            "here": a,
            "identical": bool(a == b),
        })
    repro = {
        "rows": rows,
        "all_identical": bool(rows and all(r["identical"] for r in rows)),
        "median_here": full["witness_depth_median"],
        "median_at_generation_10": g10["witness_depth_median"],
        "median_identical": bool(
            full["witness_depth_median"] == g10["witness_depth_median"]),
        "below_floor_here": full["witness_pairs_below_the_floor_barrier"],
        "below_floor_at_generation_10":
            g10["witness_pairs_below_the_floor_barrier"],
        "why": RecountRule().reproduction_control,
        "wall_clock_s": time.perf_counter() - t0,
    }
    print(f"  reproduction of generation 10's thirteen depths: "
          f"{repro['all_identical']} "
          f"(median {repro['median_here']:.4f} against "
          f"{repro['median_at_generation_10']:.4f})")
    if not repro["all_identical"]:
        print("  !! the recount is NOT comparable with generation 10 and the "
              "surviving-set numbers below must be read as a new measurement")

    # -- the counted set ------------------------------------------------------
    surviving = refine["verdict"]["surviving_pair_indices"]
    counted = [pairs[i] for i in surviving]
    if counted:
        sub = _barrier_set(sg, chart, cfg, biases, kept, counted, crit,
                           SET_LABEL + "__WIT02")
        sub["classification"] = classify(sub, dec)
    else:
        sub = {"tag": SET_LABEL + "__WIT02", "n_witness_pairs": 0,
               "classification": {"class": "UNDETERMINED",
                                  "fraction_below_floor": None}}

    # The same pair walked twice by a deterministic function must give the same
    # depth. If it does not, the subset numbers are not a subset of anything.
    by_pair = {tuple(e["pair"]): e.get("barrier_depth")
               for e in full["witness_pair_barriers"]}
    consistency = [{"pair": e["pair"],
                    "depth_in_full_run": by_pair.get(tuple(e["pair"])),
                    "depth_in_counted_run": e.get("barrier_depth"),
                    "identical": bool(
                        by_pair.get(tuple(e["pair"])) == e.get("barrier_depth"))}
                   for e in sub.get("witness_pair_barriers", [])]

    cls = sub["classification"]["class"]
    verdict = {
        "counted_pairs": len(counted),
        "of_offered": len(pairs),
        "coverage": 1.0,
        "classification_over_the_surviving_set": cls,
        "classification_at_generation_10": g10["classification"]["class"],
        "flipped": bool(cls != g10["classification"]["class"]),
        "fraction_below_floor_here": sub["classification"].get(
            "fraction_below_floor"),
        "fraction_below_floor_at_generation_10":
            g10["classification"]["fraction_below_floor"],
        "ridge_fraction": dec.ridge_fraction,
        "reading": OUTCOMES.get(cls, OUTCOMES["UNDETERMINED"]),
        "reading_was_registered_before_the_run": True,
        "outcomes_hash": _hash_outcomes(),
    }
    if counted:
        verdict["median_depth_over_the_surviving_set"] = sub[
            "witness_depth_median"]
        verdict["median_in_floor_units"] = sub["witness_median_in_floor_units"]
        verdict["median_at_generation_10"] = g10["witness_depth_median"]
        verdict["median_in_floor_units_at_generation_10"] = g10[
            "witness_median_in_floor_units"]
        verdict["margin_against_the_floor_barrier_percent"] = float(
            100.0 * (sub["witness_median_in_floor_units"] - 1.0))
        verdict["margin_at_generation_10_percent"] = float(
            100.0 * (g10["witness_median_in_floor_units"] - 1.0))

    print(f"\n  counted {len(counted)} of {len(pairs)} pairs -> "
          f"{cls} (generation 10: {g10['classification']['class']} on 13 "
          f"unrefined)")
    if counted:
        print(f"  fraction at or below the floor barrier "
              f"{sub['classification']['fraction_below_floor']:.3f} against "
              f"ridge_fraction {dec.ridge_fraction:.3f}")
        print(f"  median depth {sub['witness_depth_median']:.4f} "
              f"({sub['witness_median_in_floor_units']:.4f} floor units, "
              f"margin {verdict['margin_against_the_floor_barrier_percent']:+.1f}%)")
    print(f"  FLIPPED: {verdict['flipped']}")

    return {
        "criterion": crit.to_dict(),
        "decision": dec.to_dict(),
        "rule": RecountRule().to_dict(),
        "all_thirteen": full,
        "reproduction_control": repro,
        "surviving_set": sub,
        "self_consistency": {
            "rows": consistency,
            "all_identical": bool(
                consistency and all(r["identical"] for r in consistency)),
            "why": ("the same pair walked twice by a deterministic function "
                    "must give the same depth; if it does not, the counted set "
                    "is not a subset of the full one"),
        },
        "verdict": verdict,
    }


# ===========================================================================
# Phase 3 -- the register, version 2
# ===========================================================================

#: ``(artefact, list key, separation key, survival key)`` per committed set --
#: ``scripts/run_close.py::REFINEMENT_SOURCES`` with chart G's row repointed at
#: this run. Chart L and chart J are untouched and must stay untouched: their
#: rows in version 2 are asserted identical to version 1's by
#: ``tests/test_witness_refinement_close.py``, which is the control that the two
#: register builders agree everywhere except the one entry that moved.
REFINEMENT_SOURCES_V2: Dict[str, Optional[Tuple[str, str, str, str]]] = {
    "chart_G_d4": ("outputs/wit02_chartG/refine.json",
                   "records", "separation_decades", "survives_refinement"),
    "chart_L_d16": None,
    "chart_J_d16": ("outputs/g9/junction_refine.json",
                    "records", "separation_magnitudes_only",
                    "survives_refinement"),
}


def phase_register(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  the WIT-02 register, version 2")
    print("=" * 74)
    v1 = _read(REGISTER_V1)
    wit01 = _read(WIT01)
    doc: Dict = {
        "rule": v1["rule"],
        "supersedes": {
            "register": REGISTER_V1,
            "kept": ("version 1 stays on disk unchanged. It is the record of "
                     "what the coverage was when WIT-02 was enacted, and the "
                     "gap it reports is the reason this run exists."),
            "what_moved": ("chart G only: 3 of 13 refined becomes 13 of 13. "
                           "Chart L and chart J are untouched."),
        },
        "authorisation": (
            "operator ruling of 2026-08-28 section 2. Narrow: chart G only."),
        "provenance": {
            "inputs_sha256": {
                rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                for rel in [WIT01, REGISTER_V1]
                + [s[0] for s in REFINEMENT_SOURCES_V2.values() if s]
                if (ROOT / rel).is_file()},
            "input_manifests": ["outputs/wit02_chartG/manifest.json",
                                "outputs/g10/manifest.json",
                                "outputs/g9/manifest.json"],
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "validated_platforms": ["win32"],
            "unvalidated": "linux and darwin -- PROV-07, open and unchanged",
        },
        "sets": {},
    }
    for label, src in REFINEMENT_SOURCES_V2.items():
        offered = wit01["sets"][label]
        n_offered = int(offered["n_pairs_offered"])
        seps = [p["max_separation"] for p in offered["pairs"]]
        entry: Dict = {
            "chart": offered["chart"],
            "d": offered["d"],
            "n_pairs_offered": n_offered,
            "admissibility_ratio_WIT01": offered["admissibility_ratio"],
            "refinement_artefact": (src[0] if src else None),
            "n_refined": 0,
            "n_surviving": None,
            "coverage": 0.0,
            "compliant": False,
            "carries": v1["sets"][label]["carries"],
            "matched_by": v1["sets"][label]["matched_by"],
        }
        if src is not None and (ROOT / src[0]).is_file():
            artefact, list_key, sep_key, ok_key = src
            recs = list(_read(artefact)[list_key])
            matched = [r for r in recs if r[sep_key] in seps]
            entry["n_refined"] = len(matched)
            entry["n_surviving"] = sum(1 for r in matched if bool(r[ok_key]))
            entry["n_records_in_artefact"] = len(recs)
            entry["n_records_not_matched_to_this_set"] = len(recs) - len(matched)
            entry["coverage"] = len(matched) / float(n_offered)
            entry["compliant"] = bool(len(matched) == n_offered)
        doc["sets"][label] = entry
        print(f"  {label:14s} {entry['n_refined']:2d} of "
              f"{entry['n_pairs_offered']:2d} refined "
              f"(coverage {entry['coverage']:.3f})  surviving "
              f"{entry['n_surviving']}  compliant={entry['compliant']}")

    unchanged = {k: bool(all(doc["sets"][k].get(f) == v1["sets"][k].get(f)
                             for f in ("n_refined", "n_surviving", "coverage",
                                       "compliant", "refinement_artefact")))
                 for k in ("chart_L_d16", "chart_J_d16")}
    doc["untouched_sets_reproduce_version_1"] = {
        "rows": unchanged,
        "all": bool(all(unchanged.values())),
        "why": ("this register is built by a second implementation of the "
                "same match. The two sets that did not move must come out "
                "identical, which is what makes the one that did move a "
                "measurement rather than a difference between two builders."),
    }
    doc["verdict"] = {
        "n_sets": len(doc["sets"]),
        "n_compliant": sum(1 for e in doc["sets"].values() if e["compliant"]),
        "non_compliant": sorted(k for k, e in doc["sets"].items()
                                if not e["compliant"]),
        "all_compliant": all(e["compliant"] for e in doc["sets"].values()),
        "what_changed_since_version_1": (
            "chart G: 3 of 13 refined at close, 13 of 13 here."),
        "why_chart_L_is_still_uncovered": (
            "the ruling authorised chart G and named chart L as excluded. Its "
            "37 pairs have still never been refined, its median barrier is 212 "
            "floor units, and WITNESS-04 stays open and load-bearing."),
    }
    print(f"  untouched sets reproduce version 1: "
          f"{doc['untouched_sets_reproduce_version_1']['all']}")
    print(f"  compliant: {doc['verdict']['n_compliant']} of "
          f"{doc['verdict']['n_sets']}; still non-compliant: "
          f"{doc['verdict']['non_compliant']}")
    return doc


# ===========================================================================
# Main
# ===========================================================================

ALL_PHASES = ["preregister", "refine", "recount", "register"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/wit02_chartG")
    #: The production grid every committed barrier was measured on. Generation 9
    #: and generation 10 both default to 301; the recount is not comparable with
    #: outputs/g10/ridge_basin.json at any other value, and the reproduction
    #: control is what would catch a change here.
    ap.add_argument("--grid", type=int, default=301)
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    args = ap.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    cfg = GlobalStudyConfig()
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    man = RunManifest.create(
        "wit02_chartG",
        config={"phases": phases, "grid_n": args.grid,
                "biases": list(cfg.biases),
                "distinguishability_floor": cfg.distinguishability_floor,
                "set": SET_LABEL,
                "authorisation": ("operator ruling of 2026-08-28 section 2 -- "
                                  "chart G only")},
        seed=cfg.seed,
        notes=("WIT-02 compliance for chart G: the ten witness pairs that "
               "were never refined, and the barrier recount over what "
               "survives."),
    )
    t0 = time.perf_counter()
    for name in phases:
        if name == "preregister":
            doc = phase_preregister(out)
        elif name == "refine":
            _check_preregistration(out)
            doc = phase_refine(cfg, out)
        elif name == "recount":
            _check_preregistration(out)
            doc = phase_recount(cfg, out, args.grid)
        elif name == "register":
            _check_preregistration(out)
            doc = phase_register(out)
        else:
            raise SystemExit("unknown phase: " + name)
        target = (ROOT / REGISTER_V2) if name == "register" else (
            out / f"{name}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(doc, indent=2), encoding="utf-8", newline="\n")
        man.add_result(name, doc)
        print(f"  -> {target.relative_to(ROOT).as_posix()}")

    man.add_result("wall_clock_s", time.perf_counter() - t0)
    man.write(out)
    print(f"\ntotal {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
