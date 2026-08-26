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

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

import numpy as np

#: Chart coordinates: ``d`` log10 magnitudes, as a sequence or a NumPy array.
#: Spelled out because every caller here passes an ndarray and mypy will not
#: accept one as a ``Sequence[float]``.
Coords = Union[Sequence[float], np.ndarray]

__all__ = [
    "Chart",
    "ChartG",
    "ChartJ",
    "ChartL",
    "ChartedDoping",
    "anchor_signed_to_grid",
    "chart_forward_jacobian",
    "containment",
    "project_into_chart",
    "regrid_signed",
]


# ---------------------------------------------------------------------------
# The reconstruction operator -- one definition, for the whole repository
# ---------------------------------------------------------------------------

def _lerp(x_out: Coords, x_in: Coords, y_in: Coords) -> np.ndarray:
    """Piecewise-linear resampling: **the** operator that reaches the solver grid.

    Generation 8's ``CHART-01`` fix is the sentence "every doping array the
    solver integrates was produced by this function, and the caller said which
    chart it meant". Before it there were **five** implementations reachable from
    the analysis entry points -- ``make_oracle`` L56-57, ``run_witness_falsifier``
    L58-59, :meth:`ChartG.reconstruct`, :meth:`ChartL.reconstruct`, and the
    resampler inside ``ScharfetterGummel1D.solve`` that fired whenever a caller
    handed the solver a short array -- and which one ran was decided by which
    file you called.

    ``tests/test_one_reconstruction_g8.py`` is what keeps the sentence true: it
    walks the AST of every module under ``src/`` and ``scripts/`` and fails if an
    interpolation onto a solver grid appears outside this module without being
    named in its allowlist with a reason.
    """
    return np.interp(np.asarray(x_out, dtype=np.float64),
                     np.asarray(x_in, dtype=np.float64),
                     np.asarray(y_in, dtype=np.float64))


def anchor_signed_to_grid(C_anchor: Coords, n_grid: int) -> np.ndarray:
    """Chart L's reconstruction, applied to **signed** doping at equally spaced anchors.

    Byte-identical to the resampler deleted from ``ScharfetterGummel1D.solve`` in
    generation 8, and pinned to it by
    ``tests/test_one_reconstruction_g8.py::test_matches_the_deleted_solver_resampler``
    against 24 vectors frozen from the old code path before it was removed
    (``tests/data/chart_l_resampler_golden_g8.json``). Nothing this function
    returns differs from what the solver used to compute silently; the difference
    is that the caller now says it.

    Use it wherever a study has signed doping at ``d`` equally spaced anchors and
    a solver grid, and no :class:`Chart` object -- dataset generation, surrogate
    supervision, the demo scripts. Where the study *is* an identifiability
    measurement, build the chart and pass :class:`ChartedDoping` instead, so the
    chart travels with the vector rather than being re-chosen at each call site.
    """
    C = np.asarray(C_anchor, dtype=np.float64)
    if C.ndim != 1:
        raise ValueError(f"expected a 1-D anchor vector, got shape {C.shape}")
    n = int(n_grid)
    if C.shape[0] == n:
        return C
    return _lerp(np.linspace(0.0, 1.0, n), np.linspace(0.0, 1.0, C.shape[0]), C)


def regrid_signed(x_out: Coords, x_in: Coords, C: Coords) -> np.ndarray:
    """Chart L's interpolant on a **stated physical** abscissa rather than node index.

    Distinct from :func:`anchor_signed_to_grid`, and the distinction is the whole
    of ``CHART-01``: on a uniform grid the two agree exactly, on any other grid
    they are different reconstruction operators. Callers that hold real positions
    -- the active-learning loop resampling a user's profile onto the oracle's
    ``x`` -- use this one and say so.
    """
    return _lerp(x_out, x_in, C)


@dataclass(frozen=True)
class ChartedDoping:
    """A doping parameter vector that carries the chart it is a vector *in*.

    ``CHART-01``, stated as a type. A bare length-``d`` array crossing an API
    boundary is a chart selection made by whichever file receives it; six
    generations of identifiability results were published that way. This is how a
    parameter vector travels instead.

    ``ScharfetterGummel1D.solve`` accepts one of these, calls :meth:`on_grid`, and
    raises ``DopingChartError`` on any other array that is not already grid-valued.
    """

    chart: "Chart"
    theta: np.ndarray

    def on_grid(self) -> np.ndarray:
        """The ``N``-node profile. The solver calls this and nothing else."""
        return self.chart.reconstruct(self.theta)

    @property
    def d(self) -> int:
        return int(np.asarray(self.theta).shape[0])

    def label(self) -> str:
        return self.chart.label()


