"""Did the central object get brighter or fainter between seasons? With an honest error.

Every SPHEREx photo sees a star at a different wavelength (the filter changes across the
detector), so two photos of a perfectly steady star rarely agree: one may sit on the bright
side of its spectrum, the other on the faint side. Comparing seasons photo by photo would
mistake colour for change.

So, per camera, the photos are fitted together. Within one camera's narrow band the shape of
the spectrum is assumed fixed (a straight line in log brightness against wavelength) and only
its level may differ from season to season:

    ln(flux) = a + b x (wavelength - mean wavelength) + d[season]      d = 0 for the first season

The ratio of a season to the first is exp(d). Its error comes from the fit, scaled by how far
the photos actually scatter around it.

That error is not yet the whole truth: calibration and the measurement itself also wobble from
season to season. The ordinary stars in the same photos (the reference stars used to correct
the astrometry) do not vary, so the identical fit is run on each of them. How far their ratios
stray from 1 is this view's "floor": the change that stars which do not vary appear to show.
It is added to every error. A season counts as "changed" only when it differs from the first
by more than 3 times that total error.

Pure functions: no network, no files.
"""
from __future__ import annotations

import math

import numpy as np

from ..image.stack import MAD_TO_SIGMA

MIN_SNR = 5.0                     # below this a photo's brightness is mostly noise
MIN_PHOTOS_PER_SEASON = 2         # one photo alone cannot be told from a blemish
MIN_SEASONS = 2                   # a change needs something to change from
MIN_SPARE_PHOTOS = 2              # photos beyond the fitted numbers, so the scatter is measured
MIN_REFERENCE_STARS = 3           # fewer stars cannot measure the floor
DEFAULT_FLOOR = 0.10              # 10% (ln units): assumed when the view's own stars cannot say
CHANGED_SIGMA = 3.0               # a change counts beyond 3 x (fit error and floor together)
FLAT_BAND_MICRON = 1e-6           # photos all at one wavelength: there is no slope to fit

REASONS = {
    "no_subject": "There is no catalogued object at the centre of this view to follow.",
    "saturated": "It is too bright for SPHEREx: its brightness cannot be measured.",
    "too_faint": "It is too faint in single photos to measure its brightness reliably.",
    "one_season": "No camera has clean photos of it in two seasons yet.",
}


def _number(value) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _photo(row) -> dict | None:
    """The fields of one photo's measurement, or None if they are not readable."""
    if not isinstance(row, dict):
        return None
    camera, season = _number(row.get("camera")), _number(row.get("season"))
    if camera is None or season is None:
        return None
    flux = row.get("flux_mjy", row.get("flux"))
    return dict(camera=int(camera), season=int(season), wavelength=_number(row.get("wavelength")),
                flux=_number(flux), snr=_number(row.get("snr")), status=row.get("status"))


def _usable(p: dict) -> bool:
    """A clean photo with a confident, positive brightness at a known wavelength."""
    return (p["status"] == "ok" and p["flux"] is not None and p["flux"] > 0
            and p["snr"] is not None and p["snr"] >= MIN_SNR and p["wavelength"] is not None)


def _rows(rows) -> list[dict]:
    if not isinstance(rows, (list, tuple)):
        return []
    return [p for p in (_photo(r) for r in rows) if p is not None]


def fit_seasons(photos: list[dict]) -> dict | None:
    """Fit one object's photos from ONE camera (see the module text).

    Returns {first_season, seasons: [(season, d, error of d, n_photos)], scatter} with d and its
    error in ln units, or None when the photos cannot support a fit: fewer than two seasons
    with two usable photos each, too few photos for the number of fitted values, or no way to
    tell colour from change (each season seen at a single wavelength)."""
    usable = [p for p in photos if _usable(p)]
    by_season: dict[int, list[dict]] = {}
    for p in usable:
        by_season.setdefault(p["season"], []).append(p)
    seasons = sorted(s for s, ps in by_season.items() if len(ps) >= MIN_PHOTOS_PER_SEASON)
    if len(seasons) < MIN_SEASONS:
        return None
    used = [p for s in seasons for p in by_season[s]]
    lam = np.array([p["wavelength"] for p in used])
    y = np.log([p["flux"] for p in used])
    columns = [np.ones(len(used))]
    if np.ptp(lam) > FLAT_BAND_MICRON:
        columns.append(lam - lam.mean())
    for s in seasons[1:]:
        columns.append(np.array([1.0 if p["season"] == s else 0.0 for p in used]))
    x = np.column_stack(columns)
    n, k = x.shape
    if n < k + MIN_SPARE_PHOTOS or np.linalg.matrix_rank(x) < k:
        return None
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ coef
    scatter = math.sqrt(float(residual @ residual) / (n - k))
    cov = scatter ** 2 * np.linalg.inv(x.T @ x)
    first = len(columns) - len(seasons) + 1             # index of the first season column
    out = [(seasons[0], 0.0, 0.0, len(by_season[seasons[0]]))]
    for i, s in enumerate(seasons[1:]):
        j = first + i
        out.append((s, float(coef[j]), math.sqrt(max(float(cov[j, j]), 0.0)), len(by_season[s])))
    return dict(first_season=seasons[0], seasons=out, scatter=scatter)


