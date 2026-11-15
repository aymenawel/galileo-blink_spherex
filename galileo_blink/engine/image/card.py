"""One still picture of a view to save and share: the sky as it is on screen, a ring at the
object, and under it the name, the one result and the date, camera and band.

Display only, and pure: every word comes from the view itself, never from the request, and
nothing here can create or change a measurement.
"""
from __future__ import annotations

import io
import math
import re
import unicodedata
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from PIL import Image, ImageDraw, ImageFont

from .. import constants as C

CARD_WIDTH = 1200
MARGIN = 60
PICTURE_SIZE = CARD_WIDTH - 2 * MARGIN
CORNER = 28
SUBJECT_RING = 0.045
"""Ring radius as a fraction of the picture, the same as the site's own ring."""
TRACK_RING = 0.03
RING_WIDTH = 3

_GROUND = (13, 14, 15)              # the site's ground colour, #0d0e0f
_NO_DATA = (38, 41, 46)             # as in the GIF: no data is grey, never the black of empty sky
_ACCENT = (61, 139, 255)            # #3d8bff, the site's accent
_TEXT = (242, 243, 240)             # #f2f3f0
_QUIET = (164, 168, 166)            # #a4a8a6
_CREDIT = (122, 127, 125)           # #7a7f7d

_NAME_SIZE, _RESULT_SIZE, _SMALL_SIZE, _CREDIT_SIZE = 62, 36, 25, 21

DRAWABLE = frozenset(chr(c) for c in range(0x20, 0x7F)) | frozenset("©«°±´·»‘’“”…‹›⁄")
"""Every character Pillow's built-in font can draw (measured on Pillow 12: it lacks ″, µ and
the en dash, so the card says "arcsec", "microns" and "to")."""
_STANDS_IN = {"–": "-", "—": "-", "″": " arcsec", "′": " arcmin", "µ": "u"}
STATIC_BELOW_ARCSEC = 0.3
"""Below this predicted motion an object counts as standing still for SPHEREx (as on the site)."""


def drawable(text: str) -> str:
    """`text` in characters the font can draw: accents dropped, anything else left out."""
    text = "".join(_STANDS_IN.get(c, c) for c in unicodedata.normalize("NFKD", text))
    kept = "".join(c for c in text if c in DRAWABLE)
    return " ".join(kept.split())


def _fixed(value: float, digits: int) -> str:
    """`value` to `digits` decimals, an exact half rounded up, as the site's numbers are."""
    return str(Decimal(value).quantize(Decimal(1).scaleb(-digits), ROUND_HALF_UP))


def _arcsec(value: float, digits: int = 1) -> str:
    return f"{_fixed(value, digits)} arcsec"


def _brightness_words(ratio: float) -> str:
    """0.51 is "49% fainter", 1.79 is "79% brighter", 2.4 is "2.4 times brighter"."""
    if ratio >= 2:
        return f"{float(f'{ratio:.2g}'):g} times brighter"
    percent = int(_fixed(abs(ratio - 1) * 100, 0))
    if percent == 0:
        return "unchanged"
    return f"{percent}% {'brighter' if ratio > 1 else 'fainter'}"


def _labels(view: dict) -> dict[int, str]:
    return {s["index"]: s.get("label") or "" for s in view.get("seasons") or []}


