"""Turn aligned images into the PNGs the browser shows. Display only: nothing here can create
or hide a measurement.

Pixels with no data are written fully transparent, so the page can draw "no data" as a
visible pattern instead of a black that reads as empty sky. The one exception is the core of
a star so bright the detector overflowed: it is drawn white, because "at least this bright"
is what those pixels say (see saturated_cores).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, find_objects, label, uniform_filter

from .. import constants as C
from .stack import robust_stats

SATURATED_CORE_MAX_PX = 400
"""A blank island larger than this (about 2 arcminutes across) is not a star's overflowed core;
R Draconis, the brightest test target, leaves holes of up to 220 view pixels."""
SATURATED_RIM_MIN = 0.1
SATURATED_RIM_MEDIAN = 0.3
"""Every pixel around an overflowed core is clearly above the sky (>= 0.1 of the display) and
most are bright (median >= 0.3). Measured on the five test targets: saturated cores have rims
of minimum 0.19-0.94 and median 0.44-1.0; dead pixels in the sky have rims of 0.0."""


def display_limits(a: np.ndarray) -> tuple[float, float] | None:
    """(black point, white point) that put empty sky at black, or None if there is no data.

    The black point is tied to the measured noise (median + 2 sigma). A percentile black
    point fails on an empty field, where it stretches pure noise across the grey range."""
    d = a[np.isfinite(a)]
    if d.size == 0:
        return None
    med, sig = robust_stats(a)
    lo = med + C.SKY_FLOOR_SIGMA * sig
    hi = max(float(np.percentile(d, C.STRETCH_TOP_PERCENTILE)), lo + 6.0 * sig)
    return lo, hi


def stretch(a: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """asinh stretch to 0..1 (faint detail kept, bright stars not burnt out). NaN stays NaN."""
    x = np.clip((a - lo) / (hi - lo), 0, None)
    return np.clip(np.arcsinh(x * C.STRETCH_SOFTENING) / np.arcsinh(C.STRETCH_SOFTENING), 0, 1)


def upscale_for(n: int) -> int:
    """How much to enlarge a view of n pixels for display: 4x for the usual narrow views,
    less for wide ones, so pictures stay around 350-600 screen pixels."""
    return max(1, min(C.DISPLAY_UPSCALE, round(C.DISPLAY_TARGET_PX / n)))


def _upscaled(channel: np.ndarray, smooth: bool) -> Image.Image:
    """Array [y up] -> image [y down], enlarged for display."""
    im = Image.fromarray(np.flipud(channel).astype(np.uint8), "L")
    k = upscale_for(channel.shape[1])
    size = (channel.shape[1] * k, channel.shape[0] * k)
    return im.resize(size, Image.LANCZOS if smooth else Image.NEAREST)


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG", compress_level=6)
    return buf.getvalue()


def saturated_cores(a01: np.ndarray) -> np.ndarray:
    """Pixels with no data that are the overflowed core of a star too bright for the detector.

    NASA's pipeline cannot measure a pixel that overflowed (it flags it SUR_ERROR, with BLOOM
    or OVERFLOW), so the middle of every very bright star arrives as "no data". Such a hole is
    recognised in the picture itself: a small island of no data, away from the picture's edge,
    whose every neighbour is clearly bright and most of them near the top of the display. A
    dead pixel or a gap in coverage lies in ordinary sky or at the edge, and is not one."""
    blank = ~np.isfinite(a01)
    out = np.zeros(a01.shape, bool)
    if not blank.any() or blank.all():
        return out
    eight = np.ones((3, 3), bool)
    labels, n = label(blank, structure=eight)
    ny, nx = a01.shape
    for k, box in enumerate(find_objects(labels), start=1):
        ys, xs = box
        if ys.start == 0 or xs.start == 0 or ys.stop == ny or xs.stop == nx:
            continue                                     # touches the edge: no coverage
        y0, y1, x0, x1 = ys.start - 1, ys.stop + 1, xs.start - 1, xs.stop + 1
        island = labels[y0:y1, x0:x1] == k
        if island.sum() > SATURATED_CORE_MAX_PX:
            continue
        rim = binary_dilation(island, structure=eight) & ~island
        values = a01[y0:y1, x0:x1][rim]
        if (values.size and np.isfinite(values).all() and values.min() >= SATURATED_RIM_MIN
                and float(np.median(values)) >= SATURATED_RIM_MEDIAN):
            out[y0:y1, x0:x1] |= island
    return out


def gray_png(a01: np.ndarray, fill_saturated: bool = True) -> bytes:
    """Greyscale + alpha PNG of a 0..1 image; NaN pixels are transparent, except the overflowed
    cores of very bright stars, which are drawn white ("at least this bright"; see
    saturated_cores). Measurements never use those pixels."""
    a01 = np.asarray(a01, dtype=float)
    if fill_saturated:
        a01 = np.where(saturated_cores(a01), 1.0, a01)
    has_data = np.isfinite(a01)
    gray = np.where(has_data, np.clip(np.nan_to_num(a01), 0, 1) * 255, 0)
    return _png(Image.merge("LA", (_upscaled(gray, True),
                                   _upscaled(np.where(has_data, 255, 0), False))))


# Change maps: brighter than before = green, fainter = magenta, no change = dark. The two
# are opposite colours, so they stay apart for colour-blind eyes too.
_BRIGHTER = np.array([164, 240, 92])
_FAINTER = np.array([255, 96, 170])
CHANGE_DARK_SIGMA = 2.5
"""Changes smaller than this are drawn black: pure noise exceeds it in about 1 pixel in 80."""
CHANGE_RAMP_POWER = 1.0
"""Above the dark level colour grows in step with significance, reaching full colour at
CHANGE_LIMIT_SIGMA. A steeper curve was tried and hid real changes of 3 to 5 sigma, such as
a bright star that halved in brightness (its noise is deliberately generous)."""
CHANGE_SMOOTH_PX = 3
"""A change spread over a star's wings is faint in each pixel but clear over a few pixels
together, so a change also counts at its significance averaged over 3 x 3 pixels."""


def _smoothed_significance(sigma_map: np.ndarray) -> np.ndarray:
    """The change map averaged over CHANGE_SMOOTH_PX pixels, re-expressed in its own noise units
    (measured, so pixels that already share noise through resampling are handled honestly)."""
    has_data = np.isfinite(sigma_map)
    total = uniform_filter(np.where(has_data, sigma_map, 0.0), CHANGE_SMOOTH_PX, mode="constant")
    weight = uniform_filter(has_data.astype(float), CHANGE_SMOOTH_PX, mode="constant")
    with np.errstate(all="ignore"):
        mean = np.where(has_data & (weight > 0.5), total / weight, np.nan)
    if not np.isfinite(mean).any():
        return np.zeros(sigma_map.shape)
    return np.nan_to_num(mean / robust_stats(mean)[1])


def change_strength(sigma_map: np.ndarray) -> np.ndarray:
    """Signed display strength in -1..1 of a change map: 0 (black) below CHANGE_DARK_SIGMA,
    a smooth ramp above it, full colour at CHANGE_LIMIT_SIGMA. A pixel counts at the larger of
    its own significance and that of its 3 x 3 neighbourhood. Display only."""
    raw = np.nan_to_num(np.asarray(sigma_map, dtype=float))
    smooth = _smoothed_significance(np.asarray(sigma_map, dtype=float))
    s = np.where(np.abs(smooth) > np.abs(raw), smooth, raw)
    level = np.clip((np.abs(s) - CHANGE_DARK_SIGMA) / (C.CHANGE_LIMIT_SIGMA - CHANGE_DARK_SIGMA), 0, 1)
    return np.sign(s) * level ** CHANGE_RAMP_POWER


def change_png(sigma_map: np.ndarray) -> bytes:
    """RGBA PNG of a change map (see stack.change_map); NaN pixels are transparent. Noise is
    drawn black, so only changes that stand out from it are coloured."""
    has_data = np.isfinite(sigma_map)
    t = change_strength(sigma_map)
    rgb = np.where(t[..., None] >= 0, _BRIGHTER, _FAINTER) * np.abs(t)[..., None]
    channels = [_upscaled(rgb[..., i], True) for i in range(3)]
    channels.append(_upscaled(np.where(has_data, 255, 0), False))
    return _png(Image.merge("RGBA", channels))


def flags_png(flagged: np.ndarray) -> bytes:
    """RGBA overlay: opaque white where `flagged` is True, transparent elsewhere (the page
    tints it). Not smoothed: a flag belongs to exact pixels."""
    alpha = _upscaled(np.where(flagged, 255, 0), False)
    white = Image.new("L", alpha.size, 255)
    return _png(Image.merge("LA", (white, alpha)))


GIF_SIZE = 560                    # pixels across: large enough to read, small enough to share
_GIF_BACKGROUND = (10, 11, 13)
_GIF_NO_DATA = (38, 41, 46)
_GIF_TEXT = (236, 238, 241)
_GIF_ACCENT = (61, 139, 255)      # the site's accent


def blink_gif(pictures: list[bytes], captions: list[str], credit: str, frame_ms: int = 700) -> bytes:
    """An animated GIF that steps through `pictures` (the PNGs of one camera's dates), each
    with its caption, looping forever. Pixels with no data are drawn mid-grey, never black."""
    if not pictures:
        raise ValueError("nothing to animate")
    frames = []
    for png, caption in zip(pictures, captions):
        picture = Image.open(io.BytesIO(png)).convert("RGBA").resize((GIF_SIZE, GIF_SIZE), Image.LANCZOS)
        frame = Image.new("RGB", (GIF_SIZE, GIF_SIZE + 34), _GIF_BACKGROUND)
        sky = Image.new("RGB", (GIF_SIZE, GIF_SIZE), _GIF_NO_DATA)
        sky.paste(picture, (0, 0), picture)
        frame.paste(sky, (0, 0))
        draw = ImageDraw.Draw(frame)
        draw.text((10, GIF_SIZE + 6), caption, fill=_GIF_ACCENT, font_size=18)
        width = draw.textlength(credit, font_size=13)
        draw.text((GIF_SIZE - width - 10, GIF_SIZE + 10), credit, fill=_GIF_TEXT, font_size=13)
        frames.append(frame)
    buf = io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], duration=frame_ms, loop=0,
                   optimize=True)
    return buf.getvalue()
