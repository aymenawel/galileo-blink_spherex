"""The HTTP layer, with the engine's build step replaced by a fake (no network)."""
import threading
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
def make_client(tmp_path, monkeypatch):
    """A test client over a server whose build step is the given function."""
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path))
    from galileo_blink.engine.sky import coords
    from galileo_blink.server import jobs
    monkeypatch.setattr(jobs, "PREBUILT_DIR", tmp_path / "prebuilt")    # ignore shipped views
    monkeypatch.setattr(coords.catalogues, "gaia_cone", lambda ra, dec, r, **kw: [])
    return lambda build=fake_build: TestClient(create_app(Builder(build=build)))


@pytest.fixture
def client(make_client):
    return make_client()


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


def test_a_stale_local_copy_does_not_hide_the_shipped_view(client, tmp_path):
    from galileo_blink.server import jobs
    shipped = jobs.PREBUILT_DIR / "target-barnard"
    shipped.mkdir(parents=True)
    write_json(shipped / "view.json", dict(kind="looks", engine=C.ENGINE_VERSION, key="target-barnard", degraded=[]))
    stale = view_dir("target-barnard")
    stale.mkdir(parents=True)
    write_json(stale / "view.json", dict(kind="looks", engine="older", key="target-barnard", degraded=[]))
    assert client.get("/api/view", params=dict(target="barnard")).json() == dict(key="target-barnard", state="ready")


def test_a_blink_can_be_saved_as_an_animated_gif(client):
    import io
    from PIL import Image
    key = client.get("/api/view", params=dict(ra=180, dec=0)).json()["key"]
    wait(client, key)
    out = view_dir(key)
    rng = np.random.default_rng(1)
    (out / "c6_s1.png").write_bytes(render.gray_png(np.clip(rng.normal(0.3, 0.2, (9, 9)), 0, 1)))
    view = dict(kind="looks", engine=C.ENGINE_VERSION, key=key, degraded=[], label="Test place",
                seasons=[dict(index=0, label="Aug 2025"), dict(index=1, label="Feb 2026")],
                cameras={"6": dict(looks=[dict(season=0, png="c6_s0.png"), dict(season=1, png="c6_s1.png")])})
    write_json(out / "view.json", view)
    r = client.get(f"/api/view/{key}/blink.gif", params=dict(camera=6))
    assert r.status_code == 200 and r.headers["content-type"] == "image/gif"
    assert "galileo-blink-test-place-camera6.gif" in r.headers["content-disposition"]
    gif = Image.open(io.BytesIO(r.content))
    assert gif.n_frames == 2 and gif.info["loop"] == 0
    assert client.get(f"/api/view/{key}/blink.gif", params=dict(camera=2)).status_code == 400


def test_one_visitor_cannot_fill_the_build_queue(make_client):
    from galileo_blink.server import jobs
    release = threading.Event()

    def slow_build(req, progress):
        release.wait(5)
        fake_build(req, progress)

    client = make_client(slow_build)
    mine = {"X-Forwarded-For": "203.0.113.7"}
    try:
        codes = [client.get("/api/view", params=dict(ra=100 + i, dec=0), headers=mine).status_code
                 for i in range(jobs.MAX_PER_VISITOR + 1)]
        assert codes == [200] * jobs.MAX_PER_VISITOR + [503]
        # asking again for a view already on its way costs nothing, and nobody else is held up
        assert client.get("/api/view", params=dict(ra=100, dec=0), headers=mine).status_code == 200
        other = client.get("/api/view", params=dict(ra=200, dec=0),
                           headers={"X-Forwarded-For": "198.51.100.9"})
        assert other.status_code == 200
    finally:
        release.set()


def test_slow_lookups_are_turned_away_when_too_many_run_at_once(client, monkeypatch):
    from galileo_blink.server.app import Limiter
    client.app.state.lookups = Limiter(0)           # as if every slot were taken
    for address in ("/api/resolve?q=Vega", "/api/spectrum?ra=10&dec=10", "/api/asteroid?name=Pallas"):
        r = client.get(address)
        assert r.status_code == 503 and r.json()["error_kind"] == "busy"
    assert client.get("/api/health").status_code == 200


def test_a_limiter_frees_its_slot_even_when_the_work_fails():
    from galileo_blink.server.app import Limiter
    from galileo_blink.server.jobs import Busy
    limiter = Limiter(1)
    with pytest.raises(KeyError):
        limiter.run(lambda: {}["missing"])
    assert limiter.run(lambda: 7) == 7
    gate = threading.Event()
    held = threading.Thread(target=lambda: limiter.run(gate.wait, 5))
    held.start()
    time.sleep(0.05)
    with pytest.raises(Busy):
        limiter.run(lambda: 7)
    gate.set()
    held.join()


