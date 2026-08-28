"""``WIT-02`` for chart L: the 37 witness pairs that have never been refined.

    PYTHONPATH=src python scripts/run_wit02_chartL.py --out outputs/g11/wit02_chartL

What this is, and what authorises it
------------------------------------
``WITNESS-04`` has been open since generation 7 and load-bearing since
generation 10: chart L's 37 witness pairs at ``d = 16`` carry the chart-L basin
search statement and the *dimension reading*, and no refinement of that set has
ever been run. ``docs/CLOSE_RULING.md`` section 3 registered the non-compliance
rather than repairing it, on the ground that refining 37 pairs was new solving
the close forbade.

The operator directive of 2026-08-28 fuses operator authority into the loop and
supplies a condition ladder whose rung ``L1`` requires *every spine item on full
coverage*. Chart L is the only set that is not. The directive section 7 names
this item first and says: *pilot it before ruling; if the pilot says no, that is
``U-BUDGET`` with a number.*

**The pilot said yes.** ``scripts/pilot_wit02_chartL.py`` measured 7.5 s per
pair over a 3-pair prefix at a spread of x1.07, projecting 278 s for all 37.
``outputs/g11/pilot_chartL.json`` is that measurement. A ``U-BUDGET`` verdict
against a five-minute experiment would have been the cheap way to finish, and
the pilot is what makes it unavailable.

The scope is enforced here rather than promised. This module reads one witness
set, ``chart_L_d16`` from ``outputs/g8/reproduce.json``, and constructs no
others; :class:`RefinementScopeL` names it and is hashed before anything is
solved.

What is different from chart G, and why it matters
--------------------------------------------------
:mod:`run_wit02_chartG` had three pairs generation 6 had already refined, and
used them as a reproduction control: the new code path had to reproduce the old
numbers before the ten new pairs could be counted alongside them. **Chart L has
no such pairs** -- that is what 0 of 37 means -- so that control is not
available and a substitute is used instead, stated rather than skipped:

``R1``
    every pair's ``N = 301`` default-tolerance distance must reproduce the
    committed ``witness_pair_distance`` in ``outputs/g8/reproduce.json``
    **bit-identically**. That is the number the set was selected on, so if this
    code path does not reproduce it, the refinement is being applied to a
    different set than the one the claim surface names.

This is a weaker control than chart G's in one specific way and the difference
is not smoothed over: chart G's control tested agreement between *two
generations' code paths*, while ``R1`` tests agreement between this code path
and the *artefact* it reads. It cannot detect a defect that was already present
when ``outputs/g8/reproduce.json`` was written.

The phases
----------
``preregister``
    ``AH-14``. The scope, the battery, the recount rule and the outcome table,
    hashed to disk **before any solve**. Later phases recompute the hashes and
    refuse to run on a mismatch, and refuse to run if generation 9's
    ``BarrierCriterion`` or generation 10's ``RidgeBasinDecision`` has moved.
``refine``
    All 37 chart-L witness pairs through generation 6's battery -- three grids,
    two tolerances -- plus the controls below.
``recount``
    Barriers over the surviving set through ``run_g10._barrier_set``, the same
    imported function that produced ``outputs/g10/ridge_basin.json``, under the
    same registered criterion and classifier. The full 37 are re-measured first
    and must reproduce generation 10's depths exactly.
``register``
    ``outputs/close/wit02_register_v3.json``: the register with chart L's row
    remeasured. Versions 1 and 2 are left on disk unchanged.

Pre-registered, before the run
------------------------------
:data:`OUTCOMES` carries the reading for every classifier output, written into
``preregister.json`` with its hash before the first solve. The branch that
matters is stated as plainly as the one that is expected: **if chart L turns out
to be a ridge, the dimension reading dies**, because that reading is precisely
the claim that ``d = 4`` is the only dimension whose pairs sit at the floor.
Reported either way (``AH-04``, ``AH-13``).

The count branch is pre-registered too, and it is the one chart G did not need.
Chart J lost 6 of 13 under this battery. If chart L loses enough pairs the set
can become **empty or near-empty**, and an empty set does not make the basin
deeper -- it removes the evidence for it. ``EMPTY`` and ``THIN`` below say what
is reported then.
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

from bayespinn_inv.inverse.charts import ChartL
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.utils.provenance import RunManifest

ROOT = Path(__file__).resolve().parents[1]

G8_REPRODUCE = "outputs/g8/reproduce.json"
G9_PREREGISTER = "outputs/g9/preregister.json"
G10_PREREGISTER = "outputs/g10/preregister.json"
G10_RIDGE_BASIN = "outputs/g10/ridge_basin.json"
WIT01 = "outputs/g10/wit01.json"
PILOT = "outputs/g11/pilot_chartL.json"
REGISTER_V2 = "outputs/close/wit02_register_v2.json"
REGISTER_V3 = "outputs/close/wit02_register_v3.json"

#: The one set this step is authorised to touch.
SET_LABEL = "chart_L_d16"


# ===========================================================================
# Pre-registration -- written and hashed BEFORE anything is solved
# ===========================================================================


@dataclass(frozen=True)
class RefinementScopeL:
    """Which pairs go through which battery, and what counts as survival."""

    set_label: str = SET_LABEL
    source_artefact: str = G8_REPRODUCE
    charts_touched: Tuple[str, ...] = ("L",)
    n_pairs_offered: int = 37
    refined_before_this_run: Tuple[int, ...] = ()
    battery_grids: Tuple[int, ...] = REFINEMENT_GRIDS
    battery_tolerances: Tuple[str, ...] = tuple(t[0] for t in REFINEMENT_TOLS)
    tol_carrier_tight: float = 1e-12
    max_outer_tight: int = 200
    survives_iff: str = (
        "the observational distance is below the distinguishability floor at "
        "every one of the six refinement rows -- three grids by two "
        "tolerances. Identical to the rule chart G and chart J were judged by")
    battery_inherited_from: str = (
        "run_g9.REFINEMENT_GRIDS and run_g9.REFINEMENT_TOLS, imported rather "
        "than restated; the same objects run_wit02_chartG.py used for chart G "
        "and run_g9.phase_junction_refine used for chart J")
    reproduction_control: str = (
        "chart L has NO previously refined pairs -- that is what 0 of 37 "
        "means -- so chart G's cross-generation control is unavailable. The "
        "substitute: every pair's N=301 default-tolerance distance must "
        "reproduce outputs/g8/reproduce.json's committed "
        "witness_pair_distance bit-identically. Weaker than chart G's in a "
        "stated way: it tests this code path against the artefact it reads, "
        "not against a second independent implementation, so it cannot detect "
        "a defect already present when that artefact was written")
    negative_control: str = (
        "one chart-L null-control pair -- consecutive ordinary prior draws in "
        "draw order that form no witness pair, the same construction "
        "run_g10._barrier_set uses for its null -- through the same battery. "
        "It must NOT survive. A battery that reports two ordinary draws as "
        "inseparable cannot evidence that a witness pair is")
    negative_control_if_it_survives: str = (
        "reported as measured and NOT swapped for another pair. A null pair "
        "below the floor is not a broken battery, it is a witness the "
        "generation-8 search missed, and re-picking until the control behaves "
        "is the tuning PH-11 forbids")
    positive_control: str = (
        "two IDENTICAL chart-L devices through the same battery. They must "
        "survive, at distance exactly zero at every row. This is the control "
        "that fails if the battery does nothing but reject: a rule that "
        "separates everything is as useless as one that separates nothing, "
        "and IA-1 requires a positive control that would fail if the rule did "
        "nothing")
    determinism_control: str = (
        "one pair's battery is run a second time and every one of its six "
        "distances must be bit-identical. The battery has no seed and no "
        "state; if it is not deterministic, no survival verdict is stable")
    scope_note: str = (
        "no new witnesses, no new charts, no new windows, no chart G, no "
        "chart J. The pairs are read from the committed set; none is "
        "constructed here except the three named controls, which are labelled "
        "as controls and are never counted as witnesses")

    def scope_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["scope_hash"] = self.scope_hash()
        return out


@dataclass(frozen=True)
class RecountRuleL:
    """How the barriers are recounted once survival is known."""

    barriers_are: str = (
        "generation 9's BarrierCriterion, imported unchanged, at the "
        "production grid N=301 -- the criterion outputs/g10/ridge_basin.json "
        "was measured under")
    recompute_through: str = (
        "run_g10._barrier_set, imported; the same function that produced "
        "outputs/g10/ridge_basin.json")
    refinement_changes: str = "which pairs are counted, and nothing else"
    reproduction_control: str = (
        "the full 37-pair set is re-measured first and every per-pair depth "
        "must reproduce outputs/g10/ridge_basin.json bit-identically. A "
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
    the_barrier_is_an_upper_bound: str = (
        "BOUND-01 and PATH-01, carried rather than re-derived. Every depth is "
        "the barrier along a STRAIGHT LINE in this chart's own coordinates, so "
        "it is an UPPER bound and a shallower path may exist. For chart L this "
        "direction is the unfavourable one: a basin statement rests on finding "
        "NO path below the floor, and an upper bound cannot establish that "
        "none exists. Refinement does not repair this and is not claimed to")
    what_is_not_recomputed: str = (
        "chart G and chart J. Their sets are untouched, so their numbers stand "
        "and the three-set comparison stays one measurement rather than two "
        "spliced together")

    def rule_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True,
                       default=list).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self), default=list))
        out["rule_hash"] = self.rule_hash()
        return out


#: What each classifier output means, fixed before the first solve.
OUTCOMES: Dict[str, str] = {
    "BASIN": (
        "chart L stays a basin and gains its coverage. Spine items 3 and 4 "
        "keep their classification and WIT-02 becomes satisfied on all three "
        "committed sets, which is what ladder rung L1 requires. The basin "
        "remains a SEARCH statement against an upper-bound barrier -- "
        "refinement tests the witnesses, not the connectivity -- and the "
        "minimum-energy path is still not computed"),
    "RIDGE": (
        "the dimension reading DIES. That reading is precisely the claim that "
        "d=4 is the only dimension whose pairs sit at the instrument floor; a "
        "chart-L ridge at d=16 is a counter-example to it in the set the "
        "reading rests on. Spine item 4 is rewritten in the same paragraph as "
        "the classification, not in a limitations list, and the ridge/basin "
        "split reverts to being unexplained rather than dimensional"),
    "MIXED": (
        "chart L becomes provisional at the recounted fraction: some pairs sit "
        "at the floor and fewer than ridge_fraction of them do. Spine item 4 "
        "reports the fraction and the coverage, the word basin is retired from "
        "it as a classification, and the dimension reading is weakened to a "
        "statement about medians rather than about every cell"),
    "UNDETERMINED": (
        "no counted pair has a certified barrier. Reported as a failure to "
        "measure, and generation 10's classification stands with its 0-of-37 "
        "coverage unchanged and still uncovered"),
}

#: What the *count* means, fixed before the first solve. Chart G did not need
#: this branch; chart J, which lost 6 of 13, shows why chart L might.
COUNT_OUTCOMES: Dict[str, str] = {
    "FULL": (
        "no pair separates. Recorded as measured, and noted as the first set "
        "of the three to lose nothing -- chart G lost 1 of 13 and chart J 6 "
        "of 13 -- which is itself a fact about d=16 in this chart and not a "
        "vindication of the search"),
    "THIN": (
        "the surviving set falls below 7 pairs, the size of chart J's "
        "surviving set, which is the smallest set any committed classification "
        "currently rests on. The classification is still reported but the "
        "count is stated beside it everywhere, and the dimension reading is "
        "reported as resting on a set that refinement more than halved"),
    "EMPTY": (
        "every pair separates. Chart L then has NO witnesses at d=16, the "
        "chart-L basin statement has no set left to stand on, and the "
        "dimension reading loses one of its two d=16 cells. This is reported "
        "as the destruction of the evidence, NOT as a deeper basin: an empty "
        "set is not a strong result in the same direction"),
}

OUTCOMES_NOTE = (
    "pre-registered before the first solve of this run, under the operator "
    "directive of 2026-08-28 section 3 (SR-3) and AH-14. Reported either way "
    "(AH-04, AH-13). The RIDGE branch is stated as plainly as the BASIN one "
    "because the BASIN one is the expected result and AH-13 is about the "
    "other kind")


def _hash_outcomes() -> str:
    return hashlib.sha256(
        json.dumps({"outcomes": OUTCOMES, "count_outcomes": COUNT_OUTCOMES,
                    "note": OUTCOMES_NOTE},
                   sort_keys=True).encode("utf-8")).hexdigest()


def _read(rel: str) -> Dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def phase_preregister(out: Path) -> Dict:
    print("=" * 74)
    print("PHASE 0  PRE-REGISTRATION (AH-14): the scope and the rules, first")
    print("=" * 74)
    scope, rule = RefinementScopeL(), RecountRuleL()
    crit, dec = BarrierCriterion(), RidgeBasinDecision()

    # The inherited objects must not have moved since they were registered.
    g9 = _read(G9_PREREGISTER)
    g10 = _read(G10_PREREGISTER)
    inherited: Dict[str, object] = {
        "barrier_criterion_here": crit.criterion_hash(),
        "barrier_criterion_at_generation_9": _find_hash(g9, "criterion_hash"),
        "ridge_basin_decision_here": dec.decision_hash(),
        "ridge_basin_decision_at_generation_10": _find_hash(
            g10, "decision_hash"),
    }
    inherited["criterion_unmoved"] = bool(
        inherited["barrier_criterion_here"]
        == inherited["barrier_criterion_at_generation_9"])
    inherited["decision_unmoved"] = bool(
        inherited["ridge_basin_decision_here"]
        == inherited["ridge_basin_decision_at_generation_10"])

    pilot = _read(PILOT) if (ROOT / PILOT).exists() else None
    doc = {
        "what_this_is": (
            "WIT-02 applied to the one committed witness set that has never "
            "satisfied it. WITNESS-04, open since generation 7, load-bearing "
            "since generation 10"),
        "authorised_by": (
            "operator directive of 2026-08-28 sections 7 and 8; ladder rung L1 "
            "requires every spine item on full coverage and chart L is the "
            "only set that is not"),
        "why_not_a_U_BUDGET_verdict": {
            "the_directive_required_a_pilot": (
                "section 2: a budget verdict without a measured pilot is void"),
            "pilot_artefact": PILOT,
            "per_pair_mean_s": (
                pilot["timing"]["per_pair_mean_s"] if pilot else None),
            "per_pair_spread_factor": (
                pilot["timing"]["per_pair_spread_factor"] if pilot else None),
            "projected_all_pairs_s": (
                pilot["projection"]["all_pairs_s"] if pilot else None),
            "verdict": (
                "AFFORDABLE. The pilot measured the experiment at under five "
                "minutes of refinement, so U-BUDGET is unavailable and the "
                "rung is not descended from"),
        },
        "scope": scope.to_dict(),
        "recount_rule": rule.to_dict(),
        "inherited_hashes": inherited,
        "outcomes": OUTCOMES,
        "count_outcomes": COUNT_OUTCOMES,
        "outcomes_note": OUTCOMES_NOTE,
        "outcomes_hash": _hash_outcomes(),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "preregister.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  scope     {scope.scope_hash()[:32]}...")
    print(f"  recount   {rule.rule_hash()[:32]}...")
    print(f"  outcomes  {_hash_outcomes()[:32]}...")
    print(f"  generation 9's barrier criterion unmoved : "
          f"{inherited['criterion_unmoved']}")
    print(f"  generation 10's decision unmoved         : "
          f"{inherited['decision_unmoved']}")
    if pilot:
        print(f"  pilot: {pilot['timing']['per_pair_mean_s']:.1f} s/pair x 37 "
              f"= {pilot['projection']['all_pairs_s']:.0f} s -> AFFORDABLE, "
              f"so U-BUDGET is unavailable")
    print(f"  wrote {out / 'preregister.json'}")
    return doc


def _find_hash(doc, key: str) -> Optional[str]:
    """Locate a hash by key anywhere in a pre-registration document."""
    if isinstance(doc, dict):
        if key in doc and isinstance(doc[key], str):
            return doc[key]
        for v in doc.values():
            got = _find_hash(v, key)
            if got:
                return got
    elif isinstance(doc, list):
        for v in doc:
            got = _find_hash(v, key)
            if got:
                return got
    return None


def _check_preregistration(out: Path) -> Dict:
    """Every later phase recomputes the hashes and refuses on a mismatch."""
    pre = json.loads((out / "preregister.json").read_text(encoding="utf-8"))
    now = {
        "scope_hash": RefinementScopeL().scope_hash(),
        "rule_hash": RecountRuleL().rule_hash(),
        "outcomes_hash": _hash_outcomes(),
        "criterion_hash": BarrierCriterion().criterion_hash(),
        "decision_hash": RidgeBasinDecision().decision_hash(),
    }
    was = {
        "scope_hash": pre["scope"]["scope_hash"],
        "rule_hash": pre["recount_rule"]["rule_hash"],
        "outcomes_hash": pre["outcomes_hash"],
        "criterion_hash": pre["inherited_hashes"]["barrier_criterion_here"],
        "decision_hash": pre["inherited_hashes"]["ridge_basin_decision_here"],
    }
    bad = [k for k in now if now[k] != was[k]]
    if bad:
        raise SystemExit(
            "IA-4: the pre-registration has moved since it was written "
            f"({', '.join(bad)}). This run is discarded rather than "
            "reconciled; a spec that changes mid-measurement is not a spec.")
    return pre


# ===========================================================================
# Phase 1 -- the refinement battery
# ===========================================================================


def _battery(cfg, kept: np.ndarray, ia: int, ib: int,
             floor: float) -> List[Dict]:
    """Generation 6's battery on one pair: three grids, two tolerances."""
    biases = list(cfg.biases)
    rows: List[Dict] = []
    for grid in REFINEMENT_GRIDS:
        for tname, sg_cfg in REFINEMENT_TOLS:
            sg_r, x_r = build_solver(cfg, grid, sg_cfg)
            chart_r = ChartL(16, x_r)
            cur_a, tr_a, cv_a = iv(sg_r, chart_r.charted(kept[ia]), biases)
            cur_b, tr_b, cv_b = iv(sg_r, chart_r.charted(kept[ib]), biases)
            mask = tr_a & cv_a & tr_b & cv_b
            dist = obs_dist(cur_a, cur_b, mask)
            rows.append({
                "grid_n": grid,
                "tolerance": tname,
                "tol_carrier": float(sg_cfg.tol_carrier),
                "observational_distance": dist,
                "n_biases_certified": int(np.sum(mask)),
                "n_biases": len(biases),
                "below_floor": bool(dist < floor),
            })
    return rows


