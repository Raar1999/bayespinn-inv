"""``MECH-01`` pass 3: the analysis solves nothing, and the test was fixed first.

Two separable things are guarded here, and they fail for different reasons.

**The ``new_solves = 0`` guard, over the AST (``SW-20``).** The ruling of
2026-08-28 §5 required ``new_solves = 0`` *if the Jacobians exist*. They do not —
``outputs/g9`` stores singular values and never the left singular vectors — so
the held-out measurement has to solve, exactly as pass 2 had to. What that
leaves is a narrower and still worth-guarding claim: the **analysis** path solves
nothing. Phase ``insample`` and phase ``verdict`` are arithmetic over stored
``w_out``, and if a solver call ever appears beneath either of them, a number
that is supposed to be a re-reading of an artefact has quietly become a new
measurement.

The scan is transitive. A guard that only checked the entry points would be
defeated by one helper, which is the ``SW-20`` failure mode a level up.

**The pre-registration held.** The statistic, the admissibility rule, the
threshold and both outcomes were hashed before either held-out device was
touched. These tests re-derive the hashes from the module and compare them with
what the artefacts carry, so that editing the statistic after the fact is a test
failure rather than a silent re-write of what was promised.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_mech01_pass3.py"
MECHANISM = ROOT / "scripts" / "mech01_pass3_mechanism.py"
OUT = ROOT / "outputs" / "g13" / "mech01_pass3"

#: The calls that put a PDE solve or a Jacobian assembly on the path. Both are
#: imported from ``run_g9``; neither has any business under the analysis.
SOLVER_CALLS = frozenset({"build_solver", "cell_spectrum"})

#: The analysis entry points. Everything reachable from these must be arithmetic.
ANALYSIS_ENTRY = ("phase_insample", "phase_verdict")

#: The measurement path, where solving is the point. Named so that the guard is
#: shown to be discriminating rather than vacuous.
MEASURING_ENTRY = ("phase_measure", "phase_pilot", "_measure_cell")


def _module_functions(tree: ast.AST):
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _called_names(node: ast.AST):
    out = set()
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (
            fn.id if isinstance(fn, ast.Name) else None)
        if name:
            out.add(name)
    return out


def solver_reachable_from(tree: ast.AST, entry: str):
    """``[path]`` from ``entry`` to a solver call, or ``[]``. Transitive.

    Prose is not in an AST, so a docstring naming ``cell_spectrum`` is an
    :class:`ast.Constant` and cannot reach this. That is ``SW-20``'s mechanism
    and it is what the negative control below demonstrates.
    """
    funcs = _module_functions(tree)
    if entry not in funcs:
        return ["<missing: %s>" % entry]
    seen, stack = set(), [(entry, [entry])]
    while stack:
        name, path = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        for called in sorted(_called_names(funcs[name])):
            if called in SOLVER_CALLS:
                return [*path, called]
            if called in funcs:
                stack.append((called, [*path, called]))
    return []


@pytest.fixture(scope="module")
def tree():
    return ast.parse(SCRIPT.read_text(encoding="utf-8"))


class TestTheAnalysisSolvesNothing:

    @pytest.mark.parametrize("entry", ANALYSIS_ENTRY)
    def test_no_solver_is_reachable_from_the_analysis(self, tree, entry):
        path = solver_reachable_from(tree, entry)
        assert path == [], (
            "new_solves = 0 is violated: " + " -> ".join(path))

    @pytest.mark.parametrize("entry", MEASURING_ENTRY)
    def test_the_guard_is_not_vacuous(self, tree, entry):
        """The measurement path must trip the same scan.

        Without this, a scan that found nothing anywhere -- because the names
        were wrong, say -- would report the analysis clean and be believed.
        """
        assert solver_reachable_from(tree, entry) != [], (
            "%s should reach a solver; the scan is not detecting anything and "
            "the clean result above is worthless" % entry)

    def test_it_catches_a_planted_violation(self, tmp_path):
        """Positive control, and transitive: the solve is two hops down."""
        planted = tmp_path / "planted_solve_in_analysis.py"
        planted.write_text(
            "def _helper(x):\n"
            "    return cell_spectrum(x)\n"
            "def phase_verdict(out):\n"
            "    return _helper(out)\n",
            encoding="utf-8", newline="\n")
        got = solver_reachable_from(
            ast.parse(planted.read_text(encoding="utf-8")), "phase_verdict")
        assert got == ["phase_verdict", "_helper", "cell_spectrum"]

    def test_the_mechanism_module_solves_nothing_anywhere(self):
        """``scripts/mech01_pass3_mechanism.py`` is arithmetic end to end.

        It is scanned whole rather than from an entry point: it has no
        measuring path at all, so any solver call anywhere in it is a defect.
        That also closes the hole a per-entry-point scan would leave here --
        the module imports its helpers from ``run_mech01_pass3``, so a call
        graph built inside this file alone would not follow them.
        """
        tree = ast.parse(MECHANISM.read_text(encoding="utf-8"))
        hit = sorted(_called_names(tree) & SOLVER_CALLS)
        assert hit == [], "the mechanism description solves: %s" % hit

    def test_it_does_not_fire_on_prose_describing_it(self, tmp_path):
        """Negative control: naming the forbidden call is not calling it."""
        prose = tmp_path / "prose_about_solving.py"
        prose.write_text(
            '"""phase_verdict must never call cell_spectrum or build_solver.\n'
            'A call to cell_spectrum(sg, chart, theta) would be a new solve.\n'
            '"""\n'
            "FORBIDDEN = ('cell_spectrum', 'build_solver')\n"
            "def phase_verdict(out):\n"
            "    # cell_spectrum(out) would be wrong here\n"
            "    return sum(out)\n",
            encoding="utf-8", newline="\n")
        assert solver_reachable_from(
            ast.parse(prose.read_text(encoding="utf-8")), "phase_verdict") == []


