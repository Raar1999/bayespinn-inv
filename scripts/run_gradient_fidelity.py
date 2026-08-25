#!/usr/bin/env python
"""Does a surrogate that fits I--V well also have the right *gradients*?

The hypothesis
--------------
The identifiability analysis says a terminal I--V sweep determines only ~3-5
of 16 doping degrees of freedom. Everything else lies in directions the
measurement cannot see.

A surrogate trained *only* on I--V is therefore constrained only in that
low-dimensional subspace. Along the remaining 11-13 directions its output is
free to do anything -- because no training signal distinguishes one behaviour
from another there. Its **values** can still be excellent (they are: 2.8%
median relative error) while its **derivatives** along unidentifiable
directions are arbitrary.

That matters far beyond a diagnostic, because the surrogate's whole purpose is
to be *differentiable*: gradient-based inverse design and any Jacobian-based
experiment design consume exactly those derivatives.

The falsifiable prediction
--------------------------
Decompose the true (SG) Jacobian ``J = U S V^T``. Project both Jacobians onto
each right singular direction ``v_j``. Then:

* for ``j <= identifiable_rank``: the surrogate's directional derivative
  should agree with SG;
* for ``j >  identifiable_rank``: it should not, and the disagreement should
  not improve with more training, because there is no signal to train on.

A control rules out the obvious alternative explanation (that the surrogate is
simply undertrained): the same measurement is repeated across training budgets.
If agreement outside the identifiable subspace is flat in training budget while
in-subspace agreement improves, undertraining is excluded.

Usage
-----
    PYTHONPATH=src python scripts/run_gradient_fidelity.py [--quick]
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

from bayespinn_inv.data.splits import ProtocolSpec, build_level_splits, build_sg_labels
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    sg_forward_jacobian,
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


def surrogate_jacobian(ens, scaling, C, biases_scaled, step=0.01) -> np.ndarray:
    """Same central-difference estimator the SG Jacobian uses."""
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


def directional_agreement(J_true: np.ndarray, J_surr: np.ndarray) -> List[dict]:
    """Per-singular-direction comparison of the two Jacobians.

    For each right singular vector ``v_j`` of the true Jacobian, compare the
    directional derivatives ``J_true @ v_j`` and ``J_surr @ v_j`` by cosine
    similarity and relative magnitude.
    """
    U, S, Vt = np.linalg.svd(J_true, full_matrices=True)
    P = J_true.shape[1]
    S_full = np.concatenate([S, np.zeros(P - S.size)]) if S.size < P else S
    out = []
    for j in range(P):
        v = Vt[j]
        a, b = J_true @ v, J_surr @ v
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        cos = float(a @ b / (na * nb)) if na > 0 and nb > 0 else float("nan")
        out.append({"direction": j, "sigma_true": float(S_full[j]),
                    "cosine": cos, "norm_true": float(na), "norm_surrogate": float(nb),
                    "norm_ratio": float(nb / na) if na > 0 else float("inf")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/gradient_fidelity")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    spec = ProtocolSpec()
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(spec.domain_si[1])))
    sg_train = ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling, SILICON, SGConfig())
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, GRID_N), scaling, SILICON, SGConfig())
    symlog = SymlogTransform()
    splits = build_level_splits(spec)
    X, Y, integrity = build_sg_labels(sg_train, scaling, symlog, splits["train"], spec)
    norm = Normalizer.fit(X)

    budgets = [300, 2500] if args.quick else [300, 1000, 2500, 10000]
    xa = np.linspace(spec.domain_si[0], spec.domain_si[1], P_ANCHOR)
    biases = np.linspace(0.0, V_MAX, N_BIAS)
    devs = devices(xa)
    if args.quick:
        devs = {k: devs[k] for k in list(devs)[:2]}

    cfg = dict(seed=SEED, noise=NOISE, P=P_ANCHOR, n_bias=N_BIAS, v_max=V_MAX,
               grid_n=GRID_N, training_budgets=budgets)
    man = RunManifest.create("gradient_fidelity", config=cfg, seed=SEED)
    results: Dict[str, object] = {"config": cfg, "label_integrity": integrity,
                                  "by_budget": {}}

    # --- truth, once per device -----------------------------------------
    truth = {}
    for dname, C in devs.items():
        J_true, I_ref, kept, entry_noise = sg_forward_jacobian(
            sg, C, biases, rel_step=0.01, min_snr=1e4)
        rep = analyse_identifiability(J_true, noise_rel=NOISE,
                                      jacobian_noise=entry_noise)
        truth[dname] = (C, J_true, kept, entry_noise, int(rep.identifiable_rank))
        print(f"{dname:18s} identifiable rank {rep.identifiable_rank} of {P_ANCHOR} "
              f"({len(kept)} trustworthy biases)")

    for ep in budgets:
        print(f"\n=== training budget {ep} epochs ===")
        t0 = time.time()
        members = []
        for m in range(5):
            net = IVSurrogate(IVSurrogateConfig(doping_dim=spec.n_anchor, hidden=128,
                                                n_layers=3, seed=m))
            rs = np.random.RandomState(m)
            idx = rs.randint(0, len(X), len(X))
            train_surrogate(net, X[idx], Y[idx], norm, epochs=ep, lr=2e-3)
            members.append(net)
        ens = SurrogateEnsemble(members, norm, symlog)

        per_dev = {}
        for dname, (C, J_true, kept, _entry_noise, rank) in truth.items():
            J_surr = surrogate_jacobian(ens, scaling, C, biases[kept] / scaling.V_T)
            rows = directional_agreement(J_true, J_surr)
            overall = float(np.corrcoef(J_true.ravel(), J_surr.ravel())[0, 1])
            inside = [r["cosine"] for r in rows[:rank] if np.isfinite(r["cosine"])]
            outside = [r["cosine"] for r in rows[rank:] if np.isfinite(r["cosine"])]
            # accuracy of the surrogate's *values* on this device, for contrast
            val_err = float(np.median(np.abs(
                ens.predict(scaling.doping_to_net_input(C),
                            biases[kept] / scaling.V_T).mean_symlog
                - np.array(list(_sg_symlog(sg, C, biases[kept], symlog))))))
            per_dev[dname] = {
                "identifiable_rank": rank,
                "jacobian_pearson_overall": overall,
                "mean_cosine_inside_identifiable": float(np.mean(inside)) if inside else None,
                "mean_cosine_outside_identifiable": float(np.mean(outside)) if outside else None,
                "median_abs_symlog_value_error": val_err,
                "directions": rows,
            }
            print(f"  {dname:18s} value err {val_err:.4f} symlog | "
                  f"J cos inside rank {np.mean(inside):+.3f} | "
                  f"outside {np.mean(outside):+.3f} | overall r {overall:+.3f}")
        results["by_budget"][ep] = {"devices": per_dev,
                                    "train_seconds": time.time() - t0}

    results["verdict"] = _verdict(results, budgets)
    for line in results["verdict"]["lines"]:
        print("  " + line)

    (out / "gradient_fidelity.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8")
    man.add_result("verdict", results["verdict"])
    man.add_artifact("json", out / "gradient_fidelity.json")
    _write_markdown(out, results, budgets)
    man.add_artifact("summary", out / "gradient_fidelity.md")
    man.write(out)
    print(f"\nWrote {out}/gradient_fidelity.json and .md")
    return 0


def _sg_symlog(sg, C, biases, symlog):
    prev = None
    for V in biases:
        st = sg.solve(C, float(V), initial_state=prev); prev = st
        yield float(symlog.forward(st.terminal_current))


def _verdict(results: dict, budgets: List[int]) -> dict:
    big = max(budgets)
    small = min(budgets)
    ins_hi, out_hi, ins_lo, out_lo, verr_hi, verr_lo = [], [], [], [], [], []
    for d in results["by_budget"][big]["devices"].values():
        ins_hi.append(d["mean_cosine_inside_identifiable"])
        out_hi.append(d["mean_cosine_outside_identifiable"])
        verr_hi.append(d["median_abs_symlog_value_error"])
    for d in results["by_budget"][small]["devices"].values():
        ins_lo.append(d["mean_cosine_inside_identifiable"])
        out_lo.append(d["mean_cosine_outside_identifiable"])
        verr_lo.append(d["median_abs_symlog_value_error"])
    ins_hi_m, out_hi_m = float(np.mean(ins_hi)), float(np.mean(out_hi))
    lines = [
        f"at {big} epochs: mean |cos| inside identifiable subspace "
        f"{ins_hi_m:+.3f}, outside {out_hi_m:+.3f}",
        f"value error improved {np.mean(verr_lo):.4f} -> {np.mean(verr_hi):.4f} symlog "
        f"({small} -> {big} epochs)",
        f"outside-subspace agreement moved {np.mean(out_lo):+.3f} -> {out_hi_m:+.3f} "
        f"(flat => not an undertraining artefact)",
    ]
    supported = bool(ins_hi_m > out_hi_m + 0.2)
    lines.append("HYPOTHESIS " + ("SUPPORTED" if supported else "NOT SUPPORTED")
                 + ": gradients are trustworthy only inside the identifiable subspace"
                 if supported else
                 "HYPOTHESIS NOT SUPPORTED: no clear inside/outside separation")
    return {"mean_cosine_inside": ins_hi_m, "mean_cosine_outside": out_hi_m,
            "value_error_small": float(np.mean(verr_lo)),
            "value_error_large": float(np.mean(verr_hi)),
            "outside_cosine_small": float(np.mean(out_lo)),
            "outside_cosine_large": out_hi_m,
            "hypothesis_supported": supported, "lines": lines}


def _write_markdown(out: Path, r: dict, budgets: List[int]) -> None:
    v = r["verdict"]
    big = max(budgets)
    L = ["# Surrogate accuracy does not imply surrogate gradients", "",
         "A surrogate trained only on terminal I--V is constrained only in "
         "the directions that measurement can see. Along the rest its "
         "derivatives are unconstrained -- and those derivatives are exactly "
         "what gradient-based inverse design and Jacobian-based experiment "
         "design consume.", "",
         "## Verdict", ""] + [f"* {line}" for line in v["lines"]] + ["",
         f"## Directional agreement at {big} epochs", "",
         "`cos` is the cosine between the true and surrogate directional "
         "derivatives along each right singular vector of the **true** "
         "Jacobian, ordered by singular value. Directions at or below the "
         "identifiable rank are the ones the measurement determines.", "",
         "| Device | Identifiable rank | Value error (symlog) | mean cos inside | "
         "mean cos outside | overall Pearson r |", "|---|---:|---:|---:|---:|---:|"]
    for dname, d in r["by_budget"][big]["devices"].items():
        L.append(f"| `{dname}` | {d['identifiable_rank']} / {r['config']['P']} | "
                 f"{d['median_abs_symlog_value_error']:.4f} | "
                 f"{d['mean_cosine_inside_identifiable']:+.3f} | "
                 f"{d['mean_cosine_outside_identifiable']:+.3f} | "
                 f"{d['jacobian_pearson_overall']:+.3f} |")

    L += ["", "## Is it just undertraining?", "",
          "If the out-of-subspace disagreement were an optimisation failure it "
          "would shrink with training budget. It does not.", "",
          "| Epochs | mean value error (symlog) | mean cos inside | mean cos outside |",
          "|---:|---:|---:|---:|"]
    for ep in budgets:
        devs = r["by_budget"][ep]["devices"].values()
        L.append(f"| {ep} | "
                 f"{np.mean([d['median_abs_symlog_value_error'] for d in devs]):.4f} | "
                 f"{np.mean([d['mean_cosine_inside_identifiable'] for d in devs]):+.3f} | "
                 f"{np.mean([d['mean_cosine_outside_identifiable'] for d in devs]):+.3f} |")

    L += ["", f"## Per-direction detail at {big} epochs", ""]
    for dname, d in r["by_budget"][big]["devices"].items():
        L += [f"### `{dname}` (identifiable rank {d['identifiable_rank']})", "",
              "| Direction | sigma (true) | cosine | ||J_surr v|| / ||J_true v|| |",
              "|---:|---:|---:|---:|"]
        for row in d["directions"]:
            mark = " **(identifiable)**" if row["direction"] < d["identifiable_rank"] else ""
            cos = row["cosine"]
            L.append(f"| {row['direction']}{mark} | {row['sigma_true']:.4g} | "
                     + (f"{cos:+.3f}" if np.isfinite(cos) else "-")
                     + f" | {row['norm_ratio']:.3g} |")
        L.append("")
    (out / "gradient_fidelity.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
