"""How many distinct devices is the degeneracy, and how do we count them?

Why this module exists
----------------------
Generation 7 measured a profile likelihood along the straight line between the
two members of one witness pair and found it **bimodal**: two isolated maxima at
the endpoints, a barrier 242 log-units deep between them, only 5 of 61 path
points inside the 2% distinguishability floor, against a control along the most
observable direction that is 43.7x deeper and has no second mode.

That is a statement about *one path between two devices*. It licenses "the
degeneracy is not a flat manifold" and nothing about how many devices there are.
The witness searches found 13 pairs in chart G at ``d=4`` and 37 in chart L at
``d=16``; whether those are **two basins seen many times** or **many basins** is a
different question, and it is the one the operational consequence rests on. A
gradient-based inversion that converges to "whichever basin it started nearest"
is a mild statement if there are two basins and a severe one if there are twenty.

What is counted, and what a count is worth
------------------------------------------
The objects counted are the **members** of witness pairs, reconstructed to
profiles on the solver grid, so that members from different charts are compared
as devices rather than as coordinate vectors. The metric is

    D(a, b) = max over grid nodes of | log10|C_a(x)| - log10|C_b(x)| |

in decades, with sign disagreements **counted separately and never folded in**
(the same discipline :func:`~bayespinn_inv.inverse.charts.containment` uses: a
log-magnitude distance cannot see a sign flip, so it is reported beside it and
not summed into it).

``AH-14`` and the ordering that makes this measurable
-----------------------------------------------------
A clustering threshold chosen after seeing the clusters is a tuned cutoff wearing
a different hat. :class:`ClusterCriterion` is frozen, hashes itself, and the run
script writes that hash **before** any distance is computed -- the same protocol
``GlobalStudyConfig.prior_hash`` uses for the prior.

The threshold is not a new number either. It is ``min_separation_decades = 0.3``,
the repository's own pre-existing definition of "far apart in parameter space",
used unchanged and inherited rather than picked.

``SPEC-11`` applied to a cluster count
--------------------------------------
The operator's generation-8 ruling says a rank is a curve over cutoffs and not an
integer. A cluster count is the same kind of object: an integer produced by
applying a threshold to a continuous structure. So :func:`count_basins` reports
the count **as a function of threshold** over the whole defensible range, along
with the widest plateau, and the count at the pre-registered threshold is read off
that curve rather than replacing it. A basin count quoted without its threshold is
the same defect as a rank quoted without its cutoff.

What single-linkage does and does not claim
--------------------------------------------
Single linkage joins two groups when *any* pair across them is closer than the
threshold, so a cluster here means "connected by a chain of steps each shorter
than 0.3 decades" -- not "all within 0.3 decades of each other". That is the
correct notion for a basin, because a basin is connected, not small; and it is
the pessimistic direction for the headline, because chaining **merges** clusters
and so can only lower the count. A count obtained this way is a lower bound on the
number of distinct devices at the stated threshold, and is reported as one.

Parameter-space clustering is a proxy. :func:`barrier_depth` is the check: for a
stated sample of within-cluster and between-cluster pairs it walks the straight
line in chart coordinates and reports the deepest point of the profile likelihood
along it, which is the same measurement generation 7 made for one pair. If
within-cluster pairs have shallow barriers and between-cluster pairs have deep
ones, the proxy tracks the landscape; if they do not, the clustering is a
statement about coordinates and the module says so.

``PH-22``: float64 throughout. Nothing here calls the surrogate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "ClusterCriterion",
    "barrier_depth",
    "count_basins",
    "profile_distance_matrix",
    "single_linkage_labels",
    "witness_graph_components",
]


@dataclass(frozen=True)
class ClusterCriterion:
    """Everything that decides a basin count, fixed and hashed before use.

    Attributes
    ----------
    metric
        Name of the distance. Only ``"max_abs_log10_decades"`` is implemented;
        the field exists so the artefact records which one ran rather than
        leaving it to be inferred from the code that happened to be checked out.
    linkage
        Only ``"single"``. See the module docstring for why, and for what the
        resulting count is a bound on.
    threshold_decades
        The pre-registered cut. Inherited from
        ``GlobalStudyConfig.min_separation_decades``; not chosen here.
    threshold_grid
        The range of thresholds the count is reported over, because a count at
        one threshold is a threshold count (``SPEC-11``).
    sign_disagreements_folded_in
        Always ``False``, and stated rather than assumed: a sign flip is not a
        magnitude difference and the two are never summed (``PH-13`` in spirit --
        two incommensurable quantities are reported separately).
    """

    metric: str = "max_abs_log10_decades"
    linkage: str = "single"
    threshold_decades: float = 0.3
    threshold_grid: Tuple[float, ...] = (
        0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80,
        1.00, 1.25, 1.50, 2.00, 2.50, 3.00)
    sign_disagreements_folded_in: bool = False

    def criterion_hash(self) -> str:
        """SHA-256 of this criterion, to be recorded **before** clustering."""
        payload = asdict(self)
        payload["threshold_grid"] = list(self.threshold_grid)
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict:
        out = asdict(self)
        out["threshold_grid"] = list(self.threshold_grid)
        out["criterion_hash"] = self.criterion_hash()
        return out


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def profile_distance_matrix(
    profiles: Sequence[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    """Pairwise profile distance in decades, and the sign-disagreement counts.

    ``profiles[i]`` is a signed net-doping array on the solver grid, so devices
    reconstructed from different charts are directly comparable -- which is the
    only reason a chart-G member and a chart-L member can appear in one table.

    Returns ``(D, S)``: ``D[i, j]`` in decades, ``S[i, j]`` the number of grid
    nodes where the two profiles disagree in sign. ``S`` is returned, never
    added to ``D``.
    """
    P = np.stack([np.asarray(p, dtype=np.float64) for p in profiles])
    with np.errstate(divide="ignore", invalid="ignore"):
        L = np.log10(np.abs(P))
    if not np.isfinite(L).all():
        raise ValueError(
            "a profile has a zero or non-finite node, so log10|C| is undefined "
            "there; the distance would silently depend on how that node is "
            "patched. Fix the profile, do not clip it.")
    n = P.shape[0]
    D = np.zeros((n, n))
    S = np.zeros((n, n), dtype=int)
    sgn = np.sign(P)
    for i in range(n):
        d = np.max(np.abs(L[i + 1:] - L[i]), axis=1) if i + 1 < n else np.empty(0)
        D[i, i + 1:] = d
        D[i + 1:, i] = d
        if i + 1 < n:
            s = np.sum(sgn[i + 1:] != sgn[i], axis=1)
            S[i, i + 1:] = s
            S[i + 1:, i] = s
    return D, S


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def single_linkage_labels(D: np.ndarray, threshold: float) -> np.ndarray:
    """Connected components of the graph ``D < threshold``.

    Single linkage at a cut is exactly this graph's components, so it is written
    as the graph rather than as a dendrogram: a union-find over an explicit
    predicate is auditable, and a dendrogram cut is one indirection away from the
    predicate that produced it.
    """
    n = D.shape[0]
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            if D[i, j] < threshold:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[ra] = rb
    roots: Dict[int, int] = {}
    labels = np.zeros(n, dtype=int)
    for i in range(n):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots)
        labels[i] = roots[r]
    return labels


def count_basins(D: np.ndarray, criterion: ClusterCriterion) -> Dict:
    """Basin count as a **curve** over threshold, plus the pre-registered read.

    ``SPEC-11``'s rank-curve rule, applied to a cluster count. The returned
    ``count_at_threshold`` is a point on ``curve``, not a substitute for it, and
    ``plateau_containing_threshold`` says how much of the defensible range shares
    that answer.
    """
    curve = []
    for t in criterion.threshold_grid:
        labels = single_linkage_labels(D, float(t))
        curve.append({"threshold_decades": float(t),
                      "n_clusters": int(labels.max() + 1) if labels.size else 0,
                      "cluster_sizes": sorted(
                          np.bincount(labels).tolist(), reverse=True)
                      if labels.size else []})

    labels = single_linkage_labels(D, criterion.threshold_decades)
    n_at = int(labels.max() + 1) if labels.size else 0

    # The plateau of the curve that the pre-registered threshold sits in.
    lo = hi = criterion.threshold_decades
    grid = list(criterion.threshold_grid)
    counts = [c["n_clusters"] for c in curve]
    if criterion.threshold_decades in grid:
        k = grid.index(criterion.threshold_decades)
        i = k
        while i > 0 and counts[i - 1] == counts[k]:
            i -= 1
        j = k
        while j < len(grid) - 1 and counts[j + 1] == counts[k]:
            j += 1
        lo, hi = float(grid[i]), float(grid[j])

    return {
        "criterion": criterion.to_dict(),
        "curve": curve,
        "count_at_threshold": n_at,
        "labels_at_threshold": labels.tolist(),
        "cluster_sizes_at_threshold": sorted(
            np.bincount(labels).tolist(), reverse=True) if labels.size else [],
        "plateau_containing_threshold": {
            "lo_decades": lo, "hi_decades": hi,
            "spans_whole_grid": bool(lo == grid[0] and hi == grid[-1]),
        },
        "reading": (
            "single-linkage components at a stated threshold; chaining can only "
            "merge, so this is a LOWER bound on the number of distinct devices "
            "at that threshold, not an estimate of it"),
    }


def witness_graph_components(n_members: int,
                             edges: Sequence[Tuple[int, int]]) -> Dict:
    """Components of the witness relation itself, as a structural cross-check.

    The clustering above asks "which of these devices are close in profile
    space". This asks the different question "which of them are linked by an
    *observational* indistinguishability the search actually certified". The two
    need not agree, and where they disagree the disagreement is the finding: a
    component larger than a pair means the search found a chain of devices no two
    consecutive members of which the instrument can separate.
    """
    parent = list(range(n_members))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in edges:
        ra, rb = find(int(i)), find(int(j))
        if ra != rb:
            parent[ra] = rb
    comp: Dict[int, List[int]] = {}
    for i in range(n_members):
        comp.setdefault(find(i), []).append(i)
    sizes = sorted((len(v) for v in comp.values()), reverse=True)
    return {
        "n_members": int(n_members),
        "n_edges": len(edges),
        "n_components": len(comp),
        "component_sizes": sizes,
        "n_components_larger_than_a_pair": int(sum(1 for s in sizes if s > 2)),
    }


# ---------------------------------------------------------------------------
# The check on the proxy
# ---------------------------------------------------------------------------

def barrier_depth(
    loglik: Callable[[np.ndarray], Optional[float]],
    theta_a: np.ndarray,
    theta_b: np.ndarray,
    n_points: int = 11,
) -> Dict:
    """Deepest point of the profile likelihood on the straight line ``a -> b``.

    The same measurement ``SPEC-g7-4`` made for one pair, reduced to the one
    number that distinguishes "same basin" from "different basins": how far the
    log-likelihood falls between the endpoints. ``loglik`` returns ``None`` for a
    point the oracle refuses to certify; those are **counted**, not skipped
    silently (``PH-19``), and a path with any uncertified interior point reports
    ``certified: false`` rather than a barrier depth taken over what survived.
    """
    a = np.asarray(theta_a, dtype=np.float64)
    b = np.asarray(theta_b, dtype=np.float64)
    ts = np.linspace(0.0, 1.0, n_points)
    vals: List[Optional[float]] = []
    uncertified = 0
    for t in ts:
        v = loglik((1.0 - t) * a + t * b)
        if v is None:
            uncertified += 1
            vals.append(None)
        else:
            vals.append(float(v))
    interior = [v for v in vals[1:-1] if v is not None]
    ends = [v for v in (vals[0], vals[-1]) if v is not None]
    return {
        "n_points": int(n_points),
        "n_uncertified": int(uncertified),
        "certified": uncertified == 0,
        "loglik": vals,
        "endpoint_max": max(ends) if ends else None,
        "interior_min": min(interior) if interior else None,
        "barrier_depth": (max(ends) - min(interior))
        if (ends and interior) else None,
    }
