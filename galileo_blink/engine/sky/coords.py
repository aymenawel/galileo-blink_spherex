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
from . import targets

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
    moved_arcmin: float | None = None   # how far that target has moved from the typed position


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


def resolve(text: str) -> Place:
    """The place a typed query means. One of NASA's test targets, typed by name or by any of
    its catalogue positions, opens that target where it is today."""
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
    return Place(round(ra, 5), round(dec, 5), label=label, kind=kind)