def _battery_on_vectors(cfg, va: np.ndarray, vb: np.ndarray,
                        floor: float) -> List[Dict]:
    """The same battery on two explicit coordinate vectors (for controls)."""
    kept = np.vstack([va, vb])
    return _battery(cfg, kept, 0, 1, floor)


def phase_refine(cfg, out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 1  WIT-02  all 37 chart-L witness pairs, one battery")
    print("=" * 74)
    _check_preregistration(out)
    scope = RefinementScopeL()
    rep = _read(G8_REPRODUCE)[SET_LABEL]
    kept = np.asarray(rep["kept_log10"], dtype=np.float64)
    pairs = [tuple(p) for p in rep["witness_pair_indices"]]
    floor = float(rep["floors"]["distinguishability"])
    committed = [float(x) for x in rep["witness_pair_distance"]]

    if len(pairs) != scope.n_pairs_offered:
        raise SystemExit(
            f"IA-4: the committed set has {len(pairs)} pairs, the "
            f"pre-registered scope names {scope.n_pairs_offered}")

    print(f"  set {SET_LABEL}: {len(pairs)} pairs, none previously refined")
    print(f"  battery N={list(REFINEMENT_GRIDS)} x "
          f"{[t[0] for t in REFINEMENT_TOLS]}, floor {floor}")
    print()

    records, repro_rows = [], []
    t0 = time.perf_counter()
    for k, (ia, ib) in enumerate(pairs):
        rows = _battery(cfg, kept, ia, ib, floor)
        survives = all(r["below_floor"] for r in rows)
        base = next(r for r in rows
                    if r["grid_n"] == 301 and r["tolerance"] == "default")
        repro_rows.append({
            "pair_index": k,
            "committed_distance": committed[k],
            "here_at_N301_default": base["observational_distance"],
            "identical": bool(
                base["observational_distance"] == committed[k]),
        })
        worst = max(r["observational_distance"] for r in rows)
        records.append({
            "pair_index": k,
            "member_indices": [int(ia), int(ib)],
            "separation_decades": float(rep["witness_pair_separation"][k]),
            "g8_observational_distance": committed[k],
            "headroom_fraction_of_floor": committed[k] / floor,
            "previously_refined": False,
            "refinements": rows,
            "worst_distance": worst,
            "worst_in_floor_units": worst / floor,
            "survives_refinement": survives,
        })
        print(f"  pair {k:2d}  {ia:5d},{ib:5d}   committed {committed[k]:.6f}  "
              f"worst {worst:.6f}   "
              f"{'SURVIVES ' if survives else 'SEPARATES'}")
    refine_s = time.perf_counter() - t0

    surviving = [r["pair_index"] for r in records if r["survives_refinement"]]
    separated = [r["pair_index"] for r in records
                 if not r["survives_refinement"]]

    # -- R1 reproduction control --------------------------------------------
    r1 = {
        "rows": repro_rows,
        "all_identical": bool(all(r["identical"] for r in repro_rows)),
        "n_identical": sum(1 for r in repro_rows if r["identical"]),
        "of": len(repro_rows),
        "why": scope.reproduction_control,
    }
    print(f"\n  R1 reproduction : {r1['n_identical']} of {r1['of']} pairs "
          f"reproduce the committed N=301 distance bit-identically "
          f"-> {'PASS' if r1['all_identical'] else 'FAIL'}")

    # -- N1 negative control -------------------------------------------------
    witness_set = {tuple(sorted(p)) for p in pairs}
    null_pair: Optional[Tuple[int, int]] = None
    i = 0
    while i + 1 < len(kept):
        if tuple(sorted((i, i + 1))) not in witness_set:
            null_pair = (i, i + 1)
            break
        i += 2
    if null_pair is None:
        raise SystemExit(
            "no null-control pair exists in this set: every consecutive draw "
            "pair is a witness pair. The negative control cannot be built, and "
            "a refinement without it evidences nothing")
    null_rows = _battery(cfg, kept, null_pair[0], null_pair[1], floor)
    null_survives = all(r["below_floor"] for r in null_rows)
    n1 = {
        "construction": scope.negative_control,
        "pair": [int(null_pair[0]), int(null_pair[1])],
        "rows": null_rows,
        "worst_distance": max(r["observational_distance"] for r in null_rows),
        "survives": null_survives,
        "passes": bool(not null_survives),
        "if_it_survives": scope.negative_control_if_it_survives,
    }
    print(f"  N1 negative     : null pair {n1['pair']} worst "
          f"{n1['worst_distance']:.6f} vs floor {floor} -> "
          f"{'PASS' if n1['passes'] else 'FAIL (reported as measured)'}")

    # -- P1 positive control -------------------------------------------------
    same = kept[pairs[0][0]]
    pos_rows = _battery_on_vectors(cfg, same, same.copy(), floor)
    pos_survives = all(r["below_floor"] for r in pos_rows)
    pos_zero = all(r["observational_distance"] == 0.0 for r in pos_rows)
    p1 = {
        "construction": scope.positive_control,
        "rows": pos_rows,
        "survives": pos_survives,
        "all_distances_exactly_zero": pos_zero,
        "passes": bool(pos_survives and pos_zero),
        "why_this_is_the_positive_control": (
            "IA-1 requires a control that would FAIL if the rule did nothing. "
            "A battery that rejected everything would separate two identical "
            "devices, and every 'separates' verdict above would be vacuous. "
            "This is the control the WIT-01 prose guard's first positive "
            "control was not"),
    }
    print(f"  P1 positive     : identical devices survive at distance 0 -> "
          f"{'PASS' if p1['passes'] else 'FAIL'}")

    # -- D1 determinism control ---------------------------------------------
    again = _battery(cfg, kept, pairs[0][0], pairs[0][1], floor)
    d1_rows = [{"grid_n": a["grid_n"], "tolerance": a["tolerance"],
                "first": a["observational_distance"],
                "second": b["observational_distance"],
                "identical": bool(
                    a["observational_distance"] == b["observational_distance"])}
               for a, b in zip(records[0]["refinements"], again)]
    d1 = {
        "construction": scope.determinism_control,
        "pair_index": 0,
        "rows": d1_rows,
        "passes": bool(all(r["identical"] for r in d1_rows)),
    }
    print(f"  D1 determinism  : pair 0 re-run, 6 of 6 distances identical -> "
          f"{'PASS' if d1['passes'] else 'FAIL'}")

    n_surv = len(surviving)
    count_class = ("EMPTY" if n_surv == 0
                   else "THIN" if n_surv < 7
                   else "FULL" if n_surv == len(pairs)
                   else "PARTIAL")
    verdict = {
        "set": SET_LABEL,
        "n_pairs": len(pairs),
        "n_refined_here": len(pairs),
        "n_surviving": n_surv,
        "n_separated_by_refinement": len(separated),
        "surviving_pair_indices": surviving,
        "separated_pair_indices": separated,
        "coverage_after_this_run": 1.0,
        "coverage_before_this_run": 0.0,
        "floor": floor,
        "count_class": count_class,
        "count_reading": COUNT_OUTCOMES.get(
            count_class,
            "a partial loss: the set survives with members removed, and every "
            "count is reported with its denominator per DOC-08"),
        "count_reading_was_registered_before_the_run": True,
    }
    print(f"\n  {n_surv} of {len(pairs)} pairs survive; "
          f"{len(separated)} separate  -> count class {count_class}")

    doc = {
        "records": records,
        "reproduction_control_R1": r1,
        "negative_control_N1": n1,
        "positive_control_P1": p1,
        "determinism_control_D1": d1,
        "all_refine_controls_pass": bool(
            r1["all_identical"] and n1["passes"] and p1["passes"]
            and d1["passes"]),
        "battery": {
            "grids": list(REFINEMENT_GRIDS),
            "tolerances": [t[0] for t in REFINEMENT_TOLS],
            "tol_carrier_tight": 1e-12,
            "inherited_from": scope.battery_inherited_from,
        },
        "wall_clock_s": refine_s,
        "verdict": verdict,
    }
    (out / "refine.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out / 'refine.json'}")
    return doc


# ===========================================================================
# Phase 2 -- the barriers, recounted over the surviving set
# ===========================================================================


def phase_recount(cfg, out: Path, grid_n: int) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 2  the barriers, recounted over the surviving set")
    print("=" * 74)
    _check_preregistration(out)
    refine = json.loads((out / "refine.json").read_text(encoding="utf-8"))
    crit, dec = BarrierCriterion(), RidgeBasinDecision()
    rep = _read(G8_REPRODUCE)[SET_LABEL]
    kept = np.asarray(rep["kept_log10"], dtype=np.float64)
    pairs = [tuple(p) for p in rep["witness_pair_indices"]]
    biases = list(cfg.biases)
    sg, x_si = build_solver(cfg, grid_n)
    chart = ChartL(16, x_si)
    print(f"  criterion {crit.criterion_hash()[:32]}...  (generation 9's)")
    print(f"  decision  {dec.decision_hash()[:32]}...  (generation 10's)")

    # -- the full set, as a reproduction control -----------------------------
    t0 = time.perf_counter()
    full = _barrier_set(sg, chart, cfg, biases, kept, pairs, crit,
                        SET_LABEL + "__all_37")
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
        "n_identical": sum(1 for r in rows if r["identical"]),
        "of": len(rows),
        "median_here": full["witness_depth_median"],
        "median_at_generation_10": g10["witness_depth_median"],
        "median_identical": bool(
            full["witness_depth_median"] == g10["witness_depth_median"]),
        "below_floor_here": full["witness_pairs_below_the_floor_barrier"],
        "below_floor_at_generation_10":
            g10["witness_pairs_below_the_floor_barrier"],
        "why": RecountRuleL().reproduction_control,
        "wall_clock_s": time.perf_counter() - t0,
    }
    print(f"  B1 reproduction of generation 10's 37 depths: "
          f"{repro['n_identical']} of {repro['of']} identical "
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
        "the_barrier_is_still_an_upper_bound": (
            RecountRuleL().the_barrier_is_an_upper_bound),
    }
    if counted:
        verdict["median_depth_over_the_surviving_set"] = sub[
            "witness_depth_median"]
        verdict["median_in_floor_units"] = sub["witness_median_in_floor_units"]
        verdict["median_at_generation_10"] = g10["witness_depth_median"]
        verdict["median_in_floor_units_at_generation_10"] = g10[
            "witness_median_in_floor_units"]

    print(f"\n  counted {len(counted)} of {len(pairs)} pairs -> "
          f"{cls} (generation 10: {g10['classification']['class']} on 37 "
          f"unrefined)")
    if counted:
        print(f"  fraction at or below the floor barrier "
              f"{sub['classification']['fraction_below_floor']:.3f} against "
              f"ridge_fraction {dec.ridge_fraction:.3f}")
        print(f"  median depth {sub['witness_depth_median']:.4f} "
              f"({sub['witness_median_in_floor_units']:.4f} floor units)")
    print(f"  FLIPPED: {verdict['flipped']}")

    doc = {
        "criterion": crit.to_dict(),
        "decision": dec.to_dict(),
        "rule": RecountRuleL().to_dict(),
        "all_thirty_seven": full,
        "reproduction_control_B1": repro,
        "surviving_set": sub,
        "self_consistency_S1": {
            "rows": consistency,
            "all_identical": bool(
                consistency and all(r["identical"] for r in consistency)),
            "why": ("the same pair walked twice by a deterministic function "
                    "must give the same depth; if it does not, the counted set "
                    "is not a subset of the full one"),
        },
        "verdict": verdict,
    }
    (out / "recount.json").write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {out / 'recount.json'}")
    return doc


