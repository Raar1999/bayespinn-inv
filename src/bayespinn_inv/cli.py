"""
Command-line interface for the installed package.

Scope note
----------
``pyproject.toml`` previously declared three console scripts --
``bayespinn-train``, ``bayespinn-inverse``, ``bayespinn-al`` -- pointing at
``bayespinn_inv.scripts.*``. That package does not exist: those launchers live
in a top-level ``scripts/`` directory that is not part of the wheel, so all
three entry points failed on any clean install (AUDIT_MASTER PKG-01).

Rather than package the repo-level experiment launchers (which depend on
``configs/*.yaml`` and on repository paths, and are genuinely repo tools, not
library tools), this module exposes the subcommands the *library* can support
standalone. The experiment launchers remain available in a checkout via
``make`` or ``python scripts/<name>.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

import numpy as np

from . import __version__


def _oracle(grid_n: int = 301, length: float = 1e-6):
    from .physics.constants import SILICON
    from .physics.scaling import Scaling
    from .solvers.scharfetter_gummel import Grid1D, ScharfetterGummel1D, SGConfig

    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(np.float64(length)))
    return ScharfetterGummel1D(Grid1D.uniform(L_s, grid_n), scaling, SILICON,
                               SGConfig()), scaling


def cmd_info(args: argparse.Namespace) -> int:
    """Print environment and provenance -- what a bug report should contain."""
    from .utils.provenance import environment_info, git_commit, git_is_dirty

    payload = {
        "bayespinn_inv": __version__,
        "git_commit": git_commit(),
        "git_dirty": git_is_dirty(),
        "environment": environment_info(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_iv(args: argparse.Namespace) -> int:
    """Solve a PN-diode I--V with the reference solver and report trust flags."""
    sg, scaling = _oracle(args.grid, args.length)
    x = scaling.x_to_si(np.asarray(sg.grid.x))
    doping = np.where(x < x.max() / 2, -args.na, args.nd)
    biases = np.linspace(args.v_min, args.v_max, args.n_bias)

    rows, prev = [], None
    print(f"{'V (V)':>8} {'I (A/m^2)':>16} {'noise floor':>13} {'SNR':>10}"
          f" {'trust':>6} {'conv':>6}")
    for V in biases:
        st = sg.solve(doping, float(V), initial_state=prev)
        prev = st
        floor = st.current_noise_floor
        snr = abs(st.terminal_current) / max(floor, 1e-300)
        rows.append(dict(bias=float(V), current=st.terminal_current,
                         noise_floor=floor, snr=snr,
                         trustworthy=st.current_is_trustworthy(),
                         converged=st.converged))
        print(f"{V:8.3f} {st.terminal_current:16.6e} {floor:13.3e} {snr:10.2e}"
              f" {st.current_is_trustworthy()!s:>6} {st.converged!s:>6}")

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rows, fh, indent=2)
        print(f"\nwrote {args.json}")
    return 0


def cmd_identifiability(args: argparse.Namespace) -> int:
    """How many doping degrees of freedom does an I--V sweep determine?"""
    from .inverse.identifiability import (
        analyse_identifiability,
        sg_forward_jacobian,
    )

    sg, scaling = _oracle(args.grid, args.length)
    xa = np.linspace(0.0, args.length, args.n_anchor)
    doping = np.where(xa < args.length / 2, -args.na, args.nd)
    biases = np.linspace(0.0, args.v_max, args.n_bias)

    J, I_ref, kept, eta = sg_forward_jacobian(
        sg, doping, biases, rel_step=args.step, min_snr=args.min_snr)
    rep = analyse_identifiability(J, noise_rel=args.noise,
                                  jacobian_noise=eta)
    print(f"bias points used: {len(kept)}/{len(biases)}"
          f" (SNR > {args.min_snr:g} against the solver's own noise floor)")
    print(rep.summary())
    print("\nidentifiable dof vs measurement noise:")
    for nl, r in rep.rank_vs_noise([0.2, 0.1, 0.05, 0.02, 0.01, 1e-3, 1e-4]):
        print(f"  {nl:9.5%} -> {r:2d} / {rep.n_parameters}")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    """Physics self-check: does the installed package reproduce known physics?"""
    import math

    from .physics.constants import SILICON

    sg, scaling = _oracle(301, 1e-6)
    x = scaling.x_to_si(np.asarray(sg.grid.x))
    N_A = N_D = 1e22
    doping = np.where(x < x.max() / 2, -N_A, N_D)

    ok = True

    st = sg.solve(doping, 0.0)
    V_bi = float(st.phi[-1] - st.phi[0])
    V_bi_exact = scaling.V_T * math.log(N_A * N_D / SILICON.n_i ** 2)
    err = abs(V_bi - V_bi_exact) / V_bi_exact
    ok &= err < 1e-4
    print(f"[{'PASS' if err < 1e-4 else 'FAIL'}] built-in potential"
          f"  {V_bi:.6f} V vs analytic {V_bi_exact:.6f} V  (rel {err:.2e})")

    ratio = (st.n / scaling.n_star) * (st.p / scaling.n_star)
    ma = float(np.max(np.abs(ratio - 1.0)))
    ok &= ma < 1e-4
    print(f"[{'PASS' if ma < 1e-4 else 'FAIL'}] mass action n p = n_i^2"
          f"  max deviation {ma:.2e}")

    ok &= st.converged
    print(f"[{'PASS' if st.converged else 'FAIL'}] equilibrium solve converged")

    eq_ok = not st.current_is_trustworthy()
    ok &= eq_ok
    print(f"[{'PASS' if eq_ok else 'FAIL'}] equilibrium current correctly"
          f" flagged as below the noise floor")

    prev, I, V = None, [], np.linspace(0.25, 0.5, 8)
    for v in V:
        s = sg.solve(doping, float(v), initial_state=prev)
        prev = s
        I.append(s.terminal_current)
    slope = np.polyfit(V, np.log10(np.abs(I)), 1)[0]
    n_ideal = 1.0 / (slope * scaling.V_T * math.log(10))
    ideal_ok = 0.95 < n_ideal < 1.15
    ok &= ideal_ok
    print(f"[{'PASS' if ideal_ok else 'FAIL'}] diode ideality factor"
          f"  {n_ideal:.4f}  (expected ~1)")

    mono = bool(np.all(np.diff(I) > 0))
    ok &= mono
    print(f"[{'PASS' if mono else 'FAIL'}] I(V) monotonically increasing")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bayespinn",
        description="BayesPINN-Inv: drift-diffusion reference solver, "
                    "differentiable surrogate, and identifiability analysis.")
    ap.add_argument("--version", action="version",
                    version=f"bayespinn-inv {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("info", help="print version, git commit and environment")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("selftest", help="physics self-check of the install")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("iv", help="solve a PN-diode I-V with the SG oracle")
    p.add_argument("--na", type=float, default=1e22, help="acceptor density m^-3")
    p.add_argument("--nd", type=float, default=1e22, help="donor density m^-3")
    p.add_argument("--length", type=float, default=1e-6, help="device length m")
    p.add_argument("--grid", type=int, default=301)
    p.add_argument("--v-min", type=float, default=0.0)
    p.add_argument("--v-max", type=float, default=0.6)
    p.add_argument("--n-bias", type=int, default=13)
    p.add_argument("--json", default=None, help="write results to this path")
    p.set_defaults(func=cmd_iv)

    p = sub.add_parser("identifiability",
                       help="how many doping dof does an I-V sweep determine?")
    p.add_argument("--na", type=float, default=1e22)
    p.add_argument("--nd", type=float, default=1e22)
    p.add_argument("--length", type=float, default=1e-6)
    p.add_argument("--grid", type=int, default=301)
    p.add_argument("--n-anchor", type=int, default=16)
    p.add_argument("--v-max", type=float, default=0.9)
    p.add_argument("--n-bias", type=int, default=19)
    p.add_argument("--noise", type=float, default=0.02,
                   help="relative measurement noise")
    p.add_argument("--step", type=float, default=0.05,
                   help="finite-difference step, decades of doping")
    p.add_argument("--min-snr", type=float, default=1e8,
                   help="reject bias points below this oracle SNR")
    p.set_defaults(func=cmd_identifiability)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
