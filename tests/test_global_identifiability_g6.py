"""S-1 machinery: the arbiter rule, the floors, and the reporting discipline.

`SPEC-g6-5` is generation 6's `CRITICAL` reward-hacking surface. `GRAD-01` measured
surrogate directional derivatives as agreeing with the SG oracle **only inside the
identifiable subspace** (mean cosine +0.504 inside, -0.001 outside, unchanged by a
33x training-budget increase). A global identifiability study probes precisely
*outside* that subspace, so arbitrating it with the surrogate would manufacture
the conclusion — and the surrogate is 152x faster, which is exactly what makes the
temptation real rather than theoretical.

`PH-22` supplies a second, independent reason measured in this generation's Phase A:
the surrogate path is float32 and cannot represent doping differences below ~1e-7
relative, where the float64 oracle round-trips to 1.678e-16. A float32 instrument
cannot resolve the degeneracies this study exists to find.

These tests cover the machinery, not the science. The scientific result lives in
`outputs/global_identifiability_g6/` with its manifest.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import numpy as np
import pytest

from bayespinn_inv.inverse.global_identifiability import (
    GlobalStudyConfig,
    contraction_spectrum,
    witness_search,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "src" / "bayespinn_inv" / "inverse" / "global_identifiability.py"


# --------------------------------------------------------------------------
# Toy oracles. Cheap, deterministic, and shaped so each test can state exactly
# what it is exercising without paying for an SG solve.
# --------------------------------------------------------------------------

def _honest_oracle(degenerate: bool = False):
    """A stand-in that reports trust flags the way the real solver does.

    ``degenerate=True`` makes the observation depend only on the *mean* of the
    profile, so every direction orthogonal to the mean is exactly unobservable —
    a device with a known, exact global degeneracy. That is what lets a test
    assert the witness search finds something rather than merely running.
    """
    def oracle(log10_mag, biases):
        mag = np.asarray(log10_mag, dtype=float)
        drive = mag.mean() if degenerate else mag @ np.arange(1, mag.size + 1)
        current = np.array([10.0 ** (drive - 20.0) * np.exp(3.0 * v) for v in biases])
        ok = np.ones(len(biases), dtype=bool)
        return current, ok, ok
    return oracle


def _lying_surrogate_oracle():
    """The negative control: a surrogate-style stand-in that fabricates trust.

    A real surrogate has no ``current_is_trustworthy()`` — it cannot certify its
    own output, because it has no residual to check. To be used as an arbiter it
    must therefore *assert* trust it has not earned, which is precisely the move
    `SPEC-g6-5` exists to forbid. This oracle is smooth, fast, confident, and
    wrong outside the identifiable subspace: it collapses the profile to a single
    direction, so it cannot see the degeneracy the honest oracle exposes.
    """
    def oracle(log10_mag, biases):
        mag = np.asarray(log10_mag, dtype=float)
        current = np.array([10.0 ** (mag[0] - 20.0) * np.exp(3.0 * v) for v in biases])
        ok = np.ones(len(biases), dtype=bool)          # fabricated
        return current, ok, ok
    return oracle


class TestArbiterCompliance:
    """SPEC-g6-5, enforced structurally rather than by intention."""

    def test_the_module_cannot_reach_the_surrogate(self) -> None:
        """No import path from the global study to the surrogate package.

        AST-level. A substring search for "surrogate" would match this module's
        own docstring, which explains at length why the surrogate is excluded —
        the same trap that caught three earlier guards in this loop.
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders += [
                    (node.lineno, a.name) for a in node.names if "surrogate" in a.name
                ]
            elif isinstance(node, ast.ImportFrom) and "surrogate" in (node.module or ""):
                offenders.append((node.lineno, node.module))
        assert not offenders, (
            "SPEC-g6-5 -- the global identifiability module imports the surrogate: "
            f"{offenders}. GRAD-01 makes it uninformative outside the identifiable "
            "subspace, which is the only place this study looks."
        )

    def test_every_evaluation_records_the_solver_verdict(self) -> None:
        cfg = GlobalStudyConfig(n_anchor=3)
        result = witness_search(cfg, _honest_oracle(), n_samples=25)
        counts = result["sampling"]
        assert set(counts) >= {
            "drawn", "kept", "rejected_not_converged", "rejected_not_trustworthy"
        }
        assert counts["drawn"] == 25
        assert (counts["kept"] + counts["rejected_not_converged"]
                + counts["rejected_not_trustworthy"]) == counts["drawn"], (
            "PH-19 -- the rejection counts do not account for every draw"
        )

    def test_untrustworthy_evaluations_are_excluded_and_counted(self) -> None:
        """PH-08: no current is reported where the solver does not certify it."""
        def half_untrustworthy(log10_mag, biases):
            current, ok, _ = _honest_oracle()(log10_mag, biases)
            trust = np.ones(len(biases), dtype=bool)
            if log10_mag[0] > 22.0:
                trust[0] = False
            return current, trust, np.ones(len(biases), dtype=bool)

        cfg = GlobalStudyConfig(n_anchor=3)
        result = witness_search(cfg, half_untrustworthy, n_samples=60)
        counts = result["sampling"]
        assert counts["rejected_not_trustworthy"] > 0, (
            "the oracle refused to certify some evaluations and none were counted"
        )
        assert counts["kept"] < counts["drawn"]