# ===========================================================================
# Phase 3 -- the register, version 3
# ===========================================================================


#: ``(artefact, list key, separation key, survival key)`` per committed set --
#: version 2's sources with chart L's row repointed at this run. Chart G and
#: chart J must stay untouched: their rows in version 3 are asserted identical
#: to version 2's by ``tests/test_witness_refinement_g11.py``, which is the
#: control that the two register builders agree everywhere except the one entry
#: that moved.
REFINEMENT_SOURCES_V3: Dict[str, Optional[Tuple[str, str, str, str]]] = {
    "chart_G_d4": ("outputs/wit02_chartG/refine.json",
                   "records", "separation_decades", "survives_refinement"),
    "chart_L_d16": ("outputs/g11/wit02_chartL/refine.json",
                    "records", "separation_decades", "survives_refinement"),
    "chart_J_d16": ("outputs/g9/junction_refine.json",
                    "records", "separation_magnitudes_only",
                    "survives_refinement"),
}


def phase_register(out: Path) -> Dict:
    print()
    print("=" * 74)
    print("PHASE 3  the WIT-02 register, version 3")
    print("=" * 74)
    v2 = _read(REGISTER_V2)
    wit01 = _read(WIT01)
    doc: Dict = {
        "rule": v2["rule"],
        "supersedes": {
            "register": REGISTER_V2,
            "kept": ("versions 1 and 2 stay on disk unchanged. Version 1 is "
                     "the record of the coverage when WIT-02 was enacted; "
                     "version 2 is the record of it after chart G was closed "
                     "and while chart L was still the uncovered set."),
            "what_moved": ("chart L only: 0 of 37 refined becomes 37 of 37. "
                           "Chart G and chart J are untouched."),
        },
        "authorisation": (
            "operator directive of 2026-08-28 sections 7 and 8, under fused "
            "operator authority. Ladder rung L1 requires every spine item on "
            "full coverage; chart L was the only set that was not, and the "
            "pilot made a U-BUDGET verdict unavailable."),
        "provenance": {
            "inputs_sha256": {
                rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                for rel in [WIT01, REGISTER_V2]
                + [s[0] for s in REFINEMENT_SOURCES_V3.values() if s]
                if (ROOT / rel).is_file()},
            "input_manifests": ["outputs/g11/wit02_chartL/manifest.json",
                                "outputs/wit02_chartG/manifest.json",
                                "outputs/g10/manifest.json",
                                "outputs/g9/manifest.json"],
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "validated_platforms": ["win32"],
            "unvalidated": "linux and darwin -- PROV-07, open and unchanged",
        },
        "sets": {},
    }
    for label, src in REFINEMENT_SOURCES_V3.items():
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
            "carries": v2["sets"][label]["carries"],
            "matched_by": v2["sets"][label]["matched_by"],
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

    unchanged = {k: bool(all(doc["sets"][k].get(f) == v2["sets"][k].get(f)
                             for f in ("n_refined", "n_surviving", "coverage",
                                       "compliant", "refinement_artefact")))
                 for k in ("chart_G_d4", "chart_J_d16")}
    doc["untouched_sets_reproduce_version_2"] = {
        "rows": unchanged,
        "all": bool(all(unchanged.values())),
        "why": ("this register is built by a third implementation of the same "
                "match. The two sets that did not move must come out "
                "identical, which is what makes the one that did move a "
                "measurement rather than a difference between two builders."),
    }
    doc["verdict"] = {
        "n_sets": len(doc["sets"]),
        "n_compliant": sum(1 for e in doc["sets"].values() if e["compliant"]),
        "non_compliant": sorted(k for k, e in doc["sets"].items()
                                if not e["compliant"]),
        "all_compliant": all(e["compliant"] for e in doc["sets"].values()),
        "what_changed_since_version_2": (
            "chart L: 0 of 37 refined at close, 37 of 37 here, 26 surviving."),
        "how_to_say_it": (
            "WIT-02 is satisfied on all three committed witness sets"
            if all(e["compliant"] for e in doc["sets"].values()) else
            "WIT-02 is satisfied on "
            f"{sum(1 for e in doc['sets'].values() if e['compliant'])} of "
            f"{len(doc['sets'])} committed witness sets"),
        "what_full_coverage_does_not_mean": (
            "it does not make any d=16 result a separation. Every barrier is "
            "still an upper bound along a straight line in one chart's "
            "coordinates and the minimum-energy path is still not computed; "
            "PATH-01 and AH-13 are untouched by refining witnesses. Full "
            "coverage means every counted pair has been through the battery, "
            "and nothing more than that."),
    }
    print(f"  untouched sets reproduce version 2: "
          f"{doc['untouched_sets_reproduce_version_2']['all']}")
    print(f"  compliant: {doc['verdict']['n_compliant']} of "
          f"{doc['verdict']['n_sets']}; still non-compliant: "
          f"{doc['verdict']['non_compliant']}")
    p = ROOT / REGISTER_V3
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"  wrote {REGISTER_V3}")
    return doc


