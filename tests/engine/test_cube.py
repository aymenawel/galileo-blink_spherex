"""The all-sky cube quick-look spectrum: tile lookup and patch photometry."""
import numpy as np

from galileo_blink.engine.spectrum import cube


def test_positions_map_to_the_tiles_nasa_publishes():
    assert cube.tile_index(269.4486, 4.7689) == 7945          # Barnard's Star (checked live)
    assert cube.tile_url(7945).endswith("Norder5/Dir0/Npix7945_cube.fits")
    assert cube.tile_url(12287).endswith("Norder5/Dir10000/Npix12287_cube.fits")


def test_a_source_is_measured_above_its_surroundings():
    patch = np.full((7, 7), 2.0)                              # sky: 2 MJy/sr
    patch[2:5, 2:5] += 10.0                                   # a source: +10 in each of 9 pixels
    flux, background = cube.patch_photometry(patch)
    assert background == 2.0
    assert abs(flux - 90.0 * cube.PIXEL_SR * 1e9) < 1e-9      # 9 pixels x 10 MJy/sr x pixel area
    assert 3.8 < cube.PIXEL_SR * 1e9 < 4.0                    # 12.9" pixels: ~3.9 mJy per MJy/sr


def test_a_saturated_source_gives_no_brightness_not_a_wrong_one():
    patch = np.full((7, 7), 1.0)
    patch[3, 3] = np.nan
    flux, background = cube.patch_photometry(patch)
    assert flux is None and background == 1.0
    assert cube.patch_photometry(np.full((7, 7), np.nan)) == (None, None)