class TestTheAdmissibilityRuleIsTheOnePreRegistered:

    def test_it_is_derived_from_the_null_not_from_the_data(self):
        """``n_out >= 2 and n_in >= 2`` -- both Beta shape parameters >= 1."""
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass3 import admissible
        assert not admissible(16, 1), "n_out = 1 has a degenerate null"
        assert not admissible(16, 15), "n_in = 1 has a degenerate null"
        assert not admissible(16, 0)
        assert not admissible(16, 16)
        assert admissible(16, 2)
        assert admissible(16, 14)
        assert admissible(16, 8)

    def test_it_excludes_exactly_the_degenerate_width_cell(self):
        """The ruling's degeneracy: at the narrowest width the core and the
        measurement window coincide and ``n_out = 1`` of 16."""
        doc = json.loads((OUT / "insample.json").read_text(encoding="utf-8"))
        for dname, rec in doc["devices"].items():
            dropped = [c["param"] for c in rec["width"] if not c["admissible"]]
            assert dropped == [0.1], (
                "%s: expected only the narrowest width excluded, got %s"
                % (dname, dropped))
            for c in rec["width"]:
                if c["param"] == 0.1:
                    assert c["n_out"] == 1


class TestThePreRegistrationHeld:

    def test_the_hashes_still_derive_from_the_module(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass3 import Pass3Measure, _hash_outcomes
        pre = json.loads((OUT / "preregister.json").read_text(encoding="utf-8"))
        assert pre["measure"]["measure_hash"] == Pass3Measure().measure_hash(), (
            "the statistic changed after it was pre-registered")
        assert pre["outcomes_hash"] == _hash_outcomes(), (
            "the outcomes changed after they were pre-registered")

    def test_the_verdict_carries_the_pre_registered_hashes(self):
        pre = json.loads((OUT / "preregister.json").read_text(encoding="utf-8"))
        ver = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
        assert ver["measure_hash"] == pre["measure"]["measure_hash"]
        assert ver["outcomes_hash"] == pre["outcomes_hash"]
        assert ver["hashes_match_preregistration"] is True

    def test_the_verdict_is_one_of_the_pre_registered_outcomes(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass3 import OUTCOMES
        ver = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
        assert ver["outcome"] in OUTCOMES
        assert ver["meaning"] == OUTCOMES[ver["outcome"]]

    def test_the_analysis_artefacts_record_new_solves_zero(self):
        for name in ("insample.json", "verdict.json"):
            doc = json.loads((OUT / name).read_text(encoding="utf-8"))
            assert doc["new_solves"] == 0, name


class TestOutOfSampleIsActuallyOutOfSample:

    def test_the_held_out_devices_were_never_measured_by_pass_2(self):
        """``AH-06``: the cells that suggested a statistic cannot test it."""
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass3 import DISCOVERY, HELD_OUT
        pass2 = json.loads(
            (ROOT / "outputs" / "g12" / "mech01_rows" / "rows.json")
            .read_text(encoding="utf-8"))
        assert set(pass2["devices"]) == set(DISCOVERY)
        assert not (set(HELD_OUT) & set(pass2["devices"])), (
            "a held-out device appears in the pass-2 measurement")

    def test_the_in_sample_reanalysis_is_not_claimed_as_evidence(self):
        doc = json.loads((OUT / "insample.json").read_text(encoding="utf-8"))
        assert doc["is_evidence"] is False

    def test_the_reproduction_control_pinned_the_held_out_jacobians(self):
        """``R1'``: the widest window IS generation 9's ``wide_0.15_0.90`` cell,
        so its singular values must reproduce ``op_points.json`` bit for bit."""
        held = json.loads((OUT / "heldout.json").read_text(encoding="utf-8"))
        r1 = held["reproduction_control_R1"]
        assert r1["of"] > 0, "the control had nothing to compare"
        assert r1["all_identical"], (
            "R1' failed at %d of %d: the Jacobian is not the object generation "
            "9 measured" % (r1["n_identical"], r1["of"]))
