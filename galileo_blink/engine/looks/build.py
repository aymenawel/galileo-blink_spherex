"""Build one six-month view: a place in the sky, six cameras, every season SPHEREx has seen it.

`build_view` is the whole job: find the photos, fetch their cutouts, align and stack them per
camera and season, mark where the catalogues say moving objects should be, measure the central
object against that prediction, and write the pictures plus one `view.json` describing them.
"""
from __future__ import annotations

import hashlib
import io
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from astropy.time import Time

from .. import constants as C
from ..archive import photos as archive_photos
from ..archive.cache import atomic_write, cache_dir, write_json
from ..errors import NoCoverage, ServiceDown
from ..image import render
from ..image.frames import Frame, prepare
from ..image.grid import ViewGrid, view_grid
from ..image.measure import measure
from ..image.stack import change_map, combine
from ..sky import catalogues, targets
from ..sky.motion import Mover, offset_arcsec, predict, separation_arcsec
from . import astrometry as A
from .seasons import Season, choose, group_seasons

Progress = Callable[[str, float], None]
PIXEL_TO_MJY = (C.PIXEL_ARCSEC / 206264.806) ** 2 * 1e9
"""A fitted flux is in MJy/sr summed over pixels; times one pixel's solid angle gives mJy."""
TARGET_RADIUS_ARCSEC = 60.0       # a lone fast mover this close to the centre is the subject
CENTRAL_STAR_ARCSEC = 12.0        # otherwise the catalogued star this close to the centre is
STAR_OVERLAY_MAX = 250
STAR_OVERLAY_GMAG = 18.5


@dataclass(frozen=True)
class ViewRequest:
    ra: float
    dec: float
    size_deg: float = C.FIELD_DEFAULT_DEG
    per_look: int = C.LIVE_PHOTOS_PER_LOOK
    max_seasons: int = C.LIVE_MAX_SEASONS
    target_id: str | None = None          # one of NASA's five test targets
    label: str | None = None

    @property
    def key(self) -> str:
        """Names the view on disk and in URLs. Everything that changes the result is in it."""
        if self.target_id:
            return f"target-{self.target_id}"
        ra, dec = float(self.ra) % 360.0, float(self.dec) + 0.0
        text = (f"looks|{ra:.5f}|{dec:.5f}|{self.size_deg:.3f}|{self.per_look}|"
                f"{self.max_seasons}|{C.ENGINE_VERSION}")
        return hashlib.sha1(text.encode()).hexdigest()[:16]


def target_request(target_id: str, per_look: int = 6, max_seasons: int = 10) -> ViewRequest:
    t = targets.by_id(target_id)
    if t is None:
        raise KeyError(target_id)
    ra, dec = t.centre()
    return ViewRequest(ra=ra, dec=dec, per_look=per_look, max_seasons=max_seasons,
                       target_id=t.id, label=t.name)


def view_dir(key: str) -> Path:
    return cache_dir() / "views" / key


def _choose_subject(req: ViewRequest, gaia: list[Mover], movers: list[Mover], mjd: float
                    ) -> tuple[Mover | None, str]:
    """What the view measures, and why: "target" (a NASA test target), "mover" (the one fast
    catalogued object near the centre), "star" (the catalogued star at the centre) or "spot"
    (nothing catalogued there: the place itself)."""
    if req.target_id:
        return targets.by_id(req.target_id).mover, "target"
    near = [m for m in movers if m.catalog == "Gaia DR3"
            and separation_arcsec(*predict(m, mjd), req.ra, req.dec) <= TARGET_RADIUS_ARCSEC]
    if len(near) == 1:
        return near[0], "mover"
    central = [g for g in gaia
               if separation_arcsec(*predict(g, mjd), req.ra, req.dec) <= CENTRAL_STAR_ARCSEC]
    if central:
        return min(central, key=lambda g: g.gmag if g.gmag is not None else 99.0), "star"
    spot = Mover(name="This spot", catalog="none", source="the position you asked for",
                 ra=req.ra, dec=req.dec, epoch_mjd=mjd, pmra=0.0, pmdec=0.0)
    return spot, "spot"


def _marker(m: Mover, seasons: list[Season], grid: ViewGrid, is_subject: bool) -> dict:
    track = []
    for s in seasons:
        x, y = grid.sky_to_pixel(*predict(m, s.mjd))
        track.append(dict(season=s.index, x=round(x, 2), y=round(y, 2)))
    return dict(name=m.name, catalog=m.catalog, source=m.source, pm=round(m.pm_total, 3),
                pmra=round(m.pmra, 4), pmdec=round(m.pmdec, 4), parallax_mas=m.parallax_mas,
                gmag=m.gmag, subject=is_subject, track=track)


