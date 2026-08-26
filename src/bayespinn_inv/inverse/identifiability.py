"""
Identifiability analysis for doping recovery from terminal I--V.

Motivation
----------
This repository states -- correctly -- that recovering a full doping *profile*
from terminal I--V is ill-posed, and reports a symptom: the I--V can be matched
to ~0.2% while the recovered profile's relative L2 error stays between 0.17 and
0.84. That is evidence that *something* is unobservable, but it does not say
what, how much, or whether the situation would improve with better data.

This module answers those questions quantitatively by analysing the local
Jacobian of the forward map

    F : theta  ->  s(V; theta) = symlog I(V; theta),      theta = log10 |C| at
                                                          each profile node

and its singular value decomposition ``F' = U S V^T``:

* the **singular values** ``S`` give the gain of the forward map along each
  orthogonal direction in profile space, in units of "symlog decades of current
  per decade of doping";
* the **right singular vectors** ``V`` are those directions -- the leading ones
  are what an I--V measurement actually constrains, the trailing ones are the
  profile changes the measurement cannot see;
* comparing ``S`` against the measurement noise floor gives a **numerical rank**:
  the number of profile degrees of freedom the experiment can determine at all.

This is the standard local-identifiability treatment of a nonlinear inverse
problem (Bellman & Astrom 1970 on structural identifiability; the SVD/resolution
formulation follows Aster, Borchers & Thurber, *Parameter Estimation and Inverse
Problems*, 3rd ed., ch. 4). Nothing here is novel as *method* -- the
contribution is applying it to make this project's ill-posedness a measured,
reproducible quantity with an operational consequence (see
:func:`equivalence_perturbation`) instead of an anecdote.

Why the Jacobian is taken through the *oracle*
----------------------------------------------
Identifiability must be a property of the physics, not of a particular trained
surrogate. :func:`sg_forward_jacobian` differentiates the Scharfetter--Gummel
solver by finite differences, so the resulting spectrum characterises the
drift--diffusion forward map itself. :func:`torch_forward_jacobian` does the
same through a differentiable surrogate; comparing the two spectra is a direct
check on whether the surrogate has inherited the true problem's conditioning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "IdentifiabilityReport",
    "analyse_identifiability",
    "equivalence_perturbation",
    "rank_cutoff_record",
    "sg_forward_jacobian",
    "symlog",
    "torch_forward_jacobian",
]


def symlog(I, I0: float = 1e-6):
    """Sign-preserving log used throughout the project: sign(I) log10(1+|I|/I0)."""
    I = np.asarray(I, dtype=np.float64)
    return np.sign(I) * np.log10(1.0 + np.abs(I) / I0)


# ===========================================================================
# Report
# ===========================================================================

@dataclass
class IdentifiabilityReport:
    """Local identifiability of a forward map at one operating point.

    Attributes
    ----------
    jacobian : (B, P)
        d symlog(I) / d log10|C| -- rows are bias points, columns profile
        parameters.
    singular_values : (min(B,P),)
        Forward gains, descending.
    directions : (P, min(B,P))
        Right singular vectors as *columns*: ``directions[:, k]`` is the
        profile perturbation direction with gain ``singular_values[k]``.
    bias_modes : (B, min(B,P))
        Left singular vectors as columns -- the I--V response patterns.
    noise_symlog : float
        Measurement noise expressed in symlog units; the threshold used for
        the rank count.
    """
    jacobian: np.ndarray
    singular_values: np.ndarray
    directions: np.ndarray
    bias_modes: np.ndarray
    noise_symlog: float
    parameter_names: Optional[List[str]] = None
    #: Estimated absolute noise on a single Jacobian entry, in symlog units
    #: per decade. Singular values below the induced spectral floor are
    #: artefacts of the finite-difference estimate, not physics.
    jacobian_noise: float = 0.0

    # -- derived quantities -------------------------------------------------

    @property
    def n_parameters(self) -> int:
        return self.jacobian.shape[1]

    @property
    def n_observations(self) -> int:
        return self.jacobian.shape[0]

    @property
    def spectral_floor(self) -> float:
        """Smallest singular value this analysis can actually resolve.

        A Jacobian estimated with per-entry noise ``eta`` has a perturbed
        spectrum; by Weyl's inequality no singular value below
        ``||E||_2 <= eta*sqrt(B*P)`` is distinguishable from zero. Reporting
        singular values under this floor as if they were measurements is
        exactly the failure this module is meant to prevent.
        """
        B, P = self.jacobian.shape
        return float(self.jacobian_noise * np.sqrt(B * P))

    @property
    def resolvable_rank(self) -> int:
        """Number of singular values above this analysis's own noise floor."""
        return int(np.sum(self.singular_values > self.spectral_floor))

    @property
    def identifiable_rank(self) -> int:
        """How many profile directions produce a signal above the noise.

        A perturbation of one decade along direction ``k`` changes the I--V by
        ``singular_values[k]`` symlog units, detectable only if that exceeds
        the measurement noise. Capped by :attr:`resolvable_rank`: we cannot
        claim a direction is identifiable if our own estimate of its gain is
        indistinguishable from zero.
        """
        above_noise = int(np.sum(self.singular_values > self.noise_symlog))
        return min(above_noise, self.resolvable_rank)

    def rank_vs_noise(self, noise_levels: Sequence[float]) -> List[Tuple[float, int]]:
        """Identifiable rank as a function of relative measurement noise.

        The experimental-design question: how much does a better instrument
        actually buy? Also capped by :attr:`resolvable_rank`.
        """
        out = []
        cap = self.resolvable_rank
        for nl in noise_levels:
            thr = float(np.log10(1.0 + nl))
            out.append((float(nl),
                        min(int(np.sum(self.singular_values > thr)), cap)))
        return out

    @property
    def condition_number(self) -> float:
        s = self.singular_values
        if s.size == 0 or s[-1] <= 0:
            return float("inf")
        return float(s[0] / s[-1])

    def detectable_amplitude(self, k: int) -> float:
        """Decades of doping needed along direction ``k`` to be detectable.

        The operational reading of ill-posedness: how badly wrong the profile
        can be along this direction while the I--V still looks correct.
        """
        s = float(self.singular_values[k])
        if s <= 0:
            return float("inf")
        return self.noise_symlog / s

    def parameter_sensitivity(self) -> np.ndarray:
        """Per-parameter observability: the L2 norm of each Jacobian column."""
        return np.linalg.norm(self.jacobian, axis=0)

    def summary(self) -> str:
        s = self.singular_values
        lines = [
            "Identifiability report",
            f"  observations (bias points) : {self.n_observations}",
            f"  parameters (profile nodes) : {self.n_parameters}",
            f"  measurement noise (symlog) : {self.noise_symlog:.3e}",
            f"  identifiable rank          : {self.identifiable_rank}"
            f" / {self.n_parameters}",
            f"  resolvable by this estimate: {self.resolvable_rank}"
            f" (spectral floor {self.spectral_floor:.2e})",
            f"  condition number           : {self.condition_number:.3e}",
            "  singular values (gain, symlog per decade):",
        ]
        for k, sv in enumerate(s):
            if sv <= self.spectral_floor:
                tag = "below analysis floor"
                amp = "  --"
            elif sv > self.noise_symlog:
                tag = "observable"
                amp = f"{self.detectable_amplitude(k):8.3g}"
            else:
                tag = "UNOBSERVABLE"
                amp = f"{self.detectable_amplitude(k):8.3g}"
            lines.append(
                f"    sigma[{k:2d}] = {sv:.4e}   needs {amp} decades   {tag}")
        return "\n".join(lines)


