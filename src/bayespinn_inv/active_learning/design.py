"""Identifiability-aware bias selection: optimal experiment design for the inverse problem.

The question this module exists to answer
-----------------------------------------
The project's active learning picks the next bias to measure by *predictive
uncertainty* (``acquire_max_std``), and ``outputs/results/results_summary.md``
H4b reports that this has **no distinguishable advantage over random**.

There is a reason to expect that. Predictive uncertainty answers "where is my
forward model unsure?". The inverse problem needs a different question:
"which measurement constrains a doping direction I currently cannot see?" A
bias point can be one the surrogate predicts confidently and still be the only
one that resolves a particular profile direction -- and vice versa.

Classical optimal experiment design answers the second question directly. For
a forward map with Jacobian ``J`` (rows = bias points, columns = profile
parameters) and independent measurement noise, the Fisher information of a
chosen design ``S`` is

    M(S) = sum_{i in S} J_i J_i^T / sigma^2

and the standard criteria are

* **D-optimal** -- maximise ``log det M``: shrink the overall confidence
  ellipsoid. Blind to which direction is worst.
* **E-optimal** -- maximise ``lambda_min(M)``: improve the *worst-determined*
  direction. This is the criterion that matches the identifiability finding,
  because the finding is precisely that most directions are unconstrained.
* **A-optimal** -- minimise ``trace(M^-1)``: average parameter variance.

None of this is new -- it is Fedorov (1972) and Atkinson & Donev (1992), and
the semiconductor inverse literature (Burger et al. 2001) is well aware of it.
**No novelty is claimed for the method.** What is not in the literature is
whether it buys anything *here*, on this forward map, against the uncertainty
acquisition this project already has. That is an empirical question and this
module exists so it can be answered rather than assumed.

Honesty constraints
-------------------
* Acquisition may use the **surrogate** Jacobian only. Using the SG oracle's
  Jacobian to choose where to measure would be using the answer to pick the
  question -- the measurement is the thing being economised.
* ``lambda_min`` of a rank-deficient design is 0, which makes E-optimality
  degenerate before the design has rank P. We use the standard regularised
  form ``lambda_min(M + eps I)``, and for under-determined designs fall back
  to the largest *gain along currently-unresolved directions*, which is the
  same idea expressed on the null space.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

__all__ = [
    "DESIGN_STRATEGIES",
    "design_information_matrix",
    "design_scores",
    "design_summary",
    "greedy_design",
    "select_next_bias",
]

#: Strategies compared in ``scripts/run_experiment_design.py``.
DESIGN_STRATEGIES = ("random", "max_std", "d_optimal", "e_optimal",
                     "null_space", "std_x_nullspace")


def design_information_matrix(J: np.ndarray, selected: Sequence[int],
                              noise_symlog: float = 1.0) -> np.ndarray:
    """Fisher information ``sum_i J_i J_i^T / sigma^2`` for a chosen design."""
    P = J.shape[1]
    if len(selected) == 0:
        return np.zeros((P, P))
    Js = J[list(selected)]
    return (Js.T @ Js) / (noise_symlog ** 2)


def _unresolved_subspace(J: np.ndarray, selected: Sequence[int],
                         tol: float) -> np.ndarray:
    """Right singular vectors of the *current* design that are unresolved.

    Columns span the directions the measurements taken so far cannot
    distinguish from zero. With no measurements yet this is all of R^P.
    """
    P = J.shape[1]
    if len(selected) == 0:
        return np.eye(P)
    _, S, Vt = np.linalg.svd(J[list(selected)], full_matrices=True)
    S_full = np.concatenate([S, np.zeros(P - S.size)]) if S.size < P else S
    return Vt.T[:, S_full <= tol]


def design_scores(J: np.ndarray, selected: Sequence[int],
                  candidates: Sequence[int], strategy: str,
                  *, sigma: Optional[np.ndarray] = None,
                  noise_symlog: float = 1.0,
                  rng: Optional[np.random.Generator] = None,
                  ridge: float = 1e-12) -> np.ndarray:
    """Score every candidate bias under one design strategy. Higher is better.

    Parameters
    ----------
    J : (B, P) Jacobian of symlog(I) w.r.t. log10|C|, from the **surrogate**.
    selected : indices already measured.
    candidates : indices still available.
    sigma : (B,) predictive std per bias, required by the uncertainty
        strategies.
    """
    cand = list(candidates)
    if strategy == "random":
        rng = rng or np.random.default_rng()
        return rng.random(len(cand))

    if strategy == "max_std":
        if sigma is None:
            raise ValueError("max_std needs the predictive sigma")
        return np.asarray([float(sigma[i]) for i in cand])

    M = design_information_matrix(J, selected, noise_symlog)
    P = J.shape[1]

    if strategy in ("d_optimal", "e_optimal"):
        out = []
        for i in cand:
            Mi = M + np.outer(J[i], J[i]) / noise_symlog ** 2
            ev = np.linalg.eigvalsh(Mi + ridge * np.eye(P))
            if strategy == "d_optimal":
                # log det of the *resolved* part; a rank-deficient design has
                # log det = -inf, which would make every candidate tie.
                pos = ev[ev > ridge * 10]
                out.append(float(np.sum(np.log(pos))) if pos.size else -np.inf)
            else:
                out.append(float(ev[0]))
        return np.asarray(out)

    if strategy in ("null_space", "std_x_nullspace"):
        # How much signal does this bias put into directions the design
        # currently cannot see at all? This is E-optimality's intent, valid
        # while the design is still rank-deficient.
        smax = float(np.linalg.norm(J, 2))
        Nsp = _unresolved_subspace(J, selected, tol=1e-9 * max(smax, 1.0))
        if Nsp.shape[1] == 0:
            base = np.asarray([float(np.linalg.norm(J[i])) for i in cand])
        else:
            base = np.asarray([float(np.linalg.norm(Nsp.T @ J[i])) for i in cand])
        if strategy == "null_space":
            return base
        if sigma is None:
            raise ValueError("std_x_nullspace needs the predictive sigma")
        s = np.asarray([float(sigma[i]) for i in cand])
        # Rank-combine so the product is not dominated by whichever factor
        # happens to have the larger dynamic range.
        return _rank01(base) * _rank01(s)

    raise ValueError(f"unknown strategy {strategy!r}")


def _rank01(v: np.ndarray) -> np.ndarray:
    """Map values to their ranks in [0, 1]; ties broken by order."""
    if v.size <= 1:
        return np.ones_like(v, dtype=float)
    r = np.argsort(np.argsort(v)).astype(float)
    return r / (v.size - 1)


def select_next_bias(J: np.ndarray, selected: Sequence[int],
                     candidates: Sequence[int], strategy: str,
                     **kw) -> int:
    """Index (into the full bias array) of the next bias to measure."""
    cand = list(candidates)
    if not cand:
        raise ValueError("no candidate biases left")
    scores = design_scores(J, selected, cand, strategy, **kw)
    return int(cand[int(np.argmax(scores))])


def greedy_design(J: np.ndarray, candidates: Sequence[int], budget: int,
                  strategy: str, **kw) -> List[int]:
    """Greedily build a design of ``budget`` biases under one strategy."""
    selected: List[int] = []
    remaining = list(candidates)
    for _ in range(min(budget, len(remaining))):
        nxt = select_next_bias(J, selected, remaining, strategy, **kw)
        selected.append(nxt)
        remaining.remove(nxt)
    return selected


def design_summary(J_true: np.ndarray, selected: Sequence[int],
                   noise_rel: float = 0.02,
                   jacobian_noise: float = 0.0) -> Dict[str, float]:
    """Evaluate a finished design against the *true* (SG) Jacobian."""
    from ..inverse.identifiability import analyse_identifiability
    rep = analyse_identifiability(J_true[list(selected)], noise_rel=noise_rel,
                                  jacobian_noise=jacobian_noise)
    S = rep.singular_values
    pos = S[S > 0]
    return {
        "n_biases": len(selected),
        "identifiable_rank": int(rep.identifiable_rank),
        "resolvable_rank": int(rep.resolvable_rank),
        "log_det_information": float(2.0 * np.sum(np.log(pos))) if pos.size else -np.inf,
        "smallest_resolved_sigma": float(S[max(rep.identifiable_rank - 1, 0)])
        if rep.identifiable_rank > 0 else 0.0,
        "sigma_max": float(S[0]) if S.size else 0.0,
    }
