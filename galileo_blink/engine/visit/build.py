"""Build one visit view: a place, one camera, a few days, moment by moment. The asteroid mode.

Where the six-month view stacks each season to show slow movers, this view keeps every moment
of one visit apart, subtracts the sky that stays put, and looks for what is left moving along
a straight path. Catalogued asteroids are named; anything else is reported as unidentified,
with how sure the search is.
"""
from __future__ import annotations

import hashlib
import io
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import numpy as np
from astropy.time import Time

from .. import constants as C
from ..archive import photos as archive_photos
from ..archive.cache import atomic_write, cache_dir, write_json
from ..archive.photos import PhotoRef
from ..errors import NoCoverage, ServiceDown
from ..image import render
from ..image.frames import Frame, prepare
from ..image.grid import ViewGrid, view_grid
from ..image.stack import combine
from ..sky import asteroids
from ..sky.motion import separation_arcsec
from .detect import Track, find_movers

Progress = Callable[[str, float], None]
NAME_MIN_MATCHES = 2              # a track is named only if it matches in two moments


@dataclass(frozen=True)
class VisitRequest:
    ra: float
    dec: float
    size_deg: float = 0.2
    camera: int | None = None         # None: the camera with the most moments
    mjd_start: float | None = None    # None: the best visit is chosen
    mjd_end: float | None = None
    label: str | None = None

    @property
    def key(self) -> str:
        ra, dec = float(self.ra) % 360.0, float(self.dec) + 0.0
        text = (f"visit|{ra:.5f}|{dec:.5f}|{self.size_deg:.3f}|{self.camera}|"
                f"{self.mjd_start}|{self.mjd_end}|{C.ENGINE_VERSION}")
        return "v" + hashlib.sha1(text.encode()).hexdigest()[:15]


def moments_of(mjds: list[float]) -> list[list[int]]:
    """Indices of photos grouped into moments (photos within MOMENT_GAP_DAYS of the previous)."""
    order = sorted(range(len(mjds)), key=lambda i: mjds[i])
    groups: list[list[int]] = []
    for i in order:
        if groups and mjds[i] - mjds[groups[-1][-1]] <= C.MOMENT_GAP_DAYS:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def choose_visit(photos: list[PhotoRef], camera: int | None, start: float | None, end: float | None
                 ) -> tuple[int, list[PhotoRef]]:
    """(camera, photos) of the visit to show: the asked window, or else the stretch of at most
    VISIT_MAX_DAYS with the most separate moments (ties: the most recent)."""
    best = None
    for cam in ([camera] if camera else range(1, 7)):
        rows = sorted((p for p in photos if p.camera == cam), key=lambda p: p.mjd)
        if start is not None and end is not None:
            rows = [p for p in rows if start <= p.mjd <= end]
            windows = [rows] if rows else []
        else:
            windows = []
            for i in range(len(rows)):
                window = [p for p in rows[i:] if p.mjd - rows[i].mjd <= C.VISIT_MAX_DAYS]
                windows.append(window)
        for window in windows:
            n_moments = len(moments_of([p.mjd for p in window]))
            rank = (min(n_moments, 12), window[0].mjd)
            if best is None or rank > best[0]:
                best = (rank, cam, window)
    if best is None or best[0][0] < 1:
        raise NoCoverage("SPHEREx has no photos of this place in that camera and time.")
    return best[1], best[2]


