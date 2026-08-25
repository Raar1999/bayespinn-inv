"""
Unit tests for BayesPINN-Inv core invariants.

These tests validate the physical and numerical properties that MUST
hold for the rest of the framework to be correct. They are deliberately
fast (no full training) so that ``make test`` is a sub-30-second
operation that runs after every change.

The full integration tests (training convergence, inverse-design
end-to-end) live in tests/integration/ and are run by ``make test-slow``.
"""

import math

import numpy as np
import torch

from bayespinn_inv.calibration.metrics import (
    crps_empirical,
    expected_calibration_error,
    gaussian_nll,
)
from bayespinn_inv.physics.constants import SILICON, thermal_voltage
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.pinn.losses import ohmic_boundary_values
from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
    bernoulli,
)

# ============================================================================
# Physics constants and scaling
# ============================================================================

class TestScalingInvariants:

    def test_thermal_voltage(self):
        """V_T at 300K is 25.85 mV to 3 sig figs."""
        V_T = thermal_voltage(300.0)
        assert abs(V_T - 0.02585) / 0.02585 < 1e-3

    def test_scaling_round_trip(self):
        """SI -> scaled -> SI is identity for all quantities."""
        s = Scaling.for_material(SILICON, T=300.0)
        x = torch.tensor([1e-7, 5e-7, 1e-6])
        assert torch.allclose(s.x_to_si(s.x_to_scaled(x)), x, rtol=1e-6)
        phi = torch.tensor([0.0, 0.5, 1.0])
        assert torch.allclose(s.phi_to_si(s.phi_to_scaled(phi)), phi, rtol=1e-6)
        n = torch.tensor([1e16, 1e22, 1e25])
        assert torch.allclose(s.n_to_si(s.n_to_scaled(n)), n, rtol=1e-6)

    def test_doping_net_input_invertible(self):
        """Log-compressed doping representation is bijective."""
        s = Scaling.for_material(SILICON, T=300.0)
        C = torch.tensor([-1e23, -1e21, 0.0, 1e21, 1e23])
        lat = s.doping_to_net_input(C)
        C_back = s.net_input_to_doping_si(lat)
        assert torch.allclose(C_back, C, rtol=1e-4, atol=1.0)

    def test_doping_net_input_O1(self):
        """Compressed representation has reasonable magnitude (no saturation)."""
        s = Scaling.for_material(SILICON, T=300.0)
        # typical Si doping range: 1e21..1e25 m^-3
        C = torch.tensor([-1e25, -1e21, 1e21, 1e25])
        lat = s.doping_to_net_input(C)
        assert torch.all(torch.abs(lat) < 2.0), f"Latent saturated: {lat}"


# ============================================================================
# Scharfetter-Gummel solver
# ============================================================================

class TestBernoulli:
    """B(x) = x / (exp(x) - 1). Must be numerically stable everywhere."""

    def test_bernoulli_at_zero(self):
        assert abs(bernoulli(0.0) - 1.0) < 1e-12

    def test_bernoulli_small_x(self):
        for x in [1e-12, 1e-8, 1e-4]:
            # B(x) ~ 1 - x/2 + O(x^2)
            assert abs(bernoulli(x) - (1.0 - x / 2.0)) < x ** 2

    def test_bernoulli_large_positive(self):
        # B(x) -> x * exp(-x) for large positive x
        b = bernoulli(50.0)
        assert 0.0 <= b < 1e-10

    def test_bernoulli_large_negative(self):
        # B(-x) -> -x for x >> 0; so B(-50) ~ 50
        b = bernoulli(-50.0)
        assert abs(b - 50.0) / 50.0 < 1e-8

    def test_bernoulli_array(self):
        x = np.linspace(-30.0, 30.0, 121)
        b = np.array([bernoulli(xi) for xi in x])
        assert np.all(np.isfinite(b))
        # Monotonicity: B is strictly decreasing
        assert np.all(np.diff(b) < 0)


