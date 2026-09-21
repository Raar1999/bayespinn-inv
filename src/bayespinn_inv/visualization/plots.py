"""
Publication-grade plotting utilities.

Every plotting function:
- Takes pre-computed data (no solver calls inside plots — separation of
  concerns).
- Returns the matplotlib ``Figure`` so the caller can ``.savefig()`` or
  embed in a notebook.
- Uses a consistent style sheet (see :func:`apply_style`) so figures are
  visually coherent across the paper.

Color palette: a colorblind-safe categorical palette derived from
seaborn's "colorblind" cycle, fixed here so we don't depend on seaborn.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np


# Defer matplotlib imports so importing this module doesn't open a backend
def _mpl():
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    return matplotlib, plt


PALETTE = {
    "blue":    "#0173B2",
    "orange":  "#DE8F05",
    "green":   "#029E73",
    "red":     "#D55E00",
    "purple":  "#CC78BC",
    "brown":   "#CA9161",
    "pink":    "#FBAFE4",
    "grey":    "#949494",
    "yellow":  "#ECE133",
    "cyan":    "#56B4E9",
}


def apply_style():
    matplotlib, plt = _mpl()
    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "lines.linewidth": 1.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.3,
    })


# ============================================================================
# Field profile plots (phi, E, n, p)
# ============================================================================

def plot_device_state(
    state,                       # DeviceState
    title: Optional[str] = None,
    log_carriers: bool = True,
):
    """Standard 4-panel device-state plot: phi(x), E(x), n,p(x), C(x)."""
    apply_style()
    matplotlib, plt = _mpl()
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.5))
    x_nm = state.x * 1e9
    # phi
    ax = axes[0, 0]
    ax.plot(x_nm, state.phi, color=PALETTE["blue"])
    ax.set_ylabel(r"$\phi$ (V)")
    ax.set_xlabel("x (nm)")
    ax.set_title("Electrostatic potential")
    # E
    E = -np.gradient(state.phi, state.x)
    ax = axes[0, 1]
    ax.plot(x_nm, E * 1e-5, color=PALETTE["red"])
    ax.set_ylabel(r"$E$ (kV/cm)")
    ax.set_xlabel("x (nm)")
    ax.set_title("Electric field")
    # carriers
    ax = axes[1, 0]
    if log_carriers:
        ax.semilogy(x_nm, np.maximum(state.n, 1e10), color=PALETTE["green"], label="n")
        ax.semilogy(x_nm, np.maximum(state.p, 1e10), color=PALETTE["orange"], label="p")
    else:
        ax.plot(x_nm, state.n, color=PALETTE["green"], label="n")
        ax.plot(x_nm, state.p, color=PALETTE["orange"], label="p")
    ax.set_ylabel(r"density (m$^{-3}$)")
    ax.set_xlabel("x (nm)")
    ax.set_title("Carrier densities")
    ax.legend()
    # doping
    ax = axes[1, 1]
    ax.plot(x_nm, state.doping, color=PALETTE["purple"])
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel(r"$C = N_D - N_A$ (m$^{-3}$)")
    ax.set_xlabel("x (nm)")
    ax.set_title("Net doping")
    if title:
        fig.suptitle(title, y=1.02)
    fig.tight_layout()
    return fig


# ============================================================================
# I-V comparison with uncertainty bands
# ============================================================================

def plot_iv_with_uncertainty(
    biases: np.ndarray,
    mean: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    ground_truth: Optional[np.ndarray] = None,
    title: Optional[str] = None,
    log_y: bool = True,
):
    """Plot I-V curve with shaded uncertainty band.

    Currents shown as |I| with sign indicated.
    """
    apply_style()
    matplotlib, plt = _mpl()
    fig, ax = plt.subplots(figsize=(4.5, 3.4))
    # We plot |I| on a log axis. Taking absolute values per-series so that
    # different solvers' sign conventions don't fight each other.
    m_abs = np.abs(mean)
    # For the band, the lower/upper of |I| are min(|lo|,|hi|) and max(|lo|,|hi|)
    # if the interval doesn't straddle zero; if it does, the lower is 0.
    lo_abs = np.minimum(np.abs(lo), np.abs(hi))
    hi_abs = np.maximum(np.abs(lo), np.abs(hi))
    straddle = (lo * hi) <= 0
    lo_abs = np.where(straddle, 0.0, lo_abs)
    if log_y:
        ax.semilogy(biases, np.maximum(m_abs, 1e-12), color=PALETTE["blue"],
                     label="Mean prediction")
        ax.fill_between(biases,
                          np.maximum(lo_abs, 1e-12), np.maximum(hi_abs, 1e-12),
                          color=PALETTE["blue"], alpha=0.25,
                          label="90% interval")
    else:
        ax.plot(biases, m_abs, color=PALETTE["blue"], label="Mean prediction")
        ax.fill_between(biases, lo_abs, hi_abs, color=PALETTE["blue"], alpha=0.25,
                          label="90% interval")
    if ground_truth is not None:
        g_abs = np.abs(ground_truth)
        ax.plot(biases, np.maximum(g_abs, 1e-12) if log_y else g_abs,
                 "o-", color=PALETTE["red"],
                 mfc="white", ms=4, label="Ground truth (SG)")
    ax.set_xlabel("Bias (V)")
    ax.set_ylabel(r"$|I|$ (A/m$^2$)")
    if title:
        ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


# ============================================================================
# Doping recovery plot
# ============================================================================

def plot_doping_recovery(
    x_si: np.ndarray,
    C_recovered_mean: np.ndarray,
    C_recovered_lo: Optional[np.ndarray] = None,
    C_recovered_hi: Optional[np.ndarray] = None,
    C_true: Optional[np.ndarray] = None,
    title: Optional[str] = None,
):
    """Plot recovered doping profile with optional true profile and band."""
    apply_style()
    matplotlib, plt = _mpl()
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    x_nm = x_si * 1e9
    ax.plot(x_nm, C_recovered_mean, color=PALETTE["blue"],
             label="Recovered (mean)")
    if C_recovered_lo is not None and C_recovered_hi is not None:
        ax.fill_between(x_nm, C_recovered_lo, C_recovered_hi,
                          color=PALETTE["blue"], alpha=0.25,
                          label="90% interval")
    if C_true is not None:
        ax.plot(x_nm, C_true, "--", color=PALETTE["red"],
                 label="Ground truth")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("x (nm)")
    ax.set_ylabel(r"$C(x)$ (m$^{-3}$)")
    if title:
        ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


# ============================================================================
# Reliability diagram
# ============================================================================

def plot_reliability_diagram(
    predicted_q: np.ndarray,
    empirical_q: np.ndarray,
    ece: Optional[float] = None,
    title: Optional[str] = None,
):
    """Reliability curve with the diagonal as the ideal."""
    apply_style()
    matplotlib, plt = _mpl()
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    ax.plot([0, 1], [0, 1], "k--", lw=1.0, label="Ideal")
    ax.plot(predicted_q, empirical_q, "o-",
             color=PALETTE["blue"], ms=4, label="Observed")
    ax.fill_between(predicted_q, predicted_q, empirical_q,
                      color=PALETTE["grey"], alpha=0.18)
    ax.set_xlabel("Predicted quantile")
    ax.set_ylabel("Empirical quantile")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    if ece is not None:
        ax.text(0.05, 0.92, f"ECE = {ece:.3f}",
                 transform=ax.transAxes, fontsize=9,
                 bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))
    if title:
        ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


# ============================================================================
# Active learning convergence plot
# ============================================================================

def plot_active_learning_convergence(
    results: Dict[str, List],          # {strategy_name: [round_logs ...]}
    metric: str = "doping_error_relative",
    title: Optional[str] = None,
):
    """Compare AL strategies by per-round metric."""
    apply_style()
    matplotlib, plt = _mpl()
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    colors = [PALETTE["blue"], PALETTE["orange"], PALETTE["green"],
                PALETTE["red"], PALETTE["purple"]]
    for (name, logs), col in zip(results.items(), colors):
        if not logs:
            continue
        if isinstance(logs[0], dict):
            vals = [d[metric] for d in logs]
        else:
            vals = [getattr(d, metric) for d in logs]
        rounds = np.arange(1, len(vals) + 1)
        ax.plot(rounds, vals, "o-", color=col, ms=4, label=name)
    ax.set_xlabel("Active learning round")
    ax.set_ylabel(metric.replace("_", " "))
    ax.set_yscale("log")
    if title:
        ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


# ============================================================================
# Training loss history
# ============================================================================

def plot_training_history(
    history: List[Dict],
    keys: Sequence[str] = ("loss_total", "loss_phi", "loss_n", "loss_p", "loss_bdy"),
    title: Optional[str] = None,
):
    apply_style()
    matplotlib, plt = _mpl()
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    epochs = [h["epoch"] for h in history]
    cycle = list(PALETTE.values())
    for i, k in enumerate(keys):
        if k not in history[0]:
            continue
        vals = [h[k] for h in history]
        ax.plot(epochs, np.maximum(vals, 1e-12), color=cycle[i],
                 label=k.replace("loss_", "").replace("_", " "))
    ax.set_yscale("log")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    if title:
        ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


__all__ = [
    "PALETTE",
    "apply_style",
    "plot_active_learning_convergence",
    "plot_device_state",
    "plot_doping_recovery",
    "plot_iv_with_uncertainty",
    "plot_reliability_diagram",
    "plot_training_history",
]
