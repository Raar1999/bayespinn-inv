"""Global identifiability of the doping profile from terminal I--V.

Seed item **S-1**, the highest remaining scientific risk in this project. Every
identifiability number the repository publishes is *local*: the numerical rank of
the forward Jacobian at one operating point. A local rank says which directions
are flat **here**. It says nothing about whether a distant profile fits the same
I--V equally well, and nothing in the repository has ever ruled that out.

This module measures two things the local analysis cannot:

``witness_search``
    Does a pair of profiles exist, far apart in parameter space, whose oracle
    observations differ by less than the distinguishability floor? Such a pair is
    a **concrete, checkable witness** of global non-identifiability -- not a rank,
    an example, with both profiles and both I--V curves attached.

``contraction_spectrum``
    How much does the data contract the prior, per direction? Compared against
    the local rank, this says whether the local framing under- or over-states the
    information actually available.

The arbiter rule
----------------
**The oracle decides; the surrogate may only propose.** ``GRAD-01`` measured
surrogate directional derivatives as agreeing with the SG solver *only inside the
identifiable subspace* (mean cosine +0.504 inside, -0.001 outside, unchanged by a
33x training-budget increase). A global study probes precisely outside that
subspace, so using the surrogate to arbitrate it would manufacture the
conclusion. PH-22 adds a second, independent reason: the surrogate path is
float32 and cannot represent doping differences below ~1e-7 relative, where the
float64 oracle round-trips to 1.678e-16.

Every function here therefore takes an ``oracle`` callable and records, for every
evaluation, whether the solver converged and whether it certified its own current
(``current_is_trustworthy()``). Evaluations that fail either are **counted and
reported**, never silently dropped (PH-19).

Floors
------
Two floors, computed in one place and reported separately -- never subtracted
(PH-13, ADR-0002):

* the **solver discretisation floor**, from a grid-refinement comparison;
* the **measurement noise floor**, from the stated noise model.

The **distinguishability floor** is their maximum. Two profiles whose observations
differ by less than it are indistinguishable *by this instrument and this solver*,
and calling them "identifiable" would be a statement about arithmetic rather than
about the device.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "GlobalStudyConfig",
    "contraction_spectrum",
    "witness_search",
]


@dataclass(frozen=True)
class GlobalStudyConfig:
    """Everything that defines a global identifiability measurement.

    Frozen, and hashed by :meth:`prior_hash` **before** sampling begins (``AH-14``:
    a prior adjusted after seeing contraction is ``AH-04`` under another name).

    Attributes
    ----------
    n_anchor
        Parameterisation dimension ``d``. The result is meaningless without it
        (``SPEC-g6-3``): "3-4 of 16" and "3-4 of 4" are different claims.
    prior_lo_si, prior_hi_si
        Log-uniform prior support on the magnitude of the doping at each anchor,
        in m^-3. The result is reported *relative to this prior*, not absolutely.
    biases
        Observation set, in volts. Defaults to the range over which the oracle's
        discretisation error was measured to converge.
    noise_rel
        Relative measurement noise on the terminal current.
    discretisation_floor_rel
        Relative solver discretisation error, measured by grid refinement.
    domain_si
        Device extent in metres.
    seed
        Single seed for every draw (SW-09).
    """

    n_anchor: int = 4
    prior_lo_si: float = 1e21
    prior_hi_si: float = 1e23
    biases: Tuple[float, ...] = tuple(np.round(np.linspace(0.15, 0.90, 16), 4))
    noise_rel: float = 2.0e-2
    discretisation_floor_rel: float = 1.5e-3
    domain_si: Tuple[float, float] = (0.0, 1e-6)
    seed: int = 0
    #: Minimum parameter-space separation, in decades, for a pair to count as
    #: "far apart". 0.3 decades is a factor of 2 in doping.
    min_separation_decades: float = 0.3

    @property
    def distinguishability_floor(self) -> float:
        """max(noise floor, solver discretisation floor). Both also reported."""
        return max(self.noise_rel, self.discretisation_floor_rel)

    def prior_hash(self) -> str:
        """SHA-256 of the prior specification, for recording before sampling."""
        payload = {
            "n_anchor": self.n_anchor,
            "prior_lo_si": self.prior_lo_si,
            "prior_hi_si": self.prior_hi_si,
            "biases": list(self.biases),
            "noise_rel": self.noise_rel,
            "domain_si": list(self.domain_si),
            "seed": self.seed,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> Dict:
        out = asdict(self)
        out["biases"] = list(self.biases)
        out["domain_si"] = list(self.domain_si)
        out["distinguishability_floor"] = self.distinguishability_floor
        out["prior_hash"] = self.prior_hash()
        return out


@dataclass
class OracleSample:
    """One profile and the oracle's verdict on it."""

    log10_mag: np.ndarray          #: (d,) log10 |doping| in m^-3
    current: np.ndarray            #: (n_bias,) terminal current, A/m^2
    trustworthy: np.ndarray        #: (n_bias,) per-bias trust flag
    converged: np.ndarray          #: (n_bias,) per-bias convergence flag

    @property
    def usable(self) -> bool:
        """Every observation certified by the solver itself (PH-08)."""
        return bool(self.trustworthy.all() and self.converged.all())


