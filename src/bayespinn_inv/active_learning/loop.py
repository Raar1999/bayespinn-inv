"""
Active learning for Bayesian inverse design of semiconductor devices.

The setting: we have a learned forward PINN with uncertainty
quantification (DeepEnsemble / MC-Dropout / SWAG). We can perform
*experiments* — each experiment is a choice of bias point and yields a
noisy I-V measurement. Each experiment is expensive (in a real lab,
hours-to-days; here, an SG-solver call standing in for the lab).

Question: at which biases should we measure next so that the
inverse-design posterior over doping shrinks fastest?

We provide three acquisition policies for a clean ablation:

1. **Random**: uniform-random bias selection (baseline).

2. **MaxStd** ("BALD-lite"): pick the bias where the *ensemble predictive
   standard deviation* on the current I-V is largest. This is the cheapest
   information-theoretic-style acquisition and is the workhorse of
   BatchBALD-flavored acquisitions in regression.

3. **BayesOpt** (UCB on inverse-loss): treat the inverse-design final
   loss after one round of inversion as the objective; use a GP
   surrogate over candidate biases. This is the strongest baseline.

All three return a dict with the same diagnostic schema, so plotting
code is acquisition-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

import numpy as np
import torch

from ..bayesian.ensembles import EnsemblePrediction
from ..inverse.inverse_design import (
    FreePointwiseDoping,
    InverseConfig,
    InverseDesigner,
)
from ..pinn.forward_pinn import ForwardPINN

# ============================================================================
# Protocols
# ============================================================================

class UQModel(Protocol):
    """Anything with a DeepEnsemble-like iv_curve interface."""
    M: int
    def iv_curve(self, doping_si, biases, with_grad: bool = False
                 ) -> Tuple[torch.Tensor, EnsemblePrediction]: ...


class OracleSolver(Protocol):
    """A trusted forward solver standing in for the lab (typically SG)."""
    def solve(self, doping_si, bias): ...


# ============================================================================
# Helper: simulate a "lab measurement" via the oracle
# ============================================================================

def simulate_measurement(
    oracle: OracleSolver,
    true_doping_si: torch.Tensor,
    bias: float,
    noise_std_rel: float = 0.02,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Run the oracle, extract terminal current, add measurement noise.

    Noise model
    -----------
    Multiplicative Gaussian on the current, plus an independent additive
    floor:

        I_meas = I * (1 + sigma * eps_mult) + I_floor * eps_add

    with ``eps_mult`` and ``eps_add`` drawn *independently*. The additive
    floor is the oracle's own numerical noise floor where available, which is
    the physically meaningful "instrument can't see below this" level for
    this simulator, rather than an arbitrary constant.

    AUDIT_MASTER AL-01: the previous implementation documented "Gaussian in
    log-current space when current is significant, additive when near zero"
    but implemented neither. It used a single draw for *both* the
    multiplicative and additive terms -- making them perfectly correlated --
    and hard-coded the additive floor at ``noise_std_rel * 1e-3`` A/m^2.

    Interpolates the user-provided doping onto the oracle's native grid
    before solving (the oracle decides the simulation resolution; the
    user just provides a profile sampled on any grid).
    """
    if rng is None:
        rng = np.random.default_rng()
    # Interpolate doping to the oracle's grid if shapes differ.
    if hasattr(oracle, "grid") and hasattr(oracle, "scaling"):
        N_oracle = oracle.grid.N
        if isinstance(true_doping_si, torch.Tensor):
            doping_np = true_doping_si.detach().cpu().numpy()
        else:
            doping_np = np.asarray(true_doping_si)
        if doping_np.shape[0] != N_oracle:
            x_user = np.linspace(0.0, 1.0, doping_np.shape[0])
            x_oracle = np.linspace(0.0, 1.0, N_oracle)
            doping_for_oracle = np.interp(x_oracle, x_user, doping_np)
        else:
            doping_for_oracle = doping_np
    else:
        doping_for_oracle = (true_doping_si.detach().cpu().numpy()
                              if isinstance(true_doping_si, torch.Tensor)
                              else true_doping_si)
    state = oracle.solve(doping_for_oracle, bias)
    if hasattr(state, "terminal_current"):
        I = float(state.terminal_current)
    else:
        # DOC-02: terminal current is mean(Jn + Jp), NOT 0.5*(mean Jn + mean Jp)
        # -- the old fallback was low by a factor of two.
        I = float(np.mean(state.Jn + state.Jp))
    floor = float(getattr(state, "current_noise_floor", 0.0) or 0.0)
    eps_mult, eps_add = rng.normal(0.0, 1.0, size=2)
    noisy = I * (1.0 + noise_std_rel * eps_mult) + floor * eps_add
    return float(noisy)


