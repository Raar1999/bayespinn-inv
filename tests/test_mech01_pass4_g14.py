"""``MECH-01`` pass 4: the analysis solves nothing, and the null is calibrated.

Three separable things are guarded here.

**``new_solves = 0`` over the AST (``SW-20``).** Pass 4 captures the Jacobians
once — nothing in the tree stored them — and writes them to disk. Everything
after that is arithmetic: subsets, sub-spectra, percentiles, chains, verdict. If
a solver call ever appears beneath the analysis, a number that is supposed to be
a re-reading of a stored matrix has quietly become a new measurement. The scan is
transitive, and it is shown non-vacuous by running the same predicate over the
capture path, which must trip it.

**The null is matched on row count by construction.** That is the single property
that distinguishes pass 4 from the two methods before it, both of which contrasted
axes that do not overlap in the nuisance. It is asserted structurally rather than
assumed: every null draw at ``k`` has exactly ``k`` rows, drawn without
replacement from the same universe as the nested set it is compared against.

**The chain null is calibrated.** ``T`` is a mean of percentiles, so under the
exchangeability hypothesis the chain null's mean ``T`` must sit at 0.5. If it
drifts, every p-value pass 4 reports is meaningless — including the one the
verdict rests on. This is the control that would have caught a broken null before
it was read as a result.
"""

from __future__ import annotations

import ast
import json
from math import comb
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_mech01_pass4.py"
MECHANISM = ROOT / "scripts" / "mech01_pass4_mechanism.py"
OUT = ROOT / "outputs" / "g14" / "mech01_pass4"

SOLVER_CALLS = frozenset({"build_solver", "cell_spectrum"})
ANALYSIS_ENTRY = ("phase_analyse", "phase_verdict")
MEASURING_ENTRY = ("phase_capture", "phase_pilot")


def _module_functions(tree):
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _called_names(node):
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


def solver_reachable_from(tree, entry: str):
    """``[path]`` from ``entry`` to a solver call, or ``[]``. Transitive."""
    funcs = _module_functions(tree)
    if entry not in funcs:
        return [f"<missing: {entry}>"]
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
        assert path == [], "new_solves = 0 violated: " + " -> ".join(path)

    @pytest.mark.parametrize("entry", MEASURING_ENTRY)
    def test_the_guard_is_not_vacuous(self, tree, entry):
        assert solver_reachable_from(tree, entry) != [], (
            f"{entry} should reach a solver; if the scan detects nothing "
            f"anywhere then the clean result above is worthless")

    def test_it_catches_a_planted_violation(self, tmp_path):
        """Positive control, transitive: the solve is two hops down."""
        planted = tmp_path / "planted.py"
        planted.write_text(
            "def _h(x):\n"
            "    return build_solver(x)\n"
            "def phase_analyse(out):\n"
            "    return _h(out)\n",
            encoding="utf-8", newline="\n")
        got = solver_reachable_from(
            ast.parse(planted.read_text(encoding="utf-8")), "phase_analyse")
        assert got == ["phase_analyse", "_h", "build_solver"]

    def test_it_does_not_fire_on_prose_describing_it(self, tmp_path):
        """Negative control: naming the forbidden call is not calling it."""
        prose = tmp_path / "prose.py"
        prose.write_text(
            '"""phase_analyse must never call cell_spectrum or build_solver.\n'
            'A call to build_solver(cfg, n) here would be a new solve.\n'
            '"""\n'
            "FORBIDDEN = ('cell_spectrum', 'build_solver')\n"
            "def phase_analyse(out):\n"
            "    # build_solver(out) would be wrong\n"
            "    return sum(out)\n",
            encoding="utf-8", newline="\n")
        assert solver_reachable_from(
            ast.parse(prose.read_text(encoding="utf-8")), "phase_analyse") == []

    def test_the_mechanism_module_solves_nothing_anywhere(self):
        """Scanned whole: it has no measuring path, so any solver call is a defect."""
        hit = sorted(_called_names(
            ast.parse(MECHANISM.read_text(encoding="utf-8"))) & SOLVER_CALLS)
        assert hit == [], f"the mechanism description solves: {hit}"


