#!/usr/bin/env python
"""
Train a forward PINN (single member or full ensemble).

Usage::

    python scripts/train.py                                 # default config
    python scripts/train.py training.n_epochs=1000          # override
    python scripts/train.py --config-name train_smoke       # smoke run

Outputs go to ``cfg.out_dir`` and include per-member checkpoints,
training history JSON, and a ``manifest.json`` describing the run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import torch

# Optional hydra integration — fall back to a simple YAML loader if hydra
# isn't installed (keeps the script usable in minimal environments).
try:
    import hydra
    from omegaconf import OmegaConf, DictConfig
    _HAS_HYDRA = True
except ImportError:
    _HAS_HYDRA = False


from bayespinn_inv.physics.constants import SILICON, GAAS, Material
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.network import SemiconductorPINN, PINNConfig
from bayespinn_inv.training.trainer import PINNTrainer, TrainConfig
from bayespinn_inv.data.datasets import build_dataset


def _material_from_name(name: str) -> Material:
    lookup = {"Si": SILICON, "GaAs": GAAS, "Silicon": SILICON}
    if name not in lookup:
        raise ValueError(f"Unknown material: {name!r}. "
                          f"Available: {list(lookup.keys())}")
    return lookup[name]


def train_one(member_seed: int, cfg, out_dir: Path) -> Path:
    """Train one ensemble member; return the path to its final checkpoint."""
    material = _material_from_name(cfg["material"]["name"])
    scaling = Scaling.for_material(material, T=cfg["material"]["T"])
    L_scaled = float(scaling.x_to_scaled(
        torch.tensor(cfg["domain_si"][1] - cfg["domain_si"][0])))
    V_a_max_scaled = float(cfg["dataset"]["bias_range"][1]) / scaling.V_T

    net_cfg = PINNConfig(
        in_dim=cfg["network"]["in_dim"],
        hidden_dim=cfg["network"]["hidden_dim"],
        num_blocks=cfg["network"]["num_blocks"],
        fourier_features=cfg["network"]["fourier_features"],
        fourier_sigma=cfg["network"]["fourier_sigma"],
        dropout=cfg["network"]["dropout"],
        doping_dim=cfg["network"]["doping_dim"],
        output_dim=cfg["network"]["output_dim"],
        seed=member_seed,
        x_scaled_extent=L_scaled,
        V_a_scaled_extent=V_a_max_scaled,
    )
    net = SemiconductorPINN(net_cfg)
    print(f"[member seed={member_seed}] params={net.num_parameters():,}")

    examples, _samples = build_dataset(
        n_per_family=dict(cfg["dataset"]["n_per_family"]),
        n_points=cfg["dataset"]["n_points"],
        domain_si=tuple(cfg["domain_si"]),
        scaling=scaling,
        n_anchor=cfg["network"]["doping_dim"],
        bias_range=tuple(cfg["dataset"]["bias_range"]),
        seed=member_seed,
    )

    member_dir = out_dir / f"member_{member_seed:03d}"
    member_dir.mkdir(parents=True, exist_ok=True)
    tcfg = TrainConfig(
        lr=cfg["training"]["lr"],
        n_epochs=cfg["training"]["n_epochs"],
        batch_size=cfg["training"]["batch_size"],
        optimizer=cfg["training"]["optimizer"],
        grad_clip=cfg["training"]["grad_clip"],
        seed=member_seed,
        curriculum_epochs=cfg["training"]["curriculum_epochs"],
        bias_min=cfg["training"]["bias_min"],
        bias_max=cfg["training"]["bias_max"],
        use_ntk_weights=cfg["training"]["use_ntk_weights"],
        adaptive_weight_every=cfg["training"]["adaptive_weight_every"],
        ntk_alpha=cfg["training"]["ntk_alpha"],
        domain_si=tuple(cfg["domain_si"]),
        log_every=cfg["training"]["log_every"],
        ckpt_every=cfg["training"]["ckpt_every"],
        out_dir=str(member_dir),
    )
    trainer = PINNTrainer(net, scaling, material, examples, tcfg,
                            device=cfg["device"])
    trainer.train()
    return member_dir / "ckpt_final.pt"


def main_from_dict(cfg: dict) -> None:
    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    # Determine ensemble member seeds
    M = cfg["ensemble"]["M"]
    base_seed = cfg["seed"]
    member_seeds = (cfg["ensemble"].get("member_seeds")
                     or list(range(base_seed, base_seed + M)))
    ckpts = []
    for s in member_seeds:
        ck = train_one(s, cfg, out_dir)
        ckpts.append(str(ck))
    # Save manifest
    manifest = {
        "config": cfg,
        "member_seeds": member_seeds,
        "checkpoints": ckpts,
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\nTraining complete. Manifest: {out_dir / 'manifest.json'}")


if _HAS_HYDRA:
    @hydra.main(version_base=None,
                config_path="../configs", config_name="train_base")
    def main(cfg: DictConfig) -> None:
        main_from_dict(OmegaConf.to_container(cfg, resolve=True))
else:
    def main():  # pragma: no cover
        # Minimal fallback: read configs/train_base.yaml with PyYAML.
        import argparse, yaml
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/train_base.yaml")
        args = ap.parse_args()
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
        main_from_dict(cfg)


if __name__ == "__main__":
    main()
