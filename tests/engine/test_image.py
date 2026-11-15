"""Alignment, stacking and rendering."""
import io

import numpy as np
from PIL import Image

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive import store
from galileo_blink.engine.image import render, stack
from galileo_blink.engine.image.grid import roll_angle_deg, to_view, view_grid

from .synth import make_photo, offset_sky, star_image


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


def _rgba(png: bytes) -> np.ndarray:
    im = Image.open(io.BytesIO(png))
    assert im.mode == "RGBA"
    return np.array(im)


def _at(pixels: np.ndarray, x: int, y: int, n: int) -> np.ndarray:
    """The displayed RGBA at the middle of array pixel (x, y) [y up] of an n-pixel map."""
    k = render.upscale_for(n)
    return pixels[(n - 1 - y) * k + k // 2, x * k + k // 2]


def test_change_map_noise_is_drawn_dark():
    rng = np.random.default_rng(11)
    for noise in (rng.normal(0, 1, (89, 89)),                       # independent pixels
                  ndimage_smooth(rng.normal(0, 1, (89, 89)))):      # resampled: shared noise
        brightest = _rgba(render.change_png(noise))[..., :3].max(axis=-1)
        # nearly every pixel is black or a tint too faint to notice (under a tenth of full
        # colour), and nothing in pure noise comes near full colour
        assert float((brightest <= 25).mean()) >= 0.97
        assert float((brightest == 0).mean()) >= 0.90
        assert brightest.max() < 128


def ndimage_smooth(a):
    from scipy.ndimage import uniform_filter
    s = uniform_filter(a, 2)
    return s / stack.robust_stats(s)[1]


def test_a_strong_change_is_coloured_with_its_sign():
    rng = np.random.default_rng(12)
    m = rng.normal(0, 1, (61, 61))
    m[20, 15] = 10.0                                       # 10 sigma brighter
    m[40, 45] = -10.0                                      # 10 sigma fainter
    m[5, 5] = np.nan
    px = _rgba(render.change_png(m))
    up, down = _at(px, 15, 20, 61), _at(px, 45, 40, 61)
    assert up[1] > 150 and up[1] > up[0]                   # green: brighter
    assert down[0] > 150 and down[0] > down[1]             # magenta: fainter
    assert _at(px, 5, 5, 61)[3] == 0                       # no data stays transparent
    assert _at(px, 30, 30, 61)[3] == 255


def test_change_strength_is_zero_below_the_dark_level_and_full_at_the_limit():
    m = np.zeros((41, 41))
    m[10, 10], m[20, 20], m[30, 30] = 2.0, C.CHANGE_LIMIT_SIGMA + 1, -(C.CHANGE_LIMIT_SIGMA + 1)
    t = render.change_strength(m)
    assert t[10, 10] == 0.0
    assert t[20, 20] == 1.0 and t[30, 30] == -1.0


def _saturated_star_view(extra_masked=(), n=141):
    """A star too bright for the detector: its core pixels flagged SUR_ERROR (as NASA does).
    `extra_masked` are dead pixels at (east, north) arcsec from the centre."""
    from galileo_blink.engine.image.grid import to_view, view_grid
    star = offset_sky(180.0, 0.0, 61.5, 30.75)
    bits = np.zeros((n, n), dtype=np.int32)
    photo = make_photo(n=n, stars=[(*star, 400.0)], noise=0.01)
    x, y = (int(round(float(v))) for v in photo.wcs.world_to_pixel_values(*star))
    bits[y - 1:y + 2, x - 1:x + 2] = (1 << 2) | (1 << 26)     # SUR_ERROR + BLOOM: overflowed
    for east, north in extra_masked:                           # NONFUNC: a dead pixel
        mx, my = (int(round(float(v))) for v in
                  photo.wcs.world_to_pixel_values(*offset_sky(180.0, 0.0, east, north)))
        bits[my, mx] = 1 << 6
    photo = make_photo(n=n, stars=[(*star, 400.0)], noise=0.01, flag_bits=bits)
    photo.image += star_image(photo.image.shape, x, y, 400.0, fwhm_px=5.0)   # its broad halo
    g = view_grid(180.0, 0.0, 0.15)
    frame = to_view(photo, g)
    return frame, g, star


def test_a_saturated_core_is_drawn_white_but_a_dead_pixel_in_the_sky_stays_no_data():
    frame, g, star = _saturated_star_view(extra_masked=[(-90.0, -60.0)])
    assert np.isnan(frame).sum() > 2                       # the core really is no data
    lo, hi = render.display_limits(frame)
    s = render.stretch(frame, lo, hi)
    cores = render.saturated_cores(s)
    sx, sy = (int(round(v)) for v in g.sky_to_pixel(*star))
    assert cores[sy, sx]
    holes = ~np.isfinite(s) & ~cores
    assert holes.any()                                     # the dead pixel is still a hole
    px = np.array(Image.open(io.BytesIO(render.gray_png(s))))
    k = render.upscale_for(g.n)
    core = px[(g.n - 1 - sy) * k + k // 2, sx * k + k // 2]
    assert core[1] == 255 and core[0] == 255               # opaque white
    hy, hx = np.argwhere(holes)[0]
    assert px[(g.n - 1 - hy) * k + k // 2, hx * k + k // 2][1] == 0
    # measurements are untouched: the stretched image itself still has no data there
    assert np.isnan(s[sy, sx])


def test_a_blank_strip_at_the_edge_stays_no_data():
    a = np.full((40, 40), 0.9)                             # even next to bright pixels
    a[:, :3] = np.nan
    a[20, 20] = np.nan                                     # an enclosed hole in bright light
    cores = render.saturated_cores(a)
    assert not cores[:, :3].any()
    assert cores[20, 20]


def test_a_large_blank_region_is_not_a_star_core():
    a = np.full((60, 60), 0.9)
    a[10:40, 10:40] = np.nan
    assert not render.saturated_cores(a).any()


def test_wide_views_are_enlarged_less():
    assert render.upscale_for(89) == 4 and render.upscale_for(147) == 4
    assert render.upscale_for(235) == 2 and render.upscale_for(293) == 2
