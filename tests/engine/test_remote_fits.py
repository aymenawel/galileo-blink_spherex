"""A cutout read through byte ranges must equal the same pixels read from the whole file."""
import io

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from galileo_blink.engine.archive.remote_fits import NoOverlap, read_cutout

N = 300          # a small stand-in for SPHEREx's 2040-pixel detector


class BytesSource:
    """A file held in memory, readable only by byte range, counting what was asked for."""

    def __init__(self, data: bytes):
        self.data, self.fetched = data, 0

    def read(self, start, end):
        chunk = self.data[start:end + 1]
        self.fetched += len(chunk)
        return chunk

    def tail(self, n):
        self.fetched += n
        return self.data[-n:]


def _wave_table():
    grid = np.linspace(1, N, 9).round().astype(np.int32)
    values = np.zeros((9, 9, 2), dtype=np.float32)
    values[..., 0] = 4.0 + 0.001 * grid[:, None] + 0.0001 * grid[None, :]   # [y, x]
    values[..., 1] = 0.03
    cols = [fits.Column("X", "9J", dim="(9)", array=grid[None]),
            fits.Column("Y", "9J", dim="(9)", array=grid[None]),
            fits.Column("VALUES", "162E", dim="(2,9,9)", array=values[None])]
    return fits.BinTableHDU.from_columns(cols, name="WCS-WAVE")


def make_file(compressed_flags=True, roll_deg=24.0):
    """A SPHEREx-shaped exposure: rolled, with known pixels, flags and wavelengths."""
    rng = np.random.default_rng(1)
    image = rng.normal(0.5, 0.05, (N, N)).astype(np.float32)
    flags = np.zeros((N, N), dtype=np.int32)
    flags[rng.integers(0, N, 400), rng.integers(0, N, 400)] = 1 << 10
    flags[140:160, 150:170] |= (1 << 19) | (1 << 21)
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crpix = [N / 2 + 0.5, N / 2 + 0.5]
    w.wcs.crval = [180.0, 0.0]
    s, c = np.sin(np.radians(roll_deg)), np.cos(np.radians(roll_deg))
    scale = 6.15 / 3600
    w.wcs.cd = np.array([[-c, s], [s, c]]) * scale
    ih = w.to_header()
    ih["MJD-AVG"] = 60900.5
    ih["FINAST"] = 0
    ih["PSF_FWHM"] = 8.3
    for k in range(120):                                  # a long header, like the real one
        ih[f"HIERARCH PAD{k}"] = k
    hdus = [fits.PrimaryHDU(), fits.ImageHDU(image, ih, name="IMAGE")]
    if compressed_flags:
        hdus.append(fits.CompImageHDU(flags, name="FLAGS", compression_type="RICE_1",
                                      tile_shape=(1, N)))
    else:
        hdus.append(fits.ImageHDU(flags, name="FLAGS"))
    hdus += [fits.ImageHDU(image * 0 + 1, name="VARIANCE"), _wave_table()]
    buf = io.BytesIO()
    fits.HDUList(hdus).writeto(buf)
    return buf.getvalue(), image, flags, w


@pytest.mark.parametrize("compressed", [True, False])
def test_cutout_equals_the_same_pixels_of_the_whole_file(compressed):
    data, image, flags, w = make_file(compressed)
    ra, dec = (float(v) for v in w.pixel_to_world_values(200.2, 120.7))
    cut = read_cutout(BytesSource(data), ra, dec, half_px=20)
    assert (cut.x0, cut.y0) == (180, 101)
    assert cut.image.shape == (41, 41)
    np.testing.assert_array_equal(cut.image, image[101:142, 180:221])
    np.testing.assert_array_equal(cut.flags, flags[101:142, 180:221])


def test_cutout_reads_a_small_part_of_the_file():
    data, *_ = make_file()
    src = BytesSource(data)
    cut = read_cutout(src, 180.0, 0.0, half_px=10)
    assert src.fetched < 0.25 * len(data)
    assert cut.bytes_read == src.fetched


def test_cutout_wcs_points_at_the_same_sky_as_the_full_frame():
    data, _, _, w = make_file()
    ra, dec = (float(v) for v in w.pixel_to_world_values(60.0, 250.0))
    cut = read_cutout(BytesSource(data), ra, dec, half_px=15)
    x, y = cut.wcs.world_to_pixel_values(ra, dec)
    assert abs(x + cut.x0 - 60.0) < 1e-6 and abs(y + cut.y0 - 250.0) < 1e-6


def test_cutout_is_clipped_at_the_detector_edge():
    data, image, _, w = make_file()
    ra, dec = (float(v) for v in w.pixel_to_world_values(3.0, 296.0))
    cut = read_cutout(BytesSource(data), ra, dec, half_px=10)
    assert (cut.x0, cut.y0) == (0, 286)
    np.testing.assert_array_equal(cut.image, image[286:300, 0:14])


def test_a_place_outside_the_exposure_is_reported_not_guessed():
    data, *_ = make_file()
    with pytest.raises(NoOverlap):
        read_cutout(BytesSource(data), 185.0, 3.0, half_px=10)


def test_wavelength_is_interpolated_from_the_lookup_table():
    data, _, _, w = make_file()
    ra, dec = (float(v) for v in w.pixel_to_world_values(100.0, 200.0))
    cut = read_cutout(BytesSource(data), ra, dec, half_px=5)
    # pixel (x=100, y=200) is FITS pixel (101, 201): the table is linear in both
    expected = 4.0 + 0.001 * 201 + 0.0001 * 101
    assert abs(float(cut.wavelength[200 - cut.y0, 100 - cut.x0]) - expected) < 2e-4
