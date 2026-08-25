#!/usr/bin/env python
"""Evidence for the forward-model decision: pure-physics PINN vs SG surrogate.

``docs/forward_model_reframe.md`` argues the pure-physics PINN cannot
reproduce diode I--V and was superseded by the SG-supervised surrogate. That
argument is sound but its numbers were measured against the *pre-audit*
solver, and the conclusion has since been inherited rather than re-measured.
``RELEASE_READINESS.md`` lists the PINN pipeline as "not release-grade,
exercised only by a 5-epoch smoke test".

Before deciding whether the PINN deserves further development, measure what
it currently delivers on the one quantity the project needs from a forward
model: **terminal current as a function of doping and bias**, against the
validated SG oracle, on the same devices and biases the surrogate is scored
on.

The comparison is deliberately generous to the PINN:

* it is trained for a real budget (not the 200-epoch smoke config),
* it is scored only on bias points the oracle itself certifies as
  trustworthy -- the same filter the surrogate gets,
* its own internal self-consistency diagnostic (the spread of J across the
  domain, which is zero for an exact steady state) is reported alongside, so
  a failure can be attributed to training rather than assumed.

Usage
-----
    PYTHONPATH=src python scripts/run_pinn_vs_surrogate.py [--epochs N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.data.datasets import DopingSample, make_training_example
from bayespinn_inv.data.splits import (
    ProtocolSpec,
    build_level_splits,
    build_sg_labels,
    oracle_iv,
    step_profile,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.forward_pinn import ForwardPINN, ForwardPINNConfig
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import Grid1D, ScharfetterGummel1D, SGConfig
from bayespinn_inv.surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SymlogTransform,
    train_surrogate,
)
from bayespinn_inv.training.trainer import PINNTrainer, TrainConfig
from bayespinn_inv.utils.provenance import RunManifest

SEED = 0
N_ANCHOR = 16


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/pinn_vs_surrogate")
    ap.add_argument("--epochs", type=int, default=8000, help="PINN training epochs")
    ap.add_argument("--surrogate-epochs", type=int, default=2500)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(SEED); np.random.seed(SEED)
    spec = ProtocolSpec()
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(spec.domain_si[1])))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling, SILICON, SGConfig())
    symlog = SymlogTransform()
    splits = build_level_splits(spec)
    xa = spec.anchor_x()
    biases = spec.biases
    VT = scaling.V_T

    cfg = dict(seed=SEED, pinn_epochs=args.epochs,
               surrogate_epochs=args.surrogate_epochs, n_anchor=N_ANCHOR)
    man = RunManifest.create("pinn_vs_surrogate", config=cfg, seed=SEED)
    results: Dict[str, object] = {"config": cfg}

    # ------------------------------------------------------- SG supervision
    print("SG labels (shared) ...")
    X, Y, integrity = build_sg_labels(sg, scaling, symlog, splits["train"], spec)
    results["label_integrity"] = integrity
    norm = Normalizer.fit(X)

    # ------------------------------------------------------- the surrogate
    print(f"Training SG-supervised surrogate ({args.surrogate_epochs} epochs) ...")
    t0 = time.time()
    members = []
    for m in range(5):
        net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=128,
                                            n_layers=3, seed=m))
        rs = np.random.RandomState(m)
        idx = rs.randint(0, len(X), len(X))
        train_surrogate(net, X[idx], Y[idx], norm, epochs=args.surrogate_epochs, lr=2e-3)
        members.append(net)
    ens = SurrogateEnsemble(members, norm, symlog)
    t_surr = time.time() - t0
    print(f"  {t_surr:.1f}s")

    # ------------------------------------------------------------ the PINN
    print(f"Training pure-physics PINN ({args.epochs} epochs) ...")
    pnet = SemiconductorPINN(PINNConfig(in_dim=2, hidden_dim=64, num_blocks=4,
                                        fourier_features=16, doping_dim=N_ANCHOR,
                                        output_dim=3, seed=SEED))
    x_dense = np.linspace(spec.domain_si[0], spec.domain_si[1], 128)
    examples = [
        make_training_example(
            DopingSample(family="step", x_si=x_dense,
                         doping_si=step_profile(x_dense, float(lv)),
                         params={"level": float(lv)}),
            scaling, spec.domain_si, N_ANCHOR,
            bias_range=(0.0, float(spec.bias_max)))
        for lv in splits["train"]
    ]
    tcfg = TrainConfig(n_epochs=args.epochs, batch_size=128, lr=1e-3,
                       curriculum_epochs=max(1, args.epochs // 2),
                       bias_min=0.0, bias_max=float(spec.bias_max),
                       log_every=max(1, args.epochs // 8),
                       ckpt_every=10 ** 9, out_dir=str(out / "pinn"))
    t0 = time.time()
    trainer = PINNTrainer(pnet, scaling, SILICON, examples, tcfg)
    trainer.train()
    t_pinn = time.time() - t0
    print(f"  {t_pinn:.1f}s")
    fwd = ForwardPINN(pnet, scaling, SILICON,
                      ForwardPINNConfig(n_anchor=N_ANCHOR,
                                        domain_si=spec.domain_si))

    # -------------------------------------------------------- head-to-head
    print("\nScoring both against the SG oracle on identical points ...")
    rows = {"pinn": [], "surrogate": []}
    divJ = []
    for lv in splits["test_interp"]:
        C = step_profile(xa, lv)
        I, trust = oracle_iv(sg, C, biases, spec.trust_snr)
        pred = ens.predict(scaling.doping_to_net_input(C), biases / VT)
        Cd = torch.tensor(np.interp(np.linspace(0, 1, N_ANCHOR),
                                    np.linspace(0, 1, len(C)), C),
                          dtype=torch.float32)
        _, I_pinn = fwd.iv_curve(Cd, [float(v) for v in biases])
        I_pinn = I_pinn.detach().numpy()
        for bi in range(len(biases)):
            if not trust[bi]:
                continue
            rows["surrogate"].append(abs(pred.mean_current[bi] - I[bi]) / abs(I[bi]))
            rows["pinn"].append(abs(I_pinn[bi] - I[bi]) / abs(I[bi]))
        st = fwd.solve(Cd, float(biases[-1]))
        Jt = st.J_total
        divJ.append(float(np.std(Jt) / max(abs(np.mean(Jt)), 1e-300)))

    summary = {}
    for k, v in rows.items():
        v = np.asarray(v)
        summary[k] = {"median_rel_err": float(np.median(v)),
                      "p90_rel_err": float(np.quantile(v, 0.9)),
                      "max_rel_err": float(v.max()), "n": int(v.size),
                      "frac_within_50pct": float(np.mean(v < 0.5))}
    summary["surrogate"]["train_seconds"] = t_surr
    summary["pinn"]["train_seconds"] = t_pinn
    summary["pinn"]["self_consistency_std_over_mean_J"] = {
        "median": float(np.median(divJ)), "max": float(np.max(divJ)),
        "note": "div(J)=0 in steady state, so std(J)/|mean(J)| is 0 for an "
                "exact solution. This is the PINN's own diagnostic, "
                "independent of the oracle.",
    }
    results["head_to_head"] = summary

    print(f"\n{'model':12s} {'median rel err':>15s} {'p90':>10s} "
          f"{'frac<50%':>9s} {'train s':>9s}")
    for k in ("surrogate", "pinn"):
        s = summary[k]
        print(f"{k:12s} {s['median_rel_err']:15.2%} {s['p90_rel_err']:10.2%} "
              f"{s['frac_within_50pct']:9.0%} {s['train_seconds']:9.1f}")
    sc = summary["pinn"]["self_consistency_std_over_mean_J"]
    print(f"\nPINN self-consistency std(J)/|mean(J)|: median {sc['median']:.2f}, "
          f"max {sc['max']:.2f}   (0 = exact steady state)")

    (out / "pinn_vs_surrogate.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8")
    man.add_result("head_to_head", summary)
    man.add_artifact("json", out / "pinn_vs_surrogate.json")
    man.write(out)
    print(f"\nWrote {out}/pinn_vs_surrogate.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