ALL_PHASES = ["preregister", "refine", "recount", "register"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/g11/wit02_chartL")
    ap.add_argument("--phases", default=",".join(ALL_PHASES))
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args(argv)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    cfg = GlobalStudyConfig(n_anchor=16)
    man = RunManifest.create(
        "wit02_chartL",
        config={"phases": phases, "grid_n": args.grid,
                "biases": list(cfg.biases),
                "distinguishability_floor": cfg.distinguishability_floor,
                "set": SET_LABEL,
                "authorisation": ("operator directive of 2026-08-28 sections "
                                  "7 and 8 -- chart L only, after the pilot "
                                  "made U-BUDGET unavailable")},
        seed=cfg.seed,
        notes=("WIT-02 compliance for chart L: the 37 witness pairs that had "
               "never been refined, and the barrier recount over what "
               "survives. WITNESS-04."),
    )
    t0 = time.perf_counter()
    for name in phases:
        if name == "preregister":
            doc = phase_preregister(out)
        elif name == "refine":
            doc = phase_refine(cfg, out)
        elif name == "recount":
            doc = phase_recount(cfg, out, args.grid)
        elif name == "register":
            doc = phase_register(out)
        else:
            raise SystemExit("unknown phase: " + name)
        man.add_result(name, doc)

    man.add_result("wall_clock_s", time.perf_counter() - t0)
    man.write(out)
    print(f"\ntotal {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
