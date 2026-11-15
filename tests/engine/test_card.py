"""The still picture a visitor can save: the sky, the ring, the name and the one result."""
import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from galileo_blink.engine.image import card, render

PREBUILT = Path(__file__).resolve().parents[2] / "prebuilt"
CREDIT = "SPHEREx data: NASA/JPL-Caltech · galileoblink.earth"


def _view(**extra):
    view = dict(kind="looks", n=9, upscale=4, label="Test place",
                seasons=[dict(index=0, label="Sep 2025"), dict(index=1, label="Sep 2026")],
                cameras={"6": dict(band=[4.42, 5.0], looks=[dict(season=0, png="a.png"),
                                                           dict(season=1, png="b.png", change="c.png")])})
    view.update(extra)
    return view


def _motion(measured, predicted, error=0.4, agrees=True, first=0, last=1):
    return dict(measured=measured, predicted=predicted, error=error, agrees=agrees,
                first_season=first, last_season=last)


def _brightness(ratio, error=0.03, changed=True):
    return dict(cameras={}, best=dict(camera=6, first_season=0, last_season=1, ratio=ratio,
                                      error=error, changed=changed))


def _picture(n=9, k=4):
    rng = np.random.default_rng(3)
    return render.gray_png(np.clip(rng.normal(0.2, 0.2, (n, n)), 0, 1))


# ---------------------------------------------------------------- the result line

def test_a_star_that_stayed_put_and_changed_brightness_is_reported_by_its_brightness():
    view = _view(motion_combined=_motion(0.47, 0.03), brightness_change=_brightness(0.506, 0.032))
    assert card.result_line(view) == "49% fainter in camera 6 from Sep 2025 to Sep 2026, give or take 3%."


@pytest.mark.parametrize("ratio, words", [(1.79, "79% brighter"), (2.43, "2.4 times brighter"),
                                          (0.5, "50% fainter")])
def test_brightness_is_said_the_way_people_say_it(ratio, words):
    view = _view(motion=_motion(0.1, 0.02), brightness_change=_brightness(ratio, 0.004))
    assert card.result_line(view) == f"{words} in camera 6 from Sep 2025 to Sep 2026, give or take 1%."


def test_a_moving_star_is_reported_by_its_motion_even_if_its_brightness_changed():
    view = _view(motion_combined=_motion(10.27, 10.286, 0.455), brightness_change=_brightness(0.5))
    assert card.result_line(view) == ("Moved 10.3 arcsec between Sep 2025 and Sep 2026, give or take "
                                      "0.5 arcsec. Catalogue predicted 10.3 arcsec.")


def test_a_star_expected_to_stay_put_that_did_says_so():
    view = _view(motion=_motion(0.468, 0.028, 0.399))
    assert card.result_line(view) == "Did not move: 0.5 arcsec, give or take 0.4 arcsec, is within the error."
    unchanged = _view(motion=_motion(0.468, 0.028, 0.399), brightness_change=_brightness(0.95, changed=False))
    assert card.result_line(unchanged).startswith("Did not move")


def test_a_shift_the_error_does_not_explain_is_never_called_standing_still():
    line = card.result_line(_view(motion=_motion(1.6, 0.02, 0.3, agrees=False)))
    assert "Did not move" not in line and "1.6 arcsec" in line


def test_a_motion_without_season_names_leaves_the_dates_out():
    view = _view(seasons=[], motion=_motion(4.25, 4.61, 0.39))
    assert card.result_line(view) == "Moved 4.3 arcsec, give or take 0.4 arcsec. Catalogue predicted 4.6 arcsec."


def test_an_asteroid_view_names_its_strong_track():
    view = dict(kind="visit", label="45 Eugenia", seasons=[], cameras={},
                tracks=[dict(id=1, name=None, confidence="possible", speed_arcsec_per_hour=7.3, path=[]),
                        dict(id=0, name="Eugenia", confidence="strong", speed_arcsec_per_hour=33.12, path=[])])
    assert card.result_line(view) == "45 Eugenia, moving 33 arcsec per hour"
    slow = dict(view, label=None, tracks=[dict(id=0, name="Iris", confidence="strong",
                                              speed_arcsec_per_hour=6.24, path=[])])
    assert card.result_line(slow) == "Iris, moving 6.2 arcsec per hour"


def test_nothing_measured_means_no_result_line():
    assert card.result_line(_view()) is None
    weak = dict(kind="visit", label="x", seasons=[], cameras={},
                tracks=[dict(id=0, name=None, confidence="strong", speed_arcsec_per_hour=9, path=[])])
    assert card.result_line(weak) is None


def test_the_shipped_views_say_what_the_site_says():
    def load(name):
        return json.loads((PREBUILT / name / "view.json").read_text(encoding="utf8"))
    barnard = card.result_line(load("target-barnard"))
    assert barnard.startswith("Moved 10.3 arcsec between Aug 2025 and Aug 2026")
    assert card.result_line(load("target-rwaur")).startswith("49% fainter in camera 6")


def test_every_line_is_written_in_letters_the_font_can_draw():
    view = _view(motion=_motion(10.27, 10.286, 0.455), brightness_change=_brightness(0.5))
    for line in (card.result_line(view), card.date_line(view, 6, 1, "photo"),
                 card.date_line(view, 6, 1, "change")):
        assert all(c in card.DRAWABLE for c in line), line


