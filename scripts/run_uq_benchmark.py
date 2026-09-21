#!/usr/bin/env python
"""Fair comparison of four uncertainty backends on the SG-supervised surrogate.

Why this exists
---------------
``docs/RELEASE_READINESS.md`` Gate D recorded "MC-dropout / SWAG compared:
**not demonstrated**". They could not be: both were wired to
:class:`ForwardPINN`, the *superseded* pure-physics forward model, while the
model actually under evaluation is the SG-supervised
:class:`IVSurrogate`. ``bayesian/surrogate_uq.py`` closes that gap; this
script runs the comparison.

Fairness controls
-----------------
Every method sees the *identical* protocol -- there is one implementation of
it, in :mod:`bayespinn_inv.data.splits`:

* the same five disjoint doping-level splits,
* the same SG labels, filtered by the same oracle trust flag,
* the same symlog transform and the same feature normaliser,
* the same metrics, computed by the same functions,
* temperature fitted on the same disjoint calibration split, never on test,
* pre/post calibration measured on one identical test set (SCI-01).

Compute is **not** equalised, because the methods are not equal-cost by
nature: a deep ensemble trains M networks, MC-dropout and SWAG train one.
Equalising it would privilege one of them by construction. Instead the cost
is *measured and reported* (training seconds, inference seconds, parameter
count, forward passes per prediction) so the accuracy/uncertainty numbers can
be read against what they cost. An equal-training-budget ensemble
(``--budget-matched``) is additionally run so the "5x the compute" objection
has an answer rather than a caveat.

Usage
-----
    PYTHONPATH=src python scripts/run_uq_benchmark.py [--out DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from math import erf, sqrt
from pathlib import Path
from typing import Dict, Sequence

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.bayesian.surrogate_uq import MCDropoutSurrogate, SWAGSurrogate
from bayespinn_inv.bayesian.swag import SWAGConfig, SWAGRecorder
from bayespinn_inv.calibration.metrics import (
    crps_empirical,
    ece_floor_for_ensemble,
    expected_calibration_error,
    gaussian_nll,
    sharpness,
)
from bayespinn_inv.data.splits import (
    ProtocolSpec,
    build_level_splits,
    build_sg_labels,
    graded_profile,
    oracle_iv,
    step_profile,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import Grid1D, ScharfetterGummel1D, SGConfig
from bayespinn_inv.surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SymlogTransform,
    train_surrogate,
)
from bayespinn_inv.utils.provenance import RunManifest

SEED = 0
M_ENSEMBLE = 5
T_SAMPLES = 30          # test-time samples for MC-dropout and SWAG
DROPOUT_P = 0.1
SWA_SNAPSHOTS = 20      # SWAG snapshots collected in the SWA phase


# ---------------------------------------------------------------- statistics
def bootstrap_ci(values: Sequence[float], stat=np.median, n_boot: int = 2000,
                 alpha: float = 0.05, seed: int = 0) -> Dict[str, float]:
    v = np.asarray(list(values), dtype=float)
    if v.size == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    rs = np.random.RandomState(seed)
    boots = [stat(v[rs.randint(0, v.size, v.size)]) for _ in range(n_boot)]
    return dict(point=float(stat(v)),
                lo=float(np.quantile(boots, alpha / 2)),
                hi=float(np.quantile(boots, 1 - alpha / 2)), n=int(v.size))


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Dict[str, float]:
    if n == 0:
        return dict(point=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    z = 1.959963984540054
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return dict(point=float(phat), lo=float(max(0.0, centre - half)),
                hi=float(min(1.0, centre + half)), n=int(n))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


def nominal(z: float) -> float:
    return erf(z / sqrt(2.0))


# ------------------------------------------------------------- evaluation
class Evaluator:
    """One evaluation path, applied identically to every backend."""

    def __init__(self, sg, scaling, symlog, spec, splits):
        self.sg, self.scaling, self.symlog = sg, scaling, symlog
        self.spec, self.splits = spec, splits
        self.xa = spec.anchor_x()
        self.biases = spec.biases
        self.VT = scaling.V_T
        self._oracle_cache: Dict[tuple, tuple] = {}

    def oracle(self, level: float, family: str):
        """SG truth for one profile. Cached: identical for every backend."""
        key = (float(level), family)
        if key not in self._oracle_cache:
            C = (step_profile(self.xa, level) if family == "step"
                 else graded_profile(self.xa, level, self.spec.graded_width_si))
            I, trust = oracle_iv(self.sg, C, self.biases, self.spec.trust_snr)
            self._oracle_cache[key] = (C, I, trust)
        return self._oracle_cache[key]

    def collect(self, backend, levels, family="step") -> Dict[str, np.ndarray]:
        """Per-point (truth, mean, sigma, samples) over a level set."""
        y, mu, sd, rel, samp = [], [], [], [], []
        for lv in levels:
            C, I, trust = self.oracle(lv, family)
            pred = backend.predict(self.scaling.doping_to_net_input(C),
                                   self.biases / self.VT)
            for bi in range(len(self.biases)):
                if not trust[bi]:
                    continue
                y.append(float(self.symlog.forward(I[bi])))
                mu.append(float(pred.mean_symlog[bi]))
                sd.append(float(pred.std_symlog[bi]))
                rel.append(abs(pred.mean_current[bi] - I[bi]) / abs(I[bi]))
                samp.append(pred.samples_symlog[:, bi])
        return dict(y=np.asarray(y), mu=np.asarray(mu), sd=np.asarray(sd),
                    rel=np.asarray(rel), samples=np.asarray(samp))

    def evaluate(self, name: str, backend, cost: dict) -> dict:
        s = self.splits
        parts = {
            "interpolation": self.collect(backend, s["test_interp"], "step"),
            "extrapolation": self.collect(backend, s["test_extrap"], "step"),
            "family_graded": self.collect(backend, s["test_family_graded"], "graded"),
        }
        val = self.collect(backend, s["calibration_val"], "step")

        out: Dict[str, object] = {"method": name, "cost": cost}
        # A single-member "ensemble" has sigma identically 0: every UQ metric
        # is undefined (0/0), not bad. Say that instead of reporting NaN.
        has_uncertainty = float(np.max(np.concatenate(
            [p["sd"] for p in parts.values()]))) > 1e-12

        # --- H1 accuracy -----------------------------------------------
        out["accuracy"] = {
            k: {"median_rel_err": bootstrap_ci(p["rel"], np.median, seed=SEED),
                "p90_rel_err": float(np.quantile(p["rel"], 0.9)) if p["rel"].size else None,
                "max_rel_err": float(p["rel"].max()) if p["rel"].size else None,
                "n": int(p["rel"].size)}
            for k, p in parts.items()
        }

        if not has_uncertainty:
            out["calibration"] = out["scores"] = out["uncertainty_utility"] = None
            out["ood"] = None
            out["uq_note"] = ("sigma is identically zero for a single "
                              "deterministic model; uncertainty metrics are "
                              "undefined, not poor. Accuracy only.")
            return out

        # --- H3 calibration on the pooled interp+extrap test set --------
        test = {k: np.concatenate([parts["interpolation"][k],
                                   parts["extrapolation"][k]])
                for k in ("y", "mu", "sd")}
        test["samples"] = np.concatenate([parts["interpolation"]["samples"],
                                          parts["extrapolation"]["samples"]])
        ok = test["sd"] > 1e-12
        z_test = (test["y"][ok] - test["mu"][ok]) / test["sd"][ok]
        vok = val["sd"] > 1e-12
        z_val = (val["y"][vok] - val["mu"][vok]) / val["sd"][vok]
        # NLL-optimal scalar variance inflation, fitted on the calibration
        # split only -- never on the test set.
        T = float(np.sqrt(np.mean(z_val ** 2))) if z_val.size else float("nan")

        cal = {"temperature": T, "n_val": int(z_val.size), "n_test": int(z_test.size)}
        for zz in (1.0, 1.64, 2.0):
            cal[f"z_{zz}"] = {
                "pre": wilson_ci(int(np.sum(np.abs(z_test) <= zz)), z_test.size),
                "post": wilson_ci(int(np.sum(np.abs(z_test) <= zz * T)), z_test.size),
                "nominal": nominal(zz),
            }
        out["calibration"] = cal

        # --- proper scores, raw and temperature-corrected ---------------
        mu_t, sd_t, y_t = test["mu"][ok], test["sd"][ok], test["y"][ok]
        # ECE is estimated from the sample ECDF, so temperature scaling is
        # applied by inflating the samples about their own mean -- the same
        # transform sigma -> T*sigma, expressed on the samples.
        smp = test["samples"][ok].T                       # (M, N)
        smp_cal = mu_t[None, :] + T * (smp - mu_t[None, :])
        out["scores"] = {
            "nll_raw": gaussian_nll(mu_t, sd_t, y_t),
            "nll_calibrated": gaussian_nll(mu_t, sd_t * T, y_t),
            "crps_empirical": float(np.mean(crps_empirical(smp, y_t))),
            "crps_gaussian_calibrated": float(np.mean(
                _crps_gauss(mu_t, sd_t * T, y_t))),
            "sharpness_raw": sharpness(sd_t),
            "sharpness_calibrated": sharpness(sd_t * T),
            "ece_raw": expected_calibration_error(smp, y_t),
            "ece_calibrated": expected_calibration_error(smp_cal, y_t),
            "rmse_symlog": float(np.sqrt(np.mean((mu_t - y_t) ** 2))),
        }

        # --- H5 is sigma useful? ---------------------------------------
        allp = {k: np.concatenate([p[k] for p in parts.values()])
                for k in ("y", "mu", "sd")}
        err = np.abs(allp["y"] - allp["mu"])
        rho = spearman(allp["sd"], err)
        order = np.argsort(allp["sd"])
        quarts = np.array_split(order, 4)
        binned = [dict(q=i + 1, median_sigma=float(np.median(allp["sd"][q])),
                       median_abs_err=float(np.median(err[q])), n=int(q.size))
                  for i, q in enumerate(quarts)]
        out["uncertainty_utility"] = {
            "spearman_rho": rho, "n": int(err.size), "quartiles": binned,
            "monotone": all(binned[i]["median_abs_err"] <= binned[i + 1]["median_abs_err"]
                            for i in range(len(binned) - 1)),
        }

        # --- OOD awareness ---------------------------------------------
        ood = {k: dict(median_sigma=float(np.median(p["sd"])),
                       median_abs_err=float(np.median(np.abs(p["y"] - p["mu"]))),
                       n=int(p["y"].size))
               for k, p in parts.items()}
        base = ood["interpolation"]
        for v in ood.values():
            v["sigma_inflation_vs_interp"] = v["median_sigma"] / base["median_sigma"]
            v["error_inflation_vs_interp"] = v["median_abs_err"] / base["median_abs_err"]
        out["ood"] = ood
        return out


def _crps_gauss(mu, sigma, y):
    from bayespinn_inv.calibration.metrics import crps_gaussian
    return crps_gaussian(mu, sigma, y)


# ------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/uq_benchmark")
    ap.add_argument("--epochs", type=int, default=2500)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    epochs = 300 if args.quick else args.epochs
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    spec = ProtocolSpec()
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(spec.domain_si[1])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling, SILICON, SGConfig())
    symlog = SymlogTransform()
    splits = build_level_splits(spec)

    cfg = dict(seed=SEED, epochs=epochs, M_ensemble=M_ENSEMBLE,
               T_samples=T_SAMPLES, dropout=DROPOUT_P,
               swa_snapshots=SWA_SNAPSHOTS,
               protocol={k: getattr(spec, k) for k in
                         ("n_anchor", "bias_max", "n_bias", "train_lo",
                          "train_hi", "extrap_lo", "extrap_hi", "trust_snr")})
    man = RunManifest.create("uq_benchmark", config=cfg, seed=SEED)

    print("Generating SG training labels (shared by every backend) ...")
    t0 = time.time()
    X, Y, integrity = build_sg_labels(sg, scaling, symlog, splits["train"], spec)
    print(f"  {integrity['n_used']} labels in {time.time()-t0:.1f}s "
          f"(dropped {integrity['n_dropped_untrustworthy']}"
          f"/{integrity['n_candidate_labels']} below the oracle noise floor)")
    norm = Normalizer.fit(X)
    ev = Evaluator(sg, scaling, symlog, spec, splits)
    backends: Dict[str, tuple] = {}

    def _mk(seed, dropout=0.0):
        return IVSurrogate(IVSurrogateConfig(doping_dim=spec.n_anchor, hidden=128,
                                             n_layers=3, dropout=dropout, seed=seed))

    # ---- 1. deterministic single model (accuracy floor, no UQ) ---------
    print("\n[1/5] deterministic single surrogate ...")
    t0 = time.time()
    det = _mk(0)
    train_surrogate(det, X, Y, norm, epochs=epochs, lr=2e-3)
    t_det = time.time() - t0
    backends["deterministic"] = (
        SurrogateEnsemble([det], norm, symlog),
        dict(train_seconds=t_det, n_networks=1, params=det.num_parameters(),
             forward_passes_per_prediction=1,
             note="sigma is identically zero with one member; accuracy baseline only"))

    # ---- 2. deep ensemble (the current method) ------------------------
    print(f"[2/5] deep ensemble M={M_ENSEMBLE} ...")
    t0 = time.time()
    members = []
    for m in range(M_ENSEMBLE):
        net = _mk(m)
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))      # bootstrap for diversity
        train_surrogate(net, X[idx], Y[idx], norm, epochs=epochs, lr=2e-3)
        members.append(net)
    t_ens = time.time() - t0
    backends["deep_ensemble"] = (
        SurrogateEnsemble(members, norm, symlog),
        dict(train_seconds=t_ens, n_networks=M_ENSEMBLE,
             params=members[0].num_parameters() * M_ENSEMBLE,
             forward_passes_per_prediction=M_ENSEMBLE))

    # ---- 3. MC-dropout (one network, T stochastic passes) -------------
    print(f"[3/5] MC-dropout p={DROPOUT_P}, T={T_SAMPLES} ...")
    t0 = time.time()
    mdl = _mk(0, dropout=DROPOUT_P)
    train_surrogate(mdl, X, Y, norm, epochs=epochs, lr=2e-3)
    t_mcd = time.time() - t0
    backends["mc_dropout"] = (
        MCDropoutSurrogate(mdl, norm, symlog, n_samples=T_SAMPLES, seed=SEED),
        dict(train_seconds=t_mcd, n_networks=1, params=mdl.num_parameters(),
             forward_passes_per_prediction=T_SAMPLES, dropout_p=DROPOUT_P))

    # ---- 4. SWAG (one network + an SWA phase) -------------------------
    print(f"[4/5] SWAG, {SWA_SNAPSHOTS} snapshots, T={T_SAMPLES} ...")
    t0 = time.time()
    swa_net = _mk(0)
    burn = int(epochs * 0.75)
    train_surrogate(swa_net, X, Y, norm, epochs=burn, lr=2e-3)
    rec = SWAGRecorder(swa_net, SWAGConfig(max_rank=min(20, SWA_SNAPSHOTS),
                                           T_samples=T_SAMPLES, seed=SEED))
    per = max(1, (epochs - burn) // SWA_SNAPSHOTS)
    for _ in range(SWA_SNAPSHOTS):
        # constant-LR SWA phase: no cosine decay, so the iterates keep moving
        train_surrogate(swa_net, X, Y, norm, epochs=per, lr=2e-4)
        rec.collect()
    t_swag = time.time() - t0
    backends["swag"] = (
        SWAGSurrogate(swa_net, rec, norm, symlog),
        dict(train_seconds=t_swag, n_networks=1, params=swa_net.num_parameters(),
             forward_passes_per_prediction=T_SAMPLES,
             snapshots=SWA_SNAPSHOTS))

    # ---- 5. budget-matched ensemble -----------------------------------
    print(f"[5/5] budget-matched ensemble (M={M_ENSEMBLE}, epochs/{M_ENSEMBLE}) ...")
    t0 = time.time()
    bm = []
    for m in range(M_ENSEMBLE):
        net = _mk(m)
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))
        train_surrogate(net, X[idx], Y[idx], norm,
                        epochs=max(1, epochs // M_ENSEMBLE), lr=2e-3)
        bm.append(net)
    t_bm = time.time() - t0
    backends["deep_ensemble_budget_matched"] = (
        SurrogateEnsemble(bm, norm, symlog),
        dict(train_seconds=t_bm, n_networks=M_ENSEMBLE,
             params=bm[0].num_parameters() * M_ENSEMBLE,
             forward_passes_per_prediction=M_ENSEMBLE,
             note=f"total epochs matched to the single-network methods "
                  f"({epochs}) rather than {M_ENSEMBLE}x it"))

    # ------------------------------------------------------- evaluate
    print("\nEvaluating every backend through one identical path ...")
    results = {"config": cfg, "label_integrity": integrity,
               "splits": {k: v.tolist() for k, v in splits.items()},
               "methods": {}}
    for name, (backend, cost) in backends.items():
        t0 = time.time()
        r = ev.evaluate(name, backend, cost)
        r["cost"]["eval_seconds"] = time.time() - t0
        results["methods"][name] = r
        acc = r["accuracy"]["interpolation"]["median_rel_err"]["point"]
        uu = r["uncertainty_utility"]
        rho = uu["spearman_rho"] if uu else float("nan")
        print(f"  {name:30s} interp median rel err {acc:7.2%}   "
              f"rho(sigma,|err|) {rho:+.3f}   train {cost['train_seconds']:6.1f}s")

    results["ece_floor_M5"] = ece_floor_for_ensemble(M_ENSEMBLE)
    results["ece_floor_T30"] = ece_floor_for_ensemble(T_SAMPLES)

    (out / "uq_benchmark.json").write_text(json.dumps(results, indent=2, default=float),
                                           encoding="utf-8", newline="\n")
    man.add_result("uq_benchmark", results["methods"])
    man.add_artifact("uq_benchmark_json", out / "uq_benchmark.json")
    _write_markdown(out, results)
    man.add_artifact("uq_benchmark_summary", out / "uq_benchmark.md")
    man.write(out)
    print(f"\nWrote {out}/uq_benchmark.json and uq_benchmark.md")
    return 0


def _write_markdown(out: Path, r: dict) -> None:
    M = r["methods"]
    order = ["deterministic", "deep_ensemble", "deep_ensemble_budget_matched",
             "mc_dropout", "swag"]
    order = [o for o in order if o in M]
    L = ["# Uncertainty backends compared under one protocol", "",
         "Every method sees identical splits, identical SG labels, identical "
         "filtering, identical metrics. Temperature is fitted on the disjoint "
         "calibration split; pre/post are measured on the same test set.", "",
         f"Labels: {r['label_integrity']['n_used']} used, "
         f"{r['label_integrity']['n_dropped_untrustworthy']} of "
         f"{r['label_integrity']['n_candidate_labels']} dropped below the "
         f"oracle's noise floor.", "",
         "## Forward accuracy (median relative error, 95% CI)", "",
         "| Method | Interpolation | Extrapolation | Family transfer | n |",
         "|---|---:|---:|---:|---:|"]
    for k in order:
        a = M[k]["accuracy"]

        def _cell(split, _a=a):
            c = _a[split]["median_rel_err"]
            return f"{c['point']:.1%} ({c['lo']:.1%}-{c['hi']:.1%})"
        L.append(f"| `{k}` | {_cell('interpolation')} | {_cell('extrapolation')} | "
                 f"{_cell('family_graded')} | {a['interpolation']['n']} |")

    L += ["", "## Uncertainty quality", "",
          "| Method | rho(sigma,\\|err\\|) | NLL raw | NLL calib | CRPS | "
          "ECE raw | ECE calib | Sharpness | T |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k in order:
        if M[k]["scores"] is None:
            continue
        s, c = M[k]["scores"], M[k]["calibration"]
        u = M[k]["uncertainty_utility"]
        L.append(f"| `{k}` | {u['spearman_rho']:+.3f} | {s['nll_raw']:.3f} | "
                 f"{s['nll_calibrated']:.3f} | {s['crps_empirical']:.4f} | "
                 f"{s['ece_raw']:.3f} | {s['ece_calibrated']:.3f} | "
                 f"{s['sharpness_raw']:.4f} | {c['temperature']:.2f} |")

    L += ["", "## Interval coverage (pre -> post temperature scaling)", "",
          "| Method | +/-1σ | +/-1.64σ | +/-2σ | n |", "|---|---:|---:|---:|---:|"]
    for k in order:
        if M[k]["calibration"] is None:
            continue
        c = M[k]["calibration"]
        cells = []
        for zz in ("1.0", "1.64", "2.0"):
            d = c[f"z_{zz}"]
            cells.append(f"{d['pre']['point']:.0%} -> {d['post']['point']:.0%} "
                         f"(nom {d['nominal']:.0%})")
        L.append(f"| `{k}` | " + " | ".join(cells) + f" | {c['n_test']} |")

    L += ["", "## Out-of-distribution awareness", "",
          "Ratio of median sigma / median |error| on each set, relative to "
          "interpolation. A backend that *knows* it is extrapolating inflates "
          "sigma at least as fast as the error grows.", "",
          "| Method | sigma inflation (extrap) | error inflation (extrap) | "
          "sigma inflation (family) | error inflation (family) |",
          "|---|---:|---:|---:|---:|"]
    for k in order:
        if M[k]["ood"] is None:
            continue
        o = M[k]["ood"]
        L.append(f"| `{k}` | {o['extrapolation']['sigma_inflation_vs_interp']:.1f}x | "
                 f"{o['extrapolation']['error_inflation_vs_interp']:.1f}x | "
                 f"{o['family_graded']['sigma_inflation_vs_interp']:.1f}x | "
                 f"{o['family_graded']['error_inflation_vs_interp']:.1f}x |")

    L += ["", "## Cost", "",
          "| Method | Networks | Train (s) | Forward passes / prediction | Eval (s) |",
          "|---|---:|---:|---:|---:|"]
    for k in order:
        c = M[k]["cost"]
        L.append(f"| `{k}` | {c['n_networks']} | {c['train_seconds']:.1f} | "
                 f"{c['forward_passes_per_prediction']} | {c['eval_seconds']:.1f} |")
    L += ["", f"ECE estimator floor at M=5: {r['ece_floor_M5']:.3f}; "
              f"at T=30: {r['ece_floor_T30']:.3f}. An ECE at the floor is "
              "not evidence of miscalibration.", ""]
    (out / "uq_benchmark.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
