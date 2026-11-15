"""Brightness change between seasons, on synthetic photometry with known truth and on the
shipped views of NASA's two variable test targets."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from galileo_blink.engine.looks import variability as V

from .synth import brightness_rows

PREBUILT = Path(__file__).resolve().parents[2] / "prebuilt"


def _steady_references(n=6, camera=1, noise=0.02, jitter=0.0, seed=100):
    """Ordinary stars in the same photos. `jitter` (ln units) moves each star's level at random
    from season to season, the way an imperfect calibration would."""
    stars = []
    for i in range(n):
        rng = np.random.default_rng(seed + i)
        levels = {s: float(np.exp(rng.normal(0.0, jitter))) if s else 1.0 for s in (0, 1, 2)}
        stars.append(brightness_rows(camera=camera, levels=levels, noise=noise, flux=5.0,
                                     snr=40.0, seed=seed + 50 + i))
    return stars


def _point(result, camera, season):
    return next(p for p in result["cameras"][str(camera)]["points"] if p["season"] == season)


def test_a_steady_star_is_unchanged_within_its_error():
    rows = brightness_rows(noise=0.03, slope=2.0, seed=1)
    r = V.measure_change(rows, _steady_references())
    assert r["changed"] is False and r["reason"] is None
    cam = r["cameras"]["1"]
    assert cam["floor_measured"] is True and cam["n_reference_stars"] == 6
    for p in cam["points"][1:]:
        assert abs(p["ratio"] - 1.0) < 3 * p["error"]
        assert p["changed"] is False
    assert r["best"]["changed"] is False and r["best"]["camera"] == 1


def test_a_star_that_brightens_by_half_is_recovered_and_marked_changed():
    rows = brightness_rows(levels={0: 1.0, 1: 1.0, 2: 1.5}, noise=0.03, slope=-1.0, seed=2)
    r = V.measure_change(rows, _steady_references())
    p1, p2 = _point(r, 1, 1), _point(r, 1, 2)
    assert abs(p2["ratio"] - 1.5) < 3 * p2["error"] and abs(p2["ratio"] - 1.5) < 0.1
    assert p2["changed"] is True and p1["changed"] is False
    assert r["changed"] is True
    assert r["best"] == dict(camera=1, first_season=0, last_season=2, ratio=p2["ratio"],
                             error=p2["error"], changed=True)


def test_a_sloped_spectrum_seen_at_different_wavelengths_is_not_a_change():
    # season 0 sees only the blue end, season 1 only the red end, season 2 the middle
    lams = {0: [0.75, 0.78, 0.81, 0.84, 0.87, 0.90], 1: [0.95, 0.98, 1.01, 1.04, 1.07, 1.10],
            2: [0.85, 0.88, 0.91, 0.94, 0.97, 1.0]}
    rows = brightness_rows(slope=3.0, noise=0.02, wavelengths=lams, seed=3)
    naive = (np.median([b["flux_mjy"] for b in rows if b["season"] == 1])
             / np.median([b["flux_mjy"] for b in rows if b["season"] == 0]))
    assert naive > 1.5                                      # comparing medians would cry "change"
    r = V.measure_change(rows, _steady_references())
    for p in r["cameras"]["1"]["points"][1:]:
        assert abs(p["ratio"] - 1.0) < 3 * p["error"] and p["changed"] is False
    assert r["changed"] is False


def test_a_saturated_star_says_so():
    rows = [dict(b, flux_mjy=None, snr=None, status="saturated")
            for b in brightness_rows(seed=4)]
    r = V.measure_change(rows)
    assert r == dict(cameras={}, best=None, changed=None, reason="saturated")


def test_one_season_says_so():
    r = V.measure_change(brightness_rows(levels={0: 1.0}, seed=5))
    assert r["cameras"] == {} and r["changed"] is None and r["reason"] == "one_season"


def test_negative_and_low_signal_photos_are_ignored():
    faint = brightness_rows(seed=6, snr=3.0)
    negative = [dict(b, flux_mjy=-abs(b["flux_mjy"]), snr=20.0) for b in brightness_rows(seed=7)]
    assert V.measure_change(faint + negative)["reason"] == "too_faint"
    good = brightness_rows(levels={0: 1.0, 1: 1.0, 2: 1.5}, seed=8)
    clean = V.measure_change(good)
    mixed = V.measure_change(good + faint + negative)
    assert mixed["cameras"] == clean["cameras"]


def test_the_floor_from_unsteady_reference_stars_widens_the_error():
    rows = brightness_rows(levels={0: 1.0, 1: 1.0, 2: 1.3}, noise=0.01, seed=9)
    calm = V.measure_change(rows, _steady_references(noise=0.01))
    shaky = V.measure_change(rows, _steady_references(noise=0.01, jitter=0.2))
    assert _point(calm, 1, 2)["changed"] is True
    assert shaky["cameras"]["1"]["floor"] > 0.1
    assert _point(shaky, 1, 2)["error"] > 3 * _point(calm, 1, 2)["error"]
    assert _point(shaky, 1, 2)["changed"] is False          # a marginal change no longer counts


def test_without_three_reference_stars_the_default_floor_is_used_and_said():
    rows = brightness_rows(seed=10)
    r = V.measure_change(rows, _steady_references(n=2))
    cam = r["cameras"]["1"]
    assert cam["floor"] == V.DEFAULT_FLOOR and cam["floor_measured"] is False
    assert cam["n_reference_stars"] == 2


def test_the_output_shape_is_what_the_interface_reads():
    rows = (brightness_rows(camera=2, levels={0: 1.0, 1: 2.0}, seed=11)
            + brightness_rows(camera=5, levels={1: 1.0, 2: 1.0}, seed=12))
    r = V.measure_change(rows)
    assert set(r) == {"cameras", "best", "changed", "reason"}
    assert set(r["cameras"]) == {"2", "5"}
    cam = r["cameras"]["2"]
    assert set(cam) == {"first_season", "points", "floor", "floor_measured",
                        "n_reference_stars", "scatter"}
    first, second = cam["points"]
    assert first == dict(season=0, ratio=1.0, error=0.0, n_photos=6)
    assert set(second) == {"season", "ratio", "error", "n_photos", "changed"}
    assert r["cameras"]["5"]["first_season"] == 1
    # the error is in ratio units: ratio x the error of ln(ratio)
    ln_error = math.hypot(V.DEFAULT_FLOOR, 0.0)
    assert second["error"] >= round(second["ratio"] * ln_error, 3) - 0.001
    json.dumps(r)                                          # plain JSON, no numpy types


def test_a_spot_with_no_catalogued_object_is_not_fitted():
    r = V.measure_change(brightness_rows(seed=13), subject_kind="spot")
    assert r == dict(cameras={}, best=None, changed=None, reason="no_subject")


@pytest.mark.parametrize("subject, refs", [
    ([], None), (None, None), ([{}], []), ([{"camera": "x", "season": None}], [[{}]]),
    ([dict(camera=1, season=0, wavelength=float("nan"), flux_mjy=float("inf"), snr=9,
           status="ok")] * 8, None),
    ("nonsense", "nonsense"), ([1, 2, 3], [[1], None]),
])
def test_odd_input_never_raises(subject, refs):
    r = V.measure_change(subject, refs)
    assert set(r) == {"cameras", "best", "changed", "reason"} and r["cameras"] == {}


def test_photos_at_one_wavelength_per_season_cannot_separate_colour_from_change():
    lams = {0: [0.8] * 6, 1: [1.0] * 6}
    r = V.measure_change(brightness_rows(levels={0: 1.0, 1: 1.0}, slope=2.0, wavelengths=lams,
                                         seed=14))
    assert r["cameras"] == {}                              # no guess


def test_the_view_build_writes_the_change_and_survives_a_failure(monkeypatch):
    from galileo_blink.engine.looks import build
    rows = brightness_rows(levels={0: 1.0, 1: 1.5}, seed=15)
    out = build.brightness_change_for_view(rows, _steady_references(), "target")
    assert out["changed"] is True and out["cameras"]["1"]["floor_measured"] is True

    def broken(*args, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(build.variability, "measure_change", broken)
    assert build.brightness_change_for_view(rows, [], "target") is None


def _shipped(target):
    return json.loads((PREBUILT / f"target-{target}" / "view.json").read_text())["brightness"]


def test_rw_aurigae_changed_and_r_draconis_cannot_be_measured():
    rw = V.measure_change(_shipped("rwaur"))
    assert rw["changed"] is True and rw["reason"] is None
    six = rw["cameras"]["6"]
    assert six["floor_measured"] is False
    last = six["points"][-1]
    assert last["changed"] is True and 0.4 < last["ratio"] < 0.6
    rdra = V.measure_change(_shipped("rdra"))
    assert rdra == dict(cameras={}, best=None, changed=None, reason="saturated")
