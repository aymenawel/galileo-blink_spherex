"""Fetch one photo and make it ready for a view: aligned, quality-checked, flags counted."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from reproject import reproject_interp

from .. import constants as C
from ..archive.photos import PhotoRef
from ..archive.remote_fits import NoOverlap
from ..archive.store import Photo, fetch_photo
from ..errors import ServiceDown
from ..flags import CONTAMINATION_MASK, count_flags
from .grid import ViewGrid, coverage, to_view


@dataclass
class Frame:
    """One usable photo, aligned to the view."""
    photo: Photo
    season: int                           # which time step of the view it belongs to
    view: np.ndarray                      # the photo on the view grid (NaN = no data)
    flagged: np.ndarray                   # view-grid mask of pixels NASA flagged
    flag_counts: dict[str, int]


def _inside_view(photo: Photo, grid: ViewGrid) -> np.ndarray:
    """Which of the photo's native pixels fall inside the view."""
    ny, nx = photo.image.shape
    yy, xx = np.mgrid[:ny, :nx]
    ra, dec = photo.wcs.pixel_to_world_values(xx, yy)
    vx, vy = grid.wcs.world_to_pixel_values(ra, dec)
    return (vx > -0.5) & (vx < grid.n - 0.5) & (vy > -0.5) & (vy < grid.n - 0.5)


def prepare(ref: PhotoRef, season: int, ra: float, dec: float, size_deg: float, grid: ViewGrid):
    """Fetch one photo and align it. Returns a Frame, or a dict saying why it was left out."""
    try:
        photo = fetch_photo(ref, ra, dec, size_deg)
    except NoOverlap:
        return dict(file=ref.file, season=season, reason="off_frame")
    except ServiceDown:
        return dict(file=ref.file, season=season, reason="not_received")
    except Exception as e:                # noqa: BLE001 - one photo must not sink the view
        return dict(file=ref.file, season=season, reason="unreadable", detail=type(e).__name__)
    if photo.finast > C.FINAST_MAX:
        return dict(file=ref.file, season=season, reason="poor_astrometry", finast=photo.finast,
                    bytes=photo.bytes_read, source=photo.source)
    view = to_view(photo, grid)
    if coverage(view) < C.MIN_COVERAGE:
        return dict(file=ref.file, season=season, reason="partial_coverage",
                    bytes=photo.bytes_read, source=photo.source)
    contaminated = ((photo.flags & CONTAMINATION_MASK) != 0).astype(float)
    flagged = reproject_interp((contaminated, photo.wcs), grid.wcs, shape_out=(grid.n, grid.n),
                               order="nearest-neighbor", return_footprint=False) > 0.5
    return Frame(photo=photo, season=season, view=view, flagged=flagged,
                 flag_counts=count_flags(photo.flags, _inside_view(photo, grid)))
