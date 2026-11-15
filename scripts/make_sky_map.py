"""Draw the home page's all-sky map: the whole infrared sky as SPHEREx sees it, in one picture.

The picture is made once, here, and shipped with the site (web/public/sky/allsky.webp); the
page itself makes no outside requests. It is drawn from NASA's all-sky SPHEREx map, published
by IRSA as a HiPS (a sky map cut into HEALPix tiles):

    https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube

That HiPS is a cube of 102 frames, one per SPHEREx channel (frame = 17 * (band - 1) +
(channel - 1); frames 50 and 51 are blank). Every frame has an "Allsky" preview at HEALPix
order 3: all 768 order-3 tiles shrunk to 64 x 64 pixels and laid side by side, 27 to a row.
That is 6.9 arcminutes per pixel, finer than the map's own pixels, so a few of those files
(about 0.85 MB each) are all the script downloads.

The map is a Mollweide projection (an oval) in Galactic coordinates, centred on the centre of
the Milky Way with Galactic longitude increasing to the left, so the Galaxy runs as a
horizontal band across the middle. Outside the oval the picture is transparent. Five frames
from the longest-wavelength camera (4.4-5.0 microns, where dust hides least of the Galaxy)
are averaged, which evens out any one channel's artefacts, then stretched so the Galactic
plane, the Magellanic Clouds and the stars far from the plane all show.

Run it from the repository root:

    python scripts/make_sky_map.py
    python scripts/make_sky_map.py --frames 85 90 95 100 --cache some/folder

For a new data release, point HIPS_URL at the new HiPS (check its /properties: the frame
layout and `hips_frame = equatorial` must still hold) and run it again. The script checks
itself before writing: the Galactic centre and the Large Magellanic Cloud must come out
bright and a known empty patch of sky dark, or it stops.
"""
from __future__ import annotations

import argparse
import io
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy_healpix import HEALPix
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HIPS_URL = "https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube"
"""A NEW DATA RELEASE CHANGES THIS (one line)."""
OUTPUT = ROOT / "web" / "public" / "sky" / "allsky.webp"
DEFAULT_FRAMES = (86, 89, 92, 95, 98)
"""Band 6 (4.4-5.0 microns), spread across the band. Averaging them lowers the noise."""
USER_AGENT = "sky-map-script/1.0"

ALLSKY_ORDER = 3                   # the Allsky preview holds the order-3 tiles...
TILE = 64                          # ...each shrunk to 64 x 64 pixels...
PER_ROW = 27                       # ...27 to a row (the HiPS convention)
SUB_BITS = int(math.log2(TILE))    # a tile pixel is a HEALPix pixel SUB_BITS orders deeper

WIDTH, HEIGHT = 2000, 1000
SUPERSAMPLE = 3                    # samples per output pixel, each way: smooth stars and edge
QUALITY = 82

# ICRS -> Galactic rotation (Hipparcos, ESA 1997, vol. 1, sect. 1.5.3). Its transpose goes back.
ICRS_TO_GALACTIC = np.array([
    [-0.0548755604162154, -0.8734370902348850, -0.4838350155487132],
    [+0.4941094278755837, -0.4448296299600112, +0.7469822444972189],
    [-0.8676661490190047, -0.1980763734312015, +0.4559837761750669],
])

# Places the finished map is checked at: (name, ra, dec, should be bright?)
CHECKS = (
    ("Galactic centre", 266.405, -28.936, True),
    ("Large Magellanic Cloud", 80.894, -69.756, True),
    ("Galactic plane in Cygnus", 305.0, 40.0, True),
    ("empty sky in the Lockman Hole", 161.25, 58.0, False),
    ("empty sky in Fornax, far south of the plane", 40.0, -35.0, False),
)


# ------------------------------------------------------------------ sky geometry
def galactic_to_icrs(l_deg: np.ndarray, b_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    l, b = np.radians(l_deg), np.radians(b_deg)
    gal = np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)])
    eq = ICRS_TO_GALACTIC.T @ gal.reshape(3, -1)
    ra = np.degrees(np.arctan2(eq[1], eq[0])) % 360.0
    dec = np.degrees(np.arcsin(np.clip(eq[2], -1.0, 1.0)))
    return ra.reshape(l.shape), dec.reshape(l.shape)


def icrs_to_galactic(ra_deg: float, dec_deg: float) -> tuple[float, float]:
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    v = ICRS_TO_GALACTIC @ np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])
    return math.degrees(math.atan2(v[1], v[0])) % 360.0, math.degrees(math.asin(max(-1.0, min(1.0, v[2]))))


