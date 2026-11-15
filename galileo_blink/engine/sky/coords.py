"""Turn what a person types into a place in the sky.

Understands decimal degrees, sexagesimal (hours for right ascension), NASA's own phrasing
("Right Ascension 08h55m10.831s, declination -7d14m42.53s") and object names. Coordinates are
parsed here with no network call; names are looked up at astronomical name services.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord

from ..archive import http
from ..errors import ServiceDown, UserError
from . import catalogues, targets
from .motion import predict, separation_arcsec

SESAME_MIRRORS = ("https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oI/SNV?",
                  "https://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?")
NED = "https://ned.ipac.caltech.edu/srs/ObjectLookup?name="
NAME_SERVICE = "The astronomical name service (CDS Sesame / NASA NED)"
NAME_TIMEOUT_S = 8.0
NAME_DEADLINE_S = 10.0
"""The whole name lookup (both Sesame mirrors and NED, asked at once) ends after this long."""
NAMES_FILE = Path(__file__).resolve().parents[3] / "data" / "names.json"
_NUMBER = r"[+-]?\d+(?:\.\d+)?"
_TWO_NUMBERS = re.compile(rf"^\s*({_NUMBER})\s+({_NUMBER})\s*$")
_WORDS = re.compile(r"\b(right ascension|declination|ra|dec|j2000|icrs)\b")
EXAMPLE = 'Try "269.452 4.693", "17h57m48.5s +04d41m36s" or a name like "Barnard\'s Star".'
PLANETS = {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
           "pluto"}
PLANET_X = {"planet x", "planet nine", "planet 9", "planet ix"}
MOVES_TOO_FAST = ("Planets move too fast to have a fixed place in the sky. For an asteroid, use "
                  "Find it under Asteroids on the home page.")
NOT_FOUND_YET = ("Nobody has found Planet X yet, so it has no place to open. Try Barnard's Star, "
                 "or one of NASA's five test targets.")


@dataclass(frozen=True)
class Place:
    ra: float                     # degrees
    dec: float
    label: str                    # what to call it on screen
    kind: str                     # "coordinates" or "name"
    target_id: str | None = None  # set when this is one of NASA's five test targets
    moved_arcmin: float | None = None   # how far the object has moved from the typed position
    follows: str | None = None    # catalogue name of the moving star the view was re-centred on


def normalise(text: str) -> str:
    """Strip the words and punctuation people (and NASA's challenge page) wrap coordinates in."""
    s = str(text).lower().replace("=", " ").replace(",", " ").replace(";", " ")
    s = s.replace("−", "-").replace("°", "d").replace("′", "m").replace("″", "s")
    return " ".join(_WORDS.sub(" ", s).split())


def parse_coordinates(text: str) -> tuple[float, float] | None:
    """(ra, dec) in degrees if `text` is coordinates, None if it looks like a name.
    Raises UserError for coordinates that are out of range."""
    s = normalise(text)
    m = _TWO_NUMBERS.match(s)
    if m:
        # two plain numbers are degrees; never re-read them as hours
        problem = _off_sky(m.group(1), "deg", m.group(2))
        if problem:
            raise UserError(problem)
        return float(m.group(1)) % 360.0, float(m.group(2)) + 0.0
    if re.search(r"\d\s*[:hd]\s*\d", s) or re.fullmatch(rf"(?:{_NUMBER}\s+){{3,5}}{_NUMBER}", s):
        problem = _sexagesimal_off_sky(s)
        if problem:
            raise UserError(problem)
        try:
            c = SkyCoord(s, unit=(u.hourangle, u.deg))
        except Exception:                       # noqa: BLE001 - not coordinates after all
            return None
        return float(c.ra.deg), float(c.dec.deg)
    return None


def _off_sky(ra: str | None, unit: str, dec: str | None) -> str | None:
    """What is wrong, in words, if a right ascension or declination (as typed) is off the sky."""
    if dec is not None and abs(float(dec)) > 90:
        return (f"Declination runs from -90 to +90 degrees, so {dec.lstrip('+')} is off the sky. "
                "Example: 269.452 4.693.")
    if ra is not None and unit == "hours" and not 0 <= float(ra) < 24:
        return (f"Right ascension runs from 0 to 24 hours, so {ra}h is off the sky. "
                "Example: 17h57m48.5s +04d41m36s.")
    if ra is not None and unit == "deg" and not 0 <= float(ra) <= 360:
        return (f"Right ascension runs from 0 to 360 degrees, so {ra} is off the sky. "
                "Example: 269.452 4.693.")
    return None


def _sexagesimal_off_sky(s: str) -> str | None:
    """The same check for a position written in hours/degrees, minutes and seconds."""
    tokens = s.split()
    if len(tokens) == 2:
        ra_part, dec_part = tokens
    elif len(tokens) == 6:
        ra_part, dec_part = " ".join(tokens[:3]), " ".join(tokens[3:])
    else:
        halves = re.split(r"\s+(?=[+-])", s, maxsplit=1)
        if len(halves) != 2:
            return None
        ra_part, dec_part = halves
    ra = re.match(_NUMBER, ra_part)
    dec = re.match(_NUMBER, dec_part)
    if not ra or not dec:
        return None
    unit = "deg" if re.match(rf"{_NUMBER}\s*d", ra_part) else "hours"
    return _off_sky(ra.group(0), unit, dec.group(0))


def explain_coordinates(text: str) -> str | None:
    """For text that is clearly meant as a position but did not parse, what is wrong with it;
    None if it may be a name. Letters other than units right after a number mean a name
    ("WISE 1049-5319", "3C 273", "M 101")."""
    raw = " ".join(str(text).lower().replace(",", " ").split())
    s = normalise(text)
    if not re.search(r"\d", s) or re.search(r"[a-z]", re.sub(r"(?<=[\d.])\s*[hmsd]", " ", s)):
        return None
    numbers = re.findall(_NUMBER, s)
    if len(numbers) == 1:
        number = numbers[0]
        if re.search(r"\b(declination|dec)\b", raw):
            problem = _off_sky(None, "deg", number)
        elif re.search(r"\b(right ascension|ra)\b", raw):
            problem = _off_sky(number, "hours" if "h" in s else "deg", None)
        else:
            problem = None
        return problem or ("A position needs two numbers: right ascension, then declination. "
                           "Example: 269.452 4.693.")
    return (_sexagesimal_off_sky(s) or "That looks like a position, but it could not be read. "
            "Example: 269.452 4.693 or 17h57m48.5s +04d41m36s.")


@lru_cache(maxsize=1)
def _known_names() -> dict[str, tuple[float, float]]:
    """Well-known objects, so the names visitors type most open even when every name service
    is down. Positions are ICRS for the year 2000 (fast stars are followed to today)."""
    out = {}
    for row in json.loads(NAMES_FILE.read_text(encoding="utf8")):
        for alias in (row["name"], *row["aliases"]):
            out[_name_key(alias)] = (float(row["ra"]), float(row["dec"]))
    return out


def _name_key(name: str) -> str:
    n = " ".join(str(name).lower().replace("’", "'").split())
    return n[4:] if n.startswith("the ") else n


def known_name(name: str) -> tuple[float, float] | None:
    return _known_names().get(_name_key(name))


def _sesame(base: str, name: str) -> tuple[float, float] | None:
    r = http.get(base + urllib.parse.quote(name), service=NAME_SERVICE, timeout=NAME_TIMEOUT_S,
                 retries=0)
    lines = r.text.splitlines()
    if not any(line.startswith("#=") for line in lines):
        raise ServiceDown(NAME_SERVICE, "it sent a page that is not an answer")
    for line in lines:
        if line.startswith("%J "):
            parts = line.split()
            return float(parts[1]), float(parts[2])
    return None


def _ned(name: str) -> tuple[float, float] | None:
    r = http.get(NED + urllib.parse.quote(name), service=NAME_SERVICE, timeout=NAME_TIMEOUT_S,
                 retries=0)
    try:
        pos = json.loads(r.text)["Preferred"]["Position"]
        return float(pos["RA"]), float(pos["Dec"])
    except (ValueError, KeyError, TypeError):
        return None


def lookup_name(name: str) -> tuple[float, float]:
    """Position of a named object: from the offline table, else from the name services, all
    asked at once and given NAME_DEADLINE_S in total. A Sesame answer is preferred to NED's.

    UserError only when a Sesame mirror answered that it knows no such object; ServiceDown if
    neither did (a maintenance page is not "not found", and NED knowing nothing proves little:
    it holds galaxies, not stars)."""
    hit = known_name(name)
    if hit:
        return hit
    deadline = time.monotonic() + NAME_DEADLINE_S
    pool = ThreadPoolExecutor(3, thread_name_prefix="names")
    try:
        sesame = {pool.submit(_sesame, base, name) for base in SESAME_MIRRORS}
        ned = pool.submit(_ned, name)
        pending = set(sesame) | {ned}
        sesame_answered = False
        while pending:
            done, pending = wait(pending, timeout=max(0.0, deadline - time.monotonic()),
                                 return_when=FIRST_COMPLETED)
            if not done:
                break                           # out of time
            for job in done:
                if job is ned:
                    continue
                try:
                    hit = job.result()
                except Exception:               # noqa: BLE001 - this mirror did not answer
                    continue
                sesame_answered = True
                if hit:
                    return hit
            # the two mirrors hold the same data: one "no such object" settles it
            if (sesame_answered or not (pending & sesame)) and ned.done():
                break
        if ned.done() and not ned.cancelled():
            try:
                hit = ned.result()
            except Exception:                   # noqa: BLE001
                hit = None
            if hit:
                return hit
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if not sesame_answered:
        raise ServiceDown(NAME_SERVICE)
    raise UserError(f"No object called “{name}” was found. " + EXAMPLE)


FOLLOW_RADIUS_DEG = 0.06          # 3.6 arcmin: 26 years at 8 arcsec/yr
FOLLOW_MATCH_ARCSEC = 10.0
FOLLOW_MIN_MOVE_ARCSEC = 20.0
FOLLOW_TIMEOUT_S = 8.0
"""Gaia is asked once and briefly: if it is slow, the place simply is not re-centred."""


def follow_mover(ra: float, dec: float):
    """If (ra, dec) is an old catalogue position of a fast-moving star, where that star is
    now: (mover, ra_now, dec_now, arcminutes moved), else None.

    Name services and most catalogues give positions for the year 2000. A star moving
    4 arcsec/yr is by now 100 arcsec from there. This asks Gaia for fast stars nearby and
    checks whether one of them passed through the typed position between 1990 and today."""
    try:
        nearby = catalogues.gaia_cone(ra, dec, FOLLOW_RADIUS_DEG, timeout=FOLLOW_TIMEOUT_S, retries=0)
    except Exception:                           # noqa: BLE001 - optional: keep the typed place
        return None
    best = None
    for star in nearby:
        if star.pm_total < catalogues.C.MIN_PM_MARK_ARCSEC_YR:
            continue
        closest = min(separation_arcsec(ra, dec, *predict(star, 47892.5 + 365.25 * year))
                      for year in range(0, 38))                 # 1990 .. 2027
        if closest <= FOLLOW_MATCH_ARCSEC and (best is None or closest < best[0]):
            best = (closest, star)
    if best is None:
        return None
    star = best[1]
    now = predict(star, targets.VIEW_CENTRE_MJD)
    moved = separation_arcsec(ra, dec, *now)
    if moved < FOLLOW_MIN_MOVE_ARCSEC:
        return None                             # already centred well enough
    return star, round(now[0], 4), round(now[1], 4), moved / 60.0


def resolve(text: str, follow: bool = True) -> Place:
    """The place a typed query means. A fast-moving object typed by name, or by an old
    catalogue position, opens where it is today (NASA's test targets without any lookup)."""
    text = " ".join(str(text).split())
    if not text:
        raise UserError("Type a place in the sky. " + EXAMPLE)
    if len(text) > 120:
        raise UserError("That is too long to be a sky position or an object name.")
    coords = parse_coordinates(text)
    if coords is None:
        t = targets.by_name(text)
        if t:
            return Place(*t.centre(), label=t.name, kind="name", target_id=t.id)
        key = _name_key(text)
        if key in PLANETS:
            raise UserError(MOVES_TOO_FAST)
        if key in PLANET_X:
            raise UserError(NOT_FOUND_YET)
        problem = None if known_name(text) else explain_coordinates(text)
        if problem:
            raise UserError(problem)
        ra, dec = lookup_name(text)
        label, kind = text, "name"
    else:
        ra, dec = coords
        label, kind = f"RA {ra:.4f}°, Dec {dec:+.4f}°", "coordinates"
    near = targets.near_track(ra, dec)
    if near:
        t, moved = near
        return Place(*t.centre(), label=t.name, kind=kind, target_id=t.id,
                     moved_arcmin=round(moved, 1))
    followed = follow_mover(ra, dec) if follow else None
    if followed:
        star, ra_now, dec_now, moved = followed
        return Place(ra_now, dec_now, label=label, kind=kind, moved_arcmin=round(moved, 1),
                     follows=star.name)
    return Place(round(ra, 5), round(dec, 5), label=label, kind=kind)
