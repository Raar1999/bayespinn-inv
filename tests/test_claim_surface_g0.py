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