# ===========================================================================
# Jacobians
# ===========================================================================

def sg_forward_jacobian(
    oracle,
    doping_si: np.ndarray,
    biases: Sequence[float],
    I0: float = 1e-6,
    rel_step: float = 1e-2,
    min_snr: float = 1e4,
    *,
    chart=None,
) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """Finite-difference Jacobian d symlog(I) / d log10|C| through the SG oracle.

    Perturbs the *magnitude* of the doping at each node by ``rel_step`` decades,
    keeping its sign, and re-solves. Central differences.

    ``chart`` (``CHART-01``, generation 8)
        Required whenever ``doping_si`` is **not** grid-valued. The published
        local rank was measured by handing this function a length-16 signed
        vector and letting ``ScharfetterGummel1D.solve`` resample it -- which
        chose chart L, silently, from an array length. That resampler is gone;
        the chart is now named at the call site and reconstructs through
        :meth:`~bayespinn_inv.inverse.charts.Chart.on_grid_signed`. Passing
        ``ChartL(d, x_si)`` reproduces the old numbers exactly; passing nothing
        with a short vector now raises instead of guessing.

    PH-22 (dtype): **float64 throughout** -- this is the NumPy oracle path, and it
    is the only one permitted to arbitrate a published identifiability number. Its
    float32 sibling is :func:`torch_forward_jacobian`; the two are not
    interchangeable and their envelopes are reported separately.

    Parameters
    ----------
    oracle : ScharfetterGummel1D
    doping_si : (P,) net doping in m^-3 (the operating point)
    biases : bias values in volts
    rel_step : central-difference step in *decades* of doping. Must be large
        enough that the induced current change clears the oracle's own
        precision. Measured on the reference diode, the relative precision of
        the terminal current is ~1/SNR where SNR = |I| / current_noise_floor;
        at the default 1e-2 decades the induced change is ~2.6%, giving a
        finite-difference signal-to-noise above 100 on every retained row.
    min_snr : discard bias points whose oracle SNR is below this. A row with
        SNR = 10 carries ~10% relative precision, so differencing it produces
        noise, not a derivative -- and an SVD of a noisy Jacobian manufactures
        a spectrum that looks informative but is not. Verified empirically:
        with the previous defaults (step 1e-3 decades, SNR > 10) the measured
        response along the *exact null space* was the same size as along the
        most observable direction, i.e. the whole spectrum was noise.

    Returns
    -------
    J : (B_used, P) Jacobian
    I_ref : (B_used,) reference currents in A/m^2
    kept : indices of the biases actually used
    entry_noise : estimated absolute noise on one Jacobian entry, in symlog
        units per decade, derived from the oracle's own reported noise floor.
        Feed this to :func:`analyse_identifiability` so the SVD cannot claim
        resolution it does not have.
    """
    doping_si = np.asarray(doping_si, dtype=np.float64)
    P = doping_si.shape[0]
    if chart is None:
        def _to_grid(C):
            return C
    else:
        if chart.d != P:
            raise ValueError(
                f"{chart.label()} takes {chart.d} coordinates, got {P}")

        def _to_grid(C):
            return chart.on_grid_signed(C)

    def _iv(C):
        prev, out, floors = None, [], []
        for V in biases:
            st = oracle.solve(_to_grid(C), float(V), initial_state=prev)
            prev = st
            out.append(st.terminal_current)
            floors.append(st.current_noise_floor)
        return np.asarray(out), np.asarray(floors)

    I_ref, floors = _iv(doping_si)
    kept = [i for i in range(len(I_ref))
            if abs(I_ref[i]) > min_snr * floors[i]]
    if not kept:
        raise ValueError(
            f"No bias point reached SNR > {min_snr:g} against the oracle's own "
            "noise floor; a finite-difference Jacobian here would be noise. "
            "Increase the bias range or lower min_snr deliberately.")

    J = np.zeros((len(kept), P))
    for j in range(P):
        if doping_si[j] == 0.0:
            continue
        sign = np.sign(doping_si[j])
        mag = abs(doping_si[j])
        Cp = doping_si.copy()
        Cm = doping_si.copy()
        Cp[j] = sign * mag * 10.0 ** (+rel_step)
        Cm[j] = sign * mag * 10.0 ** (-rel_step)
        Ip, _ = _iv(Cp)
        Im, _ = _iv(Cm)
        J[:, j] = (symlog(Ip[kept], I0) - symlog(Im[kept], I0)) / (2.0 * rel_step)

    # Precision of symlog(I) is d|I|/(|I| ln 10); the oracle's own noise floor
    # gives d|I| directly. Central differencing divides by 2*rel_step and adds
    # the two evaluations in quadrature.
    rel_prec = np.asarray([floors[i] / max(abs(I_ref[i]), 1e-300) for i in kept])
    entry_noise = float(np.max(rel_prec) / np.log(10.0)
                        * np.sqrt(2.0) / (2.0 * rel_step))
    return J, I_ref[kept], kept, entry_noise


