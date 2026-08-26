#!/usr/bin/env python
"""
Quantify the identifiability of doping recovery from terminal I--V.

The repository has always *stated* that recovering a doping profile from
terminal I--V is ill-posed. This script measures it: it differentiates the
Scharfetter--Gummel oracle, takes the SVD of the forward Jacobian, and reports
how many profile degrees of freedom an I--V sweep can actually determine at a
given measurement noise -- plus how much a better instrument would buy.

Everything is measured through the SG solver, so the result characterises the
drift--diffusion physics rather than any particular trained surrogate.

The analysis validates itself in three ways:

1. **Analysis-convergence study.** The Jacobian is re-estimated at several
   finite-difference steps and oracle signal-to-noise thresholds. A conclusion
   that moves when the estimator improves is an artefact, not a result.
2. **Spectral floor.** Singular values below the noise induced by the
   finite-difference estimate itself are reported as unresolvable rather than
   as measurements.
3. **Linear-response check.** The predicted response ||J v|| along each
   singular direction is compared against an independent re-solve of the
   perturbed device.

Usage
-----
    PYTHONPATH=src python scripts/run_identifiability.py [--out DIR] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bayespinn_inv.inverse.charts import ChartL
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    equivalence_perturbation,
    sg_forward_jacobian,
    symlog,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.utils.provenance import RunManifest

DOMAIN = (0.0, 1e-6)
N_ANCHOR = 16
NOISE_GRID = [0.20, 0.10, 0.05, 0.02, 0.01, 1e-3, 1e-4, 1e-6]


def build_devices(xa: np.ndarray):
    """The device families the project actually claims to invert."""
    xj = 0.5 * DOMAIN[1]
    return {
        "step_symmetric": np.where(xa < xj, -1e22, 1e22),
        "step_asymmetric": np.where(xa < xj, -1e21, 5e22),
        "graded": 1e22 * np.tanh((xa - xj) / 1.5e-7),
        "ldd": np.where(xa < 0.35e-6, -1e22,
                        np.where(xa < 0.6e-6, 5e21, 5e23)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs/identifiability")
    ap.add_argument("--quick", action="store_true",
                    help="single device, coarse settings (smoke test)")
    ap.add_argument("--v-max", type=float, default=0.9)
    ap.add_argument("--n-bias", type=int, default=19)
    ap.add_argument("--grid", type=int, default=301)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(np.float64(DOMAIN[1] - DOMAIN[0])))
    oracle = ScharfetterGummel1D(Grid1D.uniform(L_s, args.grid), scaling,
                                 SILICON, SGConfig())
    xa = np.linspace(DOMAIN[0], DOMAIN[1], N_ANCHOR)
    biases = np.linspace(0.0, args.v_max, args.n_bias)

    devices = build_devices(xa)
    if args.quick:
        devices = {"step_symmetric": devices["step_symmetric"]}

    cfg = dict(domain_si=list(DOMAIN), n_anchor=N_ANCHOR,
               biases=[float(b) for b in biases], sg_grid=args.grid,
               noise_grid=NOISE_GRID)
    man = RunManifest.create("identifiability", config=cfg, seed=0, notes=__doc__)

    report_json = {}

    # CHART-01 (generation 8). N_ANCHOR = 16 coordinates reach a 301-node solver.
    # Until g8 the solver resampled them silently and that choice -- piecewise
    # linear in the signed value, on normalised node index -- was the chart every
    # number below is measured in, unnamed. It is named now, and it is the only
    # thing that changed: chart L reconstructs with the operator the solver used
    # to apply, pinned byte-for-byte by tests/test_one_reconstruction_g8.py.
    chart = ChartL(N_ANCHOR, scaling.x_to_si(np.asarray(oracle.grid.x)))
    cfg["chart"] = chart.label()

    # -- 1. analysis-convergence study on the reference device --------------
    print("=" * 74)
    print("ANALYSIS-CONVERGENCE STUDY (is the conclusion an artefact of the")
    print("finite-difference estimator?)")
    print("=" * 74)
    settings = [(1e4, 0.01), (1e6, 0.01), (1e6, 0.03), (1e7, 0.03)]
    if not args.quick:
        settings.append((1e8, 0.05))
    conv = []
    ref = devices["step_symmetric"]
    print(f"{'min_snr':>9} {'step':>6} {'rows':>5} {'eta':>10} {'floor':>10}"
          f" {'resolv':>7} {'ident@2%':>9} {'s1/s2':>8}")
    for snr, step in settings:
        J, I_ref, kept, eta = sg_forward_jacobian(
            oracle, ref, biases, rel_step=step, min_snr=snr, chart=chart)
        rep = analyse_identifiability(J, noise_rel=0.02, jacobian_noise=eta)
        s = rep.singular_values
        row = dict(min_snr=snr, rel_step=step, n_rows=len(kept),
                   entry_noise=eta, spectral_floor=rep.spectral_floor,
                   resolvable_rank=rep.resolvable_rank,
                   identifiable_rank=rep.identifiable_rank,
                   sigma_ratio_1_2=float(s[1] / max(s[2], 1e-300)))
        conv.append(row)
        print(f"{snr:9.0e} {step:6.2f} {len(kept):5d} {eta:10.2e}"
              f" {rep.spectral_floor:10.2e} {rep.resolvable_rank:7d}"
              f" {rep.identifiable_rank:9d} {row['sigma_ratio_1_2']:8.2f}")
    report_json["analysis_convergence"] = conv
    best_snr, best_step = settings[-1]

    # -- 2. per-device spectra ---------------------------------------------
    per_device = {}
    for name, C in devices.items():
        print()
        print("=" * 74)
        print(f"DEVICE: {name}")
        print("=" * 74)
        # Adaptive SNR threshold: use the strictest level this device can
        # actually support. Devices with lower currents (e.g. a lightly-doped
        # p-side) sit closer to the oracle's noise floor at every bias. We log
        # the level used and the rows dropped -- silently relaxing the
        # threshold would make the spectra incomparable across devices.
        J = None
        for snr_try in (best_snr, 1e7, 1e6, 1e5, 1e4):
            try:
                J, I_ref, kept, eta = sg_forward_jacobian(
                    oracle, C, biases, rel_step=best_step, min_snr=snr_try,
                    chart=chart)
            except ValueError:
                continue
            if len(kept) >= 6:
                break
        if J is None or len(kept) < 4:
            print("  SKIPPED: fewer than 4 bias points clear the oracle noise"
                  " floor for this device.")
            per_device[name] = {"error": "insufficient trustworthy bias points"}
            continue
        if snr_try != best_snr:
            print(f"  NOTE: relaxed min_snr {best_snr:.0e} -> {snr_try:.0e};"
                  f" this device's currents sit closer to the oracle floor.")
        print(f"  using {len(kept)}/{len(biases)} bias points"
              f" (min_snr={snr_try:.0e}, step={best_step})")
        rep = analyse_identifiability(J, noise_rel=0.02, jacobian_noise=eta)
        print(rep.summary())

        # linear-response validation against an independent re-solve
        Bk = biases[kept]

        # ruff B023: `Bk` is late-bound but `iv` is only called within
        # this iteration, so it always sees the intended value.
        def iv(Cp):
            prev, o = None, []
            for V in Bk:  # noqa: B023
                st = oracle.solve(chart.on_grid_signed(Cp), float(V),
                                  initial_state=prev)
                prev = st
                o.append(st.terminal_current)
            return np.asarray(o)

        s0 = symlog(iv(C))
        checks = []
        for k in range(min(4, rep.resolvable_rank)):
            v = rep.directions[:, k]
            a = 0.01
            vv = a * v / np.linalg.norm(v)
            pred = float(np.linalg.norm(J @ vv))
            Cp = np.sign(C) * np.abs(C) * 10.0 ** vv
            act = float(np.linalg.norm(symlog(iv(Cp)) - s0))
            checks.append(dict(direction=k, predicted=pred, actual=act,
                               ratio=act / max(pred, 1e-300)))
        print("  linear-response validation (a = 0.01 decades):")
        for c in checks:
            print(f"    dir {c['direction']}: ||J v|| = {c['predicted']:.4e}"
                  f"   actual = {c['actual']:.4e}   ratio = {c['ratio']:.3f}")

        rank_curve = rep.rank_vs_noise(NOISE_GRID)
        print("  identifiable dof vs measurement noise:")
        for nl, r in rank_curve:
            print(f"    {nl:9.5%} -> {r:2d} / {rep.n_parameters}")

        per_device[name] = dict(
            min_snr_used=float(snr_try),
            rel_step=float(best_step),
            n_observations=rep.n_observations,
            n_parameters=rep.n_parameters,
            biases_used=[float(biases[k]) for k in kept],
            entry_noise=eta,
            spectral_floor=rep.spectral_floor,
            resolvable_rank=rep.resolvable_rank,
            identifiable_rank_at_2pct=rep.identifiable_rank,
            singular_values=[float(x) for x in rep.singular_values],
            parameter_sensitivity=[float(x) for x in rep.parameter_sensitivity()],
            rank_vs_noise=[[float(a), int(b)] for a, b in rank_curve],
            linear_response_check=checks,
        )

        # -- 3. equivalence class: a device you cannot tell apart -----------
        try:
            twin = equivalence_perturbation(rep, C, decades=0.1, mode="least")
            dI = np.max(np.abs(iv(twin) - iv(C)) / np.abs(iv(C)))
            dprof = float(np.max(np.abs(np.log10(np.abs(twin) / np.abs(C)))))
            per_device[name]["equivalence_twin"] = dict(
                profile_max_decades=dprof, iv_max_rel_change=float(dI),
                distinguishable_at_2pct=bool(dI > 0.02))
            print(f"  equivalence twin: profile differs by up to"
                  f" {dprof:.3f} decades ({10 ** dprof:.2f}x),"
                  f" I-V by {dI:.4%}"
                  f" -> distinguishable at 2% noise: {dI > 0.02}")
        except ValueError as exc:
            per_device[name]["equivalence_twin"] = {"error": str(exc)}

    report_json["devices"] = per_device
    for k, v in per_device.items():
        man.add_result(f"{k}_identifiable_rank_at_2pct",
                       v["identifiable_rank_at_2pct"])

    path = out / "identifiability.json"
    path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    man.add_artifact("identifiability_json", path)
    man.write(out)
    print()
    print(f"Wrote {path} and {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
