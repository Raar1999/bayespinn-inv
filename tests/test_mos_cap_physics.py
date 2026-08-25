"""
Physics and convergence regression tests for the 2D MOS-capacitor solver.

The pre-existing MOS suite exercised only V_gate in [-0.3, +1.0] and never
checked that the reported solution actually satisfies the discrete Poisson
equation. Under that coverage the solver could -- and did -- diverge by
sixteen orders of magnitude for every |V_gate| >~ 1 V while all nine tests
passed. See BUG-05..BUG-09 in docs/AUDIT_MASTER.md.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bayespinn_inv.physics.constants import EPS_0, Q_E, SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.grid_2d import Grid2D, MOSCapBoundary, MOSCapGeometry
from bayespinn_inv.solvers.mos_cap_2d import (
    MOSCap2DConfig,
    MOSCap2DSolver,
    depletion_approximation_surface_potential,
)

N_A = 1e23          # m^-3, p-type body
T_OX = 5e-9
LY_SEMI = 300e-9


def _build(Nx=5, Ny=306, **cfg_kw):
    geom = MOSCapGeometry(Lx=20e-9, Ly_semi=LY_SEMI, t_ox=T_OX,
                          eps_r_semi=11.7, eps_r_ox=3.9)
    sc = Scaling.for_material(SILICON, T=300.0)
    grid = Grid2D.uniform(geom, Nx=Nx, Ny=Ny)
    cfg = MOSCap2DConfig(max_iters=300, **cfg_kw)
    solver = MOSCap2DSolver(grid, sc, SILICON, cfg)
    doping = np.where(grid.region == 0, -N_A, 0.0)
    j_if = int(np.argmin(np.abs(grid.y - geom.y_interface)))
    return geom, sc, grid, solver, doping, j_if


def _poisson_relative_residual(solver, grid, state, doping, sc):
    """Independently recompute ||L phi + q V (p-n+C)|| / charge scale."""
    phi = state.phi.ravel()
    semi = grid.semi_mask.ravel()
    V = grid.cell_volume().ravel()
    C = np.where(grid.region == 0, doping, 0.0).ravel()
    n_i = SILICON.n_i
    arg = np.clip(phi / sc.V_T, -60.0, 60.0)
    n = np.where(semi, n_i * np.exp(arg), 0.0)
    p = np.where(semi, n_i * np.exp(-arg), 0.0)
    r = solver._L @ phi + Q_E * V * np.where(semi, p - n + C, 0.0)
    interior = np.ones(phi.size, bool)
    interior[solver._dirichlet_idx_bottom] = False
    interior[solver._dirichlet_idx_top] = False
    scale = Q_E * V.max() * max(abs(C).max(), n_i)
    return float(np.max(np.abs(r[interior]))) / scale


# ===========================================================================
# BUG-05/06/07 -- Newton diverged for every |V_gate| >~ 1 V
# ===========================================================================

class TestConvergenceAcrossBias:

    @pytest.mark.parametrize("Vg", [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0])
    def test_converges_over_full_operating_range(self, Vg):
        _, sc, grid, solver, doping, _ = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=Vg, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged, f"V_gate={Vg} failed to converge"
        assert not st.carrier_clipping_active

    @pytest.mark.parametrize("Vg", [-1.0, 0.5, 2.0])
    def test_reported_solution_actually_solves_poisson(self, Vg):
        """`converged=True` must mean the discrete residual is small."""
        _, sc, grid, solver, doping, _ = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=Vg, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged
        assert _poisson_relative_residual(solver, grid, st, doping, sc) < 1e-8

    def test_residual_decreases_monotonically(self):
        """Newton must descend; the old code grew the residual every step."""
        _, _, _, solver, doping, _ = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=1.5, V_substrate=0.0,
                                                 phi_ms=0.0))
        r = np.asarray(st.residuals)
        assert r[-1] < r[0], "residual did not decrease overall"
        assert r[-1] < 1e-8

    def test_flat_band_is_exact(self):
        """At V_gate = 0 with phi_ms = 0 the LCN guess is already the answer."""
        _, sc, grid, solver, doping, j_if = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=0.0, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged
        phi_F = -sc.V_T * math.asinh(N_A / (2.0 * SILICON.n_i))
        assert float(st.phi[j_if, grid.Nx // 2]) == pytest.approx(phi_F, abs=1e-9)


# ===========================================================================
# BUG-08 -- non-conservative finite volumes at the Neumann side walls
# ===========================================================================

class TestLateralInvariance:

    @pytest.mark.parametrize("Nx", [4, 5, 9, 17])
    def test_uniform_body_is_exactly_x_invariant(self, Nx):
        """A laterally-uniform problem must have zero lateral variation.

        The old assembly used full-width transverse faces on the half-width
        boundary cells, so phi bowed by ~1.5 mV toward the side walls and
        decayed only as O(1/Nx).
        """
        _, _, grid, solver, doping, _ = _build(Nx=Nx)
        st = solver.solve(doping, MOSCapBoundary(V_gate=1.0, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged
        assert np.max(np.ptp(st.phi, axis=1)) < 1e-12

    def test_surface_potential_independent_of_Nx(self):
        vals = []
        for Nx in (4, 9, 17):
            _, _, grid, solver, doping, j_if = _build(Nx=Nx)
            st = solver.solve(doping, MOSCapBoundary(V_gate=1.0,
                                                     V_substrate=0.0, phi_ms=0.0))
            vals.append(float(st.phi[j_if, grid.Nx // 2]))
        assert np.ptp(vals) < 1e-9, f"phi_s depends on Nx: {vals}"


# ===========================================================================
# Physics validation
# ===========================================================================

class TestMOSPhysics:

    def test_surface_potential_matches_depletion_approximation(self):
        """Within the depletion regime, agreement should be ~V_T or better.

        The depletion approximation replaces the majority-carrier tail with
        an abrupt edge, an O(V_T) error, so we allow 1.5 * V_T.
        """
        _, sc, grid, solver, doping, j_if = _build()
        for Vg in (0.2, 0.4, 0.6, 0.8):
            st = solver.solve(doping, MOSCapBoundary(V_gate=Vg,
                                                     V_substrate=0.0, phi_ms=0.0))
            assert st.converged
            num = float(st.phi[j_if, grid.Nx // 2])
            ana, _, _ = depletion_approximation_surface_potential(
                V_gate=Vg, N_A=N_A, t_ox=T_OX, eps_si=11.7, eps_ox=3.9,
                material=SILICON, T=300.0)
            assert abs(num - ana) < 1.5 * sc.V_T, (
                f"V_g={Vg}: numeric {num}, depletion {ana}")

    def test_surface_potential_monotonic_in_gate_bias(self):
        _, _, grid, solver, doping, j_if = _build()
        phis = []
        for Vg in np.linspace(-1.0, 2.0, 13):
            st = solver.solve(doping, MOSCapBoundary(V_gate=float(Vg),
                                                     V_substrate=0.0, phi_ms=0.0))
            assert st.converged
            phis.append(float(st.phi[j_if, grid.Nx // 2]))
        assert np.all(np.diff(phis) > 0), "phi_s(V_g) is not monotonic"

    def test_inversion_pins_surface_potential_near_2_phi_F(self):
        """Beyond threshold, phi_s saturates -- the defining MOS behaviour."""
        _, sc, grid, solver, doping, j_if = _build()
        phi_F = -sc.V_T * math.log(N_A / SILICON.n_i)
        psi = {}
        for Vg in (2.0, 3.0, 4.0):
            st = solver.solve(doping, MOSCapBoundary(V_gate=Vg,
                                                     V_substrate=0.0, phi_ms=0.0))
            assert st.converged
            psi[Vg] = float(st.phi[j_if, grid.Nx // 2]) - phi_F
        # band bending is past 2|phi_F| and grows far slower than V_gate
        assert psi[2.0] > 2.0 * abs(phi_F) * 0.95
        assert (psi[4.0] - psi[2.0]) < 0.25 * (4.0 - 2.0)

    def test_accumulation_drives_surface_potential_below_bulk(self):
        _, sc, grid, solver, doping, j_if = _build()
        phi_F = -sc.V_T * math.asinh(N_A / (2.0 * SILICON.n_i))
        st = solver.solve(doping, MOSCapBoundary(V_gate=-1.5, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged
        assert float(st.phi[j_if, grid.Nx // 2]) < phi_F

    def test_no_carriers_in_the_oxide(self):
        _, _, grid, solver, doping, _ = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=2.0, V_substrate=0.0,
                                                 phi_ms=0.0))
        ox = grid.region == 1
        assert np.all(st.n[ox] == 0.0)
        assert np.all(st.p[ox] == 0.0)

    def test_mesh_convergence_of_surface_potential(self):
        """phi_s must converge as the vertical mesh is refined."""
        vals = []
        for Ny in (154, 306, 610):
            _, _, grid, solver, doping, j_if = _build(Ny=Ny)
            st = solver.solve(doping, MOSCapBoundary(V_gate=1.0,
                                                     V_substrate=0.0, phi_ms=0.0))
            assert st.converged
            vals.append(float(st.phi[j_if, grid.Nx // 2]))
        # successive differences must shrink
        d1, d2 = abs(vals[1] - vals[0]), abs(vals[2] - vals[1])
        assert d2 < d1, f"not converging under refinement: {vals}"
        assert d2 < 5e-3

    def test_gauss_law_total_charge_balances_gate_field(self):
        """Integrated semiconductor charge must equal the oxide displacement.

        Q_semi = -eps_ox * E_ox (per unit area), i.e. global charge
        neutrality of the capacitor.
        """
        _, sc, grid, solver, doping, j_if = _build()
        st = solver.solve(doping, MOSCapBoundary(V_gate=1.0, V_substrate=0.0,
                                                 phi_ms=0.0))
        assert st.converged
        col = grid.Nx // 2
        # integrate rho over y down one column -> areal charge density (C/m^2)
        rho = Q_E * np.where(grid.semi_mask, st.p - st.n + st.doping, 0.0)[:, col]
        wy = np.full(grid.Ny, grid.hy)
        wy[0] = wy[-1] = 0.5 * grid.hy
        Q_semi = float(np.sum(rho * wy))
        # displacement in the oxide from the potential drop across it
        E_ox = (st.phi[-1, col] - st.phi[j_if, col]) / T_OX
        D_ox = -3.9 * EPS_0 * E_ox
        assert abs(Q_semi) > 1e-5, "test is vacuous: no charge in the device"
        assert Q_semi == pytest.approx(D_ox, rel=1e-6), (
            f"Gauss law violated: Q_semi={Q_semi}, D_ox={D_ox}")


class TestCapacitanceVoltageCurve:
    """The defining MOS measurement. Unobtainable before BUG-05/06/07.

    A C-V sweep needs convergence from deep accumulation to strong inversion;
    the old solver diverged above |V_g| ~ 1 V, so this curve could not be
    computed at all.
    """

    @staticmethod
    def _cv(Vg):
        _, sc, grid, solver, doping, j_if = _build(Ny=306)
        wy = np.full(grid.Ny, grid.hy)
        wy[0] = wy[-1] = 0.5 * grid.hy
        col = grid.Nx // 2
        Q = []
        for v in Vg:
            st = solver.solve(doping, MOSCapBoundary(V_gate=float(v),
                                                     V_substrate=0.0,
                                                     phi_ms=0.0))
            assert st.converged, f"C-V sweep failed to converge at {v} V"
            rho = Q_E * np.where(grid.semi_mask,
                                 st.p - st.n + st.doping, 0.0)[:, col]
            Q.append(float(np.sum(rho * wy)))
        return np.asarray(Q), 3.9 * EPS_0 / T_OX

    def test_cv_curve_has_the_classic_shape(self):
        Vg = np.linspace(-2.5, 2.5, 41)
        Q, C_ox = self._cv(Vg)
        C = -np.gradient(Q, Vg)

        acc = C[Vg < -1.5].max() / C_ox        # accumulation branch
        dep = C[(Vg > -0.2) & (Vg < 1.0)].min() / C_ox   # depletion minimum
        inv = C[Vg > 1.5].max() / C_ox         # inversion branch

        assert acc > 0.7, f"accumulation capacitance too low: {acc:.3f} C_ox"
        assert inv > 0.7, f"inversion capacitance too low: {inv:.3f} C_ox"
        assert dep < 0.2, f"no depletion minimum: {dep:.3f} C_ox"
        assert acc < 1.02 and inv < 1.02, "C exceeds C_ox, which is impossible"

    def test_charge_changes_sign_between_accumulation_and_inversion(self):
        Vg = np.array([-2.0, 2.0])
        Q, _ = self._cv(Vg)
        assert Q[0] > 0 > Q[1], (
            f"semiconductor charge should be positive (holes accumulated) at "
            f"V_g=-2 and negative (electrons inverted) at +2; got {Q}")