def torch_forward_jacobian(
    iv_curve: Callable,
    C_si,
    biases: Sequence[float],
    I0: float = 1e-6,
):
    """Autograd Jacobian d symlog(I) / d log10|C| through a differentiable model.

    ``iv_curve`` must have the ``(C_si, biases) -> (biases, I)`` signature used
    by :class:`~bayespinn_inv.surrogate.adapters.SurrogateForwardAdapter`.

    PH-22 (dtype): **float32** -- the surrogate's own dtype, set at line
    ``C0 = torch.as_tensor(..., dtype=torch.float32)`` below. Two consequences,
    both measured:

    * doping differences below ~1e-7 relative are not representable here, so this
      function cannot resolve profile pairs closer than that (the float64 oracle
      can: its round-trip error is 1.678e-16);
    * GRAD-01 measured surrogate directional derivatives as agreeing with the
      oracle **only inside the identifiable subspace** (cosine ~ +0.50 inside,
      ~ -0.00 outside).

    Together these make this function suitable for *proposing* directions and
    unsuitable for *arbitrating* any claim about what lies outside the
    identifiable subspace. Use :func:`sg_forward_jacobian` for that.
    """
    import torch

    C0 = torch.as_tensor(np.asarray(C_si), dtype=torch.float32)
    sign = torch.sign(C0)
    log_mag = torch.log10(torch.abs(C0).clamp(min=1e-30)).clone().requires_grad_(True)

    def _f(lm):
        C = sign * torch.pow(10.0, lm)
        _, I = iv_curve(C, list(biases))
        return torch.sign(I) * torch.log10(1.0 + torch.abs(I) / I0)

    J = torch.autograd.functional.jacobian(_f, log_mag, vectorize=False)
    return J.detach().cpu().numpy()


