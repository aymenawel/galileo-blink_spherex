"""Group a place's photos into looks and seasons, and choose which photos a view uses.

SPHEREx returns to most of the sky about every six months and takes a handful of photos each
time: a *look*. The six cameras do not look on the same days, so the screen steps through
*seasons*: looks from all cameras whose middle dates fall close together. Near the ecliptic
poles coverage never stops, so long looks are cut by calendar month.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from astropy.time import Time

from .. import constants as C
from ..archive.photos import PhotoRef


@dataclass
class Season:
    index: int
    mjd: float                                    # middle date
    by_camera: dict[int, list[PhotoRef]] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return Time(self.mjd, format="mjd").datetime.strftime("%b %Y")

    @property
    def date(self) -> str:
        return Time(self.mjd, format="mjd").iso[:10]


def _middle(photos: list[PhotoRef]) -> float:
    return float(np.median([p.mjd for p in photos]))


def _month(mjd: float) -> str:
    return Time(mjd, format="mjd").iso[:7]


def camera_looks(photos: list[PhotoRef]) -> list[tuple[list[PhotoRef], str | None]]:
    """One camera's photos split into looks: (photos, month). `month` ("2026-03") is set only
    for looks cut out of continuous coverage; an ordinary look has None."""
    photos = sorted(photos, key=lambda p: p.mjd)
    runs: list[list[PhotoRef]] = []
    for p in photos:
        if runs and p.mjd - runs[-1][-1].mjd <= C.LOOK_GAP_DAYS:
            runs[-1].append(p)
        else:
            runs.append([p])
    looks: list[tuple[list[PhotoRef], str | None]] = []
    for run in runs:
        if run[-1].mjd - run[0].mjd <= C.LONG_LOOK_DAYS:
            looks.append((run, None))
            continue
        months: dict[str, list[PhotoRef]] = {}
        for p in run:
            months.setdefault(_month(p.mjd), []).append(p)
        looks.extend((months[m], m) for m in sorted(months))
    return looks


def group_seasons(photos: list[PhotoRef], cameras=(1, 2, 3, 4, 5, 6)) -> list[Season]:
    """Every camera's looks gathered into shared seasons, oldest first.

    Looks cut from continuous coverage share a season per calendar month. Ordinary looks join
    the month-season their middle date falls in, if any; otherwise they chain with their
    neighbours in time (within SEASON_LINK_DAYS, never spanning more than SEASON_SPAN_DAYS)."""
    monthly: dict[str, list] = {}
    ordinary = []
    for cam in cameras:
        for look, month in camera_looks([p for p in photos if p.camera == cam]):
            item = (_middle(look), cam, look)
            if month:
                monthly.setdefault(month, []).append(item)
            else:
                ordinary.append(item)
    groups: list[list] = []
    for item in sorted(ordinary, key=lambda it: it[0]):
        month = _month(item[0])
        if month in monthly:
            monthly[month].append(item)
        elif (groups and item[0] - groups[-1][-1][0] <= C.SEASON_LINK_DAYS
                and item[0] - groups[-1][0][0] <= C.SEASON_SPAN_DAYS):
            groups[-1].append(item)
        else:
            groups.append([item])
    groups += list(monthly.values())
    groups.sort(key=lambda g: float(np.median([it[0] for it in g])))
    seasons = []
    for i, group in enumerate(groups):
        season = Season(index=i, mjd=float(np.median([g[0] for g in group])))
        for _, cam, look in group:                # two looks of one camera in a season merge
            season.by_camera.setdefault(cam, []).extend(look)
        for cam in season.by_camera:
            season.by_camera[cam].sort(key=lambda p: p.mjd)
        seasons.append(season)
    return seasons


def spread(photos: list[PhotoRef], n: int) -> list[PhotoRef]:
    """n photos spread evenly through the list (all of them if there are fewer)."""
    if n >= len(photos):
        return list(photos)
    idx = sorted(set(np.linspace(0, len(photos) - 1, n).round().astype(int).tolist()))
    return [photos[i] for i in idx]


def choose(seasons: list[Season], per_look: int, max_seasons: int, max_photos: int
           ) -> tuple[list[Season], int]:
    """The seasons and photos a view will use: at most `per_look` photos per camera per season,
    the first and last seasons always kept and the rest spaced evenly, within both limits.
    Returns (seasons renumbered from 0, how many seasons were left out)."""
    if not seasons:
        return [], 0

    def cost(keep):
        return sum(min(per_look, len(ps)) for i in keep for ps in seasons[i].by_camera.values())

    n = len(seasons)
    k = min(n, max_seasons)
    keep = list(range(n))
    while k >= 1:
        keep = sorted(set(np.linspace(0, n - 1, k).round().astype(int).tolist())) if k > 1 else [n - 1]
        if cost(keep) <= max_photos or k == 1:
            break
        k -= 1
    chosen = []
    for new_index, i in enumerate(keep):
        s = seasons[i]
        chosen.append(Season(index=new_index, mjd=s.mjd,
                             by_camera={cam: spread(ps, per_look) for cam, ps in s.by_camera.items()}))
    return chosen, n - len(keep)
