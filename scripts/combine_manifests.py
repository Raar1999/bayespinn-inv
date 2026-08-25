#!/usr/bin/env python
"""Combine per-member training manifests into a single ensemble manifest.

When training ensemble members in parallel (each via ``scripts/train.py``
with ``ensemble.M=1``), each run writes its own ``manifest.json``. The
inverse-design / AL / calibration launchers expect a single combined
manifest listing all members.

Usage::

    python scripts/combine_manifests.py outputs/ensemble/member_*/manifest.json \
        -o outputs/ensemble/manifest.json

The combined manifest preserves the training config of the first member
(they should all be identical except for the seed) and concatenates the
``member_seeds`` and ``checkpoints`` lists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+",
                    help="One or more per-member manifest.json paths")
    ap.add_argument("-o", "--out", required=True,
                    help="Path to write the combined manifest")
    ap.add_argument("--strict", action="store_true",
                    help="Fail if member configs differ (apart from seed)")
    args = ap.parse_args()

    manifests = []
    for p in args.manifests:
        with open(p, encoding="utf-8") as f:
            manifests.append((Path(p).parent, json.load(f)))

    if not manifests:
        raise SystemExit("No manifests provided.")

    # Use the first manifest's training config as the canonical config.
    canonical_cfg = manifests[0][1]["config"]
    combined_seeds = []
    combined_ckpts = []
    for member_dir, m in manifests:
        for s in m["member_seeds"]:
            if s in combined_seeds:
                raise SystemExit(f"Duplicate seed {s} across manifests "
                                 f"(at least one collision in {member_dir})")
            combined_seeds.append(s)
        for ck in m["checkpoints"]:
            # Rewrite to absolute if it's relative to the manifest's dir
            ck_path = Path(ck)
            if not ck_path.is_absolute():
                ck_path = (member_dir / ck_path).resolve()
            combined_ckpts.append(str(ck_path))
        # Strict mode: check configs agree except for seed
        if args.strict:
            other = dict(m["config"])
            base = dict(canonical_cfg)
            other.pop("seed", None); base.pop("seed", None)
            other.get("ensemble", {}).pop("member_seeds", None)
            base.get("ensemble", {}).pop("member_seeds", None)
            if other != base:
                raise SystemExit(
                    f"Config mismatch with first manifest at {member_dir} "
                    "(use --strict=false to override)"
                )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined = {
        "config": canonical_cfg,
        "member_seeds": combined_seeds,
        "checkpoints": combined_ckpts,
        "combined_from": [str(Path(p).resolve()) for p in args.manifests],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"Combined {len(manifests)} manifests "
          f"({len(combined_seeds)} members) -> {out_path}")


if __name__ == "__main__":
    main()
