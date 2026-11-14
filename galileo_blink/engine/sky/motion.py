"""Where a catalogued object is on a given date.

A catalogue gives a position at one date (its epoch), a proper motion (steady drift across the
sky, arcsec per year) and, for nearby objects, a parallax (the yearly wobble caused by Earth
going round the Sun). SPHEREx orbits close to Earth, so Earth's position is close enough.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import astropy.units as u
from astropy.coordinates import get_body_barycentric
from astropy.time import Time

DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Mover:
    """A catalogued object with a known motion."""
    name: str
    catalog: str                  # "Gaia DR3", "CatWISE2020" or "preset"
    source: str                   # where the numbers come from, citable
    ra: float                     # degrees, at epoch_mjd
    dec: float
    epoch_mjd: float
    pmra: float                   # arcsec/yr eastward on the sky (already includes cos(dec))
    pmdec: float                  # arcsec/yr northward
    parallax_mas: float | None = None
    gmag: float | None = None     # Gaia G magnitude, when known

    @property
    def pm_total(self) -> float:
        return math.hypot(self.pmra, self.pmdec)

    def to_dict(self) -> dict:
        return asdict(self)


def earth_position_au(mjd: float) -> tuple[float, float, float]:
    """Earth's position relative to the solar-system barycentre (equatorial x, y, z in AU)."""
    xyz = get_body_barycentric("earth", Time(float(mjd), format="mjd")).get_xyz().to(u.au).value
    return float(xyz[0]), float(xyz[1]), float(xyz[2])


def parallax_offset(ra: float, dec: float, parallax_mas: float, mjd: float) -> tuple[float, float]:
    """(east, north) displacement in arcsec caused by parallax on that date."""
    x, y, z = earth_position_au(mjd)
    a, d = math.radians(ra), math.radians(dec)
    p = parallax_mas / 1000.0
    east = p * (x * math.sin(a) - y * math.cos(a))
    north = p * (x * math.cos(a) * math.sin(d) + y * math.sin(a) * math.sin(d) - z * math.cos(d))
    return east, north


def predict(m: Mover, mjd: float) -> tuple[float, float]:
    """(ra, dec) in degrees where the catalogue says `m` is at `mjd`."""
    years = (float(mjd) - m.epoch_mjd) / DAYS_PER_YEAR
    dec = m.dec + m.pmdec * years / 3600.0
    ra = m.ra + m.pmra * years / 3600.0 / max(math.cos(math.radians(dec)), 1e-6)
    if m.parallax_mas and m.parallax_mas > 0:
        east, north = parallax_offset(ra, dec, m.parallax_mas, mjd)
        dec += north / 3600.0
        ra += east / 3600.0 / max(math.cos(math.radians(dec)), 1e-6)
    return ra % 360.0, max(-90.0, min(90.0, dec))


def offset_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> tuple[float, float]:
    """(east, north) from point 1 to point 2, in arcsec (small-angle, fine for a field of view)."""
    dra = ((ra2 - ra1 + 180.0) % 360.0) - 180.0
    return (dra * 3600.0 * math.cos(math.radians(0.5 * (dec1 + dec2))), (dec2 - dec1) * 3600.0)


def separation_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    return math.hypot(*offset_arcsec(ra1, dec1, ra2, dec2))


def predicted_displacement(m: Mover, mjd_a: float, mjd_b: float) -> tuple[float, float]:
    """(east, north) arcsec the catalogue predicts `m` moves between two dates."""
    return offset_arcsec(*predict(m, mjd_a), *predict(m, mjd_b))
