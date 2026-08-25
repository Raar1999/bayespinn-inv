#!/usr/bin/env python
"""
Quantitative results for BayesPINN-Inv, with auditable methodology.

This replaces the previous ``run_results.py``. That version produced the
project's headline table but had four methodological defects, all recorded in
``docs/AUDIT_MASTER.md`` (SCI-01..SCI-07) and all fixed here:

* **SCI-01** the published calibration table put "raw" and "recalibrated"
  columns side by side as a before/after, but they were computed on two
  *different* test sets. Here every calibration number is pre/post on one set.
* **SCI-02** "H4 Active-learning gain" contained no active learning -- it
  compared three fixed bias subsets. Here H4 is a real sequential experiment:
  an uncertainty-driven acquisition against a random baseline, repeated over
  seeds, with the fixed-subset comparison kept separately and named honestly.
* **SCI-03** coverage was reported as percentages from n = 5. Every statistic
  here reports ``n`` and a bootstrap confidence interval.
* **SCI-06** "held-out profiles" were interpolation inside the training range.
  Here there are three distinct test sets: interpolation, **extrapolation**
  (outside the training range -- never previously measured), and a
  **different profile family**.

Two further changes follow from the solver audit:

* Labels are filtered by the oracle's own trust flag. A bias point whose SG
  current sits below the solver's numerical noise floor is not a measurement,
  and training or scoring on it fits noise (AUDIT_MASTER BUG-04). The number
  of dropped points is reported, never silently discarded.
* The current dynamic range is measured and reported rather than asserted.

Usage
-----
    PYTHONPATH=src python scripts/run_results.py [--out DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SymlogTransform,
    train_surrogate,
)
from bayespinn_inv.utils.provenance import RunManifest

DOMAIN = (0.0, 1e-6)
N_ANCHOR = 16
BIAS_MAX = 0.6
N_BIAS = 13
M_ENSEMBLE = 5
SEED = 0

# Doping ranges. The training band is deliberately narrower than the test
# bands so that extrapolation can actually be measured.
TRAIN_LO, TRAIN_HI = 1.0e21, 2.0e22
EXTRAP_LO, EXTRAP_HI = 2.0e20, 8.0e22          # straddles the training band


# ===========================================================================
# helpers
# ===========================================================================

def bootstrap_ci(values: Sequence[float], stat=np.median, n_boot: int = 2000,
                 alpha: float = 0.05, seed: int = 0):
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    boots = stat(v[idx], axis=1)
    return dict(point=float(stat(v)), lo=float(np.quantile(boots, alpha / 2)),
                hi=float(np.quantile(boots, 1 - alpha / 2)), n=int(v.size))


def binomial_ci(k: int, n: int, alpha: float = 0.05):
    """Wilson score interval -- honest for the small n these coverages use."""
    if n == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    from math import sqrt
    z = 1.959963984540054
    phat = k / n
    d = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / d
    half = z * sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / d
    return dict(point=float(phat), lo=float(max(0.0, centre - half)),
                hi=float(min(1.0, centre + half)), n=int(n))


def step_profile(xa, level, xj=None):
    xj = xj if xj is not None else 0.5 * DOMAIN[1]
    return np.where(xa < xj, -level, level).astype(np.float64)


def graded_profile(xa, level, width=1.5e-7):
    xj = 0.5 * DOMAIN[1]
    return (level * np.tanh((xa - xj) / width)).astype(np.float64)


def oracle_iv(sg, C, biases):
    """Return (currents, trust flags). Continuation warm-start along bias."""
    prev, I, trust = None, [], []
    for V in biases:
        st = sg.solve(C, float(V), initial_state=prev)
        prev = st
        I.append(st.terminal_current)
        trust.append(bool(st.converged and st.current_is_trustworthy()))
    return np.asarray(I), np.asarray(trust)


# ===========================================================================
# main
# ===========================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/results")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--epochs", type=int, default=2500)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(np.float64(DOMAIN[1] - DOMAIN[0])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 301), scaling, SILICON, SGConfig())
    VT = scaling.V_T
    symlog = SymlogTransform(I0=1e-6)
    biases = np.linspace(0.0, BIAS_MAX, N_BIAS)
    xa = np.linspace(DOMAIN[0], DOMAIN[1], N_ANCHOR)

    n_train = 5 if args.quick else 13
    epochs = 400 if args.quick else args.epochs
    M = 3 if args.quick else M_ENSEMBLE

    cfg = dict(domain_si=list(DOMAIN), n_anchor=N_ANCHOR, n_bias=N_BIAS,
               bias_max=BIAS_MAX, ensemble_M=M, epochs=epochs,
               train_band=[TRAIN_LO, TRAIN_HI],
               extrap_band=[EXTRAP_LO, EXTRAP_HI], seed=SEED)
    man = RunManifest.create("results", config=cfg, seed=SEED)
    results: Dict[str, object] = {"methodology": {
        "label_filter": "SG label used only where solver converged AND "
                        "|I| > 10 * current_noise_floor",
        "splits": "train / calibration-val / test-interp / test-extrap / "
                  "test-family, all disjoint in doping level",
        "uncertainty": "bootstrap 95% CI for continuous stats, Wilson score "
                       "interval for coverages; n reported everywhere",
    }}

    # ---------------------------------------------------------------- splits
    train_levels = np.geomspace(TRAIN_LO, TRAIN_HI, n_train)
    # interpolation test: geometric midpoints between adjacent train levels
    interp_levels = np.sqrt(train_levels[:-1] * train_levels[1:])[::2]
    # extrapolation test: strictly outside the training band
    extrap_levels = np.concatenate([
        np.geomspace(EXTRAP_LO, TRAIN_LO * 0.7, 3),
        np.geomspace(TRAIN_HI * 1.4, EXTRAP_HI, 3),
    ])
    # calibration split: disjoint from both, inside the band
    val_levels = np.geomspace(TRAIN_LO * 1.15, TRAIN_HI * 0.87, 5)
    val_levels = np.array([v for v in val_levels
                           if np.min(np.abs(np.log10(v / train_levels))) > 0.02])
    family_levels = np.geomspace(TRAIN_LO * 1.3, TRAIN_HI * 0.8, 5)

    for nm, lv in [("train", train_levels), ("val", val_levels),
                   ("test_interp", interp_levels),
                   ("test_extrap", extrap_levels),
                   ("test_family_graded", family_levels)]:
        print(f"{nm:20s} n={len(lv):2d}  "
              f"log10 range [{np.log10(lv.min()):.2f}, {np.log10(lv.max()):.2f}]")
    # assert disjointness in log-space
    for a, b in [("val", val_levels), ("test_interp", interp_levels),
                 ("test_extrap", extrap_levels)]:
        gap = np.min(np.abs(np.log10(b[:, None] / train_levels[None, :])))
        assert gap > 1e-3, f"{a} overlaps the training levels (gap {gap})"
    results["splits"] = {
        "train_levels": train_levels.tolist(),
        "calibration_val_levels": val_levels.tolist(),
        "test_interp_levels": interp_levels.tolist(),
        "test_extrap_levels": extrap_levels.tolist(),
        "test_family_graded_levels": family_levels.tolist(),
        "note": "disjoint by construction; extrapolation levels lie outside "
                "the training band on both sides",
    }

    # ------------------------------------------------------- training labels
    print("\nGenerating SG training labels ...")
    t0 = time.time()
    X, Y, n_drop, n_total = [], [], 0, 0
    for lv in train_levels:
        C = step_profile(xa, lv)
        latent = scaling.doping_to_net_input(C)
        I, trust = oracle_iv(sg, C, biases)
        for bi, V in enumerate(biases):
            n_total += 1
            if not trust[bi]:
                n_drop += 1
                continue
            X.append(np.concatenate([latent, [V / VT]]).astype(np.float32))
            Y.append(np.float32(symlog.forward(I[bi])))
    X = np.asarray(X, dtype=np.float32)
    Y = np.asarray(Y, dtype=np.float32)
    print(f"  {X.shape[0]} usable labels in {time.time() - t0:.1f}s; "
          f"dropped {n_drop}/{n_total} below the oracle noise floor")
    results["label_integrity"] = {
        "n_candidate_labels": n_total, "n_dropped_untrustworthy": n_drop,
        "n_used": int(X.shape[0]),
        "why": "SG terminal current below its own numerical noise floor near "
               "equilibrium; fitting it would be fitting noise",
    }

    # measured dynamic range (replaces the asserted '13 orders of magnitude')
    Ilin = np.abs(symlog.inverse(Y))
    Ipos = Ilin[Ilin > 0]
    decades = float(np.log10(Ipos.max() / Ipos.min()))
    print(f"  measured current dynamic range in the training labels: "
          f"{decades:.2f} decades "
          f"({Ipos.min():.3e} to {Ipos.max():.3e} A/m^2)")
    results["current_dynamic_range_decades"] = decades
    results["current_range_A_per_m2"] = [float(Ipos.min()), float(Ipos.max())]

    # -------------------------------------------------------------- ensemble
    norm = Normalizer.fit(X)
    print(f"\nTraining {M}-member ensemble ({epochs} epochs each) ...")
    members = []
    for m in range(M):
        net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128,
                                            n_layers=3, seed=m))
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))       # bootstrap for diversity
        train_surrogate(net, X[idx], Y[idx], norm, epochs=epochs, lr=2e-3)
        members.append(net)
    ens = SurrogateEnsemble(members, norm, symlog)
    print(f"  M={ens.M}, {members[0].num_parameters():,} params/member")
    results["model"] = {"M": ens.M,
                        "params_per_member": members[0].num_parameters()}

    # =====================================================================
    # H1  forward accuracy on three genuinely distinct test sets
    # =====================================================================
    print("\n[H1] Forward accuracy")

    def forward_errors(levels, family="step"):
        rel, per_bias = [], []
        for lv in levels:
            C = (step_profile(xa, lv) if family == "step"
                 else graded_profile(xa, lv))
            I, trust = oracle_iv(sg, C, biases)
            pred = ens.predict(scaling.doping_to_net_input(C), biases / VT)
            for bi in range(len(biases)):
                if not trust[bi]:
                    continue
                e = abs(pred.mean_current[bi] - I[bi]) / abs(I[bi])
                rel.append(e)
                per_bias.append((float(biases[bi]), float(e)))
        return np.asarray(rel), per_bias

    h1 = {}
    for name, levels, fam in [
        ("interpolation", interp_levels, "step"),
        ("extrapolation", extrap_levels, "step"),
        ("family_transfer_graded", family_levels, "graded"),
    ]:
        rel, per_bias = forward_errors(levels, fam)
        h1[name] = {
            "median_rel_err": bootstrap_ci(rel, np.median, seed=SEED),
            "p90_rel_err": float(np.quantile(rel, 0.9)) if rel.size else None,
            "max_rel_err": float(rel.max()) if rel.size else None,
            "n": int(rel.size),
            "n_profiles": len(levels),
        }
        c = h1[name]["median_rel_err"]
        print(f"  {name:24s} median {c['point']:.2%} "
              f"[{c['lo']:.2%}, {c['hi']:.2%}]  p90 {h1[name]['p90_rel_err']:.2%}"
              f"  max {h1[name]['max_rel_err']:.2%}  (n={rel.size})")
    results["H1_forward_accuracy"] = h1

    # =====================================================================
    # H2  inverse recovery of a single doping level vs measurement noise
    # =====================================================================
    print("\n[H2] Inverse recovery vs measurement noise "
          "(single-level, well-posed sub-problem)")
    half = N_ANCHOR // 2

    def encode_level(logL):
        C = torch.cat([-(10.0 ** logL).repeat(half),
                       (10.0 ** logL).repeat(N_ANCHOR - half)])
        return scaling.doping_to_net_input(C)

    bs_all = torch.tensor(biases / VT, dtype=torch.float32)

    def recover(target_symlog, member, mask):
        logL = torch.tensor(21.5, requires_grad=True)
        opt = torch.optim.Adam([logL], lr=0.05)
        bs = bs_all[mask]
        tgt = target_symlog[mask]
        for _ in range(400):
            opt.zero_grad()
            lat = encode_level(logL)
            feats = torch.stack([torch.cat([lat, bs[i].reshape(1)])
                                 for i in range(len(bs))])
            pred = member((feats - norm.mean) / norm.std).reshape(-1)
            torch.nn.functional.mse_loss(pred, tgt).backward()
            opt.step()
            logL.data.clamp_(np.log10(EXTRAP_LO), np.log10(EXTRAP_HI))
        return float(logL)

    truth_levels = interp_levels if args.quick else np.geomspace(
        TRAIN_LO * 1.5, TRAIN_HI * 0.7, 8)
    noise_levels = [0.0, 0.02, 0.05, 0.10]
    n_noise_seeds = 1 if args.quick else 5
    h2 = {}
    for noise in noise_levels:
        errs, covered = [], []
        for Ltrue in truth_levels:
            C = step_profile(xa, Ltrue)
            I, trust = oracle_iv(sg, C, biases)
            mask = torch.tensor(trust)
            for s in range(n_noise_seeds):
                # independent RNG per (level, noise, seed): the old code reused
                # one seed across noise levels, making the rows perfectly
                # correlated (SCI-03)
                rng = np.random.default_rng(
                    abs(hash((round(float(Ltrue)), noise, s))) % (2 ** 32))
                In = I * (1.0 + noise * rng.standard_normal(len(biases)))
                tgt = torch.tensor(symlog.forward(In), dtype=torch.float32)
                rec = np.array([recover(tgt, m, mask) for m in members])
                err = abs(rec.mean() - np.log10(Ltrue))
                errs.append(err)
                covered.append(bool(err <= rec.std() + 1e-12))
        h2[f"noise_{noise}"] = {
            "median_abs_err_decades": bootstrap_ci(errs, np.median, seed=SEED),
            "mean_abs_err_decades": bootstrap_ci(errs, np.mean, seed=SEED),
            "coverage_1sigma": binomial_ci(int(np.sum(covered)), len(covered)),
        }
        d = h2[f"noise_{noise}"]
        print(f"  noise {noise:4.0%}: median err "
              f"{d['median_abs_err_decades']['point']:.4f} decades "
              f"[{d['median_abs_err_decades']['lo']:.4f}, "
              f"{d['median_abs_err_decades']['hi']:.4f}]   "
              f"1-sigma coverage {d['coverage_1sigma']['point']:.0%} "
              f"[{d['coverage_1sigma']['lo']:.0%}, {d['coverage_1sigma']['hi']:.0%}]"
              f" (n={d['coverage_1sigma']['n']})")
    results["H2_inverse_vs_noise"] = h2

    # =====================================================================
    # H3  calibration -- pre and post on the SAME test set (SCI-01)
    # =====================================================================
    print("\n[H3] UQ calibration (pre and post measured on one test set)")

    def z_scores(levels, family="step"):
        z = []
        for lv in levels:
            C = (step_profile(xa, lv) if family == "step"
                 else graded_profile(xa, lv))
            I, trust = oracle_iv(sg, C, biases)
            pred = ens.predict(scaling.doping_to_net_input(C), biases / VT)
            for bi in range(len(biases)):
                if not trust[bi] or pred.std_symlog[bi] <= 1e-12:
                    continue
                z.append((symlog.forward(I[bi]) - pred.mean_symlog[bi])
                         / pred.std_symlog[bi])
        return np.asarray(z)

    from math import erf, sqrt

    def nominal(zz):
        return erf(zz / sqrt(2.0))

    z_val = z_scores(val_levels)
    z_test = z_scores(np.concatenate([interp_levels, extrap_levels]))
    # variance-inflation factor fitted on the validation split only
    T = float(np.sqrt(np.mean(z_val ** 2)))       # NLL-optimal scalar
    zs = [1.0, 1.64, 2.0]
    h3 = {"temperature": T, "n_val": int(z_val.size), "n_test": int(z_test.size),
          "fit": "T = RMS(z) on the calibration split; NLL-optimal variance "
                 "inflation. Evaluated pre and post on the identical test set."}
    for zz in zs:
        pre = binomial_ci(int(np.sum(np.abs(z_test) <= zz)), z_test.size)
        post = binomial_ci(int(np.sum(np.abs(z_test) <= zz * T)), z_test.size)
        h3[f"z_{zz}"] = {"pre": pre, "post": post, "nominal": float(nominal(zz))}
        print(f"  +/-{zz}sigma: pre {pre['point']:.0%} "
              f"[{pre['lo']:.0%},{pre['hi']:.0%}] -> post {post['point']:.0%} "
              f"[{post['lo']:.0%},{post['hi']:.0%}]  nominal {nominal(zz):.0%}"
              f"  (n={pre['n']})")
    print(f"  variance-inflation T = {T:.3f} (fit on n={z_val.size} "
          f"validation residuals)")
    results["H3_calibration"] = h3

    # =====================================================================
    # H4  bias informativeness + a REAL active-learning comparison (SCI-02)
    # =====================================================================
    print("\n[H4a] Fixed bias-subset ablation (NOT active learning)")
    subsets = {"low_3": [0, 1, 2], "mid_3": [5, 6, 7],
               "high_3": [10, 11, 12], "all_13": list(range(N_BIAS))}
    h4a = {}
    for name, idx in subsets.items():
        errs = []
        for Ltrue in truth_levels:
            C = step_profile(xa, Ltrue)
            I, trust = oracle_iv(sg, C, biases)
            mask = torch.zeros(N_BIAS, dtype=torch.bool)
            for i in idx:
                mask[i] = bool(trust[i])
            if int(mask.sum()) == 0:
                continue
            tgt = torch.tensor(symlog.forward(I), dtype=torch.float32)
            rec = np.array([recover(tgt, m, mask) for m in members])
            errs.append(abs(rec.mean() - np.log10(Ltrue)))
        h4a[name] = {"n_biases_requested": len(idx),
                     "median_abs_err_decades": bootstrap_ci(errs, np.median,
                                                            seed=SEED)}
        print(f"  {name:8s} ({len(idx):2d} biases): median err "
              f"{h4a[name]['median_abs_err_decades']['point']:.4f} decades "
              f"(n={h4a[name]['median_abs_err_decades']['n']})")
    results["H4a_bias_subset_ablation"] = h4a

    print("\n[H4b] Active learning: uncertainty-driven acquisition vs random")
    n_al_seeds = 2 if args.quick else 8
    budgets = [2, 3, 4, 6]
    h4b: Dict[str, Dict] = {}
    for strategy in ("random", "max_std"):
        per_budget: Dict[int, List[float]] = {b: [] for b in budgets}
        for seed in range(n_al_seeds):
            rng = np.random.default_rng(1000 + seed)
            for Ltrue in truth_levels[::2]:
                C = step_profile(xa, Ltrue)
                I, trust = oracle_iv(sg, C, biases)
                avail = [i for i in range(N_BIAS) if trust[i]]
                if len(avail) < max(budgets):
                    continue
                tgt = torch.tensor(symlog.forward(I), dtype=torch.float32)
                chosen = [int(rng.choice(avail))]
                for b in range(1, max(budgets) + 1):
                    if b in per_budget:
                        mask = torch.zeros(N_BIAS, dtype=torch.bool)
                        for i in chosen:
                            mask[i] = True
                        rec = np.array([recover(tgt, m, mask) for m in members])
                        per_budget[b].append(abs(rec.mean() - np.log10(Ltrue)))
                    if len(chosen) >= max(budgets):
                        break
                    remaining = [i for i in avail if i not in chosen]
                    if strategy == "random":
                        nxt = int(rng.choice(remaining))
                    else:
                        # acquire where the ensemble disagrees most, in symlog
                        # space; uses model uncertainty only -- no test labels
                        pred = ens.predict(scaling.doping_to_net_input(C),
                                           biases / VT)
                        nxt = max(remaining,
                                  key=lambda i: float(pred.std_symlog[i]))
                    chosen.append(nxt)
        h4b[strategy] = {
            str(b): bootstrap_ci(v, np.median, seed=SEED)
            for b, v in per_budget.items() if v
        }
        for b in budgets:
            if str(b) in h4b[strategy]:
                c = h4b[strategy][str(b)]
                print(f"  {strategy:8s} budget {b}: median err {c['point']:.4f} "
                      f"[{c['lo']:.4f}, {c['hi']:.4f}] decades (n={c['n']})")
    # verdict
    verdict = []
    for b in budgets:
        k = str(b)
        if k in h4b["random"] and k in h4b["max_std"]:
            r, a = h4b["random"][k], h4b["max_std"][k]
            better = a["point"] < r["point"]
            overlap = not (a["hi"] < r["lo"] or r["hi"] < a["lo"])
            verdict.append(dict(budget=b, random=r["point"], max_std=a["point"],
                                max_std_better=bool(better),
                                cis_overlap=bool(overlap)))
    sig = [v for v in verdict if v["max_std_better"] and not v["cis_overlap"]]
    conclusion = ("max_std beats random at budgets "
                  f"{[v['budget'] for v in sig]} (non-overlapping 95% CIs)"
                  if sig else
                  "NO budget shows a statistically distinguishable advantage "
                  "for uncertainty-driven acquisition over random selection")
    print(f"  VERDICT: {conclusion}")
    results["H4b_active_learning"] = {"per_strategy": h4b, "comparison": verdict,
                                      "conclusion": conclusion,
                                      "n_seeds": n_al_seeds}

    # =====================================================================
    # H5  is the uncertainty USEFUL? error-vs-uncertainty and OOD awareness
    # =====================================================================
    print("\n[H5] Uncertainty vs error -- does sigma predict the error at all?")

    def err_sigma(levels, family="step"):
        out = []
        for lv in levels:
            C = (step_profile(xa, lv) if family == "step"
                 else graded_profile(xa, lv))
            I, trust = oracle_iv(sg, C, biases)
            pred = ens.predict(scaling.doping_to_net_input(C), biases / VT)
            for bi in range(len(biases)):
                if not trust[bi]:
                    continue
                e = abs(symlog.forward(I[bi]) - pred.mean_symlog[bi])
                out.append((float(pred.std_symlog[bi]), float(e)))
        return np.asarray(out)

    groups = {
        "interpolation": err_sigma(interp_levels),
        "extrapolation": err_sigma(extrap_levels),
        "family_graded": err_sigma(family_levels, "graded"),
    }
    allpts = np.concatenate(list(groups.values()), axis=0)
    sig, err = allpts[:, 0], allpts[:, 1]

    def spearman(a, b):
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
        ra -= ra.mean(); rb -= rb.mean()
        d = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
        return float((ra * rb).sum() / d) if d > 0 else float("nan")

    rho = spearman(sig, err)
    # binned check: sort by predicted sigma, compare median error per quartile
    order = np.argsort(sig)
    quarts = np.array_split(order, 4)
    binned = [dict(q=i + 1,
                   median_sigma=float(np.median(sig[q])),
                   median_abs_err=float(np.median(err[q])),
                   n=int(q.size)) for i, q in enumerate(quarts)]
    monotone = all(binned[i]["median_abs_err"] <= binned[i + 1]["median_abs_err"]
                   for i in range(len(binned) - 1))
    print(f"  Spearman rho(sigma, |error|) = {rho:+.3f}  (n={sig.size})")
    for b in binned:
        print(f"    quartile {b['q']}: median sigma {b['median_sigma']:.4f}"
              f"   median |err| {b['median_abs_err']:.4f}   (n={b['n']})")
    print(f"  error increases monotonically across sigma quartiles: {monotone}")

    # OOD awareness: does the ensemble KNOW it is extrapolating?
    ood = {}
    for name, g in groups.items():
        ood[name] = dict(median_sigma=float(np.median(g[:, 0])),
                         median_abs_err=float(np.median(g[:, 1])),
                         n=int(g.shape[0]))
        print(f"  {name:14s} median sigma {ood[name]['median_sigma']:.4f}"
              f"   median |err| {ood[name]['median_abs_err']:.4f}"
              f"   (n={ood[name]['n']})")
    infl_sigma = (ood["extrapolation"]["median_sigma"]
                  / max(ood["interpolation"]["median_sigma"], 1e-12))
    infl_err = (ood["extrapolation"]["median_abs_err"]
                / max(ood["interpolation"]["median_abs_err"], 1e-12))
    print(f"  extrapolation vs interpolation: sigma inflates {infl_sigma:.1f}x"
          f" while the error inflates {infl_err:.1f}x")
    ood_verdict = (
        "sigma tracks the extrapolation error"
        if infl_sigma >= 0.5 * infl_err else
        "sigma UNDER-inflates: the ensemble does not know it is extrapolating")
    print(f"  VERDICT: {ood_verdict}")
    results["H5_uncertainty_vs_error"] = {
        "spearman_rho": rho, "n": int(sig.size),
        "sigma_quartiles": binned, "monotone_across_quartiles": bool(monotone),
        "per_group": ood,
        "sigma_inflation_extrap_over_interp": float(infl_sigma),
        "error_inflation_extrap_over_interp": float(infl_err),
        "verdict": ood_verdict,
    }

    # ------------------------------------------------------------------ save
    for k in ("H1_forward_accuracy", "H2_inverse_vs_noise", "H3_calibration"):
        man.add_result(k, results[k])
    (out / "results.json").write_text(json.dumps(results, indent=2),
                                      encoding="utf-8")
    man.add_artifact("results_json", out / "results.json")
    _write_markdown(out, results, decades)
    man.add_artifact("results_summary", out / "results_summary.md")
    man.write(out)
    print(f"\nWrote {out}/results.json, results_summary.md, manifest.json")
    return 0


def _write_markdown(out: Path, r: dict, decades: float) -> None:
    h1, h2, h3 = (r["H1_forward_accuracy"], r["H2_inverse_vs_noise"],
                  r["H3_calibration"])
    L = ["# BayesPINN-Inv: quantitative results (SG-supervised surrogate)",
         "",
         f"Ensemble M={r['model']['M']}, "
         f"{r['model']['params_per_member']:,} params/member. All errors are "
         "against the Scharfetter-Gummel oracle.",
         "",
         "Every statistic reports `n` and a 95% interval (bootstrap for "
         "continuous quantities, Wilson score for coverages). Labels are used "
         "only where the oracle's own noise-floor check passes: "
         f"{r['label_integrity']['n_dropped_untrustworthy']} of "
         f"{r['label_integrity']['n_candidate_labels']} candidate "
         "(profile, bias) pairs were dropped as numerically untrustworthy.",
         "",
         f"Measured current dynamic range of the training labels: "
         f"**{decades:.1f} decades** "
         f"({r['current_range_A_per_m2'][0]:.2e} to "
         f"{r['current_range_A_per_m2'][1]:.2e} A/m^2).",
         "",
         "## H1 Forward accuracy",
         "",
         "Three disjoint test sets. Interpolation lies between training doping "
         "levels; **extrapolation lies outside the training band on both "
         "sides**; family transfer uses graded junctions, a profile shape "
         "absent from training.",
         "",
         "| Test set | Median rel. error (95% CI) | p90 | max | n |",
         "|---|---:|---:|---:|---:|"]
    for k, label in [("interpolation", "Interpolation"),
                     ("extrapolation", "**Extrapolation**"),
                     ("family_transfer_graded", "Family transfer (graded)")]:
        d = h1[k]
        c = d["median_rel_err"]
        L.append(f"| {label} | {c['point']:.1%} "
                 f"({c['lo']:.1%}–{c['hi']:.1%}) | {d['p90_rel_err']:.1%} "
                 f"| {d['max_rel_err']:.1%} | {d['n']} |")
    L += ["", "## H2 Inverse recovery vs measurement noise", "",
          "Single symmetric doping level recovered from the I-V curve — the "
          "*well-posed* sub-problem. This is a one-parameter identification, "
          "not profile recovery; see `docs/NOVELTY_AUDIT.md` for the "
          "identifiability of the full profile problem.", "",
          "| Noise | Median error (decades, 95% CI) | 1σ coverage (95% CI) | n |",
          "|---|---:|---:|---:|"]
    for key, d in h2.items():
        m, cov = d["median_abs_err_decades"], d["coverage_1sigma"]
        noise = key.split("_")[1]
        L.append(f"| {float(noise):.0%} | {m['point']:.4f} "
                 f"({m['lo']:.4f}–{m['hi']:.4f}) | {cov['point']:.0%} "
                 f"({cov['lo']:.0%}–{cov['hi']:.0%}) | {cov['n']} |")
    L += ["", "## H3 UQ calibration", "",
          f"Variance-inflation factor T = {h3['temperature']:.2f}, fitted on a "
          f"disjoint calibration split (n={h3['n_val']}). **Pre and post are "
          f"measured on the identical test set** (n={h3['n_test']}) — the "
          "previous version of this table compared two different sets.", "",
          "| Interval | Empirical (raw) | Recalibrated | Nominal |",
          "|---|---:|---:|---:|"]
    for zz in (1.0, 1.64, 2.0):
        d = h3[f"z_{zz}"]
        L.append(f"| ±{zz}σ | {d['pre']['point']:.0%} "
                 f"({d['pre']['lo']:.0%}–{d['pre']['hi']:.0%}) | "
                 f"{d['post']['point']:.0%} "
                 f"({d['post']['lo']:.0%}–{d['post']['hi']:.0%}) | "
                 f"{d['nominal']:.0%} |")
    L += ["", "## H4a Bias-subset ablation (not active learning)", "",
          "| Bias subset | # biases | Median recovery error (decades) | n |",
          "|---|---:|---:|---:|"]
    for name, d in r["H4a_bias_subset_ablation"].items():
        c = d["median_abs_err_decades"]
        L.append(f"| {name.replace('_', ' ')} | {d['n_biases_requested']} | "
                 f"{c['point']:.4f} ({c['lo']:.4f}–{c['hi']:.4f}) | {c['n']} |")
    L += ["", "## H4b Active learning vs random baseline", "",
          "Sequential acquisition: at each round pick the next bias to measure, "
          "then re-invert. `max_std` picks the bias of greatest ensemble "
          "disagreement (model uncertainty only — no test labels); `random` "
          "picks uniformly among trustworthy biases.", "",
          "| Budget | Random (decades) | Max-std (decades) | Distinguishable? |",
          "|---|---:|---:|---|"]
    for v in r["H4b_active_learning"]["comparison"]:
        L.append(f"| {v['budget']} | {v['random']:.4f} | {v['max_std']:.4f} | "
                 f"{'yes' if (v['max_std_better'] and not v['cis_overlap']) else 'no'} |")
    L += ["", f"**Conclusion:** {r['H4b_active_learning']['conclusion']}.", ""]
    h5 = r.get("H5_uncertainty_vs_error")
    if h5:
        L += ["## H5 Is the uncertainty useful?", "",
              "A predictive standard deviation is only worth reporting if it "
              "tracks the actual error.", "",
              f"Spearman rank correlation between predicted sigma and "
              f"|error|: **{h5['spearman_rho']:+.3f}** (n={h5['n']}). Median "
              f"|error| across ascending sigma quartiles: "
              + ", ".join(f"{b['median_abs_err']:.4f}"
                          for b in h5["sigma_quartiles"])
              + f" (monotone: {h5['monotone_across_quartiles']}).", "",
              "Out-of-distribution awareness — does the ensemble know when it "
              "is extrapolating?", "",
              "| Test set | Median sigma | Median \\|error\\| | n |",
              "|---|---:|---:|---:|"]
        for k, v in h5["per_group"].items():
            L.append(f"| {k} | {v['median_sigma']:.4f} | "
                     f"{v['median_abs_err']:.4f} | {v['n']} |")
        L += ["",
              f"Going from interpolation to extrapolation, sigma inflates "
              f"**{h5['sigma_inflation_extrap_over_interp']:.1f}x** while the "
              f"error inflates "
              f"**{h5['error_inflation_extrap_over_interp']:.1f}x**. "
              f"{h5['verdict']}.", ""]
    (out / "results_summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
