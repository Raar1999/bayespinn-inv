"""The two parameterisation charts this repository measures identifiability in.

Why this module exists
----------------------
Generation 6 published two identifiability results:

* a **local** Jacobian rank, "3--4 of 16", from ``scripts/run_identifiability.py``;
* a **global** witness of non-identifiability at ``d = 4``, from
  ``scripts/run_global_identifiability.py``.

The generation-7 reconciliation asked whether the two may be quoted in the same
sentence. They may not, and the reason is not the dimension -- it is that the two
scripts reconstruct a doping profile from its parameters by **different
interpolants**, so ``d`` counts coordinates on two different manifolds.

Naming them is the point of this module. A chart that is never written down is a
chart that gets assumed nested.

The two charts
--------------
Both charts use the same *coordinates*: ``theta = log10|C|`` at ``d`` equally
spaced anchors, with the sign of the doping held fixed. They differ in how they
get from those ``d`` numbers to the ``N``-node profile the solver integrates.

``ChartG`` -- the global-study chart
    ``scripts/run_global_identifiability.py::make_oracle``, lines 60--62::

        mag = 10.0 ** np.interp(x_si, x_anchor, log10_mag)
        doping = sign * mag

    Piecewise-linear **in log10|C|**: geometric interpolation of the magnitude.
    The sign is a hard flip at the device midpoint, applied on the solver grid,
    so the reconstructed profile carries a genuine discontinuity there. Because
    ``make_oracle`` returns a full ``N``-node array, the solver's own resampler
    never runs.

``ChartL`` -- the local-study chart
    ``scripts/run_identifiability.py`` sets ``N_ANCHOR = 16`` and hands a
    **length-16 signed array** to a 301-node solver, which reaches
    ``solvers/scharfetter_gummel.py::ScharfetterGummel1D.solve`` lines 767--774::

        if doping_si.shape[0] != self.grid.N:
            x_in = np.linspace(0.0, 1.0, doping_si.shape[0])
            x_grid = np.linspace(0.0, 1.0, self.grid.N)
            doping_si = np.interp(x_grid, x_in, doping_si)

    Piecewise-linear **in C**: arithmetic interpolation of the signed value. The
    chart is not written anywhere in the analysis script; it is a side effect of
    a convenience resampler in the solver. That is exactly why it went unnoticed.

Containment
-----------
:func:`containment` decides the relation from the constructions, and
``docs/CHART_RECONCILIATION_g7.md`` records the result. The structural argument,
which holds at every finite ``d`` and needs no measurement:

Between two adjacent anchors carrying magnitudes ``u`` and ``v`` of the same
sign, ``ChartG`` traces ``t -> u**(1-t) * v**t`` and ``ChartL`` traces
``t -> (1-t)*u + t*v``. Geometric and arithmetic interpolation agree **iff**
``u == v``. So the images of the two charts intersect exactly in the
piecewise-constant profiles, a measure-zero subset of each. **Neither contains
the other**, and no choice of ``d`` on either side changes that -- raising ``d``
refines both families without making either a subset of the other.

There is a second, independent obstruction in the sign structure. ``ChartG``
places a jump discontinuity between the two grid nodes that straddle the
midpoint. ``ChartL`` produces a continuous piecewise-linear function and must
ramp through zero across a whole anchor interval, smearing the junction over
``L/(d-1)`` metres. A continuous function cannot equal a discontinuous one, so
this obstruction does not vanish as ``d`` grows either -- it only narrows.

Consequences for what may be said
---------------------------------
* A rank measured in one chart is a statement about **that chart's reachable
  set**, not about doping profiles in general (``PH-21`` extended).
* Rank *fractions* are not comparable across charts. "3--4 of 16" and "3 of 4"
  are different denominators over different manifolds; the generation-7 ruling
  forbids quoting them in one sentence even once the reconciliation table exists.
* A witness pair found in one chart is not automatically a witness in the other,
  and a failed embedding says the pair lies **outside** the target chart -- never
  that the degeneracy was an artefact of the source chart's dimension.

dtype
-----
``PH-22``: everything here is float64. These charts feed the NumPy oracle, the
only path permitted to arbitrate a published identifiability number.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple, Union

import numpy as np

#: Chart coordinates: ``d`` log10 magnitudes, as a sequence or a NumPy array.
#: Spelled out because every caller here passes an ndarray and mypy will not
#: accept one as a ``Sequence[float]``.
Coords = Union[Sequence[float], np.ndarray]

__all__ = [
    "Chart",
    "ChartG",
    "ChartL",
    "chart_forward_jacobian",
    "containment",
    "project_into_chart",
]


class Chart:
    """A map from ``d`` log10-magnitude coordinates to an ``N``-node profile."""

    #: Short label used in tables and manifests.
    name = "chart"

    def __init__(self, d: int, x_si: np.ndarray) -> None:
        if d < 2:
            raise ValueError(f"a chart needs at least 2 anchors, got {d}")
        self.d = int(d)
        self.x_si = np.asarray(x_si, dtype=np.float64)
        self.N = int(self.x_si.shape[0])
        self.mid = 0.5 * (self.x_si.min() + self.x_si.max())
        self.anchors = np.linspace(self.x_si.min(), self.x_si.max(), self.d)
        #: Project sign convention (PH-03/PH-04): acceptors left, donors right.
        self.anchor_signs = np.where(self.anchors < self.mid, -1.0, 1.0)

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        raise NotImplementedError

    def solver_input(self, log10_mag: Coords) -> np.ndarray:
        """What the study actually passes to ``ScharfetterGummel1D.solve``.

        The distinction matters: ``ChartG`` passes an ``N``-node array and the
        solver's resampler never fires, while ``ChartL`` passes a ``d``-node
        array *specifically so that it does*. Driving the oracle through this
        method keeps the measurement on the real code path.
        """
        return self.reconstruct(log10_mag)

    def label(self) -> str:
        return f"{self.name}(d={self.d})"


class ChartG(Chart):
    """Geometric interpolation of the magnitude; hard sign flip at the midpoint.

    Decided by ``scripts/run_global_identifiability.py::make_oracle`` L60--62.
    """

    name = "G"

    def __init__(self, d: int, x_si: np.ndarray) -> None:
        super().__init__(d, x_si)
        self.sign_grid = np.where(self.x_si < self.mid, -1.0, 1.0)

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        mag = 10.0 ** np.interp(
            self.x_si, self.anchors, np.asarray(log10_mag, dtype=np.float64))
        return self.sign_grid * mag


class ChartL(Chart):
    """Arithmetic interpolation of the signed value, on the solver's index grid.

    Decided by ``scripts/run_identifiability.py`` (``N_ANCHOR``) reaching
    ``solvers/scharfetter_gummel.py::ScharfetterGummel1D.solve`` L767--774.

    ``reconstruct`` replicates that resampler so the profile can be analysed
    without a solve; :meth:`assert_matches_solver` checks the replication against
    the solver's own stored ``DeviceState.doping``, which is written *after* the
    resampling. A chart definition that is only asserted is a chart definition
    that can drift from the code it claims to describe.
    """

    name = "L"

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        C_d = self.solver_input(log10_mag)
        return np.interp(np.linspace(0.0, 1.0, self.N),
                         np.linspace(0.0, 1.0, self.d), C_d)

    def solver_input(self, log10_mag: Coords) -> np.ndarray:
        return self.anchor_signs * 10.0 ** np.asarray(log10_mag, dtype=np.float64)

    def assert_matches_solver(self, solver, log10_mag: Coords,
                              bias: float = 0.0) -> float:
        """Positive control: does the solver reconstruct what this chart says?

        Returns the max relative disagreement. Raises if it is above round-off.
        """
        state = solver.solve(self.solver_input(log10_mag), bias)
        mine = self.reconstruct(log10_mag)
        err = float(np.max(np.abs(state.doping - mine)
                           / np.maximum(np.abs(mine), 1e-300)))
        if err > 1e-12:
            raise AssertionError(
                f"ChartL.reconstruct disagrees with the solver's resampler by "
                f"{err:.3e}; the chart definition has drifted from "
                f"scharfetter_gummel.py:767-774")
        return err


def chart_forward_jacobian(oracle, chart: Chart, log10_mag: Coords,
                           biases: Sequence[float], I0: float = 1e-6,
                           rel_step: float = 1e-2, min_snr: float = 1e4):
    """``d symlog(I) / d theta_j`` through the SG oracle, in **chart** coordinates.

    Generalises
    :func:`~bayespinn_inv.inverse.identifiability.sg_forward_jacobian`, which
    perturbs entries of whatever array it is handed. That is the same thing only
    when the array *is* the chart's coordinate vector -- true for ``ChartL``,
    false for ``ChartG``, whose profile array has one entry per grid node. Taking
    ``ChartG``'s Jacobian with the old function would differentiate a 301-node
    profile and silently answer a different question.

    ``ChartL`` is therefore the positive control: for it this function and
    ``sg_forward_jacobian`` must agree to round-off, and
    ``tests/test_charts_g7.py`` pins that.

    The estimator discipline is inherited unchanged: central differences in
    decades of doping, bias rows below ``min_snr`` against the oracle's own noise
    floor discarded rather than differenced, and the per-entry noise returned so
    :func:`analyse_identifiability` cannot claim resolution it does not have.

    ``PH-22``: float64, the NumPy oracle path.

    Returns
    -------
    J : (B_used, d)
    I_ref : (B_used,) reference currents
    kept : indices of the biases actually used
    entry_noise : estimated absolute noise on one Jacobian entry
    """
    from bayespinn_inv.inverse.identifiability import symlog

    theta = np.asarray(log10_mag, dtype=np.float64)
    if theta.shape[0] != chart.d:
        raise ValueError(f"{chart.label()} takes {chart.d} coordinates, "
                         f"got {theta.shape[0]}")

    def _iv(th):
        prev, out, floors = None, [], []
        for V in biases:
            st = oracle.solve(chart.solver_input(th), float(V), initial_state=prev)
            prev = st
            out.append(st.terminal_current)
            floors.append(st.current_noise_floor)
        return np.asarray(out), np.asarray(floors)

    I_ref, floors = _iv(theta)
    kept = [i for i in range(len(I_ref)) if abs(I_ref[i]) > min_snr * floors[i]]
    if not kept:
        raise ValueError(
            f"No bias point reached SNR > {min_snr:g} against the oracle's own "
            f"noise floor in {chart.label()}; a finite-difference Jacobian here "
            "would be noise.")

    J = np.zeros((len(kept), chart.d))
    for j in range(chart.d):
        tp = theta.copy()
        tm = theta.copy()
        tp[j] += rel_step
        tm[j] -= rel_step
        Ip, _ = _iv(tp)
        Im, _ = _iv(tm)
        J[:, j] = (symlog(Ip[kept], I0) - symlog(Im[kept], I0)) / (2.0 * rel_step)

    rel_prec = np.asarray([floors[i] / max(abs(I_ref[i]), 1e-300) for i in kept])
    entry_noise = float(np.max(rel_prec) / np.log(10.0)
                        * np.sqrt(2.0) / (2.0 * rel_step))
    return J, I_ref[kept], kept, entry_noise


def containment(chart_a: Chart, chart_b: Chart,
                log10_mag: Coords) -> Dict[str, float]:
    """Can ``chart_b`` reproduce the profile ``chart_a`` builds from ``log10_mag``?

    ``chart_b`` is given its best shot: its coordinates are **collocated** from
    ``chart_a``'s profile, which is exact at every one of ``chart_b``'s anchors.
    Whatever residual survives is therefore a property of the interpolants
    between anchors, not of a poor fit.

    Returns the residual in decades on the shared grid, and the number of grid
    nodes where the two disagree in sign.
    """
    prof_a = chart_a.reconstruct(log10_mag)
    theta_b = np.interp(chart_b.anchors, chart_a.anchors,
                        np.asarray(log10_mag, dtype=np.float64))
    prof_b = chart_b.reconstruct(theta_b)
    with np.errstate(divide="ignore", invalid="ignore"):
        dec = np.abs(np.log10(np.abs(prof_b)) - np.log10(np.abs(prof_a)))
    finite = np.isfinite(dec)
    return {
        "max_decades": float(np.max(dec[finite])) if finite.any() else float("inf"),
        "rms_decades": (float(np.sqrt(np.mean(dec[finite] ** 2)))
                        if finite.any() else float("inf")),
        "max_rel": float(np.max(np.abs(prof_b - prof_a)
                                / np.maximum(np.abs(prof_a), 1e-300))),
        "sign_disagreements": int(np.sum(np.sign(prof_b) != np.sign(prof_a))),
        "nodes_nonfinite": int(np.sum(~finite)),
        "n_nodes": int(prof_a.shape[0]),
    }


def project_into_chart(chart: Chart, target_profile: np.ndarray,
                       method: str = "log10",
                       source_chart: Optional[Chart] = None,
                       source_log10: Optional[Coords] = None,
                       ) -> Tuple[np.ndarray, Dict[str, object]]:
    """Best ``chart`` coordinates for a profile the chart cannot represent exactly.

    Three methods, all reported rather than one chosen silently -- the choice of
    norm is itself an assumption, and a "best approximation" that hides its norm
    is unfalsifiable.

    ``"collocate"``
        ``theta_j = log10|target(anchor_j)|``. Exact at the anchors. The naive
        embedding, and the one an unwary reader would assume.
    ``"linear_C"``
        Least squares in the signed value ``C``. ``ChartL`` is linear in its own
        coefficients, so this is an exact linear solve with no optimiser.
    ``"log10"``
        Least squares in ``log10|C|`` -- relative doping error, the metric the
        rest of the repository uses. Nonlinear; solved with a robust loss so the
        one or two nodes where the chart must ramp through zero cannot dominate
        the fit. Those nodes are **counted and returned**, never dropped (PH-19).

    Returns ``(theta, diagnostics)``.
    """
    target = np.asarray(target_profile, dtype=np.float64)
    anchors_norm = np.linspace(0.0, 1.0, chart.d)
    grid_norm = np.linspace(0.0, 1.0, chart.N)

    if method == "collocate":
        if source_chart is not None and source_log10 is not None:
            theta = np.interp(chart.anchors, source_chart.anchors,
                              np.asarray(source_log10, dtype=np.float64))
        else:
            theta = np.log10(np.abs(np.interp(chart.anchors, chart.x_si, target)))
        return theta, {"method": method}

    if method == "linear_C":
        basis = np.stack([
            np.interp(grid_norm, anchors_norm, np.eye(chart.d)[j])
            for j in range(chart.d)], axis=1)                      # (N, d)
        coef, *_ = np.linalg.lstsq(basis, target, rcond=None)
        with np.errstate(divide="ignore", invalid="ignore"):
            theta = np.log10(np.abs(coef))
        return theta, {
            "method": method,
            "coef_sign_flips_vs_chart":
                int(np.sum(np.sign(coef) != chart.anchor_signs)),
        }

    if method == "log10":
        from scipy.optimize import least_squares

        logt = np.log10(np.abs(target))
        theta0, _ = project_into_chart(chart, target, method="collocate",
                                       source_chart=source_chart,
                                       source_log10=source_log10)

        def resid(theta):
            prof = chart.reconstruct(theta)
            with np.errstate(divide="ignore", invalid="ignore"):
                r = np.log10(np.abs(prof)) - logt
            return np.nan_to_num(r, nan=0.0, posinf=6.0, neginf=-6.0)

        sol = least_squares(resid, theta0, loss="soft_l1", f_scale=0.05,
                            max_nfev=4000)
        prof = chart.reconstruct(sol.x)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log10(np.abs(prof)) - logt
        good = np.isfinite(r)
        return sol.x, {
            "method": method,
            "loss": "soft_l1",
            "f_scale": 0.05,
            "nfev": int(sol.nfev),
            "nodes_saturated": int(np.sum(~good)),
            "max_decades": float(np.max(np.abs(r[good]))) if good.any() else None,
        }

    raise ValueError(f"unknown method {method!r}")
