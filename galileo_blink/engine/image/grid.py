"""Put every photo on one north-up grid.

SPHEREx rolls with the ecliptic, so photos of one place arrive in two orientations 180 degrees
apart. Blinked raw, the whole field would spin and every star would seem to move. Each photo
is therefore resampled (bilinear interpolation, which leaves no empty pixels to flicker) onto
a common grid: north up, east left, SPHEREx's own pixel size.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from astropy.wcs import WCS
from reproject import reproject_interp

from .. import constants as C
from ..archive.store import Photo


@dataclass(frozen=True)
class ViewGrid:
    """The square patch of sky a view shows."""
    ra: float
    dec: float
    size_deg: float
    n: int                        # pixels per side (odd, so the centre is a pixel centre)
    wcs: WCS

    def sky_to_pixel(self, ra, dec):
        """(x, y) in view pixels; y grows north, x grows west-to-east leftwards (east is left)."""
        x, y = self.wcs.world_to_pixel_values(ra, dec)
        return float(x), float(y)

    def pixel_to_sky(self, x, y):
        ra, dec = self.wcs.pixel_to_world_values(x, y)
        return float(ra), float(dec)


def view_grid(ra: float, dec: float, size_deg: float) -> ViewGrid:
    n = int(round(size_deg * 3600.0 / C.PIXEL_ARCSEC)) | 1
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2.0, (n + 1) / 2.0]
    w.wcs.cdelt = [-C.PIXEL_ARCSEC / 3600.0, C.PIXEL_ARCSEC / 3600.0]
    w.wcs.cunit = ["deg", "deg"]
    return ViewGrid(ra=ra, dec=dec, size_deg=size_deg, n=n, wcs=w)


def to_view(photo: Photo, grid: ViewGrid) -> np.ndarray:
    """The photo resampled onto the view grid. Masked pixels and sky the photo does not cover
    are NaN, which every later step treats as "no data" (never as zero)."""
    data = np.where(photo.masked, np.nan, photo.image).astype(float)
    out = reproject_interp((data, photo.wcs), grid.wcs, shape_out=(grid.n, grid.n),
                           return_footprint=False)
    return out.astype(np.float32)


def coverage(frame: np.ndarray) -> float:
    """Fraction of the view that has data."""
    return float(np.isfinite(frame).mean())


def roll_angle_deg(photo: Photo) -> float:
    """Position angle (degrees east of north) of the photo's +y axis: how tilted it arrived."""
    m = photo.wcs.pixel_scale_matrix
    return float(np.degrees(np.arctan2(m[0, 1], m[1, 1])) % 360.0)