def test_every_answer_carries_the_browser_safety_headers(client):
    for address in ("/api/health", "/api/view/nothing-here"):
        h = client.get(address).headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["referrer-policy"] and h["strict-transport-security"]


@pytest.mark.parametrize("key", ["..%5C..%5Cprebuilt%5Ctarget-barnard", "a" * 80, "bad key", "x.y"])
def test_a_view_key_is_only_ever_letters_digits_and_dashes(client, key):
    assert client.get(f"/api/view/{key}").status_code == 404
    assert client.get(f"/files/{key}/view.json").status_code == 404


def test_a_saved_gif_gets_a_plain_filename_whatever_the_place_is_called(client, tmp_path):
    key = wait(client, client.get("/api/view", params=dict(ra=180, dec=0)).json()["key"])["key"]
    folder = view_dir(key)
    view = dict(kind="looks", engine=C.ENGINE_VERSION, key=key, ra=180, dec=0, degraded=[],
                label="Étoile β 北", seasons=[dict(index=0, label="Jan 2026")],
                cameras={"6": dict(looks=[dict(season=0, png="c6_s0.png")])})
    write_json(folder / "view.json", view)
    r = client.get(f"/api/view/{key}/blink.gif", params=dict(camera=6))
    assert r.status_code == 200
    assert r.headers["content-disposition"].isascii()


def test_a_saved_gif_credits_the_data_and_the_site(client, monkeypatch):
    stamps = []
    real = render.blink_gif
    monkeypatch.setattr(render, "blink_gif", lambda p, c, credit, ms: stamps.append(credit) or real(p, c, credit, ms))
    key = wait(client, client.get("/api/view", params=dict(ra=180, dec=0)).json()["key"])["key"]
    view = dict(kind="looks", engine=C.ENGINE_VERSION, key=key, degraded=[], label="x",
                seasons=[dict(index=0, label="19 May 21:51")],
                cameras={"6": dict(looks=[dict(season=0, png="c6_s0.png")])})
    write_json(view_dir(key) / "view.json", view)
    assert client.get(f"/api/view/{key}/blink.gif", params=dict(camera=6)).status_code == 200
    assert stamps == ["SPHEREx data: NASA/JPL-Caltech · galileoblink.earth"]
    from PIL import Image, ImageDraw
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    caption = draw.textlength("19 May 21:51  ·  camera 6", font_size=18)
    assert 10 + caption + 10 < render.GIF_SIZE - draw.textlength(stamps[0], font_size=13) - 10


def test_built_scripts_are_cached_for_good_and_fonts_have_their_type(tmp_path, monkeypatch):
    from galileo_blink.server import app as server
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html>")
    (dist / "assets" / "index-3f2a.js").write_text("console.log(1)")
    (dist / "assets" / "inter-9c1b.woff2").write_bytes(b"wOF2" + b"\0" * 2000)
    monkeypatch.setattr(server, "WEB_DIST", dist)
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path / "cache"))
    client = TestClient(create_app(Builder(build=fake_build)))
    js = client.get("/assets/index-3f2a.js")
    assert js.status_code == 200
    assert js.headers["cache-control"] == "public, max-age=31536000, immutable"
    font = client.get("/assets/inter-9c1b.woff2")
    assert font.headers["content-type"] == "font/woff2"
    assert font.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/assets/missing.js").status_code == 404


def test_a_build_that_waited_in_the_queue_is_not_reported_as_too_slow(make_client, monkeypatch):
    from galileo_blink.server import jobs
    release = threading.Event()

    def slow_build(req, progress):
        if req.dec < 1:
            release.wait(5)
        fake_build(req, progress)

    client = make_client(slow_build)
    try:
        for i in range(jobs.MAX_BUILDS_AT_ONCE):        # every builder is busy
            client.get("/api/view", params=dict(ra=100 + i, dec=0))
        waiting = client.get("/api/view", params=dict(ra=150, dec=5)).json()["key"]
        monkeypatch.setattr(jobs, "JOB_MAX_RUN_S", 0.2)
        time.sleep(0.3)
        assert client.get(f"/api/view/{waiting}").json()["state"] == "queued"
        busy = client.get("/api/view", params=dict(ra=100, dec=0)).json()["key"]
        s = client.get(f"/api/view/{busy}").json()
        assert s["state"] == "failed" and s["error_kind"] == "service"
        assert "slow" in s["error"] and "try again" in s["error"]
    finally:
        release.set()
    monkeypatch.setattr(jobs, "JOB_MAX_RUN_S", 600.0)
    assert wait(client, waiting)["state"] == "ready"