# ===========================================================================
# Analysis
# ===========================================================================

def analyse_identifiability(
    J: np.ndarray,
    noise_rel: float = 0.02,
    I0: float = 1e-6,
    I_ref: Optional[np.ndarray] = None,
    parameter_names: Optional[List[str]] = None,
    jacobian_noise: float = 0.0,
) -> IdentifiabilityReport:
    """SVD analysis of a forward Jacobian.

    ``noise_rel`` is the *relative* current measurement noise. A relative error
    of ``eps`` on a current well above ``I0`` shifts symlog by approximately
    ``log10(1+eps) ~ eps/ln(10)``, which is the threshold used to decide whether
    a singular direction is observable.
    """
    J = np.asarray(J, dtype=np.float64)
    # full_matrices=True on the right factor so that the *exact* null space is
    # represented. With B bias points and P > B profile parameters the map has
    # a null space of dimension at least P - B; truncating V to B columns
    # hides it, and those are precisely the directions an experiment can never
    # constrain. Missing singular values are padded with exact zeros.
    U, S, Vt = np.linalg.svd(J, full_matrices=True)
    P = J.shape[1]
    if S.size < P:
        S = np.concatenate([S, np.zeros(P - S.size)])
    noise_symlog = float(np.log10(1.0 + noise_rel))
    return IdentifiabilityReport(
        jacobian=J,
        singular_values=S,
        directions=Vt.T,
        bias_modes=U,
        noise_symlog=noise_symlog,
        parameter_names=parameter_names,
        jacobian_noise=float(jacobian_noise),
    )


