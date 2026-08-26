"""``SPEC-g10-1``: the localisation verdict is computed, never asserted.

The clause requires *a stated localisation measure fixed before looking*, because
"the singular vectors localise" is the kind of claim that can be made true after
the fact by choosing the statistic. Two things therefore need guarding, and they
are different things:

``TestTheMeasureIsNotVacuous``
    the statistic separates a localised direction from a delocalised one, is
    invariant to the sign gauge a singular vector is only defined up to, and
    refuses to answer at all when it is handed coordinates whose positions it
    does not know. ``SW-20``'s two controls: planted extremes it must separate,
    and a rotation it must ignore.

``TestTheVerdictIsDerivedFromTheHashedCriterion``
    the artefact's ``supported`` flag is re-derived here from the numbers the
    artefact itself records and the thresholds in the pre-registration. A verdict
    a result document could restate more generously than the measurement is the
    failure mode; re-deriving it is the only check that catches it.

``TestReliabilityIsStamped``
    a right singular vector below the identifiable rank spans a near-null
    subspace, and its orientation inside that subspace is not determined by the
    data. Such vectors must be reported and stamped, never silently mixed with
    the ones that are measurements.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bayespinn_inv.inverse.charts import ChartG
from bayespinn_inv.inverse.identifiability import (
    analyse_identifiability,
    singular_vector_localisation,
)

REPO = Path(__file__).resolve().parents[1]
D = 16


def _positions(d: int = D) -> np.ndarray:
    return ChartG(d, np.linspace(0.0, 1e-6, 301)).anchors


def _leading(J: np.ndarray, rank: int = 1, **kw) -> dict:
    rep = analyse_identifiability(np.asarray(J, dtype=np.float64),
                                 noise_rel=0.02)
    return singular_vector_localisation(rep, _positions(J.shape[1]),
                                        n_vectors=1, rank=rank, **kw)["vectors"][0]


class TestTheMeasureIsNotVacuous:

    def test_a_planted_delta_direction_is_maximally_localised(self):
        """`SW-20` positive control: the extreme the statistic must recognise."""
        J = np.zeros((4, D))
        J[0, D // 2] = 1.0
        row = _leading(J)
        assert row["spread_fraction"] == pytest.approx(1.0 / D), (
            "a direction supported on one anchor must score 1/d; it scored "
            f"{row['spread_fraction']}")

    def test_a_planted_uniform_direction_is_maximally_delocalised(self):
        J = np.zeros((4, D))
        J[0, :] = 1.0 / np.sqrt(D)
        assert _leading(J)["spread_fraction"] == pytest.approx(1.0)

    def test_the_two_extremes_are_not_the_same_number(self):
        """A statistic that cannot separate the extremes measures nothing."""
        a = np.zeros((4, D))
        a[0, 0] = 1.0
        b = np.zeros((4, D))
        b[0, :] = 1.0 / np.sqrt(D)
        assert _leading(a)["spread_fraction"] < 0.5 * _leading(b)["spread_fraction"]

    def test_the_statistic_ignores_the_sign_gauge(self):
        """`SW-20` negative control: a singular vector's sign is not data."""
        J = np.zeros((4, D))
        J[0, 3:7] = np.array([0.4, 0.6, -0.5, 0.48])
        first = _leading(J)
        second = _leading(-J)
        assert first["spread_fraction"] == pytest.approx(
            second["spread_fraction"])
        assert first["centroid"] == pytest.approx(second["centroid"])

    def test_it_refuses_coordinates_whose_positions_are_unknown(self):
        """A spatial statistic over a coordinate with no position is not one."""
        rep = analyse_identifiability(np.eye(4, D), noise_rel=0.02)
        with pytest.raises(ValueError, match="one position per coordinate"):
            singular_vector_localisation(rep, _positions(4))

    def test_the_centroid_of_a_symmetric_direction_is_the_midpoint(self):
        J = np.zeros((4, D))
        J[0, 0] = J[0, -1] = 1.0 / np.sqrt(2.0)
        x = _positions()
        assert _leading(J)["centroid"] == pytest.approx(
            0.5 * (x[0] + x[-1]))

    def test_the_reference_distance_is_reported_only_when_asked(self):
        J = np.zeros((4, D))
        J[0, 2] = 1.0
        assert "reference_distance" not in _leading(J)
        x = _positions()
        mid = float(0.5 * (x.min() + x.max()))
        row = _leading(J, reference_position=mid)
        assert row["reference_distance"] == pytest.approx(abs(x[2] - mid))


