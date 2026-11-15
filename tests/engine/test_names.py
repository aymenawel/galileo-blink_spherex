"""Names typed into the search box when the name services are down, slow or confused."""
import json
import time

import pytest

from galileo_blink.engine.errors import ServiceDown, UserError
from galileo_blink.engine.sky import coords
from galileo_blink.engine.sky.motion import separation_arcsec


@pytest.fixture
def no_name_service(monkeypatch):
    """Every name service fails, and Gaia has nothing nearby."""
    asked = []

    def down(*args, **kwargs):
        asked.append(args)
        raise ServiceDown(coords.NAME_SERVICE, "HTTP 503")
    monkeypatch.setattr(coords, "_sesame", down)
    monkeypatch.setattr(coords, "_ned", down)
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda *a, **k: [])
    return asked


@pytest.mark.parametrize("name, ra, dec", [
    ("Proxima Centauri", 217.4289, -62.6795), ("proxima", 217.4289, -62.6795),
    ("Alpha Centauri", 219.9021, -60.8340), ("Wolf 359", 164.1205, 7.0147),
    ("Teegarden’s Star", 43.2537, 16.8813), ("Luhman 16", 162.3288, -53.3195),
    ("Kapteyn's Star", 77.9191, -45.0184), ("Lalande 21185", 165.8341, 35.9699),
    ("Ross 128", 176.9350, 0.8046), ("Sirius", 101.2872, -16.7161), ("VEGA", 279.2347, 38.7837),
    ("Betelgeuse", 88.7929, 7.4071), ("Polaris", 37.9546, 89.2641), ("Aldebaran", 68.9802, 16.5093),
    ("M31", 10.6847, 41.2688), ("Andromeda Galaxy", 10.6847, 41.2688), ("M 42", 83.8201, -5.3876),
    ("Orion Nebula", 83.8201, -5.3876), ("Pleiades", 56.6008, 24.1139), ("M13", 250.4235, 36.4613),
    ("Sagittarius A*", 266.4168, -29.0078), ("galactic center", 266.4168, -29.0078),
    ("LMC", 80.8942, -69.7561), ("Small Magellanic Cloud", 13.1583, -72.8003),
])
def test_well_known_names_resolve_with_every_name_service_down(no_name_service, name, ra, dec):
    place = coords.resolve(name)
    assert separation_arcsec(place.ra, place.dec, ra, dec) < 1.0
    assert place.kind == "name" and not no_name_service


def test_an_unknown_name_with_every_service_down_is_an_outage_not_a_typo(no_name_service):
    with pytest.raises(ServiceDown):
        coords.resolve("HD 12345678")


def test_ned_knowing_nothing_is_not_a_not_found_when_sesame_is_down(monkeypatch):
    def down(*args, **kwargs):
        raise ServiceDown(coords.NAME_SERVICE, "HTTP 503")
    monkeypatch.setattr(coords, "_sesame", down)
    monkeypatch.setattr(coords, "_ned", lambda name: None)       # NED answers, but knows no stars
    with pytest.raises(ServiceDown):
        coords.lookup_name("Gliese 1002")


def test_sesame_answering_no_such_object_is_the_visitors_typo(monkeypatch):
    monkeypatch.setattr(coords, "_sesame", lambda base, name: None)
    monkeypatch.setattr(coords, "_ned", lambda name: None)
    with pytest.raises(UserError):
        coords.lookup_name("Barnad's Starr")


def test_the_two_sesame_mirrors_are_asked_at_once(monkeypatch):
    def slow_first(base, name):
        if base == coords.SESAME_MIRRORS[0]:
            time.sleep(1.0)
            return None
        return (10.0, 20.0)
    monkeypatch.setattr(coords, "_sesame", slow_first)
    monkeypatch.setattr(coords, "_ned", lambda name: None)
    t = time.time()
    assert coords.lookup_name("Gliese 1002") == (10.0, 20.0)
    assert time.time() - t < 0.8


def test_the_whole_name_lookup_has_one_deadline(monkeypatch):
    monkeypatch.setattr(coords, "NAME_DEADLINE_S", 0.3)

    def hang(*args, **kwargs):
        time.sleep(2.0)
        return None
    monkeypatch.setattr(coords, "_sesame", hang)
    monkeypatch.setattr(coords, "_ned", hang)
    t = time.time()
    with pytest.raises(ServiceDown):
        coords.lookup_name("Gliese 1002")
    assert time.time() - t < 1.0


def test_sesames_answer_is_preferred_to_neds(monkeypatch):
    def sesame(base, name):
        time.sleep(0.2)
        return (1.0, 2.0)
    monkeypatch.setattr(coords, "_sesame", sesame)
    monkeypatch.setattr(coords, "_ned", lambda name: (3.0, 4.0))
    assert coords.lookup_name("Gliese 1002") == (1.0, 2.0)


