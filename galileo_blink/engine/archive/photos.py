"""Which SPHEREx photos cover a place in the sky.

Asked of IRSA's Simple Image Access service (one small request per data collection, answered
in about a second). The list is cached; the archive only grows, so if IRSA is down an older
list is still a true, smaller answer and is served marked `stale`.
"""
from __future__ import annotations

import csv
import io
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from astropy.time import Time

from .. import constants as C
from ..errors import ServiceDown
from . import http
from .cache import cache_dir, read_json, write_json

SERVICE = "NASA's image archive (IRSA)"
SIA = C.IRSA + "/SIA"
_CAMERA = re.compile(r"D([1-6])\b")
_VERSION = re.compile(r"l2b\w*-v(\d+)-")      # l2b-v27-..., l2b_retry-v27-...


@dataclass(frozen=True)
class PhotoRef:
    """One exposure by one camera: where the file is and when it was taken."""
    file: str            # level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits
    path: str            # dr1/level2/2025W33_2C/l2b-v27-2026-228/6/<file>: the same key at IRSA and in the cloud
    camera: int          # 1..6
    mjd: float           # start of the exposure (Modified Julian Date)
    collection: str      # spherex_dr1, spherex_qr3, ...

    @property
    def version(self) -> int | None:
        m = _VERSION.search(self.file)
        return int(m.group(1)) if m else None


@dataclass
class PhotoList:
    ra: float
    dec: float
    photos: list[PhotoRef]
    fetched_at: float
    stale: bool = False

    @property
    def data_through(self) -> str | None:
        """Date of the newest photo, e.g. '2026-10-05'."""
        if not self.photos:
            return None
        return Time(max(p.mjd for p in self.photos), format="mjd").iso[:10]


def parse_sia_csv(text: str) -> list[PhotoRef]:
    """Rows of an SIA answer that are SPHEREx Level-2 science exposures."""
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        url = (row.get("access_url") or "").strip()
        collection = (row.get("obs_collection") or "").strip()
        if not collection.startswith("spherex") or "/level2/" not in url:
            continue
        if C.IRSA_DATA_PREFIX not in url:
            continue
        cam = _CAMERA.search(row.get("energy_bandpassname") or "")
        try:
            mjd = float(row["t_min"])
        except (KeyError, ValueError):
            continue
        if not cam:
            continue
        path = url.split(C.IRSA_DATA_PREFIX, 1)[1]
        out.append(PhotoRef(file=path.rsplit("/", 1)[-1], path=path, camera=int(cam.group(1)),
                            mjd=mjd, collection=collection))
    return out


def _ask(ra: float, dec: float, collection: str | None) -> list[PhotoRef]:
    params = {"POS": f"circle {ra:.6f} {dec:.6f} 0.0005", "RESPONSEFORMAT": "csv"}
    if collection:
        params["COLLECTION"] = collection
    r = http.get(SIA, service=SERVICE, params=params, timeout=C.PHOTO_LIST_TIMEOUT_S,
                 backoff=C.PHOTO_LIST_BACKOFF_S)
    return parse_sia_csv(r.text)


def query_archive(ra: float, dec: float) -> list[PhotoRef]:
    """Every SPHEREx exposure containing (ra, dec), all six cameras, oldest first."""
    photos: dict[str, PhotoRef] = {}
    failures = 0
    with ThreadPoolExecutor(len(C.SPHEREX_COLLECTIONS)) as pool:
        jobs = [pool.submit(_ask, ra, dec, name) for name in C.SPHEREX_COLLECTIONS]
        for job in jobs:
            try:
                for p in job.result():
                    photos[p.file] = p
            except ServiceDown:
                failures += 1
    if failures == len(C.SPHEREX_COLLECTIONS) or (failures and not photos):
        # collection names change with data releases: ask for everything and keep SPHEREx
        for p in _ask(ra, dec, None):
            photos[p.file] = p
    elif failures:
        raise ServiceDown(SERVICE, "part of the photo list did not arrive")
    return sorted(photos.values(), key=lambda p: (p.mjd, p.camera))


def list_photos(ra: float, dec: float, *, max_age_s: float = C.PHOTO_LIST_TTL_S) -> PhotoList:
    """The photo list for a place, from the cache when it is fresh enough."""
    ra, dec = float(ra) % 360.0, float(dec) + 0.0
    path = cache_dir() / "lists" / f"{ra:.4f}_{dec:+.4f}.json"
    cached = read_json(path)
    if cached and time.time() - cached.get("fetched_at", 0) < max_age_s:
        return _from_json(cached)
    try:
        photos = query_archive(ra, dec)
    except ServiceDown:
        if cached:
            stale = _from_json(cached)
            stale.stale = True
            return stale
        raise
    result = PhotoList(ra=ra, dec=dec, photos=photos, fetched_at=time.time())
    write_json(path, dict(ra=ra, dec=dec, fetched_at=result.fetched_at,
                          photos=[asdict(p) for p in photos]))
    return result


def _from_json(obj) -> PhotoList:
    return PhotoList(ra=obj["ra"], dec=obj["dec"], fetched_at=obj["fetched_at"],
                     photos=[PhotoRef(**p) for p in obj["photos"]])
