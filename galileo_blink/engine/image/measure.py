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


def _search(residual, start, lo, hi):
    """Minimise |residual(p)|^2 over a 2-parameter position inside [lo, hi] with a damped
    Gauss-Newton search (a few dozen evaluations; a general optimiser costs 10x more here)."""
    p = np.asarray(start, dtype=float)
    r = residual(p)
    cost, damping, step_size = float(r @ r), 1e-3, 1e-3
    for _ in range(15):
        jac = np.empty((r.size, 2))
        for k in range(2):
            dp = np.zeros(2)
            dp[k] = step_size
            jac[:, k] = (residual(p + dp) - r) / step_size
        a, g = jac.T @ jac, jac.T @ r
        moved = False
        for _ in range(8):
            try:
                step = np.linalg.solve(a + damping * (np.diag(np.diag(a)) + 1e-12 * np.eye(2)), -g)
            except np.linalg.LinAlgError:
                return p
            q = np.clip(p + step, lo, hi)
            rq = residual(q)
            if float(rq @ rq) < cost:
                p, r, cost, damping, moved = q, rq, float(rq @ rq), damping * 0.3, True
                break
            damping *= 10.0
        if not moved or float(np.abs(step).max()) < 1e-4:
            break
    return p


def fit_star(image, good, x_guess, y_guess, sigma_px, sky, radius=C.FIT_RADIUS_PX):
    """(x, y, flux) of the best-fitting star near the guess, using only `good` pixels within
    `radius`, or None when too few pixels remain. The flux is solved exactly for each trial
    position, so only the position is searched."""
    ny, nx = image.shape
    yy, xx = np.mgrid[:ny, :nx]
    lo = np.array([x_guess - SEARCH_PX, y_guess - SEARCH_PX])
    hi = np.array([x_guess + SEARCH_PX, y_guess + SEARCH_PX])
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

        p = _search(residual, np.clip([cx, cy], lo + 1e-3, hi - 1e-3), lo, hi)
        best = (float(p[0]), float(p[1]), flux_at(p)[0])
        cx, cy = best[0], best[1]
    return best


def measure(photo: Photo, ra: float, dec: float) -> Measurement:
    """Measure whatever is at the expected sky position (ra, dec) in this photo."""
    return measure_many(photo, [(ra, dec)])[0]


def measure_many(photo: Photo, places: list[tuple[float, float]]) -> list[Measurement]:
    """Measure several expected sky positions in one photo (the sky-to-pixel conversions are
    done together, which is where most of the time goes)."""
    if not places:
        return []
    ras, decs = np.array([p[0] for p in places]), np.array([p[1] for p in places])
    xs, ys = photo.wcs.world_to_pixel_values(ras, decs)
    out = [_measure_at_pixel(photo, float(x), float(y)) for x, y in zip(np.atleast_1d(xs), np.atleast_1d(ys))]
    found = [i for i, m in enumerate(out) if m.x is not None]
    if found:
        sra, sdec = photo.wcs.pixel_to_world_values(np.array([out[i].x for i in found]),
                                                    np.array([out[i].y for i in found]))
        for i, mra, mdec in zip(found, np.atleast_1d(sra), np.atleast_1d(sdec)):
            out[i].east, out[i].north = offset_arcsec(places[i][0], places[i][1], float(mra), float(mdec))
    return out


def _measure_at_pixel(photo: Photo, ex: float, ey: float) -> Measurement:
    """Measure at an expected pixel position; the sky offset is filled in by the caller."""
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
    return out
