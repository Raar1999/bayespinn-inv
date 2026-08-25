#!/usr/bin/env python
"""Freeze experimental results into LaTeX tables and a Markdown summary.

Consumes the JSON summaries produced by the experiment scripts and emits:

  - ``papers/results_tables.tex``   LaTeX tables ready to \\input{}
  - ``papers/results_summary.md``   Markdown version for the README

Usage::

    python scripts/freeze_results.py \\
        --benchmark   outputs/benchmarks/summary.json \\
        --inverse     outputs/inverse_sweep/aggregate.json \\
        --al          outputs/al_aggregated.json \\
        --calibration outputs/calibration/summary.json \\
        --defect      outputs/defect_study/metrics.json \\
        --out_tex     papers/results_tables.tex \\
        --out_md      papers/results_summary.md

Any of the inputs can be omitted; the corresponding section is skipped.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent
from typing import Optional

# =============================================================================
# LaTeX table fragments
# =============================================================================

def _benchmark_table(summary: dict) -> str:
    """Forward-model accuracy: per-family medians."""
    fams = sorted(summary.get("by_family", {}).keys())
    rows = []
    for f in fams:
        s = summary["by_family"][f]
        rows.append(
            f"{f} & {s['phi_rms_V']['median']:.3e} & "
            f"{s['log_n_rms']['median']:.3f} & "
            f"{s['log_p_rms']['median']:.3f} & "
            f"{s['I_relative']['median']:.3e} & "
            f"{s.get('n', 0)} \\\\"
        )
    body = "\n      ".join(rows)
    return dedent(rf"""
        \begin{{table}}[h]
          \centering
          \begin{{tabular}}{{lrrrrr}}
            \toprule
            Family & $\phi$ RMS (V) & $\log_{{10}}(n)$ RMS & $\log_{{10}}(p)$ RMS & $|\Delta I|/I$ & $n$ \\
            \midrule
            {body}
            \bottomrule
          \end{{tabular}}
          \caption{{Forward-model accuracy: PINN vs Scharfetter–Gummel on held-out profiles.
            Per-family medians across all biases.}}
          \label{{tab:forward_accuracy}}
        \end{{table}}""").strip()


def _inverse_table(agg: dict) -> str:
    """Inverse recovery: rel-L2 and coverage by (param, noise)."""
    rows = []
    for key in sorted(agg.keys()):
        s = agg[key]
        param, noise = key.split("/")
        n = noise.split("=")[1]
        rows.append(
            f"{param} & {n} & "
            f"{s['rel_L2_C_median']:.4f} & "
            f"({s['rel_L2_C_p10']:.4f}, {s['rel_L2_C_p90']:.4f}) & "
            f"{s['coverage_90_median']:.3f} \\\\"
        )
    body = "\n      ".join(rows)
    return dedent(rf"""
        \begin{{table}}[h]
          \centering
          \begin{{tabular}}{{llrlr}}
            \toprule
            Parameterization & Noise & Rel.\ $L_2(C)$ median & 10/90 quantile & Coverage \\
            \midrule
            {body}
            \bottomrule
          \end{{tabular}}
          \caption{{Inverse-design accuracy as a function of measurement noise.
            Median across targets; coverage is the empirical fraction of true
            anchor values inside the 90\% credible band.}}
          \label{{tab:inverse_recovery}}
        \end{{table}}""").strip()


def _calibration_table(summary: dict) -> str:
    """UQ method comparison: ECE / CRPS / NLL before and after temperature scaling."""
    rows = []
    for m in sorted(summary.keys()):
        s = summary[m]
        u = s["uncalibrated"]; c = s["temperature_scaled"]
        rows.append(
            f"{m.replace('_', r' ')} & {u['ECE']:.4f} & {c['ECE']:.4f} & "
            f"{c['CRPS']:.4e} & {c['NLL']:.4f} & {c['T']:.3f} \\\\"
        )
    body = "\n      ".join(rows)
    return dedent(rf"""
        \begin{{table}}[h]
          \centering
          \begin{{tabular}}{{lrrrrr}}
            \toprule
            Method & ECE (uncal) & ECE (cal) & CRPS & NLL & $T$ \\
            \midrule
            {body}
            \bottomrule
          \end{{tabular}}
          \caption{{Calibration metrics on held-out I-V predictions, before and
            after temperature scaling. CRPS and NLL are reported after
            recalibration; $T$ is the fitted temperature.}}
          \label{{tab:calibration}}
        \end{{table}}""").strip()


def _al_table(al: dict) -> str:
    """Final-round AL metric per strategy."""
    rows = []
    for s in sorted(al.keys()):
        info = al[s]
        rows.append(
            f"{s.replace('_', r' ')} & {info['n_seeds']} & "
            f"{len(info['rounds'])} & "
            f"{info['mean'][-1]:.4f} & "
            f"({info['p10'][-1]:.4f}, {info['p90'][-1]:.4f}) \\\\"
        )
    body = "\n      ".join(rows)
    return dedent(rf"""
        \begin{{table}}[h]
          \centering
          \begin{{tabular}}{{lrrrl}}
            \toprule
            Strategy & Seeds & Rounds & Final mean error & 10/90 quantile \\
            \midrule
            {body}
            \bottomrule
          \end{{tabular}}
          \caption{{Active-learning acquisition strategies: relative $L_2$
            doping error after the final round, aggregated across seeds.}}
          \label{{tab:active_learning}}
        \end{{table}}""").strip()


def _defect_block(metrics: dict) -> str:
    return dedent(rf"""
        \begin{{table}}[h]
          \centering
          \begin{{tabular}}{{lr}}
            \toprule
            Quantity & Value \\
            \midrule
            Relative $L_2$ doping error & {metrics['rel_L2_C']:.4f} \\
            Coverage of 90\% band       & {metrics['coverage_90']:.3f} \\
            True defect amplitude       & {metrics['true_amp']:+.2e} m$^{{-3}}$ \\
            Recovered defect amplitude  & {metrics['recovered_amp']:+.2e} m$^{{-3}}$ \\
            True defect center          & {metrics['true_center']*1e9:.0f} nm \\
            Recovered defect center     & {metrics['recovered_center']*1e9:.0f} nm \\
            Mean inverse-design loss    & {metrics['mean_loss']:.3e} \\
            Ensemble size $M$           & {metrics['M']} \\
            \bottomrule
          \end{{tabular}}
          \caption{{Defect-detection case study results (paper Figure 5).}}
          \label{{tab:defect}}
        \end{{table}}""").strip()


# =============================================================================
# Markdown helpers
# =============================================================================

def _benchmark_md(summary: dict) -> str:
    fams = sorted(summary.get("by_family", {}).keys())
    out = ["### Forward-model accuracy (SG vs PINN)\n",
           "| Family | phi RMS (V) | log10(n) RMS | log10(p) RMS | |dI|/I | n |",
           "|---|---:|---:|---:|---:|---:|"]
    for f in fams:
        s = summary["by_family"][f]
        out.append(
            f"| {f} | {s['phi_rms_V']['median']:.3e} | "
            f"{s['log_n_rms']['median']:.3f} | "
            f"{s['log_p_rms']['median']:.3f} | "
            f"{s['I_relative']['median']:.3e} | {s.get('n', 0)} |"
        )
    return "\n".join(out)


def _inverse_md(agg: dict) -> str:
    out = ["### Inverse-design accuracy\n",
           "| Parameterization | Noise | rel-L2(C) median | 10-90% | Coverage |",
           "|---|---:|---:|---|---:|"]
    for key in sorted(agg.keys()):
        s = agg[key]
        p, n = key.split("/"); n = n.split("=")[1]
        out.append(f"| {p} | {n} | {s['rel_L2_C_median']:.4f} | "
                   f"({s['rel_L2_C_p10']:.4f}, {s['rel_L2_C_p90']:.4f}) | "
                   f"{s['coverage_90_median']:.3f} |")
    return "\n".join(out)


def _calibration_md(summary: dict) -> str:
    out = ["### Calibration of UQ methods\n",
           "| Method | ECE (uncal) | ECE (cal) | CRPS | NLL | T |",
           "|---|---:|---:|---:|---:|---:|"]
    for m in sorted(summary.keys()):
        s = summary[m]
        u, c = s["uncalibrated"], s["temperature_scaled"]
        out.append(f"| {m} | {u['ECE']:.4f} | {c['ECE']:.4f} | "
                   f"{c['CRPS']:.4e} | {c['NLL']:.4f} | {c['T']:.3f} |")
    return "\n".join(out)


def _al_md(al: dict) -> str:
    out = ["### Active learning convergence\n",
           "| Strategy | Seeds | Rounds | Final mean error | 10-90% |",
           "|---|---:|---:|---:|---|"]
    for s in sorted(al.keys()):
        info = al[s]
        out.append(f"| {s} | {info['n_seeds']} | {len(info['rounds'])} | "
                   f"{info['mean'][-1]:.4f} | "
                   f"({info['p10'][-1]:.4f}, {info['p90'][-1]:.4f}) |")
    return "\n".join(out)


def _defect_md(metrics: dict) -> str:
    return dedent(f"""
        ### Defect detection case study

        - Relative $L_2$ doping error: **{metrics['rel_L2_C']:.4f}**
        - Coverage of 90% credible band: **{metrics['coverage_90']:.3f}**
        - Defect amplitude: true {metrics['true_amp']:+.2e}, recovered {metrics['recovered_amp']:+.2e} m^-3
        - Defect center: true {metrics['true_center']*1e9:.0f} nm, recovered {metrics['recovered_center']*1e9:.0f} nm
        - Ensemble size: $M = {metrics['M']}$
    """).strip()


# =============================================================================
# Main
# =============================================================================

def _maybe_load(path: Optional[str]) -> Optional[dict]:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        print(f"  warning: {p} not found, skipping")
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark")
    ap.add_argument("--inverse")
    ap.add_argument("--al")
    ap.add_argument("--calibration")
    ap.add_argument("--defect")
    ap.add_argument("--out_tex", default="papers/results_tables.tex")
    ap.add_argument("--out_md",  default="papers/results_summary.md")
    args = ap.parse_args()

    bench = _maybe_load(args.benchmark)
    inv   = _maybe_load(args.inverse)
    al    = _maybe_load(args.al)
    cal   = _maybe_load(args.calibration)
    def_  = _maybe_load(args.defect)

    out_tex = Path(args.out_tex); out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_md  = Path(args.out_md);  out_md.parent.mkdir(parents=True, exist_ok=True)

    tex_parts = ["% Auto-generated by scripts/freeze_results.py",
                  "% Do not edit by hand; re-run the script to refresh.",
                  ""]
    md_parts  = ["# BayesPINN-Inv: experimental results\n",
                  "*Auto-generated from JSON summaries. Re-run "
                  "`scripts/freeze_results.py` to refresh.*\n"]

    if bench:
        tex_parts.append(_benchmark_table(bench)); tex_parts.append("")
        md_parts.append(_benchmark_md(bench));     md_parts.append("")
    if inv:
        tex_parts.append(_inverse_table(inv));     tex_parts.append("")
        md_parts.append(_inverse_md(inv));         md_parts.append("")
    if cal:
        tex_parts.append(_calibration_table(cal)); tex_parts.append("")
        md_parts.append(_calibration_md(cal));     md_parts.append("")
    if al:
        tex_parts.append(_al_table(al));           tex_parts.append("")
        md_parts.append(_al_md(al));               md_parts.append("")
    if def_:
        tex_parts.append(_defect_block(def_));     tex_parts.append("")
        md_parts.append(_defect_md(def_));         md_parts.append("")

    with open(out_tex, "w", encoding="utf-8") as f:
        f.write("\n".join(tex_parts))
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_parts))
    print(f"  -> {out_tex}")
    print(f"  -> {out_md}")


if __name__ == "__main__":
    main()