def test_the_small_line_names_the_dates_the_camera_and_the_band():
    view = _view()
    assert card.date_line(view, 6, 1, "photo") == "Sep 2026 · camera 6 · 4.4 to 5.0 microns"
    change = card.date_line(view, 6, 1, "change")
    assert "Sep 2025 to Sep 2026" in change and "camera 6" in change


def test_an_asteroid_moment_is_dated_to_the_minute_with_its_year():
    view = dict(kind="visit", seasons=[dict(index=0, label="08 Sep 11:31")],
                cameras={"4": dict(band=[2.42, 3.82], looks=[dict(season=0, png="a.png", date="2025-09-08 11:31")])})
    assert card.date_line(view, 4, 0, "photo") == "8 Sep 2025, 11:31 UTC · camera 4 · 2.4 to 3.8 microns"


def test_long_lines_wrap_without_splitting_a_number_from_its_error():
    from PIL import ImageFont
    font = ImageFont.load_default(size=36)
    text = "49% fainter in camera 6 from Sep 2025 to Sep 2026, give or take 3%."
    lines = card._wrap(text, font, round(font.getlength(text)) - 20)
    assert lines == ["49% fainter in camera 6 from Sep 2025 to Sep 2026,", "give or take 3%."]


def test_a_name_in_letters_the_font_lacks_is_still_readable():
    assert card.drawable("Étoile β") == "Etoile"
    assert card.drawable("北") == ""


# ---------------------------------------------------------------- the picture

def test_the_card_is_a_wide_png_on_the_sites_ground_colour():
    png = card.card_png(_picture(), _view(motion=_motion(10.27, 10.286, 0.455)), 6, 1, "photo", CREDIT)
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG" and image.width == card.CARD_WIDTH == 1200
    assert image.height > card.PICTURE_SIZE + 200
    assert image.convert("RGB").getpixel((2, 2)) == (13, 14, 15)
    assert image.convert("RGB").getpixel((2, image.height - 3)) == (13, 14, 15)


def test_the_ring_is_drawn_where_the_subject_is_on_that_date():
    marker = dict(name="Test place", subject=True, track=[dict(season=0, x=2, y=2), dict(season=1, x=6, y=6)])
    black = render.gray_png(np.zeros((9, 9)))
    view = _view(markers=[marker])
    image = np.asarray(Image.open(io.BytesIO(card.card_png(black, view, 6, 1, "photo", CREDIT))).convert("RGB"))
    side = card.PICTURE_SIZE / 9
    cx, cy = card.MARGIN + (6 + 0.5) * side, card.MARGIN + (9 - 0.5 - 6) * side
    radius = card.SUBJECT_RING * card.PICTURE_SIZE
    on_ring = image[round(cy), round(cx + radius)]
    assert np.abs(on_ring.astype(int) - card._ACCENT).max() < 40   # the ring is the site's accent
    assert image[round(cy), round(cx)].max() < 40                # the star itself is not covered
    old = (card.MARGIN + 2.5 * side + radius, card.MARGIN + 6.5 * side)
    assert image[round(old[1]), round(old[0])].max() < 40        # nor drawn at another date


def test_on_a_change_map_the_ring_is_not_green():
    marker = dict(name="x", subject=True, track=[dict(season=1, x=4, y=4)])
    black = render.gray_png(np.zeros((9, 9)))
    image = np.asarray(Image.open(io.BytesIO(
        card.card_png(black, _view(markers=[marker]), 6, 1, "change", CREDIT))).convert("RGB"))
    side = card.PICTURE_SIZE / 9
    c = card.MARGIN + 4.5 * side
    r, g, b = (int(v) for v in image[round(c), round(c + card.SUBJECT_RING * card.PICTURE_SIZE)])
    assert min(r, g, b) > 180 and max(r, g, b) - min(r, g, b) < 30


def test_an_asteroid_card_rings_the_found_track_at_that_moment():
    black = render.gray_png(np.zeros((20, 20)))
    view = dict(kind="visit", n=20, upscale=4, label="7 Iris", seasons=[dict(index=0, label="10 May 01:45")],
                cameras={"3": dict(band=[1.63, 2.41], looks=[dict(season=0, png="a.png")])},
                tracks=[dict(id=0, name="Iris", confidence="strong", speed_arcsec_per_hour=22.6,
                             path=[dict(season=0, x=10, y=10)])])
    assert card.rings(view, 0) == [(10, 10, card.TRACK_RING)]
    image = np.asarray(Image.open(io.BytesIO(card.card_png(black, view, 3, 0, "photo", CREDIT))).convert("RGB"))
    c = card.MARGIN + 10.5 * card.PICTURE_SIZE / 20
    y = card.MARGIN + (20 - 0.5 - 10) * card.PICTURE_SIZE / 20
    on_ring = image[round(y), round(c + card.TRACK_RING * card.PICTURE_SIZE)]
    assert np.abs(on_ring.astype(int) - card._ACCENT).max() < 40   # the ring is the site's accent


def test_a_card_without_a_result_still_has_the_name_and_credit():
    png = card.card_png(_picture(), _view(), 6, 0, "photo", CREDIT)
    assert Image.open(io.BytesIO(png)).width == 1200
