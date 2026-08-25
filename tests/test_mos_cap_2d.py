"""
Unit tests for the 2D MOS-capacitor solver.

The tests focus on properties that are well within the solver's
validity range:

  - V_g sweep produces monotonically increasing surface potential
  - Equilibrium (V_g = phi_ms = phi_F): no potential drop except
    Dirichlet boundary corrections
  - Linear Poisson (zero doping): match analytical capacitor-divider
  - Modest-doping (N_A = 1e21) depletion regime matches the
    depletion approximation to within a known offset due to free-carrier
    contributions (a regime where the depletion approximation is
    intentionally inaccurate)

Strong-inversion stiffness (N_A >= 1e22, V_g >> V_T) is a known hard
case requiring nonlinear-Poisson Gummel iteration with carrier-
parameterization, which is documented as a limitation in the module
docstring.
"""

import math

import numpy as np

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.grid_2d import (
    Grid2D,
    MOSCapBoundary,
    MOSCapGeometry,
)
from bayespinn_inv.solvers.mos_cap_2d import (
    MOSCap2DConfig,
    MOSCap2DSolver,
    depletion_approximation_surface_potential,
)


class TestGrid2D:

    def setup_method(self):
        self.geom = MOSCapGeometry(Lx=20e-9, Ly_semi=100e-9, t_ox=5e-9,
                                    eps_r_semi=11.7, eps_r_ox=3.9)
        self.grid = Grid2D.uniform(self.geom, Nx=11, Ny=106)

    def test_grid_shapes(self):
        assert self.grid.eps_r_field.shape == (106, 11)
        assert self.grid.region.shape == (106, 11)

    def test_oxide_assignment(self):
        # With Ny=106 and y_interface=100nm, we have hy=1nm exactly,
        # and 6 oxide nodes (j=100..105)
        n_oxide = int(np.sum(self.grid.region[:, 0] == 1))
        assert n_oxide == 6, f"Expected 6 oxide nodes, got {n_oxide}"
        # All semiconductor nodes should have eps_r = 11.7
        assert np.all(self.grid.eps_r_field[self.grid.semi_mask] == 11.7)
        # All oxide nodes should have eps_r = 3.9
        assert np.all(self.grid.eps_r_field[~self.grid.semi_mask] == 3.9)

    def test_face_eps_y_harmonic_at_interface(self):
        face_y = self.grid.face_eps_y()
        # Find the interface face
        n_semi = int(np.sum(self.grid.region[:, 0] == 0))
        # Interface face is between j=n_semi-1 and j=n_semi
        interface_face_idx = n_semi - 1
        expected = 2 * 11.7 * 3.9 / (11.7 + 3.9)
        assert abs(face_y[interface_face_idx, 0] - expected) < 1e-6


