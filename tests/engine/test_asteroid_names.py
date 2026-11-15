"""Famous asteroids are listed twice in NASA's moving-object search (an old entry and the
numbered one), so their plain names come back as "multiple matches". The engine must pick the
numbered asteroid and ask again, not tell the visitor the asteroid is unknown."""
import pytest

from galileo_blink.engine.errors import UserError
from galileo_blink.engine.sky import asteroids

AMBIGUOUS = """
Object Name Error:

User Input String=Vesta

Multiple matches to the input string in the list from Horizons.

Vesta, Object Type=Asteroid, NAIF ID=2000004, Designation=NO_VALUE 
4 Vesta, Object Type=Asteroid, NAIF ID=20000004, Designation=A807 FA 

Hints: If the name is ambiguous, search using the NAIF ID.
"""

SEVERAL = """
Multiple matches to the input string in the list from Horizons.

Io, Object Type=Satellite, NAIF ID=501, Designation=NO_VALUE 
85 Io, Object Type=Asteroid, NAIF ID=20000085, Designation=A865 SA 
1234 Iona, Object Type=Asteroid, NAIF ID=20001234, Designation=NO_VALUE 
"""


def test_the_numbered_asteroid_is_picked_from_a_list_of_matches():
    assert asteroids.numbered_match(AMBIGUOUS, "Vesta") == "4"
    assert asteroids.numbered_match(AMBIGUOUS, "vesta") == "4"
    # the entry whose name is exactly what was typed wins over one that only starts like it
    assert asteroids.numbered_match(SEVERAL, "Io") == "85"


def test_an_answer_that_is_not_a_list_of_matches_picks_nothing():
    assert asteroids.numbered_match("Object Name Error: not found", "Vesta") is None
    assert asteroids.numbered_match(AMBIGUOUS, "Ceres") is None


class _Answer:
    def __init__(self, text):
        self.text = text


def test_a_famous_name_is_asked_again_by_its_number(monkeypatch):
    asked = []

    def fake_get(url, *, params, **kwargs):
        asked.append(params["obj_name"])
        return _Answer(AMBIGUOUS if params["obj_name"] == "Vesta" else "\\object_name = 4 Vesta\n")

    monkeypatch.setattr(asteroids.http, "get", fake_get)
    monkeypatch.setattr(asteroids, "parse_most",
                        lambda text: ("4 Vesta (A807 FA)", ["a sighting"]) if "object_name" in text else (None, []))
    name, sightings = asteroids.asteroid_sightings("Vesta")
    assert asked == ["Vesta", "4"]
    assert name == "4 Vesta (A807 FA)" and sightings == ["a sighting"]


def test_a_name_nobody_knows_is_still_the_visitors_to_fix(monkeypatch):
    monkeypatch.setattr(asteroids.http, "get",
                        lambda url, **kwargs: _Answer("Object Name Error:\nUser Input String=zzz\nnot found"))
    with pytest.raises(UserError):
        asteroids.asteroid_sightings("zzz")


def test_the_list_of_matches_is_read_even_when_it_arrives_as_an_error_answer(monkeypatch):
    """NASA's search sends "multiple matches" with an error status (HTTP 400)."""
    from galileo_blink.engine.errors import ServiceDown
    asked = []

    def fake_get(url, *, params, **kwargs):
        asked.append(params["obj_name"])
        if params["obj_name"] == "Vesta":
            raise ServiceDown(asteroids.MOST_SERVICE, "HTTP 400", body=AMBIGUOUS)
        return _Answer("\\object_name = 4 Vesta\n")

    monkeypatch.setattr(asteroids.http, "get", fake_get)
    monkeypatch.setattr(asteroids, "parse_most", lambda text: ("4 Vesta (A807 FA)", ["a sighting"]))
    name, sightings = asteroids.asteroid_sightings("Vesta")
    assert asked == ["Vesta", "4"] and name == "4 Vesta (A807 FA)"


def test_a_refused_request_keeps_what_the_service_said(monkeypatch):
    from galileo_blink.engine.archive import http
    from galileo_blink.engine.errors import ServiceDown

    class Refusal:
        status_code = 400
        text = "Object Name Error: Multiple matches"

    class Session:
        def request(self, *args, **kwargs):
            return Refusal()

    monkeypatch.setattr(http, "session", lambda: Session())
    with pytest.raises(ServiceDown) as caught:
        http.get("https://example.invalid/", service="a test service")
    assert caught.value.detail == "HTTP 400" and "Multiple matches" in caught.value.body


def test_a_hiccup_on_the_second_ask_is_an_outage_not_an_unknown_asteroid(monkeypatch):
    """If the search refuses the very number it just listed, that is its problem: the visitor
    is asked to try again, and is never told that "4" is an unknown asteroid."""
    from galileo_blink.engine.errors import ServiceDown

    def fake_get(url, *, params, **kwargs):
        body = AMBIGUOUS if params["obj_name"] == "Vesta" else "Object Name Error"
        raise ServiceDown(asteroids.MOST_SERVICE, "HTTP 400", body=body)

    monkeypatch.setattr(asteroids.http, "get", fake_get)
    with pytest.raises(ServiceDown):
        asteroids.asteroid_sightings("Vesta")
