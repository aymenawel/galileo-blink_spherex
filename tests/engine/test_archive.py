"""Getting the data when NASA's services misbehave: error pages, cut-off answers, timeouts."""
import time

import pytest
import requests

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive import http, photos
from galileo_blink.engine.errors import ServiceDown

HEADER = ("s_ra,s_dec,energy_bandpassname,access_url,obs_collection,t_min,t_max\n")
ROW = ("269.45,4.69,SPHEREx-D6,https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W33_2C/"
       "l2b-v27-2026-228/6/level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits,spherex_dr1,"
       "60900.5,60900.51\n")


def test_an_error_page_sent_as_a_success_is_not_an_empty_photo_list():
    page = "<html><head><title>IRSA is down for maintenance</title></head><body>Back soon</body></html>"
    with pytest.raises(ServiceDown):
        photos.parse_sia_csv(page)


def test_an_empty_collection_still_answers_with_its_header_row():
    assert photos.parse_sia_csv(HEADER) == []
    assert len(photos.parse_sia_csv(HEADER + ROW)) == 1


def test_a_cut_off_answer_keeps_the_rows_that_arrived():
    second = ROW.replace("0321", "0322")
    cut = HEADER + ROW + second[:second.index(",60900.5")]      # ends before its date
    got = photos.parse_sia_csv(cut)
    assert [p.file for p in got] == ["level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits"]


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path))
    return tmp_path


def test_an_empty_photo_list_is_never_kept(cache, monkeypatch):
    monkeypatch.setattr(photos, "_ask", lambda ra, dec, collection: [])
    assert photos.list_photos(10.0, 20.0).photos == []
    assert not list((cache / "lists").glob("*.json"))
    good = photos.parse_sia_csv(HEADER + ROW)
    monkeypatch.setattr(photos, "_ask", lambda ra, dec, collection: good)
    assert len(photos.list_photos(10.0, 20.0).photos) == 1     # asked again, not served empty
    assert len(list((cache / "lists").glob("*.json"))) == 1


def _timing_out(calls):
    def fake(method, url, timeout=None, **kw):
        calls.append(url)
        raise requests.Timeout("slow")
    return fake


def test_a_service_that_keeps_timing_out_is_given_up_on_quickly(monkeypatch):
    calls = []
    monkeypatch.setattr(http.session(), "request", _timing_out(calls))
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(ServiceDown):
        http.get("https://example.invalid/x", service="S", backoff=C.PHOTO_LIST_BACKOFF_S)
    assert len(calls) == 2


def test_busy_answers_are_still_retried_patiently(monkeypatch):
    calls = []

    class Busy:
        status_code = 503

    def fake(method, url, timeout=None, **kw):
        calls.append(url)
        return Busy()
    monkeypatch.setattr(http.session(), "request", fake)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(ServiceDown):
        http.get("https://example.invalid/x", service="S", backoff=C.PHOTO_LIST_BACKOFF_S)
    assert len(calls) == len(C.PHOTO_LIST_BACKOFF_S) + 1


def test_a_timeout_between_busy_answers_does_not_end_the_retries(monkeypatch):
    answers = iter(["timeout", 503, "timeout", 503, 200])

    class Answer:
        def __init__(self, code):
            self.status_code = code

    def fake(method, url, timeout=None, **kw):
        a = next(answers)
        if a == "timeout":
            raise requests.Timeout("slow")
        return Answer(a)
    monkeypatch.setattr(http.session(), "request", fake)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    assert http.get("https://example.invalid/x", service="S", backoff=C.PHOTO_LIST_BACKOFF_S).status_code == 200


