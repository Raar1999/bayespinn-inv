#!/usr/bin/env python
"""Train a PINN with SWAG (Stochastic Weight Averaging-Gaussian) posterior.

Two-phase training:
  Phase 1: standard training to warm-start (uses ``training.n_epochs`` from config)
  Phase 2: SWA phase at a constant learning rate ``swag_lr``, during which
           a :class:`SWAGRecorder` collects K=swag_K parameter snapshots.

The final output contains:
  - ``manifest.json``  (compatible with ``run_calibration.py``)
  - ``member_000/ckpt_final.pt``      (the SWA *mean* network)
  - ``swag_recorder.pt``              (the SWAGRecorder with theta_bar, theta2_bar, D_dev)

Usage::

    python scripts/train_swag.py \\
        --config configs/train_base.yaml \\
        --swag_epochs 30 \\
        --swag_K 20 \\
        --swag_lr 5e-4 \\
        --out_dir outputs/swag/
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.bayesian.swag import SWAGConfig, SWAGRecorder
from bayespinn_inv.data.datasets import build_dataset
from bayespinn_inv.physics.constants import GAAS, SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.training.trainer import PINNTrainer, TrainConfig


def _material(name: str):
    return {"Si": SILICON, "Silicon": SILICON, "GaAs": GAAS}[name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/train_base.yaml")
    ap.add_argument("--swag_epochs", type=int, default=30,
                    help="Number of SWA-phase epochs (after warm-start)")
    ap.add_argument("--swag_K", type=int, default=20,
                    help="Rank of low-rank deviation matrix")
    ap.add_argument("--swag_lr", type=float, default=5e-4,
                    help="Constant LR during SWA phase")
    ap.add_argument("--collect_every", type=int, default=1,
                    help="Collect a snapshot every N SWA epochs")
    ap.add_argument("--out_dir", default=None)
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if args.out_dir is not None:
        cfg["out_dir"] = args.out_dir

    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    member_dir = out_dir / "member_000"
    member_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- Phase 1: warm-start training ----------------
    material = _material(cfg["material"]["name"])
    scaling = Scaling.for_material(material, T=cfg["material"]["T"])
    L_scaled = float(scaling.x_to_scaled(
        torch.tensor(cfg["domain_si"][1] - cfg["domain_si"][0])))
    V_a_max = float(cfg["dataset"]["bias_range"][1]) / scaling.V_T
    net_cfg = PINNConfig(
        in_dim=cfg["network"]["in_dim"],
        hidden_dim=cfg["network"]["hidden_dim"],
        num_blocks=cfg["network"]["num_blocks"],
        fourier_features=cfg["network"]["fourier_features"],
        fourier_sigma=cfg["network"]["fourier_sigma"],
        dropout=cfg["network"]["dropout"],
        doping_dim=cfg["network"]["doping_dim"],
        output_dim=cfg["network"]["output_dim"],
        seed=cfg["seed"],
        x_scaled_extent=L_scaled,
        V_a_scaled_extent=V_a_max,
    )
    net = SemiconductorPINN(net_cfg)
    print(f"SWAG training: warm-start phase ({cfg['training']['n_epochs']} epochs), "
          f"then SWA phase ({args.swag_epochs} epochs)")

    examples, _ = build_dataset(
        n_per_family=dict(cfg["dataset"]["n_per_family"]),
        n_points=cfg["dataset"]["n_points"],
        domain_si=tuple(cfg["domain_si"]),
        scaling=scaling,
        n_anchor=cfg["network"]["doping_dim"],
        bias_range=tuple(cfg["dataset"]["bias_range"]),
        seed=cfg["seed"],
    )

    tcfg = TrainConfig(
        lr=cfg["training"]["lr"],
        n_epochs=cfg["training"]["n_epochs"],
        batch_size=cfg["training"]["batch_size"],
        optimizer=cfg["training"]["optimizer"],
        grad_clip=cfg["training"]["grad_clip"],
        seed=cfg["seed"],
        curriculum_epochs=cfg["training"]["curriculum_epochs"],
        bias_min=cfg["training"]["bias_min"],
        bias_max=cfg["training"]["bias_max"],
        use_ntk_weights=cfg["training"]["use_ntk_weights"],
        adaptive_weight_every=cfg["training"]["adaptive_weight_every"],
        ntk_alpha=cfg["training"]["ntk_alpha"],
        domain_si=tuple(cfg["domain_si"]),
        log_every=cfg["training"]["log_every"],
        ckpt_every=10**9,
        out_dir=str(member_dir),
    )
    trainer = PINNTrainer(net, scaling, material, examples, tcfg)
    t0 = time.time()
    trainer.train()
    print(f"Phase 1 done in {time.time() - t0:.1f}s, "
          f"loss = {trainer.history[-1]['loss_total']:.3e}")

    # ---------------- Phase 2: SWA collection ----------------
    swag_cfg = SWAGConfig(max_rank=args.swag_K, T_samples=30)
    recorder = SWAGRecorder(net, swag_cfg)
    # Switch optimizer to constant LR
    for g in trainer.opt.param_groups:
        g["lr"] = args.swag_lr
    print(f"\nPhase 2: SWA collection, lr={args.swag_lr}, K={args.swag_K}")
    t0 = time.time()
    for swa_epoch in range(args.swag_epochs):
        # Train one epoch's worth of steps. We reuse trainer._compute_loss
        # to keep the loss aligned with phase 1.
        for _ in range(max(1, cfg["training"]["batch_size"] // 64)):
            ex = trainer._draw_example()
            loss, _ = trainer._compute_loss(ex, V_max_curr=tcfg.bias_max)
            trainer.opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), tcfg.grad_clip)
            trainer.opt.step()
        if (swa_epoch + 1) % args.collect_every == 0:
            recorder.collect()
        if (swa_epoch + 1) % 5 == 0:
            print(f"  SWA epoch {swa_epoch + 1}/{args.swag_epochs}: "
                  f"loss={loss.item():.3e}, snapshots={recorder.n_collected}")
    print(f"Phase 2 done in {time.time() - t0:.1f}s, "
          f"collected {recorder.n_collected} snapshots")

    # Save: SWA-mean network + recorder
    # First load the running mean into the network so ckpt_final.pt is the SWA mean
    from bayespinn_inv.bayesian.swag import _unflatten_params
    orig = torch.cat([p.detach().reshape(-1) for p in net.parameters()])
    _unflatten_params(recorder.theta_bar, net)
    torch.save({
        "model_state": net.state_dict(),
        "cfg": cfg, "swag_K": args.swag_K, "swag_epochs": args.swag_epochs,
        "history": trainer.history,
    }, member_dir / "ckpt_final.pt")
    torch.save(recorder, out_dir / "swag_recorder.pt")
    _unflatten_params(orig, net)   # restore (not strictly needed)

    manifest = {
        "config": cfg,
        "member_seeds": [cfg["seed"]],
        "checkpoints":  [str(member_dir / "ckpt_final.pt")],
        "swag_recorder": str(out_dir / "swag_recorder.pt"),
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\nDone -> {out_dir}")
    print(f"  manifest: {out_dir / 'manifest.json'}")
    print(f"  recorder: {out_dir / 'swag_recorder.pt'}")


if __name__ == "__main__":
    main()
