"""Regression tests for AUDIT_g0 GRAD-02 and seed item S-3.

GRAD-02
-------
``pinn/losses.py::ohmic_boundary_values`` selected the majority carrier with

    torch.where(pos, 0.5 * (C + sqrt(C**2 + 4)), 1.0 / (0.5 * (-C + sqrt(C**2 + 4))))

``torch.where`` evaluates **both** branches. For large positive ``C_s``,
``-C + sqrt(C**2 + 4)`` underflows to exactly ``0.0`` (measured: ``1.490116e-08``
at ``C_s = 1e8``, ``0.0`` at ``C_s = 1e9``), so the discarded branch is ``inf`` and
the backward pass computes ``0 * inf = NaN``, which contaminates the gradient of
the *selected* branch.

Bisected onset (40 steps): the last finite input is ``C_s = 1.3922e+08`` and the
first non-finite input agrees with it to 7 significant figures, i.e.
**N = 1.3922e24 m^-3**. The solver's own documented doping range is 1e21-1e25
m^-3 (``scharfetter_gummel.py``, BUG-11 comment), so **21.4% of the documented
envelope by decades** returned NaN gradients.

No published number was affected -- the protocol bands reach only ``C_s <= 8.0e6``
-- so this is a latent defect in exported public API, not a wrong result.

**AH-02 applies.** The envelope under test is the solver's own claim. Narrowing it
to make these tests pass is an automatic discard, not a fix.

S-3
---
``solvers/scharfetter_gummel.py::_ohmic_bc`` and
``pinn/losses.py::ohmic_boundary_values`` are independent implementations of the
same physics -- the duplication that caused BUG-11. Their *values* agreed across
``C_s = 1e0 ... 1e11`` before this generation; their *gradients* did not. These
tests pin both.

Reference
---------
At an ohmic contact, charge neutrality ``n - p - C = 0`` with ``n * p = 1`` in
scaled units gives ``n = (C + sqrt(C**2 + 4)) / 2``, so

    log n = asinh(C / 2)        d(log n)/dC = 1 / sqrt(4 + C**2)

both finite for every finite ``C``. The analytic derivative is what the gradient
tests compare against, so they check correctness and not merely finiteness.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.pinn.losses import ohmic_boundary_values

#: The doping envelope the solver documents, in m^-3.
ENVELOPE_SI = (1e21, 1e25)

#: The same envelope in scaled units, C_s = N / n_i.
ENVELOPE_CS = (ENVELOPE_SI[0] / SILICON.n_i, ENVELOPE_SI[1] / SILICON.n_i)

#: Resolution of the sweep: 0.02 decades, far finer than the ~0.5-decade feature.
N_SWEEP = 201


def _envelope_points() -> np.ndarray:
    """Log-spaced scaled doping across the documented envelope, both signs."""
    mag = np.logspace(
        math.log10(ENVELOPE_CS[0]), math.log10(ENVELOPE_CS[1]), N_SWEEP
    )
    return np.concatenate([mag, -mag])


def _grad_of(field: str, c_value: float) -> float:
    """d(field)/d(C_s) at ``c_value``, taken through ``ohmic_boundary_values``."""
    c = torch.tensor(float(c_value), dtype=torch.float64, requires_grad=True)
    zero = torch.zeros((), dtype=torch.float64)
    out = ohmic_boundary_values(c, c, zero)[field]
    out.backward()
    assert c.grad is not None
    return float(c.grad)


ALL_FIELDS = (
    "phi_s_left",
    "phi_s_right",
    "log_n_left",
    "log_n_right",
    "log_p_left",
    "log_p_right",
)


class TestGradientsAreFiniteAcrossTheDocumentedEnvelope:
    """SPEC-g0-4: no non-finite gradient at any finite input in 1e21-1e25 m^-3."""

    @pytest.mark.parametrize("field", ALL_FIELDS)
    def test_no_non_finite_gradient(self, field: str) -> None:
        bad = []
        for c_value in _envelope_points():
            g = _grad_of(field, c_value)
            if not math.isfinite(g):
                bad.append((c_value, g))
        assert not bad, (
            f"AUDIT_g0 GRAD-02 -- d({field})/dC_s is non-finite at {len(bad)} of "
            f"{2 * N_SWEEP} points inside the documented 1e21-1e25 m^-3 envelope. "
            f"First: C_s={bad[0][0]:.4e} (N={bad[0][0] * SILICON.n_i:.4e} m^-3) "
            f"-> {bad[0][1]}"
        )

    def test_values_stay_finite_too(self) -> None:
        """Values were already correct; this pins them so a fix cannot regress them."""
        for c_value in _envelope_points():
            c = torch.tensor(float(c_value), dtype=torch.float64)
            out = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
            for field, value in out.items():
                assert torch.isfinite(value).all(), f"{field} non-finite at C_s={c_value:.3e}"


class TestGradientsMatchTheAnalyticDerivative:
    """Finiteness is not correctness: compare against d(log n)/dC = 1/sqrt(4+C^2)."""

    @pytest.mark.parametrize(
        "c_value", [1e0, -1e0, 1e3, 1e5, 1e7, 1.4e8, 1e9, -1e7, -1e9]
    )
    def test_log_n_left_gradient(self, c_value: float) -> None:
        expected = 1.0 / math.sqrt(4.0 + c_value ** 2)
        got = _grad_of("log_n_left", c_value)
        assert math.isfinite(got), f"non-finite gradient at C_s={c_value:.3e}"
        assert got == pytest.approx(expected, rel=1e-10), (
            f"d(log n)/dC at C_s={c_value:.3e}: expected {expected:.6e}, got {got:.6e}"
        )

    @pytest.mark.parametrize("c_value", [1e0, -1e0, 1e5, 1e9])
    def test_log_p_is_the_mirror_of_log_n(self, c_value: float) -> None:
        """n * p = 1 exactly, so log p = -log n and the gradients are opposite."""
        assert _grad_of("log_p_left", c_value) == pytest.approx(
            -_grad_of("log_n_left", c_value), rel=1e-10
        )


class TestMassActionHoldsExactly:
    """PH-07: the returned pair must satisfy n * p = 1 in scaled units."""

    def test_np_product_is_unity_across_the_envelope(self) -> None:
        worst = 0.0
        for c_value in _envelope_points():
            c = torch.tensor(float(c_value), dtype=torch.float64)
            out = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
            product = float(torch.exp(out["log_n_left"] + out["log_p_left"]))
            worst = max(worst, abs(product - 1.0))
        assert worst < 1e-12, f"max |n*p - 1| = {worst:.3e} over the envelope"

    def test_charge_neutrality_holds_across_the_envelope(self) -> None:
        """n - p - C = 0, the other equation defining the contact."""
        worst = 0.0
        for c_value in _envelope_points():
            c = torch.tensor(float(c_value), dtype=torch.float64)
            out = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
            n = float(torch.exp(out["log_n_left"]))
            p = float(torch.exp(out["log_p_left"]))
            worst = max(worst, abs(n - p - c_value) / max(abs(c_value), 1.0))
        assert worst < 1e-12, f"max relative |n - p - C| = {worst:.3e}"


class TestTheTwoOhmicImplementationsAgree:
    """S-3: duplicate physics. Until it is one definition, pin the equivalence."""

    def test_values_agree_with_the_solver_implementation(self) -> None:
        from bayespinn_inv.physics.scaling import Scaling
        from bayespinn_inv.solvers.scharfetter_gummel import (
            Grid1D,
            ScharfetterGummel1D,
            SGConfig,
        )

        scaling = Scaling.for_material(SILICON, T=300.0)
        sg = ScharfetterGummel1D(
            Grid1D.uniform(1.0, 11), scaling, SILICON, SGConfig()
        )
        worst_phi = worst_n = worst_p = 0.0
        for c_value in _envelope_points():
            phi_ref, n_ref, p_ref = sg._ohmic_bc(float(c_value))
            c = torch.tensor(float(c_value), dtype=torch.float64)
            out = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
            phi = float(out["phi_s_left"])
            n = float(torch.exp(out["log_n_left"]))
            p = float(torch.exp(out["log_p_left"]))
            worst_phi = max(worst_phi, abs(phi - phi_ref) / max(abs(phi_ref), 1e-300))
            worst_n = max(worst_n, abs(n - n_ref) / max(abs(n_ref), 1e-300))
            worst_p = max(worst_p, abs(p - p_ref) / max(abs(p_ref), 1e-300))
        assert worst_phi < 1e-12, f"phi disagrees by {worst_phi:.3e} relative"
        assert worst_n < 1e-12, f"n disagrees by {worst_n:.3e} relative"
        assert worst_p < 1e-12, f"p disagrees by {worst_p:.3e} relative"


class TestBiasConventionIsUnchanged:
    """PH-04: a gradient fix must not move the bias convention."""

    @pytest.mark.parametrize("v_applied", [0.0, 0.25, -0.25, 1.0])
    def test_right_contact_potential_drops_by_the_applied_bias(
        self, v_applied: float
    ) -> None:
        c = torch.tensor(1e7, dtype=torch.float64)
        v = torch.tensor(float(v_applied), dtype=torch.float64)
        out = ohmic_boundary_values(c, c, v)
        at_zero = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
        shift = float(out["phi_s_right"] - at_zero["phi_s_right"])
        assert shift == pytest.approx(-v_applied, abs=1e-12)

    def test_left_contact_is_the_reference(self) -> None:
        c = torch.tensor(1e7, dtype=torch.float64)
        a = ohmic_boundary_values(c, c, torch.zeros((), dtype=torch.float64))
        b = ohmic_boundary_values(c, c, torch.tensor(0.7, dtype=torch.float64))
        assert float(a["phi_s_left"]) == pytest.approx(float(b["phi_s_left"]), abs=1e-15)


# ---------------------------------------------------------------------------
# AUDIT_g0 GRAD-03 -- found by the generation-0 falsifier candidate (g0c5).
#
# The tests above run in float64, where the NaN onset sits at C_s = 1.3922e8 and
# covers the top 21.4% of the envelope. Networks in this repository train in
# float32 (`TrainConfig.dtype`, `IVSurrogate`), and float32 has far less headroom
# before `-C + sqrt(C**2 + 4)` cancels to exactly zero.
#
# Measured on the pre-fix tree: the float32 onset is C_s = 7.079e3, i.e.
# N = 7.079e19 m^-3 -- *below* the envelope's lower bound. All 41 sampled points
# from N = 1e21 to 1e25 returned NaN gradients: 100% of the documented envelope,
# not 21.4%.
#
# Blast radius, measured rather than assumed: the only caller,
# `losses.boundary_residuals`, receives `C_s_bdy` as data with no
# `requires_grad_`, so autograd never walks the d/dC_s path. A PINN training step
# at N = 1e21, 1e24 and 1e25 m^-3 in float32 produced NaN in **0 of 26** weight
# gradient tensors. D1 and ADR-0004 are therefore *not* confounded by this defect.
# It fires only when doping itself carries a gradient -- inverse design, and the
# Jacobian that the identifiability analysis is built on.
#
# These tests are additive. No test above was edited, skipped or relaxed; the
# gate moves in the direction of strictness only (operator ruling section 3).
# ---------------------------------------------------------------------------

def _grad_in(field: str, c_value: float, dtype: torch.dtype) -> float:
    """d(field)/d(C_s) at ``c_value``, evaluated in ``dtype``."""
    c = torch.tensor(float(c_value), dtype=dtype, requires_grad=True)
    out = ohmic_boundary_values(c, c, torch.zeros((), dtype=dtype))[field]
    out.backward()
    assert c.grad is not None
    return float(c.grad)


class TestGradientsAreFiniteInEveryTrainingDtype:
    """SPEC-g0-4 holds in the dtype the networks actually use, not only float64."""

    @pytest.mark.parametrize("dtype", [torch.float64, torch.float32])
    @pytest.mark.parametrize("field", ["log_n_left", "log_p_left", "phi_s_left"])
    def test_no_non_finite_gradient(self, dtype: torch.dtype, field: str) -> None:
        bad = [
            c for c in _envelope_points()
            if not math.isfinite(_grad_in(field, c, dtype))
        ]
        assert not bad, (
            f"AUDIT_g0 GRAD-03 -- d({field})/dC_s is non-finite at {len(bad)} of "
            f"{2 * N_SWEEP} points in {dtype} inside the documented envelope. "
            f"First: C_s={bad[0]:.4e} (N={bad[0] * SILICON.n_i:.4e} m^-3)"
        )

    @pytest.mark.parametrize(
        "dtype,rel", [(torch.float64, 1e-12), (torch.float32, 1e-5)]
    )
    def test_gradient_matches_the_analytic_derivative(
        self, dtype: torch.dtype, rel: float
    ) -> None:
        """Finiteness is not correctness -- compare against 1/sqrt(4 + C^2).

        The tolerance is set by the dtype's epsilon, not by what the code happens
        to produce: float32 carries ~7 decimal digits, so 1e-5 is loose enough to
        be honest and tight enough that a wrong formula still fails.
        """
        worst, worst_at = 0.0, None
        for c_value in _envelope_points():
            got = _grad_in("log_n_left", c_value, dtype)
            expected = 1.0 / math.sqrt(4.0 + float(c_value) ** 2)
            assert math.isfinite(got), f"non-finite at C_s={c_value:.3e} in {dtype}"
            err = abs(got - expected) / expected
            if err > worst:
                worst, worst_at = err, c_value
        assert worst < rel, (
            f"d(log n)/dC_s in {dtype}: max relative error {worst:.3e} at "
            f"C_s={worst_at:.4e}, tolerance {rel:.0e}"
        )


class TestTheDefectDoesNotReachNetworkWeights:
    """The measured blast radius, pinned so a future change cannot widen it silently."""

    @pytest.mark.parametrize("doping_si", [1e21, 1e24, 1e25])
    def test_pinn_boundary_loss_has_finite_weight_gradients(
        self, doping_si: float
    ) -> None:
        from bayespinn_inv.pinn.losses import boundary_residuals
        from bayespinn_inv.pinn.network import PINNConfig, SemiconductorPINN

        cfg = PINNConfig()
        net = SemiconductorPINN(cfg).to(dtype=torch.float32)
        c_s = doping_si / SILICON.n_i
        # Exactly the trainer's construction: boundary doping is data, not a leaf
        # requiring grad (trainer.py:262).
        x_b = torch.tensor([[0.0], [1.0]], dtype=torch.float32)
        v_b = torch.full((2, 1), 0.5, dtype=torch.float32)
        latent = torch.zeros((2, cfg.doping_dim), dtype=torch.float32)
        c_b = torch.tensor([[-c_s], [c_s]], dtype=torch.float32)

        net.zero_grad(set_to_none=True)
        residuals = boundary_residuals(net, x_b, v_b, latent, c_b)
        loss = sum(torch.mean(r ** 2) for r in residuals.values())
        loss.backward()

        offenders = [
            name for name, p in net.named_parameters()
            if p.grad is not None and not torch.isfinite(p.grad).all()
        ]
        assert not offenders, (
            f"non-finite weight gradients at N={doping_si:.0e} m^-3: {offenders}"
        )
