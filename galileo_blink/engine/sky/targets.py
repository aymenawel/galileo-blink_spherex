"""NASA's five test targets for the challenge, with the catalogue values used to track them."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from astropy.time import Time

from .motion import Mover, predict, separation_arcsec

DATA = Path(__file__).resolve().parents[3] / "data" / "targets.json"
MATCH_ARCMIN = 3.0
"""A typed position this close to a target's path across the sky (2000-2030) opens the target.
Catalogue coordinates are old: NASA's WISE 0855 coordinate is its 2010 position, 2 arcminutes
from where it is now."""


@dataclass(frozen=True)
class Target:
    id: str
    name: str
    aliases: tuple[str, ...]
    kind: str
    blurb: str
    mover: Mover

    def centre(self, mjd: float | None = None) -> tuple[float, float]:
        """Where it is now (or at `mjd`), rounded so every visitor shares one view."""
        ra, dec = predict(self.mover, mjd if mjd is not None else Time.now().mjd)
        return round(ra, 3), round(dec, 3)


@lru_cache(maxsize=1)
def targets() -> tuple[Target, ...]:
    out = []
    for t in json.loads(DATA.read_text(encoding="utf8")):
        mover = Mover(name=t["name"], catalog="preset", source=t["source"], ra=t["ra"],
                      dec=t["dec"], epoch_mjd=t["epoch_mjd"], pmra=t["pmra"], pmdec=t["pmdec"],
                      parallax_mas=t.get("parallax_mas"))
        out.append(Target(id=t["id"], name=t["name"], aliases=tuple(t["aliases"]),
                          kind=t["kind"], blurb=t["blurb"], mover=mover))
    return tuple(out)


def by_id(target_id: str) -> Target | None:
    return next((t for t in targets() if t.id == target_id), None)


def _norm(name: str) -> str:
    return " ".join(str(name).lower().replace("’", "'").split())


def by_name(name: str) -> Target | None:
    n = _norm(name)
    return next((t for t in targets() if n == _norm(t.name) or n in t.aliases), None)


def near_track(ra: float, dec: float) -> tuple[Target, float] | None:
    """(target, arcminutes it has moved from the typed position) if (ra, dec) lies on a
    target's past or present path."""
    best = None
    for t in targets():
        mjds = np.arange(51544.5, 51544.5 + 30 * 365.25, 91.3)
        d = min(separation_arcsec(ra, dec, *predict(t.mover, m)) for m in mjds) / 60.0
        if d <= MATCH_ARCMIN and (best is None or d < best[1]):
            best = (t, d)
    if best is None:
        return None
    t = best[0]
    return t, separation_arcsec(ra, dec, *predict(t.mover, Time.now().mjd)) / 60.0
