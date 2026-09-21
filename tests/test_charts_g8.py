"""``SPEC-g8-2``: chart J, and what makes it a *third* chart rather than a third name.

The generation-7 state file recorded, as its highest remaining scientific risk,
that "the dimension moves the rank and the chart does not" was measured across
two charts that differ in exactly one way -- geometric against arithmetic
interpolation between equally spaced anchors in ``log10|C|``, with the same fixed
sign convention. One axis, two points on it.

Chart J is a point off that axis and it is off it for a physical reason: the
junction position is a fabrication parameter, and charts G and L both pin it.

Two things have to be true for the comparison to mean anything, and both are
tested here rather than asserted in a document:

* **the positive control** -- chart J with its junction at the midpoint must be
  chart G at ``d-1``, bit for bit. If it is not, chart J is not "chart G plus a
  coordinate" and every movement measured against chart G is confounded;
* **the negative control** -- with the junction *pinned* (``junction_scale = 0``)
  the discriminator must return *not different*. A discriminator that always says
  "different" is not measuring anything.

The units problem is tested too, because it is the interesting part. Chart J's
Jacobian has ``d-1`` columns in decades of doping and one in decades of junction
ratio, so its singular spectrum depends on a units choice with no canonical
answer. The tests below pin that the choice is *exposed* (``junction_scale``
changes the spectrum) and that the magnitude sub-block is *invariant* to it --
which is what makes the sub-block the honest comparison.
"""

from __future__ import annotations

import numpy as np
import pytest

from bayespinn_inv.inverse.charts import (
    ChartG,
    ChartJ,
    ChartL,
    chart_forward_jacobian,
    project_into_chart,
)
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

GRID = 301


@pytest.fixture(scope="module")
def rig():
    cfg = GlobalStudyConfig()
    sc = Scaling.for_material(SILICON, T=300.0)
    ls = float(sc.x_to_scaled(np.float64(cfg.domain_si[1] - cfg.domain_si[0])))
    sg = ScharfetterGummel1D(Grid1D.uniform(ls, GRID), sc, SILICON, SGConfig())
    return cfg, sg, sc.x_to_si(np.asarray(sg.grid.x))


# ===========================================================================
# Construction
# ===========================================================================

class TestConstruction:

    def test_it_needs_a_coordinate_to_spend(self, rig):
        _, _, x = rig
        with pytest.raises(ValueError, match="at least 3"):
            ChartJ(2, x)

    def test_d_counts_coordinates_and_one_of_them_is_the_junction(self, rig):
        _, _, x = rig
        J = ChartJ(16, x)
        assert (J.d, J.n_mag) == (16, 15)
        assert J.reconstruct(np.concatenate([[0.0], np.full(15, 22.0)])).shape \
            == (GRID,)
        with pytest.raises(ValueError, match="16 coordinates"):
            J.reconstruct(np.full(16 - 1, 22.0))

    @pytest.mark.parametrize("d", [3, 4, 8, 16])
    def test_positive_control_J_at_s0_is_G_at_d_minus_one(self, rig, d):
        """Bit-identical, at every ``d``, for a generic magnitude vector."""
        _, _, x = rig
        rng = np.random.default_rng(d)
        m = rng.uniform(21.0, 23.0, size=d - 1)
        assert np.array_equal(
            ChartJ(d, x).reconstruct(np.concatenate([[0.0], m])),
            ChartG(d - 1, x).reconstruct(m))

    def test_the_junction_moves_monotonically_and_covers_the_device(self, rig):
        _, _, x = rig
        J = ChartJ(16, x)
        ss = np.linspace(-2.0, 2.0, 21)
        xs = np.array([J.junction_position(s) for s in ss])
        assert np.all(np.diff(xs) > 0)
        assert J.junction_position(0.0) == pytest.approx(0.5e-6, rel=1e-12)
        assert xs[0] > 0.0 and xs[-1] < 1e-6

    def test_pinning_the_junction_makes_the_coordinate_dead(self, rig):
        _, _, x = rig
        Jp = ChartJ(16, x, junction_scale=0.0)
        m = np.full(15, 22.0)
        a = Jp.reconstruct(np.concatenate([[-3.0], m]))
        b = Jp.reconstruct(np.concatenate([[+3.0], m]))
        assert np.array_equal(a, b)
        assert Jp.junction_node_shift(0.0, 0.05) == 0.0


# ===========================================================================
# The reachable set really is different
# ===========================================================================

