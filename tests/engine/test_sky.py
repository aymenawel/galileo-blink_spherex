"""Coordinates as people type them, catalogue prediction, and NASA's five targets."""
import math

import pytest

from galileo_blink.engine.errors import UserError
from galileo_blink.engine.sky import coords, targets
from galileo_blink.engine.sky.catalogues import parse_ipac_table
from galileo_blink.engine.sky.motion import (Mover, offset_arcsec, parallax_offset, predict,
                                               predicted_displacement, separation_arcsec)

WISE0855 = (133.795129, -7.245147)


@pytest.mark.parametrize("text", [
    "Right Ascension 08h55m10.831s, declination -7d14m42.53s",        # NASA's challenge page
    "08h55m10.831s, -7d14m42.53s",
    "08:55:10.831 -07:14:42.53",
    "08 55 10.831 -07 14 42.53",
    "133.795129 -7.245147",
    "RA = 133.795129, Dec = -7.245147",
])
def test_every_way_of_writing_nasas_wise0855_coordinate_gives_one_position(text):
    ra, dec = coords.parse_coordinates(text)
    assert separation_arcsec(ra, dec, *WISE0855) < 0.1


def test_names_are_not_mistaken_for_coordinates():
    for name in ("Barnard's Star", "M 101", "WISE 0855", "R Dra", "NGC 6543"):
        assert coords.parse_coordinates(name) is None


@pytest.mark.parametrize("text", ["400 10", "-10 20", "180 95"])
def test_out_of_range_degrees_are_refused_not_reread_as_hours(text):
    with pytest.raises(UserError):
        coords.parse_coordinates(text)


def test_nasas_wise0855_coordinate_opens_the_target_where_it_is_now():
    place = coords.resolve("Right Ascension 08h55m10.831s, declination -7d14m42.53s")
    assert place.target_id == "wise0855"
    assert 1.5 < place.moved_arcmin < 3.0                  # 2010 position; ~2 arcmin since
    assert separation_arcsec(place.ra, place.dec, *WISE0855) > 90


def test_target_names_resolve_without_the_network():
    assert coords.resolve("barnards star").target_id == "barnard"
    assert coords.resolve("R Dra").target_id == "rdra"
    assert len(targets.targets()) == 5


def test_barnards_star_moves_as_gaia_says():
    b = targets.by_id("barnard").mover
    # Aug 2025 -> Aug 2026: same time of year, so parallax cancels and ~10.4"/yr remains
    east, north = predicted_displacement(b, 60903.0, 60903.0 + 365.25)
    assert abs(math.hypot(east, north) - 10.39) < 0.05
    assert north > 10 and east < 0


def test_parallax_is_a_yearly_wobble_of_the_right_size():
    b = targets.by_id("barnard").mover
    sizes = [math.hypot(*parallax_offset(b.ra, b.dec, b.parallax_mas, 60900.0 + d))
             for d in range(0, 366, 10)]
    assert 0.5 < max(sizes) <= 0.5470 * 1.02               # at most parallax x Earth's distance
    e1, n1 = parallax_offset(b.ra, b.dec, b.parallax_mas, 60900.0)
    e2, n2 = parallax_offset(b.ra, b.dec, b.parallax_mas, 60900.0 + 182.6)
    assert e1 * e2 + n1 * n2 < 0                           # opposite sides six months apart


def test_parallax_matches_an_independent_astropy_calculation():
    import astropy.units as u
    from astropy.coordinates import GCRS, ICRS, SkyCoord
    from astropy.time import Time
    ra, dec, plx, mjd = 269.45, 4.74, 546.98, 61100.0
    star = SkyCoord(ra * u.deg, dec * u.deg, distance=(1000.0 / plx) * u.pc, frame=ICRS)
    far = SkyCoord(ra * u.deg, dec * u.deg, distance=1e9 * u.pc, frame=ICRS)
    t = Time(mjd, format="mjd")
    de, dn = far.transform_to(GCRS(obstime=t)).spherical_offsets_to(star.transform_to(GCRS(obstime=t)))
    east, north = parallax_offset(ra, dec, plx, mjd)
    assert abs(east - de.to_value(u.arcsec)) < 0.005 and abs(north - dn.to_value(u.arcsec)) < 0.005


