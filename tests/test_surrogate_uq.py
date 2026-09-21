"""Interface and behaviour tests for the surrogate uncertainty backends.

The point of ``bayesian/surrogate_uq.py`` is that MC-dropout, SWAG and the
deep ensemble become *interchangeable* -- one evaluation path, three
uncertainty sources. If they drift apart in shape, dtype or convention the
comparison in ``scripts/run_uq_benchmark.py`` silently stops being a
comparison. These tests pin that contract down.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from bayespinn_inv.bayesian.surrogate_uq import MCDropoutSurrogate, SWAGSurrogate
from bayespinn_inv.bayesian.swag import SWAGConfig, SWAGRecorder
from bayespinn_inv.surrogate.iv_surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SurrogatePrediction,
    train_surrogate,
)

N_ANCHOR = 16
N_FEAT = N_ANCHOR + 1


@pytest.fixture(scope="module")
def fitted():
    """A tiny synthetic regression, trained once for the whole module."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(160, N_FEAT))
    Y = 2.0 * X[:, 0] + X[:, 1] - 0.5 * X[:, -1]
    norm = Normalizer.fit(X)

    members = []
    for s in range(3):
        m = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=32,
                                          n_layers=2, seed=s))
        train_surrogate(m, X, Y, norm, epochs=80)
        members.append(m)

    drop = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=32,
                                         n_layers=2, dropout=0.1, seed=0))
    train_surrogate(drop, X, Y, norm, epochs=80)

    swa = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=32,
                                        n_layers=2, seed=0))
    rec = SWAGRecorder(swa, SWAGConfig(max_rank=5, T_samples=12, seed=0))
    for _ in range(8):
        train_surrogate(swa, X, Y, norm, epochs=10, lr=1e-3)
        rec.collect()

    return dict(
        norm=norm,
        doping=rng.normal(size=N_ANCHOR),
        biases=np.linspace(0.0, 20.0, 7),
        ensemble=SurrogateEnsemble(members, norm),
        mc_dropout=MCDropoutSurrogate(drop, norm, n_samples=12, seed=0),
        swag=SWAGSurrogate(swa, rec, norm),
        swa_model=swa,
    )


BACKENDS = ["ensemble", "mc_dropout", "swag"]


class TestUnifiedInterface:
    """Every backend must be substitutable for every other."""

    @pytest.mark.parametrize("name", BACKENDS)
    def test_prediction_type_and_shapes(self, fitted, name):
        b = fitted[name]
        p = b.predict(fitted["doping"], fitted["biases"])
        B = len(fitted["biases"])
        assert isinstance(p, SurrogatePrediction)
        assert p.mean_symlog.shape == (B,)
        assert p.std_symlog.shape == (B,)
        assert p.mean_current.shape == (B,)
        assert p.samples_symlog.shape == (b.M, B)
        assert p.mean_current_linear.shape == (B,)

    @pytest.mark.parametrize("name", BACKENDS)
    def test_all_finite(self, fitted, name):
        p = fitted[name].predict(fitted["doping"], fitted["biases"])
        for field in ("mean_symlog", "std_symlog", "mean_current",
                      "samples_symlog", "mean_current_linear"):
            assert np.all(np.isfinite(getattr(p, field))), field

    @pytest.mark.parametrize("name", BACKENDS)
    def test_sigma_is_nonnegative_and_nonzero(self, fitted, name):
        """A UQ backend whose sigma is identically zero is not doing UQ."""
        p = fitted[name].predict(fitted["doping"], fitted["biases"])
        assert np.all(p.std_symlog >= 0.0)
        assert float(np.max(p.std_symlog)) > 0.0

    @pytest.mark.parametrize("name", BACKENDS)
    def test_mean_and_std_match_the_samples(self, fitted, name):
        """`mean_symlog`/`std_symlog` must be the moments of `samples_symlog`.

        If a backend computed them any other way the three would not be on a
        common footing and the cross-method comparison would be invalid.
        """
        p = fitted[name].predict(fitted["doping"], fitted["biases"])
        assert np.allclose(p.mean_symlog, p.samples_symlog.mean(0), atol=1e-6)
        assert np.allclose(p.std_symlog, p.samples_symlog.std(0), atol=1e-6)


class TestMCDropout:

    def test_requires_a_dropout_trained_model(self, fitted):
        """Dropout at test time without dropout at train time is meaningless."""
        plain = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=16,
                                              n_layers=2, dropout=0.0))
        with pytest.raises(ValueError, match="dropout"):
            MCDropoutSurrogate(plain, fitted["norm"])

    def test_is_reproducible(self, fitted):
        a = fitted["mc_dropout"].predict(fitted["doping"], fitted["biases"])
        b = fitted["mc_dropout"].predict(fitted["doping"], fitted["biases"])
        assert np.array_equal(a.samples_symlog, b.samples_symlog)

    def test_does_not_disturb_the_global_rng(self, fitted):
        """AUDIT_MASTER API-03: a model must not mutate the caller's RNG."""
        torch.manual_seed(1234)
        before = torch.randn(4)
        torch.manual_seed(1234)
        fitted["mc_dropout"].predict(fitted["doping"], fitted["biases"])
        after = torch.randn(4)
        assert torch.equal(before, after)

    def test_leaves_dropout_disabled_afterwards(self, fitted):
        """A stray train-mode Dropout would make later `eval()` calls random."""
        fitted["mc_dropout"].predict(fitted["doping"], fitted["biases"])
        drops = [m for m in fitted["mc_dropout"].model.modules()
                 if isinstance(m, torch.nn.Dropout)]
        assert drops and all(not d.training for d in drops)


class TestSWAG:

    def test_requires_collected_snapshots(self, fitted):
        net = IVSurrogate(IVSurrogateConfig(doping_dim=N_ANCHOR, hidden=16,
                                            n_layers=2))
        empty = SWAGRecorder(net, SWAGConfig(max_rank=4))
        with pytest.raises(ValueError, match="snapshot"):
            SWAGSurrogate(net, empty, fitted["norm"])

    def test_restores_the_model_weights(self, fitted):
        """Sampling writes weights into the net; it must put them back."""
        before = [p.detach().clone() for p in fitted["swa_model"].parameters()]
        fitted["swag"].predict(fitted["doping"], fitted["biases"])
        after = list(fitted["swa_model"].parameters())
        assert all(torch.equal(a, b) for a, b in zip(before, after))

    def test_is_reproducible(self, fitted):
        a = fitted["swag"].predict(fitted["doping"], fitted["biases"])
        b = fitted["swag"].predict(fitted["doping"], fitted["biases"])
        assert np.array_equal(a.samples_symlog, b.samples_symlog)


class TestBackendsAreComparable:

    def test_same_input_gives_same_shaped_output_across_backends(self, fitted):
        preds = {n: fitted[n].predict(fitted["doping"], fitted["biases"])
                 for n in BACKENDS}
        shapes = {p.mean_symlog.shape for p in preds.values()}
        assert len(shapes) == 1

    def test_means_are_in_the_same_ballpark(self, fitted):
        """All three fit the same data, so their means must broadly agree.

        This catches a transform/convention mismatch (e.g. one backend
        aggregating in linear space and another in symlog), which would make
        the benchmark compare quantities that are not the same thing.
        """
        preds = [fitted[n].predict(fitted["doping"], fitted["biases"]).mean_symlog
                 for n in BACKENDS]
        spread = np.max(np.abs(preds[0] - preds[1])) + np.max(np.abs(preds[0] - preds[2]))
        scale = max(float(np.max(np.abs(preds[0]))), 1.0)
        assert spread < 20.0 * scale
