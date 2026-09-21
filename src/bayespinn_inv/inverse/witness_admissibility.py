"""``WIT-01``: a separation the representation cannot carry is not a witness.

The defect that forced the rule
-------------------------------
Generation 9 put all thirteen chart-J witness pairs through the generation-6
refinement battery and six of them separated: their observational distance rose
under ``N = 301 -> 601 -> 1201``, so they were witnesses of the grid rather than
of the device. The rise was extreme -- 195% for one pair -- and the pairs it
happened to were the ones whose junctions were **0.4 nm apart** on a grid whose
node spacing is 3.33 nm. Those two devices are the *same* device as far as the
reconstruction is concerned: ``ChartJ.reconstruct`` places the sign flip with
``x_si < x_j``, so two junctions inside one node interval build the same profile
bit for bit, and a search that calls them indistinguishable has measured its own
grid.

Generation 9 found this the expensive way -- by refining every pair on the oracle
and watching which ones came apart. Refinement is the right *falsifier* and the
wrong *filter*: it costs three solves per bias per pair to discover something the
chart could have said for free, and it discovers it after the count has been
published.

The rule
--------
    ``WIT-01``. A pair whose separation along any coordinate falls below the
    grid resolution is not a witness and is excluded **before** counting, not
    filtered afterwards by refinement. State the admissibility ratio and apply
    it to every existing witness count.

What "along any coordinate" has to mean
---------------------------------------
Read literally -- *reject the pair if any one coordinate is separated by less
than its resolution* -- the rule rejects almost every real witness, including the
ones it is meant to protect. Two chart-J devices sharing a junction and differing
by a decade in doping have a junction separation of exactly zero, which is below
any positive resolution; they are nonetheless a perfectly good witness, and the
generation-8 headline pair would survive only by accident.

So the rule is implemented on the separation that **qualifies** the pair. A pair
enters the witness set because ``max_c |theta_a[c] - theta_b[c]| >=
min_separation_decades``; ``WIT-01`` requires that the coordinate carrying that
qualifying separation be one the representation can actually resolve::

    admissible  iff  there exists a coordinate c with
                     sep_c >= min_separation_decades  and  sep_c resolved

Coordinates whose separation is **nonzero but unresolved** are counted and
reported separately rather than being treated as either. They are differences the
search believes it is testing and the representation does not carry, and their
count is the honest measure of how much of a witness set is grid.

Where the rule bites, and where it is vacuous
---------------------------------------------
:meth:`~bayespinn_inv.inverse.charts.Chart.coordinate_resolution` returns zero for
every magnitude coordinate, because anchor magnitudes reach the grid through
``_lerp`` exactly. So for charts G and L the admissibility ratio is **1.000 by
construction**, and this module's answer for them is a *stated* vacuity rather
than an unexamined assumption. ``WIT-01`` is, on today's chart inventory, a
chart-J rule. Saying so is the point: a rule whose scope is stated can be checked
against the next chart, and a rule whose scope is assumed cannot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence, Union

import numpy as np

#: Coordinates arrive as arrays from every caller; see ``charts.Coords``.
Coords = Union[Sequence[float], np.ndarray]

__all__ = ["AdmissibilityRule", "admissibility", "apply_to_witness_set"]


@dataclass(frozen=True)
class AdmissibilityRule:
    """``WIT-01`` as a hashable object, so it can be registered before use."""

    min_separation_decades: float = 0.3
    predicate: str = (
        "admissible iff some coordinate is separated by at least "
        "min_separation_decades AND that separation is resolved by the chart's "
        "reconstruction")
    resolution_source: str = (
        "Chart.separation_is_resolved -- exact; the junction coordinate of "
        "chart J is a node-index test, every magnitude coordinate is exact")
    applied: str = "before counting, never as a post-hoc filter"

    def rule_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = json.loads(json.dumps(asdict(self)))
        out["rule_hash"] = self.rule_hash()
        return out


def admissibility(chart, theta_a: Coords, theta_b: Coords,
                  rule: Optional[AdmissibilityRule] = None) -> Dict:
    """``WIT-01`` for one pair, with the reason attached to the verdict."""
    rule = rule or AdmissibilityRule()
    a = np.asarray(theta_a, dtype=np.float64)
    b = np.asarray(theta_b, dtype=np.float64)
    sep = np.abs(a - b)
    resolved = np.asarray(chart.separation_is_resolved(a, b), dtype=bool)
    res = np.asarray(chart.coordinate_resolution(a), dtype=np.float64)

    qualifying = sep >= rule.min_separation_decades
    carriers = np.nonzero(qualifying & resolved)[0]
    unresolved_nonzero = np.nonzero((sep > 0.0) & ~resolved)[0]

    ok = bool(carriers.size > 0)
    if ok:
        reason = (f"coordinate {int(carriers[0])} is separated by "
                  f"{float(sep[carriers[0]]):.4g} and is resolved")
    elif not bool(np.any(qualifying)):
        reason = (f"no coordinate reaches the "
                  f"{rule.min_separation_decades} separation criterion; this "
                  f"pair is not a witness before WIT-01 is applied")
    else:
        c = int(np.nonzero(qualifying)[0][0])
        reason = (f"the only coordinates reaching the separation criterion are "
                  f"unresolved by the chart; coordinate {c} is separated by "
                  f"{float(sep[c]):.4g} against a resolution of "
                  f"{float(res[c]):.4g}")
    return {
        "admissible": ok,
        "reason": reason,
        "max_separation": float(np.max(sep)) if sep.size else 0.0,
        "qualifying_coordinates": [int(i) for i in np.nonzero(qualifying)[0]],
        "resolved_qualifying_coordinates": [int(i) for i in carriers],
        "coordinates_separated_but_unresolved": [int(i)
                                                 for i in unresolved_nonzero],
        "separation_of_unresolved": [float(sep[i]) for i in unresolved_nonzero],
        "resolution_of_unresolved": [float(res[i]) for i in unresolved_nonzero],
    }


def apply_to_witness_set(chart, kept_log10: Union[Sequence[Coords], np.ndarray],
                         pair_indices: Sequence[Sequence[int]],
                         rule: Optional[AdmissibilityRule] = None,
                         label: str = "") -> Dict:
    """``WIT-01`` over a whole witness set, with the admissibility ratio.

    ``pair_indices`` are indices into ``kept_log10``, exactly as
    :func:`~bayespinn_inv.inverse.global_identifiability.witness_search` returns
    them under ``include_samples=True``. No oracle call is made: admissibility is
    a property of the chart and the coordinates, which is the whole reason the
    rule is cheaper than the refinement battery that found the defect.
    """
    rule = rule or AdmissibilityRule()
    kept = np.asarray(kept_log10, dtype=np.float64)
    rows: List[Dict] = []
    for (i, j) in pair_indices:
        v = admissibility(chart, kept[int(i)], kept[int(j)], rule)
        rows.append({"pair": [int(i), int(j)], **v})
    n = len(rows)
    n_ok = sum(1 for r in rows if r["admissible"])
    n_unres = sum(1 for r in rows if r["coordinates_separated_but_unresolved"])
    vacuous = (bool(float(np.max(chart.coordinate_resolution(kept[0]))) == 0.0)
               if len(kept) else None)
    return {
        "label": label or chart.label(),
        "chart": chart.name,
        "d": int(chart.d),
        "rule": rule.to_dict(),
        "n_pairs_offered": n,
        "n_admissible": n_ok,
        "n_rejected": n - n_ok,
        "admissibility_ratio": (float(n_ok) / n) if n else float("nan"),
        "n_pairs_with_a_separated_but_unresolved_coordinate": n_unres,
        "rule_is_vacuous_for_this_chart": vacuous,
        "pairs": rows,
    }
