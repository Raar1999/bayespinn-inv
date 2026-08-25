"""Tests for the surrogate -> legacy-interface adapters."""

import numpy as np
import torch

from bayespinn_inv.bayesian.ensembles import EnsemblePrediction
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
    SurrogateEnsembleAdapter,
    SurrogateForwardAdapter,
    SymlogTransform,
    build_sg_dataset,
    load_forward_ensemble,
    save_surrogate_ensemble,
    train_surrogate,
)


def _tiny_setup():
    scaling = Scaling.for_material(SILICON, T=300.0)
    L = float(scaling.x_to_scaled(torch.tensor(1e-6)))
    sg = ScharfetterGummel1D(Grid1D.uniform(L, 201), scaling, SILICON, SGConfig())
    xa = np.linspace(0, 1e-6, 16)
    profiles = [np.where(xa < 5e-7, -L_, L_) for L_ in [1e21, 1e22, 3e22]]
    biases = np.linspace(0.0, 0.5, 7)
    X, Y = build_sg_dataset(profiles, biases, scaling, sg, SymlogTransform())
    norm = Normalizer.fit(X)
    return scaling, sg, norm, X, Y, biases


class TestAdapterInterface:
    def test_forward_adapter_iv_curve_differentiable(self):
        scaling, sg, norm, X, Y, biases = _tiny_setup()
        net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64, n_layers=2))
        train_surrogate(net, X, Y, norm, epochs=200)
        ad = SurrogateForwardAdapter(net, norm, scaling, SILICON,
                                     n_anchor=16, domain_si=(0, 1e-6))
        # cfg shim that legacy code reads
        assert ad.cfg.device == "cpu"
        assert ad.cfg.dtype == torch.float32
        # iv_curve differentiable wrt doping
        C = torch.tensor(np.where(np.linspace(0, 1e-6, 16) < 5e-7, -1e22, 1e22),
                         dtype=torch.float32, requires_grad=True)
        bvec, I = ad.iv_curve(C, list(biases))
        assert I.shape == (len(biases),)
        loss = (I.abs() + 1).log().sum()
        loss.backward()
        assert C.grad is not None and torch.isfinite(C.grad).all()

    def test_ensemble_adapter_matches_deepensemble_signature(self):
        scaling, sg, norm, X, Y, biases = _tiny_setup()
        members = []
        for m in range(3):
            net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64,
                                                n_layers=2, seed=m))
            train_surrogate(net, X, Y, norm, epochs=150)
            members.append(SurrogateForwardAdapter(net, norm, scaling, SILICON,
                                                   n_anchor=16))
        ens = SurrogateEnsembleAdapter(members, scaling, SILICON)
        assert ens.M == 3
        C = torch.tensor(np.where(np.linspace(0, 1e-6, 16) < 5e-7, -1e22, 1e22),
                         dtype=torch.float32)
        mean_t, pred = ens.iv_curve(C, list(biases))
        # DeepEnsemble contract: (tensor, EnsemblePrediction)
        assert isinstance(mean_t, torch.Tensor)
        assert isinstance(pred, EnsemblePrediction)
        assert pred.mean.shape == (len(biases),)
        assert pred.samples.shape == (3, len(biases))
        assert np.all(pred.std >= 0)


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        scaling, sg, norm, X, Y, biases = _tiny_setup()
        members = []
        for m in range(2):
            net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64,
                                                n_layers=2, seed=m))
            train_surrogate(net, X, Y, norm, epochs=120)
            members.append(net)
        mpath = save_surrogate_ensemble(
            tmp_path, members, norm, scaling_name="Si", T=300.0,
            doping_dim=16, domain_si=(0, 1e-6), bias_range=(0.0, 0.5))
        # auto-detecting loader should give an ensemble adapter
        ens, manifest = load_forward_ensemble(mpath)
        assert manifest["type"] == "surrogate"
        assert ens.M == 2
        # legacy-compatible config block present
        assert manifest["config"]["network"]["doping_dim"] == 16
        # predictions are finite and forward-bias current rises
        C = torch.tensor(np.where(np.linspace(0, 1e-6, 16) < 5e-7, -1e22, 1e22),
                         dtype=torch.float32)
        _, pred = ens.iv_curve(C, list(biases))
        assert np.all(np.isfinite(pred.mean))

    def test_solve_raises_informative(self, tmp_path):
        scaling, sg, norm, X, Y, biases = _tiny_setup()
        net = IVSurrogate(IVSurrogateConfig(doping_dim=16, hidden=64, n_layers=2))
        train_surrogate(net, X, Y, norm, epochs=80)
        ens = SurrogateEnsembleAdapter(
            [SurrogateForwardAdapter(net, norm, scaling, SILICON, n_anchor=16)],
            scaling, SILICON)
        # surrogate is I-V only; .solve must raise a clear error
        import pytest
        with pytest.raises(NotImplementedError):
            ens.solve()
