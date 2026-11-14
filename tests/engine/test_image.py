"""Alignment, stacking and rendering."""
import io

import numpy as np
from PIL import Image

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive import store
from galileo_blink.engine.image import render, stack
from galileo_blink.engine.image.grid import roll_angle_deg, to_view, view_grid

from .synth import make_photo, offset_sky


def _peak(frame):
    y, x = np.unravel_index(np.nanargmax(frame), frame.shape)
    return x, y


def test_mask_is_exactly_the_documented_bits_and_never_the_mover_bits():
    assert store.mask_value() == (1 << 2) | (1 << 6) | (1 << 9) | (1 << 10) | (1 << 11)
    for bit in (15, 19, 26, 27, 28, 29):
        assert not store.mask_value() & (1 << bit), f"bit {bit} must never be masked"


def test_the_view_grid_is_north_up_east_left_and_odd():
    g = view_grid(180.0, 0.0, 0.15)
    assert g.n % 2 == 1 and g.n == 89
    cx, cy = g.sky_to_pixel(180.0, 0.0)
    assert abs(cx - 44) < 1e-6 and abs(cy - 44) < 1e-6
    nx, ny = g.sky_to_pixel(*offset_sky(180.0, 0.0, 0, 61.5))
    ex, ey = g.sky_to_pixel(*offset_sky(180.0, 0.0, 61.5, 0))
    assert abs(ny - cy - 10) < 0.01 and abs(nx - cx) < 0.01          # north is up
    assert abs(ex - cx + 10) < 0.01 and abs(ey - cy) < 0.01          # east is left


def test_photos_at_opposite_rolls_align_on_the_same_pixels():
    star = offset_sky(180.0, 0.0, 123.0, -86.1)            # 20 px east, 14 px south
    g = view_grid(180.0, 0.0, 0.15)
    peaks = []
    for roll in (24.2, 204.2):
        photo = make_photo(roll_deg=roll, stars=[(*star, 50.0)])
        assert abs(roll_angle_deg(photo) - roll) < 0.01
        peaks.append(_peak(to_view(photo, g)))
    expected = tuple(round(v) for v in g.sky_to_pixel(*star))
    assert peaks[0] == peaks[1] == expected


def test_masked_pixels_and_uncovered_sky_become_no_data_not_zero():
    photo = make_photo(n=61, masked=[(30, 30)])            # too small to fill a 0.15 deg view
    frame = to_view(photo, view_grid(180.0, 0.0, 0.15))
    assert np.isnan(frame[0, 0])                           # outside the photo
    c = (frame.shape[0] - 1) // 2
    assert np.isnan(frame[c, c])                           # the masked pixel


def test_bits_that_flag_movers_are_not_masked():
    bits = np.zeros((141, 141), dtype=np.int32)
    bits[60:80, 60:80] = (1 << 19) | (1 << 26) | (1 << 28) | (1 << 15)
    photo = make_photo(flag_bits=bits)
    assert not photo.masked.any()


def test_a_median_of_three_ignores_a_cosmic_ray():
    rng = np.random.default_rng(3)
    frames = [rng.normal(1.0 + i, 0.01, (40, 40)) for i in range(3)]    # different sky levels
    frames[1][10, 10] += 50.0
    out = stack.combine(frames)
    assert abs(out[10, 10]) < 0.05
    assert abs(float(np.median(out))) < 0.01               # sky removed


def test_two_photos_still_reject_a_cosmic_ray_but_keep_a_star():
    rng = np.random.default_rng(4)
    a, b = rng.normal(0, 0.01, (40, 40)), rng.normal(0, 0.01, (40, 40))
    a[5, 5] += 30.0                                        # cosmic ray: in one photo only
    a[20, 20] += 10.0
    b[20, 20] += 13.0                                      # a star, 30% different (wavelength)
    out = stack.combine([a, b])
    assert abs(out[5, 5]) < 0.05
    assert abs(out[20, 20] - 11.5) < 0.1


def test_no_data_in_every_photo_stays_no_data():
    a = np.full((10, 10), 1.0)
    a[2, 2] = np.nan
    out = stack.combine([a, a.copy(), a.copy()])
    assert np.isnan(out[2, 2]) and np.isfinite(out[3, 3])


def test_change_map_shows_a_new_source_and_not_a_star_that_changed_colour():
    rng = np.random.default_rng(5)
    base = rng.normal(0, 0.01, (60, 60))
    stars = [(10, 10), (40, 15), (25, 45), (50, 50), (12, 38), (30, 30)]
    for x, y in stars:
        base[y, x] += 20.0
    look = rng.normal(0, 0.01, (60, 60))
    for x, y in stars:
        look[y, x] += 20.0 * 1.25                          # every star 25% brighter: wavelength
    look[45, 8] += 0.3                                     # something new, 30 sigma
    ref = stack.combine([base, look])
    d = stack.change_map(look, base, ref)
    assert d[45, 8] > 8
    assert max(abs(d[y, x]) for x, y in stars) < 2


def test_empty_sky_renders_black_and_no_data_renders_transparent():
    rng = np.random.default_rng(6)
    a = rng.normal(0, 1.0, (30, 30))
    a[15, 15] = 500.0
    a[0, 0] = np.nan
    lo, hi = render.display_limits(a)
    s = render.stretch(a, lo, hi)
    assert float(np.nanmedian(s)) == 0.0                   # sky at black
    im = Image.open(io.BytesIO(render.gray_png(s)))
    assert im.mode == "LA" and im.size == (30 * render.upscale_for(30),) * 2
    alpha = np.array(im)[..., 1]
    assert alpha[-1, 0] == 0 and alpha[0, 0] == 255        # array row 0 is the bottom of the picture
    assert render.display_limits(np.full((4, 4), np.nan)) is None


def test_wide_views_are_enlarged_less():
    assert render.upscale_for(89) == 4 and render.upscale_for(147) == 4
    assert render.upscale_for(235) == 2 and render.upscale_for(293) == 2