def equivalence_perturbation(
    report: IdentifiabilityReport,
    doping_si: np.ndarray,
    rank: Optional[int] = None,
    decades: float = 0.3,
    mode: str = "least",
) -> np.ndarray:
    """Build a doping profile that is *far* from the original but I--V-equivalent.

    Takes the least-observable direction (or a random combination of all
    directions below the identifiable rank), scales it to ``decades`` of doping
    change, and applies it multiplicatively in log-magnitude space so the sign
    of the doping -- and hence the junction structure -- is preserved.

    This turns the abstract statement "the problem is ill-posed" into a concrete
    counter-example: two physically distinct devices whose measured I--V curves
    an experimentalist could not tell apart.
    """
    if rank is None:
        rank = report.identifiable_rank
    if rank >= report.directions.shape[1]:
        raise ValueError(
            "Every resolved direction is identifiable at this noise level; "
            "no equivalence perturbation exists in the analysed subspace.")
    null_dirs = report.directions[:, rank:]          # (P, n_null)
    if mode == "least":
        v = null_dirs[:, -1]                         # smallest gain of all
    elif mode == "weighted":
        # Combine unobservable directions weighted by 1/gain so the least
        # observable ones dominate; exact-null directions get the full weight.
        s_null = report.singular_values[rank:]
        w = 1.0 / (s_null + report.noise_symlog * 1e-6)
        v = null_dirs @ (w / np.linalg.norm(w))
    else:
        raise ValueError(f"unknown mode {mode!r}")
    if np.max(np.abs(v)) < 1e-12:                    # degenerate cancellation
        v = null_dirs[:, -1]
    v = v / np.max(np.abs(v)) * decades
    doping_si = np.asarray(doping_si, dtype=np.float64)
    sign = np.sign(doping_si)
    mag = np.abs(doping_si)
    return sign * mag * (10.0 ** v)