def thin(photos: list[PhotoRef], limit: int) -> list[PhotoRef]:
    """At most `limit` photos, keeping every moment represented where possible."""
    if len(photos) <= limit:
        return photos
    groups = moments_of([p.mjd for p in photos])
    per = max(1, limit // len(groups))
    kept = [photos[i] for g in groups for i in g[:per]]
    return sorted(kept, key=lambda p: p.mjd)[:limit]


def _name_tracks(tracks: list[Track], known: list[list[asteroids.KnownObject]], grid: ViewGrid) -> None:
    """Give a track a catalogued asteroid's name when it lies on that asteroid's predicted
    position in at least NAME_MIN_MATCHES moments."""
    for t in tracks:
        votes: dict[str, int] = {}
        for d in t.detections:
            ra, dec = grid.pixel_to_sky(d.x, d.y)
            for obj in known[d.moment]:
                if separation_arcsec(ra, dec, obj.ra, obj.dec) <= C.ASTEROID_MATCH_ARCSEC:
                    votes[obj.name] = votes.get(obj.name, 0) + 1
        if votes:
            name, n = max(votes.items(), key=lambda kv: kv[1])
            if n >= NAME_MIN_MATCHES:
                t.name = name
                t.confidence = "strong"         # the catalogue independently confirms it


def build_visit(req: VisitRequest, progress: Progress = lambda stage, fraction: None) -> dict:
    """Build the visit view and return its description (also written to view.json)."""
    started = time.time()
    progress("Asking NASA's archive which photos cover this place", 0.03)
    listing = archive_photos.list_photos(req.ra, req.dec)
    if not listing.photos:
        raise NoCoverage("SPHEREx has no photos of this place yet.")
    camera, chosen = choose_visit(listing.photos, req.camera, req.mjd_start, req.mjd_end)
    chosen = thin(chosen, C.VISIT_MAX_PHOTOS)
    grid = view_grid(req.ra, req.dec, req.size_deg)

    progress(f"Fetching {len(chosen)} photos from NASA", 0.08)
    frames: list[Frame] = []
    left_out: list[dict] = []
    done = 0
    with ThreadPoolExecutor(C.DOWNLOAD_WORKERS) as pool:
        for result in pool.map(lambda ref: prepare(ref, 0, req.ra, req.dec, req.size_deg, grid), chosen):
            done += 1
            (frames if isinstance(result, Frame) else left_out).append(result)
            progress(f"Fetching photos from NASA ({done} of {len(chosen)})",
                     0.08 + 0.6 * done / len(chosen))
    if not frames:
        if any(d["reason"] == "not_received" for d in left_out):
            raise ServiceDown("NASA's image archive", "none of the photos arrived")
        raise NoCoverage("SPHEREx's photos of this place in that visit could not be used.")
    frames.sort(key=lambda f: f.photo.mjd)
    groups = moments_of([f.photo.mjd for f in frames])
    for k, g in enumerate(groups):
        for i in g:
            frames[i].season = k
    moment_frames = [[frames[i] for i in g] for g in groups]
    mjds = [float(np.mean([f.photo.mjd for f in fs])) for fs in moment_frames]
    days = [m - mjds[0] for m in mjds]
    images = [combine([f.view for f in fs]) for fs in moment_frames]

    progress("Subtracting the sky that stays put", 0.72)
    tracks, sky, maps = find_movers(images, days)

    progress("Checking the asteroid catalogue", 0.82)
    degraded = ["photo_list"] if listing.stale else []
    if any(d["reason"] == "not_received" for d in left_out):
        degraded.append("photos")
    radius = req.size_deg * 0.75

    def ask(mjd: float):
        try:
            return asteroids.skybot(req.ra, req.dec, radius, mjd)
        except Exception:                       # noqa: BLE001 - the catalogue is optional
            return None

    with ThreadPoolExecutor(4) as pool:
        answers = list(pool.map(ask, mjds))
    if any(a is None for a in answers):
        degraded.append("asteroid_catalogue")
    known = [a or [] for a in answers]
    _name_tracks(tracks, known, grid)

    out = cache_dir() / "views" / req.key
    out.mkdir(parents=True, exist_ok=True)
    reference = sky if len(images) >= C.VISIT_MIN_MOMENTS else combine(images)
    limits = render.display_limits(reference)
    lo, hi = limits if limits else (0.0, 1.0)
    atomic_write(out / f"c{camera}_all.png", render.gray_png(render.stretch(reference, lo, hi)))
    stacks = {f"c{camera}_all": reference}
    looks = []
    for k, (fs, image) in enumerate(zip(moment_frames, images)):
        counts: dict[str, int] = {}
        for f in fs:
            for name, n in f.flag_counts.items():
                counts[name] = counts.get(name, 0) + n
        lams = [float(f.photo.wavelength[f.photo.wavelength.shape[0] // 2,
                                         f.photo.wavelength.shape[1] // 2]) for f in fs]
        look = dict(season=k, png=f"c{camera}_s{k}.png", flags_png=None, change=None,
                    n_photos=len(fs), date=Time(mjds[k], format="mjd").iso[:16],
                    mjd=round(mjds[k], 5), mjd_first=round(fs[0].photo.mjd, 5),
                    mjd_last=round(fs[-1].photo.mjd, 5),
                    wavelength=[round(min(lams), 3), round(max(lams), 3)],
                    files=[f.photo.ref.file for f in fs], flag_counts=counts)
        atomic_write(out / look["png"], render.gray_png(render.stretch(image, lo, hi)))
        flagged = np.any([f.flagged for f in fs], axis=0)
        if flagged.any():
            look["flags_png"] = f"c{camera}_s{k}_flags.png"
            atomic_write(out / look["flags_png"], render.flags_png(flagged))
        if maps:
            look["change"] = f"c{camera}_s{k}_change.png"
            atomic_write(out / look["change"], render.change_png(maps[k]))
        stacks[f"c{camera}_s{k}"] = image
        looks.append(look)
    buf = io.BytesIO()
    np.savez_compressed(buf, **stacks)
    atomic_write(out / "stacks.npz", buf.getvalue())

    cameras = {str(c): dict(camera=c, band=list(C.CAMERA_BANDS_MICRON[c]), looks=[],
                            empty="not_in_visit") for c in range(1, 7)}
    cameras[str(camera)] = dict(camera=camera, band=list(C.CAMERA_BANDS_MICRON[camera]),
                                combined=f"c{camera}_all.png", looks=looks)

    # catalogued asteroids: where each should be at every moment, and whether it was found
    by_name: dict[str, dict] = {}
    for k, objs in enumerate(known):
        for obj in objs:
            x, y = grid.sky_to_pixel(obj.ra, obj.dec)
            entry = by_name.setdefault(obj.name, dict(name=obj.name, number=obj.number,
                                                      catalog="SkyBoT (IMCCE)", vmag=obj.vmag,
                                                      kind=obj.kind, track=[]))
            entry["track"].append(dict(season=k, x=round(x, 2), y=round(y, 2)))
    found_names = {t.name for t in tracks if t.name}
    known_out = []
    for entry in sorted(by_name.values(), key=lambda e: e["vmag"]):
        inside = [p for p in entry["track"]
                  if -0.5 <= p["x"] < grid.n - 0.5 and -0.5 <= p["y"] < grid.n - 0.5]
        # in view AND searchable: the leftover map has data there at that moment
        searchable = [p for p in inside if maps and np.isfinite(
            maps[p["season"]][int(round(p["y"])), int(round(p["x"]))])]
        entry["found"] = entry["name"] in found_names
        entry["moments_in_view"] = len(searchable)
        if entry["found"]:
            entry["note"] = "found"
        elif len(searchable) < C.VISIT_MIN_MOMENTS:
            entry["note"] = "in_view_too_briefly"
        elif entry["vmag"] > C.ASTEROID_FAINT_VMAG:
            entry["note"] = "too_faint"
        else:
            entry["note"] = "missed"
        if inside:
            known_out.append(entry)

    def track_out(i: int, t: Track) -> dict:
        return dict(id=i, name=t.name, confidence=t.confidence,
                    speed_arcsec_per_hour=round(t.speed_arcsec_per_hour, 2),
                    direction_deg=round(t.direction_deg, 1), rms_px=round(t.rms_px, 2),
                    n_moments=len({d.moment for d in t.detections}),
                    points=[dict(season=d.moment, x=round(d.x, 2), y=round(d.y, 2),
                                 significance=round(d.significance, 1)) for d in t.detections],
                    path=[dict(season=k, x=round(t.position(days[k])[0], 2),
                               y=round(t.position(days[k])[1], 2)) for k in range(len(days))])

    span_h = (mjds[-1] - mjds[0]) * 24.0
    view = dict(
        kind="visit", engine=C.ENGINE_VERSION, key=req.key, ra=req.ra, dec=req.dec,
        size_deg=req.size_deg, n=grid.n, pixel_arcsec=C.PIXEL_ARCSEC, upscale=render.upscale_for(grid.n),
        label=req.label, target=None, camera=camera,
        built_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        data_through=listing.data_through, photos_in_archive=len(listing.photos),
        seasons=[dict(index=k, label=Time(m, format="mjd").datetime.strftime("%d %b %H:%M"),
                      date=Time(m, format="mjd").iso[:16], mjd=round(m, 5)) for k, m in enumerate(mjds)],
        seasons_left_out=0, span_hours=round(span_h, 1), cameras=cameras,
        tracks=[track_out(i, t) for i, t in enumerate(tracks)],
        known_asteroids=known_out, markers=[], stars=[],
        search=dict(searched=len(images) >= C.VISIT_MIN_MOMENTS, moments=len(images),
                    min_moments=C.VISIT_MIN_MOMENTS, faint_vmag=C.ASTEROID_FAINT_VMAG,
                    detect_sigma=C.VISIT_DETECT_SIGMA),
        left_out=left_out, degraded=sorted(set(degraded)),
        versions=sorted({f.photo.ref.version for f in frames if f.photo.ref.version}),
        stats=dict(total_s=round(time.time() - started, 1), photos_used=len(frames),
                   photos_asked=len(chosen),
                   mb_downloaded=round(sum(f.photo.bytes_read for f in frames) / 1e6, 1)),
    )
    write_json(out / "view.json", view)
    progress("Done", 1.0)
    return view
