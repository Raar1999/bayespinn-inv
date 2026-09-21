#!/usr/bin/env python
"""Train a PINN with dropout enabled, for MC-Dropout uncertainty.

This is a thin wrapper around ``scripts/train.py`` that forces
``network.dropout > 0`` and ``ensemble.M = 1`` (since MC-Dropout uses
test-time stochasticity to replace ensembling).

Usage::

    python scripts/train_mc_dropout.py \\
        --config configs/train_base.yaml \\
        --dropout 0.15 \\
        --out_dir outputs/mc_dropout/

The output directory will contain a single ``member_000/`` with
``ckpt_final.pt``, plus a ``manifest.json`` compatible with
``run_calibration.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from train import main_from_dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/train_base.yaml")
    ap.add_argument("--dropout", type=float, default=0.15,
                    help="Dropout probability (must be > 0 for MC-Dropout)")
    ap.add_argument("--out_dir", default=None,
                    help="Override cfg.out_dir from the config")
    args = ap.parse_args()

    if args.dropout <= 0:
        raise SystemExit("--dropout must be > 0 for MC-Dropout training")

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Force MC-Dropout-appropriate config
    cfg["network"]["dropout"] = args.dropout
    cfg["ensemble"]["M"] = 1
    if args.out_dir is not None:
        cfg["out_dir"] = args.out_dir
    print(f"MC-Dropout training: dropout={args.dropout}, "
          f"out_dir={cfg['out_dir']}")
    main_from_dict(cfg)


if __name__ == "__main__":
    main()
