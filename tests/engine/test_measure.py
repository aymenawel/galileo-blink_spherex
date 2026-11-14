"""Position and brightness of a star in one photo."""
import math

import numpy as np

from galileo_blink.engine.image.measure import measure

from .synth import make_photo, offset_sky, star_image

HERE = (180.0, 0.0)


def _offset_error(m, east, north):
    return math.hypot(m.east - east, m.north - north)


def test_a_bright_star_is_found_where_it_is_not_where_it_was_expected():
    truth = (3.1, -2.2)                                    # arcsec from the expected place
    photo = make_photo(stars=[(*offset_sky(*HERE, *truth), 200.0)], noise=0.01)
    m = measure(photo, *HERE)
    assert m.status == "ok" and m.snr > 100
    assert _offset_error(m, *truth) < 0.15
    assert abs(m.flux - 200.0) / 200.0 < 0.03


def test_a_faint_star_is_not_pulled_onto_its_expected_position():
    errors = []
    for seed in range(30):
        photo = make_photo(stars=[(*offset_sky(*HERE, 3.0, 0.0), 0.32)], noise=0.02, seed=seed)
        m = measure(photo, *HERE)
        errors.append((m.east, m.snr))
    east = float(np.median([e for e, _ in errors]))
    assert 5 < np.median([s for _, s in errors]) < 12      # a faint detection
    assert abs(east - 3.0) < 0.45                          # recovered, not shrunk toward zero


def test_a_masked_peak_pixel_spoils_the_brightness_but_not_the_position():
    truth = (1.0, 0.5)
    star = offset_sky(*HERE, *truth)
    clean = make_photo(stars=[(*star, 200.0)])
    x, y = (int(round(float(v))) for v in clean.wcs.world_to_pixel_values(*star))
    photo = make_photo(stars=[(*star, 200.0)], masked=[(x, y)])
    m = measure(photo, *HERE)
    assert m.status == "partial" and not m.has_brightness and m.has_position
    assert _offset_error(m, *truth) < 0.6


def test_a_saturated_star_is_tracked_by_its_wings():
    # a real star image has faint wings well beyond its core; the core is masked (saturated)
    truth = (4.0, 6.0)
    star = offset_sky(*HERE, *truth)
    clean = make_photo(stars=[(*star, 5000.0)])
    fx, fy = (float(v) for v in clean.wcs.world_to_pixel_values(*star))
    hole = [(x, y) for x in range(int(fx) - 4, int(fx) + 6) for y in range(int(fy) - 4, int(fy) + 6)
            if math.hypot(x - fx, y - fy) <= 2.2]
    errors = []
    for seed in range(8):
        photo = make_photo(stars=[(*star, 5000.0)], masked=hole, seed=seed)
        photo.image += star_image(photo.image.shape, fx, fy, 800.0, fwhm_px=5.5).astype("float32")
        m = measure(photo, *HERE)
        assert m.status == "saturated" and m.flux is None and not m.has_brightness
        errors.append(_offset_error(m, *truth))
    assert np.median(errors) < 1.0                         # within the stated 1" floor for saturated photos


def test_a_saturated_star_with_no_usable_wings_falls_back_to_its_masked_core():
    truth = (4.0, 6.0)
    star = offset_sky(*HERE, *truth)
    clean = make_photo(stars=[(*star, 5000.0)])
    fx, fy = (float(v) for v in clean.wcs.world_to_pixel_values(*star))
    hole = [(x, y) for x in range(int(fx) - 5, int(fx) + 7) for y in range(int(fy) - 5, int(fy) + 7)
            if math.hypot(x - fx, y - fy) <= 3.5]
    m = measure(make_photo(stars=[(*star, 5000.0)], masked=hole), *HERE)
    assert m.status == "saturated"
    assert _offset_error(m, *truth) < 2.5                  # within ~a third of a pixel


def test_a_place_at_the_edge_is_reported_unmeasurable():
    photo = make_photo(n=61)
    m = measure(photo, *offset_sky(*HERE, 180.0, 0.0))
    assert m.status == "off-edge" and not m.has_position


def test_empty_sky_gives_a_low_signal_not_a_detection():
    snrs = [measure(make_photo(noise=0.02, seed=s), *HERE).snr for s in range(20)]
    assert np.median(np.abs(snrs)) < 2.5
