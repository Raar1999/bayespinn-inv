"""Leakage and protocol invariants for the canonical evaluation splits.

``bayespinn_inv.data.splits`` is the single definition of the experimental
protocol. Every headline number in this project is conditioned on those
splits being what they claim to be, so the claims are asserted here rather
than trusted: overlapping splits would turn every "extrapolation" result into
an interpolation result wearing the wrong label, and nothing downstream would
notice.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bayespinn_inv.data.splits import (
    ProtocolSpec,
    build_level_splits,
    build_sg_labels,
    graded_profile,
    oracle_iv,
    step_profile,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import Grid1D, ScharfetterGummel1D, SGConfig
from bayespinn_inv.surrogate import SymlogTransform

SPEC = ProtocolSpec()
EVAL_SPLITS = ["calibration_val", "test_interp", "test_extrap", "test_family_graded"]


@pytest.fixture(scope="module")
def splits():
    return build_level_splits(SPEC)


class TestNoLeakage:

    @pytest.mark.parametrize("name", EVAL_SPLITS)
    def test_no_evaluation_level_coincides_with_a_training_level(self, splits, name):
        train = splits["train"]
        gap = np.min(np.abs(np.log10(splits[name][:, None] / train[None, :])))
        assert gap > 1e-3, f"{name} has a level within {gap} decades of training"

    def test_every_split_is_nonempty(self, splits):
        for name, levels in splits.items():
            assert levels.size > 0, name

    def test_extrapolation_really_is_outside_the_training_band(self, splits):
        lo, hi = splits["train"].min(), splits["train"].max()
        outside = (splits["test_extrap"] < lo) | (splits["test_extrap"] > hi)
        assert outside.all(), "an 'extrapolation' level lies inside the training band"

    def test_extrapolation_straddles_the_band_on_both_sides(self, splits):
        """One-sided extrapolation would hide half the failure mode."""
        lo, hi = splits["train"].min(), splits["train"].max()
        assert (splits["test_extrap"] < lo).any()
        assert (splits["test_extrap"] > hi).any()

    def test_interpolation_really_is_inside_the_training_band(self, splits):
        lo, hi = splits["train"].min(), splits["train"].max()
        assert ((splits["test_interp"] > lo) & (splits["test_interp"] < hi)).all()

    def test_calibration_split_is_disjoint_from_every_test_split(self, splits):
        val = splits["calibration_val"]
        for name in ("test_interp", "test_extrap", "test_family_graded"):
            gap = np.min(np.abs(np.log10(splits[name][:, None] / val[None, :])))
            assert gap > 1e-6, f"calibration split touches {name}"

    def test_a_deliberately_overlapping_spec_is_rejected(self):
        """The disjointness assertion must actually fire, not just be present."""
        bad = ProtocolSpec(train_lo=1e21, train_hi=2e22,
                           extrap_lo=1e21, extrap_hi=2e22)
        with pytest.raises(AssertionError, match="overlaps"):
            build_level_splits(bad)


class TestProfiles:

    def test_step_profile_is_a_pn_junction(self):
        xa = SPEC.anchor_x()
        C = step_profile(xa, 1e22)
        assert C[0] < 0 < C[-1], "p on the left, n on the right"
        assert np.isclose(abs(C[0]), abs(C[-1]))
        assert len(np.unique(C)) == 2, "a step profile takes exactly two values"

    def test_graded_profile_is_monotone_and_smooth(self):
        xa = np.linspace(0.0, 1e-6, 64)
        C = graded_profile(xa, 1e22)
        assert np.all(np.diff(C) > 0), "tanh grading is monotone increasing"
        assert C[0] < 0 < C[-1]
        # strictly more than two distinct values -- this is the point of the
        # family-transfer split: a *shape* the training set never contains.
        assert len(np.unique(C)) > 10

    def test_profile_families_are_actually_different(self):
        xa = SPEC.anchor_x()
        assert not np.allclose(step_profile(xa, 1e22), graded_profile(xa, 1e22))


@pytest.fixture(scope="module")
def sg():
    scaling = Scaling.for_material(SILICON, T=300.0)
    L_s = float(scaling.x_to_scaled(torch.tensor(SPEC.domain_si[1])))
    return ScharfetterGummel1D(Grid1D.uniform(L_s, 201), scaling,
                               SILICON, SGConfig()), scaling


class TestLabelIntegrity:

    def test_untrustworthy_points_are_dropped_and_counted(self, sg, splits):
        """Near equilibrium the true current is below any solver's floor.

        Those points must be excluded *and* accounted for -- a silent drop
        would make the label count unexplainable (AUDIT_MASTER BUG-04).
        """
        oracle, scaling = sg
        X, Y, integrity = build_sg_labels(oracle, scaling, SymlogTransform(),
                                          splits["train"][:3], SPEC)
        assert integrity["n_used"] + integrity["n_dropped_untrustworthy"] == \
            integrity["n_candidate_labels"]
        assert integrity["n_used"] == X.shape[0] == Y.shape[0]
        assert integrity["n_dropped_untrustworthy"] > 0, (
            "V=0 sits below the oracle noise floor; if nothing was dropped "
            "the trust filter is not running")

    def test_feature_layout_is_doping_latent_then_scaled_bias(self, sg, splits):
        oracle, scaling = sg
        X, _, _ = build_sg_labels(oracle, scaling, SymlogTransform(),
                                  splits["train"][:2], SPEC)
        assert X.shape[1] == SPEC.n_anchor + 1
        # the last column must be bias/V_T, i.e. within the swept range
        assert X[:, -1].max() <= SPEC.bias_max / scaling.V_T + 1e-6
        assert X[:, -1].min() >= 0.0

    def test_oracle_iv_is_warm_started_and_monotone_in_forward_bias(self, sg):
        oracle, scaling = sg
        xa = SPEC.anchor_x()
        C = step_profile(xa, 1e22)
        I, trust = oracle_iv(oracle, C, SPEC.biases, SPEC.trust_snr)
        assert I.shape == trust.shape == SPEC.biases.shape
        good = np.where(trust)[0]
        assert good.size >= 2
        # forward bias raises the current, over every trustworthy point
        assert np.all(np.diff(I[good]) > 0)