def _draw_profiles(cfg: GlobalStudyConfig, n: int) -> np.ndarray:
    """``n`` log-uniform draws of shape (n, d). Seeded from ``cfg.seed`` alone."""
    rng = np.random.default_rng(cfg.seed)
    lo, hi = np.log10(cfg.prior_lo_si), np.log10(cfg.prior_hi_si)
    return rng.uniform(lo, hi, size=(n, cfg.n_anchor))


def _sample_oracle(
    cfg: GlobalStudyConfig,
    oracle: Callable[[np.ndarray, Sequence[float]], Tuple[np.ndarray, np.ndarray, np.ndarray]],
    log10_mag: np.ndarray,
) -> OracleSample:
    current, trust, conv = oracle(log10_mag, cfg.biases)
    return OracleSample(
        log10_mag=np.asarray(log10_mag, dtype=np.float64),
        current=np.asarray(current, dtype=np.float64),
        trustworthy=np.asarray(trust, dtype=bool),
        converged=np.asarray(conv, dtype=bool),
    )


def _observational_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Max relative difference in terminal current, comparable to the noise floor.

    Relative because the noise model is relative, and max rather than mean because
    a single distinguishable bias point is enough to tell two devices apart.
    """
    denom = np.maximum(np.abs(a), np.abs(b))
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.abs(a - b) / denom
    rel = rel[np.isfinite(rel)]
    return float(np.max(rel)) if rel.size else float("inf")


def _collect(
    cfg: GlobalStudyConfig,
    oracle: Callable,
    n: int,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Tuple[List[OracleSample], Dict[str, int]]:
    """Draw and solve ``n`` profiles, keeping only those the oracle certifies.

    Rejections are counted by reason and returned, never silently dropped
    (PH-19: every filter states its predicate and its removal count).
    """
    draws = _draw_profiles(cfg, n)
    kept: List[OracleSample] = []
    counts = {"drawn": n, "kept": 0, "rejected_not_converged": 0,
              "rejected_not_trustworthy": 0}
    for i, lm in enumerate(draws):
        sample = _sample_oracle(cfg, oracle, lm)
        if not sample.converged.all():
            counts["rejected_not_converged"] += 1
        elif not sample.trustworthy.all():
            counts["rejected_not_trustworthy"] += 1
        else:
            kept.append(sample)
        if progress is not None:
            progress(i + 1, n)
    counts["kept"] = len(kept)
    return kept, counts


def witness_search(
    cfg: GlobalStudyConfig,
    oracle: Callable,
    n_samples: int,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """Hunt for two distant profiles the instrument cannot tell apart.

    Samples ``n_samples`` profiles from the prior, solves each **on the oracle**,
    and examines all pairs. Sampling once and comparing pairwise gives
    ``n(n-1)/2`` candidate pairs from ``n`` solves, which is what makes an
    oracle-arbitrated search affordable at all.

    A **witness** is a pair whose parameter separation is at least
    ``cfg.min_separation_decades`` and whose observational distance is below
    ``cfg.distinguishability_floor``.

    Returns a dict carrying the closest pairs found, the rejection counts, and
    both floors. ``AH-13``: if no witness is found this reports *"no witness found
    at this budget"*. That is not the same sentence as "identifiable", and only
    the first one is measured.
    """
    kept, counts = _collect(cfg, oracle, n_samples, progress)
    if len(kept) < 2:
        return {"config": cfg.to_dict(), "sampling": counts, "witnesses": [],
                "n_pairs_examined": 0,
                "verdict": "insufficient usable samples to form a pair"}

    mags = np.stack([s.log10_mag for s in kept])          # (m, d)
    curs = np.stack([s.current for s in kept])            # (m, n_bias)
    m = len(kept)

    pairs = []
    for i in range(m):
        # Vectorised over j > i: separation in decades, distance in relative current.
        sep = np.max(np.abs(mags[i + 1:] - mags[i]), axis=1)
        denom = np.maximum(np.abs(curs[i + 1:]), np.abs(curs[i]))
        with np.errstate(divide="ignore", invalid="ignore"):
            rel = np.abs(curs[i + 1:] - curs[i]) / denom
        dist = np.nanmax(rel, axis=1)
        for off in np.argsort(dist)[:8]:                  # keep the best few per i
            j = i + 1 + int(off)
            pairs.append((float(dist[off]), float(sep[off]), i, j))

    pairs.sort(key=lambda t: t[0])
    n_pairs = m * (m - 1) // 2
    floor = cfg.distinguishability_floor
    far = [p for p in pairs if p[1] >= cfg.min_separation_decades]
    witnesses = [p for p in far if p[0] < floor]

    def _render(p):
        dist, sep, i, j = p
        return {
            "observational_distance": dist,
            "separation_decades": sep,
            "profile_a_log10": kept[i].log10_mag.tolist(),
            "profile_b_log10": kept[j].log10_mag.tolist(),
            "current_a": kept[i].current.tolist(),
            "current_b": kept[j].current.tolist(),
        }

    return {
        "config": cfg.to_dict(),
        "sampling": counts,
        "n_pairs_examined": n_pairs,
        "floors": {
            "noise_rel": cfg.noise_rel,
            "discretisation_rel": cfg.discretisation_floor_rel,
            "distinguishability": floor,
        },
        "n_witnesses": len(witnesses),
        "witnesses": [_render(p) for p in witnesses[:5]],
        "closest_far_pair": _render(far[0]) if far else None,
        "closest_any_pair": _render(pairs[0]) if pairs else None,
        "verdict": (
            f"{len(witnesses)} witness pair(s) found"
            if witnesses else
            f"no witness found at this budget (n_samples={n_samples}, "
            f"{n_pairs} pairs examined, floor={floor:.3e})"
        ),
    }


def contraction_spectrum(
    cfg: GlobalStudyConfig,
    oracle: Callable,
    n_samples: int,
    truth_log10: Optional[np.ndarray] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """Prior -> posterior variance ratio per direction, arbitrated by the oracle.

    Importance sampling: draw from the prior, weight each draw by a Gaussian
    likelihood in relative current with width ``cfg.noise_rel`` around the
    observation of ``truth_log10``, and compare per-direction variance before and
    after weighting.

    A direction whose variance ratio is near 1 was not constrained by the data --
    the observation told us nothing about it that the prior did not already say.
    The count of materially contracting directions is the global analogue of the
    local Jacobian rank, and ``SPEC-g6-4`` requires the two to be compared rather
    than merely listed.

    ``AH-15``: the ratio is meaningless without its ``n`` and its prior, so both
    are returned alongside it.
    """
    kept, counts = _collect(cfg, oracle, n_samples, progress)
    if len(kept) < 10:
        return {"config": cfg.to_dict(), "sampling": counts,
                "verdict": "insufficient usable samples"}

    if truth_log10 is None:
        # Centre of the prior: a deliberate, stated choice, fixed before weighting.
        truth_log10 = np.full(
            cfg.n_anchor,
            0.5 * (np.log10(cfg.prior_lo_si) + np.log10(cfg.prior_hi_si)),
        )
    truth = _sample_oracle(cfg, oracle, np.asarray(truth_log10, dtype=np.float64))

    mags = np.stack([s.log10_mag for s in kept])
    curs = np.stack([s.current for s in kept])

    denom = np.maximum(np.abs(curs), np.abs(truth.current))
    with np.errstate(divide="ignore", invalid="ignore"):
        resid = (curs - truth.current) / denom
    resid = np.nan_to_num(resid, nan=0.0, posinf=0.0, neginf=0.0)

    prior_var = mags.var(axis=0)
    #: A direction contracts if its posterior variance is at most half the prior's.
    #: Fixed before the measurement, not chosen to hit a rank.
    threshold = 0.5
    #: Below this effective sample size the weighted variance is dominated by a
    #: handful of draws and is not an estimate of anything. Chosen before running.
    ess_floor = 20.0

    # Contraction is reported as a function of the tolerance, not at one noise
    # level. At the instrument's own 2% noise, importance sampling from a
    # 2-decade prior collapses -- essentially no random profile reproduces a
    # given I-V to 2% -- and a collapsed weight vector yields "every direction
    # contracts", which is an artefact of the estimator rather than a statement
    # about the device. Sweeping the tolerance makes the collapse visible and
    # gives the rows where the estimate is still supported. Directly analogous
    # to the existing rank-vs-instrument-quality result (C13).
    tolerances = [cfg.noise_rel * m for m in (1, 2, 5, 10, 25, 50, 100, 250)]
    rows = []
    for tol in tolerances:
        log_like = -0.5 * np.sum((resid / tol) ** 2, axis=1)
        log_like -= log_like.max()
        weights = np.exp(log_like)
        weights /= weights.sum()
        ess = float(1.0 / np.sum(weights ** 2))
        mean_w = np.sum(weights[:, None] * mags, axis=0)
        post_var = np.sum(weights[:, None] * (mags - mean_w) ** 2, axis=0)
        ratio = post_var / np.where(prior_var > 0, prior_var, np.nan)
        rows.append({
            "tolerance_rel": float(tol),
            "tolerance_multiple_of_noise": float(tol / cfg.noise_rel),
            "effective_sample_size": ess,
            "supported": bool(ess >= ess_floor),
            "variance_ratio": ratio.tolist(),
            "n_contracting_directions": int(np.sum(ratio < threshold)),
        })

    supported = [r for r in rows if r["supported"]]
    tightest = supported[0] if supported else None

    return {
        "config": cfg.to_dict(),
        "sampling": counts,
        "truth_log10": np.asarray(truth_log10, dtype=np.float64).tolist(),
        "truth_usable": truth.usable,
        "prior_variance": prior_var.tolist(),
        "contraction_threshold": threshold,
        "ess_floor": ess_floor,
        "n_directions": int(cfg.n_anchor),
        "tolerance_sweep": rows,
        "tightest_supported": tightest,
        "verdict": (
            (f"at the tightest supported tolerance "
             f"({tightest['tolerance_multiple_of_noise']:.0f}x the {cfg.noise_rel:.0%} "
             f"noise floor, ESS {tightest['effective_sample_size']:.1f}), "
             f"{tightest['n_contracting_directions']} of {cfg.n_anchor} directions "
             f"contract below ratio {threshold}")
            if tightest else
            (f"prior importance sampling collapses at every tolerance tried "
             f"(ESS < {ess_floor:g} throughout, n={len(kept)} usable samples); "
             "contraction is NOT measured at this budget")
        ),
    }