class TestSGEquilibrium:
    """SG at zero bias should produce the analytical built-in voltage."""

    def setup_method(self):
        s = Scaling.for_material(SILICON, T=300.0)
        L = 1e-6
        N = 201
        L_s = s.x_to_scaled(torch.tensor(L)).item()
        self.grid = Grid1D.uniform(L_s, N)
        self.scaling = s
        self.solver = ScharfetterGummel1D(self.grid, s, SILICON, SGConfig())

    def test_V_bi_uniform_PN(self):
        """V_bi = V_T * ln(N_A * N_D / n_i^2) for uniform PN at equilibrium."""
        N_A = 1e22; N_D = 1e22
        x = self.scaling.x_to_si(torch.as_tensor(self.grid.x)).numpy()
        doping = np.where(x < x.max() / 2, -N_A, N_D)
        state = self.solver.solve(doping, bias=0.0)
        assert state.converged
        V_bi_expected = self.scaling.V_T * math.log(N_A * N_D / SILICON.n_i ** 2)
        V_bi_actual = float(state.phi[-1] - state.phi[0])
        assert abs(V_bi_actual - V_bi_expected) / V_bi_expected < 1e-3

    def test_mass_action(self):
        """n*p = n_i^2 everywhere at equilibrium."""
        N_A = 1e22; N_D = 1e22
        x = self.scaling.x_to_si(torch.as_tensor(self.grid.x)).numpy()
        doping = np.where(x < x.max() / 2, -N_A, N_D)
        state = self.solver.solve(doping, bias=0.0)
        np_product = state.n * state.p
        n_i_sq = SILICON.n_i ** 2
        ratio = np_product / n_i_sq
        assert np.all(np.isfinite(ratio))
        # Tightened from 5e-2 after BUG-03 (docs/AUDIT_MASTER.md): the old
        # tolerance was loose enough to pass with a 1.3e-2 violation caused
        # by an unequilibrated continuity solve plus a convergence test that
        # only watched the potential. The equilibrated solver reaches ~8e-6.
        assert np.all(np.abs(ratio - 1.0) < 1e-4)

    def test_forward_bias_increases_current(self):
        """V_a > 0 should mean forward bias: |I| increases by many orders.

        This is the regression test for the sign-convention bug we hit
        early in development. A uniformly-doped PN diode at room temp
        should yield diode ideality factor n ~ 1 when fit in the linear
        log-I-V range V in [0.3, 0.55].
        """
        N_A = 1e22; N_D = 1e22
        x = self.scaling.x_to_si(torch.as_tensor(self.grid.x)).numpy()
        doping = np.where(x < x.max() / 2, -N_A, N_D)
        biases = np.linspace(0.0, 0.55, 12)
        prev = None
        I = []
        for V in biases:
            s = self.solver.solve(doping, float(V), initial_state=prev)
            I.append(s.terminal_current)
            prev = s
        I_abs = np.abs(np.asarray(I))
        # Many orders of magnitude swing in current
        assert I_abs.max() / I_abs[0] > 1e6
        # Diode ideality factor
        mask = (biases >= 0.3) & (biases <= 0.55)
        slope, _ = np.polyfit(biases[mask], np.log10(I_abs[mask]), 1)
        n_ideal = 1.0 / (slope * self.scaling.V_T * math.log(10))
        assert 0.95 < n_ideal < 1.20, f"Ideality factor out of range: {n_ideal}"


# ============================================================================
# Ohmic boundary numerical stability
# ============================================================================

class TestOhmicBoundary:

    def test_log_np_zero(self):
        """log(n) + log(p) = 0 at ohmic contacts (n*p = 1 in scaled units)."""
        C_L = torch.tensor([-1e6])
        C_R = torch.tensor([ 1e6])
        V_a = torch.tensor([0.0])
        b = ohmic_boundary_values(C_L, C_R, V_a)
        assert abs(b["log_n_left"]  + b["log_p_left"]).item()  < 1e-6
        assert abs(b["log_n_right"] + b["log_p_right"]).item() < 1e-6

    def test_V_bi_scaled(self):
        """phi_right - phi_left = ln(C_R) - ln(-C_L) at zero bias."""
        C_L = torch.tensor([-1e6])
        C_R = torch.tensor([ 1e6])
        V_a = torch.tensor([0.0])
        b = ohmic_boundary_values(C_L, C_R, V_a)
        V_bi = (b["phi_s_right"] - b["phi_s_left"]).item()
        expected = 2.0 * math.log(1e6)
        assert abs(V_bi - expected) / expected < 1e-4

    def test_stable_at_extreme_doping(self):
        """Heavy doping (|C_s| > 1e7) must not give inf."""
        C_L = torch.tensor([-1e8])
        C_R = torch.tensor([ 1e8])
        V_a = torch.tensor([0.0])
        b = ohmic_boundary_values(C_L, C_R, V_a)
        for k in ("phi_s_left", "phi_s_right",
                  "log_n_left", "log_n_right",
                  "log_p_left", "log_p_right"):
            assert torch.all(torch.isfinite(b[k])), f"{k} is inf"


# ============================================================================
# Network architecture
# ============================================================================

class TestNetwork:

    def test_forward_shapes(self):
        cfg = PINNConfig(in_dim=2, hidden_dim=32, num_blocks=3,
                          fourier_features=8, doping_dim=16, seed=0)
        net = SemiconductorPINN(cfg)
        x = torch.randn(64, 1)
        V = torch.zeros(64, 1)
        latent = torch.randn(64, 16) * 0.1
        phi, log_n, log_p = net(x, V, latent)
        assert phi.shape == (64, 1)
        assert log_n.shape == (64, 1)
        assert log_p.shape == (64, 1)

    def test_seed_reproducibility(self):
        """Same seed -> identical network params."""
        cfg = PINNConfig(seed=42, doping_dim=16)
        n1 = SemiconductorPINN(cfg)
        n2 = SemiconductorPINN(cfg)
        for p1, p2 in zip(n1.parameters(), n2.parameters()):
            assert torch.allclose(p1, p2)

    def test_different_seed_differs(self):
        cfg1 = PINNConfig(seed=1, doping_dim=16)
        cfg2 = PINNConfig(seed=2, doping_dim=16)
        n1 = SemiconductorPINN(cfg1)
        n2 = SemiconductorPINN(cfg2)
        # at least one param tensor must differ
        any_diff = any(
            not torch.allclose(p1, p2)
            for p1, p2 in zip(n1.parameters(), n2.parameters())
        )
        assert any_diff