def test_a_mover_without_parallax_moves_in_a_straight_line():
    m = Mover("x", "CatWISE2020", "x", 100.0, 60.0, 57170.0, pmra=2.0, pmdec=-1.0)
    east, north = offset_arcsec(100.0, 60.0, *predict(m, 57170.0 + 365.25 * 10))
    assert abs(east - 20.0) < 0.02 and abs(north + 10.0) < 0.01


def test_ipac_tables_parse():
    text = "\\fixlen = T\n|  ra_pm| dec_pm|  source_name|\n| double| double|   char|\n 133.79  -7.24  J0855\n"
    assert parse_ipac_table(text) == [{"ra_pm": "133.79", "dec_pm": "-7.24", "source_name": "J0855"}]


def test_a_fast_star_typed_at_its_year_2000_position_opens_where_it_is_now(monkeypatch):
    # Proxima-like: 3.85"/yr; Gaia's position is for 2016.0
    star = Mover("Gaia DR3 1", "Gaia DR3", "Gaia DR3 1", 217.39, -62.676, 57388.5, pmra=-3.78, pmdec=0.77)
    slow = Mover("Gaia DR3 2", "Gaia DR3", "Gaia DR3 2", 217.40, -62.68, 57388.5, pmra=0.004, pmdec=0.002)
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda ra, dec, r: [slow, star])
    j2000 = predict(star, 51544.5)
    place = coords.resolve(f"{j2000[0]:.5f} {j2000[1]:.5f}")
    assert place.follows == "Gaia DR3 1" and 1.4 < place.moved_arcmin < 2.0
    assert separation_arcsec(place.ra, place.dec, *predict(star, 61100.0)) < 1.0


def test_an_ordinary_place_is_left_where_it_was_typed(monkeypatch):
    slow = Mover("Gaia DR3 2", "Gaia DR3", "Gaia DR3 2", 180.0, 0.0, 57388.5, pmra=0.004, pmdec=0.002)
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda ra, dec, r: [slow])
    place = coords.resolve("180.0 0.0")
    assert (place.ra, place.dec, place.follows, place.moved_arcmin) == (180.0, 0.0, None, None)

    def down(ra, dec, r):
        raise RuntimeError("catalogue down")
    monkeypatch.setattr(coords.catalogues, "gaia_cone", down)
    assert coords.resolve("180.0 0.0").follows is None            # the lookup is optional


def test_catwise_echoes_of_a_bright_fast_star_are_not_marked():
    from galileo_blink.engine.sky.catalogues import fast_movers
    from .synth import offset_sky
    barnard = Mover("Gaia DR3 B", "Gaia DR3", "g", 269.4485, 4.7394, 57388.5, pmra=-0.80, pmdec=10.36)
    at_catwise_epoch = predict(barnard, 57170.0)
    echoes = [Mover(f"CatWISE2020 e{i}", "CatWISE2020", "c", *offset_sky(*at_catwise_epoch, 20.0 * i, -30.0),
                    57170.0, pmra=-0.6, pmdec=9.0 + 0.1 * i) for i in range(1, 6)]
    brown_dwarf = Mover("CatWISE2020 bd", "CatWISE2020", "c", *offset_sky(*at_catwise_epoch, 200.0, 100.0),
                        57170.0, pmra=-8.0, pmdec=0.7)          # a real, different mover
    unrelated = Mover("CatWISE2020 u", "CatWISE2020", "c", *offset_sky(*at_catwise_epoch, 40.0, 40.0),
                      57170.0, pmra=3.0, pmdec=-2.0)            # near, but moving differently
    marked = fast_movers([barnard], echoes + [brown_dwarf, unrelated])
    assert [m.name for m in marked] == ["Gaia DR3 B", "CatWISE2020 bd", "CatWISE2020 u"]
