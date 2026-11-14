"""Every number that changes what Galileo Blink shows or measures, in one place.

Each constant says what it is, where the value comes from, and what breaks if it changes.
Nothing elsewhere in the engine may hide a tuning number in the middle of a function.
"""

# --------------------------------------------------------------------------- the instrument
PIXEL_ARCSEC = 6.15
"""SPHEREx's native pixel, in arcseconds. (The "0.615" in some documents is the oversampled
point-spread-function grid, ten times finer.) Every speed, distance and scale bar uses this."""

DETECTOR_PIXELS = 2040
"""Width and height of one SPHEREx exposure, in pixels."""

CAMERA_BANDS_MICRON = {
    1: (0.75, 1.09),
    2: (1.10, 1.62),
    3: (1.63, 2.41),
    4: (2.42, 3.82),
    5: (3.83, 4.41),
    6: (4.42, 5.00),
}
"""Wavelength range of each of the six detector arrays ("cameras")."""

DEFAULT_PSF_FWHM_ARCSEC = 8.3
"""Used only when a photo's header lacks PSF_FWHM (measured range: 7.5" camera 2 to 9.0"
camera 6, i.e. 1.2-1.5 pixels: the star image is undersampled)."""

# --------------------------------------------------------------------------- flags (bit numbers)
MASK_BITS = (2, 6, 9, 10, 11)
"""FLAGS bits treated as "no data": SUR_ERROR, NONFUNC, MISSING_DATA, HOT, COLD.

Deliberately NOT masked, because NASA's pipeline sets them on real moving objects and on real
bright stars: 19 OUTLIER (it flags pixels that disagree between exposures, which is what a
mover is: masking it hid a 500-sigma asteroid), 26 BLOOM and 28 HALO (both seen on asteroids),
27 SNOWBALL and 29 SATELLITE_HALO (untested, treated the same), 15 NONLINEAR (punches holes in
every bright star). A test pins this list."""

NEVER_MASK_BITS = (15, 19, 26, 27, 28, 29)

FINAST_MAX = 0
"""Header keyword FINAST: 0 = good astrometry, 1 = marginal, >1 = NASA says "should not be
used". Marginal astrometry fakes about 1" of motion in a tool that measures 1" motions, so
only 0 is accepted."""

# --------------------------------------------------------------------------- the archive
SPHEREX_COLLECTIONS = ("spherex_dr1", "spherex_dr1_deep", "spherex_qr3", "spherex_qr3_deep")
"""Image collections asked for at IRSA. A NEW DATA RELEASE IS ADDED HERE (one line); if every
collection here fails, the engine falls back to asking IRSA for all collections and keeping
those whose name starts with "spherex"."""

IRSA = "https://irsa.ipac.caltech.edu"
IRSA_DATA_PREFIX = IRSA + "/ibe/data/spherex/"
CLOUD_DATA_PREFIX = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
"""NASA/IRSA's public copy of the SPHEREx archive on AWS Open Data. A file's key there is its
IRSA path after /ibe/data/spherex/. It answers partial (HTTP Range) reads in ~0.2 s and does
not send "server busy", so it is tried first; IRSA's own copy of the same file is the fallback."""

USER_AGENT = "GalileoBlink/0.1 (NASA Space Apps 2026; github.com/aymenawel/galileo-blink_spherex)"

HTTP_TIMEOUT_S = 30.0
"""Deadline for one ordinary request. Every network call in the engine has a deadline."""

PHOTO_LIST_TIMEOUT_S = 45.0
PHOTO_LIST_BACKOFF_S = (0.3, 0.3, 0.3, 0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0)
"""The photo list is the one step with no second source, and IRSA's refusals are instant
(0.2 s), so it is retried many times, quickly: 12 tries turn a 65% failure rate into <1%."""
BUSY_STATUS = (429, 500, 502, 503, 504)
BUSY_BACKOFF_S = (0.5, 1.0, 2.0, 4.0, 6.0)
"""Waits between retries when a service answers "busy". IRSA does this in bursts: on
2026-11-14 about half of all requests got an instant 502 while identical retries succeeded."""

DOWNLOAD_WORKERS = 12
"""Photos fetched at once from the cloud copy (IRSA's own servers get IRSA_WORKERS)."""
IRSA_WORKERS = 4
"""IRSA's cutout and file servers refuse more than about five simultaneous requests."""

PHOTO_LIST_TTL_S = 6 * 3600
"""How long a cached photo list is trusted. The archive only ever grows, so an older list is
still a valid (smaller) answer and is served, marked stale, if IRSA is down."""

