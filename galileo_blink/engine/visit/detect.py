"""Find things that move within one visit (hours to days): asteroids.

The method is image subtraction. The median of all the visit's moments is the sky that stays
put; subtracting it from each moment leaves only what was different then. A real mover shows
up as a leftover in several moments, lined up along a straight path at a steady speed. A
cosmic ray or a blemish shows up once.

Subtracting first matters: a faint asteroid passing over a star is invisible as "a slightly
brighter star", but it is a clear leftover once the star is removed.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import maximum_filter

from .. import constants as C
from ..image.stack import change_map


@dataclass
class Detection:
    moment: int
    x: float                      # view pixels
    y: float
    significance: float           # leftover brightness in units of noise


@dataclass
class Track:
    """Detections in several moments that fit one straight, steady path."""
    detections: list[Detection]
    vx: float                     # pixels per day
    vy: float
    x0: float                     # position at time t0 (the first moment's time)
    y0: float
    rms_px: float
    moments_spanned: int          # moments between its first and last sighting, inclusive
    confidence: str = "possible"  # "strong" or "possible"
    name: str | None = None       # a catalogued asteroid, when one matches

    @property
    def speed_arcsec_per_hour(self) -> float:
        return math.hypot(self.vx, self.vy) * C.PIXEL_ARCSEC / 24.0

    @property
    def direction_deg(self) -> float:
        """Direction of travel, degrees east of north (east is -x on a north-up view)."""
        return math.degrees(math.atan2(-self.vx, self.vy)) % 360.0

    @property
    def score(self) -> float:
        return sum(d.significance for d in self.detections)

    def position(self, days: float) -> tuple[float, float]:
        return self.x0 + self.vx * days, self.y0 + self.vy * days


def static_sky(moments: list[np.ndarray]) -> np.ndarray:
    """What stays put. Where three or more moments have data: their median, which a mover
    cannot survive. Where only two do (photos are rolled, so corners are covered less often):
    the fainter of the two, since a mover only ever adds light. Where only one does there is
    nothing to compare with, so no sky and no search (NaN)."""
    cube = np.stack(moments)
    valid = np.isfinite(cube).sum(axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sky = np.nanmedian(cube, axis=0)
        low = np.nanmin(cube, axis=0)
    sky = np.where(valid == 2, low, sky)
    return np.where(valid >= 2, sky, np.nan)


def leftovers(moment: np.ndarray, sky: np.ndarray) -> np.ndarray:
    """The moment minus the static sky, in units of noise (see stack.change_map)."""
    return change_map(moment, sky, sky)


def find_peaks(significance: np.ndarray, moment: int) -> list[Detection]:
    """Positive leftovers above the threshold, one per local maximum, brightest first."""
    s = np.nan_to_num(significance, nan=0.0)
    edge = C.VISIT_EDGE_PX
    peak = (s >= C.VISIT_DETECT_SIGMA) & (s == maximum_filter(s, size=3))
    peak[:edge] = peak[-edge:] = False
    peak[:, :edge] = peak[:, -edge:] = False
    out = []
    for y, x in zip(*np.nonzero(peak)):
        box = np.clip(s[y - 2:y + 3, x - 2:x + 3], 0, None)
        yy, xx = np.mgrid[y - 2:y + 3, x - 2:x + 3]
        total = box.sum()
        out.append(Detection(moment, float((box * xx).sum() / total), float((box * yy).sum() / total),
                             float(s[y, x])))
    out.sort(key=lambda d: -d.significance)
    return out[:C.VISIT_MAX_PEAKS_PER_MOMENT]


def _fit(points: list[Detection], days: list[float]) -> tuple[float, float, float, float, float]:
    """Least-squares straight path through the detections: (x0, y0, vx, vy, rms)."""
    t = np.array([days[d.moment] for d in points])
    xs, ys = np.array([d.x for d in points]), np.array([d.y for d in points])
    a = np.vstack([np.ones_like(t), t]).T
    (x0, vx), _, _, _ = np.linalg.lstsq(a, xs, rcond=None)
    (y0, vy), _, _, _ = np.linalg.lstsq(a, ys, rcond=None)
    res = np.concatenate([xs - (x0 + vx * t), ys - (y0 + vy * t)])
    return float(x0), float(y0), float(vx), float(vy), float(np.sqrt(np.mean(res ** 2)))


def link(detections: list[list[Detection]], days: list[float], has_data=None) -> list[Track]:
    """Straight, steady paths through detections in at least VISIT_MIN_MOMENTS moments.

    `days[k]` is moment k's time; `has_data(moment, x, y)` says whether a moment has data at
    a pixel (used to judge whether a track was seen wherever it could have been)."""
    n = len(detections)
    tracks: list[Track] = []
    for a in range(n):
        for b in range(a + 1, n):
            dt = days[b] - days[a]
            if dt <= 0:
                continue
            for p in detections[a]:
                for q in detections[b]:
                    shift = math.hypot(q.x - p.x, q.y - p.y)
                    speed = shift * C.PIXEL_ARCSEC / (dt * 24.0)
                    if shift < C.VISIT_MIN_SHIFT_PX or speed > C.VISIT_MAX_SPEED_ARCSEC_H:
                        continue
                    vx, vy = (q.x - p.x) / dt, (q.y - p.y) / dt
                    members = [p, q]
                    for c in range(n):
                        if c in (a, b):
                            continue
                        ex, ey = p.x + vx * (days[c] - days[a]), p.y + vy * (days[c] - days[a])
                        near = [d for d in detections[c]
                                if math.hypot(d.x - ex, d.y - ey) <= C.VISIT_LINK_TOLERANCE_PX]
                        if near:
                            members.append(min(near, key=lambda d: math.hypot(d.x - ex, d.y - ey)))
                    if len(members) < C.VISIT_MIN_MOMENTS:
                        continue
                    if (len(members) == C.VISIT_MIN_MOMENTS
                            and min(d.significance for d in members) < C.VISIT_THREE_MOMENT_SIGMA):
                        continue                # three faint leftovers line up by chance
                    members.sort(key=lambda d: d.moment)
                    x0, y0, fvx, fvy, rms = _fit(members, days)
                    if rms > C.VISIT_MAX_RMS_PX:
                        continue
                    first, last = members[0].moment, members[-1].moment
                    tracks.append(Track(members, fvx, fvy, x0, y0, rms, last - first + 1))
    tracks = _one_per_object(tracks)
    for t in tracks:
        t.confidence = _confidence(t, days, has_data)
    return sorted(tracks, key=lambda t: (t.confidence != "strong", -t.score))[:C.VISIT_MAX_TRACKS]


def _one_per_object(tracks: list[Track]) -> list[Track]:
    """Keep the best track among those sharing a detection (the same object found twice)."""
    kept: list[Track] = []
    for t in sorted(tracks, key=lambda t: (-len(t.detections), -t.score)):
        ids = {id(d) for d in t.detections}
        if not any(ids & {id(d) for d in k.detections} for k in kept):
            kept.append(t)
    return kept


def _confidence(t: Track, days: list[float], has_data) -> str:
    """"strong" only if it was seen in most of the moments where it could have been seen, in
    at least VISIT_STRONG_MOMENTS of them."""
    seen = {d.moment for d in t.detections}
    first, last = min(seen), max(seen)
    possible = 0
    for k in range(first, last + 1):
        x, y = t.position(days[k])
        if has_data is None or has_data(k, x, y):
            possible += 1
    completeness = len(seen) / max(possible, 1)
    if len(seen) >= C.VISIT_STRONG_MOMENTS and completeness >= C.VISIT_MIN_COMPLETENESS:
        return "strong"
    return "possible"


def find_movers(moments: list[np.ndarray], days: list[float]) -> tuple[list[Track], np.ndarray, list[np.ndarray]]:
    """(tracks, the static sky, each moment's leftover map)."""
    if len(moments) < C.VISIT_MIN_MOMENTS:
        return [], static_sky(moments) if moments else np.zeros((0, 0)), []
    sky = static_sky(moments)
    # Movers are searched for only where three or more moments overlap: with two, a leftover
    # cannot be told from a cosmic ray or a star that changed colour.
    searchable = np.isfinite(np.stack(moments)).sum(axis=0) >= C.VISIT_MIN_MOMENTS
    maps = [np.where(searchable, leftovers(m, sky), np.nan) for m in moments]
    detections = [find_peaks(s, k) for k, s in enumerate(maps)]

    def has_data(k: int, x: float, y: float) -> bool:
        xi, yi = int(round(x)), int(round(y))
        inside = 0 <= yi < moments[k].shape[0] and 0 <= xi < moments[k].shape[1]
        return bool(inside and np.isfinite(moments[k][yi, xi]))

    return link(detections, days, has_data), sky, maps
