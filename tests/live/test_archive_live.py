"""Checks against NASA's live services. Run with:  python -m pytest -m live tests/live"""
import io
import time
import warnings

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from galileo_blink.engine import constants as C
from galileo_blink.engine.archive import http
from galileo_blink.engine.archive.photos import query_archive
from galileo_blink.engine.archive.store import fetch_photo, half_pixels

pytestmark = pytest.mark.live
BARNARD = (269.4520, 4.7600)


@pytest.fixture(scope="module")
def barnard_photos():
    t = time.time()
    photos, complete = query_archive(*BARNARD)
    assert complete
    print(f"\nphoto list: {len(photos)} photos in {time.time() - t:.1f} s")
    return photos


def test_photo_list_covers_all_six_cameras(barnard_photos):
    assert len(barnard_photos) >= 300
    assert {p.camera for p in barnard_photos} == {1, 2, 3, 4, 5, 6}
    assert all(p.version for p in barnard_photos)


@pytest.mark.parametrize("pick", ["first", "last"])
def test_cloud_cutout_matches_irsas_own_cutout_service(barnard_photos, pick, tmp_path, monkeypatch):
    """Same pixels, same flags, same sky mapping and same wavelengths as IRSA's cutout
    service returns for the same exposure (oldest DR1 photo and newest QR3 photo)."""
    monkeypatch.setenv("GALILEO_BLINK_CACHE", str(tmp_path))
    cam6 = [p for p in barnard_photos if p.camera == 6]
    ref = cam6[0] if pick == "first" else cam6[-1]
    size = 0.15
    t = time.time()
    photo = fetch_photo(ref, *BARNARD, size)
    dt = time.time() - t
    print(f"\n{ref.collection} {ref.file}: {photo.bytes_read / 1e6:.2f} MB in {dt:.2f} s from {photo.source}")

    url = f"{C.IRSA_DATA_PREFIX}{ref.path}?center={BARNARD[0]},{BARNARD[1]}d&size={size * C.OVERFETCH:.4f}"
    r = http.get(url, service="IRSA cutout service", timeout=120)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with fits.open(io.BytesIO(r.content)) as hl:
            ih = hl["IMAGE"].header
            official, oflags = hl["IMAGE"].data.astype(np.float32), hl["FLAGS"].data.astype(np.int64)
            ow = WCS(ih)
            sw = WCS(ih, fobj=hl, key="W")
            sw.sip = None
            # the same sky position must land on the same pixel VALUE in both
            sky = photo.wcs.pixel_to_world_values([10, 40, 70], [15, 45, 75])
            ox, oy = ow.world_to_pixel_values(*sky)
            for (px, py), x, y in zip([(10, 15), (40, 45), (70, 75)], ox, oy):
                xi, yi = int(round(float(x))), int(round(float(y)))
                assert abs(x - xi) < 0.02 and abs(y - yi) < 0.02, "cutouts are not on one pixel grid"
                assert photo.image[py, px] == official[yi, xi] or (
                    np.isnan(photo.image[py, px]) and np.isnan(official[yi, xi]))
                assert int(photo.flags[py, px]) == int(oflags[yi, xi])
                lam = float(np.atleast_1d(sw.pixel_to_world_values(float(xi), float(yi))[0])[0])
                assert abs(float(photo.wavelength[py, px]) - lam) < 2e-3, (photo.wavelength[py, px], lam)
    assert half_pixels(size) * 2 + 1 >= photo.image.shape[0]
    assert photo.bytes_read < 4e6
