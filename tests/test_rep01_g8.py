"""``REP-01``: a representation error is not a number until it names its method.

The defect that forced the rule
-------------------------------
The generation-7 ruling opened with a headline -- *"the published local analysis
was conducted in a chart blind to the degeneracy"* -- built on a single figure:
witness member b embeds into chart L at **146% of the instrument floor**. That
figure was correct. It was a **collocation** error, and collocation is the naive
embedding, not the best one. Under least-squares projection followed by
refinement in observation space the same member reaches **2.2%** of the floor.

A factor of **67**, on the same object, from a choice of method that the number
did not carry. The headline was withdrawn in full.

The rule, as enacted at generation 8 §1
----------------------------------------
    Every representation, embedding, projection, or approximation error states
    the method that produced it, in the same table cell or sentence as the
    value. Where more than one method is admissible, the reported value is the
    best admissible one, and the ordering is pinned by test.

Both halves are guarded here.

``TestEveryReportedErrorNamesItsMethod``
    sweeps the committed measurement artefacts and fails on any record that
    reports a representation-shaped error without a method in the *same JSON
    object*. Not in the enclosing document, not in the file's prose -- the same
    object, which is the machine-readable form of "the same table cell".
``TestTheBestAdmissibleMethodIsTheOneReported``
    the ordering, generalised from
    ``test_projection_is_at_least_as_good_as_collocation``: wherever an artefact
    reports several admissible methods for one object, the one it calls best must
    actually be the best.

``SW-20``: the subject here is a JSON record rather than source code, so there is
no AST to walk, but the two controls the rule requires are implemented --
:meth:`test_the_guard_catches_a_planted_violation` and
:meth:`test_the_guard_does_not_fire_on_prose_describing_the_rule`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: A key whose value is a representation, embedding, projection or approximation
#: error. Substring match on the key name, which is deliberately broad: the cost
#: of a false positive is one line naming a method, and the cost of a false
#: negative is a withdrawn headline.
ERROR_KEY_MARKERS = (
    "representation_error",
    "profile_max_decades",
    "profile_rms_decades",
    "max_decades",
    "rms_decades",
    "profile_distance_from_operating_point_decades",
    "standin_error",
    "approximation_error",
)

#: What counts as naming the method, in the same object.
METHOD_MARKERS = ("method", "diagnostics", "projection", "how_produced")

#: Objects that carry an error-shaped key for a reason that is not a choice of
#: projection, with the reason. Same discipline as the interpolation allowlist in
#: ``tests/test_one_reconstruction_g8.py``: named, reasoned, and narrow.
CONTEXT_EXEMPTIONS: dict = {}

#: ``REP-01`` was enacted at generation 8. Generation 7's artefacts predate it and
#: two of them violate it, which the guard found on its first run. Under ``R-4``
#: a committed artefact is not rewritten -- it is what was measured -- so the
#: remedy is the DOC-07 remedy: name every pre-enactment violation here together
#: with the method that actually produced it, read out of the code that ran, and
#: assert the set exactly. Exactly, so that the list is a *guard* on the old
#: artefacts and not an amnesty for them: a new violation in a g7 file fails here,
#: and so does silently fixing one.
#:
#: The methods below are read from ``scripts/run_chart_reconciliation_g7.py``,
#: which is committed at 3e05c9d and is what produced these files.
PRE_ENACTMENT_VIOLATIONS = {
    "outputs/chart_reconciliation_g7/containment.json": {
        "records": [
            ("G_into_G", ["max_decades", "rms_decades"]),
            ("G_into_L", ["max_decades", "rms_decades"]),
            ("L_into_G_step_asymmetric", ["max_decades", "rms_decades"]),
            ("L_into_G_prior_draw", ["max_decades", "rms_decades"]),
        ],
        "method_that_produced_them": (
            "collocation: charts.containment() sets the target chart's "
            "coordinates by np.interp of the source chart's log10 magnitudes "
            "onto the target's anchors (charts.py, `theta_b = np.interp("
            "chart_b.anchors, chart_a.anchors, log10_mag)`). Collocation is "
            "exact at the anchors and is NOT the best admissible embedding -- "
            "the same distinction that cost the g7 headline. These four numbers "
            "are therefore upper bounds on the representation error, not the "
            "representation error, and any document that quotes them has to "
            "say so. Generation 8 does not quote them."),
    },
    "outputs/chart_reconciliation_g7/spectra.json": {
        "records": [
            ("cells.G_d4", ["profile_distance_from_operating_point_decades"]),
            ("cells.G_d16", ["profile_distance_from_operating_point_decades"]),
            ("cells.L_d16", ["profile_distance_from_operating_point_decades"]),
            ("cells.L_d4", ["profile_distance_from_operating_point_decades"]),
        ],
        "method_that_produced_them": (
            "run_chart_reconciliation_g7.py::phase_spectra.theta_for(). Chart G "
            "cells: exact -- the operating point is a chart-G object, distance "
            "0. Chart L d=16: the phase-2 `observational_refine` stand-in "
            "(Nelder-Mead on the oracle, budget 800, seeded from the best "
            "analytic projection), distance 1.2387 dec. Chart L d=4: "
            "`project_into_chart(..., method='log10')`, least squares in "
            "log10|C| with a soft_l1 loss at f_scale 0.05, distance 1.7856 dec. "
            "Two different methods in one table column, and the artefact does "
            "not say which cell used which. That is the defect REP-01 names."),
    },
    "outputs/chart_reconciliation_g7/manifest.json": {
        "records": [
            ("results.containment.G_into_G", ["max_decades", "rms_decades"]),
            ("results.containment.G_into_L", ["max_decades", "rms_decades"]),
            ("results.containment.L_into_G_step_asymmetric",
             ["max_decades", "rms_decades"]),
            ("results.containment.L_into_G_prior_draw",
             ["max_decades", "rms_decades"]),
            ("results.spectra.cells.G_d4",
             ["profile_distance_from_operating_point_decades"]),
            ("results.spectra.cells.G_d16",
             ["profile_distance_from_operating_point_decades"]),
            ("results.spectra.cells.L_d16",
             ["profile_distance_from_operating_point_decades"]),
            ("results.spectra.cells.L_d4",
             ["profile_distance_from_operating_point_decades"]),
        ],
        "method_that_produced_them": (
            "The manifest embeds a copy of every phase result, so it inherits "
            "both sets above verbatim -- four collocation residuals from "
            "charts.containment() and four operating-point distances produced by "
            "three different methods across the four cells. Same numbers, same "
            "omission, one more place it has to be corrected forward rather than "
            "rewritten (R-4)."),
    },
}


def _is_error_key(key: str) -> bool:
    return any(m in key for m in ERROR_KEY_MARKERS)


def _names_a_method(obj: dict) -> bool:
    return any(any(m in k for m in METHOD_MARKERS) for k in obj)


def scan_record(obj, path="", exempt=()):
    """Every object that reports an error without naming a method, with its path."""
    bad = []
    if isinstance(obj, dict):
        keys = [k for k in obj if _is_error_key(k)]
        if (keys and not _names_a_method(obj)
                and not any(e in path for e in exempt)):
            bad.append((path or "<root>", sorted(keys)))
        for k, v in obj.items():
            bad.extend(scan_record(v, f"{path}.{k}" if path else k, exempt))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad.extend(scan_record(v, f"{path}[{i}]", exempt))
    return bad


def _artefacts():
    """Committed measurement artefacts. Uncommitted runs are not evidence."""
    out = []
    for d in ("outputs/chart_reconciliation_g7", "outputs/g8"):
        p = ROOT / d
        if p.is_dir():
            out.extend(sorted(p.glob("*.json")))
    return out


def _artefact_names():
    return [str(p.relative_to(ROOT)).replace("\\", "/") for p in _artefacts()]


class TestEveryReportedErrorNamesItsMethod:

    def test_there_are_artefacts_to_check(self):
        """A sweep over nothing passes trivially, so say how much it swept."""
        found = _artefacts()
        assert len(found) >= 6, (
            f"only {len(found)} artefacts found; this guard is vacuous")

    @pytest.mark.parametrize("rel", sorted(_artefact_names()))
    def test_artefact(self, rel):
        path = ROOT / rel
        doc = json.loads(path.read_text(encoding="utf-8"))
        bad = scan_record(doc, exempt=tuple(CONTEXT_EXEMPTIONS))
        known = PRE_ENACTMENT_VIOLATIONS.get(rel)
        if known is not None:
            expected = [(p, list(k)) for p, k in known["records"]]
            assert sorted(bad) == sorted(expected), (
                f"{rel}: the set of pre-REP-01 violations changed.\n"
                f"  now      {sorted(bad)}\n  recorded {sorted(expected)}\n"
                "This list is a guard, not an amnesty: a new violation in a "
                "generation-7 artefact fails here, and so does quietly "
                "repairing one (R-4 -- the artefact records what was measured).")
            assert len(known["method_that_produced_them"]) > 120
            return
        assert not bad, (
            f"{rel}: {len(bad)} record(s) report a representation error "
            f"without naming the method that produced it, e.g. {bad[:3]}. "
            "REP-01: collocation and least-squares projection differ by a "
            "factor of 67 on the same object, so a value without its method is "
            "not a value. Put the method in the same object, or add the record "
            "to CONTEXT_EXEMPTIONS with the reason it is not a projection.")

    def test_no_generation_8_artefact_violates_the_rule(self):
        """The surface the rule actually binds: everything written after it.

        Split out from the sweep so it cannot be satisfied by an empty ``outputs/
        g8``: the count is asserted.
        """
        g8 = sorted((ROOT / "outputs/g8").glob("*.json")) \
            if (ROOT / "outputs/g8").is_dir() else []
        if not g8:
            pytest.skip("outputs/g8 not present in this checkout")
        assert len(g8) >= 6, f"only {len(g8)} g8 artefacts; sweep is thin"
        for path in g8:
            doc = json.loads(path.read_text(encoding="utf-8"))
            bad = scan_record(doc, exempt=tuple(CONTEXT_EXEMPTIONS))
            assert not bad, f"{path.name}: {bad[:3]}"

    def test_every_pre_enactment_violation_names_its_method(self):
        """The remedy R-4 leaves available: say what produced the number."""
        for rel, rec in PRE_ENACTMENT_VIOLATIONS.items():
            assert (ROOT / rel).is_file(), rel
            assert rec["records"], rel
            assert len(rec["method_that_produced_them"]) > 120, rel

    def test_every_exemption_states_a_reason(self):
        for key, reason in CONTEXT_EXEMPTIONS.items():
            assert len(reason) > 60, key

    def test_the_guard_catches_a_planted_violation(self):
        """Positive control: the g7 table row, stripped of its method."""
        planted = {"members": {"b": {"candidates": [
            {"observational_representation_error": 2.918e-02},
        ]}}}
        bad = scan_record(planted)
        assert bad == [("members.b.candidates[0]",
                        ["observational_representation_error"])]

    def test_the_guard_passes_the_same_record_with_its_method(self):
        ok = {"members": {"b": {"candidates": [
            {"method": "collocate",
             "observational_representation_error": 2.918e-02},
        ]}}}
        assert scan_record(ok) == []

    def test_the_guard_does_not_fire_on_prose_describing_the_rule(self):
        """Negative control: a description of the forbidden record is not one.

        ``SW-20``'s purpose, applied to JSON: a guard that cannot tell a record
        from a sentence about records will fire on its own documentation forever,
        and its authors will learn to ignore it.
        """
        prose = {
            "note": ("do not write a bare observational_representation_error: "
                     "collocation gives 2.918e-02 and refinement gives "
                     "4.338e-04, and a profile_max_decades with no method is "
                     "not a number"),
            "rule": "REP-01",
            "forbidden_key_names": ["observational_representation_error",
                                    "profile_max_decades"],
        }
        assert scan_record(prose) == []


class TestTheBestAdmissibleMethodIsTheOneReported:

    def test_the_g7_representation_table_reports_the_best_method(self):
        """The ordering the operator named, read off the artefact it came from."""
        path = ROOT / "outputs/chart_reconciliation_g7/representation.json"
        if not path.is_file():
            pytest.skip("g7 representation artefact not present")
        doc = json.loads(path.read_text(encoding="utf-8"))
        for member, rec in doc["members"].items():
            errs = {m: c["observational_representation_error"]
                    for m, c in rec["candidates"].items()}
            best = rec["best_method"]
            assert errs[best] == min(errs.values()), (
                f"member {member}: the artefact calls {best} best, but "
                f"{min(errs, key=errs.get)} is better. REP-01 requires the "
                "reported value to be the best admissible one.")
            assert errs[best] <= errs["collocate"], (
                f"member {member}: the reported embedding is worse than "
                "collocation, which is the naive one")

    def test_every_candidate_carries_its_own_method(self):
        path = ROOT / "outputs/chart_reconciliation_g7/representation.json"
        if not path.is_file():
            pytest.skip("g7 representation artefact not present")
        doc = json.loads(path.read_text(encoding="utf-8"))
        for rec in doc["members"].values():
            for name, cand in rec["candidates"].items():
                assert "method" in cand["diagnostics"], name