def _old_view(key, degraded):
    import os
    folder = view_dir(key)
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "view.json", dict(kind="looks", engine=C.ENGINE_VERSION, key=key,
                                          degraded=degraded, label="old"))
    then = time.time() - C.DEGRADED_RETRY_S - 60
    os.utime(folder / "view.json", (then, then))


def test_a_view_built_during_an_outage_is_kept_when_its_rebuild_fails_too(make_client):
    from galileo_blink.engine.looks.build import ViewRequest
    calls = []

    def still_down(req, progress):
        calls.append(req.key)
        raise ServiceDown("NASA's MAST archive (Gaia catalogue)", "HTTP 503")

    client = make_client(still_down)
    key = ViewRequest(ra=50.0, dec=40.0, size_deg=C.FIELD_DEFAULT_DEG).key
    _old_view(key, ["gaia"])
    assert client.get("/api/view", params=dict(ra=50, dec=40)).json()["key"] == key
    done = wait(client, key)
    assert calls == [key]                                   # it really was tried again
    assert done["state"] == "ready" and done["view"]["label"] == "old"


def test_a_failed_view_can_be_tried_again(make_client):
    calls = []

    def counting(req, progress):
        calls.append(req.key)
        fake_build(req, progress)

    client = make_client(counting)
    key = client.get("/api/view", params=dict(ra=50, dec=10.0)).json()["key"]
    assert wait(client, key)["state"] == "failed" and len(calls) == 1
    client.get("/api/view", params=dict(ra=50, dec=10.0))
    assert wait(client, key)["state"] == "failed" and len(calls) == 2


def test_a_view_built_during_an_outage_is_passed_over_once_old_enough(client):
    from galileo_blink.server import jobs
    _old_view("k-gaia", ["gaia"])
    _old_view("k-list", ["photo_list"])
    assert jobs.Builder.find("k-gaia") is None
    assert jobs.Builder.find("k-list") is not None          # an older photo list stays true
    shipped = jobs.PREBUILT_DIR / "k-shipped"
    shipped.mkdir(parents=True)
    write_json(shipped / "view.json", dict(kind="looks", engine=C.ENGINE_VERSION, key="k-shipped",
                                           degraded=["gaia"]))
    import os
    then = time.time() - C.DEGRADED_RETRY_S - 60
    os.utime(shipped / "view.json", (then, then))
    assert jobs.Builder.find("k-shipped") is not None       # a shipped view is never passed over


def test_every_shipped_example_opens_from_the_real_prebuilt_folder(tmp_path, monkeypatch):
    import json
    from galileo_blink.engine.looks.build import target_request
    from galileo_blink.engine.sky import targets
    from galileo_blink.server import app as server
    from galileo_blink.server import jobs
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path))     # nothing built locally
    keys = [target_request(t.id).key for t in targets.targets()]
    keys += [server._example_request(e).key
             for e in json.loads(server.ASTEROID_EXAMPLES.read_text(encoding="utf8"))]
    assert len(keys) == 10
    for key in keys:
        found = jobs.Builder.find(key)
        assert found is not None, f"{key} is not shipped for engine {C.ENGINE_VERSION}"
        folder, view = found
        assert folder.parent == jobs.PREBUILT_DIR and view["engine"] == C.ENGINE_VERSION
        cameras = view.get("cameras", {}).values()
        pictures = [look[k] for cam in cameras for look in cam.get("looks", [])
                    for k in ("png", "change", "flags_png") if look.get(k)]
        pictures += [cam["combined"] for cam in cameras if cam.get("combined")]
        assert pictures, key
        for name in pictures:
            assert (folder / name).is_file(), f"{key}/{name} is missing"


def test_a_made_up_address_does_not_buy_more_builds(make_client):
    """Google's front end appends the visitor's real address last; an entry the sender wrote
    in front of it must not make them look like someone new."""
    from galileo_blink.server import jobs
    release = threading.Event()

    def slow_build(req, progress):
        release.wait(5)
        fake_build(req, progress)

    client = make_client(slow_build)
    try:
        for i in range(jobs.MAX_PER_VISITOR):
            r = client.get("/api/view", params=dict(ra=100 + i, dec=0),
                           headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.7"})
            assert r.status_code == 200
        held = client.get("/api/view", params=dict(ra=150, dec=0),
                          headers={"X-Forwarded-For": "10.9.8.7, 203.0.113.7"})
        assert held.status_code == 503
        other = client.get("/api/view", params=dict(ra=200, dec=0),
                           headers={"X-Forwarded-For": "10.9.8.7, 198.51.100.9"})
        assert other.status_code == 200
    finally:
        release.set()
