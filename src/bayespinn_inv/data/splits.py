"""The canonical evaluation protocol: doping-level splits and SG labels.

This is the single implementation of the project's experimental protocol.
``scripts/run_results.py`` (the headline table) and
``scripts/run_uq_benchmark.py`` (the three-backend uncertainty comparison)
both build their data from here, which is what makes their numbers
comparable: identical splits, identical label filtering, identical
transforms. Duplicating this logic per script is how two "test sets" with
the same name end up meaning different things -- AUDIT_MASTER SCI-01.

The splits
----------
Five level sets, disjoint in doping level by construction and asserted so at
runtime:

``train``
    Geometrically spaced across the training band.
``calibration_val``
    Inside the band but off the training levels -- where a temperature is
    fitted. Never used to report a test number.
``test_interp``
    Geometric midpoints *between* adjacent training levels: interpolation.
``test_extrap``
    Strictly outside the training band, on **both** sides.
``test_family_graded``
    A different profile family (tanh-graded rather than step): shape
    transfer, not just level transfer.

A "sample" is one (doping profile, bias) pair. Levels never cross splits, so
the 13 bias points of one profile can never be split across train and test --
the leakage mode that a naive random split of I--V rows would introduce.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

__all__ = [
    "ProtocolSpec",
    "build_level_splits",
    "build_sg_labels",
    "graded_profile",
    "oracle_iv",
    "step_profile",
]


@dataclass(frozen=True)
class ProtocolSpec:
    """Every constant that defines the experimental protocol."""

    domain_si: Tuple[float, float] = (0.0, 1e-6)
    n_anchor: int = 16
    bias_max: float = 0.6
    n_bias: int = 13
    seed: int = 0
    #: Training band, deliberately narrower than the test bands so that
    #: extrapolation can actually be measured (AUDIT_MASTER SCI-06).
    train_lo: float = 1.0e21
    train_hi: float = 2.0e22
    #: Extrapolation band; straddles the training band on both sides.
    extrap_lo: float = 2.0e20
    extrap_hi: float = 8.0e22
    n_train_levels: int = 12
    #: SNR the SG terminal current must clear to be used as a label.
    trust_snr: float = 10.0
    graded_width_si: float = 1.5e-7

    @property
    def biases(self) -> np.ndarray:
        return np.linspace(0.0, self.bias_max, self.n_bias)

    def anchor_x(self) -> np.ndarray:
        return np.linspace(self.domain_si[0], self.domain_si[1], self.n_anchor)


def step_profile(xa: np.ndarray, level: float,
                 xj: Optional[float] = None) -> np.ndarray:
    """Abrupt PN step junction: -level on the p side, +level on the n side."""
    xj = xj if xj is not None else 0.5 * float(np.max(xa))
    return np.where(xa < xj, -level, level).astype(np.float64)


def graded_profile(xa: np.ndarray, level: float,
                   width: float = 1.5e-7) -> np.ndarray:
    """tanh-graded junction -- a profile *shape* absent from training."""
    xj = 0.5 * float(np.max(xa))
    return (level * np.tanh((xa - xj) / width)).astype(np.float64)


def build_level_splits(spec: ProtocolSpec) -> Dict[str, np.ndarray]:
    """Return the five disjoint doping-level sets.

    Disjointness is asserted here, not assumed: a silent overlap between the
    training levels and any evaluation set would make every downstream number
    an interpolation result wearing an extrapolation label.
    """
    train = np.geomspace(spec.train_lo, spec.train_hi, spec.n_train_levels)
    interp = np.sqrt(train[:-1] * train[1:])[::2]
    extrap = np.concatenate([
        np.geomspace(spec.extrap_lo, spec.train_lo * 0.7, 3),
        np.geomspace(spec.train_hi * 1.4, spec.extrap_hi, 3),
    ])
    val = np.geomspace(spec.train_lo * 1.15, spec.train_hi * 0.87, 5)
    val = np.array([v for v in val
                    if np.min(np.abs(np.log10(v / train))) > 0.02])
    family = np.geomspace(spec.train_lo * 1.3, spec.train_hi * 0.8, 5)

    splits = {
        "train": train,
        "calibration_val": val,
        "test_interp": interp,
        "test_extrap": extrap,
        "test_family_graded": family,
    }
    for name, levels in splits.items():
        if name == "train":
            continue
        gap = float(np.min(np.abs(np.log10(levels[:, None] / train[None, :]))))
        assert gap > 1e-3, f"{name} overlaps the training levels (gap {gap})"
    return splits


def oracle_iv(sg, C: np.ndarray, biases: np.ndarray,
              trust_snr: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """SG I--V sweep with continuation warm-start, plus per-point trust flags.

    A point is trustworthy only when the solve converged *and* the terminal
    current clears the solver's own noise floor. Near equilibrium the true
    current falls below the floor of any finite-precision drift-diffusion
    solve, so those points are numerical noise, not measurements
    (AUDIT_MASTER BUG-04, ADR-0002).
    """
    prev, I, trust = None, [], []
    for V in biases:
        st = sg.solve(C, float(V), initial_state=prev)
        prev = st
        I.append(st.terminal_current)
        trust.append(bool(st.converged and st.current_is_trustworthy(trust_snr)))
    return np.asarray(I), np.asarray(trust)


def build_sg_labels(sg, scaling, symlog, levels: np.ndarray,
                    spec: ProtocolSpec, family: str = "step"):
    """Generate ``(X, Y, integrity)`` supervision from the SG oracle.

    ``X`` rows are ``[doping_latent (n_anchor), bias / V_T]``; ``Y`` is the
    symlog-transformed terminal current. Untrustworthy points are dropped and
    counted -- never silently discarded.
    """
    xa = spec.anchor_x()
    biases = spec.biases
    V_T = scaling.V_T
    X, Y, n_drop, n_total = [], [], 0, 0
    for lv in levels:
        C = (step_profile(xa, lv) if family == "step"
             else graded_profile(xa, lv, spec.graded_width_si))
        latent = scaling.doping_to_net_input(C)
        I, trust = oracle_iv(sg, C, biases, spec.trust_snr)
        for bi, V in enumerate(biases):
            n_total += 1
            if not trust[bi]:
                n_drop += 1
                continue
            X.append(np.concatenate([latent, [V / V_T]]).astype(np.float32))
            Y.append(np.float32(symlog.forward(I[bi])))
    X_arr = np.asarray(X, dtype=np.float32)
    Y_arr = np.asarray(Y, dtype=np.float32)
    integrity = {
        "n_candidate_labels": int(n_total),
        "n_dropped_untrustworthy": int(n_drop),
        "n_used": int(X_arr.shape[0]),
        "why": "SG terminal current below its own numerical noise floor near "
               "equilibrium; fitting it would be fitting noise",
    }
    return X_arr, Y_arr, integrity
