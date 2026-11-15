"""Synthetic SPHEREx-like photos for offline tests: rolled, undersampled stars, known truth."""
from __future__ import annotations

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.special import erf

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive.photos import PhotoRef
from galileo_blink.engine.archive.store import Photo

FWHM_PX = 1.35                  # SPHEREx's star image is narrower than two pixels


def star_image(shape, x0, y0, flux, fwhm_px=FWHM_PX):
    """A star of total `flux`, integrated over each pixel (not sampled at pixel centres)."""
    s = fwhm_px / 2.3548
    k = 1.0 / (s * np.sqrt(2.0))
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    px = 0.5 * (erf((xx + 0.5 - x0) * k) - erf((xx - 0.5 - x0) * k))
    py = 0.5 * (erf((yy + 0.5 - y0) * k) - erf((yy - 0.5 - y0) * k))
    return flux * px * py


def rolled_wcs(ra, dec, n, roll_deg):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix = [n / 2 + 0.5, n / 2 + 0.5]
    w.wcs.crval = [ra, dec]
    s, c = np.sin(np.radians(roll_deg)), np.cos(np.radians(roll_deg))
    w.wcs.cd = np.array([[-c, s], [s, c]]) * C.PIXEL_ARCSEC / 3600.0
    return w


def make_photo(ra=180.0, dec=0.0, n=141, roll_deg=24.0, stars=(), noise=0.01, sky=0.4,
               mjd=61000.0, camera=6, seed=0, masked=(), flag_bits=None, wavelength=4.6,
               shift_arcsec=(0.0, 0.0)):
    """A Photo whose `stars` are (ra, dec, flux) tuples. `masked` pixels (x, y) get the HOT flag.
    `shift_arcsec` (east, north) mis-registers the photo's WCS, like real astrometric error."""
    w = rolled_wcs(ra, dec, n, roll_deg)
    rng = np.random.default_rng(seed)
    image = rng.normal(sky, noise, (n, n))
    for sra, sdec, flux in stars:
        x, y = w.world_to_pixel_values(sra, sdec)
        image += star_image((n, n), float(x), float(y), flux)
    flags = np.zeros((n, n), dtype=np.int32)
    for x, y in masked:
        flags[y, x] |= 1 << 10
    if flag_bits is not None:
        flags |= flag_bits
    header = w.to_header()
    if shift_arcsec != (0.0, 0.0):
        # the WCS claims the field is shifted: stars appear displaced by -shift
        header["CRVAL1"] += shift_arcsec[0] / 3600.0 / np.cos(np.radians(dec))
        header["CRVAL2"] += shift_arcsec[1] / 3600.0
    header["MJD-AVG"] = mjd
    header["FINAST"] = 0
    header["PSF_FWHM"] = FWHM_PX * C.PIXEL_ARCSEC
    ref = PhotoRef(file=f"level2_synth_{seed}_D{camera}_spx_l2b-v27-2026-001.fits",
                   path=f"synth/{seed}", camera=camera, mjd=mjd - 0.0007, collection="spherex_synth")
    return Photo(ref=ref, image=image.astype(np.float32), flags=flags,
                 wavelength=np.full((n, n), wavelength, dtype=np.float32),
                 header=fits.Header(header), x0=0, y0=0)


def brightness_rows(camera=1, levels=None, per_season=6, band=(0.75, 1.1), slope=0.0,
                    noise=0.02, flux=100.0, snr=500.0, status="ok", seed=0, wavelengths=None):
    """One object's per-photo brightness in one camera, shaped like view.json's `brightness`.

    `levels` maps season -> true brightness relative to the first (default: three steady
    seasons). Every photo sees a different wavelength, drawn across `band` unless
    `wavelengths` (season -> list) fixes them. ln(flux) = ln(flux x level) + slope x
    (wavelength - middle of band) + Gaussian noise of `noise` (in ln units)."""
    levels = levels if levels is not None else {0: 1.0, 1: 1.0, 2: 1.0}
    rng = np.random.default_rng(seed)
    middle = 0.5 * (band[0] + band[1])
    rows = []
    for season, level in levels.items():
        lams = (wavelengths or {}).get(season)
        if lams is None:
            lams = rng.uniform(band[0], band[1], per_season)
        for lam in lams:
            f = flux * level * np.exp(slope * (lam - middle) + rng.normal(0.0, noise))
            rows.append(dict(camera=camera, season=season, mjd=60900.0 + 180.0 * season,
                             wavelength=round(float(lam), 4), flux_mjy=float(f), snr=snr,
                             status=status))
    return rows


def offset_sky(ra, dec, east_arcsec, north_arcsec):
    """(ra, dec) moved by a small offset on the sky."""
    return (ra + east_arcsec / 3600.0 / np.cos(np.radians(dec)), dec + north_arcsec / 3600.0)