@pytest.mark.parametrize("text, words", [
    ("dec 95", ["Declination", "-90 to +90", "95 is off the sky", "Example: 269.452 4.693."]),
    ("180 95", ["Declination", "95 is off the sky"]),
    ("RA 10, Dec -91.5", ["Declination", "-91.5 is off the sky"]),
    ("ra 400 dec 10", ["Right ascension", "0 to 360 degrees", "400 is off the sky"]),
    ("400 10", ["Right ascension", "400 is off the sky"]),
    ("-10 20", ["Right ascension", "-10 is off the sky"]),
    ("ra 400", ["Right ascension", "400 is off the sky"]),
    ("25h00m00s +10d00m00s", ["Right ascension", "24 hours", "25h is off the sky"]),
    ("25:00:00 +10:00:00", ["Right ascension", "24 hours"]),
    ("17h57m48.5s +95d00m00s", ["Declination", "95 is off the sky"]),
    ("17 57 48.5 +95 00 00", ["Declination", "95 is off the sky"]),
    ("370d 10d", ["Right ascension", "370 is off the sky"]),
    ("dec 45", ["two numbers"]),
    ("12.5", ["two numbers"]),
])
def test_coordinates_off_the_sky_say_what_is_wrong(no_name_service, text, words):
    with pytest.raises(UserError) as e:
        coords.resolve(text)
    for w in words:
        assert w in str(e.value), (text, str(e.value))
    assert "No object called" not in str(e.value) and not no_name_service


@pytest.mark.parametrize("name", ["Jupiter", "mars", "The Moon", "Moon", "Sun", "Saturn", "Pluto"])
def test_planets_are_explained_not_looked_up(no_name_service, name):
    with pytest.raises(UserError) as e:
        coords.resolve(name)
    assert str(e.value) == ("Planets move too fast to have a fixed place in the sky. For an asteroid, "
                            "use Find it under Asteroids on the home page.")
    assert not no_name_service


@pytest.mark.parametrize("name", ["Planet X", "planet nine", "Planet 9"])
def test_planet_x_is_explained(no_name_service, name):
    with pytest.raises(UserError) as e:
        coords.resolve(name)
    assert str(e.value) == ("Nobody has found Planet X yet, so it has no place to open. Try Barnard's "
                            "Star, or one of NASA's five test targets.")


@pytest.mark.parametrize("name", ["WISE 1049-5319", "2MASS J0523-1403", "3C 273", "M 101", "Gliese 229 B"])
def test_names_with_numbers_still_go_to_the_name_service(monkeypatch, name):
    monkeypatch.setattr(coords, "_sesame", lambda base, n: (100.0, 10.0))
    monkeypatch.setattr(coords, "_ned", lambda n: None)
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda *a, **k: [])
    assert coords.resolve(name).kind == "name"


def test_follow_mover_asks_gaia_briefly_and_only_once(monkeypatch):
    seen = {}

    def gaia(ra, dec, radius, **kwargs):
        seen.update(kwargs)
        raise ServiceDown("MAST", "ReadTimeout", timed_out=True)
    monkeypatch.setattr(coords.catalogues, "gaia_cone", gaia)
    assert coords.follow_mover(180.0, 0.0) is None
    assert seen["timeout"] <= 8 and seen["retries"] == 0


def test_gaia_cone_passes_its_deadline_to_the_request(monkeypatch):
    from galileo_blink.engine.sky import catalogues
    seen = {}

    class Answer:
        def json(self):
            return {"data": [], "paging": {"pagesFiltered": 1}}

    def request(method, url, **kwargs):
        seen.update(kwargs)
        return Answer()
    monkeypatch.setattr(catalogues.http, "request", request)
    assert catalogues.gaia_cone(1.0, 2.0, 0.1, timeout=8, retries=0) == []
    assert seen["timeout"] == 8 and seen["retries"] == 0
    catalogues.gaia_cone(1.0, 2.0, 0.1)
    assert seen["timeout"] == catalogues.C.CATALOGUE_TIMEOUT_S and seen["retries"] == 1


def test_the_offline_names_file_is_well_formed():
    rows = json.loads(coords.NAMES_FILE.read_text(encoding="utf8"))
    for row in rows:
        assert 0 <= row["ra"] < 360 and -90 <= row["dec"] <= 90
        assert all(a == a.lower() for a in row["aliases"])


def test_one_mirror_saying_no_is_enough_when_the_other_hangs(monkeypatch):
    def sesame(base, name):
        if base == coords.SESAME_MIRRORS[1]:
            time.sleep(2.0)
            raise ServiceDown(coords.NAME_SERVICE, "ReadTimeout", timed_out=True)
        return None
    monkeypatch.setattr(coords, "_sesame", sesame)
    monkeypatch.setattr(coords, "_ned", lambda name: None)
    t = time.time()
    with pytest.raises(UserError):
        coords.lookup_name("Gliese 229")
    assert time.time() - t < 1.0
