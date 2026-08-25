"""Regression tests for AUDIT_g0 API-05 — minibatch sampling used the global RNG.

`SW-09`: every RNG is seeded from a single ``cfg.seed``, and ensemble members
differ **only** by their ``seed`` field.

``surrogate/iv_surrogate.py::train_surrogate`` drew its minibatch indices with

    idx = torch.randint(0, n, (batch_size,))

which reads the *global* torch RNG. Two consecutive calls with identical
arguments therefore produced different models, and an ensemble trained in a loop
would have members differing by both their seed and by wherever the global RNG
happened to be — which is not "only by their seed field".

Measured before the fix, same data, same ``cfg.seed=0``, 200 epochs,
``batch_size=32``, two consecutive calls:

    run 1  state-dict sha256 091450bf7c0965bb   final loss 0.1584867537
    run 2  state-dict sha256 cc67824aa4e606ff   final loss 0.1693387926

The full-batch path was already deterministic (``c3aa71f10f7f8172`` twice), and
**no caller in the repository passes ``batch_size``** — every experiment uses the
default ``None``. So this was latent: real, but not reachable by any published
number. `PINNTrainer` gets this right already (``trainer.py:132`` passes
``generator=rng``), which is what made ``train_surrogate`` the odd one out.

The contract under test is *reproducibility from the seed*, not any particular
weight value, so these tests compare runs against each other rather than against
a recorded hash.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
import torch

from bayespinn_inv.surrogate.iv_surrogate import (
    IVSurrogate,
    IVSurrogateConfig,
    Normalizer,
    train_surrogate,
)


def _fingerprint(model: torch.nn.Module) -> str:
    """Order-independent sha256 over a model's parameters."""
    h = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        h.update(key.encode("utf-8"))
        h.update(value.detach().cpu().numpy().tobytes())
    return h.hexdigest()


@pytest.fixture()
def data():
    rng = np.random.default_rng(0)
    x = rng.standard_normal((120, 17))
    y = rng.standard_normal(120)
    return x, y, Normalizer.fit(x)


def _train(data, **kwargs) -> tuple:
    x, y, norm = data
    model = IVSurrogate(IVSurrogateConfig(doping_dim=16, seed=0))
    history = train_surrogate(model, x, y, norm, epochs=60, **kwargs)
    return _fingerprint(model), history[-1]


class TestFullBatchTrainingIsDeterministic:
    """The path every current caller uses. Guarded so it stays that way."""

    def test_two_consecutive_runs_are_bit_identical(self, data) -> None:
        assert _train(data) == _train(data)


class TestMinibatchTrainingIsDeterministic:
    """API-05: the same seed must give the same model, with no global reseed."""

    def test_two_consecutive_runs_are_bit_identical(self, data) -> None:
        first = _train(data, batch_size=32)
        second = _train(data, batch_size=32)
        assert first == second, (
            "AUDIT_g0 API-05 -- two consecutive train_surrogate calls with the "
            f"same seed and batch_size gave different models: {first} vs {second}"
        )

    def test_an_intervening_global_draw_changes_nothing(self, data) -> None:
        """The sharper form: SW-09 means the global RNG must be irrelevant."""
        first = _train(data, batch_size=32)
        torch.rand(1000)          # perturb the global RNG between runs
        second = _train(data, batch_size=32)
        assert first == second, (
            "AUDIT_g0 API-05 -- an unrelated global draw changed the result, so "
            "minibatch sampling still reads the global RNG"
        )

    def test_different_seeds_still_give_different_models(self, data) -> None:
        """Negative control: determinism must not collapse into seed-blindness.

        A fix that ignored the seed entirely would pass both tests above. This
        one fails if members stop differing by their seed field.
        """
        x, y, norm = data
        prints = []
        for seed in (0, 1, 2):
            model = IVSurrogate(IVSurrogateConfig(doping_dim=16, seed=seed))
            train_surrogate(model, x, y, norm, epochs=60, batch_size=32)
            prints.append(_fingerprint(model))
        assert len(set(prints)) == 3, (
            f"seeds 0/1/2 produced {len(set(prints))} distinct models, not 3 -- "
            "the seed no longer controls the result"
        )

    def test_minibatch_actually_takes_the_minibatch_path(self, data) -> None:
        """Control: with batch_size >= n the code takes the full-batch branch.

        Without this, a batch_size that silently fell through to full-batch would
        make the determinism tests above pass for the wrong reason.
        """
        x, _, _ = data
        assert x.shape[0] > 32, "batch_size must be smaller than n to exercise the branch"
        small = _train(data, batch_size=32)
        full = _train(data, batch_size=x.shape[0])
        assert small != full, (
            "batch_size=32 and batch_size=n produced identical models, so the "
            "minibatch branch is not being exercised"
        )
