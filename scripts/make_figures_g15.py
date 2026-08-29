#!/usr/bin/env python
"""The paper's first three figures, from artefacts that already exist.

``docs/PAPER_AUDIT_g15.md`` §5 names six figures the paper needs and creates
none. The close-out ruling of 2026-08-29 §6 orders three of them, in the order
effect-over-effort puts them::

    F4  the headline pair      -- two devices, two I-V curves, one noise band
    F2  the observation-set result -- rank against window width, spacing flat
    F6  gradient fidelity      -- cosine against direction, cutoff marked

**No solve is performed and no number is computed here.** Every value plotted is
read from a committed artefact; the only arithmetic is the +-2% band in F4,
which is the noise level the study is conducted at applied to a stored curve,
and the log10 of stored magnitudes. A figure script that recomputes its own
inputs is a second implementation of the study, and a disagreement between it
and the tables would be undiagnosable.

Usage::

    python scripts/make_figures_g15.py [--out outputs/figures_g15]

Outputs ``F2.png``, ``F4.png``, ``F6.png``, each also as ``.pdf``, plus
``manifest.json`` recording the digest of every input artefact read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.inverse.charts import ChartJ
from bayespinn_inv.utils.provenance import RunManifest

REPO = Path(__file__).resolve().parents[1]

#: Every artefact this script reads. Digested into the manifest so a figure can
#: be traced to the bytes it was drawn from.
INPUTS = {
    "F4": "outputs/g8/chart_j.json",
    "F4_refine": "outputs/g9/junction_refine.json",
    "F2": "outputs/g9/rank_obs.json",
    "F6": "outputs/gradient_fidelity/gradient_fidelity.json",
}

#: The study's noise level. Stated in every artefact read here; asserted against
#: them below rather than trusted, because it sets F4's band.
NOISE_REL = 0.02

# Colour-blind-safe pair, and every series is also distinguished by line style
# and marker so the figures survive greyscale printing.
C_A, C_B = "#0072B2", "#D55E00"
C_GREY = "#555555"


def _digest(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def _load(rel: str) -> Any:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def _style() -> None:
    plt.rcParams.update({
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
        "savefig.bbox": "tight",
    })


def _save(fig: plt.Figure, out: Path, name: str) -> Dict[str, str]:
    """Write PNG and PDF, both bit-reproducible across runs.

    The PNGs were already identical on re-run; the PDFs were not, because
    matplotlib stamps a ``CreationDate`` into the PDF info dictionary and it is
    the only byte that moves. Setting it to ``None`` drops the key. Without
    this, every regeneration of a figure produces a diff that says nothing,
    which is how a real change stops being visible.
    """
    paths = {}
    for ext in ("png", "pdf"):
        p = out / f"{name}.{ext}"
        meta = {"CreationDate": None} if ext == "pdf" else None
        fig.savefig(p, metadata=meta)
        paths[f"{name}.{ext}"] = str(p.relative_to(REPO)).replace("\\", "/")
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# F4 -- the headline pair
# ---------------------------------------------------------------------------

def figure_f4(out: Path) -> Dict[str, Any]:
    """Two devices 423 nm apart in junction depth, indistinguishable in I-V.

    Both profiles and both current vectors are stored in
    ``outputs/g8/chart_j.json``'s witness record. The junction positions are
    read from ``outputs/g9/junction_refine.json``'s verdict, and re-derived here
    through ``ChartJ.junction_position`` as a cross-check -- two routes to the
    same number, because a figure asserting "694 nm" should not be the only
    place that number is computed.
    """
    cj = _load(INPUTS["F4"])["native_witness"]
    ref = _load(INPUTS["F4_refine"])["verdict"]["widest_junction_pair"]

    assert cj["config"]["noise_rel"] == NOISE_REL, "F4: noise level moved"
    idx = ref["pair_index"]
    w = cj["witnesses"][idx]
    assert cj["witness_pair_indices"][idx] == [299, 612], "F4: pair moved"
    assert abs(w["observational_distance"]
               - ref["distance_at_301_default"]) < 1e-12, "F4: distance moved"

    biases = np.asarray(cj["config"]["biases"], dtype=float)
    lo_si, hi_si = cj["config"]["domain_si"]
    n_grid = 301                      # the grid the stored distance was taken on
    x_si = np.linspace(lo_si, hi_si, n_grid)

    theta_a = np.asarray(w["profile_a_log10"], dtype=float)
    theta_b = np.asarray(w["profile_b_log10"], dtype=float)
    chart = ChartJ(d=theta_a.shape[0], x_si=x_si)

    xj_a = chart.junction_position(float(theta_a[0]))
    xj_b = chart.junction_position(float(theta_b[0]))
    # Cross-check against the stored verdict: same junctions, two routes.
    assert abs(xj_a - ref["junction_x_si_a"]) < 1e-12, "F4: x_j(a) disagrees"
    assert abs(xj_b - ref["junction_x_si_b"]) < 1e-12, "F4: x_j(b) disagrees"

    prof_a = chart.reconstruct(theta_a)
    prof_b = chart.reconstruct(theta_b)
    i_a = np.asarray(w["current_a"], dtype=float)
    i_b = np.asarray(w["current_b"], dtype=float)

    x_nm = x_si * 1e9
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(5.4, 5.6), gridspec_kw={"height_ratios": [1.0, 1.15]})

    # -- top: the two doping profiles, which are visibly different -----------
    ax1.plot(x_nm, np.sign(prof_a) * np.log10(np.abs(prof_a)),
             color=C_A, lw=1.6, ls="-", label="device A")
    ax1.plot(x_nm, np.sign(prof_b) * np.log10(np.abs(prof_b)),
             color=C_B, lw=1.6, ls="--", label="device B")
    ax1.axhline(0.0, color=C_GREY, lw=0.6, ls=":")
    for xj, c in ((xj_a, C_A), (xj_b, C_B)):
        ax1.axvline(xj * 1e9, color=c, lw=1.0, ls=":", alpha=0.9)
    ax1.annotate(f"$x_j$ = {xj_b * 1e9:.0f} nm", xy=(xj_b * 1e9, 0),
                 xytext=(xj_b * 1e9 - 8, -14), color=C_B, ha="right", fontsize=8)
    ax1.annotate(f"$x_j$ = {xj_a * 1e9:.0f} nm", xy=(xj_a * 1e9, 0),
                 xytext=(xj_a * 1e9 + 8, -14), color=C_A, ha="left", fontsize=8)
    ax1.annotate("", xy=(xj_a * 1e9, -19), xytext=(xj_b * 1e9, -19),
                 arrowprops=dict(arrowstyle="<->", color=C_GREY, lw=0.9))
    ax1.text(0.5 * (xj_a + xj_b) * 1e9, -18.2,
             f"{(xj_a - xj_b) * 1e9:.0f} nm apart", ha="center", va="bottom",
             fontsize=8, color=C_GREY)
    ax1.set_xlabel("position $x$ (nm)")
    ax1.set_ylabel(r"signed $\log_{10}|C|$   ($C$ in m$^{-3}$)")
    ax1.set_title("Two devices, chart J at $d$=16", loc="left")
    ax1.legend(loc="upper left", frameon=False)

    # -- bottom: their I-V curves, inside the band ---------------------------
    ax2.semilogy(biases, i_a, color=C_A, lw=1.6, ls="-", marker="o", ms=3.2,
                 label="device A")
    ax2.semilogy(biases, i_b, color=C_B, lw=1.3, ls="--", marker="s", ms=3.0,
                 mfc="none", label="device B")
    ax2.fill_between(biases, i_a * (1 - NOISE_REL), i_a * (1 + NOISE_REL),
                     color=C_A, alpha=0.22, lw=0,
                     label=f"$\\pm${NOISE_REL:.0%} band about A "
                           "(thinner than the line here — see inset)")
    ax2.set_xlabel("terminal bias $V$ (V)")
    ax2.set_ylabel("terminal current (A m$^{-2}$, SI)")
    ax2.legend(loc="upper left", frameon=False)

    # The residual, as an inset: the whole claim in one axis.
    resid = np.abs(i_b - i_a) / i_a
    axi = ax2.inset_axes((0.56, 0.13, 0.41, 0.36))
    axi.plot(biases, 100 * resid, color=C_GREY, lw=1.2, marker="o", ms=2.4)
    axi.axhline(100 * NOISE_REL, color="k", lw=1.0, ls="--")
    axi.text(biases[0], 100 * NOISE_REL * 1.08, f"{NOISE_REL:.0%} noise",
             fontsize=6.5, va="bottom")
    axi.set_ylim(0, 100 * NOISE_REL * 1.45)
    axi.set_xlabel("$V$ (V)", fontsize=6.5, labelpad=1)
    axi.set_ylabel("|B$-$A|/A  (%)", fontsize=6.5, labelpad=1)
    axi.tick_params(labelsize=6)

    fig.suptitle(
        "The junction is not identifiable from terminal I–V\n"
        f"observational distance {w['observational_distance']:.4f}"
        f" < floor {cj['floors']['distinguishability']:.2f}",
        fontsize=9.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    return {
        "paths": _save(fig, out, "F4"),
        "junction_a_nm": xj_a * 1e9,
        "junction_b_nm": xj_b * 1e9,
        "separation_nm": (xj_a - xj_b) * 1e9,
        "observational_distance": w["observational_distance"],
        "floor": cj["floors"]["distinguishability"],
        "max_relative_iv_difference_pct": float(100 * resid.max()),
    }


# ---------------------------------------------------------------------------
# F2 -- the observation set is a curve, and the control is flat
# ---------------------------------------------------------------------------

def figure_f2(out: Path) -> Dict[str, Any]:
    """Rank against window width, with the spacing control beside it.

    Both panels share a y-axis on purpose: the result is that one curve rises
    and the other does not, and putting them on separate scales would let a
    reader miss it.
    """
    d = _load(INPUTS["F2"])
    widths = np.asarray(d["axes"]["width"]["widths_V"], dtype=float)
    alphas = np.asarray(d["axes"]["spacing"]["alphas"], dtype=float)
    centre = d["axes"]["width"]["centre_V"]

    devices = [("g8_operating_point", "device 1 (g8 operating point)", C_A,
                "-", "o"),
               ("device_p50", "device 2 (prior median)", C_B, "--", "s")]

    fig, (axw, axs) = plt.subplots(1, 2, figsize=(6.6, 3.0), sharey=True)

    rows: Dict[str, Any] = {}
    for key, label, colour, ls, marker in devices:
        dev = d["devices"][key]
        rw = [r["rank_at_operational_cutoff"] for r in dev["width_curve"]]
        rs = [r["rank_at_operational_cutoff"] for r in dev["spacing_curve"]]
        axw.plot(widths, rw, color=colour, ls=ls, marker=marker, ms=4.2,
                 lw=1.6, mfc="none" if marker == "s" else colour, label=label)
        axs.plot(alphas, rs, color=colour, ls=ls, marker=marker, ms=4.2,
                 lw=1.6, mfc="none" if marker == "s" else colour, label=label)
        rows[key] = {"width_curve_rank": rw, "spacing_curve_rank": rs,
                     "summary": dev["summary"]}

    axw.set_xlabel(f"bias-window width (V), centred at {centre} V")
    axw.set_ylabel("identifiable directions\n(count above the 2% cutoff)")
    axw.set_title("widening the window", loc="left")
    axw.legend(loc="upper left", frameon=False)

    axs.set_xlabel(r"spacing $\alpha$  (0 = linear, 1 = geometric)")
    axs.set_title("re-spacing it — the control", loc="left")
    axs.text(0.5, 0.12, "flat: same window, same count",
             transform=axs.transAxes, ha="center", fontsize=8, color=C_GREY)

    for ax in (axw, axs):
        ax.set_ylim(0, 5.4)
        ax.set_yticks([0, 1, 2, 3, 4, 5])
        ax.grid(axis="y", lw=0.4, alpha=0.35)

    # CHART LABEL. Both curves are ``cell_spectrum(sg, G16, m16, b, cfg)`` in
    # ``scripts/run_g9.py::phase_rank_obs`` -- chart **G** at d=16, with the
    # device lifted from chart G at d=4 by ``np.interp`` over the anchors.
    # ``docs/CLAIM_EVIDENCE_MATRIX.md`` row I5 agrees. The paper said chart L
    # at three sites; that is ``COR-2`` in ``papers/CORRIGENDA_g6.md``, and this
    # figure is labelled from the code rather than from the paper.
    fig.suptitle("The rank is a property of the measurement, not of the device"
                 "   ·   chart G at $d$=16, 2% noise, 16 biases",
                 fontsize=9.5, y=1.03)
    fig.tight_layout()

    return {"paths": _save(fig, out, "F2"), "devices": rows,
            "widths_V": widths.tolist(), "alphas": alphas.tolist(),
            "chart": "G", "d": 16,
            "chart_label_source": (
                "scripts/run_g9.py::phase_rank_obs, which calls cell_spectrum "
                "with ChartG(16). NOT from the artefact: rank_obs.json's "
                "width_curve and spacing_curve rows drop the chart and "
                "chart_label fields cell_spectrum returns, so the artefact "
                "does not carry the chart its own numbers were taken in. That "
                "is the root cause of COR-2 and is reported, not fixed here")}


# ---------------------------------------------------------------------------
# F6 -- gradient fidelity against the identifiable subspace
# ---------------------------------------------------------------------------

def figure_f6(out: Path) -> Dict[str, Any]:
    """Cosine agreement per direction, with each device's own cutoff drawn.

    Small multiples rather than one panel: ``identifiable_rank`` differs between
    devices, so a single averaged axis would need one cutoff line standing for
    four different ones. Four panels show every point and every cutoff.
    """
    d = _load(INPUTS["F6"])
    budgets = [str(b) for b in (d["config"]["training_budgets"][0],
                                d["config"]["training_budgets"][-1])]
    dev_names = list(d["by_budget"][budgets[0]]["devices"].keys())

    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.6), sharex=True, sharey=True)
    rows: Dict[str, Any] = {}

    for ax, name in zip(axes.ravel(), dev_names):
        # One cutoff line per panel, so the rank must not depend on the budget.
        # It must not: it is a property of the reference solver's Jacobian and
        # the surrogate never enters it. Asserted rather than assumed, because
        # drawing one line for two different cutoffs would be silent.
        ranks = {b: int(d["by_budget"][b]["devices"][name]["identifiable_rank"])
                 for b in d["by_budget"]}
        assert len(set(ranks.values())) == 1, (
            f"F6: {name} identifiable_rank differs across budgets: {ranks}")
        rank = int(ranks[budgets[0]])

        for budget, colour, marker, ls in ((budgets[0], C_GREY, "^", ":"),
                                           (budgets[-1], C_A, "o", "-")):
            dev = d["by_budget"][budget]["devices"][name]
            k = [x["direction"] for x in dev["directions"]]
            cos = [x["cosine"] for x in dev["directions"]]
            ax.plot(k, cos, color=colour, ls=ls, marker=marker, ms=3.4, lw=1.2,
                    mfc="none", label=f"{int(budget):,} epochs")
            rows.setdefault(name, {})[budget] = {
                "identifiable_rank": rank,
                "mean_cosine_inside": dev["mean_cosine_inside_identifiable"],
                "mean_cosine_outside": dev["mean_cosine_outside_identifiable"],
                "median_abs_symlog_value_error":
                    dev["median_abs_symlog_value_error"],
            }
        ax.axvline(rank - 0.5, color="k", lw=1.0, ls="--")
        ax.axhline(0.0, color=C_GREY, lw=0.6)
        ax.axvspan(-0.6, rank - 0.5, color=C_A, alpha=0.07, lw=0)
        ax.set_title(f"{name}   (identifiable rank {rank})", loc="left",
                     fontsize=8.5)
        ax.set_ylim(-1.15, 1.15)
        ax.set_xticks([0, 4, 8, 12, 15])
        ax.grid(axis="y", lw=0.4, alpha=0.3)

    axes[0, 0].legend(loc="lower right", frameon=False, fontsize=7.5)
    axes[0, 0].text(0.03, 0.04, "identifiable", transform=axes[0, 0].transAxes,
                    fontsize=7.5, color=C_A, ha="left")
    for ax in axes[1, :]:
        ax.set_xlabel("singular direction index $k$")
    for ax in axes[:, 0]:
        ax.set_ylabel("cosine, reference vs\nsurrogate derivative")

    v = d["verdict"]
    fig.suptitle(
        "A surrogate's gradients agree with the solver only inside the "
        "identifiable subspace\n"
        f"mean cosine inside {v['mean_cosine_inside']:+.3f},  "
        f"outside {v['mean_cosine_outside']:+.3f}  "
        f"(outside is flat across a {int(budgets[-1]) // int(budgets[0])}× "
        "budget, so it is not undertraining)", fontsize=9, y=1.045)
    fig.tight_layout()

    return {"paths": _save(fig, out, "F6"), "budgets_plotted": budgets,
            "devices": rows, "verdict": v}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/figures_g15")
    args = ap.parse_args()

    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    _style()

    manifest = RunManifest.create(
        experiment="figures_g15",
        config={"inputs": INPUTS, "noise_rel": NOISE_REL},
        notes="F4, F2 and F6 of docs/PAPER_AUDIT_g15.md section 5. Reads "
              "committed artefacts and performs no solve.")

    results = {"F4": figure_f4(out), "F2": figure_f2(out),
               "F6": figure_f6(out)}
    manifest.results = results
    manifest.config["input_sha256"] = {v: _digest(v) for v in INPUTS.values()}
    manifest.artifacts = {k: v for r in results.values()
                          for k, v in r["paths"].items()}
    manifest.write(out)          # RunManifest.write takes the directory

    for name, r in results.items():
        print(f"  {name}: " + ", ".join(sorted(r["paths"])))
    print(f"\nmanifest: {(out / 'manifest.json').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