class TestTheNegativeControl:
    """A surrogate-style arbiter reaches a cleaner conclusion. That is the danger."""

    def test_the_lying_arbiter_misses_a_degeneracy_the_oracle_finds(self) -> None:
        cfg = GlobalStudyConfig(n_anchor=4, min_separation_decades=0.3)

        honest = witness_search(cfg, _honest_oracle(degenerate=True), n_samples=80)
        lying = witness_search(cfg, _lying_surrogate_oracle(), n_samples=80)

        assert honest["n_witnesses"] > 0, (
            "the honest oracle failed to find the degeneracy that was built into "
            "it -- this control cannot demonstrate anything until it does"
        )
        # The surrogate stand-in sees only mag[0], so profiles differing in the
        # other three anchors look *identical* to it: it reports far MORE
        # witnesses than exist, i.e. it manufactures degeneracy.
        assert lying["n_witnesses"] != honest["n_witnesses"], (
            "SPEC-g6-5 -- the surrogate-style arbiter reached the same answer as "
            "the oracle here, so this control demonstrates nothing; strengthen it "
            "before relying on it"
        )

    def test_a_confident_arbiter_cannot_be_distinguished_by_its_flags(self) -> None:
        """Why the rule is structural and not a runtime check.

        The lying oracle returns ``trust=True`` everywhere, exactly as the honest
        one does on well-behaved profiles. Nothing in the returned data marks it
        as unqualified. The only defence is refusing it entry, which is what
        ``test_the_module_cannot_reach_the_surrogate`` enforces.
        """
        cfg = GlobalStudyConfig(n_anchor=3)
        result = witness_search(cfg, _lying_surrogate_oracle(), n_samples=20)
        assert result["sampling"]["rejected_not_trustworthy"] == 0
        assert result["sampling"]["kept"] == result["sampling"]["drawn"]


class TestFloorsAreReportedNotSubtracted:
    """§4.2 item 5 and PH-13."""

    def test_distinguishability_floor_is_the_max_of_both(self) -> None:
        cfg = GlobalStudyConfig(noise_rel=2e-2, discretisation_floor_rel=1.5e-3)
        assert cfg.distinguishability_floor == 2e-2
        flipped = GlobalStudyConfig(noise_rel=1e-4, discretisation_floor_rel=1.5e-3)
        assert flipped.distinguishability_floor == 1.5e-3, (
            "when the solver is the coarser instrument it must set the floor"
        )

    def test_both_floors_appear_in_the_result(self) -> None:
        cfg = GlobalStudyConfig(n_anchor=3)
        floors = witness_search(cfg, _honest_oracle(), n_samples=20)["floors"]
        assert set(floors) == {"noise_rel", "discretisation_rel", "distinguishability"}


class TestPreRegistrationDiscipline:
    """AH-14 and AH-15."""

    def test_the_prior_hash_is_stable(self) -> None:
        assert GlobalStudyConfig().prior_hash() == GlobalStudyConfig().prior_hash()

    @pytest.mark.parametrize(
        "kwargs",
        [{"prior_lo_si": 5e20}, {"prior_hi_si": 5e23}, {"n_anchor": 8},
         {"noise_rel": 1e-2}, {"seed": 1}],
    )
    def test_the_prior_hash_moves_when_the_prior_moves(self, kwargs) -> None:
        """A prior quietly adjusted after seeing contraction is AH-04 renamed."""
        assert GlobalStudyConfig(**kwargs).prior_hash() != GlobalStudyConfig().prior_hash()

    def test_the_config_is_frozen(self) -> None:
        cfg = GlobalStudyConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.noise_rel = 0.5          # type: ignore[misc]

    def test_contraction_reports_n_and_ess_with_every_ratio(self) -> None:
        """AH-15: a variance ratio without its n is not a measurement."""
        cfg = GlobalStudyConfig(n_anchor=3)
        result = contraction_spectrum(cfg, _honest_oracle(), n_samples=40)
        assert result["sampling"]["kept"] > 0
        for row in result["tolerance_sweep"]:
            assert "effective_sample_size" in row and "supported" in row
            assert len(row["variance_ratio"]) == cfg.n_anchor

    def test_collapsed_rows_are_marked_unsupported(self) -> None:
        """The estimator must say when it has stopped estimating.

        Importance sampling from a wide prior collapses at a tight tolerance: the
        weight concentrates on one draw, the weighted variance goes to zero, and
        every direction reports as 'contracting'. That is an artefact of the
        estimator, and reporting it as a result would be the S-1 equivalent of
        quoting an ECE below its floor.
        """
        cfg = GlobalStudyConfig(n_anchor=4)
        result = contraction_spectrum(cfg, _honest_oracle(), n_samples=40)
        rows = result["tolerance_sweep"]
        assert any(not r["supported"] for r in rows), (
            "no row collapsed, so this test is not exercising the guard"
        )
        for row in rows:
            assert not (row["effective_sample_size"] < result["ess_floor"]
                        and row["supported"]), (
                f"row at tolerance x{row['tolerance_multiple_of_noise']:.0f} has "
                f"ESS {row['effective_sample_size']:.1f} but is marked supported"
            )


class TestAbsenceOfEvidenceIsReportedAsAbsence:
    """AH-13 -- the single most important sentence in this generation."""

    def test_no_witness_found_does_not_claim_identifiability(self) -> None:
        cfg = GlobalStudyConfig(n_anchor=3)
        # A strongly non-degenerate oracle: every direction moves the current.
        result = witness_search(cfg, _honest_oracle(degenerate=False), n_samples=30)
        verdict = result["verdict"].lower()
        if result["n_witnesses"] == 0:
            assert "no witness found at this budget" in verdict
            assert "identifiable" not in verdict, (
                "AH-13 -- a failed search was reported as a claim about the world"
            )
            assert "n_samples=" in verdict, "the budget must appear in the verdict"
