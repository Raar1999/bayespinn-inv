"""
Training loop for the forward PINN.

The trainer combines three ingredients that, in our experience, are jointly
necessary for PINN convergence on the drift-diffusion system:

1. **Bias curriculum.** We do *not* train on all bias values
   simultaneously. The network is first fit at ``V_a = 0`` (equilibrium),
   then biases are ramped up linearly over ``cfg.curriculum_epochs``
   epochs. Without curriculum, the loss is dominated by the equilibrium
   regime and the network never learns the strong forward-bias diffusion
   currents.

2. **NTK-style adaptive loss weighting** (Wang et al. 2022). Updated every
   ``cfg.adaptive_weight_every`` steps. Loss components on different
   physical scales (Poisson residual ~ 10^2, current divergences ~ 10^-3)
   would otherwise leave the network optimizing only the largest one.

3. **Gradient clipping**. PINN losses occasionally produce gradient spikes
   that destabilize Adam. We clip to ``cfg.grad_clip`` (default 1.0).

The trainer is **deterministic**: every seed-able operation is seeded from
``cfg.seed`` so that ensemble members differ only via their ``seed`` field,
and a re-run with the same config produces byte-identical results.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch

from ..physics.constants import Material
from ..physics.scaling import Scaling
from ..pinn.losses import (
    LossWeights,
    NTKAdaptiveWeights,
    PhysicsParams,
    boundary_residuals,
    pde_residuals,
)
from ..pinn.network import SemiconductorPINN

# ============================================================================
# Config
# ============================================================================

@dataclass
class TrainConfig:
    """Trainer hyperparameters and bookkeeping options."""
    # Optimization
    lr: float = 1e-3
    n_epochs: int = 5_000
    batch_size: int = 256              # PDE collocation points per step
    n_boundary: int = 2                # 2 per device per step (L and R)
    optimizer: str = "adam"            # "adam" or "lbfgs"
    grad_clip: float = 1.0
    seed: int = 0

    # Curriculum
    curriculum_epochs: int = 1_500
    bias_min: float = 0.0
    bias_max: float = 0.6              # volts, applied at right contact

    # Adaptive weighting
    use_ntk_weights: bool = True
    adaptive_weight_every: int = 100
    ntk_alpha: float = 0.9

    # Domain
    domain_si: Tuple[float, float] = (0.0, 1e-6)

    # Logging
    log_every: int = 100
    ckpt_every: int = 1_000
    out_dir: Optional[str] = None

    # Data loss
    use_data_loss: bool = False        # Set true if SG-oracle fields are paired


# ============================================================================
# Data structures for one training example
# ============================================================================

@dataclass
class TrainingExample:
    """A single (doping, bias) parameter realization to train on.

    All fields are scaled units. ``doping_latent`` is the (n_anchor,)
    representation. ``C_on_query_fn`` is a callable mapping a tensor of
    scaled x-coordinates to the scaled net doping at those coordinates
    (so we can evaluate at random collocation points).
    """
    doping_latent: torch.Tensor
    C_on_query_fn: Callable[[torch.Tensor], torch.Tensor]
    C_at_boundaries: torch.Tensor      # (2,) values at xL, xR
    bias_range: Tuple[float, float] = (0.0, 0.0)   # SI volts


# ============================================================================
# Curriculum
# ============================================================================

def curriculum_bias_max(
    epoch: int, total_epochs: int, V_min: float, V_max: float,
) -> float:
    """Piecewise-linear ramp from V_min to V_max."""
    if total_epochs <= 0:
        return V_max
    frac = min(1.0, max(0.0, epoch / total_epochs))
    return V_min + frac * (V_max - V_min)


# ============================================================================
# Sampling
# ============================================================================

def sample_collocation(
    batch_size: int,
    L_scaled: float,
    device: str = "cpu",
    dtype: torch.dtype = torch.float32,
    rng: Optional[torch.Generator] = None,
) -> torch.Tensor:
    """Uniform random samples on ``[0, L_scaled]``, shape ``(batch_size, 1)``."""
    u = torch.rand((batch_size, 1), device=device, dtype=dtype, generator=rng)
    return u * L_scaled


# ============================================================================
# Trainer
# ============================================================================

class PINNTrainer:
    """One-process trainer for a single PINN.

    For ensembles, instantiate one ``PINNTrainer`` per ensemble member
    (each with a different :class:`PINNConfig.seed`) and train in parallel
    via your launcher of choice. The trainer itself is single-process and
    has no MPI or DataParallel logic — this keeps it composable.
    """

    def __init__(
        self,
        network: SemiconductorPINN,
        scaling: Scaling,
        material: Material,
        examples: Sequence[TrainingExample],
        cfg: Optional[TrainConfig] = None,
        device: str = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        self.network = network.to(device=device, dtype=dtype)
        self.scaling = scaling
        self.material = material
        self.examples = list(examples)
        self.cfg = cfg or TrainConfig()
        self.device = device
        self.dtype = dtype

        # Deterministic seeding
        torch.manual_seed(self.cfg.seed)
        np.random.seed(self.cfg.seed)
        self._rng = torch.Generator(device=device).manual_seed(self.cfg.seed)

        # Cached scaled physics params
        self.physics = PhysicsParams(
            mu_n_s=scaling.mu_to_scaled(material.mu_n),
            mu_p_s=scaling.mu_to_scaled(material.mu_p),
            tau_n_s=material.tau_n / scaling.t_star,
            tau_p_s=material.tau_p / scaling.t_star,
        )
        self.L_scaled = float(
            scaling.x_to_scaled(torch.as_tensor(self.cfg.domain_si[1]
                                                - self.cfg.domain_si[0]))
        )

        # Optimizer
        if self.cfg.optimizer.lower() == "adam":
            self.opt = torch.optim.Adam(self.network.parameters(), lr=self.cfg.lr)
        elif self.cfg.optimizer.lower() == "lbfgs":
            self.opt = torch.optim.LBFGS(
                self.network.parameters(), lr=self.cfg.lr,
                history_size=20, max_iter=20, tolerance_grad=1e-9,
                line_search_fn="strong_wolfe",
            )
        else:
            raise ValueError(f"Unknown optimizer {self.cfg.optimizer!r}")

        self.weights = LossWeights()
        self.ntk = NTKAdaptiveWeights(["phi", "n", "p", "bdy"],
                                      alpha=self.cfg.ntk_alpha) if self.cfg.use_ntk_weights else None
        self.history: List[Dict[str, Any]] = []

        # Output dir
        if self.cfg.out_dir is not None:
            self.out_dir = Path(self.cfg.out_dir)
            self.out_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.out_dir = None

    # ------------------------------------------------------------------
    # One step
    # ------------------------------------------------------------------

    def _draw_example(self) -> TrainingExample:
        idx = int(torch.randint(0, len(self.examples), (1,),
                                 generator=self._rng).item())
        return self.examples[idx]

    def _build_batch(
        self, ex: TrainingExample, V_max_curr: float,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Build (x_s, V_a_s, latent, C_s) tensors for a step."""
        x_s = sample_collocation(
            self.cfg.batch_size, self.L_scaled,
            device=self.device, dtype=self.dtype, rng=self._rng,
        ).requires_grad_(True)
        V_lo, V_hi = ex.bias_range
        V_hi = min(V_hi, V_max_curr)
        V_lo = min(V_lo, V_hi)
        V_a = (V_lo + (V_hi - V_lo) * torch.rand(
            (1, 1), device=self.device, dtype=self.dtype, generator=self._rng))
        V_a_s = self.scaling.phi_to_scaled(V_a) * torch.ones_like(x_s)
        latent = ex.doping_latent.to(device=self.device, dtype=self.dtype)
        latent_b = latent[None, :].expand(self.cfg.batch_size, -1)
        C_s = ex.C_on_query_fn(x_s)
        return x_s, V_a_s, latent_b, C_s

    def _compute_loss(
        self, ex: TrainingExample, V_max_curr: float,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        x_s, V_a_s, latent_b, C_s = self._build_batch(ex, V_max_curr)

        # Per-batch normalization: divide Poisson residual by |C_s|.max
        # to bring loss to O(1); current residual gets a fixed mu*n_i scale.
        poisson_scale = float(C_s.detach().abs().max().clamp(min=1.0))
        current_scale = max(self.physics.mu_n_s, self.physics.mu_p_s) * 1.0
        physics_step = PhysicsParams(
            mu_n_s=self.physics.mu_n_s, mu_p_s=self.physics.mu_p_s,
            tau_n_s=self.physics.tau_n_s, tau_p_s=self.physics.tau_p_s,
            enable_srh=self.physics.enable_srh,
            poisson_scale=poisson_scale, current_scale=current_scale,
        )
        res = pde_residuals(self.network, x_s, V_a_s, latent_b, C_s,
                            physics_step)

        # Boundary points
        xb = torch.tensor([[0.0], [self.L_scaled]],
                          device=self.device, dtype=self.dtype, requires_grad=False)
        # Use the SAME bias for all boundary points as we drew above
        V_bdy = V_a_s[0:1].repeat(2, 1)
        latent_bdy = ex.doping_latent[None, :].expand(2, -1).to(
            device=self.device, dtype=self.dtype,
        )
        Cb = ex.C_at_boundaries.to(device=self.device, dtype=self.dtype
                                   ).reshape(-1, 1)
        bdy = boundary_residuals(self.network, xb, V_bdy, latent_bdy, Cb)

        # Per-component scalar losses (for NTK weighting if enabled)
        mse = lambda t: torch.mean(t ** 2)
        l_phi = mse(res["r_phi"])
        l_n   = mse(res["r_n"])
        l_p   = mse(res["r_p"])
        l_bdy = (
            mse(bdy["r_phi_L"]) + mse(bdy["r_phi_R"]) +
            mse(bdy["r_n_L"])   + mse(bdy["r_n_R"])   +
            mse(bdy["r_p_L"])   + mse(bdy["r_p_R"])
        )
        if self.ntk is not None:
            w = self.ntk.weights
            self.weights = LossWeights(
                w_phi=w["phi"], w_n=w["n"], w_p=w["p"], w_bdy=w["bdy"],
            )
        loss = (self.weights.w_phi * l_phi + self.weights.w_n * l_n +
                self.weights.w_p * l_p + self.weights.w_bdy * l_bdy)

        diag = {
            "loss_phi": float(l_phi.detach()),
            "loss_n":   float(l_n.detach()),
            "loss_p":   float(l_p.detach()),
            "loss_bdy": float(l_bdy.detach()),
            "loss_total": float(loss.detach()),
            "w_phi": self.weights.w_phi, "w_n": self.weights.w_n,
            "w_p":   self.weights.w_p,   "w_bdy": self.weights.w_bdy,
        }
        # Return *also* the per-component losses (so .train() can run NTK update)
        diag["_components"] = {"phi": l_phi, "n": l_n, "p": l_p, "bdy": l_bdy}
        return loss, diag

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def train(self, n_epochs: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run the training loop. Returns the history list."""
        if n_epochs is None:
            n_epochs = self.cfg.n_epochs
        start_time = time.time()
        for epoch in range(n_epochs):
            V_max_curr = curriculum_bias_max(
                epoch, self.cfg.curriculum_epochs,
                self.cfg.bias_min, self.cfg.bias_max,
            )
            ex = self._draw_example()

            # NTK adaptive weight update
            if (self.ntk is not None and
                    epoch > 0 and
                    epoch % self.cfg.adaptive_weight_every == 0):
                # Need per-component losses with retained graph for grad norms
                loss, diag = self._compute_loss(ex, V_max_curr)
                self.ntk.update(diag["_components"], list(self.network.parameters()))
                # Throw away this loss; will redo the step below with fresh draw
                # (cleaner than reusing partially-consumed graph)
                self.opt.zero_grad(set_to_none=True)

            # Standard training step
            if self.cfg.optimizer.lower() == "adam":
                self.opt.zero_grad(set_to_none=True)
                loss, diag = self._compute_loss(ex, V_max_curr)
                loss.backward()
                if self.cfg.grad_clip is not None:
                    torch.nn.utils.clip_grad_norm_(self.network.parameters(),
                                                    self.cfg.grad_clip)
                self.opt.step()
            else:  # LBFGS
                # ruff B023: `ex` / `V_max_curr` are late-bound, but the
                # closure is consumed by opt.step() inside this same loop
                # iteration and never escapes it, so the binding is correct.
                def closure():
                    self.opt.zero_grad(set_to_none=True)
                    loss, diag = self._compute_loss(ex, V_max_curr)  # noqa: B023
                    loss.backward()
                    closure.last_loss = loss
                    closure.last_diag = diag
                    return loss
                self.opt.step(closure)
                loss = closure.last_loss
                diag = closure.last_diag

            # Logging
            if epoch % self.cfg.log_every == 0 or epoch == n_epochs - 1:
                diag = {k: v for k, v in diag.items() if not k.startswith("_")}
                diag["epoch"] = epoch
                diag["V_max_curr"] = V_max_curr
                diag["wall_s"] = time.time() - start_time
                self.history.append(diag)
                print(
                    f"[epoch {epoch:5d}] loss={diag['loss_total']:.3e} "
                    f"(phi={diag['loss_phi']:.2e} n={diag['loss_n']:.2e} "
                    f"p={diag['loss_p']:.2e} bdy={diag['loss_bdy']:.2e}) "
                    f"V_max={V_max_curr:.3f}V"
                )

            # Checkpointing
            if self.out_dir is not None and epoch % self.cfg.ckpt_every == 0 and epoch > 0:
                self.save_checkpoint(self.out_dir / f"ckpt_{epoch:06d}.pt")

        if self.out_dir is not None:
            self.save_checkpoint(self.out_dir / "ckpt_final.pt")
            with open(self.out_dir / "history.json", "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, default=float)
        return self.history

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def save_checkpoint(self, path: Path) -> None:
        torch.save({
            "model_state": self.network.state_dict(),
            "opt_state": self.opt.state_dict(),
            "cfg": asdict(self.cfg),
            "weights": asdict(self.weights),
            "history": self.history,
        }, path)

    def load_checkpoint(self, path: Path) -> None:
        # AUDIT_g0 SEC-02 / SW-16: this was weights_only=False unconditionally,
        # so every checkpoint load executed arbitrary pickle. save_checkpoint
        # writes only tensors and plain scalars (model_state, opt_state, and
        # asdict() of two dataclasses), all of which weights_only=True accepts.
        ck = torch.load(path, map_location=self.device, weights_only=True)
        self.network.load_state_dict(ck["model_state"])
        self.opt.load_state_dict(ck["opt_state"])
        # cfg, weights, history are informational on load


__all__ = [
    "PINNTrainer",
    "TrainConfig",
    "TrainingExample",
    "curriculum_bias_max",
    "sample_collocation",
]
