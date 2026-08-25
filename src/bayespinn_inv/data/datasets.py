"""
Synthetic doping-profile dataset for training the PINN forward model.

We expose four families of doping profiles that span the regimes most
relevant to inverse-design experiments:

- **step**:  abrupt PN junction. Parameters: ``N_A, N_D, x_junction``.
- **graded**:  error-function-graded junction with grading length L_g.
- **LDD**:  lightly-doped-drain three-segment profile, used in modern
            MOSFET source/drain extensions to suppress hot-carrier injection.
- **defect**:  step profile with an additional Gaussian *anomaly* of
            user-prescribed sign and amplitude — represents an unknown
            defect cluster, which is exactly the inverse problem use case.

Each generated profile comes with:

- ``doping_si``: dense (N,) profile in m^-3 on a uniform grid spanning
                 ``domain_si``.
- ``params``: dict of generator parameters, for reproducibility.
- ``family``: profile family name (string), for stratification.

The :class:`DopingDataset` class converts profiles into
:class:`TrainingExample` instances by:

1. Sampling the dense profile onto the network's fixed anchor grid (the
   "doping latent").
2. Building a closure ``C_on_query_fn(x_s)`` that returns the scaled
   net doping at arbitrary scaled coordinates via linear interpolation.

This decoupling means the trainer can sample collocation points
anywhere, not only at anchor positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from ..physics.scaling import Scaling
from ..training.trainer import TrainingExample

# ============================================================================
# Profile generators
# ============================================================================

def step_profile(x: np.ndarray, N_A: float, N_D: float,
                 x_junction: float) -> np.ndarray:
    """C(x) = N_D - N_A. P-region (negative C) on the left."""
    C = np.where(x < x_junction, -N_A, N_D)
    return C.astype(np.float64)


def graded_profile(x: np.ndarray, N_A: float, N_D: float,
                   x_junction: float, L_grade: float) -> np.ndarray:
    """erf-graded junction with grading length L_grade."""
    from scipy.special import erf
    C = 0.5 * (N_D - N_A) + 0.5 * (N_D + N_A) * erf((x - x_junction) / L_grade)
    return C.astype(np.float64)


def ldd_profile(
    x: np.ndarray,
    N_A_body: float,
    N_D_ldd: float,
    N_D_sd: float,
    x_ldd_start: float,
    x_ldd_end: float,
) -> np.ndarray:
    """Three-segment NMOS source/drain extension:
        [0, x_ldd_start]    P-body (acceptor) at N_A_body
        [x_ldd_start, x_ldd_end]   N-LDD at N_D_ldd
        [x_ldd_end, L]      N+ source/drain at N_D_sd
    """
    C = np.full_like(x, -N_A_body, dtype=np.float64)
    in_ldd = (x >= x_ldd_start) & (x < x_ldd_end)
    in_sd  = x >= x_ldd_end
    C[in_ldd] = N_D_ldd
    C[in_sd]  = N_D_sd
    return C


def defect_profile(
    x: np.ndarray,
    N_A: float,
    N_D: float,
    x_junction: float,
    defect_amplitude: float,
    defect_center: float,
    defect_width: float,
) -> np.ndarray:
    """Step profile + Gaussian defect bump.

    The defect amplitude is the *additive* perturbation to C in m^-3
    (can be positive or negative).
    """
    C = step_profile(x, N_A, N_D, x_junction)
    bump = defect_amplitude * np.exp(-0.5 * ((x - defect_center) / defect_width) ** 2)
    return C + bump


# ============================================================================
# Family sampler
# ============================================================================

@dataclass
class DopingSample:
    family: str
    doping_si: np.ndarray              # (N,)
    x_si: np.ndarray                   # (N,)
    params: Dict[str, float]


def sample_doping(
    family: str,
    n_points: int,
    domain_si: Tuple[float, float],
    rng: np.random.Generator,
    doping_range: Optional[Tuple[float, float]] = None,
) -> DopingSample:
    """Draw a random doping profile of the given family.

    Sampling ranges are chosen to span typical device design space:
    bulk doping 1e15--1e18 cm^-3, junction locations within the middle
    50% of the device, grading lengths and defect widths of order 10%
    of the device length.

    ``doping_range`` optionally overrides the per-level magnitude range
    ``(lo, hi)`` in m^-3 for the ``step`` and ``graded`` families. Use this
    to keep targets within a forward surrogate's validated range.
    """
    L = domain_si[1] - domain_si[0]
    x = np.linspace(domain_si[0], domain_si[1], n_points)
    if doping_range is not None:
        lo_e, hi_e = np.log10(doping_range[0]), np.log10(doping_range[1])
    else:
        lo_e, hi_e = 21, 24
    if family == "step":
        N_A = 10 ** rng.uniform(lo_e, hi_e)     # m^-3
        N_D = 10 ** rng.uniform(lo_e, hi_e)
        xj  = domain_si[0] + rng.uniform(0.25, 0.75) * L
        C = step_profile(x, N_A, N_D, xj)
        params = dict(N_A=N_A, N_D=N_D, x_junction=xj)
    elif family == "graded":
        N_A = 10 ** rng.uniform(lo_e, hi_e)
        N_D = 10 ** rng.uniform(lo_e, hi_e)
        xj  = domain_si[0] + rng.uniform(0.3, 0.7) * L
        Lg  = rng.uniform(0.02, 0.15) * L
        C = graded_profile(x, N_A, N_D, xj, Lg)
        params = dict(N_A=N_A, N_D=N_D, x_junction=xj, L_grade=Lg)
    elif family == "ldd":
        N_A_body = 10 ** rng.uniform(21, 23)
        N_D_ldd  = 10 ** rng.uniform(22, 24)
        N_D_sd   = 10 ** rng.uniform(24, 25)
        x_s = domain_si[0] + rng.uniform(0.25, 0.5) * L
        x_e = x_s + rng.uniform(0.1, 0.35) * L
        x_e = min(x_e, domain_si[1] - 0.05 * L)
        C = ldd_profile(x, N_A_body, N_D_ldd, N_D_sd, x_s, x_e)
        params = dict(N_A_body=N_A_body, N_D_ldd=N_D_ldd, N_D_sd=N_D_sd,
                       x_ldd_start=x_s, x_ldd_end=x_e)
    elif family == "defect":
        N_A = 10 ** rng.uniform(22, 23)
        N_D = 10 ** rng.uniform(22, 23)
        xj  = domain_si[0] + rng.uniform(0.4, 0.6) * L
        amp = rng.choice([-1, 1]) * 10 ** rng.uniform(22, 23)
        cen = domain_si[0] + rng.uniform(0.15, 0.85) * L
        wid = rng.uniform(0.03, 0.12) * L
        C = defect_profile(x, N_A, N_D, xj, amp, cen, wid)
        params = dict(N_A=N_A, N_D=N_D, x_junction=xj,
                       defect_amplitude=amp, defect_center=cen,
                       defect_width=wid)
    else:
        raise ValueError(f"Unknown doping family: {family!r}")
    return DopingSample(family=family, doping_si=C, x_si=x, params=params)


# ============================================================================
# TrainingExample builder
# ============================================================================

def make_training_example(
    sample: DopingSample,
    scaling: Scaling,
    domain_si: Tuple[float, float],
    n_anchor: int,
    bias_range: Tuple[float, float] = (0.0, 0.7),
    device: str = "cpu",
    dtype: torch.dtype = torch.float32,
) -> TrainingExample:
    """Convert a :class:`DopingSample` into a :class:`TrainingExample`."""
    # 1) Resample to anchor grid, then log-compress for network input
    x_anchor_si = np.linspace(domain_si[0], domain_si[1], n_anchor)
    C_anchor_si = np.interp(x_anchor_si, sample.x_si, sample.doping_si)
    # Use the log-compressed representation -- raw C/n_i has magnitudes ~1e7
    # which saturates tanh networks at initialization.
    latent_arr = scaling.doping_to_net_input(C_anchor_si)
    latent = torch.as_tensor(latent_arr, device=device, dtype=dtype)

    # 2) Build a closure for C_s(x_s) via linear interp on scaled coords
    x_dense_s = scaling.x_to_scaled(torch.as_tensor(sample.x_si, dtype=dtype))
    C_dense_s = torch.as_tensor(sample.doping_si / scaling.n_star, dtype=dtype)

    def C_on_query_fn(x_query_s: torch.Tensor) -> torch.Tensor:
        """Return scaled C at scaled-coordinate query points (shape (N,1) or (N,)).

        Linear interpolation via the same searchsorted trick we use in
        ForwardPINN.doping_to_latent.
        """
        flat = x_query_s.reshape(-1)
        flat_c = torch.clamp(flat, x_dense_s.min(), x_dense_s.max())
        right = torch.searchsorted(x_dense_s.contiguous().to(device=flat.device),
                                    flat_c.contiguous())
        right = torch.clamp(right, 1, len(x_dense_s) - 1)
        left = right - 1
        xl, xr = x_dense_s.to(flat.device)[left], x_dense_s.to(flat.device)[right]
        yl, yr = C_dense_s.to(flat.device)[left], C_dense_s.to(flat.device)[right]
        w = torch.where(xr > xl, (flat_c - xl) / (xr - xl + 1e-30),
                        torch.zeros_like(xr))
        out = yl + w * (yr - yl)
        return out.reshape(x_query_s.shape)

    # 3) Boundary values
    C_bdy = torch.tensor(
        [sample.doping_si[0] / scaling.n_star,
         sample.doping_si[-1] / scaling.n_star],
        device=device, dtype=dtype,
    )

    return TrainingExample(
        doping_latent=latent,
        C_on_query_fn=C_on_query_fn,
        C_at_boundaries=C_bdy,
        bias_range=bias_range,
    )


# ============================================================================
# Dataset factory
# ============================================================================

def build_dataset(
    n_per_family: Dict[str, int],
    n_points: int,
    domain_si: Tuple[float, float],
    scaling: Scaling,
    n_anchor: int,
    bias_range: Tuple[float, float] = (0.0, 0.7),
    seed: int = 0,
    device: str = "cpu",
    dtype: torch.dtype = torch.float32,
) -> Tuple[List[TrainingExample], List[DopingSample]]:
    """Generate a full dataset.

    Parameters
    ----------
    n_per_family : dict[str, int]
        e.g. {"step": 16, "graded": 16, "ldd": 8, "defect": 8} for a 48-profile
        training set.
    n_points : int
        Dense profile resolution (used for plotting and validation; the
        network always sees the anchor-resolution latent).

    Returns
    -------
    examples, samples : lists of length sum(n_per_family.values())
    """
    rng = np.random.default_rng(seed)
    samples: List[DopingSample] = []
    examples: List[TrainingExample] = []
    for family, count in n_per_family.items():
        for _ in range(count):
            s = sample_doping(family, n_points, domain_si, rng)
            samples.append(s)
            ex = make_training_example(
                s, scaling, domain_si, n_anchor,
                bias_range=bias_range, device=device, dtype=dtype,
            )
            examples.append(ex)
    return examples, samples


__all__ = [
    "DopingSample",
    "build_dataset",
    "defect_profile",
    "graded_profile",
    "ldd_profile",
    "make_training_example",
    "sample_doping",
    "step_profile",
]