class TestReliabilityIsStamped:

    def test_vectors_below_the_rank_are_labelled_unreliable(self):
        J = np.zeros((6, D))
        J[0, 0] = 1.0
        J[1, 1] = 1e-9                      # far below any sensible cutoff
        rep = analyse_identifiability(J, noise_rel=0.02)
        out = singular_vector_localisation(rep, _positions(), n_vectors=4,
                                           rank=1)
        assert out["vectors"][0]["reliable"] is True
        assert all(not v["reliable"] for v in out["vectors"][1:])
        assert all(v["why_unreliable"] for v in out["vectors"][1:])

    def test_the_rank_used_is_recorded(self):
        rep = analyse_identifiability(np.eye(6, D), noise_rel=0.02)
        out = singular_vector_localisation(rep, _positions(), n_vectors=2,
                                           rank=3)
        assert out["rank_used_for_reliability"] == 3


class TestTheVerdictIsDerivedFromTheHashedCriterion:
    """Re-derive the artefact's own verdict from the artefact's own numbers."""

    @staticmethod
    def _artefacts():
        loc = REPO / "outputs" / "g10" / "localisation.json"
        pre = REPO / "outputs" / "g10" / "preregister.json"
        if not (loc.is_file() and pre.is_file()):
            return None, None
        return (json.loads(loc.read_text(encoding="utf-8")),
                json.loads(pre.read_text(encoding="utf-8")))

    def test_the_measure_hash_on_disk_matches_the_pre_registration(self):
        loc, pre = self._artefacts()
        if loc is None:
            pytest.skip("outputs/g10/localisation.json not measured yet")
        assert (loc["measure"]["measure_hash"]
                == pre["localisation_measure"]["measure_hash"]), (
            "SPEC-g10-1 was measured against a criterion that is not the one "
            "registered before it ran")

    def test_each_device_verdict_follows_from_its_recorded_statistics(self):
        loc, pre = self._artefacts()
        if loc is None:
            pytest.skip("outputs/g10/localisation.json not measured yet")
        m = pre["localisation_measure"]
        for name, dev in loc["devices"].items():
            s = dev["summary"]
            width_ok = s["rho_width"] >= m["min_rho"]
            rng_a = s["range_over_spacing"]
            contrast_ok = bool(rng_a > 0 and
                               s["range_over_width"] / rng_a
                               >= m["min_range_ratio"])
            assert s["device_supports_hypothesis"] == (width_ok and contrast_ok), (
                f"{name}: the recorded verdict does not follow from the "
                f"recorded statistics under the registered thresholds")

    def test_the_overall_verdict_is_the_conjunction_over_devices(self):
        loc, _ = self._artefacts()
        if loc is None:
            pytest.skip("outputs/g10/localisation.json not measured yet")
        per = [d["summary"]["device_supports_hypothesis"]
               for d in loc["devices"].values()]
        assert loc["verdict"]["supported"] == bool(per and all(per))

    def test_the_curve_is_a_curve(self):
        loc, _ = self._artefacts()
        if loc is None:
            pytest.skip("outputs/g10/localisation.json not measured yet")
        for name, dev in loc["devices"].items():
            for axis in ("width_curve", "spacing_curve"):
                pts = [c for c in dev[axis] if "error" not in c]
                assert len(pts) >= 3, (
                    f"{name} {axis}: a 'curve' over {len(pts)} points is not one")

    def test_every_cell_carries_the_rank_it_stamped_reliability_with(self):
        loc, _ = self._artefacts()
        if loc is None:
            pytest.skip("outputs/g10/localisation.json not measured yet")
        for name, dev in loc["devices"].items():
            for axis in ("width_curve", "spacing_curve"):
                for cell in dev[axis]:
                    if "error" in cell:
                        continue
                    assert (cell["localisation"]["rank_used_for_reliability"]
                            == cell["rank_at_operational_cutoff"]), (
                        f"{name} {axis}: reliability was stamped with a rank "
                        "other than the cell's own")