class Chart:
    """A map from ``d`` coordinates to an ``N``-node profile.

    Subclasses differ in exactly two declared ways, and nothing else:

    :attr:`abscissa`
        where the anchors live -- ``"physical"`` (metres along the device,
        ``x_si``) or ``"index"`` (normalised node index). On a uniform grid the
        two coincide; on any other grid they are different operators. Until
        generation 8 this was decided by which file you called.
    :meth:`reconstruct`
        what quantity is interpolated between the anchors, and how the sign is
        placed.

    Both reach the grid through :meth:`_to_grid`, which is the only route in the
    package (see :func:`_lerp`).
    """

    #: Short label used in tables and manifests.
    name = "chart"

    #: ``"physical"`` or ``"index"``. See the class docstring.
    abscissa = "physical"

    def __init__(self, d: int, x_si: np.ndarray) -> None:
        if d < 2:
            raise ValueError(f"a chart needs at least 2 anchors, got {d}")
        self.d = int(d)
        self.x_si = np.asarray(x_si, dtype=np.float64)
        self.N = int(self.x_si.shape[0])
        self.mid = 0.5 * (self.x_si.min() + self.x_si.max())
        #: How many of the ``d`` coordinates are log10 magnitudes at anchors.
        #: Equal to ``d`` for every chart whose coordinates are *only*
        #: magnitudes; :class:`ChartJ` spends one coordinate on the junction.
        self.n_mag = self._n_mag(self.d)
        self.anchors = np.linspace(self.x_si.min(), self.x_si.max(), self.n_mag)
        #: Project sign convention (PH-03/PH-04): acceptors left, donors right.
        self.anchor_signs = np.where(self.anchors < self.mid, -1.0, 1.0)

    @staticmethod
    def _n_mag(d: int) -> int:
        return int(d)

    # -- the one route to the grid -----------------------------------------

    def _to_grid(self, y_anchor: Coords) -> np.ndarray:
        """Anchor values -> grid values, by this chart's declared abscissa.

        Every chart reconstruction in this repository passes through here.
        """
        y = np.asarray(y_anchor, dtype=np.float64)
        if y.shape[0] != self.n_mag:
            raise ValueError(f"{self.label()} interpolates {self.n_mag} anchor "
                             f"values, got {y.shape[0]}")
        if self.abscissa == "physical":
            return _lerp(self.x_si, self.anchors, y)
        if self.abscissa == "index":
            return _lerp(np.linspace(0.0, 1.0, self.N),
                         np.linspace(0.0, 1.0, self.n_mag), y)
        raise ValueError(f"{self.label()}: unknown abscissa {self.abscissa!r}")

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        raise NotImplementedError

    def on_grid_signed(self, C_anchor: Coords) -> np.ndarray:
        """Reconstruct from **signed** doping at the anchors, not from log10.

        The coordinates ``sg_forward_jacobian`` differentiates are signed
        ``C`` values, not ``log10|C|``, so a chart has to be able to receive them
        in that form. Same operator, same abscissa; only the quantity differs.
        """
        raise NotImplementedError

    # -- carrying the chart across an API boundary --------------------------

    def charted(self, log10_mag: Coords) -> ChartedDoping:
        """Wrap coordinates so they carry this chart to the solver (``CHART-01``)."""
        return ChartedDoping(self, np.asarray(log10_mag, dtype=np.float64))

    def solver_input(self, log10_mag: Coords) -> ChartedDoping:
        """What the study passes to ``ScharfetterGummel1D.solve``.

        Before generation 8 this returned a bare array, and what happened next
        depended on its length: an ``N``-node array was integrated as given,
        while a ``d``-node array was silently interpolated by the solver. Both
        charts now return a :class:`ChartedDoping`, the solver reconstructs
        through the chart, and a bare short array raises instead.
        """
        return self.charted(log10_mag)

    # -- WIT-01: what the representation can actually resolve ---------------

    def coordinate_resolution(self, log10_mag: Coords) -> np.ndarray:
        """Smallest change in each coordinate that changes the grid profile.

        ``WIT-01``, as a property of the chart rather than of a search. A
        witness pair is two devices the *instrument* cannot tell apart, and that
        is a statement about semiconductors only if the *representation* can
        tell them apart in the first place. A coordinate difference the
        reconstruction rounds away produces two identical ``N``-node profiles,
        which are then indistinguishable for a reason that has nothing to do
        with the device.

        For a magnitude coordinate the answer is **zero**. :meth:`_to_grid`
        carries anchor values into :func:`_lerp` exactly and the map from anchor
        magnitudes to grid values is injective, so no difference is rounded
        away. Charts whose coordinates are *only* magnitudes therefore have no
        sub-resolution pairs at all and the rule is vacuous for them -- which is
        stated here rather than left to be assumed, because "the rule does not
        bite" and "the rule was not applied" are different sentences and only
        one of them is checkable. :class:`ChartJ` overrides this, because its
        junction coordinate moves a sign flip that is applied *on the grid* and
        therefore moves in whole nodes.

        Returns
        -------
        (d,) resolutions, each in its own coordinate's units.
        """
        theta = np.asarray(log10_mag, dtype=np.float64)
        if theta.shape[0] != self.d:
            raise ValueError(f"{self.label()} takes {self.d} coordinates, "
                             f"got {theta.shape[0]}")
        return np.zeros(self.d, dtype=np.float64)

    def separation_is_resolved(self, theta_a: Coords,
                               theta_b: Coords) -> np.ndarray:
        """Per coordinate: does this difference change the reconstruction?

        The *exact* companion to :meth:`coordinate_resolution`, which is a local
        linearisation and so is a scale to report rather than a test to apply. A
        magnitude coordinate resolves any nonzero difference; :class:`ChartJ`
        overrides the junction coordinate with the exact node test.
        """
        a = np.asarray(theta_a, dtype=np.float64)
        b = np.asarray(theta_b, dtype=np.float64)
        if a.shape[0] != self.d or b.shape[0] != self.d:
            raise ValueError(f"{self.label()} takes {self.d} coordinates, "
                             f"got {a.shape[0]} and {b.shape[0]}")
        return a != b

    def label(self) -> str:
        return f"{self.name}(d={self.d})"


