"""Fetch one photo's cutout: from disk if we have it, else NASA's cloud copy, else IRSA.

A `Photo` is the unit the rest of the engine works with: calibrated pixels in the exposure's
own grid, NASA's flags, the wavelength of every pixel, and the mapping to the sky.
"""
from __future__ import annotations

import io
import math
import threading
import time
from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from .. import constants as C
from ..errors import ServiceDown
from . import http
from .cache import atomic_write, cache_dir, lock_for
from .photos import PhotoRef
from .remote_fits import NoOverlap, RawCutout, cutout_wcs, read_cutout

CLOUD = "NASA's cloud copy of the SPHEREx archive"
IRSA_FILES = "NASA's image archive (IRSA)"
CLOUD_DOWN_S = 120.0
"""When the cloud copy fails outright (not one missing file), photos go straight to IRSA for
this long, so a build of 160 photos does not wait out the cloud's deadline 160 times."""
_cloud_down_until = 0.0
_irsa_slots = threading.BoundedSemaphore(C.IRSA_WORKERS)
"""IRSA's own file servers refuse more than about five requests at once, however many photos
are being fetched in parallel from the cloud copy."""


class HttpSource:
    """A remote file read by HTTP Range requests."""

    def __init__(self, url: str, service: str):
        self.url, self.service = url, service

    def read(self, start: int, end: int) -> bytes:
        return http.read_range(self.url, start, end, service=self.service)

    def tail(self, n: int) -> bytes:
        r = http.get(self.url, service=self.service, retries=2, headers={"Range": f"bytes=-{n}"})
        if r.status_code != 206:
            raise ServiceDown(self.service, "it ignored a partial-read request")
        return r.content


@dataclass
class Photo:
    ref: PhotoRef
    image: np.ndarray             # float32, MJy/sr, native pixels
    flags: np.ndarray             # int32, NASA's flag bits
    wavelength: np.ndarray        # float32, micron per pixel
    header: fits.Header
    x0: int
    y0: int
    bytes_read: int = 0           # 0 when it came from our own disk
    source: str = "disk"          # "cloud", "irsa" or "disk"
    _wcs: WCS | None = field(default=None, repr=False)

    @property
    def wcs(self) -> WCS:
        if self._wcs is None:
            self._wcs = cutout_wcs(self.header, self.x0, self.y0, *self.image.shape)
        return self._wcs

    @property
    def camera(self) -> int:
        return self.ref.camera

    @property
    def mjd(self) -> float:
        """Middle of the exposure."""
        return float(self.header.get("MJD-AVG", self.ref.mjd))

    @property
    def finast(self) -> int:
        """NASA's astrometry grade: 0 good, 1 marginal, more = do not use."""
        return int(self.header.get("FINAST", 0))

    @property
    def psf_fwhm_arcsec(self) -> float:
        return float(self.header.get("PSF_FWHM") or C.DEFAULT_PSF_FWHM_ARCSEC)

    @property
    def masked(self) -> np.ndarray:
        """True where the pixel carries no usable data."""
        return ((self.flags & mask_value()) != 0) | ~np.isfinite(self.image)


def mask_value() -> int:
    return sum(1 << b for b in C.MASK_BITS)


def half_pixels(size_deg: float) -> int:
    """Half-width, in pixels, of the cutout needed to fill a north-up view of `size_deg`."""
    return int(math.ceil(size_deg * C.OVERFETCH * 3600.0 / C.PIXEL_ARCSEC / 2.0)) + 1


def _cache_path(ref: PhotoRef, ra: float, dec: float, half: int):
    stem = ref.file[:-5] if ref.file.endswith(".fits") else ref.file
    return cache_dir() / "photos" / f"{stem}_{ra:.4f}_{dec:+.4f}_{half}.npz"


def _save(path, raw: RawCutout) -> None:
    buf = io.BytesIO()
    np.savez_compressed(buf, image=raw.image, flags=raw.flags, wavelength=raw.wavelength,
                        header=np.array(raw.header.tostring()), origin=np.array([raw.x0, raw.y0]))
    atomic_write(path, buf.getvalue())


def _load(path, ref: PhotoRef) -> Photo:
    with np.load(path) as z:
        x0, y0 = (int(v) for v in z["origin"])
        return Photo(ref=ref, image=z["image"], flags=z["flags"], wavelength=z["wavelength"],
                     header=fits.Header.fromstring(str(z["header"])), x0=x0, y0=y0)


def _is_outage(e: Exception) -> bool:
    """The cloud copy failing as a whole (no answer, busy, refusing), not one file missing."""
    return isinstance(e, ServiceDown) and e.detail not in ("HTTP 403", "HTTP 404")


def _mark_cloud_down() -> None:
    global _cloud_down_until
    _cloud_down_until = time.time() + CLOUD_DOWN_S


def fetch_photo(ref: PhotoRef, ra: float, dec: float, size_deg: float) -> Photo:
    """The cutout of `ref` around (ra, dec). Raises NoOverlap if the place is off the frame,
    ServiceDown if neither copy of the archive answered."""
    half = half_pixels(size_deg)
    path = _cache_path(ref, ra, dec, half)
    with lock_for(str(path)):                   # one download per photo at a time
        if path.exists():
            try:
                return _load(path, ref)
            except Exception:                   # noqa: BLE001 - a bad cached file is fetched again
                path.unlink(missing_ok=True)
        raw, source, last = None, "", None
        for name, prefix, service in (("cloud", C.CLOUD_DATA_PREFIX, CLOUD),
                                      ("irsa", C.IRSA_DATA_PREFIX, IRSA_FILES)):
            if name == "cloud" and time.time() < _cloud_down_until:
                continue
            try:
                if name == "irsa":
                    with _irsa_slots:
                        raw = read_cutout(HttpSource(prefix + ref.path, service), ra, dec, half)
                else:
                    raw = read_cutout(HttpSource(prefix + ref.path, service), ra, dec, half)
                source = name
                break
            except NoOverlap:
                raise
            except Exception as e:              # noqa: BLE001 - try the other copy
                last = e
                if name == "cloud" and _is_outage(e):
                    _mark_cloud_down()
        if raw is None:
            if isinstance(last, ServiceDown):
                raise last
            raise ServiceDown(IRSA_FILES, f"{ref.file} could not be read ({type(last).__name__})")
        _save(path, raw)                        # only a cutout that parsed is ever cached
    return Photo(ref=ref, image=raw.image, flags=raw.flags, wavelength=raw.wavelength,
                 header=raw.header, x0=raw.x0, y0=raw.y0, bytes_read=raw.bytes_read,
                 source=source)