def _render_camera(cam: int, frames: list[Frame], out: Path,
                   stacks: dict[str, np.ndarray]) -> dict:
    """One camera's pictures: a stack per season, all seasons combined, and change maps."""
    lo_um, hi_um = C.CAMERA_BANDS_MICRON[cam]
    info: dict = dict(camera=cam, band=[lo_um, hi_um], looks=[])
    if not frames:
        info["empty"] = "no_photos"
        return info
    by_season: dict[int, list[Frame]] = {}
    for f in sorted(frames, key=lambda f: f.photo.mjd):
        by_season.setdefault(f.season, []).append(f)
    look_stack = {s: combine([f.view for f in fs]) for s, fs in by_season.items()}
    combined = combine([f.view for f in frames])
    limits = render.display_limits(combined)
    if limits is None:
        info["empty"] = "no_data"
        return info
    lo, hi = limits
    info["combined"] = f"c{cam}_all.png"
    atomic_write(out / info["combined"], render.gray_png(render.stretch(combined, lo, hi)))
    stacks[f"c{cam}_all"] = combined
    first = min(by_season)
    for s in sorted(by_season):
        fs = by_season[s]
        mjds = [f.photo.mjd for f in fs]
        lams = [float(f.photo.wavelength[f.photo.wavelength.shape[0] // 2,
                                         f.photo.wavelength.shape[1] // 2]) for f in fs]
        counts: dict[str, int] = {}
        for f in fs:
            for name, n in f.flag_counts.items():
                counts[name] = counts.get(name, 0) + n
        look = dict(season=s, png=f"c{cam}_s{s}.png", flags_png=None, change=None,
                    n_photos=len(fs), date=Time(float(np.median(mjds)), format="mjd").iso[:10],
                    mjd=round(float(np.median(mjds)), 4),
                    mjd_first=round(min(mjds), 4), mjd_last=round(max(mjds), 4),
                    wavelength=[round(min(lams), 3), round(max(lams), 3)],
                    files=[f.photo.ref.file for f in fs], flag_counts=counts)
        atomic_write(out / look["png"], render.gray_png(render.stretch(look_stack[s], lo, hi)))
        flagged = np.any([f.flagged for f in fs], axis=0)
        if flagged.any():
            look["flags_png"] = f"c{cam}_s{s}_flags.png"
            atomic_write(out / look["flags_png"], render.flags_png(flagged))
        if s != first:
            look["change"] = f"c{cam}_s{s}_change.png"
            atomic_write(out / look["change"],
                         render.change_png(change_map(look_stack[s], look_stack[first], combined)))
        stacks[f"c{cam}_s{s}"] = look_stack[s]
        info["looks"].append(look)
    return info


def build_view(req: ViewRequest, progress: Progress = lambda stage, fraction: None) -> dict:
    """Build the view and return its description (also written to <view_dir>/view.json)."""
    started = time.time()
    progress("Asking NASA's archive which photos cover this place", 0.03)
    listing = archive_photos.list_photos(req.ra, req.dec)
    list_s = time.time() - started
    if not listing.photos:
        raise NoCoverage("SPHEREx has no photos of this place yet. It maps the whole sky every "
                         "six months, so this is unexpected: check the coordinates.")
    all_seasons = group_seasons(listing.photos)
    seasons, seasons_left_out = choose(all_seasons, req.per_look, req.max_seasons, C.LIVE_MAX_PHOTOS)
    jobs = [(ref, s.index) for s in seasons for refs in s.by_camera.values() for ref in refs]
    grid = view_grid(req.ra, req.dec, req.size_deg)
    mid_mjd = float(np.median([ref.mjd for ref, _ in jobs]))

    # The catalogues are asked while the photos download: the pictures never wait for them.
    radius = req.size_deg * 0.75
    side = ThreadPoolExecutor(2)
    gaia_job = side.submit(catalogues.gaia_cone, req.ra, req.dec, radius)
    catwise_job = side.submit(catalogues.catwise_cone, req.ra, req.dec, radius)

    progress(f"Fetching {len(jobs)} photos from NASA", 0.08)
    t_fetch = time.time()
    frames: list[Frame] = []
    left_out: list[dict] = []
    done = 0
    with ThreadPoolExecutor(C.DOWNLOAD_WORKERS) as pool:
        for result in pool.map(lambda job: prepare(job[0], job[1], req.ra, req.dec, req.size_deg, grid), jobs):
            done += 1
            if isinstance(result, Frame):
                frames.append(result)
            else:
                left_out.append(result)
            if done % 4 == 0 or done == len(jobs):
                progress(f"Fetching photos from NASA ({done} of {len(jobs)})",
                         0.08 + 0.57 * done / len(jobs))
    fetch_s = time.time() - t_fetch
    if not frames:
        if any(d["reason"] == "not_received" for d in left_out):
            raise ServiceDown("NASA's image archive", "none of the photos arrived")
        raise NoCoverage("SPHEREx's photos of this place could not be used "
                         "(they only graze it, or their astrometry is marked poor).")

    degraded = []
    gaia: list[Mover] = []
    catwise: list[Mover] = []
    try:
        gaia = gaia_job.result()
    except Exception:                     # noqa: BLE001 - the catalogue is optional
        degraded.append("gaia")
    try:
        catwise = catwise_job.result()
    except Exception:                     # noqa: BLE001
        degraded.append("catwise")
    side.shutdown(wait=False)
    if listing.stale:
        degraded.append("photo_list")
    if any(d["reason"] == "not_received" for d in left_out):
        degraded.append("photos")

    progress("Stacking each camera's seasons", 0.68)
    t_render = time.time()
    out = view_dir(req.key)
    out.mkdir(parents=True, exist_ok=True)
    stacks: dict[str, np.ndarray] = {}
    cameras = {str(cam): _render_camera(cam, [f for f in frames if f.photo.camera == cam],
                                        out, stacks) for cam in range(1, 7)}
    buf = io.BytesIO()                    # kept so any two dates can be added or subtracted later
    np.savez_compressed(buf, **stacks)
    atomic_write(out / "stacks.npz", buf.getvalue())

    render_s = time.time() - t_render
    progress("Measuring against the star catalogue", 0.80)
    t_measure = time.time()
    movers = catalogues.fast_movers(gaia, catwise)
    subject, subject_kind = _choose_subject(req, gaia, movers, mid_mjd)
    references = A.pick_reference_stars(gaia, [subject] if subject else [], mid_mjd)

    def analyse(frame: Frame):
        reg, ref_meas = A.register(frame.photo, references)
        return frame, reg, ref_meas, measure(frame.photo, *predict(subject, frame.photo.mjd))

    with ThreadPoolExecutor(8) as pool:
        analysed = list(pool.map(analyse, frames))

    sightings: list[A.Sighting] = []
    reg_errors: dict[tuple[int, int], list[float]] = {}
    ref_sightings: dict[int, dict[int, dict[int, list[A.Sighting]]]] = {}
    brightness, contaminated = [], 0
    for frame, reg, ref_meas, m in analysed:
        cam, season = frame.photo.camera, frame.season
        reg_errors.setdefault((cam, season), []).append(reg.error)
        for i, rm in ref_meas.items():
            ref_sightings.setdefault(cam, {}).setdefault(i, {}).setdefault(season, []).append(
                A.corrected(rm, reg, season))
        if not m.has_position:
            continue
        s = A.corrected(m, reg, season)
        sightings.append(s)
        off = math.hypot(s.east, s.north)
        if (subject_kind != "spot" and m.status == "ok" and (m.snr or 0) >= C.MIN_MEASURE_SNR
                and off > C.MAX_TRACK_OFFSET_ARCSEC):
            contaminated += 1             # confident light that is NOT on the predicted path
            continue
        brightness.append(dict(camera=cam, season=season, mjd=round(m.mjd, 4),
                               wavelength=round(m.wavelength, 4) if m.wavelength else None,
                               flux_mjy=None if m.flux is None else round(m.flux * PIXEL_TO_MJY, 4),
                               snr=None if m.snr is None else round(m.snr, 1), status=m.status))
    look_reg_error = {k: float(np.median(v)) / math.sqrt(len(v)) for k, v in reg_errors.items()}
    reference_looks = {cam: {i: {s: A.look_position(g, look_reg_error.get((cam, s), 0.0))
                                 for s, g in per.items()} for i, per in stars.items()}
                       for cam, stars in ref_sightings.items()}

    motion, per_camera, reason, looks = None, {}, None, {}
    if subject_kind == "spot":
        reason = "catalogue_down" if "gaia" in degraded else "no_target"
    else:
        motion, per_camera, reason, looks = A.measure_motion(subject, sightings, look_reg_error,
                                                             reference_looks)
    measure_s = time.time() - t_measure

    # the predicted path, for drawing: offsets from where the subject is at the first season
    path = []
    if subject and len(seasons) >= 1:
        t0, t1 = seasons[0].mjd, seasons[-1].mjd
        origin = predict(subject, t0)
        for mjd in np.linspace(t0, t1, max(2, int((t1 - t0) / 7) + 1)):
            e, n = offset_arcsec(*origin, *predict(subject, float(mjd)))
            path.append(dict(mjd=round(float(mjd), 2), east=round(e, 3), north=round(n, 3)))

    shown = ([subject] if subject and subject_kind != "spot" else []) + [m for m in movers if m is not subject]
    n_ref = [reg.n_stars for _, reg, _, _ in analysed]
    star_dots = []
    for g in sorted((g for g in gaia if g.gmag is not None and g.gmag <= STAR_OVERLAY_GMAG),
                    key=lambda g: g.gmag)[:STAR_OVERLAY_MAX]:
        x, y = grid.sky_to_pixel(*predict(g, mid_mjd))
        if -0.5 < x < grid.n - 0.5 and -0.5 < y < grid.n - 0.5:
            star_dots.append([round(x, 1), round(y, 1), round(g.gmag, 1)])

    target = targets.by_id(req.target_id) if req.target_id else None
    view = dict(
        kind="looks", engine=C.ENGINE_VERSION, key=req.key,
        ra=req.ra, dec=req.dec, size_deg=req.size_deg, n=grid.n, pixel_arcsec=C.PIXEL_ARCSEC,
        upscale=C.DISPLAY_UPSCALE, label=req.label,
        target=dict(id=target.id, name=target.name, kind=target.kind, blurb=target.blurb) if target else None,
        built_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        data_through=listing.data_through, photos_in_archive=len(listing.photos),
        seasons=[dict(index=s.index, label=s.label, date=s.date, mjd=round(s.mjd, 3)) for s in seasons],
        seasons_left_out=seasons_left_out, cameras=cameras,
        subject=dict(kind=subject_kind, name=subject.name, catalog=subject.catalog,
                     source=subject.source, pm=round(subject.pm_total, 4),
                     pmra=round(subject.pmra, 4), pmdec=round(subject.pmdec, 4),
                     parallax_mas=subject.parallax_mas, gmag=subject.gmag),
        markers=[_marker(m, seasons, grid, m is subject) for m in shown[:C.MAX_MARKERS]],
        markers_left_out=max(0, len(shown) - C.MAX_MARKERS),
        stars=star_dots,
        motion=motion.to_dict() if motion else None,
        motion_reason=reason, motion_reason_text=A.REASONS.get(reason) if reason else None,
        motion_by_camera={str(c): m.to_dict() for c, m in per_camera.items()},
        # cameras are combined only when they compared the same two seasons as the best one
        motion_combined=A.combine_cameras({c: m for c, m in per_camera.items() if motion and
                                           (m.first_season, m.last_season)
                                           == (motion.first_season, motion.last_season)}),
        track={str(cam): [dict(season=s, mjd=round(lp.mjd, 3), east=round(lp.east, 3),
                               north=round(lp.north, 3), error=round(lp.error, 3), n=lp.n,
                               snr=round(lp.snr, 1)) for s, lp in sorted(ls.items())]
               for cam, ls in looks.items()},
        path=path,
        brightness=brightness, brightness_left_out=contaminated,
        reference_stars=dict(available=len(references), median_used=int(np.median(n_ref)) if n_ref else 0),
        left_out=left_out, degraded=sorted(set(degraded)),
        versions=sorted({f.photo.ref.version for f in frames if f.photo.ref.version}),
        stats=dict(total_s=round(time.time() - started, 1), list_s=round(list_s, 1),
                   fetch_s=round(fetch_s, 1), render_s=round(render_s, 1),
                   measure_s=round(measure_s, 1),
                   photos_used=len(frames), photos_asked=len(jobs),
                   mb_downloaded=round(sum(f.photo.bytes_read for f in frames) / 1e6, 1),
                   from_cloud=sum(1 for f in frames if f.photo.source == "cloud"),
                   from_irsa=sum(1 for f in frames if f.photo.source == "irsa"),
                   from_disk=sum(1 for f in frames if f.photo.source == "disk")),
    )
    write_json(out / "view.json", view)
    progress("Done", 1.0)
    return view
