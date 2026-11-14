"""Measured motion versus catalogue motion, with error bars that the view measures for itself.

Every photo's sky mapping is slightly off (around an arcsecond). The ordinary Gaia stars in
the same photo tell us by how much, so each photo is first corrected with them
("registration"). The same stars then give the honest error: after correction, stars that do
not move still appear to shift a little between looks, and that shift is the floor below which
no motion can be claimed in this view.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .. import constants as C
from ..archive.store import Photo
from ..image.measure import Measurement, measure_many
from ..image.stack import MAD_TO_SIGMA
from ..sky.motion import Mover, predict, predicted_displacement, separation_arcsec

REF_MAX_STARS = 8
REF_GMAG_RANGE = (9.5, 17.0)      # brighter saturates SPHEREx; fainter is too noisy to anchor on
REF_MIN_SNR = 12.0
REF_MAX_OFFSET_ARCSEC = 6.0       # further than a pixel from its catalogue place: a mismatch
REF_ISOLATION_ARCSEC = 20.0       # no comparably bright neighbour inside ~3 pixels
REF_MIN_STARS = 3
CENTROID_ERROR_FACTOR = 5.3       # arcsec x S/N: one photo's position error for an 8" star image
SATURATED_SNR = 1000.0            # a saturated star is certainly detected
AGREE_FACTOR = 2.45
"""Measured and predicted motion "agree" when their vector difference is within 2.45 x the
per-axis error: the 95% radius of a two-dimensional Gaussian."""


@dataclass
class Registration:
    """How far one photo's sky mapping is off, from its reference stars (arcsec)."""
    east: float = 0.0
    north: float = 0.0
    error: float = C.ASTROMETRY_FLOOR_ARCSEC      # per axis
    n_stars: int = 0

    @property
    def measured(self) -> bool:
        return self.n_stars >= REF_MIN_STARS


def pick_reference_stars(gaia: list[Mover], avoid: list[Mover], mjd: float) -> list[Mover]:
    """Isolated Gaia stars of suitable brightness, brightest first. Fast movers are fine: each
    star's own catalogue motion is applied when it is used."""
    lo, hi = REF_GMAG_RANGE
    pos = {id(g): predict(g, mjd) for g in gaia}
    avoid_pos = [predict(a, mjd) for a in avoid]
    out = []
    for g in sorted((g for g in gaia if g.gmag is not None and lo <= g.gmag <= hi),
                    key=lambda g: g.gmag):
        here = pos[id(g)]
        if any(separation_arcsec(*here, *p) < REF_ISOLATION_ARCSEC for p in avoid_pos):
            continue
        crowded = any(o is not g and o.gmag is not None and o.gmag < g.gmag + 2.5
                      and separation_arcsec(*here, *pos[id(o)]) < REF_ISOLATION_ARCSEC
                      for o in gaia)
        if not crowded:
            out.append(g)
        if len(out) >= REF_MAX_STARS:
            break
    return out


def _robust_sigma(values: np.ndarray) -> float:
    return float(MAD_TO_SIGMA * np.median(np.abs(values - np.median(values))))


def register(photo: Photo, references: list[Mover]) -> tuple[Registration, dict[int, Measurement]]:
    """The photo's offset from its reference stars, and each star's own measurement
    (keyed by its index in `references`)."""
    good: dict[int, Measurement] = {}
    measured = measure_many(photo, [predict(star, photo.mjd) for star in references])
    for i, m in enumerate(measured):
        if (m.status == "ok" and m.snr and m.snr >= REF_MIN_SNR
                and math.hypot(m.east, m.north) <= REF_MAX_OFFSET_ARCSEC):
            good[i] = m
    if len(good) < REF_MIN_STARS:
        return Registration(), good
    east = np.array([m.east for m in good.values()])
    north = np.array([m.north for m in good.values()])
    scatter = math.hypot(_robust_sigma(east), _robust_sigma(north)) / math.sqrt(2.0)
    error = max(1.2533 * scatter / math.sqrt(len(good)), 0.02)       # error of a median
    return Registration(float(np.median(east)), float(np.median(north)), error, len(good)), good


@dataclass
class Sighting:
    """One object in one photo, after the photo's registration was removed."""
    camera: int
    season: int
    mjd: float
    east: float                   # corrected offset from the catalogue position, arcsec
    north: float
    snr: float | None
    status: str


@dataclass
class LookPosition:
    """An object's position in one camera's look: the median of its sightings."""
    camera: int
    season: int
    mjd: float
    east: float
    north: float
    error: float                  # per axis, arcsec
    n: int
    snr: float


