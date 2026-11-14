"""Turn what a person types into a place in the sky.

Understands decimal degrees, sexagesimal (hours for right ascension), NASA's own phrasing
("Right Ascension 08h55m10.831s, declination -7d14m42.53s") and object names. Coordinates are
parsed here with no network call; names are looked up at astronomical name services.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass

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
_NUMBER = r"[+-]?\d+(?:\.\d+)?"
_TWO_NUMBERS = re.compile(rf"^\s*({_NUMBER})\s+({_NUMBER})\s*$")
_WORDS = re.compile(r"\b(right ascension|declination|ra|dec|j2000|icrs)\b")
EXAMPLE = 'Try "269.452 4.693", "17h57m48.5s +04d41m36s" or a name like "Barnard\'s Star".'


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
        ra, dec = float(m.group(1)), float(m.group(2))
        if not (0 <= ra <= 360 and -90 <= dec <= 90):
            # two plain numbers are degrees; never re-read them as hours
            raise UserError("Right ascension must be between 0 and 360 degrees and declination "
                            "between -90 and +90. " + EXAMPLE)
        return ra % 360.0, dec + 0.0
    if re.search(r"\d\s*[:hd]\s*\d", s) or re.fullmatch(rf"(?:{_NUMBER}\s+){{3,5}}{_NUMBER}", s):
        try:
            c = SkyCoord(s, unit=(u.hourangle, u.deg))
        except Exception:                       # noqa: BLE001 - not coordinates after all
            return None
        return float(c.ra.deg), float(c.dec.deg)
    return None


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
    """Position of a named object. UserError if no service knows it; ServiceDown if none
    answered at all (a maintenance page is not "not found")."""
    answered = False
    for ask in (lambda: _sesame(SESAME_MIRRORS[0], name), lambda: _sesame(SESAME_MIRRORS[1], name),
                lambda: _ned(name)):
        try:
            hit = ask()
        except ServiceDown:
            continue
        answered = True
        if hit:
            return hit
    if not answered:
        raise ServiceDown(NAME_SERVICE)
    raise UserError(f"No object called “{name}” was found. " + EXAMPLE)


FOLLOW_RADIUS_DEG = 0.06          # 3.6 arcmin: 26 years at 8 arcsec/yr
FOLLOW_MATCH_ARCSEC = 10.0
FOLLOW_MIN_MOVE_ARCSEC = 20.0


def follow_mover(ra: float, dec: float):
    """If (ra, dec) is an old catalogue position of a fast-moving star, where that star is
    now: (mover, ra_now, dec_now, arcminutes moved), else None.

    Name services and most catalogues give positions for the year 2000. A star moving
    4 arcsec/yr is by now 100 arcsec from there. This asks Gaia for fast stars nearby and
    checks whether one of them passed through the typed position between 1990 and today."""
    try:
        nearby = catalogues.gaia_cone(ra, dec, FOLLOW_RADIUS_DEG)
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
