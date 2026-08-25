#!/usr/bin/env python
"""Aggregate active-learning runs across seeds and strategies.

Given a directory containing per-run ``log.json`` files (as produced by
``scripts/active_learning.py``, organized as
``outputs/al/<strategy>_seed<n>/<strategy>/log.json``), compute the
per-round mean and 80% interval of the doping-recovery error for each
strategy.

The output ``aggregated.json`` has the structure::

    {
      "random": {
        "rounds": [1, 2, ...],
        "mean":   [...],
        "p10":    [...],
        "p90":    [...],
        "n_seeds": 10
      },
      "max_std": {...},
      "ucb":     {...}
    }

and a comparison figure ``convergence.png`` if matplotlib is available.

Usage::

    python scripts/aggregate_al.py outputs/al/ -o outputs/al_aggregated.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


def _find_log_files(root: Path):
    """Yield (strategy, seed, log_path) for every found log.json."""
    pattern = re.compile(r"(?P<strategy>random|max_std|ucb).*?seed[_=]?(?P<seed>\d+)",
                          re.IGNORECASE)
    for p in root.rglob("log.json"):
        # Try to extract (strategy, seed) from the path
        rel = p.relative_to(root)
        m = pattern.search(str(rel))
        if not m:
            # Fall back to active_learning.py layout: <root>/<strategy>/log.json
            # where strategy is the immediate parent and seed is in a grandparent
            parts = rel.parts
            if len(parts) >= 2:
                strategy = parts[-2]
                if strategy in ("random", "max_std", "ucb"):
                    # Default seed to a hash of the path so multiple runs in
                    # the same strategy dir don't collide silently
                    yield strategy, hash(str(rel)) % 10_000, p
            continue
        yield m.group("strategy").lower(), int(m.group("seed")), p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="Directory containing AL run outputs")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--metric", default="doping_error_relative",
                    help="Per-round metric to aggregate")
    args = ap.parse_args()

    root = Path(args.root)
    by_strategy = defaultdict(list)   # strategy -> list of per-seed value arrays
    seed_index = defaultdict(set)
    for strategy, seed, log_path in _find_log_files(root):
        with open(log_path, encoding="utf-8") as f:
            log = json.load(f)
        values = []
        for entry in log:
            if args.metric in entry:
                v = entry[args.metric]
                if isinstance(v, (int, float)) and np.isfinite(v):
                    values.append(float(v))
                else:
                    values.append(np.nan)
        if values:
            by_strategy[strategy].append(values)
            seed_index[strategy].add(seed)

    if not by_strategy:
        raise SystemExit(f"No AL logs found under {root}")

    aggregated = {}
    for strategy, runs in by_strategy.items():
        # Pad to the shortest run length (or could max-pad with NaN; we
        # truncate to keep the comparison fair across strategies)
        min_len = min(len(r) for r in runs)
        arr = np.stack([np.asarray(r[:min_len]) for r in runs])
        # ignore nan in stats
        mean = np.nanmean(arr, axis=0)
        p10  = np.nanquantile(arr, 0.10, axis=0)
        p90  = np.nanquantile(arr, 0.90, axis=0)
        aggregated[strategy] = {
            "metric":  args.metric,
            "rounds":  list(range(1, min_len + 1)),
            "mean":    mean.tolist(),
            "p10":     p10.tolist(),
            "p90":     p90.tolist(),
            "n_seeds": len(runs),
            "seeds":   sorted(seed_index[strategy]),
        }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2, default=str)
    print(f"Aggregated {sum(len(v) for v in by_strategy.values())} runs "
          f"across {len(by_strategy)} strategies -> {out_path}")
    for s, info in aggregated.items():
        print(f"  {s:10s}: {info['n_seeds']} seeds, {len(info['rounds'])} rounds, "
              f"final mean {args.metric} = {info['mean'][-1]:.4f}")

    # Optional figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5.0, 3.5))
        colors = {"random": "#949494", "max_std": "#0173B2", "ucb": "#DE8F05"}
        for s, info in aggregated.items():
            r = np.asarray(info["rounds"])
            mean = np.asarray(info["mean"])
            lo   = np.asarray(info["p10"])
            hi   = np.asarray(info["p90"])
            c = colors.get(s)
            ax.plot(r, mean, "o-", color=c, ms=4, label=f"{s} (n={info['n_seeds']})")
            ax.fill_between(r, lo, hi, color=c, alpha=0.18)
        ax.set_xlabel("AL round")
        ax.set_ylabel(args.metric.replace("_", " "))
        ax.set_yscale("log")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_path.with_suffix(".png"), dpi=200)
        print(f"  figure -> {out_path.with_suffix('.png')}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