class TestReachableSet:

    @pytest.mark.parametrize("frac", [0.25, 0.35, 0.65, 0.75])
    def test_neither_G_nor_L_can_place_the_junction(self, rig, frac):
        """The obstruction is in the sign structure and it does not shrink.

        Charts G and L reproduce the *magnitude* of a displaced-junction device
        essentially exactly -- it is a constant here -- and then put the junction
        in the wrong place, because both of them put it at the midpoint. The
        residual is therefore reported as a count of grid nodes doped the wrong
        type, which is a device-level statement, not a norm.
        """
        _, _, x = rig
        J = ChartJ(16, x)
        s = float(np.log10(frac / (1.0 - frac)))
        target = J.reconstruct(np.concatenate([[s], np.full(15, 22.0)]))
        expected = int(abs(frac - 0.5) * (GRID - 1))
        for chart in (ChartG(16, x), ChartL(16, x)):
            worst = GRID
            for method in ("collocate", "log10"):
                th, _ = project_into_chart(chart, target, method=method)
                prof = chart.reconstruct(th)
                worst = min(worst, int(np.sum(np.sign(prof) != np.sign(target))))
            assert worst >= expected - 2, (
                f"{chart.label()} placed the junction at x_j/L={frac} with only "
                f"{worst} nodes of the wrong type; it is not supposed to be able "
                "to place it at all")

    def test_and_it_can_place_the_midpoint(self, rig):
        """The same predicate must return the negative answer where it should.

        Without this the test above is satisfied by a chart that can never
        reproduce anything.
        """
        _, _, x = rig
        J = ChartJ(16, x)
        target = J.reconstruct(np.concatenate([[0.0], np.full(15, 22.0)]))
        th, _ = project_into_chart(ChartG(16, x), target, method="collocate")
        prof = ChartG(16, x).reconstruct(th)
        assert int(np.sum(np.sign(prof) != np.sign(target))) == 0


# ===========================================================================
# The units of the junction coordinate
# ===========================================================================

class TestJunctionUnits:

    def test_the_magnitude_block_does_not_depend_on_the_units_choice(self, rig):
        """What makes the magnitude sub-block the honest comparison.

        Rescaling the junction coordinate rescales one Jacobian column and
        nothing else, so any statement made about the other 15 columns is
        independent of a choice with no canonical answer. Any statement about the
        full spectrum is not, and must carry ``junction_scale``.
        """
        cfg, sg, x = rig
        theta = np.concatenate([[0.0], np.full(15, 22.0)])
        blocks, junction = [], []
        for js in (0.1, 1.0, 10.0):
            J, _, _, _ = chart_forward_jacobian(
                sg, ChartJ(16, x, junction_scale=js), theta, cfg.biases,
                rel_step=0.05, min_snr=1e4)
            blocks.append(J[:, 1:])
            junction.append(float(np.linalg.norm(J[:, 0])))
        for b in blocks[1:]:
            assert np.array_equal(blocks[0], b)
        assert junction[0] < junction[1] < junction[2]

    def test_the_magnitude_block_is_chart_G_at_d_minus_one(self, rig):
        """Positive control for the Jacobian, not just for the reconstruction."""
        cfg, sg, x = rig
        m = np.full(15, 22.0)
        Jj, _, kj, _ = chart_forward_jacobian(
            sg, ChartJ(16, x), np.concatenate([[0.0], m]), cfg.biases,
            rel_step=0.05, min_snr=1e4)
        Jg, _, kg, _ = chart_forward_jacobian(
            sg, ChartG(15, x), m, cfg.biases, rel_step=0.05, min_snr=1e4)
        assert kj == kg
        assert np.array_equal(Jj[:, 1:], Jg)

    def test_the_finite_difference_actually_moves_the_junction(self, rig):
        """``PH-11``-adjacent: an estimator that cannot resolve its own step.

        The sign flip is applied on the grid, so a step in ``s`` that moves the
        junction by less than one node differentiates a constant and returns
        exactly zero. The default step must clear that, and the check is the shift
        in nodes rather than a belief about it.
        """
        _, _, x = rig
        J = ChartJ(16, x)
        assert J.junction_node_shift(0.0, 0.05) > 1.0
        tiny = ChartJ(16, x, junction_scale=1e-4)
        assert tiny.junction_node_shift(0.0, 0.05) < 1.0

    def test_a_junction_column_that_cannot_move_is_exactly_zero(self, rig):
        """The negative control, at the level of the Jacobian."""
        cfg, sg, x = rig
        J, _, _, _ = chart_forward_jacobian(
            sg, ChartJ(16, x, junction_scale=0.0),
            np.concatenate([[0.0], np.full(15, 22.0)]), cfg.biases,
            rel_step=0.05, min_snr=1e4)
        assert np.all(J[:, 0] == 0.0)


# ===========================================================================
# It behaves like a chart
# ===========================================================================

class TestItIsAChart:

    def test_the_jacobian_has_chart_width_not_grid_width(self, rig):
        cfg, sg, x = rig
        J, _, _, _ = chart_forward_jacobian(
            sg, ChartJ(16, x), np.concatenate([[0.0], np.full(15, 22.0)]),
            cfg.biases, rel_step=0.05, min_snr=1e4)
        assert J.shape[1] == 16

    def test_it_reaches_the_solver_carrying_itself(self, rig):
        cfg, sg, x = rig
        J = ChartJ(16, x)
        theta = np.concatenate([[0.3], np.full(15, 22.0)])
        st = sg.solve(J.charted(theta), 0.3)
        assert st.converged
        assert np.array_equal(st.doping, J.reconstruct(theta))

    def test_wrong_coordinate_count_raises_rather_than_broadcasting(self, rig):
        cfg, sg, x = rig
        with pytest.raises(ValueError, match="takes 16 coordinates"):
            chart_forward_jacobian(sg, ChartJ(16, x), np.full(15, 22.0),
                                   cfg.biases)
