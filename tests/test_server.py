"""The HTTP layer, with the engine's build step replaced by a fake (no network)."""
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive.cache import write_json
from galileo_blink.engine.errors import ServiceDown, UserError
from galileo_blink.engine.image import render
from galileo_blink.engine.looks.build import view_dir
from galileo_blink.server.app import create_app
from galileo_blink.server.jobs import Builder


def fake_build(req, progress):
    progress("Fetching photos from NASA", 0.5)
    if abs(req.dec - 10.0) < 1e-6:
        raise ServiceDown("NASA's image archive (IRSA)", "HTTP 502")
    if abs(req.dec - 20.0) < 1e-6:
        raise UserError("SPHEREx has no photos of this place yet.")
    if abs(req.dec - 30.0) < 1e-6:
        raise KeyError("uri")
    out = view_dir(req.key)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1, (9, 9)), rng.normal(0, 1, (9, 9))
    np.savez(out / "stacks.npz", c6_all=a, c6_s0=a, c6_s1=b)
    (out / "c6_s0.png").write_bytes(render.gray_png(np.clip(a, 0, 1)))
    write_json(out / "view.json", dict(kind="looks", engine=C.ENGINE_VERSION, key=req.key,
                                       ra=req.ra, dec=req.dec, degraded=[]))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path))
    from galileo_blink.engine.sky import coords
    from galileo_blink.server import jobs
    monkeypatch.setattr(jobs, "PREBUILT_DIR", tmp_path / "prebuilt")    # ignore shipped views
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda ra, dec, r: [])
    return TestClient(create_app(Builder(build=fake_build)))


def wait(client, key):
    for _ in range(100):
        s = client.get(f"/api/view/{key}").json()
        if s["state"] in ("ready", "failed"):
            return s
        time.sleep(0.02)
    raise AssertionError("the build never finished")


def test_a_view_is_built_once_then_served(client):
    first = client.get("/api/view", params=dict(ra=180, dec=0)).json()
    assert first["state"] in ("queued", "building", "ready")
    done = wait(client, first["key"])
    assert done["state"] == "ready" and done["view"]["ra"] == 180
    again = client.get("/api/view", params=dict(ra=180, dec=0)).json()
    assert again == dict(key=first["key"], state="ready")


def test_the_five_targets_are_listed_with_stable_keys(client):
    listed = client.get("/api/targets").json()
    assert [t["id"] for t in listed] == ["barnard", "epsindib", "wise0855", "rwaur", "rdra"]
    assert listed[0]["key"] == "target-barnard" and listed[0]["ready"] is False
    key = client.get("/api/view", params=dict(target="barnard")).json()["key"]
    assert key == "target-barnard" and wait(client, key)["state"] == "ready"


def test_nasas_own_coordinate_text_resolves(client):
    r = client.get("/api/resolve", params=dict(q="Right Ascension 08h55m10.831s, declination -7d14m42.53s"))
    assert r.status_code == 200 and r.json()["target_id"] == "wise0855"


@pytest.mark.parametrize("params", [dict(ra=400, dec=0), dict(ra=10, dec=95), dict(ra=10),
                                    dict(ra=10, dec=0, size=5), dict(target="pluto")])
def test_bad_requests_are_explained_as_the_visitors_to_fix(client, params):
    r = client.get("/api/view", params=params)
    assert r.status_code == 400 and r.json()["error_kind"] == "request"


def test_failures_say_whose_fault_they_are(client):
    for dec, kind in ((10.0, "service"), (20.0, "request"), (30.0, "internal")):
        key = client.get("/api/view", params=dict(ra=50, dec=dec)).json()["key"]
        s = wait(client, key)
        assert s["state"] == "failed" and s["error_kind"] == kind
    assert "uri" not in s["error"]                      # internals are never shown to visitors


def test_a_failed_view_can_be_tried_again(client):
    key = client.get("/api/view", params=dict(ra=50, dec=10.0)).json()["key"]
    assert wait(client, key)["state"] == "failed"
    assert client.get("/api/view", params=dict(ra=50, dec=10.0)).json()["state"] in ("queued", "building", "failed")


def test_pictures_are_served_and_nothing_else_is(client):
    key = client.get("/api/view", params=dict(ra=180, dec=0)).json()["key"]
    wait(client, key)
    r = client.get(f"/files/{key}/c6_s0.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "no-cache"
    assert client.get(f"/files/{key}/stacks.npz").status_code == 404
    assert client.get(f"/files/{key}/..%2Fview.json").status_code == 404
    assert client.get("/files/nope/c6_s0.png").status_code == 404


def test_any_two_seasons_can_be_subtracted_or_added(client):
    key = client.get("/api/view", params=dict(ra=180, dec=0)).json()["key"]
    wait(client, key)
    for op in ("subtract", "add"):
        r = client.get(f"/api/view/{key}/compare", params=dict(camera=6, a="1", b="0", op=op))
        assert r.status_code == 200 and r.content[:4] == b"\x89PNG"
    assert client.get(f"/api/view/{key}/compare", params=dict(camera=2, a="1", b="0")).status_code == 400


def test_an_unknown_view_is_a_404(client):
    assert client.get("/api/view/doesnotexist").status_code == 404


def test_a_spectrum_can_be_asked_for_anywhere(client, monkeypatch):
    from galileo_blink.engine.spectrum import cube
    monkeypatch.setattr(cube, "quick_spectrum", lambda ra, dec: dict(ra=ra, dec=dec, points=[], unit="mJy"))
    assert client.get("/api/spectrum", params=dict(ra=10, dec=20)).json()["unit"] == "mJy"
    assert client.get("/api/spectrum", params=dict(ra=10, dec=120)).status_code == 422

    def down(ra, dec):
        raise ServiceDown(cube.SERVICE, "HTTP 503")
    monkeypatch.setattr(cube, "quick_spectrum", down)
    r = client.get("/api/spectrum", params=dict(ra=10, dec=20))
    assert r.status_code == 502 and r.json()["error_kind"] == "service"


def test_the_asteroid_view_opens_by_place_or_by_name(client, monkeypatch):
    from galileo_blink.engine.sky import asteroids
    key = client.get("/api/visit", params=dict(ra=180, dec=0, camera=3)).json()["key"]
    assert key.startswith("v") and wait(client, key)["state"] == "ready"
    monkeypatch.setattr(asteroids, "find_asteroid", lambda name: asteroids.AsteroidVisit(
        name="45 Eugenia", camera=4, ra=83.6, dec=16.6, size_deg=0.4, mjd_start=60926.3,
        mjd_end=60927.5, vmag=13.6, n_photos=20, n_moments=7))
    r = client.get("/api/asteroid", params=dict(name="Eugenia")).json()
    assert r["asteroid"]["name"] == "45 Eugenia" and wait(client, r["key"])["state"] == "ready"

    def unknown(name):
        raise UserError("No asteroid called that is known.")
    monkeypatch.setattr(asteroids, "find_asteroid", unknown)
    assert client.get("/api/asteroid", params=dict(name="zzz")).status_code == 400