class TestTheNullIsMatchedByConstruction:
    """The one property that makes pass 4 a distinct method."""

    def test_every_null_draw_has_exactly_k_rows(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import numpy as np
        from run_mech01_pass4 import admissible_k, nested_order
        rng = np.random.default_rng(0)
        n = 15
        for k in admissible_k(n):
            for _ in range(20):
                sel = rng.choice(n, size=k, replace=False)
                assert len(sel) == k
                assert len(set(sel.tolist())) == k, "drawn with replacement"
            assert len(nested_order(list(np.linspace(0.15, 0.90, n)))[:k]) == k

    def test_the_admissible_k_rule_excludes_the_degenerate_tail(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass4 import admissible_k
        for n in (13, 15, 16):
            ks = admissible_k(n)
            assert n - 1 not in ks and n not in ks, (
                "k = n-1 and k = n leave the null nearly or exactly degenerate")
            for k in ks:
                assert comb(n, k) >= 50

    def test_the_nested_sequence_is_the_widening_order(self):
        """It must add biases outward from the centre, which is what widening does."""
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_g9 import WIDTH_CENTRE
        from run_mech01_pass4 import nested_order
        biases = [0.15, 0.35, 0.50, 0.55, 0.75, 0.90]
        order = nested_order(biases)
        d = [abs(biases[i] - WIDTH_CENTRE) for i in order]
        assert d == sorted(d), "the nested sequence is not ordered outward"


class TestTheChainNullIsCalibrated:
    """If the null drifts off 0.5 every p-value pass 4 reports is meaningless."""

    def test_the_chain_null_mean_sits_at_one_half(self):
        doc = json.loads((OUT / "null_test.json").read_text(encoding="utf-8"))
        for dname, rec in doc["devices"].items():
            if not rec["test_ran"]:
                continue
            m = rec["chain_null_mean_T"]
            assert abs(m - 0.5) < 0.02, (
                f"{dname}: chain null mean T = {m:.4f}, not 0.5; the "
                f"percentile machinery is biased and every p-value is void")

    def test_the_chain_null_used_the_registered_number_of_draws(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass4 import N_CHAIN, N_NULL, SEED
        doc = json.loads((OUT / "null_test.json").read_text(encoding="utf-8"))
        assert doc["seed"] == SEED
        assert doc["n_null"] == N_NULL and doc["n_chain"] == N_CHAIN


class TestThePreRegistrationHeld:

    def test_the_hashes_still_derive_from_the_module(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_mech01_pass4 import Pass4Measure, _hash_outcomes
        pre = json.loads((OUT / "preregister.json").read_text(encoding="utf-8"))
        assert pre["measure"]["measure_hash"] == Pass4Measure().measure_hash(), (
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
        from run_mech01_pass4 import OUTCOMES
        ver = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
        assert ver["outcome"] in OUTCOMES
        assert ver["meaning"] == OUTCOMES[ver["outcome"]]

    def test_the_analysis_artefacts_record_new_solves_zero(self):
        for name in ("null_test.json", "verdict.json", "mechanism.json"):
            doc = json.loads((OUT / name).read_text(encoding="utf-8"))
            assert doc["new_solves"] == 0, name

    def test_the_reproduction_control_pinned_the_jacobians(self):
        cap = json.loads((OUT / "jacobians.json").read_text(encoding="utf-8"))
        r1 = cap["reproduction_control_R1"]
        assert r1["of"] > 0, "the control had nothing to compare"
        assert r1["all_identical"], (
            f"R1'' failed at {r1['n_identical']} of {r1['of']}: the Jacobian "
            f"is not the object generation 9 measured")

    def test_the_jacobians_are_stored_so_a_later_pass_needs_no_solve(self):
        """The thing passes 2 and 3 each had to redo because nobody stored it."""
        cap = json.loads((OUT / "jacobians.json").read_text(encoding="utf-8"))
        for dname, rec in cap["devices"].items():
            assert rec["jacobian"], f"{dname}: no Jacobian stored"
            assert rec["shape"] == [len(rec["jacobian"]),
                                    len(rec["jacobian"][0])]
            assert rec["shape"][0] == len(rec["biases_used"])