def corrected(m: Measurement, reg: Registration, season: int) -> Sighting:
    snr = SATURATED_SNR if m.status == "saturated" else m.snr
    return Sighting(camera=m.camera, season=season, mjd=m.mjd, east=m.east - reg.east,
                    north=m.north - reg.north, snr=snr, status=m.status)


def look_position(sightings: list[Sighting], registration_error: float) -> LookPosition:
    """The median position of one look, with a per-axis error: the scatter between its photos
    when there are enough to measure it, never below what the photos' own limits allow."""
    east = np.array([s.east for s in sightings])
    north = np.array([s.north for s in sightings])
    snr = float(np.median([s.snr or 0.0 for s in sightings]))
    n = len(sightings)
    floors = [C.PHOTO_POSITION_FLOOR_ARCSEC.get(s.status, 1.0) for s in sightings]
    per_photo = max(CENTROID_ERROR_FACTOR / max(snr, 1.0), float(np.median(floors)))
    stat = per_photo / math.sqrt(n)
    if n >= 3:
        scatter = math.hypot(_robust_sigma(east), _robust_sigma(north)) / math.sqrt(2.0)
        stat = max(1.2533 * scatter / math.sqrt(n), C.PHOTO_POSITION_FLOOR_ARCSEC["ok"] / math.sqrt(n))
    return LookPosition(camera=sightings[0].camera, season=sightings[0].season,
                        mjd=float(np.median([s.mjd for s in sightings])),
                        east=float(np.median(east)), north=float(np.median(north)),
                        error=math.hypot(stat, registration_error), n=n, snr=snr)


def static_floor(reference_looks: dict[int, dict[int, LookPosition]], a: int, b: int) -> tuple[float | None, int]:
    """Per-axis scatter (arcsec) of the apparent shift of reference stars between seasons a
    and b, and how many stars it rests on. None with fewer than 4 stars."""
    shifts = []
    for looks in reference_looks.values():
        if a in looks and b in looks:
            shifts += [looks[b].east - looks[a].east, looks[b].north - looks[a].north]
    n = len(shifts) // 2
    if n < 4:
        return None, n
    v = np.array(shifts)
    return float(MAD_TO_SIGMA * np.median(np.abs(v))) * math.sqrt(n / (n - 1.0)), n


@dataclass
class Motion:
    camera: int
    first_season: int
    last_season: int
    years: float
    same_time_of_year: bool       # parallax cancels in the comparison
    measured: float               # arcsec moved between the two looks
    measured_east: float
    measured_north: float
    predicted: float              # what the catalogue predicts for the same dates
    predicted_east: float
    predicted_north: float
    error: float                  # per-axis one-sigma error on the measured motion
    residual: float               # length of (measured - predicted), arcsec
    agrees: bool
    floor: float | None           # how far stars that do not move appear to shift here
    n_reference_stars: int

    def to_dict(self) -> dict:
        return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def _same_time_of_year(days: float) -> bool:
    r = days % 365.25
    return days >= C.MIN_PAIR_DAYS and min(r, 365.25 - r) <= C.SAME_SEASON_DAYS


REASONS = {
    "no_target": "There is no single catalogued moving object at the centre of this view to measure.",
    "catalogue_down": "The star catalogue did not answer, so there is no predicted motion to compare with.",
    "one_season": "SPHEREx has photographed this place in only one season so far; motion needs two.",
    "too_faint": "It is too faint in single photos for a reliable position.",
    "off_track": "No camera saw it on its predicted path; what sits there is probably a different object.",
}


def camera_motion(target: Mover, looks: dict[int, LookPosition],
                  reference_looks: dict[int, dict[int, LookPosition]]) -> Motion | None:
    """Motion from one camera's looks (season -> position), or None with fewer than two."""
    order = sorted(looks)
    if len(order) < 2:
        return None
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]
             if _same_time_of_year(looks[b].mjd - looks[a].mjd)]
    same = bool(pairs)
    a, b = (max(pairs, key=lambda p: looks[p[1]].mjd - looks[p[0]].mjd) if pairs
            else (order[0], order[-1]))
    A, B = looks[a], looks[b]
    pe, pn = predicted_displacement(target, A.mjd, B.mjd)
    re, rn = B.east - A.east, B.north - A.north             # measured minus predicted
    floor, n_ref = static_floor(reference_looks, a, b)
    floor_used = floor if floor is not None else C.ASTROMETRY_FLOOR_ARCSEC
    error = math.sqrt(A.error ** 2 + B.error ** 2 + floor_used ** 2 + C.SYSTEMATIC_FLOOR_ARCSEC ** 2)
    residual = math.hypot(re, rn)
    return Motion(camera=A.camera, first_season=a, last_season=b,
                  years=(B.mjd - A.mjd) / 365.25, same_time_of_year=same,
                  measured=math.hypot(pe + re, pn + rn), measured_east=pe + re,
                  measured_north=pn + rn, predicted=math.hypot(pe, pn), predicted_east=pe,
                  predicted_north=pn, error=error, residual=residual,
                  agrees=residual <= AGREE_FACTOR * error, floor=floor, n_reference_stars=n_ref)


