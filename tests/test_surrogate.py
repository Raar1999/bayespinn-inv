"""Unit tests for the SG-supervised IV surrogate."""

import numpy as np
import torch

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)
from bayespinn_inv.surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    SurrogateEnsemble,
    SymlogTransform,
    build_sg_dataset,
    train_surrogate,
)


class TestSymlog:
    def test_roundtrip(self):
        t = SymlogTransform(I0=1e-6)
        for I in [-1e5, -1.0, 0.0, 1e-3, 4e-8, 2e5]:
            s = t.forward(I)
            back = t.inverse(s)
            assert abs(back - I) <= 1e-6 + 1e-6 * abs(I)

    def test_monotonic_sign_preserving(self):
        t = SymlogTransform()
        assert t.forward(10.0) > t.forward(1.0) > 0
        assert t.forward(-10.0) < t.forward(-1.0) < 0

    def test_torch_and_numpy_agree(self):
        t = SymlogTransform()
        I = np.array([1e-3, 1.0, 1e4])
        s_np = t.forward(I)
        s_t = t.forward(torch.tensor(I)).numpy()
        assert np.allclose(s_np, s_t, rtol=1e-5)


class TestSurrogateTraining:
    def setup_method(self):
        self.scaling = Scaling.for_material(SILICON, T=300.0)
        self.L = float(self.scaling.x_to_scaled(torch.tensor(1e-6)))
        self.sg = ScharfetterGummel1D(Grid1D.uniform(self.L, 201),
                                       self.scaling, SILICON, SGConfig())
        xa = np.linspace(0, 1e-6, 16)
        self.profiles = [np.where(xa < 5e-7, -L, L)
                         for L in [1e21, 5e21, 2e22]]
        self.biases = np.linspace(0.0, 0.5, 7)

    def test_dataset_shapes(self):
        X, Y = build_sg_dataset(self.profiles, self.biases, self.scaling,
                                 self.sg, SymlogTransform())
        assert X.shape == (len(self.profiles) * len(self.biases), 17)
        assert Y.shape == (len(self.profiles) * len(self.biases),)
        assert np.all(np.isfinite(X)) and np.all(np.isfinite(Y))

    def test_train_reduces_loss(self):
        X, Y = build_sg_dataset(self.profiles, self.biases, self.scaling,
                                 self.sg, SymlogTransform())
        norm = Normalizer.fit(X)
        net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64,
                                             n_layers=2, seed=0))
        hist = train_surrogate(net, X, Y, norm, epochs=400, lr=2e-3)
        assert hist[-1] < 0.5 * hist[0], "training should reduce the loss"
        assert np.isfinite(hist[-1])

    def test_ensemble_predicts_with_uncertainty(self):
        X, Y = build_sg_dataset(self.profiles, self.biases, self.scaling,
                                 self.sg, SymlogTransform())
        norm = Normalizer.fit(X)
        members = []
        for m in range(3):
            net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64,
                                                 n_layers=2, seed=m))
            train_surrogate(net, X, Y, norm, epochs=300, lr=2e-3)
            members.append(net)
        ens = SurrogateEnsemble(members, norm, SymlogTransform())
        latent = self.scaling.doping_to_net_input(self.profiles[0])
        pred = ens.predict(latent, self.biases / self.scaling.V_T)
        assert pred.mean_current.shape == (len(self.biases),)
        assert pred.std_symlog.shape == (len(self.biases),)
        assert np.all(pred.std_symlog >= 0)
        # forward bias should give rising current
        assert pred.mean_current[-1] > pred.mean_current[0]