def reference_floor(stars: list[list[dict]]) -> tuple[float | None, int]:
    """(floor in ln units, number of stars it rests on) for one camera: the robust spread
    around 1 (1.48 x the median of |ln ratio|) of every reference star's season ratios.
    None with fewer than MIN_REFERENCE_STARS fitted stars."""
    lns, n = [], 0
    for photos in stars:
        fit = fit_seasons(photos)
        if fit is None:
            continue
        n += 1
        lns += [d for _, d, _, _ in fit["seasons"][1:]]
    if n < MIN_REFERENCE_STARS or not lns:
        return None, n
    return float(MAD_TO_SIGMA * np.median(np.abs(lns))), n


def _reason(photos: list[dict]) -> str:
    """Why no camera gave a result."""
    if not photos:
        return "too_faint"
    if len({p["season"] for p in photos}) < 2:
        return "one_season"
    lost = [p for p in photos if not _usable(p)]
    saturated = sum(1 for p in lost if p["status"] in ("saturated", "partial"))
    faint = len(lost) - saturated
    if not lost:
        return "one_season"            # every photo was clean, but too few per season
    return "saturated" if saturated >= faint else "too_faint"


def _empty(reason: str | None) -> dict:
    return dict(cameras={}, best=None, changed=None, reason=reason)


def measure_change(subject, references=None, subject_kind: str | None = None) -> dict:
    """How the subject's brightness changed, per camera, against its first measured season.

    `subject` is view.json's `brightness` list (camera, season, wavelength, flux_mjy, snr,
    status per photo). `references` is a list with one such list per reference star (their
    photos in every camera). Returns

        {"cameras": {"<camera>": {"first_season", "points", "floor", "floor_measured",
                                  "n_reference_stars", "scatter"}},
         "best": {"camera", "first_season", "last_season", "ratio", "error", "changed"} | None,
         "changed": True | False | None,
         "reason": None | "saturated" | "too_faint" | "one_season" | "no_subject"}

    Each point is {"season", "ratio", "error", "n_photos"} plus "changed" after the first.
    `ratio` is the brightness relative to the camera's first season; `error` is its one-sigma
    error IN RATIO UNITS (ratio x the total error of ln(ratio), where the total is the fit
    error and the floor in quadrature). `floor` and `scatter` are in ln units (0.1 = about 10%):
    the floor measured from the reference stars (or DEFAULT_FLOOR, with floor_measured false),
    and the subject's own photo-to-photo scatter around its fit.

    `best` is the most significant change over the longest span of seasons; when nothing
    changed, the camera that measured it best over the longest span, with changed false.
    Cameras without a result are left out; with none, `reason` says why. Never raises.
    """
    try:
        return _measure_change(subject, references, subject_kind)
    except Exception:                      # noqa: BLE001 - odd input must not sink a view
        return _empty("too_faint")


def _measure_change(subject, references, subject_kind) -> dict:
    if subject_kind == "spot":
        return _empty("no_subject")
    photos = _rows(subject)
    stars = [_rows(s) for s in references] if isinstance(references, (list, tuple)) else []
    cameras: dict[str, dict] = {}
    candidates = []
    for cam in sorted({p["camera"] for p in photos}):
        fit = fit_seasons([p for p in photos if p["camera"] == cam])
        if fit is None:
            continue
        floor, n_ref = reference_floor([[p for p in s if p["camera"] == cam] for s in stars])
        measured = floor is not None
        floor = floor if measured else DEFAULT_FLOOR
        first, points = fit["first_season"], []
        for season, d, fit_error, n in fit["seasons"]:
            ratio = math.exp(d)
            if season == first:
                points.append(dict(season=season, ratio=1.0, error=0.0, n_photos=n))
                continue
            ln_error = math.hypot(fit_error, floor)
            changed = abs(d) > CHANGED_SIGMA * ln_error
            points.append(dict(season=season, ratio=round(ratio, 3),
                               error=round(ratio * ln_error, 3), n_photos=n, changed=changed))
            candidates.append(dict(camera=cam, first_season=first, last_season=season,
                                   ratio=round(ratio, 3), error=round(ratio * ln_error, 3),
                                   changed=changed, _span=season - first,
                                   _significance=abs(d) / ln_error if ln_error > 0 else math.inf,
                                   _ln_error=ln_error))
        cameras[str(cam)] = dict(first_season=first, points=points, floor=round(floor, 3),
                                 floor_measured=measured, n_reference_stars=n_ref,
                                 scatter=round(fit["scatter"], 3))
    if not cameras:
        return _empty(_reason(photos))
    changed = [c for c in candidates if c["changed"]]
    if changed:
        best = max(changed, key=lambda c: (c["_span"], c["_significance"]))
    else:
        best = max(candidates, key=lambda c: (c["_span"], -c["_ln_error"]))
    best = {k: v for k, v in best.items() if not k.startswith("_")}
    return dict(cameras=cameras, best=best, changed=bool(changed), reason=None)
