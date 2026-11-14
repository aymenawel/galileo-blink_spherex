"""Measure a star's position and brightness in one photo, in the photo's own pixels.

SPHEREx's star image is 1.2-1.5 pixels wide: narrower than two pixels ("undersampled"). A
simple centre-of-light is biased by that and by any masked pixel, so the position comes from
fitting a star profile of the photo's known width, integrated over each pixel, to the pixels
that have data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.special import erf

from .. import constants as C
from ..archive.store import Photo
from ..sky.motion import offset_arcsec
from .stack import MAD_TO_SIGMA

FWHM_TO_SIGMA = 2.3548
EDGE_PX = 5
SKY_INNER_PX = 7.0
WINDOW_PX = 14                    # half-width of the patch examined around a star
SEARCH_PX = 3.0                   # the fit may move this far from where it was told to look


@dataclass
class Measurement:
    """One object in one photo. Offsets are measured minus expected position, in arcsec."""
    status: str                   # "ok", "partial", "saturated" or "off-edge"
    mjd: float
    camera: int
    file: str
    x: float | None = None        # measured position, native pixels of the cutout
    y: float | None = None
    east: float | None = None     # offset from the expected position, arcsec
    north: float | None = None
    flux: float | None = None     # MJy/sr summed over the star's profile (None if saturated)
    snr: float | None = None
    wavelength: float | None = None   # micron, at the star's pixel
    masked_nearby: int = 0

    @property
    def has_position(self) -> bool:
        return self.status in ("ok", "partial", "saturated") and self.east is not None

    @property
    def has_brightness(self) -> bool:
        return self.status == "ok" and self.flux is not None


def _profile(xx, yy, x0, y0, s):
    """Fraction of a star's light in each pixel: a Gaussian of width s integrated over the pixel."""
    k = 1.0 / (s * math.sqrt(2.0))
    px = 0.5 * (erf((xx + 0.5 - x0) * k) - erf((xx - 0.5 - x0) * k))
    py = 0.5 * (erf((yy + 0.5 - y0) * k) - erf((yy - 0.5 - y0) * k))
    return px * py


def fit_star(image, good, x_guess, y_guess, sigma_px, sky, radius=C.FIT_RADIUS_PX):
    """(x, y, flux) of the best-fitting star near the guess, using only `good` pixels within
    `radius`, or None when too few pixels remain. The flux is solved exactly for each trial
    position, so only the position is searched."""
    ny, nx = image.shape
    yy, xx = np.mgrid[:ny, :nx]
    cx, cy, best = x_guess, y_guess, None
    for _ in range(2):                                  # second pass re-centres the window
        win = good & (np.hypot(xx - cx, yy - cy) <= radius)
        if win.sum() < 8:
            return best
        X, Y, Z = xx[win].astype(float), yy[win].astype(float), image[win].astype(float) - sky

        def flux_at(p):
            prof = _profile(X, Y, p[0], p[1], sigma_px)
            denom = float(prof @ prof)
            return (float(prof @ Z) / denom if denom > 0 else 0.0), prof

        def residual(p):
            f, prof = flux_at(p)
            return f * prof - Z

        lo = [x_guess - SEARCH_PX, y_guess - SEARCH_PX]
        hi = [x_guess + SEARCH_PX, y_guess + SEARCH_PX]
        start = [min(max(cx, lo[0] + 1e-3), hi[0] - 1e-3), min(max(cy, lo[1] + 1e-3), hi[1] - 1e-3)]
        try:
            r = least_squares(residual, start, bounds=(lo, hi), diff_step=1e-3)
        except Exception:                               # noqa: BLE001 - a fit that cannot run
            return best
        best = (float(r.x[0]), float(r.x[1]), flux_at(r.x)[0])
        cx, cy = best[0], best[1]
    return best


def measure(photo: Photo, ra: float, dec: float) -> Measurement:
    """Measure whatever is at the expected sky position (ra, dec) in this photo."""
    w = photo.wcs
    ex, ey = (float(v) for v in w.world_to_pixel_values(ra, dec))
    out = Measurement(status="off-edge", mjd=photo.mjd, camera=photo.camera, file=photo.ref.file)
    ny, nx = photo.image.shape
    if not (EDGE_PX <= ex < nx - EDGE_PX and EDGE_PX <= ey < ny - EDGE_PX):
        return out
    out.wavelength = float(photo.wavelength[int(round(ey)), int(round(ex))])
    # work in a small window around the star: everything below is local
    x_lo, y_lo = max(0, int(ex) - WINDOW_PX), max(0, int(ey) - WINDOW_PX)
    image = photo.image[y_lo:int(ey) + WINDOW_PX + 1, x_lo:int(ex) + WINDOW_PX + 1]
    bad = photo.masked[y_lo:int(ey) + WINDOW_PX + 1, x_lo:int(ex) + WINDOW_PX + 1]
    lx, ly = ex - x_lo, ey - y_lo
    yy, xx = np.mgrid[:image.shape[0], :image.shape[1]]
    r = np.hypot(xx - lx, yy - ly)
    sky_pixels = image[(r > SKY_INNER_PX) & ~bad]
    if sky_pixels.size < 20:
        return out
    sky = float(np.median(sky_pixels))
    noise = float(MAD_TO_SIGMA * np.median(np.abs(sky_pixels - sky))) or 1e-9
    out.masked_nearby = int((bad & (r < C.FIT_RADIUS_PX)).sum())

    sigma_px = photo.psf_fwhm_arcsec / C.PIXEL_ARCSEC / FWHM_TO_SIGMA
    if out.masked_nearby >= C.SATURATED_CORE_PIXELS:
        # Saturated: the core is masked, so the brightness cannot be measured. The position
        # comes from the star's unsaturated wings; if those are too faint, from the centre of
        # the masked core.
        out.status = "saturated"
        wide = sigma_px * C.WING_PROFILE_WIDEN
        fit = fit_star(image, ~bad, lx, ly, wide, sky, radius=C.WING_FIT_RADIUS_PX)
        wing_snr = fit[2] / (noise * math.sqrt(4.0 * math.pi * wide ** 2)) if fit else 0.0
        if fit and wing_snr >= C.WING_MIN_SNR:
            fx, fy = fit[0], fit[1]
        else:
            hole = bad & (r < SKY_INNER_PX)
            fx, fy = float(xx[hole].mean()), float(yy[hole].mean())
    else:
        fit = fit_star(image, ~bad, lx, ly, sigma_px, sky)
        if fit is None:
            return out
        fx, fy, out.flux = fit
        near = bad & (np.hypot(xx - fx, yy - fy) <= C.PARTIAL_RADIUS_PX)
        out.status = "partial" if near.any() else "ok"
        # the optimal-fit noise: a Gaussian's noise-equivalent area is 4*pi*sigma^2 pixels
        out.snr = out.flux / (noise * math.sqrt(4.0 * math.pi * sigma_px ** 2))
    out.x, out.y = fx + x_lo, fy + y_lo
    sra, sdec = (float(v) for v in w.pixel_to_world_values(out.x, out.y))
    out.east, out.north = offset_arcsec(ra, dec, sra, sdec)
    return out
