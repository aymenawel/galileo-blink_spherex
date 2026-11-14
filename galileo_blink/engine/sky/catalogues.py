"""Star catalogues: which objects in a field are known to move, and which can serve as fixed
reference points.

Gaia DR3 comes from NASA's MAST archive (it answers in a couple of seconds). CatWISE2020,
which sees the cold brown dwarfs Gaia cannot, comes from NASA/IPAC IRSA.
"""
from __future__ import annotations

import json
import math

from .. import constants as C
from ..archive import http
from .motion import Mover, predict, separation_arcsec

MAST = "https://mast.stsci.edu/api/v0/invoke"
MAST_SERVICE = "NASA's MAST archive (Gaia catalogue)"
GATOR = C.IRSA + "/cgi-bin/Gator/nph-query"
GATOR_SERVICE = "NASA's IRSA catalogue service (CatWISE)"
MAST_PAGE = 20000
FRAGMENT_ARCSEC = 5.0
FRAGMENT_PM = 1.0


def gaia_cone(ra: float, dec: float, radius_deg: float) -> list[Mover]:
    """Every Gaia DR3 source with a measured motion inside the cone."""
    out: list[Mover] = []
    page = 1
    while True:
        req = {"service": "Mast.Catalogs.GaiaDR3.Cone", "format": "json", "pagesize": MAST_PAGE,
               "page": page, "params": {"ra": ra, "dec": dec, "radius": radius_deg}}
        r = http.request("POST", MAST, service=MAST_SERVICE, timeout=C.CATALOGUE_TIMEOUT_S,
                         retries=1, data={"request": json.dumps(req)})
        body = r.json()
        for row in body.get("data") or []:
            if row.get("pmra") is None or row.get("pmdec") is None:
                continue
            plx = row.get("parallax")
            out.append(Mover(
                name=f"Gaia DR3 {row['source_id']}", catalog="Gaia DR3",
                source=f"Gaia DR3 {row['source_id']}", ra=float(row["ra"]), dec=float(row["dec"]),
                epoch_mjd=C.GAIA_EPOCH_MJD, pmra=row["pmra"] / 1000.0, pmdec=row["pmdec"] / 1000.0,
                parallax_mas=float(plx) if plx and plx > 0 else None,
                gmag=row.get("phot_g_mean_mag")))
        paging = body.get("paging") or {}
        if page >= int(paging.get("pagesFiltered", 1) or 1):
            return out
        page += 1


def parse_ipac_table(text: str) -> list[dict]:
    """Rows of an IPAC-format text table as dicts of strings."""
    names, rows = None, []
    for line in text.splitlines():
        if line.startswith("\\") or not line.strip():
            continue
        if line.startswith("|"):
            if names is None:
                names = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        if names:
            cells = line.split()
            if len(cells) == len(names):
                rows.append(dict(zip(names, cells)))
    return rows


def catwise_cone(ra: float, dec: float, radius_deg: float) -> list[Mover]:
    """CatWISE2020 sources moving fast and significantly, with fragments of one object merged
    (CatWISE splits fast movers into several entries with the same motion)."""
    params = dict(catalog="catwise_2020", spatial="cone", radius=f"{radius_deg * 3600:.1f}",
                  radunits="arcsec", objstr=f"{ra:.6f} {dec:.6f}", outfmt=1,
                  selcols="source_name,ra_pm,dec_pm,pmra,pmdec,sigpmra,sigpmdec",
                  constraints=f"pmra*pmra+pmdec*pmdec>={C.CATWISE_MIN_PM_ARCSEC_YR ** 2}")
    r = http.get(GATOR, service=GATOR_SERVICE, params=params, timeout=C.CATALOGUE_TIMEOUT_S)
    merged: list[Mover] = []
    for row in parse_ipac_table(r.text):
        try:
            pmra, pmdec = float(row["pmra"]), float(row["pmdec"])
            sig = math.hypot(float(row["sigpmra"]), float(row["sigpmdec"]))
            cra, cdec = float(row["ra_pm"]), float(row["dec_pm"])
        except (KeyError, ValueError):
            continue
        pm = math.hypot(pmra, pmdec)
        if pm < C.CATWISE_MIN_PM_ARCSEC_YR or sig <= 0 or pm / sig < C.CATWISE_MIN_SIGNIFICANCE:
            continue
        if any(separation_arcsec(m.ra, m.dec, cra, cdec) <= FRAGMENT_ARCSEC
               and math.hypot(m.pmra - pmra, m.pmdec - pmdec) <= FRAGMENT_PM for m in merged):
            continue
        name = f"CatWISE2020 {row['source_name']}"
        merged.append(Mover(name=name, catalog="CatWISE2020", source=name, ra=cra, dec=cdec,
                            epoch_mjd=C.CATWISE_EPOCH_MJD, pmra=pmra, pmdec=pmdec))
    return merged


def fast_movers(gaia: list[Mover], catwise: list[Mover]) -> list[Mover]:
    """Objects worth marking: Gaia stars above the marking speed, plus CatWISE movers that are
    not simply the same Gaia star again. Fastest first."""
    out = [g for g in gaia if g.pm_total >= C.MIN_PM_MARK_ARCSEC_YR]
    for c in catwise:
        if not any(separation_arcsec(*predict(g, C.CATWISE_EPOCH_MJD), c.ra, c.dec)
                   <= FRAGMENT_ARCSEC for g in out):
            out.append(c)
    return sorted(out, key=lambda m: -m.pm_total)