# ============================================================================
# Acquisition strategies
# ============================================================================

def acquire_random(
    candidate_biases: np.ndarray,
    rng: np.random.Generator,
    **_kwargs,
) -> int:
    """Return the index of a uniformly-random candidate."""
    return int(rng.integers(0, len(candidate_biases)))


def acquire_max_std(
    candidate_biases: np.ndarray,
    uq: UQModel,
    current_doping_si: torch.Tensor,
    **_kwargs,
) -> int:
    """Return the candidate index with maximum ensemble std in predicted I."""
    biases_list = list(candidate_biases.tolist())
    with torch.no_grad():
        _, pred = uq.iv_curve(current_doping_si, biases_list)
    # std normalized by mean magnitude (avoid scale dominance)
    rel_std = pred.std / np.maximum(np.abs(pred.mean), 1e-9)
    return int(np.argmax(rel_std))


def acquire_ucb(
    candidate_biases: np.ndarray,
    history_pairs: List[Tuple[float, float]],   # (bias_added, loss_after) per round
    rng: np.random.Generator,
    kappa: float = 2.0,
    **_kwargs,
) -> int:
    """UCB selection over candidates using a tiny GP surrogate.

    ``history_pairs`` is a list of ``(bias_added_that_round, loss_after_inversion)``
    tuples, one per completed AL round. Falls back to random if fewer
    than 3 pairs are available or scikit-learn isn't installed.
    """
    if len(history_pairs) < 3:
        return int(rng.integers(0, len(candidate_biases)))
    try:
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import (
            RBF,
            WhiteKernel,
        )
        from sklearn.gaussian_process.kernels import (
            ConstantKernel as C,
        )
    except ImportError:
        return int(rng.integers(0, len(candidate_biases)))
    X = np.asarray([p[0] for p in history_pairs], dtype=float).reshape(-1, 1)
    y = np.asarray([p[1] for p in history_pairs], dtype=float).reshape(-1)
    y_mean, y_std = float(y.mean()), float(y.std() + 1e-12)
    y_n = (y - y_mean) / y_std
    kernel = C(1.0) * RBF(length_scale=0.1) + WhiteKernel(noise_level=1e-3)
    gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6,
                                    normalize_y=False, n_restarts_optimizer=2)
    gp.fit(X, y_n)
    Xc = candidate_biases.reshape(-1, 1)
    mu, sigma = gp.predict(Xc, return_std=True)
    # MINIMIZE loss -> argmin(mu - kappa*sigma)
    return int(np.argmin(mu - kappa * sigma))


# ============================================================================
# Main AL loop
# ============================================================================

@dataclass
class ActiveLearningConfig:
    n_rounds: int = 20
    candidate_biases: np.ndarray = field(
        default_factory=lambda: np.linspace(0.0, 0.7, 71))
    initial_biases: Sequence[float] = (0.0, 0.3, 0.6)
    strategy: str = "max_std"          # "random", "max_std", "ucb"
    inverse_cfg: InverseConfig = field(default_factory=InverseConfig)
    n_inverse_iters: int = 300
    measurement_noise_rel: float = 0.02
    seed: int = 0


@dataclass
class ALRoundLog:
    round_idx: int
    chosen_bias: float
    inverse_loss: float
    doping_error_l2: float
    doping_error_relative: float


