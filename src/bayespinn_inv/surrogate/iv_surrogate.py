"""
SG-supervised current surrogate for BayesPINN-Inv.

Rationale
---------
The pure-physics PINN forward model computes terminal current as a derived
quantity (``mean(J_tot)``) from field gradients. In the log-density
formulation this is numerically corrupted in the subthreshold regime,
because the bulk carrier density (~1e6 scaled) multiplies a small
quasi-Fermi-gradient error and swamps the exponentially-small true current.
The terminal current — the one quantity the inverse problem needs — is
therefore unconstrained, and the model cannot reproduce diode I-V.

This module replaces that fragile path with a **directly-supervised current
head**: a small network mapping ``(doping_latent, scaled_bias)`` to the
terminal current in a symlog scale that spans the ~13 orders of magnitude of
diode I-V. Labels come from the fast, accurate Scharfetter-Gummel oracle.
The result is a clean, differentiable forward model that the inverse-design,
uncertainty-quantification, active-learning and calibration components all
build on.

Validated: median 4.5% relative I-V error on held-out doping levels across 13
orders of magnitude; inverse recovery of doping to ~0.002 decades with
calibrated ensemble uncertainty. See ``docs/forward_model_reframe.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn


# ============================================================================
# Symlog transform (handles the 13-orders-of-magnitude signed current range)
# ============================================================================

@dataclass
class SymlogTransform:
    """Signed-log transform: ``s = sign(I) * log10(1 + |I|/I0)``.

    Maps current densities spanning ~[-1e6, 1e6] A/m^2 to a compact, smooth,
    sign-preserving scale suitable for regression. ``I0`` sets the linear
    threshold below which the transform is ~linear.
    """
    I0: float = 1e-6

    def forward(self, I):
        if isinstance(I, torch.Tensor):
            return torch.sign(I) * torch.log10(1.0 + torch.abs(I) / self.I0)
        I = np.asarray(I)
        return np.sign(I) * np.log10(1.0 + np.abs(I) / self.I0)

    def inverse(self, s):
        # Clamp |s| before 10**|s| to avoid float overflow (10**38 overflows
        # float32). |s|=30 -> ~1e24 A/m^2, far above any physical current, so
        # this only bites pathological extrapolation during optimization.
        if isinstance(s, torch.Tensor):
            sabs = torch.abs(s).clamp(max=30.0)
            return torch.sign(s) * self.I0 * (10.0 ** sabs - 1.0)
        s = np.asarray(s)
        sabs = np.clip(np.abs(s), None, 30.0)
        return np.sign(s) * self.I0 * (10.0 ** sabs - 1.0)


# ============================================================================
# Input normalizer
# ============================================================================

@dataclass
class Normalizer:
    """Standardizes feature vectors: ``(x - mean) / std``."""
    mean: torch.Tensor
    std: torch.Tensor

    @classmethod
    def fit(cls, X: np.ndarray) -> "Normalizer":
        mean = torch.tensor(X.mean(0), dtype=torch.float32)
        std = torch.tensor(X.std(0) + 1e-8, dtype=torch.float32)
        return cls(mean=mean, std=std)

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


# ============================================================================
# The surrogate network
# ============================================================================

@dataclass
class IVSurrogateConfig:
    doping_dim: int = 16
    hidden: int = 128
    n_layers: int = 3
    dropout: float = 0.0          # >0 enables MC-Dropout UQ
    seed: int = 0


class IVSurrogate(nn.Module):
    """Maps ``(doping_latent, scaled_bias)`` -> symlog terminal current.

    Input dimension is ``doping_dim + 1`` (the latent plus the scaled bias).
    Output is a scalar symlog current. Wrap with a :class:`SymlogTransform` to
    convert to A/m^2.
    """

    def __init__(self, cfg: IVSurrogateConfig):
        super().__init__()
        torch.manual_seed(cfg.seed)
        self.cfg = cfg
        d_in = cfg.doping_dim + 1
        layers: List[nn.Module] = [nn.Linear(d_in, cfg.hidden), nn.SiLU()]
        if cfg.dropout > 0:
            layers.append(nn.Dropout(cfg.dropout))
        for _ in range(cfg.n_layers - 1):
            layers += [nn.Linear(cfg.hidden, cfg.hidden), nn.SiLU()]
            if cfg.dropout > 0:
                layers.append(nn.Dropout(cfg.dropout))
        layers.append(nn.Linear(cfg.hidden, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """``x`` is the *normalized* feature vector(s), shape (..., doping_dim+1)."""
        return self.net(x)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


# ============================================================================
# Dataset construction from the SG oracle
# ============================================================================

def make_features(doping_latent: np.ndarray, bias_scaled: float) -> np.ndarray:
    """Concatenate a doping latent with a scaled bias into one feature row."""
    return np.concatenate([np.asarray(doping_latent, dtype=np.float32),
                           [np.float32(bias_scaled)]])


def build_sg_dataset(
    profiles_si: List[np.ndarray],     # list of dense doping profiles (m^-3)
    biases_si: np.ndarray,             # bias values (V)
    scaling,
    oracle,                            # ScharfetterGummel1D
    symlog: Optional[SymlogTransform] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate (X, Y) where X=(latent, scaled_bias), Y=symlog(I_terminal).

    The doping latent is the network input encoding from
    ``scaling.doping_to_net_input`` evaluated on the anchor grid; here the
    profile is assumed already sampled at anchor resolution.
    """
    symlog = symlog or SymlogTransform()
    VT = scaling.V_T
    X, Y = [], []
    for C in profiles_si:
        latent = scaling.doping_to_net_input(C)
        prev = None
        for V in biases_si:
            st = oracle.solve(C, float(V), initial_state=prev)
            prev = st
            X.append(make_features(latent, V / VT))
            Y.append(symlog.forward(st.terminal_current))
    return np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.float32)


