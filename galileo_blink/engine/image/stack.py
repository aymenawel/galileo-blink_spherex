"""Add photos together, and subtract one date from another.

Stacking several photos of one look beats down noise and removes one-off blemishes (cosmic
rays, satellite streaks). It is what makes faint, cold objects visible at all.
"""
from __future__ import annotations

import warnings

import numpy as np

from .. import constants as C

MAD_TO_SIGMA = 1.4826


def robust_stats(a: np.ndarray) -> tuple[float, float]:
    """(median, sigma) of the finite pixels; sigma from the median absolute deviation, so stars
    do not inflate it. Returns (0, 1) for an empty frame."""
    d = a[np.isfinite(a)]
    if d.size == 0:
        return 0.0, 1.0
    med = float(np.median(d))
    sig = float(np.median(np.abs(d - med)) * MAD_TO_SIGMA)
    return med, sig if sig > 0 else 1.0


def remove_sky(frame: np.ndarray) -> np.ndarray:
    """Subtract the frame's own median: the zodiacal glow differs from photo to photo."""
    return frame - robust_stats(frame)[0]


def combine(frames: list[np.ndarray]) -> np.ndarray:
    """One image from several aligned photos (each has its own sky level removed first).

    3 or more: the median, which ignores anything present in only one photo.
    2: the mean, except where the two disagree by far more than noise and wavelength can
       explain, where the fainter value is kept (a cosmic ray only ever adds light).
    A pixel with no data in any photo stays NaN.
    """
    if not frames:
        raise ValueError("nothing to combine")
    clean = [remove_sky(np.asarray(f, dtype=float)) for f in frames]
    if len(clean) == 1:
        return clean[0].astype(np.float32)
    cube = np.stack(clean)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)         # all-NaN pixels stay NaN
        if len(clean) >= 3:
            return np.nanmedian(cube, axis=0).astype(np.float32)
        mean = np.nanmean(cube, axis=0)
        low = np.nanmin(cube, axis=0)
    sigma = max(robust_stats(c)[1] for c in clean)
    tolerance = 5.0 * np.sqrt(sigma ** 2 + (C.CHANGE_STAR_FRACTION * np.clip(low, 0, None)) ** 2)
    both = np.isfinite(cube).all(axis=0)
    disagree = both & (np.abs(cube[0] - cube[1]) > tolerance)
    return np.where(disagree, low, mean).astype(np.float32)


def bright_static_pixels(reference: np.ndarray, percentile: float = 97.0) -> np.ndarray:
    """The brightest pixels of a reference image: the stars used to match two looks' scales."""
    if not np.isfinite(reference).any():
        return np.zeros(reference.shape, bool)
    return np.isfinite(reference) & (reference > np.nanpercentile(reference, percentile))


def change_map(look: np.ndarray, baseline: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """How much `look` differs from `baseline`, in units of noise ("sigma").

    The baseline is first scaled so the field's stars match (each look sees slightly different
    wavelengths). The noise grows under bright stars, whose brightness legitimately flickers
    with wavelength, so only changes that stand out from that are large. Positive = brighter.
    """
    stars = bright_static_pixels(reference) & np.isfinite(look) & np.isfinite(baseline)
    scale = 1.0
    if stars.sum() >= 5:
        with np.errstate(all="ignore"):
            ratio = float(np.nanmedian(look[stars] / baseline[stars]))
        if np.isfinite(ratio) and 0.2 < ratio < 5.0:
            scale = ratio
    diff = look - scale * baseline
    # Pixels where the look IS the baseline (a median of few frames picks one of them) are
    # exactly zero and would make the noise look smaller than it is.
    sigma = robust_stats(np.where(diff == 0, np.nan, diff))[1]
    star = C.CHANGE_STAR_FRACTION * np.clip(np.nan_to_num(reference), 0, None)
    return (diff / np.sqrt(sigma ** 2 + star ** 2)).astype(np.float32)