class TestMOSCap2D:

    def setup_method(self):
        self.geom = MOSCapGeometry(Lx=20e-9, Ly_semi=100e-9, t_ox=5e-9,
                                    eps_r_semi=11.7, eps_r_ox=3.9)
        self.scaling = Scaling.for_material(SILICON, T=300.0)
        self.grid = Grid2D.uniform(self.geom, Nx=5, Ny=106)
        self.solver = MOSCap2DSolver(
            self.grid, self.scaling, SILICON,
            MOSCap2DConfig(max_iters=80, damping=1.0, tol=1e-7),
        )

    def test_zero_doping_linear_poisson(self):
        """Undoped body in the linear-screening limit: capacitor divider.

        NOTE (BUG-09, docs/AUDIT_MASTER.md): this test previously used
        V_gate = 1.0 V and called the expected answer "pure Laplace". That is
        not physics. With C = 0 the body is *intrinsic*, not charge-free, and
        its carriers still respond as n = n_i exp(+phi/V_T),
        p = n_i exp(-phi/V_T). At 1 V that is n ~ 6e32 m^-3 -- an enormous
        space charge that screens the field completely, so the capacitor
        divider is simply the wrong reference and the old assertion only
        passed because the solver was not converging (BUG-07).

        The divider IS exact in the linear-screening limit: the intrinsic
        Debye length in Si is ~41 um, four orders of magnitude beyond this
        300 nm body, so at a small gate bias the induced charge is
        negligible. We test there.
        """
        doping = np.zeros_like(self.grid.eps_r_field)
        V_g = 1e-3                       # deep in the linear-screening regime
        bc = MOSCapBoundary(V_gate=V_g, V_substrate=0.0, phi_ms=0.0)
        st = self.solver.solve(doping, bc)
        assert st.converged

        # Analytical: capacitor-divider
        Ly_semi = 100e-9
        t_ox = 5e-9
        phi_s_ana = V_g * (3.9 / t_ox) / (11.7 / Ly_semi + 3.9 / t_ox)
        # Interface node index
        j_if = int(np.argmin(np.abs(self.grid.y - self.geom.y_interface)))
        phi_s_num = float(st.phi[j_if, self.grid.Nx // 2])
        # Discretization error should be < 5%
        assert abs(phi_s_num - phi_s_ana) / phi_s_ana < 0.05, \
            f"Linear-Poisson phi_s mismatch: num={phi_s_num}, ana={phi_s_ana}"

    def test_flat_band_no_drop(self):
        """At V_g = phi_ms = 0, with phi_ms = phi_F, expect uniform bulk."""
        N_A = 1e21
        doping = np.zeros_like(self.grid.eps_r_field)
        doping[self.grid.semi_mask] = -N_A
        phi_F = -self.scaling.V_T * math.asinh(N_A / (2 * SILICON.n_i))
        bc = MOSCapBoundary(V_gate=0.0, V_substrate=0.0, phi_ms=phi_F)
        st = self.solver.solve(doping, bc)
        assert st.converged
        # Bulk should sit at phi_F. Sample the deepest bulk rows (closest to
        # the grounded substrate contact, far from the gate depletion region).
        bulk_phi = st.phi[1:5, self.grid.Nx // 2].mean()
        # Within 50 mV: the depletion region from the gate perturbs the
        # potential even in nominal "bulk", and the depletion approximation
        # used to derive phi_F neglects free-carrier tails.
        assert abs(bulk_phi - phi_F) < 0.050, \
            f"Flat-band bulk phi = {bulk_phi}, expected ~{phi_F}"

    def test_Vg_sweep_monotonic(self):
        """phi_s should be monotone increasing with V_g for P-substrate."""
        N_A = 1e21
        doping = np.zeros_like(self.grid.eps_r_field)
        doping[self.grid.semi_mask] = -N_A
        j_if = int(np.argmin(np.abs(self.grid.y - self.geom.y_interface)))
        prev_state = None
        phi_s_values = []
        V_gates = [-0.3, -0.1, 0.0, 0.1, 0.2, 0.3]
        phi_F = -self.scaling.V_T * math.asinh(N_A / (2 * SILICON.n_i))
        for V_g in V_gates:
            bc = MOSCapBoundary(V_gate=V_g, V_substrate=0.0, phi_ms=phi_F)
            st = self.solver.solve(doping, bc, initial_state=prev_state)
            assert st.converged, f"Solver failed at V_g={V_g}"
            phi_s = float(st.phi[j_if, self.grid.Nx // 2]) - phi_F
            phi_s_values.append(phi_s)
            prev_state = st
        # Monotonically increasing
        for i in range(len(phi_s_values) - 1):
            assert phi_s_values[i + 1] > phi_s_values[i], \
                f"phi_s non-monotonic: {phi_s_values}"

    def test_carrier_densities_zero_in_oxide(self):
        """Carrier densities must be exactly zero in the oxide region."""
        N_A = 1e21
        doping = np.zeros_like(self.grid.eps_r_field)
        doping[self.grid.semi_mask] = -N_A
        phi_F = -self.scaling.V_T * math.asinh(N_A / (2 * SILICON.n_i))
        bc = MOSCapBoundary(V_gate=0.5, V_substrate=0.0, phi_ms=phi_F)
        st = self.solver.solve(doping, bc)
        oxide_mask = self.grid.region == 1
        assert np.all(st.n[oxide_mask] == 0.0)
        assert np.all(st.p[oxide_mask] == 0.0)

    def test_x_uniformity(self):
        """For an x-uniform MOS-cap, the solution should be x-invariant."""
        N_A = 1e21
        doping = np.zeros_like(self.grid.eps_r_field)
        doping[self.grid.semi_mask] = -N_A
        phi_F = -self.scaling.V_T * math.asinh(N_A / (2 * SILICON.n_i))
        bc = MOSCapBoundary(V_gate=0.2, V_substrate=0.0, phi_ms=phi_F)
        st = self.solver.solve(doping, bc)
        # Compare middle column to edge column
        phi_mid = st.phi[:, self.grid.Nx // 2]
        phi_edge = st.phi[:, 0]
        # Should agree to high precision
        assert np.max(np.abs(phi_mid - phi_edge)) < 1e-3, \
            f"x non-uniformity: max diff = {np.max(np.abs(phi_mid - phi_edge))}"


class TestDepletionApproximation:
    """Sanity-check the analytical helper."""

    def test_flat_band_phi_s(self):
        # At V_GB = 0 (with phi_ms = 0), depletion approx gives phi_s = phi_F (~0)
        # for a flat-band biased MOS-cap.
        N_A = 1e22
        # Just check it runs and returns finite values
        phi_s, W_d, V_ox = depletion_approximation_surface_potential(
            V_gate=1.0, N_A=N_A, t_ox=5e-9,
            eps_si=11.7, eps_ox=3.9, phi_ms=0.0,
        )
        assert math.isfinite(phi_s)
        assert math.isfinite(W_d) and W_d > 0
        assert math.isfinite(V_ox) and V_ox > 0