def test_the_ask_everything_fallback_is_skipped_when_irsa_timed_out(monkeypatch):
    asked = []

    def fake(ra, dec, collection):
        asked.append(collection)
        raise ServiceDown(photos.SERVICE, "ReadTimeout", timed_out=True)
    monkeypatch.setattr(photos, "_ask", fake)
    with pytest.raises(ServiceDown):
        photos.query_archive(10.0, 20.0)
    assert None not in asked

    asked.clear()

    def refused(ra, dec, collection):
        asked.append(collection)
        raise ServiceDown(photos.SERVICE, "HTTP 404")
    monkeypatch.setattr(photos, "_ask", refused)
    with pytest.raises(ServiceDown):
        photos.query_archive(10.0, 20.0)
    assert None in asked                                    # renamed collections are still found


# ------------------------------------------------------------------ the cloud copy and IRSA
def _raw():
    import numpy as np
    from astropy.io import fits
    from galileo_blink.engine.archive.remote_fits import RawCutout
    z = np.zeros((5, 5), dtype=np.float32)
    return RawCutout(image=z, flags=z.astype(np.int32), wavelength=z, header=fits.Header(),
                     x0=0, y0=0, bytes_read=10)


def _ref(i):
    return photos.PhotoRef(file=f"level2_x_{i}_D6.fits", path=f"dr1/x/{i}.fits", camera=6,
                           mjd=60900.0 + i, collection="spherex_dr1")


@pytest.fixture
def store(cache, monkeypatch):
    from galileo_blink.engine.archive import store
    monkeypatch.setattr(store, "_cloud_down_until", 0.0)
    return store


def test_a_cloud_copy_that_is_down_is_skipped_for_a_while(store, monkeypatch):
    asked = []

    def read(source, ra, dec, half):
        asked.append(source.service)
        if source.service == store.CLOUD:
            raise ServiceDown(store.CLOUD, "ConnectionError")
        return _raw()
    monkeypatch.setattr(store, "read_cutout", read)
    assert store.fetch_photo(_ref(1), 10.0, 20.0, 0.1).source == "irsa"
    assert store.fetch_photo(_ref(2), 10.0, 20.0, 0.1).source == "irsa"
    assert asked == [store.CLOUD, store.IRSA_FILES, store.IRSA_FILES]
    monkeypatch.setattr(store.time, "time", lambda: 1e12)          # long after: tried again
    store.fetch_photo(_ref(3), 10.0, 20.0, 0.1)
    assert asked[-2:] == [store.CLOUD, store.IRSA_FILES]


def test_one_missing_file_in_the_cloud_copy_is_not_an_outage(store, monkeypatch):
    asked = []

    def read(source, ra, dec, half):
        asked.append(source.service)
        if source.service == store.CLOUD and "/1." in source.url:
            raise ServiceDown(store.CLOUD, "HTTP 404")
        return _raw()
    monkeypatch.setattr(store, "read_cutout", read)
    assert store.fetch_photo(_ref(1), 10.0, 20.0, 0.1).source == "irsa"
    assert store.fetch_photo(_ref(2), 10.0, 20.0, 0.1).source == "cloud"