def rank_cutoff_record(rep: "IdentifiabilityReport", noise_rel: float,
                       cutoff_grid: Optional[Sequence[float]] = None) -> dict:
    """The spectrum, then **rank as a curve over cutoffs** -- never a bare integer.

    ``SPEC-11``, enacted by operator ruling at generation 8 §5.

        Every rank is reported as ``rank(cutoff)`` over the range of defensible
        cutoffs, with the spectrum, the chosen cutoff, and whether that cutoff
        sits in a population gap. A bare integer rank appears only where a gap
        justifies it.

    The defect that forced it. Generation 7 measured four ``(chart, d)`` cells and
    found that at ``d = 4`` the operational cutoff falls inside the spectrum's
    largest multiplicative gap (x7.39 in chart G, x17.46 in chart L) while at
    ``d = 16`` it does not (x4.99 and x5.12, cutoff outside). So "3 of 4" is a
    boundary between two populations of singular values and "4 of 16" is a
    threshold applied to a smooth decay. They are different kinds of object and
    were being quoted in the same voice.

    What "defensible" means here, stated rather than tuned
    ------------------------------------------------------
    The cutoff is a measurement-noise level expressed in symlog units,
    ``log10(1 + noise_rel)``. Its range is bounded

    * **below** by this analysis's own ``spectral_floor``: under it, a singular
      value is not distinguishable from zero by Weyl's inequality, so a rank
      counted there counts estimator noise;
    * **above** by a noise level no one would claim for this instrument.

    The default grid is the repository's existing ``NOISE_GRID`` from
    ``scripts/run_identifiability.py``, so the range is inherited, not invented
    for this report.

    The gap criterion is also inherited, unchanged, from the generation-7
    reconciliation: **a bare integer rank is justified iff the operational cutoff
    falls strictly inside the largest multiplicative gap of the resolvable
    spectrum.** Fixing it in an earlier generation is what keeps ``AH-14`` clean
    here -- it cannot have been chosen after seeing the g8 cells.

    ``plateau_containing_operational_cutoff`` is the continuous companion: the
    span of noise levels over which the rank does not move. A wide plateau and an
    in-gap cutoff are the same fact seen twice; a narrow plateau with an in-gap
    verdict would be a contradiction worth chasing.
    """
    s = np.asarray(rep.singular_values, dtype=np.float64)
    floor = rep.spectral_floor
    above = s[s > floor]

    gap_idx, gap_ratio, in_gap = None, None, None
    if above.size >= 2:
        ratios = above[:-1] / np.maximum(above[1:], 1e-300)
        gap_idx = int(np.argmax(ratios))
        gap_ratio = float(ratios[gap_idx])
    op_cut = float(np.log10(1.0 + noise_rel))
    if gap_idx is not None:
        in_gap = bool(above[gap_idx + 1] <= op_cut < above[gap_idx])

    grid = list(cutoff_grid) if cutoff_grid is not None else [
        0.20, 0.10, 0.05, 0.02, 0.01, 1e-3, 1e-4, 1e-6]
    curve = []
    for nl in grid:
        thr = float(np.log10(1.0 + float(nl)))
        curve.append({
            "noise_rel": float(nl),
            "cutoff_symlog": thr,
            "rank": int(min(int(np.sum(s > thr)), rep.resolvable_rank)),
            "cutoff_below_spectral_floor": bool(thr < floor),
        })

    ranks = [c["rank"] for c in curve]
    lo = hi = None
    if noise_rel in grid:
        k = grid.index(noise_rel)
        i = k
        while i > 0 and ranks[i - 1] == ranks[k]:
            i -= 1
        j = k
        while j < len(grid) - 1 and ranks[j + 1] == ranks[k]:
            j += 1
        lo, hi = float(grid[j]), float(grid[i])   # grid descends in noise

    return {
        "singular_values": [float(x) for x in s],
        "spectral_floor": float(floor),
        "jacobian_noise": float(rep.jacobian_noise),
        "n_observations": int(rep.n_observations),
        "n_parameters": int(rep.n_parameters),
        "operational_noise_rel": float(noise_rel),
        "operational_cutoff_symlog": op_cut,
        "rank_curve": curve,
        "rank_at_operational_cutoff": int(rep.identifiable_rank),
        "resolvable_rank": int(rep.resolvable_rank),
        "largest_gap_after_index": gap_idx,
        "largest_gap_ratio": gap_ratio,
        "operational_cutoff_falls_in_largest_gap": in_gap,
        "bare_integer_rank_justified": bool(in_gap) if in_gap is not None else False,
        "plateau_containing_operational_cutoff": {
            "noise_rel_lo": lo, "noise_rel_hi": hi,
            "limited_by_resolvable_rank": bool(
                rep.identifiable_rank == rep.resolvable_rank),
            "note": "a wide plateau means the rank does not move with the cutoff -- UNLESS it is pinned by resolvable_rank, in which case the estimator's own floor is doing the work and the plateau says nothing about the spectrum's population structure",
        },
        "how_to_quote": (
            f"rank {rep.identifiable_rank} at cutoff {op_cut:.3e} symlog "
            f"(noise_rel={noise_rel:g})"
            + ("; the cutoff falls inside the largest multiplicative gap "
               f"(x{gap_ratio:.2f} after index {gap_idx}), so this is a "
               "population boundary and the bare integer may be quoted"
               if in_gap else
               "; the cutoff does NOT fall inside the largest multiplicative "
               f"gap (x{gap_ratio:.2f} after index {gap_idx}) -- this is a "
               "threshold count and must never be quoted without its cutoff")),
    }