def active_learning_loop(
    uq_model: UQModel,
    oracle: OracleSolver,
    true_doping_si: torch.Tensor,
    forward_for_inverse: ForwardPINN,
    initial_doping_si: torch.Tensor,
    cfg: Optional[ActiveLearningConfig] = None,
) -> Dict[str, Any]:
    """Run one full active learning trajectory.

    Returns
    -------
    dict with:
      "biases_acquired": list[float]
      "measurements": list[float]
      "log": list[ALRoundLog]
      "final_doping": np.ndarray
      "strategy": str
    """
    cfg = cfg or ActiveLearningConfig()
    rng = np.random.default_rng(cfg.seed)

    # Initial measurements
    biases_acquired = list(cfg.initial_biases)
    measurements = [
        simulate_measurement(oracle, true_doping_si, V,
                              noise_std_rel=cfg.measurement_noise_rel, rng=rng)
        for V in biases_acquired
    ]
    log: List[ALRoundLog] = []
    history_losses: List[float] = []

    # Build a fresh inverse-design parameterization & designer
    x_si = torch.linspace(0, forward_for_inverse.cfg.domain_si[1],
                           initial_doping_si.shape[0])
    icfg = InverseConfig(
        n_iters=cfg.n_inverse_iters,
        lr=cfg.inverse_cfg.lr,
        optimizer=cfg.inverse_cfg.optimizer,
        lambda_TV=cfg.inverse_cfg.lambda_TV,
        lambda_smooth=cfg.inverse_cfg.lambda_smooth,
        lambda_solubility=cfg.inverse_cfg.lambda_solubility,
        C_max_si=cfg.inverse_cfg.C_max_si,
        seed=cfg.seed,
        log_every=cfg.inverse_cfg.log_every,
    )

    current_doping = initial_doping_si.detach().clone()
    designer = InverseDesigner(forward_for_inverse, icfg)
    # Matched (bias_added_that_round, loss_after_inversion) pairs for UCB.
    ucb_history: List[Tuple[float, float]] = []
    last_added_bias: Optional[float] = None

    for r in range(cfg.n_rounds):
        # 1) Solve inverse problem with current data
        target_b = torch.as_tensor(biases_acquired, dtype=torch.float32)
        target_I = torch.as_tensor(measurements, dtype=torch.float32)
        param = FreePointwiseDoping(x_si, current_doping)
        result = designer.design(param, target_b, target_I)
        current_doping = result.C_recovered_si.detach()
        history_losses.append(result.final_loss)
        if last_added_bias is not None:
            ucb_history.append((last_added_bias, result.final_loss))

        # 2) Pick next bias
        if cfg.strategy == "random":
            idx = acquire_random(cfg.candidate_biases, rng=rng)
        elif cfg.strategy == "max_std":
            idx = acquire_max_std(cfg.candidate_biases, uq_model,
                                    current_doping)
        elif cfg.strategy == "ucb":
            idx = acquire_ucb(cfg.candidate_biases, ucb_history, rng=rng)
        else:
            raise ValueError(f"Unknown strategy: {cfg.strategy!r}")
        next_bias = float(cfg.candidate_biases[idx])
        # Avoid trivial duplicate selections
        if next_bias in biases_acquired:
            # Move a small step (~ resolution of the bias grid)
            dB = float(np.median(np.diff(cfg.candidate_biases)))
            next_bias = float(np.clip(next_bias + dB,
                                         cfg.candidate_biases[0],
                                         cfg.candidate_biases[-1]))

        # 3) Acquire measurement
        m = simulate_measurement(oracle, true_doping_si, next_bias,
                                   noise_std_rel=cfg.measurement_noise_rel,
                                   rng=rng)
        biases_acquired.append(next_bias)
        measurements.append(m)
        last_added_bias = next_bias

        # 4) Log
        err = (current_doping - true_doping_si).detach().cpu().numpy()
        l2 = float(np.linalg.norm(err))
        rel = l2 / max(float(np.linalg.norm(true_doping_si.detach())), 1e-30)
        log.append(ALRoundLog(
            round_idx=r,
            chosen_bias=next_bias,
            inverse_loss=result.final_loss,
            doping_error_l2=l2,
            doping_error_relative=rel,
        ))

    return {
        "biases_acquired": biases_acquired,
        "measurements": measurements,
        "log": log,
        "final_doping": current_doping.detach().cpu().numpy(),
        "strategy": cfg.strategy,
    }


__all__ = [
    "ALRoundLog",
    "ActiveLearningConfig",
    "acquire_max_std",
    "acquire_random",
    "acquire_ucb",
    "active_learning_loop",
    "simulate_measurement",
]
