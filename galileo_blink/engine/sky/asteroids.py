"""Known solar-system objects: what is in a field at a moment, and where a named asteroid
appears in SPHEREx's photos.

"What is here?" is answered by IMCCE's SkyBoT cone search. "Where was Bamberga?" is answered
by NASA/IPAC's Moving Object Search Tool (MOST), which knows SPHEREx's pointing history.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import astropy.units as u
from astropy.coordinates import SkyCoord

from .. import constants as C
from ..archive import http
from ..errors import ServiceDown, UserError

SKYBOT = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php"
SKYBOT_SERVICE = "The asteroid catalogue service (IMCCE SkyBoT)"
MOST = C.IRSA + "/cgi-bin/MOST/nph-most"
MOST_SERVICE = "NASA's moving-object search (IRSA MOST)"
MOST_TIMEOUT_S = 45.0
MISSION_START = "2025 04 01"
_OBS_ID = re.compile(r"^\d{4}W\d+_\w+$")
_CAMERA = re.compile(r"^D([1-6])$")


@dataclass(frozen=True)
class KnownObject:
    """A catalogued solar-system object at one moment."""
    name: str
    number: str
    ra: float
    dec: float
    vmag: float
    kind: str                     # SkyBoT's class, e.g. "MB>Inner"


def skybot(ra: float, dec: float, radius_deg: float, mjd: float) -> list[KnownObject]:
    """Catalogued solar-system objects within the cone at that moment (as seen from Earth's
    centre: for main-belt objects SPHEREx's orbit changes the position by a few arcsec)."""
    params = {"RA": f"{ra:.6f}", "DEC": f"{dec:.6f}", "SR": f"{radius_deg:.4f}",
              "EPOCH": f"{mjd + 2400000.5:.6f}", "-mime": "text", "-output": "object",
              "-loc": "500", "-from": "GalileoBlink"}
    r = http.get(SKYBOT, service=SKYBOT_SERVICE, params=params, timeout=45, retries=1)
    if r.status_code == 204:
        return []                               # SkyBoT's answer when nothing is in the cone
    flag = re.match(r"# Flag:\s*(-?\d+)", r.text)
    if not flag:
        raise ServiceDown(SKYBOT_SERVICE, "it sent a page that is not an asteroid list")
    if int(flag.group(1)) < 0:
        raise ServiceDown(SKYBOT_SERVICE, "it reported an error")
    out = []
    for line in r.text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6:
            continue
        try:
            where = SkyCoord(cells[2], cells[3], unit=(u.hourangle, u.deg))
            out.append(KnownObject(name=cells[1], number=cells[0], ra=float(where.ra.deg),
                                   dec=float(where.dec.deg), vmag=float(cells[5]), kind=cells[4]))
        except (ValueError, IndexError):
            continue
    return out


@dataclass(frozen=True)
class Sighting:
    """One SPHEREx exposure that contains a named asteroid, with where it was then."""
    mjd: float
    camera: int
    obs_id: str
    ra: float
    dec: float
    vmag: float


def parse_most(text: str) -> tuple[str | None, list[Sighting]]:
    """(the object's full name, its sightings) from a MOST "Brief" answer."""
    name = None
    sightings = []
    for line in text.splitlines():
        if line.startswith("\\object_name"):
            name = line.split("=", 1)[1].strip().strip('"')
        if not line.strip() or line.startswith(("\\", "|")):
            continue
        cells = line.split()
        try:
            at = next(i for i, c in enumerate(cells) if _OBS_ID.match(c))
            camera = next(int(m.group(1)) for c in cells[at:at + 4] if (m := _CAMERA.match(c)))
            mjd = next(float(c) for c in cells[at:] if re.fullmatch(r"6\d{4}\.\d+", c))
            sightings.append(Sighting(mjd=mjd, camera=camera, obs_id=cells[at], ra=float(cells[0]),
                                      dec=float(cells[1]), vmag=float(cells[6])))
        except (StopIteration, ValueError, IndexError):
            continue
    return name, sorted(sightings, key=lambda s: s.mjd)


class NoSightings(UserError):
    """The asteroid is known, but no SPHEREx photo holds it."""


_MATCH_LINE = re.compile(r"^\s*(\d+)\s+(.+?),\s*Object Type=Asteroid", re.MULTILINE)


def numbered_match(answer: str, name: str) -> str | None:
    """The number of the asteroid the visitor meant, when the search answers "multiple
    matches". Famous asteroids are listed twice (an old entry and the numbered one), so
    "Vesta" alone is ambiguous while "4" is not. Only an entry whose name is exactly what was
    typed counts; None if the answer is not such a list or holds no such entry."""
    if "multiple matches" not in answer.lower():
        return None
    wanted = name.strip().lower()
    numbers = [int(number) for number, listed in _MATCH_LINE.findall(answer)
               if listed.strip().lower() == wanted]
    return str(min(numbers)) if numbers else None


def _ask_by_number(number: str) -> tuple[str, list[Sighting]]:
    """Ask again for an asteroid by the number the search itself listed. If it now refuses
    that number, the fault is the search's, not the visitor's."""
    try:
        return asteroid_sightings(number, _retried=True)
    except NoSightings:
        raise
    except UserError:
        raise ServiceDown(MOST_SERVICE, "it refused a name it had just listed") from None


def asteroid_sightings(name: str, _retried: bool = False) -> tuple[str, list[Sighting]]:
    """Every SPHEREx exposure that caught the named asteroid."""
    from astropy.time import Time
    params = dict(catalog="spherex", input_type="name_input", obj_type="Asteroid", obj_name=name,
                  obs_begin=MISSION_START, obs_end=Time.now().strftime("%Y %m %d"),
                  output_mode="Brief")
    unknown = UserError(f"No asteroid called “{name}” is known to NASA's moving-object "
                        "search. Try a name or number such as Bamberga, Eugenia or 324.")
    try:
        r = http.get(MOST, service=MOST_SERVICE, params=params, timeout=MOST_TIMEOUT_S,
                     backoff=C.BUSY_BACKOFF_S)
    except ServiceDown as e:
        if e.detail == "HTTP 400":              # MOST's way of saying it cannot settle the name
            number = None if _retried else numbered_match(e.body, name)
            if number:                          # "Vesta" is ambiguous; "4" is not
                return _ask_by_number(number)
            raise unknown from None
        raise
    full_name, sightings = parse_most(r.text)
    if not sightings and not _retried:
        number = numbered_match(r.text, name)
        if number:                              # "Vesta" is ambiguous; "4" is not
            return _ask_by_number(number)
    if not sightings:
        head = r.text.lower()[:2000]
        if "<html" in head and "not found" not in head:
            raise ServiceDown(MOST_SERVICE, "it sent a page that is not an answer")
        if "not found" in r.text.lower() or "error" in head:
            raise unknown
        if full_name is None:                   # not even the header of an answer
            raise ServiceDown(MOST_SERVICE, "it sent a page that is not an answer")
        raise NoSightings(f"SPHEREx has not photographed “{name}” yet, or it was never "
                          "inside a photo.")
    return full_name or name, sightings


@dataclass(frozen=True)
class AsteroidVisit:
    """The best stretch of photos in which to watch a named asteroid move."""
    name: str
    camera: int
    ra: float                     # centre of its path during the visit
    dec: float
    size_deg: float
    mjd_start: float
    mjd_end: float
    vmag: float
    n_photos: int
    n_moments: int


def best_visit(name: str, sightings: list[Sighting]) -> AsteroidVisit:
    """The camera and stretch of days with the most separate moments on the asteroid, small
    enough to fit one view. Ties go to the brightest, then the most recent."""
    best = None
    for camera in range(1, 7):
        rows = [s for s in sightings if s.camera == camera]
        runs: list[list[Sighting]] = []
        for s in rows:
            if runs and s.mjd - runs[-1][-1].mjd <= C.VISIT_GAP_DAYS:
                runs[-1].append(s)
            else:
                runs.append([s])
        for run in runs:
            while len(run) >= 1:
                span = _span_deg(run)
                if run[-1].mjd - run[0].mjd <= C.VISIT_MAX_DAYS and span <= C.FIELD_MAX_DEG * 0.7:
                    break
                run = run[:-1]                  # shorten until it fits the view and the window
            moments = 1 + sum(1 for a, b in zip(run, run[1:]) if b.mjd - a.mjd > C.MOMENT_GAP_DAYS)
            vmag = min(s.vmag for s in run)
            rank = (min(moments, 8), -vmag, run[0].mjd)
            if moments >= C.VISIT_MIN_MOMENTS and (best is None or rank > best[0]):
                best = (rank, camera, run, moments, vmag)
    if best is None:
        raise UserError(f"SPHEREx never caught {name} in three separate moments within a few "
                        "days, which is what watching it move needs.")
    _, camera, run, moments, vmag = best
    ras, decs = [s.ra for s in run], [s.dec for s in run]
    centre = SkyCoord(ras * u.deg, decs * u.deg).cartesian.mean()
    centre = SkyCoord(centre).spherical
    size = min(C.FIELD_MAX_DEG, max(C.FIELD_DEFAULT_DEG, round(_span_deg(run) * 1.5 + 0.06, 2)))
    return AsteroidVisit(name=name, camera=camera, ra=round(float(centre.lon.deg), 4),
                         dec=round(float(centre.lat.deg), 4), size_deg=size,
                         mjd_start=run[0].mjd - 0.005, mjd_end=run[-1].mjd + 0.005, vmag=vmag,
                         n_photos=len(run), n_moments=moments)


def _span_deg(run: list[Sighting]) -> float:
    if len(run) < 2:
        return 0.0
    first = SkyCoord(run[0].ra * u.deg, run[0].dec * u.deg)
    return float(max(first.separation(SkyCoord(s.ra * u.deg, s.dec * u.deg)).deg for s in run))


def find_asteroid(name: str) -> AsteroidVisit:
    """Where and when to watch a named asteroid in SPHEREx data."""
    name = " ".join(str(name).split())
    if not name or len(name) > 60:
        raise UserError("Type an asteroid's name or number, such as Bamberga or 324.")
    full_name, sightings = asteroid_sightings(name)
    return best_visit(full_name, sightings)