# ============================================================================
# Calibration metrics
# ============================================================================

class TestCalibrationMetrics:

    def test_ece_perfect(self):
        """Perfectly calibrated samples -> ECE ~ 0.

        Setup: ground truths are drawn from N(0, 1). Predictive
        distribution at each point is *also* N(0, 1) (independent of the
        truth, so the predictive q-quantile is ~ Phi^{-1}(q)). Then the
        empirical fraction of truths below the q-quantile is
        Phi(Phi^{-1}(q)) = q -- perfect calibration.
        """
        rng = np.random.default_rng(0)
        N = 2000; M = 500
        y_true = rng.standard_normal(N)
        # Independent predictive samples from the true distribution
        samples = rng.standard_normal((M, N))
        ece = expected_calibration_error(samples, y_true, n_bins=10)
        assert ece < 0.05, f"ECE too high for well-calibrated: {ece}"

    def test_ece_overconfident(self):
        """Overconfident predictions -> high ECE."""
        rng = np.random.default_rng(0)
        N = 1000; M = 200
        y_true = rng.standard_normal(N)
        # samples cluster much too tightly around y_true (sigma=0.1 << 1.0)
        samples = y_true[None, :] + 0.1 * rng.standard_normal((M, N))
        ece = expected_calibration_error(samples, y_true, n_bins=10)
        assert ece > 0.15, f"ECE not high for overconfident: {ece}"

    def test_crps_gaussian_vs_empirical(self):
        """Empirical CRPS converges to closed-form CRPS as M -> infinity."""
        from bayespinn_inv.calibration.metrics import crps_gaussian
        rng = np.random.default_rng(0)
        N = 100
        mu = rng.standard_normal(N)
        sigma = np.full(N, 0.5)
        y = mu + sigma * rng.standard_normal(N)
        crps_cf = crps_gaussian(mu, sigma, y).mean()
        # M = 500 samples
        samples = mu[None, :] + sigma[None, :] * rng.standard_normal((500, N))
        crps_emp = crps_empirical(samples, y).mean()
        # Within 10% for this sample size
        assert abs(crps_cf - crps_emp) / abs(crps_cf) < 0.1

    def test_nll_under_correct_model(self):
        """NLL = 0.5*log(2*pi*sigma^2) + 0.5 (in expectation) when sigma is right."""
        rng = np.random.default_rng(0)
        N = 10000
        mu = np.zeros(N)
        sigma = np.full(N, 1.0)
        y = rng.standard_normal(N)
        nll = gaussian_nll(mu, sigma, y)
        # E[NLL] = 0.5 log(2 pi) + 0.5 ~ 1.4189
        assert abs(nll - 1.4189) < 0.05


# ============================================================================
# End-to-end smoke test
# ============================================================================

class TestEndToEndSmoke:
    """Confirm the training stack starts on a tiny problem without NaN."""

    def test_training_no_nan_in_5_epochs(self):
        from bayespinn_inv.data.datasets import build_dataset
        from bayespinn_inv.training.trainer import PINNTrainer, TrainConfig
        torch.manual_seed(0)
        scaling = Scaling.for_material(SILICON, T=300.0)
        L_scaled = float(scaling.x_to_scaled(torch.tensor(1e-6)))
        V_max_s = 0.3 / scaling.V_T
        cfg_net = PINNConfig(in_dim=2, hidden_dim=24, num_blocks=2,
                              fourier_features=8, doping_dim=16, seed=0,
                              x_scaled_extent=L_scaled,
                              V_a_scaled_extent=V_max_s)
        net = SemiconductorPINN(cfg_net)
        examples, _ = build_dataset(
            n_per_family={"step": 1}, n_points=32,
            domain_si=(0., 1e-6), scaling=scaling, n_anchor=16, seed=0,
        )
        tcfg = TrainConfig(lr=1e-3, n_epochs=5, batch_size=32,
                            curriculum_epochs=3, bias_max=0.2,
                            use_ntk_weights=False, log_every=10,
                            ckpt_every=100, seed=0, domain_si=(0., 1e-6))
        trainer = PINNTrainer(net, scaling, SILICON, examples, tcfg)
        hist = trainer.train()
        last = hist[-1]
        assert math.isfinite(last["loss_total"]), \
            f"Training produced non-finite loss: {last}"