class ChartG(Chart):
    """Geometric interpolation of the magnitude; hard sign flip at the midpoint.

    Was decided by ``scripts/run_global_identifiability.py::make_oracle`` L60--62
    and, separately and identically, by
    ``scripts/run_witness_falsifier.py::solve_profile`` L58--59 -- two copies of
    one chart: the study, and the falsifier that was supposed to be independent
    of it. Both now call this class.
    """

    name = "G"
    abscissa = "physical"

    def __init__(self, d: int, x_si: np.ndarray) -> None:
        super().__init__(d, x_si)
        self.sign_grid = np.where(self.x_si < self.mid, -1.0, 1.0)

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        return self.sign_grid * 10.0 ** self._to_grid(log10_mag)

    def on_grid_signed(self, C_anchor: Coords) -> np.ndarray:
        C = np.asarray(C_anchor, dtype=np.float64)
        return self.reconstruct(np.log10(np.abs(C)))


class ChartL(Chart):
    """Arithmetic interpolation of the signed value, on the solver's index grid.

    Was decided by ``scripts/run_identifiability.py`` (``N_ANCHOR``) reaching a
    resampler inside ``ScharfetterGummel1D.solve`` -- a chart chosen by an array
    length, in a file that never mentions charts. Generation 8 deleted that
    resampler; this class is now the only place the operator exists, and
    :func:`anchor_signed_to_grid` is the same operator for callers holding signed
    ``C`` and no chart object.

    The old positive control compared :meth:`reconstruct` against the solver's
    own stored ``DeviceState.doping``. With the resampler gone that control is
    vacuous -- the solver now calls this method -- so it is replaced by
    :meth:`assert_matches_frozen_reference`, which compares against 24 vectors
    captured from the deleted code path before it was deleted.
    """

    name = "L"
    abscissa = "index"

    def reconstruct(self, log10_mag: Coords) -> np.ndarray:
        return self._to_grid(self.signed_anchors(log10_mag))

    def signed_anchors(self, log10_mag: Coords) -> np.ndarray:
        """The ``d`` signed anchor values this chart interpolates between."""
        return self.anchor_signs * 10.0 ** np.asarray(log10_mag, dtype=np.float64)

    def on_grid_signed(self, C_anchor: Coords) -> np.ndarray:
        return self._to_grid(C_anchor)

    def assert_matches_frozen_reference(self, C_anchor: Coords,
                                        expected: Coords) -> float:
        """Regression control against the deleted solver resampler.

        ``expected`` is a profile the *old* ``ScharfetterGummel1D.solve`` produced
        from ``C_anchor``, frozen before the resampler was removed. Returns the
        max relative disagreement and raises above round-off. A chart definition
        that is only asserted is a chart definition that can drift.
        """
        mine = self.on_grid_signed(C_anchor)
        ref = np.asarray(expected, dtype=np.float64)
        err = float(np.max(np.abs(ref - mine) / np.maximum(np.abs(mine), 1e-300)))
        if err > 1e-15:
            raise AssertionError(
                f"ChartL disagrees with the frozen pre-g8 solver resampler by "
                f"{err:.3e}; the CHART-01 fix changed a published number")
        return err