def result_line(view: dict) -> str | None:
    """The one result, in the site's words: a brightness change for a star that stayed put as
    expected, else the motion, else the asteroid found. None when there is nothing to say."""
    labels = _labels(view)
    motion = view.get("motion_combined") or view.get("motion")
    best = (view.get("brightness_change") or {}).get("best")
    static = motion is not None and motion["predicted"] < STATIC_BELOW_ARCSEC
    if static and motion.get("agrees") and best and best.get("changed"):
        first, last = labels.get(best["first_season"]), labels.get(best["last_season"])
        span = f" from {first} to {last}" if first and last else ""
        error = max(1, int(_fixed(best["error"] * 100, 0)))
        return drawable(f"{_brightness_words(best['ratio'])} in camera {best['camera']}{span}, "
                        f"give or take {error}%.")
    if motion is not None:
        measured, error = _arcsec(motion["measured"]), _arcsec(motion["error"])
        if static:
            if motion.get("agrees"):
                return f"Did not move: {measured}, give or take {error}, is within the error."
            return (f"Shifted {measured}, give or take {error}: more than the error explains, "
                    "so treat it with caution.")
        span_of = view.get("motion") or motion
        first, last = labels.get(span_of.get("first_season")), labels.get(span_of.get("last_season"))
        between = f" between {first} and {last}" if first and last else ""
        return drawable(f"Moved {measured}{between}, give or take {error}. "
                        f"Catalogue predicted {_arcsec(motion['predicted'])}.")
    if view.get("kind") == "visit":
        for track in view.get("tracks") or []:
            if track.get("confidence") == "strong" and track.get("name"):
                label = view.get("label") or ""
                name = label if track["name"] in label else track["name"]
                speed = track["speed_arcsec_per_hour"]
                return drawable(f"{name}, moving {_arcsec(speed, 1 if speed < 10 else 0)} per hour")
    return None


def _look(view: dict, camera: int, season: int) -> dict:
    looks = (view.get("cameras", {}).get(str(camera)) or {}).get("looks") or []
    return next((look for look in looks if look.get("season") == season), {})


def _when(view: dict, camera: int, season: int) -> str:
    """The date of one look: the season's name, or for an asteroid view the moment, with its year."""
    if view.get("kind") == "visit":
        try:
            moment = datetime.strptime(_look(view, camera, season).get("date") or "", "%Y-%m-%d %H:%M")
            return f"{moment.day} {moment:%b %Y, %H:%M} UTC"
        except ValueError:
            pass
    return _labels(view).get(season, "")


def date_line(view: dict, camera: int, season: int, layer: str) -> str:
    """Date(s), camera and wavelength band of the picture on the card."""
    cam = view.get("cameras", {}).get(str(camera)) or {}
    lo, hi = cam.get("band") or C.CAMERA_BANDS_MICRON.get(camera, (0, 0))
    when = _when(view, camera, season)
    looks = cam.get("looks") or []
    if layer == "change" and looks and looks[0].get("season") != season:
        first = _when(view, camera, looks[0]["season"])
        when = f"Change from {first} to {when}: green brighter, pink fainter"
    parts = [when, f"camera {camera}", f"{_fixed(lo, 1)} to {_fixed(hi, 1)} microns"]
    return drawable(" · ".join(p for p in parts if p))


def _position(track: list[dict], season: int) -> tuple[float, float] | None:
    return next(((p["x"], p["y"]) for p in track if p.get("season") == season), None)


def rings(view: dict, season: int) -> list[tuple[float, float, float]]:
    """(x, y, radius as a fraction of the picture) of every ring on the card, in view pixels:
    the subject's catalogue position on that date, or the asteroid search's found tracks."""
    out = []
    if view.get("kind") == "visit":
        tracks = view.get("tracks") or []
        strong = [t for t in tracks if t.get("confidence") == "strong"]
        for track in strong or tracks:
            if (p := _position(track.get("path") or [], season)) is not None:
                out.append((*p, TRACK_RING))
    else:
        for marker in view.get("markers") or []:
            if marker.get("subject") and (p := _position(marker.get("track") or [], season)) is not None:
                out.append((*p, SUBJECT_RING))
    return out


