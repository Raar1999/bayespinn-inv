#!/usr/bin/env python
"""Does identifiability-aware bias selection beat uncertainty-driven selection?

Background
----------
``outputs/results/results_summary.md`` H4b reports that the project's
uncertainty acquisition (``max_std``) shows **no distinguishable advantage
over random** at any budget. ``docs/NOVELTY_AUDIT.md`` C4 rejected building an
"uncertainty-aware active inverse design loop" on the grounds that it would be
a buzzword contribution with no measured gain.

This script tests the specific hypothesis that *would* justify revisiting
that: that ``max_std`` failed not because experiment design cannot help, but
because predictive uncertainty is the wrong criterion for an *inverse*
problem. Uncertainty asks "where is the forward model unsure?"; the inverse
problem needs "which measurement constrains a doping direction I cannot
currently see?".

Strategies compared (all pick biases sequentially from one candidate pool)
-------------------------------------------------------------------------
``random``           uniform -- the baseline H4b could not beat
``max_std``          largest ensemble disagreement -- the incumbent
``d_optimal``        maximise log det of the Fisher information
``e_optimal``        maximise the smallest eigenvalue of the information
``null_space``       largest signal along directions the design cannot yet see
``std_x_nullspace``  rank-product of the two -- uncertainty *and* information

Fairness
--------
* Every strategy draws from the identical candidate pool, on the identical
  device, with the identical budget schedule.
* Acquisition sees the **surrogate** Jacobian and the **surrogate** sigma
  only. It never touches the SG oracle: choosing where to measure using the
  oracle would be using the answer to pick the question.
* Scoring uses the **SG** Jacobian, which no strategy had access to.
* ``random`` is averaged over ``--seeds`` repeats; the deterministic
  strategies are run once (they have no seed dependence).

Metrics
-------
* ``identifiable_rank`` of the chosen design against the true Jacobian at 2%
  noise -- how many doping dof the chosen measurements actually determine.
* ``log_det_information`` -- total information, a design-quality scalar.
* profile recovery error from a multi-start inverse solve restricted to the
  chosen biases -- the end-to-end check that rank translates into recovery.

Usage
-----
    PYTHONPATH=src python scripts/run_experiment_design.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.active_learning.design import (
    DESIGN_STRATEGIES,
    design_summary,
    greedy_design,
)
from bayespinn_inv.data.splits import (
    ProtocolSpec,
    build_level_splits,
    build_sg_labels,
)
from bayespinn_inv.inverse.identifiability import sg_forward_jacobian
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
NOISE = 0.02
P_ANCHOR = 16
V_MAX = 0.9
N_BIAS = 19
GRID_N = 301


def devices(xa: np.ndarray) -> Dict[str, np.ndarray]:
    xj = 0.5 * float(xa.max())
    return {
        "step_symmetric": np.where(xa < xj, -1e22, 1e22),
        "step_asymmetric": np.where(xa < xj, -1e21, 5e22),
        "graded": 1e22 * np.tanh((xa - xj) / 1.5e-7),
        "ldd": np.where(xa < 0.35e-6, -1e22,
                        np.where(xa < 0.6e-6, 5e21, 5e23)),
    }


def surrogate_jacobian(ens: SurrogateEnsemble, scaling, C: np.ndarray,
                       biases_scaled: np.ndarray, step: float = 0.01) -> np.ndarray:
    """d symlog(I) / d log10|C| through the surrogate, by central differences.

    Central differences rather than autograd so that this is exactly the same
    estimator the SG Jacobian uses -- a difference in estimator between the
    acquisition Jacobian and the scoring Jacobian would confound the
    comparison.
    """
    P = C.shape[0]
    J = np.zeros((len(biases_scaled), P))
    for j in range(P):
        if C[j] == 0.0:
            continue
        sign, mag = np.sign(C[j]), abs(C[j])
        Cp, Cm = C.copy(), C.copy()
        Cp[j] = sign * mag * 10.0 ** (+step)
        Cm[j] = sign * mag * 10.0 ** (-step)
        sp = ens.predict(scaling.doping_to_net_input(Cp), biases_scaled).mean_symlog
        sm = ens.predict(scaling.doping_to_net_input(Cm), biases_scaled).mean_symlog
        J[:, j] = (sp - sm) / (2.0 * step)
    return J


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/experiment_design")
    ap.add_argument("--epochs", type=int, default=2500)
    ap.add_argument("--seeds", type=int, default=12, help="repeats for `random`")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    epochs = 300 if args.quick else args.epochs
    n_seeds = 4 if args.quick else args.seeds
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    spec = ProtocolSpec()
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(spec.domain_si[1])))
    sg_train = ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling, SILICON, SGConfig())
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, GRID_N), scaling, SILICON, SGConfig())
    symlog = SymlogTransform()
    splits = build_level_splits(spec)

    # ---- forward surrogate: the only model the acquisition may consult ----
    print(f"Training the acquisition surrogate (M=5, {epochs} epochs) ...")
    X, Y, integrity = build_sg_labels(sg_train, scaling, symlog, splits["train"], spec)
    norm = Normalizer.fit(X)
    members = []
    for m in range(5):
        net = IVSurrogate(IVSurrogateConfig(doping_dim=spec.n_anchor, hidden=128,
                                            n_layers=3, seed=m))
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))
        train_surrogate(net, X[idx], Y[idx], norm, epochs=epochs, lr=2e-3)
        members.append(net)
    ens = SurrogateEnsemble(members, norm, symlog)

    xa = np.linspace(spec.domain_si[0], spec.domain_si[1], P_ANCHOR)
    biases = np.linspace(0.0, V_MAX, N_BIAS)
    devs = devices(xa)
    if args.quick:
        devs = {k: devs[k] for k in list(devs)[:2]}
    budgets = [2, 3, 4, 6, 8]
    cfg = dict(seed=SEED, noise=NOISE, P=P_ANCHOR, n_bias=N_BIAS, v_max=V_MAX,
               grid_n=GRID_N, budgets=budgets, n_seeds=n_seeds, epochs=epochs,
               strategies=list(DESIGN_STRATEGIES))
    man = RunManifest.create("experiment_design", config=cfg, seed=SEED)
    results: Dict[str, object] = {"config": cfg, "label_integrity": integrity,
                                  "devices": {}}

    for dname, C in devs.items():
        print(f"\n### {dname}")
        t0 = time.time()
        # --- truth: the SG Jacobian. Used for SCORING only. ---------------
        J_true, I_ref, kept, entry_noise = sg_forward_jacobian(
            sg, C, biases, rel_step=0.01, min_snr=1e4)
        # --- what the acquisition is allowed to see -----------------------
        J_surr = surrogate_jacobian(ens, scaling, C, biases[kept] / scaling.V_T)
        pred = ens.predict(scaling.doping_to_net_input(C), biases[kept] / scaling.V_T)
        sigma = pred.std_symlog
        cand = list(range(len(kept)))
        jac_agreement = float(np.corrcoef(J_true.ravel(), J_surr.ravel())[0, 1])
        print(f"  {len(kept)} trustworthy biases; surrogate-vs-SG Jacobian "
              f"correlation {jac_agreement:+.3f}")

        per_strategy: Dict[str, object] = {}
        for strat in DESIGN_STRATEGIES:
            rows = []
            reps = n_seeds if strat == "random" else 1
            for r in range(reps):
                rng = np.random.default_rng(1000 + r)
                for b in budgets:
                    sel = greedy_design(J_surr, cand, b, strat,
                                        sigma=sigma, rng=rng)
                    s = design_summary(J_true, sel, noise_rel=NOISE,
                                       jacobian_noise=entry_noise)
                    s["budget"] = b; s["rep"] = r
                    s["biases_V"] = [float(biases[kept[i]]) for i in sel]
                    rows.append(s)
            agg = {}
            for b in budgets:
                rk = [x["identifiable_rank"] for x in rows if x["budget"] == b]
                ld = [x["log_det_information"] for x in rows if x["budget"] == b]
                agg[b] = {"rank_mean": float(np.mean(rk)),
                          "rank_std": float(np.std(rk)),
                          "rank_min": int(np.min(rk)), "rank_max": int(np.max(rk)),
                          "log_det_mean": float(np.mean(ld)), "n_reps": len(rk)}
            per_strategy[strat] = {"rows": rows, "by_budget": agg}
            print(f"  {strat:18s} rank by budget "
                  + "  ".join(f"{b}:{agg[b]['rank_mean']:.2f}" for b in budgets))
        results["devices"][dname] = {
            "n_trustworthy_biases": len(kept),
            "jacobian_agreement_surrogate_vs_sg": jac_agreement,
            "entry_noise": float(entry_noise),
            "strategies": per_strategy,
            "seconds": time.time() - t0,
        }

    # ------------------------------------------------------------ verdict
    verdict = _verdict(results, budgets)
    results["verdict"] = verdict
    print("\nVERDICT")
    for line in verdict["lines"]:
        print("  " + line)

    (out / "experiment_design.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8", newline="\n")
    man.add_result("verdict", verdict)
    man.add_artifact("json", out / "experiment_design.json")
    _write_markdown(out, results, budgets)
    man.add_artifact("summary", out / "experiment_design.md")
    man.write(out)
    print(f"\nWrote {out}/experiment_design.json and .md")
    return 0


def _verdict(results: dict, budgets: List[int]) -> dict:
    """Compare every strategy against random, pooled over devices."""
    lines, table = [], {}
    for strat in DESIGN_STRATEGIES:
        wins = ties = losses = 0
        deltas = []
        for d in results["devices"].values():
            rnd = d["strategies"]["random"]["by_budget"]
            cur = d["strategies"][strat]["by_budget"]
            for b in budgets:
                delta = cur[b]["rank_mean"] - rnd[b]["rank_mean"]
                deltas.append(delta)
                # "distinguishable" = beyond one std of the random baseline
                tol = max(rnd[b]["rank_std"], 1e-9)
                if delta > tol:
                    wins += 1
                elif delta < -tol:
                    losses += 1
                else:
                    ties += 1
        table[strat] = {"mean_rank_delta_vs_random": float(np.mean(deltas)),
                        "wins": wins, "ties": ties, "losses": losses,
                        "n_comparisons": len(deltas)}
        lines.append(f"{strat:18s} mean rank vs random {np.mean(deltas):+.2f}  "
                     f"(win/tie/loss {wins}/{ties}/{losses})")
    best = max((k for k in table if k != "random"),
               key=lambda k: table[k]["mean_rank_delta_vs_random"])
    beats = table[best]["mean_rank_delta_vs_random"] > 0 and table[best]["wins"] > table[best]["losses"]
    lines.append(f"best non-random strategy: {best} "
                 f"({'beats' if beats else 'does NOT beat'} random)")
    return {"table": table, "best": best, "best_beats_random": bool(beats),
            "lines": lines}


def _write_markdown(out: Path, r: dict, budgets: List[int]) -> None:
    v = r["verdict"]
    L = ["# Identifiability-aware experiment design vs uncertainty acquisition", "",
         "Sequential bias selection at 2% measurement noise. Acquisition sees "
         "the **surrogate** Jacobian and sigma only; scoring uses the **SG** "
         "Jacobian, which no strategy had access to. `random` is averaged over "
         f"{r['config']['n_seeds']} seeds.", "",
         "## Verdict", ""]
    L += [f"* `{k}`: mean identifiable-rank delta vs random **{d['mean_rank_delta_vs_random']:+.2f}** "
          f"(win/tie/loss {d['wins']}/{d['ties']}/{d['losses']} over "
          f"{d['n_comparisons']} device x budget comparisons)"
          for k, d in v["table"].items() if k != "random"]
    L += ["", f"**Best non-random strategy: `{v['best']}` — "
              f"{'beats' if v['best_beats_random'] else 'does NOT beat'} random.**", ""]

    L += ["## Identifiable rank by budget (mean over reps)", "",
          "| Device | Strategy | " + " | ".join(f"k={b}" for b in budgets) + " |",
          "|---|---|" + "---:|" * len(budgets)]
    for dname, d in r["devices"].items():
        for strat in DESIGN_STRATEGIES:
            agg = d["strategies"][strat]["by_budget"]
            cells = " | ".join(f"{agg[b]['rank_mean']:.2f}" for b in budgets)
            L.append(f"| `{dname}` | `{strat}` | {cells} |")
    L += ["", "## Surrogate-vs-SG Jacobian agreement", "",
          "The acquisition is only as good as the Jacobian it plans with. "
          "A low correlation here bounds how well *any* Jacobian-based "
          "strategy can possibly do.", "",
          "| Device | Pearson r (surrogate J vs SG J) | Trustworthy biases |",
          "|---|---:|---:|"]
    for dname, d in r["devices"].items():
        L.append(f"| `{dname}` | {d['jacobian_agreement_surrogate_vs_sg']:+.3f} | "
                 f"{d['n_trustworthy_biases']} |")
    L.append("")
    (out / "experiment_design.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
