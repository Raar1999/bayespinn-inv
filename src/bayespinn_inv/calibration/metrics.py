"""
Calibration metrics and post-hoc recalibration for regression UQ.

We use the regression definitions consistent with Kuleshov et al.
(ICML 2018) and Gneiting & Raftery (JASA 2007):

- **Expected Calibration Error (ECE)** for regression: bin predicted
  quantiles into deciles, compare to empirical coverage. A perfectly
  calibrated model satisfies P(y <= F^{-1}(q)) = q for all q in [0, 1].

- **Continuous Ranked Probability Score (CRPS)**: a proper scoring rule
  for predictive distributions. CRPS(F, y) = integral (F(z) - 1{z>=y})^2 dz.
  For Gaussian predictions, there is a closed form; otherwise we use the
  empirical-CDF estimator on the ensemble samples.

- **Negative Log-Likelihood (NLL)**: assuming Gaussian predictive,
  -log N(y; mu, sigma^2). Used for sanity check; sensitive to outliers.

- **Sharpness**: average predictive std. Used jointly with calibration —
  a perfectly calibrated but very-wide prediction is uninformative.

Post-hoc recalibration:
- **Temperature scaling** (Guo et al. 2017) adapted to regression:
  scale predictive std by a single learned factor T to minimize NLL on
  a validation set. Cheap (1 scalar), interpretable, often sufficient.
- **Isotonic regression** on the quantile CDF: more flexible but needs
  more validation data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np

from ..bayesian.ensembles import EnsemblePrediction

# ============================================================================
# Reliability diagram + ECE
# ============================================================================

def reliability_diagram_regression(
    samples: np.ndarray,             # (M, N) predictive samples
    y_true: np.ndarray,              # (N,) ground truth
    n_bins: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute reliability curve (predicted_quantile, empirical_frequency).

    For each predicted quantile level q in [0, 1] (sampled at n_bins+1
    points), compute the fraction of test points whose true value falls
    at or below the predictive q-quantile.

    Returns
    -------
    predicted_q : (n_bins+1,) target quantile levels
    empirical_q : (n_bins+1,) empirical fractions
    """
    if samples.ndim != 2 or samples.shape[1] != y_true.shape[0]:
        raise ValueError("samples must be (M, N) and y_true (N,)")
    predicted_q = np.linspace(0.0, 1.0, n_bins + 1)
    empirical_q = np.empty_like(predicted_q)
    for i, q in enumerate(predicted_q):
        # Predictive q-quantile at each data point
        q_pred = np.quantile(samples, q, axis=0)        # (N,)
        empirical_q[i] = float((y_true <= q_pred).mean())
    return predicted_q, empirical_q


def ece_floor_for_ensemble(M: int, n_bins: int = 10,
                           n_samples: int = 20000) -> float:
    """Smallest ECE a *perfectly calibrated* M-member ensemble can achieve.

    :func:`reliability_diagram_regression` uses the raw ensemble ECDF as the
    predictive distribution. With M members, the q-quantile is estimated from
    M order statistics, so even for a flawless model
    ``P(y <= min of M) ~ 1/(M+1)`` rather than 0. The reliability curve is
    therefore biased at the extremes and ECE has a positive floor.

    This function returns that floor (computed for the exactly-calibrated
    case) so ECE differences smaller than it are not over-interpreted.
    Measured floors (n_bins = 10): M=3 -> 0.13, M=5 -> 0.085, M=10 -> 0.046,
    M=20 -> 0.027. The project previously reported "ECE 0.224 -> 0.086 after
    temperature scaling" for an M=5 ensemble: 0.086 is *at* the M=5 floor, so
    the recalibrated model is indistinguishable from perfectly calibrated by
    this estimator, and the number should not be read as a calibration
    quality. See AUDIT_MASTER API-04.
    """
    if M < 2:
        return float("nan")
    # Estimated by simulation rather than in closed form: the closed-form
    # order-statistic argument is only approximate once np.quantile's linear
    # interpolation is taken into account (it drifts by ~4x at M = 200),
    # whereas simulating the *exact* estimator this module uses is both simple
    # and exact. Fixed seed -> deterministic, cache-able.
    rng = np.random.default_rng(12345)
    samples = rng.standard_normal((M, n_samples))
    y = rng.standard_normal(n_samples)
    return expected_calibration_error(samples, y, n_bins=n_bins)


def expected_calibration_error(
    samples: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10,
) -> float:
    """ECE = mean over bins of |predicted_q - empirical_q|.

    Lower is better; 0.0 means perfectly calibrated -- but see
    :func:`ece_floor_for_ensemble`: with a small ensemble this estimator
    cannot reach 0 even for a perfect model. Compare any reported ECE against
    that floor before claiming an improvement.
    """
    pq, eq = reliability_diagram_regression(samples, y_true, n_bins)
    return float(np.mean(np.abs(pq - eq)))


def maximum_calibration_error(
    samples: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10,
) -> float:
    """MCE = max over bins of |predicted_q - empirical_q|."""
    pq, eq = reliability_diagram_regression(samples, y_true, n_bins)
    return float(np.max(np.abs(pq - eq)))


# ============================================================================
# CRPS
# ============================================================================

