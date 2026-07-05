#!/usr/bin/env python
"""Train an SG-supervised surrogate ensemble and save a loadable manifest.

The resulting ``manifest.json`` (type="surrogate") is consumed by the
pipeline scripts (run_inverse_sweep.py, run_calibration.py,
defect_case_study.py) via the auto-detecting ``load_forward_ensemble``.

Usage:
    python scripts/train_surrogate_ensemble.py --out outputs/surrogate_ensemble \\
        --M 5 --epochs 2500
"""
from __future__ import annotations
import argparse, time
from pathlib import Path
import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import ScharfetterGummel1D, Grid1D, SGConfig
from bayespinn_inv.surrogate import (
    SymlogTransform, Normalizer, IVSurrogate, IVSurrogateConfig,
    build_sg_dataset, train_surrogate, save_surrogate_ensemble,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/surrogate_ensemble")
    ap.add_argument("--M", type=int, default=5)
    ap.add_argument("--epochs", type=int, default=2500)
    ap.add_argument("--doping_dim", type=int, default=16)
    ap.add_argument("--bias_max", type=float, default=0.6)
    ap.add_argument("--n_levels", type=int, default=11)
    ap.add_argument("--include_graded", action="store_true", default=True)
    args = ap.parse_args()

    DOMAIN = (0.0, 1e-6)
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_scaled = float(scaling.x_to_scaled(torch.tensor(DOMAIN[1] - DOMAIN[0])))
    symlog = SymlogTransform(I0=1e-6)
    sg = ScharfetterGummel1D(Grid1D.uniform(L_scaled, 301), scaling, SILICON, SGConfig())
    biases = np.linspace(0.0, args.bias_max, 13)

    xa = np.linspace(*DOMAIN, args.doping_dim)
    def step_asym(NA, ND, xj): return np.where(xa < xj, -NA, ND).astype(float)
    def graded_asym(NA, ND, xj, w):
        from scipy.special import erf as _erf
        return (0.5*(ND-NA) + 0.5*(ND+NA)*_erf((xa-xj)/w)).astype(float)

    # Train on the SAME distribution the inverse parameterizations explore:
    # randomized ASYMMETRIC step + graded junctions over the valid doping
    # range, plus a symmetric backbone for coverage. The 16-anchor encoding
    # represents any profile, so the surrogate learns the full doping -> I-V map.
    rng = np.random.RandomState(0)
    C_LO, C_HI = 5e20, 5e22
    profiles = []
    levels = np.geomspace(C_LO, C_HI, args.n_levels)
    profiles += [step_asym(L, L, 0.5*DOMAIN[1]) for L in levels]        # symmetric backbone
    for _ in range(120):                                                # random asymmetric steps
        NA = 10**rng.uniform(np.log10(C_LO), np.log10(C_HI))
        ND = 10**rng.uniform(np.log10(C_LO), np.log10(C_HI))
        xj = rng.uniform(0.35, 0.65) * DOMAIN[1]
        profiles.append(step_asym(NA, ND, xj))
    for _ in range(60):                                                 # random graded
        NA = 10**rng.uniform(np.log10(C_LO), np.log10(C_HI))
        ND = 10**rng.uniform(np.log10(C_LO), np.log10(C_HI))
        xj = rng.uniform(0.4, 0.6) * DOMAIN[1]
        w = 10**rng.uniform(np.log10(8e-9), np.log10(4e-8))
        profiles.append(graded_asym(NA, ND, xj, w))

    print(f"Building SG dataset: {len(profiles)} profiles x {len(biases)} biases")
    t0 = time.time()
    X, Y = build_sg_dataset(profiles, biases, scaling, sg, symlog)
    norm = Normalizer.fit(X)
    print(f"  data {X.shape} in {time.time()-t0:.1f}s")

    members = []
    for m in range(args.M):
        net = IVSurrogate(IVSurrogateConfig(doping_dim=args.doping_dim,
                                            hidden=128, n_layers=3, seed=m))
        rs = np.random.RandomState(m); idx = rs.randint(0, len(X), len(X))
        train_surrogate(net, X[idx], Y[idx], norm, epochs=args.epochs, lr=2e-3)
        members.append(net)
        print(f"  member {m} trained")

    mpath = save_surrogate_ensemble(
        args.out, members, norm, scaling_name="Si", T=300.0,
        doping_dim=args.doping_dim, domain_si=DOMAIN,
        bias_range=(0.0, args.bias_max), symlog_I0=1e-6,
    )
    print(f"\nSaved surrogate ensemble manifest -> {mpath}")
    print("Use it with any pipeline script, e.g.:")
    print(f"  python scripts/run_inverse_sweep.py --ensemble {mpath} ...")


if __name__ == "__main__":
    main()