# --------------------------------------------------------------------------- framing
OVERFETCH = 1.45
"""Cutouts are read this much wider than the view. Photos arrive rolled to the ecliptic, so a
north-up view needs their corners (below ~1.42 a rotated frame leaves an empty wedge)."""

FIELD_MIN_DEG, FIELD_MAX_DEG, FIELD_DEFAULT_DEG = 0.05, 0.5, 0.15

DISPLAY_UPSCALE = 4
"""Display only: each SPHEREx pixel is drawn as 4x4 screen pixels (Lanczos)."""

MIN_COVERAGE = 0.6
"""A photo must cover this fraction of the view to be used."""

# --------------------------------------------------------------------------- looks and seasons
LOOK_GAP_DAYS = 30.0
"""A gap longer than this in one camera's photos starts a new look (SPHEREx returns to most
places every ~6 months)."""
LONG_LOOK_DAYS = 45.0
"""A look longer than this (near the ecliptic poles coverage is continuous) is cut by month."""
SEASON_LINK_DAYS = 45.0
SEASON_SPAN_DAYS = 60.0
"""Cameras do not share looks, so the screen steps through seasons: looks of all cameras whose
middle dates chain within SEASON_LINK_DAYS, never spanning more than SEASON_SPAN_DAYS."""

LIVE_PHOTOS_PER_LOOK = 4
LIVE_MAX_SEASONS = 8
LIVE_MAX_PHOTOS = 160
"""Limits for one live view (6 cameras x seasons x photos per look)."""

# --------------------------------------------------------------------------- display stretch
SKY_FLOOR_SIGMA = 2.0
"""Black point = sky median + this many sigma, so empty sky is black instead of static."""
STRETCH_TOP_PERCENTILE = 99.9
STRETCH_SOFTENING = 12.0
"""asinh softening: larger shows faint things more, bright things less."""
CHANGE_LIMIT_SIGMA = 9.0
"""A change map's colours span +/- this many sigma."""
CHANGE_STAR_FRACTION = 0.4
"""A star's brightness legitimately differs between looks (each photo is a different
wavelength), so the noise used for a change map grows with the star: sqrt(sigma^2 + (0.4 x
star)^2). Without it every star shows as a "change"."""

# --------------------------------------------------------------------------- measurement
FIT_RADIUS_PX = 3.5
"""Pixels around a star used by the profile fit."""
PARTIAL_RADIUS_PX = 1.5
"""A masked pixel this close to a star spoils its brightness but not its position."""
SATURATED_CORE_PIXELS = 3
"""This many masked pixels inside FIT_RADIUS_PX means the star is saturated: its position is
taken from the centre of the masked core and its brightness is not measured."""
MIN_MEASURE_SNR = 5.0
"""A season's median signal-to-noise must reach this for a motion measurement."""
MAX_TRACK_OFFSET_ARCSEC = 3.0
"""What is measured must stay this close to the catalogue's predicted track in every season,
or it is a different (usually static) object."""
ASTROMETRY_FLOOR_ARCSEC = 1.0
"""Per-look position floor when a view has too few reference stars to measure its own."""
AGREE_SIGMA = 2.0
"""Measured motion "agrees" with the catalogue if their vector difference is within this many
error bars."""
MIN_PAIR_DAYS = 300.0
SAME_SEASON_DAYS = 45.0
"""Motion is compared between looks a whole number of years apart when possible (within
SAME_SEASON_DAYS), because parallax then cancels."""

# --------------------------------------------------------------------------- catalogues
GAIA_EPOCH_MJD = 57388.5
"""Gaia DR3 reference epoch J2016.0."""
CATWISE_EPOCH_MJD = 57170.0
"""CatWISE2020 positions (ra_pm, dec_pm) are given at this date."""
MIN_PM_MARK_ARCSEC_YR = 0.5
"""Slower stars are not marked as movers: over SPHEREx's ~1.5 years they shift under 1"."""
CATWISE_MIN_PM_ARCSEC_YR = 2.0
CATWISE_MIN_SIGNIFICANCE = 5.0
"""CatWISE motions below these are mostly blends in crowded fields."""
CATALOGUE_TIMEOUT_S = 25.0
MAX_MARKERS = 12
"""More markers than this cover the picture."""
REFERENCE_STAR_MAX_PM = 0.05
"""Gaia stars slower than this (arcsec/yr) serve as fixed reference points."""

# --------------------------------------------------------------------------- cache
ENGINE_VERSION = "gb1"
"""Part of every cache key. Bump it whenever the engine's output changes, or old views are
served forever."""
DEGRADED_RETRY_S = 1800.0
"""A view built while a service was failing says so, and is rebuilt after this long."""