_KEEP_TOGETHER = re.compile(r"give or take [\d.]+%?(?: arcsec)?|[\d.]+ (?:arcsec|microns)")


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Lines no wider than `width`, never breaking "give or take 3%" or a number from its unit."""
    glued = _KEEP_TOGETHER.sub(lambda m: m.group().replace(" ", "\0"), text)
    lines, line = [], ""
    for word in glued.split(" "):
        word = word.replace("\0", " ")
        trial = f"{line} {word}".strip()
        if line and font.getlength(trial) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


def _ring(sky: Image.Image, cx: float, cy: float, radius: float, colour) -> None:
    """A smooth ring, drawn four times larger on a small patch and shrunk into place."""
    ss, half = 4, int(radius + RING_WIDTH + 3)
    x0, y0 = math.floor(cx) - half, math.floor(cy) - half
    size = 2 * half + 1
    big = Image.new("L", (size * ss, size * ss), 0)
    ox, oy = (cx - x0) * ss, (cy - y0) * ss
    r = radius * ss
    ImageDraw.Draw(big).ellipse((ox - r - RING_WIDTH * ss / 2, oy - r - RING_WIDTH * ss / 2,
                                 ox + r + RING_WIDTH * ss / 2, oy + r + RING_WIDTH * ss / 2),
                                outline=255, width=RING_WIDTH * ss)
    sky.paste(Image.new("RGB", (size, size), colour), (x0, y0), big.resize((size, size), Image.BOX))


def _rounded(image: Image.Image) -> Image.Image:
    ss = 3
    mask = Image.new("L", (image.width * ss, image.height * ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, mask.width - 1, mask.height - 1), CORNER * ss, fill=255)
    return mask.resize(image.size, Image.LANCZOS)


def card_png(picture: bytes, view: dict, camera: int, season: int, layer: str, credit: str) -> bytes:
    """The card: `picture` (one of the view's own PNGs: a photo, or a change map when `layer`
    is "change") drawn large with its rings, and the name, result, date line and credit under it."""
    source = Image.open(io.BytesIO(picture)).convert("RGBA")
    n = view.get("n") or source.width // max(1, view.get("upscale") or 1)
    sky = Image.new("RGB", (PICTURE_SIZE, PICTURE_SIZE), _NO_DATA)
    scaled = source.resize((PICTURE_SIZE, PICTURE_SIZE), Image.LANCZOS)
    sky.paste(scaled, (0, 0), scaled)
    side = PICTURE_SIZE / n
    colour = _TEXT if layer == "change" else _ACCENT      # on a change map green means "brighter"
    for x, y, fraction in rings(view, season):
        cx, cy = (x + 0.5) * side, (n - 0.5 - y) * side   # view pixels are y up, centres at whole numbers
        if 0 <= cx < PICTURE_SIZE and 0 <= cy < PICTURE_SIZE:
            _ring(sky, cx, cy, fraction * PICTURE_SIZE, colour)

    name = drawable((view.get("target") or {}).get("name") or view.get("label")
                    or (view.get("subject") or {}).get("name") or "") or "A place in the sky"
    blocks = []                                           # (gap above, lines, font, colour)
    fonts = {s: ImageFont.load_default(size=s) for s in (_NAME_SIZE, _RESULT_SIZE, _SMALL_SIZE, _CREDIT_SIZE)}
    blocks.append((52, _wrap(name, fonts[_NAME_SIZE], PICTURE_SIZE), fonts[_NAME_SIZE], _TEXT))
    if result := result_line(view):
        blocks.append((22, _wrap(result, fonts[_RESULT_SIZE], PICTURE_SIZE), fonts[_RESULT_SIZE], _TEXT))
    blocks.append((20, _wrap(date_line(view, camera, season, layer), fonts[_SMALL_SIZE], PICTURE_SIZE),
                   fonts[_SMALL_SIZE], _QUIET))
    blocks.append((60, _wrap(drawable(credit), fonts[_CREDIT_SIZE], PICTURE_SIZE), fonts[_CREDIT_SIZE], _CREDIT))

    def line_height(font):
        return round(font.size * 1.3)

    height = MARGIN + PICTURE_SIZE + sum(gap + len(lines) * line_height(font) for gap, lines, font, _ in blocks) + 48
    card = Image.new("RGB", (CARD_WIDTH, height), _GROUND)
    card.paste(sky, (MARGIN, MARGIN), _rounded(sky))
    draw = ImageDraw.Draw(card)
    y = MARGIN + PICTURE_SIZE
    for gap, lines, font, fill in blocks:
        y += gap
        for line in lines:
            draw.text((MARGIN, y), line, font=font, fill=fill, anchor="la")
            y += line_height(font)
    buf = io.BytesIO()
    card.save(buf, "PNG", optimize=True)
    return buf.getvalue()
