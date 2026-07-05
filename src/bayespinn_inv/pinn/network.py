"""
Neural network architecture for the physics-informed semiconductor PINN.

Design choices and their justifications
---------------------------------------

1. **Output parameterization in scaled units.** The network predicts the
   *scaled* potential ``phi_s`` directly, plus *scaled log-densities*
   ``log_n`` and ``log_p`` such that ``n = n_i * exp(log_n)``. This handles
   the 10-20 orders of magnitude dynamic range in carrier densities without
   gradient pathology.

2. **Doping is an input to the network**, not a fixed grid quantity. This is
   what makes the PINN polymorphic over doping profiles for inverse design.
   The network signature is ``(x, V_a, doping_param) -> (phi_s, log_n, log_p)``.

3. **Tanh activations** with Fourier feature embedding on x. Tanh has been
   shown empirically to outperform ReLU/SiLU for PINNs of elliptic problems
   (Wang et al. 2022). Fourier features mitigate the spectral bias known to
   hurt PINN convergence on multi-scale fields.

4. **MC-dropout option built in** at the dropout layer level so the same
   architecture supports point estimates, MC-dropout, and ensemble members.

5. **Reflection/skip pathway** between input and output of every hidden block
   (modified residual MLP, Wang & Perdikaris 2021): each block computes
   ``z_{l+1} = (1 - g) * tanh(W z_l + b) + g * z_l`` with a learnable gate
   ``g``. Empirically helpful for PINN convergence; the gate becomes an
   ablation axis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import torch
import torch.nn as nn


# ============================================================================
# Fourier-feature embedding
# ============================================================================

class FourierEmbedding(nn.Module):
    """
    Random Fourier feature map y = [cos(2π B x), sin(2π B x)] with B ~ N(0, σ²).
    Output dimension is 2 * num_features. B is fixed (not learned) per Tancik
    et al. 2020, but can be re-seeded via the constructor for ensembling.
    """

    def __init__(self, in_dim: int, num_features: int = 32, sigma: float = 1.0,
                 seed: Optional[int] = None):
        super().__init__()
        gen = torch.Generator()
        if seed is not None:
            gen.manual_seed(seed)
        B = torch.randn(in_dim, num_features, generator=gen) * sigma
        # Register as buffer: moves to GPU but not updated by optimizer.
        self.register_buffer("B", B)
        self.out_dim = 2 * num_features

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (..., in_dim)
        proj = 2.0 * math.pi * x @ self.B  # (..., num_features)
        return torch.cat([torch.cos(proj), torch.sin(proj)], dim=-1)


# ============================================================================
# Gated residual MLP block
# ============================================================================

class GatedBlock(nn.Module):
    """One hidden block of the modified residual PINN MLP."""

    def __init__(self, dim: int, dropout: float = 0.0):
        super().__init__()
        self.lin = nn.Linear(dim, dim)
        self.act = nn.Tanh()
        self.dropout = nn.Dropout(p=dropout) if dropout > 0 else nn.Identity()
        # Per-block learnable gate (sigmoid-bounded)
        self.gate = nn.Parameter(torch.tensor(0.0))

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        h = self.dropout(self.act(self.lin(z)))
        g = torch.sigmoid(self.gate)
        return (1.0 - g) * h + g * z


# ============================================================================
# Main PINN network
# ============================================================================

@dataclass
class PINNConfig:
    in_dim: int = 2                   # x, V_a (doping injected separately)
    hidden_dim: int = 96
    num_blocks: int = 6
    fourier_features: int = 32
    fourier_sigma: float = 2.0
    dropout: float = 0.0              # set > 0 to enable MC-dropout
    doping_dim: int = 16              # dimension of doping latent / parameterization
    output_dim: int = 3               # phi_s, log_n, log_p
    seed: Optional[int] = None
    # Domain extent in *scaled* units along x. Used to normalize x to [0, 1]
    # before the Fourier embedding so that the fourier_sigma default is
    # device-agnostic.  Set at the wrapper level; default 1.0 = no rescaling.
    x_scaled_extent: float = 1.0
    # Bias range (scaled units) for normalizing V_a to [-1, 1] before
    # the Fourier embedding. Same motivation.
    V_a_scaled_extent: float = 1.0


class SemiconductorPINN(nn.Module):
    """
    A PINN network that maps
        (x_scaled, V_applied_scaled, doping_latent)  ->  (phi_s, log_n, log_p)

    The doping latent can be either:
      (a) a low-dimensional parameterization (e.g. junction depth, peak doping,
          gradient) — the inverse-design optimization variable, or
      (b) a dense pointwise doping profile fed via a small encoder.

    For the M1 stage we use the low-dim parameterization (default); the
    architecture supports the dense version via ``doping_encoder=True``.
    """

    def __init__(self, cfg: PINNConfig, doping_encoder: bool = False):
        super().__init__()
        self.cfg = cfg
        if cfg.seed is not None:
            torch.manual_seed(cfg.seed)

        # Coordinate embedding (Fourier on x and V_a)
        self.embed = FourierEmbedding(cfg.in_dim, cfg.fourier_features,
                                       cfg.fourier_sigma, seed=cfg.seed)
        # Optional doping encoder (small MLP -> doping_dim)
        if doping_encoder:
            self.doping_enc = nn.Sequential(
                nn.Linear(cfg.doping_dim, 2 * cfg.doping_dim), nn.Tanh(),
                nn.Linear(2 * cfg.doping_dim, cfg.doping_dim),
            )
        else:
            self.doping_enc = nn.Identity()

        in_proj = self.embed.out_dim + cfg.doping_dim
        self.input_proj = nn.Linear(in_proj, cfg.hidden_dim)
        self.blocks = nn.ModuleList([
            GatedBlock(cfg.hidden_dim, dropout=cfg.dropout)
            for _ in range(cfg.num_blocks)
        ])
        # Three independent output heads — empirically slightly better than
        # a shared head for multi-output PINNs.
        self.head_phi = nn.Linear(cfg.hidden_dim, 1)
        self.head_log_n = nn.Linear(cfg.hidden_dim, 1)
        self.head_log_p = nn.Linear(cfg.hidden_dim, 1)

    def forward(
        self,
        x: torch.Tensor,           # (..., 1) scaled coordinate (physical scaled)
        V_a: torch.Tensor,         # (..., 1) scaled bias (same shape as x)
        doping_latent: torch.Tensor,  # (..., doping_dim)
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Returns
        -------
        phi_s : (..., 1)
            Scaled electric potential.
        log_n : (..., 1)
            log( n / n_i ).
        log_p : (..., 1)
            log( p / n_i ).
        """
        # Normalize inputs to ~[0, 1] / [-1, 1] before Fourier embedding so
        # the default fourier_sigma=2 is invariant to the physical scale.
        x_norm = x / self.cfg.x_scaled_extent
        V_norm = V_a / max(self.cfg.V_a_scaled_extent, 1e-6)
        coords = torch.cat([x_norm, V_norm], dim=-1)     # (..., 2)
        emb = self.embed(coords)                         # (..., 2*F)
        d_enc = self.doping_enc(doping_latent)           # (..., doping_dim)
        z = torch.cat([emb, d_enc], dim=-1)
        z = self.input_proj(z)
        for blk in self.blocks:
            z = blk(z)
        phi_s = self.head_phi(z)
        log_n = self.head_log_n(z)
        log_p = self.head_log_p(z)
        return phi_s, log_n, log_p

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


__all__ = [
    "FourierEmbedding",
    "GatedBlock",
    "PINNConfig",
    "SemiconductorPINN",
]
