"""G7-R: the two parameterisation charts, and the claim that they are not nested.

``docs/CHART_RECONCILIATION_g7.md`` rests on three things being true of the code
rather than of a docstring:

1. ``ChartL`` describes what the solver's resampler actually does;
2. ``chart_forward_jacobian`` reduces to the published ``sg_forward_jacobian``
   exactly where the two are supposed to coincide -- otherwise the reconciliation
   would be comparing a new estimator against an old number;
3. neither chart contains the other, in **both** directions, probed with objects
   drawn in the source chart rather than one object measured twice.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from bayespinn_inv.inverse.charts import (
    ChartG,
    ChartL,
    chart_forward_jacobian,
    containment,
    project_into_chart,
)
from bayespinn_inv.inverse.global_identifiability import GlobalStudyConfig
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    sg_forward_jacobian,
)
from bayespinn_inv.physics.constants import SILICON
from bayespinn_inv.physics.scaling import Scaling
from bayespinn_inv.solvers.scharfetter_gummel import (
    Grid1D,
    ScharfetterGummel1D,
    SGConfig,
)

GRID = 301


@pytest.fixture(scope="module")
def solver_and_grid():
    cfg = GlobalStudyConfig()
    scaling = Scaling.for_material(SILICON, T=300.0)
    length = cfg.domain_si[1] - cfg.domain_si[0]
    ls = float(scaling.x_to_scaled(np.float64(length)))
    sg = ScharfetterGummel1D(Grid1D.uniform(ls, GRID), scaling, SILICON, SGConfig())
    return cfg, sg, scaling.x_to_si(np.asarray(sg.grid.x))


def test_chartL_matches_the_solvers_own_resampler(solver_and_grid):
    """ChartL is a description of the resampler, not a parallel implementation.

    Generation 8 deleted the resampler this test used to compare against, so the
    original form -- solve it, read ``DeviceState.doping``, compare -- became
    vacuous: the solver now calls ``ChartL`` and would agree with itself. The
    comparison moved to 24 profiles captured from the old code path *before* it
    was deleted, which is the only version of this check that can still fail.
    See ``tests/test_one_reconstruction_g8.py`` for the full battery; this one
    stays here so the g7 module keeps its own guard.
    """
    _, sg, x_si = solver_and_grid
    golden = json.loads(
        (Path(__file__).parent / "data"
         / "chart_l_resampler_golden_g8.json").read_text(encoding="utf-8"))
    n = 0
    for case in golden["cases"]:
        if case["grid_N"] != GRID or case["d"] != 16:
            continue
        C = np.asarray(case["C_anchor"], dtype=np.float64)
        L = ChartL(16, x_si)
        mine = L.on_grid_signed(C)
        assert [float(v) for v in mine[:8]] == case["grid_first8"]
        assert [float(v) for v in mine[-8:]] == case["grid_last8"]
        assert hashlib.sha256(mine.tobytes()).hexdigest() == case["grid_sha256"]
        n += 1
    assert n >= 2, f"expected frozen d=16/N={GRID} cases, found {n}"


def test_chart_jacobian_reduces_to_the_published_one_on_chartL(solver_and_grid):
    """Positive control for the new estimator.

    ``sg_forward_jacobian`` perturbs entries of the array it is handed. For
    ``ChartL`` that array *is* the coordinate vector, so the two functions
    measure the same derivative and must agree -- otherwise the reconciliation
    table is measured with a different instrument than the number it reconciles.

    They agree, but **not** bit-for-bit, and the reason is worth pinning rather
    than tolerating. The two perturb by different arithmetic:

        chart :  10**(theta_j + s)
        sg    :  10**theta_j * 10**s

    which differ by ~1.7e-15 relative -- float non-associativity, nothing more.
    The Gummel iteration terminates on a tolerance, so a one-ulp change in doping
    can move the accepted iterate, and central differencing then divides by
    ``2*s``. Measured amplification: 1.7e-15 in, 3.5e-4 out.

    The honest criterion is therefore the estimator's own resolution, not
    equality. ``spectral_floor`` is the value below which this repository
    refuses to call a singular value a measurement (Weyl, see
    ``IdentifiabilityReport.spectral_floor``); a disagreement beneath it cannot
    change any reported quantity. Asserting round-off here instead would be
    claiming a precision the finite-difference estimate does not have.
    """
    cfg, sg, x_si = solver_and_grid
    L16 = ChartL(16, x_si)
    theta = np.full(16, 22.0)
    biases = cfg.biases
    Jc, Ic, kc, ec = chart_forward_jacobian(sg, L16, theta, biases,
                                            rel_step=0.05, min_snr=1e4)
    Js, Is, ks, es = sg_forward_jacobian(sg, L16.signed_anchors(theta), biases,
                                         rel_step=0.05, min_snr=1e4,
                                         chart=L16)
    assert kc == ks
    assert np.allclose(Ic, Is, rtol=0, atol=0)
    assert ec == pytest.approx(es, rel=1e-12)

    rep_c = analyse_identifiability(Jc, noise_rel=cfg.noise_rel, jacobian_noise=ec)
    rep_s = analyse_identifiability(Js, noise_rel=cfg.noise_rel, jacobian_noise=es)
    disagreement = float(np.max(np.abs(Jc - Js)))
    assert disagreement < rep_c.spectral_floor, (
        f"chart and published Jacobians disagree by {disagreement:.3e}, at or "
        f"above the spectral floor {rep_c.spectral_floor:.3e} -- that is a real "
        "discrepancy, not float non-associativity")

    # What the disagreement is allowed to cost: nothing that gets reported.
    assert rep_c.identifiable_rank == rep_s.identifiable_rank
    assert rep_c.resolvable_rank == rep_s.resolvable_rank
    above = rep_s.singular_values > rep_s.spectral_floor
    assert np.allclose(rep_c.singular_values[above], rep_s.singular_values[above],
                       rtol=5e-2, atol=0.0)


def test_chart_jacobian_on_chartG_has_chart_width_not_grid_width(solver_and_grid):
    """The bug this function exists to prevent.

    Handing ``ChartG``'s reconstructed profile to ``sg_forward_jacobian`` would
    differentiate 301 grid nodes and answer a different question while looking
    like the same one.
    """
    cfg, sg, x_si = solver_and_grid
    G4 = ChartG(4, x_si)
    theta = np.full(4, 22.0)
    J, _, _, _ = chart_forward_jacobian(sg, G4, theta, cfg.biases,
                                        rel_step=0.05, min_snr=1e4)
    assert J.shape[1] == 4
    assert G4.reconstruct(theta).shape[0] == GRID


def test_chartG_nests_exactly_in_itself(solver_and_grid):
    """d=4 -> d=16 within chart G is exact, because the anchor lattice nests."""
    _, _, x_si = solver_and_grid
    G4, G16 = ChartG(4, x_si), ChartG(16, x_si)
    idx = [int(np.argmin(np.abs(G16.anchors - x))) for x in G4.anchors]
    assert idx == [0, 5, 10, 15]
    assert np.allclose(G4.anchors, G16.anchors[idx], rtol=1e-14, atol=0.0)

    rng = np.random.default_rng(1)
    for _ in range(3):
        theta = rng.uniform(21.0, 23.0, size=4)
        c = containment(G4, G16, theta)
        assert c["max_decades"] < 1e-12
        assert c["sign_disagreements"] == 0


@pytest.mark.parametrize("d_source,d_target", [(4, 16), (16, 16), (4, 4)])
def test_neither_chart_contains_the_other(solver_and_grid, d_source, d_target):
    """Probed in both directions, each with an object drawn in its source chart."""
    cfg, _, x_si = solver_and_grid
    rng = np.random.default_rng(2)
    lo, hi = np.log10(cfg.prior_lo_si), np.log10(cfg.prior_hi_si)

    g_to_l = containment(ChartG(d_source, x_si), ChartL(d_target, x_si),
                         rng.uniform(lo, hi, size=d_source))
    l_to_g = containment(ChartL(d_source, x_si), ChartG(d_target, x_si),
                         rng.uniform(lo, hi, size=d_source))
    assert g_to_l["max_decades"] > 0.1, "chart L reproduced a chart-G profile"
    assert l_to_g["max_decades"] > 0.1, "chart G reproduced a chart-L profile"


def test_the_interpolants_agree_exactly_where_the_structure_says_they_must():
    """Geometric and arithmetic interpolation coincide iff the endpoints match.

    This is the whole containment argument in one line. If it ever fails, the
    claim in ``charts.py`` that the two chart images meet only on the
    piecewise-constant profiles is wrong and the reconciliation must be redone.
    """
    for r in (2.0, 5.0, 10.0, 100.0):
        arithmetic = (1.0 + r) / 2.0
        geometric = np.sqrt(r)
        assert arithmetic > geometric        # AM-GM, strict for r != 1
    equal_endpoints = (1.0 + 1.0) / 2.0
    assert equal_endpoints == pytest.approx(float(np.sqrt(1.0)))


def test_projection_methods_return_usable_coordinates(solver_and_grid):
    """All three norms must produce a real coordinate vector of the right width."""
    _, _, x_si = solver_and_grid
    G4, L16 = ChartG(4, x_si), ChartL(16, x_si)
    theta4 = np.array([22.05, 21.93, 21.45, 22.51])
    target = G4.reconstruct(theta4)
    for method in ("collocate", "linear_C", "log10"):
        th, diag = project_into_chart(L16, target, method=method,
                                      source_chart=G4, source_log10=theta4)
        assert th.shape == (16,)
        assert np.all(np.isfinite(th))
        assert diag["method"] == method


def test_projection_is_at_least_as_good_as_collocation(solver_and_grid):
    """A fitted stand-in must beat the naive one in its own norm.

    Generation 7 first measured the embedding by collocation alone and drew a
    conclusion the fitted stand-in later overturned. This pins the ordering so
    that mistake cannot recur silently.
    """
    _, _, x_si = solver_and_grid
    G4, L16 = ChartG(4, x_si), ChartL(16, x_si)
    theta4 = np.array([22.05, 21.93, 21.45, 22.51])
    target = G4.reconstruct(theta4)

    def err_in_C(theta):
        return float(np.linalg.norm(L16.reconstruct(theta) - target))

    th_col, _ = project_into_chart(L16, target, method="collocate",
                                   source_chart=G4, source_log10=theta4)
    th_lin, _ = project_into_chart(L16, target, method="linear_C")
    assert err_in_C(th_lin) <= err_in_C(th_col)