def measure_motion(target: Mover, sightings: list[Sighting],
                   registration_error: dict[tuple[int, int], float],
                   reference_looks: dict[int, dict[int, dict[int, LookPosition]]]
                   ) -> tuple[Motion | None, dict[int, Motion], str | None, dict[int, dict[int, LookPosition]]]:
    """(best motion, motion per camera, reason code if none, look positions per camera).

    `registration_error[(camera, season)]` is that look's registration error;
    `reference_looks[camera][star][season]` are the reference stars' own look positions."""
    if len({s.season for s in sightings}) < 2:
        return None, {}, "one_season", {}
    positional = [s for s in sightings if s.status in ("ok", "partial", "saturated")]
    if not positional:
        return None, {}, "too_faint", {}
    by_look: dict[tuple[int, int], list[Sighting]] = {}
    for s in positional:
        by_look.setdefault((s.camera, s.season), []).append(s)
    looks: dict[int, dict[int, LookPosition]] = {}
    for (cam, season), group in by_look.items():
        looks.setdefault(cam, {})[season] = look_position(
            group, registration_error.get((cam, season), C.ASTROMETRY_FLOOR_ARCSEC))
    detected = {cam: {s: lp for s, lp in ls.items() if lp.snr >= C.MIN_MEASURE_SNR}
                for cam, ls in looks.items()}
    if not any(len(ls) >= 2 for ls in detected.values()):
        return None, {}, "too_faint", looks
    # Only looks where the object sits on its predicted path count. A confident position that
    # does not follow the prediction is a different object (a static neighbour), or the target
    # blended with one it is passing.
    on_track = {cam: {s: lp for s, lp in ls.items()
                      if math.hypot(lp.east, lp.north) <= C.MAX_TRACK_OFFSET_ARCSEC}
                for cam, ls in detected.items()}
    on_track = {cam: ls for cam, ls in on_track.items() if len(ls) >= 2}
    if not on_track:
        return None, {}, "off_track", looks
    motions = {}
    for cam, ls in on_track.items():
        m = camera_motion(target, ls, reference_looks.get(cam, {}))
        if m:
            motions[cam] = m
    if not motions:
        return None, {}, "one_season", looks
    best = min(motions.values(), key=lambda m: (not m.same_time_of_year, m.error, -m.years))
    return best, motions, None, looks


def combine_cameras(motions: dict[int, Motion]) -> dict | None:
    """All cameras' measurements as one: each camera is an independent instrument, so their
    (measured - predicted) vectors are averaged, weighted by their errors. None unless at
    least two cameras measured the motion."""
    if len(motions) < 2:
        return None
    ms = list(motions.values())
    w = np.array([1.0 / m.error ** 2 for m in ms])
    res_e = float(np.sum(w * [m.measured_east - m.predicted_east for m in ms]) / w.sum())
    res_n = float(np.sum(w * [m.measured_north - m.predicted_north for m in ms]) / w.sum())
    pred_e = float(np.sum(w * [m.predicted_east for m in ms]) / w.sum())
    pred_n = float(np.sum(w * [m.predicted_north for m in ms]) / w.sum())
    # averaging beats down each camera's own noise, but not what the cameras share
    error = math.hypot(float(1.0 / math.sqrt(w.sum())), C.SYSTEMATIC_FLOOR_ARCSEC)
    residual = math.hypot(res_e, res_n)
    floors = [m.floor for m in ms if m.floor is not None]
    return dict(cameras=sorted(motions), n_cameras=len(ms),
                first_season=ms[0].first_season, last_season=ms[0].last_season,
                floor=round(float(np.median(floors)), 3) if floors else None,
                n_reference_stars=max(m.n_reference_stars for m in ms),
                measured=round(math.hypot(pred_e + res_e, pred_n + res_n), 3),
                measured_east=round(pred_e + res_e, 3), measured_north=round(pred_n + res_n, 3),
                predicted=round(math.hypot(pred_e, pred_n), 3),
                predicted_east=round(pred_e, 3), predicted_north=round(pred_n, 3),
                error=round(error, 3), residual=round(residual, 3),
                agrees=bool(residual <= AGREE_FACTOR * error),
                years=round(float(np.sum(w * [m.years for m in ms]) / w.sum()), 3),
                same_time_of_year=all(m.same_time_of_year for m in ms))
