#!/usr/bin/env python
"""How far the instrument can be improved before the witness pairs separate.

The paper's global result is stated at a 2% instrument and the 2% is asserted
everywhere and argued nowhere -- ``docs/PAPER_AUDIT_g15.md`` §7.1 records that a
search of the ledger, the rulings, the matrix and the paper returns the noise
model *stated* and never *argued*. The operator ruling of 2026-08-29 §6 item 2
orders the answerable half: not a justification of 2%, but the **sensitivity** of
the conclusion to it.

The arithmetic, and it is only arithmetic
-----------------------------------------
A witness pair is indistinguishable while its observational distance sits below
the distinguishability floor, and the floor is the relative noise level. So a
pair with worst-case distance ``dmax`` stops being a witness exactly when the
instrument improves past ``dmax``. Per set:

``floor_last_witness``
    ``min`` of ``dmax`` over the surviving pairs. **Below this the set has no
    witness left**, and this is the number that answers "down to what floor?".
``floor_first_loss``
    ``max`` of ``dmax`` over the surviving pairs. Above this every member
    survives; below it the set begins to lose members.

``dmax`` is the **worst** observational distance over the whole refinement
battery -- six (grid, tolerance) configurations -- not the distance at the
default grid. Taking the worst is the conservative direction: it is the earliest
floor at which the pair could separate under any configuration already run.

**No solve is performed.** Every distance is read from the committed refinement
artefacts. This computes no new physics; it re-expresses distances already
measured against a floor that is already recorded, which is why it can be done
without reopening anything.

Usage::

    python scripts/floor_sensitivity_g15.py [--out outputs/floor_sensitivity_g15]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.utils.provenance import RunManifest

REPO = Path(__file__).resolve().parents[1]

#: The three committed witness sets, as ``outputs/close/wit02_register_v3.json``
#: names them, each with the refinement artefact that set records for it.
SETS: Dict[str, Dict[str, Any]] = {
    "chart_G_d4": {"artefact": "outputs/wit02_chartG/refine.json",
                   "chart": "G", "d": 4, "carries": "the ridge result"},
    "chart_J_d16": {"artefact": "outputs/g9/junction_refine.json",
                    "chart": "J", "d": 16,
                    "carries": "the junction degeneracy"},
    "chart_L_d16": {"artefact": "outputs/g11/wit02_chartL/refine.json",
                    "chart": "L", "d": 16,
                    "carries": "the chart-L basin search statement"},
}

REGISTER = "outputs/close/wit02_register_v3.json"


def _digest(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def _load(rel: str) -> Any:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def analyse_set(name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    doc = _load(spec["artefact"])
    verdict = doc["verdict"]
    floor = float(verdict["floor"])

    survivors: List[Dict[str, Any]] = []
    separated: List[Dict[str, Any]] = []
    for rec in doc["records"]:
        dists = [float(r["observational_distance"]) for r in rec["refinements"]]
        row = {
            "pair_index": rec["pair_index"],
            "distance_default_grid": float(rec.get(
                "distance_at_301_default", rec.get("g8_observational_distance"))),
            "distance_worst_over_battery": max(dists),
            "n_configurations": len(dists),
            "worst_in_floor_units": max(dists) / floor,
        }
        (survivors if rec["survives_refinement"] else separated).append(row)

    assert len(survivors) == verdict["n_surviving"], (
        f"{name}: survivor count disagrees with the artefact's own verdict")

    worst = [r["distance_worst_over_battery"] for r in survivors]
    last = min(worst)
    first = max(worst)
    tightest = min(survivors, key=lambda r: r["distance_worst_over_battery"])

    # The same quantity read at the default grid only. Reported beside the
    # worst-case one because the ruling and the artefacts quote this reading
    # (``headroom_fraction_of_floor``), and the two differ: refinement moves
    # some distances up and some down, so the conservative number is the worst
    # over the battery and the optimistic one is this.
    default_last = min(r["distance_default_grid"] for r in survivors)

    return {
        "chart": spec["chart"], "d": spec["d"], "carries": spec["carries"],
        "artefact": spec["artefact"],
        "floor": floor,
        "n_pairs": verdict["n_pairs"],
        "n_surviving": verdict["n_surviving"],
        # The two numbers the paper needs.
        "floor_last_witness": last,
        "floor_last_witness_pct": 100.0 * last,
        "floor_last_witness_in_floor_units": last / floor,
        "floor_first_loss": first,
        "floor_first_loss_pct": 100.0 * first,
        "floor_first_loss_in_floor_units": first / floor,
        "floor_last_witness_default_grid": default_last,
        "floor_last_witness_default_grid_pct": 100.0 * default_last,
        "floor_last_witness_default_grid_in_floor_units": default_last / floor,
        "tightest_surviving_pair_index": tightest["pair_index"],
        "n_separated_by_refinement": len(separated),
        "survivors": sorted(survivors,
                            key=lambda r: r["distance_worst_over_battery"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/floor_sensitivity_g15")
    args = ap.parse_args()
    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)

    reg = _load(REGISTER)
    manifest = RunManifest.create(
        experiment="floor_sensitivity_g15",
        config={"register": REGISTER, "sets": SETS,
                "input_sha256": {v: _digest(v) for v in
                                 [REGISTER] + [s["artefact"]
                                               for s in SETS.values()]}},
        notes="Operator ruling of 2026-08-29 section 6 item 2. Re-expresses "
              "committed witness distances against the floor they were "
              "measured under. No solve.")

    results = {name: analyse_set(name, spec) for name, spec in SETS.items()}

    # Cross-check against the register that governs which sets are committed.
    for name, r in results.items():
        assert reg["sets"][name]["n_surviving"] == r["n_surviving"], (
            f"{name}: register and refinement artefact disagree on survivors")

    overall = min(r["floor_last_witness"] for r in results.values())
    doc: Dict[str, Any] = {
        "question": ("at what instrument noise level does each committed "
                     "witness set stop containing an indistinguishable pair"),
        "method": ("worst observational distance over the refinement battery, "
                   "per surviving pair; the set's last witness goes when the "
                   "floor drops below the smallest of those"),
        "floor_as_stated": 0.02,
        "sets": results,
        "headline": {
            "tightest_set": min(results, key=lambda k:
                                results[k]["floor_last_witness"]),
            "floor_last_witness_anywhere": overall,
            "floor_last_witness_anywhere_pct": 100.0 * overall,
            "reading": (
                "every committed witness set still contains an "
                "indistinguishable pair at an instrument of "
                f"{100.0 * overall:.2f}% relative noise, and the global "
                "degeneracy statement therefore does not depend on the 2% "
                "figure to within a factor of "
                f"{0.02 / overall:.2f}"),
        },
        "what_this_is_not": (
            "not a justification of the 2% noise model, and not a statement "
            "about noise models other than relative Gaussian. It says only how "
            "far the stated floor can move before the stated conclusion "
            "changes. A different noise model would need a different search, "
            "not a rescaling of this one"),
    }
    manifest.results = doc
    (out / "floor_sensitivity.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8", newline="\n")
    manifest.artifacts = {"floor_sensitivity.json":
                          f"{args.out}/floor_sensitivity.json"}
    manifest.write(out)

    print(f"floor as stated: {doc['floor_as_stated']:.3f}  (2% instrument)\n")
    hdr = (f"{'set':14} {'surviving':>9} {'last (worst-case)':>19} "
           f"{'last (default grid)':>21} {'first loss':>16}")
    print(hdr)
    print("-" * len(hdr))
    for name, r in results.items():
        print(f"{name:14} {r['n_surviving']:>4}/{r['n_pairs']:<4} "
              f"{r['floor_last_witness_pct']:>13.3f}% "
              f"({r['floor_last_witness_in_floor_units']:.2f}f) "
              f"{r['floor_last_witness_default_grid_pct']:>14.3f}% "
              f"({r['floor_last_witness_default_grid_in_floor_units']:.2f}f) "
              f"{r['floor_first_loss_pct']:>9.3f}% "
              f"({r['floor_first_loss_in_floor_units']:.2f}f)")
    print(f"\n{doc['headline']['reading']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
