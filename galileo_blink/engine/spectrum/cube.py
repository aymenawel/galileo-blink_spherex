"""A quick 102-colour spectrum of any place, from SPHEREx's all-sky cube.

NASA's DR1 release includes a mosaic of the whole sky in all 102 SPHEREx channels, stored as
HEALPix tiles of 512 x 512 x 102 pixels (321 MB each). Reading only the few pixels around one
position, in every channel, takes about two seconds and 1.4 MB.

It is a quick look, not precise photometry: the mosaic averages every date together (so it
cannot show change), its pixels are 12.9", and NASA warns of striping near bright emission
lines. The per-photo spectrum built from a view's own photos is the careful one.
"""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import astropy.units as u
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy_healpix import HEALPix

from .. import constants as C
from ..archive import http
from ..archive.cache import cache_dir, read_json, write_json

SERVICE = "NASA's cloud copy of the SPHEREx all-sky cube"
CUBE_PREFIX = C.CLOUD_DATA_PREFIX + "dr1/hips5_cube/hips_20261026/Norder5/"
"""A NEW CUBE RELEASE CHANGES THIS PATH (one line)."""
TILE_ORDER = 5
TILE_PIXELS = 512
CHANNELS = 102
BLOCK = 2880
HALF = 3                          # a 7 x 7 pixel patch is read around the position
APERTURE = 1                      # the central 3 x 3 pixels (38.6") hold the source
PIXEL_SR = 4.0 * math.pi / (12 * 4 ** (TILE_ORDER + 9))
"""Solid angle of one cube pixel (HEALPix order 14: 12.9" across)."""
_WCS_KEYS = re.compile(r"(CTYPE|CRPIX|CRVAL|CDELT|CUNIT)[12]|PC[12]_[12]|CD[12]_[12]|PV[12]_\d+"
                       r"|LONPOLE|LATPOLE|RADESYS")
_healpix = HEALPix(nside=2 ** TILE_ORDER, order="nested")


def tile_index(ra: float, dec: float) -> int:
    """Which of the 12,288 tiles holds (ra, dec)."""
    return int(_healpix.lonlat_to_healpix(ra * u.deg, dec * u.deg))


def tile_url(index: int) -> str:
    return f"{CUBE_PREFIX}Dir{index // 10000 * 10000}/Npix{index}_cube.fits"


def _header(buf: bytes) -> tuple[fits.Header, int]:
    pos = 0
    while buf[pos:pos + 8] != b"END     ":
        pos += 80
        if pos >= len(buf):
            raise ValueError("FITS header has no END")
    length = math.ceil((pos + 80) / BLOCK) * BLOCK
    return fits.Header.fromstring(buf[:length].decode("ascii", "replace")), length


def patch_photometry(patch: np.ndarray) -> tuple[float | None, float | None]:
    """(flux above surroundings in mJy, surrounding surface brightness in MJy/sr) from a
    (2*HALF+1)-pixel square patch. None where the source pixels have no data (saturated)."""
    c = HALF
    core = patch[c - APERTURE:c + APERTURE + 1, c - APERTURE:c + APERTURE + 1]
    ring = patch.copy()
    ring[c - APERTURE - 1:c + APERTURE + 2, c - APERTURE - 1:c + APERTURE + 2] = np.nan
    if not np.isfinite(ring).any():
        return None, None
    background = float(np.nanmedian(ring))
    if not np.isfinite(core).all():
        return None, background
    return float((core - background).sum() * PIXEL_SR * 1e9), background


@lru_cache(maxsize=1)
def _channels(url: str) -> tuple[dict, ...]:
    """Wavelength, bandwidth and camera of each of the 102 channels (the same in every tile).
    The table is the second-to-last HDU: the file ends with two 2-block tables."""
    r = http.get(url, service=SERVICE, retries=2, headers={"Range": f"bytes=-{4 * BLOCK}"})
    table = fits.BinTableHDU.fromstring(r.content[:2 * BLOCK]).data
    if len(table) != CHANNELS:
        raise ValueError("unexpected all-sky cube channel table")
    return tuple(dict(wavelength=round(float(row["WAVELENGTH"]), 4),
                      bandwidth=round(float(row["BANDWIDTH"]), 4), camera=int(row["DETECTOR"]))
                 for row in table)


def quick_spectrum(ra: float, dec: float) -> dict:
    """The all-sky cube's spectrum at (ra, dec): one point per SPHEREx channel."""
    ra, dec = round(float(ra) % 360.0, 4), round(float(dec), 4)
    path = cache_dir() / "spectra" / f"{ra:.4f}_{dec:+.4f}.json"
    cached = read_json(path)
    if cached:
        return cached
    url = tile_url(tile_index(ra, dec))
    head = http.read_range(url, 0, 6 * BLOCK - 1, service=SERVICE)
    primary, primary_len = _header(head)
    image_header, image_len = _header(head[primary_len:])
    if image_header.get("EXTNAME", "").strip() != "IMAGE" or image_header["NAXIS3"] != CHANNELS:
        raise ValueError("unexpected all-sky cube layout")
    sky = fits.Header()
    for card in image_header.cards:
        if _WCS_KEYS.fullmatch(card.keyword):
            sky[card.keyword] = card.value
    x, y = (int(round(float(v))) for v in WCS(sky).world_to_pixel_values(ra, dec))
    x = min(max(x, HALF), TILE_PIXELS - HALF - 1)           # stay inside the tile at its edges
    y = min(max(y, HALF), TILE_PIXELS - HALF - 1)
    data_at = primary_len + image_len
    plane_bytes = TILE_PIXELS * TILE_PIXELS * 4
    side = 2 * HALF + 1

    def patch(channel: int) -> np.ndarray:
        start = data_at + channel * plane_bytes + (y - HALF) * TILE_PIXELS * 4
        raw = http.read_range(url, start, start + side * TILE_PIXELS * 4 - 1, service=SERVICE)
        rows = np.frombuffer(raw, dtype=">f4").reshape(side, TILE_PIXELS)
        return rows[:, x - HALF:x + HALF + 1].astype(float)

    with ThreadPoolExecutor(16) as pool:
        patches = list(pool.map(patch, range(CHANNELS)))
    points = []
    for info, p in zip(_channels(url), patches):
        flux, background = patch_photometry(p)
        points.append(dict(info, flux_mjy=None if flux is None else round(flux, 4),
                           background=None if background is None else round(background, 4)))
    result = dict(ra=ra, dec=dec, unit="mJy", aperture_arcsec=round(3 * math.degrees(math.sqrt(PIXEL_SR)) * 3600, 1),
                  points=points,
                  source="SPHEREx DR1 all-sky spectral cube (NASA/IPAC IRSA)",
                  note="A quick look from NASA's all-sky mosaic: every date averaged together, "
                       "12.9-arcsecond pixels. Good for the shape of a spectrum, not for precise "
                       "brightness.")
    write_json(path, result)
    return result