def crps_gaussian(mu: np.ndarray, sigma: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Closed-form CRPS for Gaussian predictive.

    Gneiting & Raftery (2007) eq. 17.

    Returns
    -------
    per_point_crps : (N,) array of CRPS values; mean is the aggregate CRPS.
    """
    sigma = np.maximum(sigma, 1e-12)
    z = (y - mu) / sigma
    # Standard normal pdf and cdf
    pdf = np.exp(-0.5 * z ** 2) / np.sqrt(2.0 * np.pi)
    from math import erf
    erf_v = np.vectorize(erf)
    cdf = 0.5 * (1.0 + erf_v(z / np.sqrt(2.0)))
    return sigma * (z * (2.0 * cdf - 1.0) + 2.0 * pdf - 1.0 / np.sqrt(np.pi))


def crps_empirical(samples: np.ndarray, y_true: np.ndarray) -> np.ndarray:
    """Empirical-CDF CRPS estimator (Hersbach 2000).

    For an ensemble of M samples,
        CRPS = (1/M) sum_m |x_m - y| - (1/(2 M^2)) sum_{m,m'} |x_m - x_m'|

    Returns
    -------
    per_point_crps : (N,) array; mean is the aggregate CRPS.
    """
    if samples.ndim != 2 or samples.shape[1] != y_true.shape[0]:
        raise ValueError("samples must be (M, N), y_true (N,)")
    M, N = samples.shape
    # Term 1: (1/M) sum_m |x_m - y|
    term1 = np.abs(samples - y_true[None, :]).mean(axis=0)        # (N,)
    # Term 2: (1/(2 M^2)) sum_{m,m'} |x_m - x_m'| -- O(M log M) via sort.
    s_sorted = np.sort(samples, axis=0)
    weights = (2.0 * np.arange(1, M + 1) - 1.0 - M) / (M * M)
    term2 = (weights[:, None] * s_sorted).sum(axis=0)
    return term1 - term2


# ============================================================================
# NLL + sharpness
# ============================================================================

def gaussian_nll(mu: np.ndarray, sigma: np.ndarray, y: np.ndarray) -> float:
    sigma = np.maximum(sigma, 1e-12)
    return float(np.mean(
        0.5 * np.log(2.0 * np.pi * sigma ** 2) + 0.5 * ((y - mu) / sigma) ** 2
    ))


def sharpness(sigma: np.ndarray) -> float:
    """Mean predictive standard deviation."""
    return float(np.mean(sigma))


# ============================================================================
# Temperature scaling (regression)
# ============================================================================

def fit_temperature_regression(
    mu: np.ndarray, sigma: np.ndarray, y: np.ndarray,
    T_init: float = 1.0,
    n_iters: int = 200,
    lr: float = 0.05,
) -> float:
    """Fit a single scalar T such that ``sigma_calibrated = T * sigma``
    minimizes Gaussian NLL on (mu, sigma, y).

    Uses simple log-space gradient descent on log T so T > 0 always.
    """
    log_T = np.log(T_init)
    sigma = np.maximum(sigma, 1e-12)
    z2 = ((y - mu) / sigma) ** 2
    for _ in range(n_iters):
        T = np.exp(log_T)
        # NLL(T) = log(T) + 0.5 * mean(z^2 / T^2)
        d_logT = 1.0 - np.mean(z2) / (T ** 2)
        log_T -= lr * d_logT
    return float(np.exp(log_T))


# ============================================================================
# Isotonic recalibration on quantile CDF
# ============================================================================

def fit_isotonic_recalibrator(
    samples: np.ndarray,
    y_true: np.ndarray,
) -> Callable[[np.ndarray], np.ndarray]:
    """Returns a function ``g(q)`` such that calibrated quantile q_cal is
    obtained from the predicted q_pred by ``g(q_pred)``. Uses isotonic
    regression on (predicted, empirical) quantiles.

    Requires scipy.
    """
    from sklearn.isotonic import IsotonicRegression
    n_bins = max(10, min(50, y_true.shape[0] // 5))
    pq, eq = reliability_diagram_regression(samples, y_true, n_bins=n_bins)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(pq, eq)
    def g(q: np.ndarray) -> np.ndarray:
        return iso.transform(np.atleast_1d(q))
    return g


# ============================================================================
# Unified report
# ============================================================================

@dataclass
class CalibrationReport:
    ece: float
    mce: float
    crps: float
    nll: float
    sharpness: float
    predicted_q: np.ndarray
    empirical_q: np.ndarray

    def summary(self) -> str:
        return (
            f"Calibration report:\n"
            f"  ECE        = {self.ece:.4f}     (lower is better, 0 = perfect)\n"
            f"  MCE        = {self.mce:.4f}     (worst-case bin error)\n"
            f"  CRPS       = {self.crps:.4e}\n"
            f"  NLL (G)    = {self.nll:.4f}\n"
            f"  Sharpness  = {self.sharpness:.4e}\n"
        )


def report_calibration(
    prediction: EnsemblePrediction,
    y_true: np.ndarray,
    n_bins: int = 10,
) -> CalibrationReport:
    samples = prediction.samples
    pq, eq = reliability_diagram_regression(samples, y_true, n_bins=n_bins)
    ece = float(np.mean(np.abs(pq - eq)))
    mce = float(np.max(np.abs(pq - eq)))
    crps = float(crps_empirical(samples, y_true).mean())
    nll = gaussian_nll(prediction.mean, prediction.std, y_true)
    sh = sharpness(prediction.std)
    return CalibrationReport(ece=ece, mce=mce, crps=crps, nll=nll,
                              sharpness=sh,
                              predicted_q=pq, empirical_q=eq)


__all__ = [
    "CalibrationReport",
    "crps_empirical",
    "crps_gaussian",
    "ece_floor_for_ensemble",
    "expected_calibration_error",
    "fit_isotonic_recalibrator",
    "fit_temperature_regression",
    "gaussian_nll",
    "maximum_calibration_error",
    "reliability_diagram_regression",
    "report_calibration",
    "sharpness",
]