def map_to_galactic(fx: np.ndarray, fy: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fractions across and down the picture (0..1) -> (l, b, inside the oval). Inverse Mollweide."""
    x = (fx * 2.0 - 1.0) * 2.0 * math.sqrt(2.0)
    y = (1.0 - fy * 2.0) * math.sqrt(2.0)
    inside = x * x / 8.0 + y * y / 2.0 <= 1.0
    theta = np.arcsin(np.clip(y / math.sqrt(2.0), -1.0, 1.0))
    b = np.degrees(np.arcsin(np.clip((2.0 * theta + np.sin(2.0 * theta)) / math.pi, -1.0, 1.0)))
    cos_t = np.maximum(np.cos(theta), 1e-12)
    lon = np.degrees(math.pi * x / (2.0 * math.sqrt(2.0) * cos_t))   # east of centre, to the right
    l = (-lon) % 360.0                                                  # longitude grows to the left
    return l, b, inside


def galactic_to_map(l_deg: float, b_deg: float) -> tuple[float, float]:
    """(l, b) -> fractions across and down the picture. Forward Mollweide (Newton's method)."""
    phi = math.radians(b_deg)
    theta = phi
    for _ in range(50):
        if abs(abs(phi) - math.pi / 2) < 1e-9:
            theta = phi
            break
        step = (2 * theta + math.sin(2 * theta) - math.pi * math.sin(phi)) / (2 + 2 * math.cos(2 * theta))
        theta -= step
        if abs(step) < 1e-12:
            break
    lon = ((l_deg + 180.0) % 360.0) - 180.0
    x = -2.0 * math.sqrt(2.0) / math.pi * math.radians(lon) * math.cos(theta)
    y = math.sqrt(2.0) * math.sin(theta)
    return (x / (2.0 * math.sqrt(2.0)) + 1.0) / 2.0, (1.0 - y / math.sqrt(2.0)) / 2.0


# ------------------------------------------------------------------ the data
def fetch(path: str, cache: Path) -> bytes:
    local = cache / path.replace("/", "_")
    if local.exists() and local.stat().st_size > 0:
        return local.read_bytes()
    request = urllib.request.Request(f"{HIPS_URL}/{path}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    local.parent.mkdir(parents=True, exist_ok=True)
    tmp = local.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(local)
    return data


def check_properties(cache: Path) -> None:
    text = fetch("properties", cache).decode("utf-8", "replace")
    props = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            props[key.strip()] = value.strip()
    if props.get("hips_frame") != "equatorial":
        sys.exit(f"expected an equatorial HiPS, found hips_frame = {props.get('hips_frame')}")
    if props.get("hips_tile_format", "").split()[0:1] != ["png"]:
        sys.exit(f"expected PNG tiles, found {props.get('hips_tile_format')}")


def load_allsky(frame: int, cache: Path) -> np.ndarray:
    """One frame's Allsky preview as a float array (0..255, the archive's own asinh stretch)."""
    image = Image.open(io.BytesIO(fetch(f"Norder{ALLSKY_ORDER}/Allsky_{frame}.png", cache)))
    grey = np.asarray(image.convert("L"), dtype=np.float32)
    rows = math.ceil(12 * 4 ** ALLSKY_ORDER / PER_ROW)
    if grey.shape != (rows * TILE, PER_ROW * TILE):
        sys.exit(f"Allsky_{frame}.png is {grey.shape}, expected {(rows * TILE, PER_ROW * TILE)}")
    return grey


def sample_allsky(allsky: np.ndarray, ra: np.ndarray, dec: np.ndarray) -> np.ndarray:
    """Value of the Allsky preview at each (ra, dec).

    The pixel's HEALPix nested index at order 3 + 6 splits into its order-3 tile (the high
    bits) and its place inside the tile (the low 12 bits). Those low bits interleave two
    6-bit numbers: the even bits give the row in the tile image, the odd bits the column.
    (Of the eight ways to lay them out, only this one joins the tiles without seams.)
    """
    healpix = HEALPix(nside=2 ** (ALLSKY_ORDER + SUB_BITS), order="nested")
    index = healpix.lonlat_to_healpix(ra.ravel() * u.deg, dec.ravel() * u.deg).astype(np.int64)
    tile = index >> (2 * SUB_BITS)
    inner = index & ((1 << (2 * SUB_BITS)) - 1)
    row = np.zeros_like(inner)
    col = np.zeros_like(inner)
    for bit in range(SUB_BITS):
        row |= ((inner >> (2 * bit)) & 1) << bit
        col |= ((inner >> (2 * bit + 1)) & 1) << bit
    y = (tile // PER_ROW) * TILE + row
    x = (tile % PER_ROW) * TILE + col
    return allsky[y, x].reshape(ra.shape)


# ------------------------------------------------------------------ the picture
STRETCH_IN = (0.0, 35.0, 50.0, 64.0, 110.0, 158.0, 212.0, 255.0)
STRETCH_OUT = (0.0, 0.09, 0.19, 0.31, 0.52, 0.74, 0.90, 1.0)


def stretch(value: np.ndarray) -> np.ndarray:
    """0..255 archive values -> 0..1 display brightness.

    The archive's PNGs already carry an asinh stretch (0 to 40 MJy/sr) with zero at the
    sky's background: empty sky is 0 and the faintest stars jump straight to about 35. This
    curve keeps those faint stars quiet, so the sky far from the Galaxy reads as dark with
    stars in it, while the plane (64 to 212) spreads over most of the grey range and the
    Galactic centre keeps some shape below white.
    """
    return np.interp(value, STRETCH_IN, STRETCH_OUT)


def render(frames: list[np.ndarray]) -> Image.Image:
    s = SUPERSAMPLE
    total = np.zeros((HEIGHT, WIDTH), dtype=np.float64)
    cover = np.zeros((HEIGHT, WIDTH), dtype=np.float64)
    for j in range(s):
        for i in range(s):
            fx = (np.arange(WIDTH) + (i + 0.5) / s) / WIDTH
            fy = (np.arange(HEIGHT) + (j + 0.5) / s) / HEIGHT
            FX, FY = np.meshgrid(fx, fy)
            l, b, inside = map_to_galactic(FX, FY)
            ra, dec = galactic_to_icrs(l, b)
            value = np.mean([sample_allsky(f, ra, dec) for f in frames], axis=0)
            total += np.where(inside, stretch(value), 0.0)
            cover += inside
    brightness = np.where(cover > 0, total / np.maximum(cover, 1), 0.0)
    floor = 6.0 / 255.0                               # empty sky: just short of pure black
    grey = np.clip(floor + brightness * (1.0 - floor), 0.0, 1.0)
    alpha = cover / (s * s)                           # the oval's edge, smoothed
    rgba = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = np.round(grey * 255)
    rgba[..., 3] = np.round(alpha * 255)
    return Image.fromarray(rgba, "RGBA")


def verify(image: Image.Image) -> None:
    """Sample the map where the answer is known. Stops the script if any is wrong."""
    grey = np.asarray(image, dtype=np.float32)[..., 0]
    inside = np.asarray(image, dtype=np.float32)[..., 3] > 250
    typical = float(np.median(grey[inside]))
    failures = []
    for name, ra, dec, bright in CHECKS:
        fx, fy = galactic_to_map(*icrs_to_galactic(ra, dec))
        x, y = int(fx * WIDTH), int(fy * HEIGHT)
        patch = grey[max(y - 4, 0):y + 5, max(x - 4, 0):x + 5]
        level = float(np.median(patch))
        ok = level > typical + 25 if bright else level < typical + 6
        print(f"  {name:40s} ra {ra:8.3f} dec {dec:+8.3f} -> ({x:4d}, {y:4d}) "
              f"median {level:5.1f} (whole sky {typical:4.1f}) {'ok' if ok else 'WRONG'}")
        if not ok:
            failures.append(name)
    if failures:
        sys.exit("the map fails its checks at: " + ", ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frames", type=int, nargs="+", default=list(DEFAULT_FRAMES),
                        help="cube frames to average (0-101; 50 and 51 are blank)")
    parser.add_argument("--cache", type=Path, default=ROOT / "cache" / "sky_map",
                        help="where downloads are kept between runs")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if any(f in (50, 51) or not 0 <= f <= 101 for f in args.frames):
        sys.exit("frames must be 0-101, not 50 or 51 (blank)")

    check_properties(args.cache)
    with ThreadPoolExecutor(4) as pool:              # a handful of files: be gentle
        frames = list(pool.map(lambda f: load_allsky(f, args.cache), args.frames))
    print(f"averaging {len(frames)} frames: {args.frames}")
    image = render(frames)
    verify(image)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out, "WEBP", quality=QUALITY, method=6)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} kB, {WIDTH} x {HEIGHT})")


if __name__ == "__main__":
    main()
