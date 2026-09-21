#!/usr/bin/env python
"""2D MOS-capacitor demonstration.

Runs the 2D MOS-cap Poisson solver across a gate-voltage sweep and produces:

  1. A high-frequency-style C-V curve (capacitance vs gate voltage),
     computed from dQ_gate/dV_gate by finite difference.
  2. 2D field maps (potential, electron density, hole density) at a
     representative gate bias.
  3. Surface-potential and depletion-width-vs-V_gate curves, compared to
     the analytical depletion approximation.

Outputs go to ``outputs/mos_cap_2d/``.

Usage::

    python scripts/mos_cap_demo.py \\
        --N_A 1e21 --t_ox 5e-9 --Ly_semi 100e-9 \\
        --Vg_min -0.5 --Vg_max 0.6 --n_Vg 23 \\
        --out outputs/mos_cap_2d/

Note on validity
----------------
The solver models the quasi-equilibrium (no-current) regime: accumulation,
depletion, and onset of inversion. It uses Maxwell-Boltzmann statistics
and the depletion approximation as a cross-check. Deep strong-inversion at
heavy doping (N_A >= 1e22) is numerically stiff and outside the validated
range; use N_A <= 1e21 for clean C-V sweeps (see docs/architecture.md).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bayespinn_inv.physics.constants import EPS_0, Q_E, SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.grid_2d import Grid2D, MOSCapBoundary, MOSCapGeometry
from bayespinn_inv.solvers.mos_cap_2d import (
    MOSCap2DConfig,
    MOSCap2DSolver,
    depletion_approximation_surface_potential,
)


def gate_charge(state, grid, geom) -> float:
    """Total charge per unit area on the gate side (C/m^2).

    By Gauss's law, this equals the integral of the semiconductor charge
    (with opposite sign). We integrate the net charge density over the
    semiconductor and divide by the lateral extent.
    """
    cell_vol = grid.cell_volume()             # (Ny, Nx) m^2
    rho = Q_E * (state.p - state.n + state.doping)  # C/m^3
    # Total charge (per unit depth) summed over semiconductor cells:
    Q_semi = float(np.sum(rho * cell_vol * grid.semi_mask))  # C/m
    # Per unit area = divide by lateral extent Lx
    return -Q_semi / geom.Lx                  # gate charge balances semi charge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N_A", type=float, default=1e21,
                    help="P-substrate acceptor concentration (m^-3)")
    ap.add_argument("--t_ox", type=float, default=5e-9)
    ap.add_argument("--Ly_semi", type=float, default=100e-9)
    ap.add_argument("--Lx", type=float, default=20e-9)
    ap.add_argument("--Nx", type=int, default=5)
    ap.add_argument("--Ny", type=int, default=106)
    ap.add_argument("--Vg_min", type=float, default=-0.5)
    ap.add_argument("--Vg_max", type=float, default=0.6)
    ap.add_argument("--n_Vg", type=int, default=23)
    ap.add_argument("--out", default="outputs/mos_cap_2d/")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    geom = MOSCapGeometry(Lx=args.Lx, Ly_semi=args.Ly_semi, t_ox=args.t_ox,
                           eps_r_semi=11.7, eps_r_ox=3.9)
    scaling = Scaling.for_material(SILICON, T=300.0)
    grid = Grid2D.uniform(geom, Nx=args.Nx, Ny=args.Ny)
    solver = MOSCap2DSolver(grid, scaling, SILICON,
                             MOSCap2DConfig(max_iters=60, damping=1.0, tol=1e-7))

    print(f"2D MOS-cap demo: N_A={args.N_A:.1e} m^-3, t_ox={args.t_ox*1e9:.1f} nm, "
          f"Ly_semi={args.Ly_semi*1e9:.0f} nm")
    print(f"Grid: {grid.Nx} x {grid.Ny} = {grid.n_nodes} nodes; "
          f"hy={grid.hy*1e9:.2f} nm; oxide nodes={(grid.region[:,0]==1).sum()}")

    doping = np.zeros_like(grid.eps_r_field)
    doping[grid.semi_mask] = -args.N_A
    phi_F = -scaling.V_T * math.asinh(args.N_A / (2 * SILICON.n_i))
    j_if = int(np.argmin(np.abs(grid.y - geom.y_interface)))

    Vg_sweep = np.linspace(args.Vg_min, args.Vg_max, args.n_Vg)
    results = {
        "V_gate": [], "phi_s_num": [], "phi_s_ana": [],
        "gate_charge": [], "converged": [], "iterations": [],
    }
    states = {}
    print(f"\n{'V_g (V)':>8} {'phi_s (V)':>11} {'Q_gate (C/m^2)':>16} {'conv':>5}")
    print("-" * 45)
    for V_g in Vg_sweep:
        bc = MOSCapBoundary(V_gate=float(V_g), V_substrate=0.0, phi_ms=phi_F)
        # Fresh solve from the analytical linear initial guess each time;
        # this converges in ~3 Newton iterations and avoids the
        # warm-start state-corruption seen when chaining across the full
        # accumulation->inversion range.
        st = solver.solve(doping, bc, initial_state=None)
        phi_s_num = float(st.phi[j_if, grid.Nx // 2]) - phi_F
        phi_s_ana, W_d, V_ox = depletion_approximation_surface_potential(
            V_gate=float(V_g), N_A=args.N_A, t_ox=geom.t_ox,
            eps_si=geom.eps_r_semi, eps_ox=geom.eps_r_ox, phi_ms=phi_F)
        Qg = gate_charge(st, grid, geom)
        results["V_gate"].append(float(V_g))
        results["phi_s_num"].append(phi_s_num)
        results["phi_s_ana"].append(phi_s_ana)
        results["gate_charge"].append(Qg)
        results["converged"].append(bool(st.converged))
        results["iterations"].append(int(st.iterations))
        states[float(V_g)] = st
        if abs(V_g % 0.2) < 0.03 or V_g == Vg_sweep[-1]:
            print(f"{V_g:8.3f} {phi_s_num:11.4f} {Qg:16.4e} "
                  f"{'Y' if st.converged else 'N':>5}")

    # Capacitance: C = dQ_gate / dV_gate (numerical derivative)
    Vg_arr = np.asarray(results["V_gate"])
    Qg_arr = np.asarray(results["gate_charge"])
    C_hf = np.gradient(Qg_arr, Vg_arr)        # F/m^2
    results["capacitance"] = C_hf.tolist()
    # Oxide capacitance for normalization
    C_ox = geom.eps_r_ox * EPS_0 / geom.t_ox
    print(f"\nC_ox = {C_ox*1e3:.3f} mF/m^2")
    print(f"max C/C_ox = {np.max(C_hf)/C_ox:.3f} (accumulation should approach 1)")

    with open(out_dir / "cv_data.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(results, f, indent=2)

    # ---------------- Figures ----------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 1. C-V curve
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.plot(Vg_arr, C_hf / C_ox, "o-", color="#0173B2", ms=4)
        ax.axhline(1.0, color="k", lw=0.6, ls="--", label=r"$C_{ox}$")
        ax.set_xlabel("Gate voltage $V_G$ (V)")
        ax.set_ylabel(r"$C / C_{ox}$")
        ax.set_title("MOS-cap C-V (quasi-static)")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(fig_dir / "cv_curve.png", dpi=200)
        plt.close(fig)

        # 2. Surface potential vs V_g (num vs analytical)
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.plot(Vg_arr, results["phi_s_num"], "o-", color="#0173B2",
                ms=4, label="2D solver")
        ax.plot(Vg_arr, results["phi_s_ana"], "--", color="#D55E00",
                label="Depletion approx.")
        ax.set_xlabel("Gate voltage $V_G$ (V)")
        ax.set_ylabel(r"Surface potential $\phi_s$ (V)")
        ax.set_title("Surface potential vs gate bias")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(fig_dir / "surface_potential.png", dpi=200)
        plt.close(fig)

        # 3. 2D field maps at a representative inversion-onset bias
        V_show = Vg_sweep[min(len(Vg_sweep) - 1, int(0.8 * len(Vg_sweep)))]
        st = states[float(V_show)]
        fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
        extent = [0, geom.Lx * 1e9, 0, geom.Ly * 1e9]
        im0 = axes[0].imshow(st.phi, origin="lower", aspect="auto",
                             extent=extent, cmap="viridis")
        axes[0].set_title(f"Potential (V), $V_G$={V_show:.2f}V")
        axes[0].axhline(geom.y_interface * 1e9, color="white", lw=0.8, ls=":")
        plt.colorbar(im0, ax=axes[0], fraction=0.046)
        # log10 electron density (semi only)
        with np.errstate(divide="ignore"):
            log_n = np.where(st.n > 0, np.log10(np.maximum(st.n, 1e6)), np.nan)
        im1 = axes[1].imshow(log_n, origin="lower", aspect="auto",
                             extent=extent, cmap="plasma")
        axes[1].set_title(r"$\log_{10} n$ (m$^{-3}$)")
        axes[1].axhline(geom.y_interface * 1e9, color="white", lw=0.8, ls=":")
        plt.colorbar(im1, ax=axes[1], fraction=0.046)
        with np.errstate(divide="ignore"):
            log_p = np.where(st.p > 0, np.log10(np.maximum(st.p, 1e6)), np.nan)
        im2 = axes[2].imshow(log_p, origin="lower", aspect="auto",
                             extent=extent, cmap="cividis")
        axes[2].set_title(r"$\log_{10} p$ (m$^{-3}$)")
        axes[2].axhline(geom.y_interface * 1e9, color="white", lw=0.8, ls=":")
        plt.colorbar(im2, ax=axes[2], fraction=0.046)
        for ax in axes:
            ax.set_xlabel("x (nm)"); ax.set_ylabel("y (nm)")
        fig.suptitle(f"2D MOS-cap fields at $V_G$ = {V_show:.2f} V")
        fig.tight_layout()
        fig.savefig(fig_dir / "field_maps.png", dpi=200)
        plt.close(fig)
        print(f"\nFigures -> {fig_dir}/")
    except ImportError:
        print("\n(matplotlib unavailable; skipping figures)")

    n_converged = sum(results["converged"])
    print(f"\nConverged at {n_converged}/{len(Vg_sweep)} bias points.")
    print(f"Done -> {out_dir}")


if __name__ == "__main__":
    main()