def test_irsa_is_never_asked_for_more_than_a_few_files_at_once(store, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    now, most, guard = [0], [0], threading.Lock()
    monkeypatch.setattr(store, "_cloud_down_until", 1e12)          # the cloud copy is down

    def read(source, ra, dec, half):
        with guard:
            now[0] += 1
            most[0] = max(most[0], now[0])
        time.sleep(0.05)
        with guard:
            now[0] -= 1
        return _raw()
    monkeypatch.setattr(store, "read_cutout", read)
    with ThreadPoolExecutor(C.DOWNLOAD_WORKERS) as pool:
        list(pool.map(lambda i: store.fetch_photo(_ref(i), 10.0, 20.0, 0.1), range(16)))
    assert most[0] <= C.IRSA_WORKERS


def test_nasas_moving_object_search_is_asked_briefly(monkeypatch):
    from galileo_blink.engine.sky import asteroids
    seen = {}

    def get(url, **kwargs):
        seen.update(kwargs)
        raise ServiceDown(asteroids.MOST_SERVICE, "ReadTimeout", timed_out=True)
    monkeypatch.setattr(asteroids.http, "get", get)
    with pytest.raises(ServiceDown):
        asteroids.asteroid_sightings("Bamberga")
    assert seen["timeout"] <= 45 and seen["backoff"] == C.BUSY_BACKOFF_S


# ------------------------------------------------------------------ catalogue answers that are not answers
class _Text:
    def __init__(self, text, status_code=200):
        self.text, self.status_code = text, status_code


GATOR_EMPTY = r"""\fixlen = T
\RowsRetrieved =                 0
\ORIGIN  = 'IPAC Infrared Science Archive (IRSA), Caltech/JPL'
|           ra|          dec|          clon|          clat|                source_name|        ra_pm|       dec_pm|       pmra|      pmdec|   sigpmra|  sigpmdec|           dist|       angle|
|       double|       double|          char|          char|                       char|       double|       double|     double|     double|    double|    double|         double|      double|
"""


@pytest.mark.parametrize("text", ["<html><body>IRSA is down for maintenance</body></html>",
                                  "\\fixlen = T\n|  ra|", ""])
def test_a_catwise_answer_that_is_not_a_table_is_an_outage(monkeypatch, text):
    from galileo_blink.engine.sky import catalogues
    monkeypatch.setattr(catalogues.http, "get", lambda url, **kw: _Text(text))
    with pytest.raises(ServiceDown):
        catalogues.catwise_cone(10.0, 20.0, 0.1)


def test_an_empty_catwise_table_is_a_real_answer(monkeypatch):
    from galileo_blink.engine.sky import catalogues
    monkeypatch.setattr(catalogues.http, "get", lambda url, **kw: _Text(GATOR_EMPTY))
    assert catalogues.catwise_cone(10.0, 20.0, 0.1) == []


SKYBOT_ANSWER = """# Flag: 1
# Ticket: 188194302164311210
# Num | Name | RA(h) | DE(deg) | Class | Mv | Err(arcsec) | d(arcsec)
 45 | Eugenia | 05 33 56.5953 | +16 38 57.711 | MB>Middle | 13.5 | 0.002 | 432.121
"""


def test_skybot_answers_are_read_and_its_error_pages_are_outages(monkeypatch):
    from galileo_blink.engine.sky import asteroids
    monkeypatch.setattr(asteroids.http, "get", lambda url, **kw: _Text(SKYBOT_ANSWER))
    assert [o.name for o in asteroids.skybot(83.6, 16.6, 0.3, 60926.5)] == ["Eugenia"]
    monkeypatch.setattr(asteroids.http, "get", lambda url, **kw: _Text("", 204))   # nothing there
    assert asteroids.skybot(180.0, 80.0, 0.01, 60926.5) == []
    for page in ("<html>Service unavailable</html>", "# Flag: -1\n# Error: bad epoch\n"):
        monkeypatch.setattr(asteroids.http, "get", lambda url, page=page, **kw: _Text(page))
        with pytest.raises(ServiceDown):
            asteroids.skybot(83.6, 16.6, 0.3, 60926.5)


def test_a_moving_object_answer_that_is_not_one_is_an_outage(monkeypatch):
    from galileo_blink.engine.errors import UserError
    from galileo_blink.engine.sky import asteroids
    monkeypatch.setattr(asteroids.http, "get",
                        lambda url, **kw: _Text("<html><body>Proxy timeout</body></html>"))
    with pytest.raises(ServiceDown):
        asteroids.asteroid_sightings("Bamberga")
    known = '\\catalog = "spherex"\n\\object_name = "99942 Apophis (2004 MN4)"\n|ra_obj|dec_obj|\n'
    monkeypatch.setattr(asteroids.http, "get", lambda url, **kw: _Text(known))
    with pytest.raises(UserError, match="has not photographed"):
        asteroids.asteroid_sightings("Apophis")