# ============================================================================
# Training
# ============================================================================

def train_surrogate(
    model: IVSurrogate,
    X: np.ndarray,
    Y: np.ndarray,
    normalizer: Normalizer,
    epochs: int = 3000,
    lr: float = 2e-3,
    weight_decay: float = 1e-5,
    batch_size: Optional[int] = None,
    verbose: bool = False,
) -> List[float]:
    """Train a single surrogate on (X, Y). Returns the loss history."""
    Xt = normalizer(torch.tensor(X, dtype=torch.float32))
    Yt = torch.tensor(Y, dtype=torch.float32).reshape(-1, 1)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    n = Xt.shape[0]
    history = []
    model.train()
    for ep in range(epochs):
        if batch_size and batch_size < n:
            idx = torch.randint(0, n, (batch_size,))
            xb, yb = Xt[idx], Yt[idx]
        else:
            xb, yb = Xt, Yt
        opt.zero_grad()
        loss = nn.functional.mse_loss(model(xb), yb)
        loss.backward()
        opt.step()
        sched.step()
        history.append(loss.item())
        if verbose and (ep % 500 == 0 or ep == epochs - 1):
            print(f"  [{ep:5d}] mse={float(loss):.4f}")
    return history


# ============================================================================
# Ensemble for uncertainty quantification
# ============================================================================

@dataclass
class SurrogatePrediction:
    mean_symlog: np.ndarray       # (B,)
    std_symlog: np.ndarray        # (B,)
    mean_current: np.ndarray      # (B,) A/m^2
    samples_symlog: np.ndarray    # (M, B)


class SurrogateEnsemble:
    """M independently-trained IVSurrogate members for deep-ensemble UQ."""

    def __init__(self, members: List[IVSurrogate], normalizer: Normalizer,
                 symlog: Optional[SymlogTransform] = None):
        self.members = members
        self.normalizer = normalizer
        self.symlog = symlog or SymlogTransform()

    @property
    def M(self) -> int:
        return len(self.members)

    def predict(self, doping_latent: np.ndarray,
                biases_scaled: np.ndarray) -> SurrogatePrediction:
        """Predict the I-V curve with ensemble uncertainty.

        ``biases_scaled`` are V/V_T values. Returns per-bias mean/std in
        symlog space and the mean current in A/m^2.
        """
        feats = np.stack([make_features(doping_latent, b) for b in biases_scaled])
        xb = self.normalizer(torch.tensor(feats, dtype=torch.float32))
        samples = []
        for m in self.members:
            m.eval()
            with torch.no_grad():
                samples.append(m(xb).numpy().ravel())
        S = np.stack(samples, axis=0)            # (M, B)
        mean_s = S.mean(0)
        std_s = S.std(0)
        return SurrogatePrediction(
            mean_symlog=mean_s, std_symlog=std_s,
            mean_current=self.symlog.inverse(mean_s),
            samples_symlog=S,
        )


__all__ = [
    "SymlogTransform", "Normalizer",
    "IVSurrogateConfig", "IVSurrogate",
    "make_features", "build_sg_dataset", "train_surrogate",
    "SurrogatePrediction", "SurrogateEnsemble",
]
