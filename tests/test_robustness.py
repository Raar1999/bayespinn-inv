"""
Adversarial / property-based tests: find the failure modes before users do.

Everything here probes an edge the happy path never touches -- extreme doping,
degenerate grids, malformed inputs, NaN/Inf, zero variance. Several of these
correspond to real defects found in the audit (the LDD profile returned NaN at
every bias; an asymmetric step returned currents four orders of magnitude above
anything physical, both while reporting success).
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bayespinn_inv.calibration.metrics import (
    crps_empirical,
    crps_gaussian,
    ece_floor_for_ensemble,
    expected_calibration_error,
    fit_temperature_regression,
    gaussian_nll,
)
from bayespinn_inv.inverse.charts import anchor_signed_to_grid
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    DopingChartError,
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
    bernoulli,
)
from bayespinn_inv.surrogate.iv_surrogate import SymlogTransform


def _solver(N=201):
    sc = Scaling.for_material(SILICON, T=300.0)
    L_s = float(sc.x_to_scaled(np.float64(1e-6)))
    return sc, ScharfetterGummel1D(Grid1D.uniform(L_s, N), sc, SILICON, SGConfig())


# ===========================================================================
# Device families the project claims to support must not produce NaN
# ===========================================================================

class TestDeviceFamilyRobustness:
    """Regression for BUG-10: undamped Newton overflowed to inf -> NaN."""

    @staticmethod
    def _families(xa):
        xj = 0.5e-6
        return {
            "step_symmetric": np.where(xa < xj, -1e22, 1e22),
            "step_asymmetric": np.where(xa < xj, -1e21, 5e22),
            "step_very_asymmetric": np.where(xa < xj, -1e20, 1e24),
            "graded": 1e22 * np.tanh((xa - xj) / 1.5e-7),
            "ldd": np.where(xa < 0.35e-6, -1e22,
                            np.where(xa < 0.6e-6, 5e21, 5e23)),
            "defect": (np.where(xa < xj, -1e22, 1e22)
                       + 5e21 * np.exp(-0.5 * ((xa - 0.3e-6) / 5e-8) ** 2)),
            "heavy": np.where(xa < xj, -1e24, 1e24),
            "light": np.where(xa < xj, -1e20, 1e20),
        }

    @pytest.mark.parametrize("bias", [0.0, 0.3, 0.6, 0.9])
    def test_all_families_finite_and_converged(self, bias):
        sc, sg = _solver()
        xa = np.linspace(0.0, 1e-6, 16)
        for name, C in self._families(xa).items():
            st = sg.solve(anchor_signed_to_grid(C, sg.grid.N), bias)
            assert np.all(np.isfinite(st.phi)), f"{name} @ {bias}V: phi has NaN"
            assert np.all(np.isfinite(st.n)), f"{name} @ {bias}V: n has NaN"
            assert np.all(np.isfinite(st.p)), f"{name} @ {bias}V: p has NaN"
            assert np.isfinite(st.terminal_current), f"{name} @ {bias}V: I is NaN"
            assert st.converged, f"{name} @ {bias}V did not converge"

    def test_currents_are_physically_plausible(self):
        """A 1 um Si diode cannot carry 1e9 A/m^2 at 0.6 V."""
        sc, sg = _solver()
        xa = np.linspace(0.0, 1e-6, 16)
        for name, C in self._families(xa).items():
            I = sg.solve(anchor_signed_to_grid(C, sg.grid.N), 0.6).terminal_current
            assert abs(I) < 1e8, f"{name}: implausible current {I:.3e} A/m^2"

    def test_carrier_densities_stay_positive(self):
        sc, sg = _solver()
        xa = np.linspace(0.0, 1e-6, 16)
        for name, C in self._families(xa).items():
            st = sg.solve(anchor_signed_to_grid(C, sg.grid.N), 0.5)
            assert np.all(st.n > 0), f"{name}: non-positive electron density"
            assert np.all(st.p > 0), f"{name}: non-positive hole density"


# ===========================================================================
# Extreme inputs
# ===========================================================================

class TestExtremeInputs:

    @pytest.mark.parametrize("level", [1e19, 1e20, 1e22, 1e24, 1e25])
    def test_doping_magnitude_sweep(self, level):
        sc, sg = _solver()
        x = sc.x_to_si(np.asarray(sg.grid.x))
        C = np.where(x < x.max() / 2, -level, level)
        st = sg.solve(C, 0.4)
        assert np.isfinite(st.terminal_current)
        assert st.converged

    def test_zero_doping_is_intrinsic_not_a_crash(self):
        sc, sg = _solver()
        C = np.zeros(sg.grid.N)
        st = sg.solve(C, 0.2)
        assert np.all(np.isfinite(st.phi))
        # intrinsic material: n = p = n_i everywhere at zero net doping
        assert np.isfinite(st.terminal_current)

    def test_reverse_bias_does_not_explode(self):
        sc, sg = _solver()
        x = sc.x_to_si(np.asarray(sg.grid.x))
        C = np.where(x < x.max() / 2, -1e22, 1e22)
        for V in (-0.5, -2.0, -5.0):
            st = sg.solve(C, V)
            assert np.isfinite(st.terminal_current), f"reverse {V} V gave NaN"

    def test_tiny_grid(self):
        sc, sg = _solver(N=5)
        x = sc.x_to_si(np.asarray(sg.grid.x))
        C = np.where(x < x.max() / 2, -1e22, 1e22)
        st = sg.solve(C, 0.3)
        assert np.isfinite(st.terminal_current)

    def test_grid_mismatched_doping_raises_instead_of_resampling(self):
        """``CHART-01``: the old contract was the defect, so it is inverted here.

        Until generation 8 this test asserted the opposite -- "any-length profile
        is interpolated" -- and that documented contract is how six generations of
        identifiability results were published in an unnamed parameterisation
        chart. A length-9 array on a 201-node grid is not a profile; it is a
        parameter vector in a chart nobody has said out loud, and the solver now
        refuses it.

        The two halves are the controls: the bare array must raise, and the same
        numbers reconstructed through the named operator must go through and give
        a finite current.
        """
        sc, sg = _solver(N=201)
        C = np.where(np.linspace(0, 1, 9) < 0.5, -1e22, 1e22)
        with pytest.raises(DopingChartError, match=r"CHART-01|chart"):
            sg.solve(C, 0.3)
        st = sg.solve(anchor_signed_to_grid(C, sg.grid.N), 0.3)
        assert st.doping.shape[0] == 201
        assert np.isfinite(st.terminal_current)

    @pytest.mark.filterwarnings("ignore::scipy.sparse.linalg.MatrixRankWarning")
    def test_non_finite_doping_is_not_silently_accepted(self):
        """NaN in must not become a plausible-looking number out.

        The singular-matrix warning from the linear solve is the *expected*
        symptom here and is filtered so the suite stays clean.
        """
        sc, sg = _solver()
        C = np.where(sc.x_to_si(np.asarray(sg.grid.x)) < 5e-7, -1e22, 1e22)
        C[10] = np.nan
        st = sg.solve(C, 0.3)
        assert not (st.converged and np.isfinite(st.terminal_current)), (
            "NaN doping produced a finite 'converged' current")


# ===========================================================================
# Transforms
# ===========================================================================

class TestSymlogRobustness:

    def test_roundtrip_over_the_full_range(self):
        t = SymlogTransform(I0=1e-6)
        I = np.concatenate([-np.logspace(-9, 6, 40), [0.0],
                            np.logspace(-9, 6, 40)])
        assert np.allclose(t.inverse(t.forward(I)), I, rtol=1e-8, atol=1e-12)

    def test_zero_maps_to_zero(self):
        t = SymlogTransform()
        assert float(t.forward(0.0)) == 0.0
        assert float(t.inverse(0.0)) == 0.0

    def test_monotone_and_sign_preserving(self):
        t = SymlogTransform()
        I = np.linspace(-1e5, 1e5, 501)
        s = t.forward(I)
        assert np.all(np.diff(s) > 0)
        assert np.all(np.sign(s) == np.sign(I))

    def test_torch_and_numpy_agree_at_extremes(self):
        t = SymlogTransform()
        I = np.array([-1e6, -1.0, 0.0, 1e-9, 1e6])
        a = t.forward(I)
        b = t.forward(torch.tensor(I, dtype=torch.float64)).numpy()
        assert np.allclose(a, b, rtol=1e-10)

    def test_inverse_saturates_rather_than_overflowing(self):
        t = SymlogTransform()
        assert np.all(np.isfinite(t.inverse(np.array([-1e3, 1e3]))))


class TestBernoulliProperties:

    def test_strictly_decreasing(self):
        x = np.linspace(-50, 50, 4001)
        assert np.all(np.diff(bernoulli(x)) < 0)

    def test_never_negative(self):
        """B(x) = x/(exp(x)-1) > 0 for all real x; it underflows to +0 only."""
        x = np.concatenate([-np.logspace(-8, 3, 200), np.logspace(-8, 3, 200)])
        b = bernoulli(x)
        assert np.all(b >= 0.0)
        # strictly positive wherever double precision can represent it
        rep = np.abs(x) < 700.0
        assert np.all(b[rep] > 0.0)

    def test_series_matches_expm1_at_the_branch_seam(self):
        eps = 1e-4
        lo = float(bernoulli(eps * (1 - 1e-9)))
        hi = float(bernoulli(eps * (1 + 1e-9)))
        assert abs(lo - hi) < 1e-12, "discontinuity at the small-x branch seam"


# ===========================================================================
# Calibration metrics
# ===========================================================================

class TestCalibrationRobustness:

    def test_zero_variance_ensemble_does_not_divide_by_zero(self):
        mu = np.zeros(10)
        sigma = np.zeros(10)
        y = np.zeros(10)
        assert np.isfinite(gaussian_nll(mu, sigma, y))
        assert np.all(np.isfinite(crps_gaussian(mu, sigma, y)))

    def test_identical_samples_give_finite_crps(self):
        s = np.ones((5, 20))
        y = np.ones(20)
        assert np.all(np.isfinite(crps_empirical(s, y)))

    def test_crps_empirical_matches_gaussian_closed_form(self):
        rng = np.random.default_rng(0)
        M, N = 4000, 40
        mu = rng.standard_normal(N)
        sigma = np.abs(rng.standard_normal(N)) + 0.5
        samples = mu + sigma * rng.standard_normal((M, N))
        y = rng.standard_normal(N)
        a = crps_empirical(samples, y).mean()
        b = crps_gaussian(mu, sigma, y).mean()
        assert a == pytest.approx(b, rel=0.05)

    def test_temperature_fit_recovers_a_known_inflation(self):
        rng = np.random.default_rng(1)
        N = 20000
        mu = np.zeros(N)
        sigma = np.ones(N)
        y = 3.0 * rng.standard_normal(N)      # true sigma is 3x claimed
        T = fit_temperature_regression(mu, sigma, y, n_iters=500, lr=0.1)
        assert pytest.approx(3.0, rel=0.05) == T

    def test_ece_floor_is_positive_and_decreasing_in_M(self):
        floors = [ece_floor_for_ensemble(M) for M in (3, 5, 10, 20)]
        assert all(f > 0 for f in floors)
        assert floors == sorted(floors, reverse=True)

    def test_perfect_ensemble_scores_at_its_floor(self):
        """Guards the interpretation: small-M ECE cannot reach zero."""
        rng = np.random.default_rng(7)
        M, N = 5, 4000
        samples = rng.standard_normal((M, N))
        y = rng.standard_normal(N)
        got = expected_calibration_error(samples, y)
        assert got == pytest.approx(ece_floor_for_ensemble(M), abs=0.02)


# ===========================================================================
# Provenance
# ===========================================================================

class TestProvenance:

    def test_manifest_records_commit_and_environment(self, tmp_path):
        from bayespinn_inv.utils.provenance import RunManifest
        man = RunManifest.create("unit-test", config={"a": 1}, seed=3)
        man.add_result("x", 42)
        p = man.write(tmp_path)
        import json
        # AUDIT_g6 3.2a (BUG-14 class): RunManifest.write() writes UTF-8, so the
        # read must say so. Without it this decodes with the platform encoding --
        # cp1252 on the Windows CI leg -- and any non-ASCII in the environment
        # block (processor string, locale-dependent fields) either raises or
        # mis-decodes silently.
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["experiment"] == "unit-test"
        assert d["seed"] == 3
        assert d["results"]["x"] == 42
        assert "python" in d["environment"]
        assert "numpy" in d["environment"]
        assert "git" in d and "dirty" in d["git"]

    def test_manifest_is_json_serializable_with_numpy(self, tmp_path):
        from bayespinn_inv.utils.provenance import RunManifest
        man = RunManifest.create("np-test")
        man.add_result("arr", np.float64(1.5))
        man.write(tmp_path)      # must not raise