class ChartJ(Chart):
    """Geometric magnitude over ``d-1`` anchors, with the **junction free**.

    Charts G and L differ only in whether the interpolation between anchors is
    geometric or arithmetic. Every invariance statement measured across those two
    is measured along one axis with two points on it, which the generation-7 state
    file recorded as its highest remaining scientific risk. This chart is a point
    off that axis, and it is off it for a physical reason rather than a numerical
    one: **where the junction sits is a fabrication parameter**, and neither G nor
    L lets it move.

    Coordinates, ``d`` of them::

        theta = [s, m_1, ..., m_{d-1}]

    ``m_i = log10|C|`` at ``d-1`` equally spaced anchors, exactly as in chart G.
    ``s`` places the junction, in decades of the ratio ``x_j / (L - x_j)``::

        x_j / L = 1 / (1 + 10 ** (-s * junction_scale))

    ``s = 0`` is the device midpoint. So **chart J at ``s = 0`` is chart G at
    ``d-1``**, exactly. That is this chart's positive control, and it is also the
    negative control for "the third chart is genuinely different": a
    discriminator that cannot return *not different* for a pinned junction is not
    measuring anything.

    How the reachable sets differ, precisely
    ----------------------------------------
    * Chart G's sign flip is pinned between the two grid nodes straddling the
      midpoint. It cannot move, at any ``d``.
    * Chart L's zero crossing is *not* pinned to the midpoint -- it lands where
      the arithmetic interpolant crosses zero, which depends on the two
      magnitudes straddling the midpoint -- but it cannot leave the one anchor
      interval of width ``L/(d-1)`` that contains the midpoint.
    * Chart J's junction is free over the whole device, and is a genuine
      discontinuity wherever it lands.

    ``junction_scale`` and why it is reported rather than chosen
    ------------------------------------------------------------
    A Jacobian whose columns carry different units has a basis-dependent singular
    spectrum, and here ``d-1`` columns are decades of doping while one is decades
    of junction ratio. There is no units-free choice, so the choice is *stated*
    and its effect *measured*: ``junction_scale`` rescales the junction
    coordinate, and generation 8 reports the spectrum over a range of it rather
    than at one value -- ``SPEC-11``'s rank-curve rule, applied to a coordinate
    scaling instead of to a cutoff.

    Grid quantisation
    -----------------
    The sign flip is applied on the grid, so ``x_j`` moves in steps of one node.
    A finite-difference step in ``s`` that moves the junction less than one node
    differentiates a constant and returns exactly zero.
    :meth:`junction_node_shift` reports the shift in nodes for a given step, so
    the estimator can be checked against the discretisation rather than trusted.
    """

    name = "J"
    abscissa = "physical"

    def __init__(self, d: int, x_si: np.ndarray,
                 junction_scale: float = 1.0) -> None:
        if d < 3:
            raise ValueError(
                f"chart J spends one coordinate on the junction, so it needs at "
                f"least 3 (2 magnitudes + 1 junction), got {d}")
        super().__init__(d, x_si)
        self.junction_scale = float(junction_scale)

    @staticmethod
    def _n_mag(d: int) -> int:
        return int(d) - 1

    def junction_position(self, s: float) -> float:
        """``x_j`` in metres, for junction coordinate ``s``."""
        frac = 1.0 / (1.0 + 10.0 ** (-float(s) * self.junction_scale))
        lo, hi = float(self.x_si.min()), float(self.x_si.max())
        return lo + frac * (hi - lo)

    def junction_node_shift(self, s: float, ds: float) -> float:
        """Grid nodes the junction moves when ``s`` changes by ``ds``."""
        dx = abs(self.junction_position(s + ds) - self.junction_position(s))
        span = float(self.x_si.max() - self.x_si.min())
        return dx / (span / (self.N - 1))

    def node_spacing_si(self) -> float:
        """Grid spacing in metres. One node is the junction's resolution."""
        return float(self.x_si.max() - self.x_si.min()) / (self.N - 1)

    def junction_node_index(self, s: float) -> int:
        """How many grid nodes lie strictly left of the junction at ``s``.

        :meth:`reconstruct` depends on ``s`` **only** through the boolean mask
        ``x_si < x_j``, so this integer is the whole of what the representation
        carries about the junction. Two values of ``s`` sharing it build the
        same profile, bit for bit.
        """
        return int(np.count_nonzero(self.x_si < self.junction_position(s)))

    def coordinate_resolution(self, theta: Coords) -> np.ndarray:
        """``WIT-01``: the junction coordinate resolves in whole grid nodes.

        The magnitude coordinates are exact, as in every chart. The junction is
        not: the sign flip is placed on the grid, so the resolution is the
        change in ``s`` that moves ``x_j`` by one node. It is taken *locally* at
        ``theta[0]`` because ``s -> x_j`` is a logistic and its slope is not
        constant -- the same coordinate is worth far fewer nanometres per decade
        near the contacts than at the midpoint, which is why a single number for
        "the junction resolution" would be wrong at both ends.

        ``dx_j/ds = L ln(10) js f (1 - f)`` with ``f = x_j / L``. Where the slope
        vanishes the resolution is ``inf``: ``junction_scale = 0`` pins the
        junction and *no* change in ``s`` moves it, which is exactly the
        pinned-junction control that generations 8 and 9 rest their junction
        numbers on.
        """
        th = np.asarray(theta, dtype=np.float64)
        if th.shape[0] != self.d:
            raise ValueError(f"{self.label()} takes {self.d} coordinates, "
                             f"got {th.shape[0]}")
        res = np.zeros(self.d, dtype=np.float64)
        span = float(self.x_si.max() - self.x_si.min())
        frac = (self.junction_position(float(th[0]))
                - float(self.x_si.min())) / span
        slope = span * np.log(10.0) * self.junction_scale * frac * (1.0 - frac)
        res[0] = (self.node_spacing_si() / slope) if slope > 0.0 else np.inf
        return res

    def separation_is_resolved(self, theta_a: Coords,
                               theta_b: Coords) -> np.ndarray:
        """Exact per-coordinate resolution test; the junction is a node test."""
        out = super().separation_is_resolved(theta_a, theta_b)
        a = np.asarray(theta_a, dtype=np.float64)
        b = np.asarray(theta_b, dtype=np.float64)
        out = out.copy()
        out[0] = (self.junction_node_index(float(a[0]))
                  != self.junction_node_index(float(b[0])))
        return out

    def reconstruct(self, theta: Coords) -> np.ndarray:
        th = np.asarray(theta, dtype=np.float64)
        if th.shape[0] != self.d:
            raise ValueError(f"{self.label()} takes {self.d} coordinates "
                             f"(1 junction + {self.n_mag} magnitudes), "
                             f"got {th.shape[0]}")
        xj = self.junction_position(th[0])
        return np.where(self.x_si < xj, -1.0, 1.0) * 10.0 ** self._to_grid(th[1:])

    def on_grid_signed(self, C_anchor: Coords) -> np.ndarray:
        C = np.asarray(C_anchor, dtype=np.float64)
        if C.shape[0] != self.d:
            raise ValueError(f"{self.label()} takes {self.d} coordinates")
        return self.reconstruct(
            np.concatenate([C[:1], np.log10(np.abs(C[1:]))]))

    def label(self) -> str:
        if self.junction_scale == 1.0:
            return f"{self.name}(d={self.d})"
        return f"{self.name}(d={self.d},js={self.junction_scale:g})"


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
