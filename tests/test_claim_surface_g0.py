"""Regression tests for AUDIT_g0 SCI-08.

The claim surface (README headline table, CLAIM_EVIDENCE_MATRIX, RELEASE_READINESS)
publishes solver-quality numbers together with the command that is said to produce
them. AUDIT_g0 measured those commands and found three published values that the
stated command cannot produce under any configuration:

===============================  ==============  =========================
claim                            published       measured 2026-08-25
===============================  ==============  =========================
built-in potential rel. error    2.8e-7          7.243e-14
mass action max|np - 1|          7.6e-6          2.93e-9
equilibration gain (off -> on)   1.32e-2         6.77e-3
                                 -> 7.62e-6      -> 9.73e-10
===============================  ==============  =========================

These tests fail on the pre-fix tree and pass once the documents quote what their
own commands measure. They deliberately re-measure rather than hard-coding the
2026-08-25 values, so they keep working as the solver improves: the contract under
test is *the documents agree with the code*, not *the code produces a fixed number*.

A factor-of-10 band is used throughout. Published values are quoted to two
significant figures, so anything inside 10x is a rounding or grid choice; anything
outside it is a stale number.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Tuple

import numpy as np
import pytest

from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Ratio by which a published value may differ from the measured one.
TOLERANCE_FACTOR = 10.0


def _read(relative: str) -> str:
    """Read a repository text file as UTF-8 (SW-05: never the platform encoding)."""
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _selftest_equilibrium() -> Tuple[float, float]:
    """Re-run the two physics checks that ``bayespinn selftest`` reports.

    Uses exactly the configuration of ``bayespinn_inv.cli.cmd_selftest``: a
    301-node uniform grid over a 1 um silicon PN junction at N_A = N_D = 1e22
    m^-3, solved at zero bias.

    Returns
    -------
    (v_bi_rel_err, mass_action_dev)
        ``v_bi_rel_err`` is dimensionless |V_bi - V_bi_exact| / V_bi_exact.
        ``mass_action_dev`` is dimensionless max|n*p/n_i^2 - 1| over all nodes.
    """
    scaling = Scaling.for_material(SILICON, T=300.0)
    length_scaled = float(scaling.x_to_scaled(np.float64(1e-6)))
    sg = ScharfetterGummel1D(
        Grid1D.uniform(length_scaled, 301), scaling, SILICON, SGConfig()
    )
    x = scaling.x_to_si(np.asarray(sg.grid.x))
    n_a = n_d = 1e22
    state = sg.solve(np.where(x < x.max() / 2, -n_a, n_d), 0.0)

    v_bi = float(state.phi[-1] - state.phi[0])
    v_bi_exact = scaling.V_T * math.log(n_a * n_d / SILICON.n_i ** 2)
    v_bi_rel_err = abs(v_bi - v_bi_exact) / v_bi_exact

    ratio = (state.n / scaling.n_star) * (state.p / scaling.n_star)
    return v_bi_rel_err, float(np.max(np.abs(ratio - 1.0)))


def _equilibration_pair() -> Tuple[float, float]:
    """Mass-action deviation with equilibration off and on, at the S1 configuration.

    Mirrors ``tests/test_sg_numerics.py::test_equilibration_beats_plain_spsolve``:
    201-node uniform grid, 1 um silicon PN junction, N_A = N_D = 1e22 m^-3.

    Returns
    -------
    (without_equilibration, with_equilibration)
        Both dimensionless max|n*p/n_i^2 - 1|.
    """
    scaling = Scaling.for_material(SILICON, T=300.0)
    length_scaled = float(scaling.x_to_scaled(np.float64(1e-6)))
    grid = Grid1D.uniform(length_scaled, 201)
    x = scaling.x_to_si(np.asarray(grid.x))
    doping = np.where(x < x.max() / 2, -1e22, 1e22)

    out = {}
    for equilibrate in (False, True):
        sg = ScharfetterGummel1D(
            grid, scaling, SILICON, SGConfig(equilibrate=equilibrate, max_outer=60)
        )
        state = sg.solve(doping, bias=0.0)
        ratio = (state.n / scaling.n_star) * (state.p / scaling.n_star)
        out[equilibrate] = float(np.max(np.abs(ratio - 1.0)))
    return out[False], out[True]


def _assert_agrees(published: float, measured: float, where: str, what: str) -> None:
    """Fail unless ``published`` is within ``TOLERANCE_FACTOR`` of ``measured``."""
    assert measured > 0.0, f"{what}: measured value is not positive ({measured})"
    ratio = max(published / measured, measured / published)
    assert ratio <= TOLERANCE_FACTOR, (
        f"AUDIT_g0 SCI-08 -- {where} publishes {what} = {published:.3g}, but the "
        f"command it cites measures {measured:.3g} (off by {ratio:.3g}x, tolerance "
        f"{TOLERANCE_FACTOR:g}x). Update the document to the measured value."
    )


def _extract(pattern: str, text: str, where: str) -> float:
    """Pull a single float out of ``text`` with ``pattern``; fail loudly if absent."""
    match = re.search(pattern, text)
    assert match is not None, (
        f"could not locate the claim in {where} with pattern {pattern!r} -- if the "
        "document was restructured, update this test to match its new shape"
    )
    return float(match.group(1))


class TestPublishedSolverQualityIsReproducible:
    """Every published solver-quality number must match its own stated command."""

    def test_readme_built_in_potential(self) -> None:
        published = _extract(
            r"\*\*Built-in potential\*\* vs analytic \| rel\. error \*\*([0-9.eE+-]+)\*\*",
            _read("README.md"),
            "README.md",
        )
        measured, _ = _selftest_equilibrium()
        _assert_agrees(
            published, measured, "README.md", "built-in potential rel. error"
        )

    def test_claim_matrix_built_in_potential(self) -> None:
        published = _extract(
            r"\| C17 \|[^|]*\|\s*rel\. error ([0-9.eE+-]+)\s*\|",
            _read("docs/CLAIM_EVIDENCE_MATRIX.md"),
            "docs/CLAIM_EVIDENCE_MATRIX.md C17",
        )
        measured, _ = _selftest_equilibrium()
        _assert_agrees(
            published,
            measured,
            "CLAIM_EVIDENCE_MATRIX C17",
            "built-in potential rel. error",
        )

    def test_claim_matrix_mass_action(self) -> None:
        text = _read("docs/CLAIM_EVIDENCE_MATRIX.md")
        row = _extract(
            r"\| C18 \|.*?= ([0-9.eE+-]+)\s*\|", text, "docs/CLAIM_EVIDENCE_MATRIX.md C18"
        )
        _, measured = _selftest_equilibrium()
        _assert_agrees(row, measured, "CLAIM_EVIDENCE_MATRIX C18", "mass action")

    def test_release_readiness_quotes_both(self) -> None:
        text = _read("docs/RELEASE_READINESS.md")
        v_bi_pub = _extract(
            r"V_bi vs analytic to ([0-9.eE+-]+) rel\.", text, "RELEASE_READINESS"
        )
        ma_pub = _extract(r"mass action ([0-9.eE+-]+)", text, "RELEASE_READINESS")
        v_bi_meas, ma_meas = _selftest_equilibrium()
        _assert_agrees(
            v_bi_pub, v_bi_meas, "RELEASE_READINESS", "built-in potential rel. error"
        )
        _assert_agrees(ma_pub, ma_meas, "RELEASE_READINESS", "mass action")

    @pytest.mark.parametrize("which", ["before", "after"])
    def test_claim_matrix_equilibration_gain(self, which: str) -> None:
        text = _read("docs/CLAIM_EVIDENCE_MATRIX.md")
        published_before = _extract(
            r"\| S1 \|[^|]*\|\s*([0-9.eE+-]+) → [0-9.eE+-]+",
            text,
            "docs/CLAIM_EVIDENCE_MATRIX.md S1",
        )
        published_after = _extract(
            r"\| S1 \|[^|]*\|\s*[0-9.eE+-]+ → ([0-9.eE+-]+)",
            text,
            "docs/CLAIM_EVIDENCE_MATRIX.md S1",
        )
        measured_before, measured_after = _equilibration_pair()
        if which == "before":
            _assert_agrees(
                published_before,
                measured_before,
                "CLAIM_EVIDENCE_MATRIX S1",
                "mass action without equilibration",
            )
        else:
            _assert_agrees(
                published_after,
                measured_after,
                "CLAIM_EVIDENCE_MATRIX S1",
                "mass action with equilibration",
            )


# ---------------------------------------------------------------------------
# AUDIT_g0 SCI-11 / PH-21 -- a local Jacobian rank is never reported as an
# identifiability result without the word "local".
# ---------------------------------------------------------------------------

#: Documents this loop is permitted to correct. `papers/**` is excluded here and
#: handled by :class:`TestParkedPapersInstance` below -- it is protected from
#: edits by operator ruling R-3, so its one unqualified passage is pinned rather
#: than fixed. Excluding it from this tuple narrows the guard's *reach*, never its
#: *strictness*: the papers instance is asserted on, not skipped.
CLAIM_SURFACE = (
    "README.md",
    "docs/RELEASE_READINESS.md",
    "docs/CLAIM_EVIDENCE_MATRIX.md",
)

#: A statement of the identifiable-rank result, e.g. "3-4 of 16 dof".
_RANK_CLAIM = re.compile(r"\d\s*(?:-|–|—)?\s*\d?\s*of\s*16\b")

#: How many lines either side count as the same passage.
_CONTEXT = 6


def _rank_claim_lines(text: str):
    """Yield (line_number, line) for every line asserting the rank result."""
    for i, line in enumerate(text.splitlines()):
        if _RANK_CLAIM.search(line):
            yield i, line


class TestIdentifiabilityIsLabelledLocal:
    """PH-21: the regime label travels with the number, in every document."""

    @pytest.mark.parametrize("document", CLAIM_SURFACE)
    def test_every_rank_claim_is_qualified(self, document: str) -> None:
        lines = _read(document).splitlines()
        unqualified = []
        for i, line in _rank_claim_lines("\n".join(lines)):
            lo = max(0, i - _CONTEXT)
            hi = min(len(lines), i + _CONTEXT + 1)
            if "local" not in "\n".join(lines[lo:hi]).lower():
                unqualified.append(f"{document}:{i + 1}: {line.strip()[:110]}")
        assert not unqualified, (
            "AUDIT_g0 SCI-11 / PH-21 -- identifiable-rank claims stated without a "
            "local/global label:\n  " + "\n  ".join(unqualified)
        )

    def test_the_guard_would_catch_a_regression(self) -> None:
        """A negative control: the checker must reject an unqualified passage.

        Without this, a bug that made `_RANK_CLAIM` match nothing would leave the
        test above passing vacuously on every document.
        """
        assert list(_rank_claim_lines("determines only 3-4 of 16 doping dof")), (
            "the rank-claim pattern matches nothing -- the guard above is vacuous"
        )
        lines = ["determines only 3-4 of 16 doping dof"]
        found = [
            i for i, _ in _rank_claim_lines("\n".join(lines))
            if "local" not in "\n".join(lines).lower()
        ]
        assert found == [0]


class TestParkedPapersInstance:
    """`papers/draft.md` carries one unqualified rank claim. It is parked, not fixed.

    Operator ruling R-3 makes `papers/**` reserved: this loop may not mutate it.
    AUDIT_g0 SCI-11 is therefore only partly closable, and the honest record is a
    pinned count rather than a silent exclusion.

    The document *does* label the result `local` three times (lines 23, 73 and an
    explicit limitation at 349), so a reader of the whole paper is not misled. The
    passage below is unqualified within its own paragraph, which is what PH-21
    addresses -- a reader quoting that sentence does not carry line 349 with it.

    This test fails in **both** directions on purpose:

    - if the count rises, a new unqualified claim entered the protected document;
    - if it falls to zero, the operator has released R-3 or fixed the passage, and
      `papers/draft.md` should be moved into ``CLAIM_SURFACE`` and this test deleted.
    """

    #: Pinned at generation 0. See docs/gen/DECISIONS.md DEC-g0-4.
    KNOWN_UNQUALIFIED = 1

    def _unqualified(self):
        lines = _read("papers/draft.md").splitlines()
        out = []
        for i, line in _rank_claim_lines("\n".join(lines)):
            lo = max(0, i - _CONTEXT)
            hi = min(len(lines), i + _CONTEXT + 1)
            if "local" not in "\n".join(lines[lo:hi]).lower():
                out.append((i + 1, line.strip()))
        return out

    def test_count_is_exactly_what_generation_0_measured(self) -> None:
        found = self._unqualified()
        assert len(found) == self.KNOWN_UNQUALIFIED, (
            f"papers/draft.md unqualified rank claims: expected "
            f"{self.KNOWN_UNQUALIFIED} (parked under R-3), found {len(found)}:\n  "
            + "\n  ".join(f"line {n}: {t[:110]}" for n, t in found)
        )

    def test_the_document_does_label_the_result_elsewhere(self) -> None:
        """The parked instance is a passage-level defect, not a missing caveat."""
        text = _read("papers/draft.md").lower()
        assert text.count("local") >= 3, (
            "papers/draft.md no longer labels the identifiability result as local "
            "anywhere -- this is now a document-level defect, not a parked passage"
        )
