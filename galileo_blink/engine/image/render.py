"""Turn aligned images into the PNGs the browser shows. Display only: nothing here can create
or hide a measurement.

Pixels with no data are written fully transparent, so the page can draw "no data" as a
visible pattern instead of a black that reads as empty sky.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw

from .. import constants as C
from .stack import robust_stats


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


def gray_png(a01: np.ndarray) -> bytes:
    """Greyscale + alpha PNG of a 0..1 image; NaN pixels are transparent."""
    has_data = np.isfinite(a01)
    gray = np.where(has_data, np.clip(np.nan_to_num(a01), 0, 1) * 255, 0)
    return _png(Image.merge("LA", (_upscaled(gray, True),
                                   _upscaled(np.where(has_data, 255, 0), False))))


# Change maps: brighter than before = warm, fainter = cool, no change = dark.
_WARM = np.array([255, 176, 64])
_COOL = np.array([72, 176, 255])


def change_png(sigma_map: np.ndarray) -> bytes:
    """RGBA PNG of a change map (see stack.change_map); NaN pixels are transparent."""
    has_data = np.isfinite(sigma_map)
    t = np.clip(np.nan_to_num(sigma_map) / C.CHANGE_LIMIT_SIGMA, -1, 1)
    strength = np.abs(t) ** 0.7
    rgb = np.where(t[..., None] >= 0, _WARM, _COOL) * strength[..., None]
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
_GIF_ACCENT = (255, 178, 74)


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
