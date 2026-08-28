"""``SPEC-g8-1``: there is exactly one way for a doping vector to reach the grid.

What ``CHART-01`` actually was
------------------------------
Not "two charts went unrecorded". Two *reconstruction operators* for one
coordinate vector, in files that never refer to each other, selected by which
entry point was called. Generation 7 named the charts; naming them does not stop
a third from appearing, so generation 8 removes the mechanism.

A census taken over the full test suite at the moment of the fix, by patching
``ScharfetterGummel1D.solve`` and counting every call whose doping array was not
grid-valued, found **seven** distinct production call sites relying on the
implicit resampler across **three** grid resolutions -- including
``sg_forward_jacobian``, which produced the published local rank, and
``simulate_iv_dataset``, which produced the surrogate's entire training set.
None of them said which chart they meant, because none of them knew they were
choosing one.

The three guards below are the operator's three bullets, in order.

1. ``TestOneOperator`` -- one reconstruction operator, one definition, used by
   both entry points, and byte-identical to the deleted one.
2. ``TestTheVectorCarriesItsChart`` -- a bare length-``d`` array handed to a
   solver expecting a grid raises rather than interpolating by whatever that
   file happens to do.
3. ``TestNoSecondPathCanBeIntroduced`` -- an AST guard that fails when a second
   reconstruction path appears anywhere under ``src/`` or ``scripts/``.

``SW-20`` and this module
-------------------------
Guard 3's subject is source code, so it is written over the AST and ships both
controls: :meth:`test_the_guard_catches_a_planted_violation` plants one, and
:meth:`test_the_guard_does_not_fire_on_prose_describing_it` supplies a module
whose *text* contains the forbidden call and whose *code* does not. This module
excludes itself from the scan, and the exclusion is asserted rather than trusted.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from bayespinn_inv.inverse.charts import (
    ChartedDoping,
    ChartG,
    ChartJ,
    ChartL,
    anchor_signed_to_grid,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    DopingChartError,
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "data" / "chart_l_resampler_golden_g8.json"


@pytest.fixture(scope="module")
def solver():
    sc = Scaling.for_material(SILICON, T=300.0)
    L_s = float(sc.x_to_scaled(np.float64(1e-6)))
    sg = ScharfetterGummel1D(Grid1D.uniform(L_s, 301), sc, SILICON, SGConfig())
    return sg, sc.x_to_si(np.asarray(sg.grid.x))


# ===========================================================================
# 1. One reconstruction operator
# ===========================================================================

class TestOneOperator:

    def test_matches_the_deleted_solver_resampler(self):
        """The fix must not have moved a single published number.

        ``tests/data/chart_l_resampler_golden_g8.json`` holds 24 profiles the
        *old* ``ScharfetterGummel1D.solve`` produced, captured from the running
        code before the resampler was deleted, across three grid resolutions and
        four dimensions. Comparing against a re-implementation would prove
        nothing; comparing against the outputs of the code that is gone is the
        only check that can still fail.
        """
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        assert len(golden["cases"]) == 24
        for case in golden["cases"]:
            C = np.asarray(case["C_anchor"], dtype=np.float64)
            mine = anchor_signed_to_grid(C, case["grid_N"])
            assert mine.shape == (case["grid_N"],)
            assert hashlib.sha256(mine.tobytes()).hexdigest() == \
                case["grid_sha256"], (
                    f"chart L moved for d={case['d']} N={case['grid_N']} "
                    f"{case['kind']}: the CHART-01 fix changed a number")

    def test_chartL_reconstruct_is_that_same_operator(self, solver):
        """``ChartL`` is not a parallel implementation; it calls the operator."""
        _, x_si = solver
        L = ChartL(16, x_si)
        theta = np.linspace(21.0, 23.0, 16)
        assert np.array_equal(
            L.reconstruct(theta),
            anchor_signed_to_grid(L.signed_anchors(theta), L.N))

    def test_every_chart_reaches_the_grid_through_to_grid(self, solver):
        """No chart may interpolate on its own; all of them go through ``_to_grid``.

        Enforced by counting: ``_to_grid`` is replaced with a counting wrapper and
        each chart's ``reconstruct`` must call it exactly once. A chart that grew
        its own resampler would call it zero times and still return a profile.
        """
        _, x_si = solver
        calls = {"n": 0}
        for chart, theta in (
            (ChartG(4, x_si), np.full(4, 22.0)),
            (ChartL(16, x_si), np.full(16, 22.0)),
            (ChartJ(16, x_si), np.concatenate([[0.0], np.full(15, 22.0)])),
        ):
            calls["n"] = 0
            real = chart._to_grid

            def counted(y, _real=real):
                calls["n"] += 1
                return _real(y)

            chart._to_grid = counted            # type: ignore[method-assign]
            prof = chart.reconstruct(theta)
            assert prof.shape == (chart.N,)
            assert calls["n"] == 1, (
                f"{chart.label()}.reconstruct called the shared operator "
                f"{calls['n']} times; it must be exactly once")

    def test_the_two_charts_declare_different_abscissae(self, solver):
        """The difference that used to be implicit is now an attribute."""
        _, x_si = solver
        assert ChartG(4, x_si).abscissa == "physical"
        assert ChartL(4, x_si).abscissa == "index"
        assert ChartJ(4, x_si).abscissa == "physical"


# ===========================================================================
# 2. The vector carries its chart
# ===========================================================================

class TestTheVectorCarriesItsChart:

    def test_a_bare_parameter_vector_raises(self, solver):
        sg, _ = solver
        with pytest.raises(DopingChartError, match="CHART-01"):
            sg.solve(np.full(16, -1e22), 0.3)

    @pytest.mark.parametrize("d", [4, 8, 9, 16, 128, 300, 302])
    def test_it_raises_at_every_wrong_length(self, solver, d):
        sg, _ = solver
        with pytest.raises(DopingChartError):
            sg.solve(np.full(d, -1e22), 0.0)

    def test_a_grid_valued_array_still_goes_through(self, solver):
        sg, x_si = solver
        C = np.where(x_si < 0.5e-6, -1e22, 1e22)
        st = sg.solve(C, 0.3)
        assert st.converged and np.isfinite(st.terminal_current)

    def test_a_charted_vector_goes_through_and_agrees(self, solver):
        """The two admissible spellings must give bit-identical currents."""
        sg, x_si = solver
        L = ChartL(16, x_si)
        theta = np.full(16, 22.0)
        a = sg.solve(L.charted(theta), 0.3)
        b = sg.solve(anchor_signed_to_grid(L.signed_anchors(theta), 301), 0.3)
        assert a.terminal_current == b.terminal_current

    def test_solver_input_returns_something_that_carries_the_chart(self, solver):
        _, x_si = solver
        L = ChartL(16, x_si)
        cd = L.solver_input(np.full(16, 22.0))
        assert isinstance(cd, ChartedDoping)
        assert cd.chart is L
        assert cd.label() == "L(d=16)"

    def test_a_chart_built_on_the_wrong_grid_is_caught(self, solver):
        """A chart is only meaningful against the grid it was built on."""
        sg, _ = solver
        other = np.linspace(0.0, 1e-6, 201)
        with pytest.raises(DopingChartError, match="different grid"):
            sg.solve(ChartG(4, other).charted(np.full(4, 22.0)), 0.0)


# ===========================================================================
# 3. No second path can be introduced
# ===========================================================================

#: Every interpolation call reachable under ``src/`` and ``scripts/``, with the
#: reason it is not a doping-to-solver-grid reconstruction. Counts are exact:
#: adding a second call to an already-listed file fails this guard too, so the
#: allowlist cannot be used as a blanket exemption for a whole module.
INTERPOLATION_ALLOWLIST = {
    "src/bayespinn_inv/inverse/charts.py": (
        5, "THE reconstruction operator, plus the anchor-to-anchor collocations "
           "that project between charts. This is the one module allowed to hold "
           "one."),
    "src/bayespinn_inv/solvers/scharfetter_gummel.py": (
        1, "Grid1D's non-uniform grid constructor: it interpolates a node "
           "*position* CDF, not a doping value."),
    "src/bayespinn_inv/data/datasets.py": (
        1, "grid -> anchors, the inverse direction: sampling a known profile "
           "down onto anchors is not reconstructing one up onto the grid."),
    "src/bayespinn_inv/benchmarks/sg_vs_pinn.py": (
        3, "interpolates phi, n and p onto a common comparison abscissa. Not "
           "doping, and never fed to a solver."),
    "src/bayespinn_inv/pinn/forward_pinn.py": (
        1, "evaluates doping at the PINN's own collocation points, which is a "
           "different object from the SG grid and a different solver."),
    "scripts/run_chart_reconciliation_g7.py": (
        3, "g7: anchor-to-anchor collocation between two charts' anchor "
           "lattices; the grid is reached through the chart objects."),
    "scripts/run_g8.py": (
        6, "g8: anchor-to-anchor collocation of the operating point between "
           "chart dimensions; the grid is reached through the chart objects."),
    "scripts/run_g9.py": (
        3, "g9: the same anchor-to-anchor collocation, at each of the further "
           "operating points -- chart G d=4 coordinates onto the d=15 and d=16 "
           "anchor lattices. Every one of the three lands on an anchor vector "
           "that is then handed to a Chart, so the solver grid is still reached "
           "only through charts._lerp."),
    "scripts/run_g10.py": (
        1, "g10: the same anchor-to-anchor collocation as g9, once -- chart G "
           "d=4 coordinates onto the d=16 anchor lattice, at each device whose "
           "singular vectors SPEC-g10-1 localises. It lands on an anchor "
           "vector that is then handed to a Chart, so the solver grid is still "
           "reached only through charts._lerp."),
    "scripts/run_mech01_rows.py": (
        2, "g12: the same anchor-to-anchor collocation as g9 and g10 -- chart "
           "G d=4 coordinates onto the d=16 anchor lattice, once per device "
           "for MECH-01's row-side measurement. Verified rather than asserted: "
           "both calls produce `m16`, which is only ever passed to "
           "run_g9.cell_spectrum as a chart-relative theta, and this module "
           "contains no .charted, no .reconstruct and no solver call, so the "
           "grid is still reached only through charts._lerp."),
    "scripts/run_mech01_pass3.py": (
        2, "g13: the same anchor-to-anchor collocation as g9, g10 and g12 -- "
           "chart G d=4 coordinates onto the d=16 anchor lattice, once in "
           "phase_pilot and once in phase_measure for MECH-01 pass 3. "
           "Verified rather than asserted: both calls produce `m16`, which is "
           "only ever passed to run_g9.cell_spectrum as a chart-relative "
           "theta, and this module contains no .charted, no .reconstruct and "
           "no solver call of its own, so the grid is still reached only "
           "through charts._lerp."),
    "scripts/defect_case_study.py": (
        1, "grid -> anchors for the L2 comparison against the recovery."),
    "scripts/run_inverse_sweep.py": (
        2, "grid -> anchors for the L2 comparison against the recovery."),
    "scripts/run_demo.py": (
        2, "grid -> anchors for plotting and for the recovery comparison."),
    "scripts/run_pinn_vs_surrogate.py": (
        1, "down-samples a profile to the PINN's anchor count; the PINN is not "
           "the SG solver and has its own input contract."),
    "scripts/validate_sg_supervised.py": (
        1, "anchors -> PINN collocation points, not the SG grid."),
}


def _interpolation_calls(tree: ast.AST) -> int:
    """Count interpolation calls in an AST. Prose is not in an AST (``SW-20``)."""
    n = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (
            fn.id if isinstance(fn, ast.Name) else None)
        if name in ("interp", "interp1d"):
            n += 1
    return n


def scan(paths):
    """``{relpath: count}`` for every file with at least one interpolation call."""
    found = {}
    for p in paths:
        try:
            tree = ast.parse(Path(p).read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        n = _interpolation_calls(tree)
        if n:
            found[str(Path(p)).replace("\\", "/")] = n
    return found


def _tree_paths():
    out = []
    for base in ("src", "scripts"):
        out.extend(sorted((ROOT / base).rglob("*.py")))
    return out


class TestNoSecondPathCanBeIntroduced:

    def test_the_scan_scope_excludes_this_module(self):
        """``SW-20``: assert the exclusion, do not trust it."""
        paths = {str(p) for p in _tree_paths()}
        assert str(Path(__file__).resolve()) not in paths
        assert not any(Path(p).name.startswith("test_") for p in paths)

    def test_no_unlisted_interpolation_reaches_the_grid(self):
        rel = {}
        for p in _tree_paths():
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            n = _interpolation_calls(tree)
            if n:
                rel[str(p.relative_to(ROOT)).replace("\\", "/")] = n

        unlisted = {k: v for k, v in rel.items()
                    if k not in INTERPOLATION_ALLOWLIST}
        assert not unlisted, (
            "a new interpolation call appeared in "
            f"{sorted(unlisted)}. If it reconstructs doping onto the solver "
            "grid it is a second reconstruction path and CHART-01 has "
            "recurred: call bayespinn_inv.inverse.charts instead. If it does "
            "something else, add it to INTERPOLATION_ALLOWLIST with the reason.")

        moved = {k: (rel[k], INTERPOLATION_ALLOWLIST[k][0])
                 for k in rel if rel[k] != INTERPOLATION_ALLOWLIST[k][0]}
        assert not moved, (
            f"interpolation-call counts changed: {moved}. The allowlist is per "
            "call, not per file, so a new call in an already-listed module "
            "fails here too. Say what the new one does.")

        gone = {k for k in INTERPOLATION_ALLOWLIST if k not in rel}
        assert not gone, (
            f"{sorted(gone)} no longer contains the interpolation the allowlist "
            "excuses. Delete the entry -- a stale exemption is a hole.")

    def test_every_allowlist_entry_states_a_reason(self):
        for path, (count, reason) in INTERPOLATION_ALLOWLIST.items():
            assert count >= 1, path
            assert len(reason) > 40, (
                f"{path}: an exemption without a reason is an exemption nobody "
                "can review")

    def test_the_guard_catches_a_planted_violation(self, tmp_path):
        """Positive control: the scan must fire on a real second path."""
        planted = tmp_path / "planted_second_reconstruction.py"
        planted.write_text(
            "import numpy as np\n"
            "def reconstruct(doping_si, grid_N):\n"
            "    x_in = np.linspace(0.0, 1.0, doping_si.shape[0])\n"
            "    x_grid = np.linspace(0.0, 1.0, grid_N)\n"
            "    return np.interp(x_grid, x_in, doping_si)\n",
            encoding="utf-8", newline="\n")
        assert scan([planted]) == {str(planted).replace("\\", "/"): 1}

    def test_the_guard_does_not_fire_on_prose_describing_it(self, tmp_path):
        """Negative control: a description of the forbidden call is not the call.

        This is the failure that made four generation-6 guards useless -- a
        character scan cannot tell code from prose about code, and the guard that
        searched for ``def bernoulli`` matched its own pattern literal forever.
        An AST walk can, because prose is not in the AST.
        """
        prose = tmp_path / "prose_about_the_rule.py"
        prose.write_text(
            '"""Do not write this:\n'
            '\n'
            '    x_grid = np.linspace(0.0, 1.0, self.grid.N)\n'
            '    doping_si = np.interp(x_grid, x_in, doping_si)\n'
            '\n'
            'That call chooses a parameterisation chart from an array length.\n'
            '"""\n'
            'FORBIDDEN = "np.interp(x_grid, x_in, doping_si)"\n'
            'ALSO_FORBIDDEN = "scipy.interpolate.interp1d(x, y)"\n',
            encoding="utf-8", newline="\n")
        assert scan([prose]) == {}
        assert "np.interp" in prose.read_text(encoding="utf-8")

    def test_the_solver_holds_no_doping_interpolation_at_all(self):
        """The specific line that was deleted, asserted gone from its file."""
        src = (ROOT / "src/bayespinn_inv/solvers/scharfetter_gummel.py")
        tree = ast.parse(src.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name in ("solve", "_doping_on_grid"):
                assert _interpolation_calls(node) == 0, (
                    f"{node.name} interpolates again; the resampler is back")
