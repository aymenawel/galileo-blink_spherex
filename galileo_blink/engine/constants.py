"""The main tuning numbers of Galileo Blink, each with its reason.

Each constant says what it is, where the value comes from, and what breaks if it changes.
Numbers that belong to one step are named at the top of that step's module; none is hidden in
the middle of a function.
"""

# --------------------------------------------------------------------------- the instrument
PIXEL_ARCSEC = 6.15
"""SPHEREx's native pixel, in arcseconds. (The "0.615" in some documents is the oversampled
point-spread-function grid, ten times finer.) Every speed, distance and scale bar uses this."""

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
PHOTO_LIST_BACKOFF_S = (0.3,) * 3 + (0.5,) * 3 + (1.0,) * 4 + (2.0,) * 5 + (3.0,) * 5
"""The photo list is the one step with no second source, and IRSA's refusals are instant
(0.2 s), so it is retried many times: on 2026-11-14 IRSA refused about two requests in three,
in bursts lasting several seconds, while identical retries succeeded."""

BUSY_STATUS = (429, 500, 502, 503, 504)
BUSY_BACKOFF_S = (0.5, 1.0, 2.0, 4.0, 6.0)
"""Waits between retries when any other service answers "busy"."""

DOWNLOAD_WORKERS = 20
"""Photos fetched at once. Those that have to come from IRSA's own servers instead of the cloud
copy are further limited to IRSA_WORKERS at a time (archive/store.py)."""
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
"""Display only: each SPHEREx pixel is drawn as up to 4x4 screen pixels (Lanczos)."""
DISPLAY_TARGET_PX = 520
"""Wide views are enlarged less, so every picture is roughly this many screen pixels across."""

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
"""This many masked pixels inside FIT_RADIUS_PX means the star is saturated: its brightness is
not measured, and its position comes from fitting its unsaturated wings."""
WING_FIT_RADIUS_PX = 6.5
WING_PROFILE_WIDEN = 2.0
"""Wing fit for saturated stars: the profile fit run on the unmasked pixels out to 6.5 px with
a profile twice as wide (far from the core a star's light falls off more slowly than its
core's Gaussian). Measured on Barnard's Star, 110 saturated photos in six cameras: unbiased
(median within 0.1-0.4" of Gaia's prediction) with 0.5-1.3" scatter per photo, where the
centre of the masked hole was off by up to 7"."""
WING_MIN_SNR = 10.0
"""Below this the wings are too faint to fit and the centre of the masked core is used."""
PHOTO_POSITION_FLOOR_ARCSEC = {"ok": 0.3, "partial": 0.6, "saturated": 1.0}
"""Per-axis position error of ONE photo that no amount of signal removes (pixel sampling,
masked pixels, saturation). Measured: clean field stars shift ~0.2-0.3" between looks;
Barnard's Star's partly masked photos scatter 0.3-0.5", its saturated ones 0.5-1.3"."""
MIN_MEASURE_SNR = 5.0
"""A season's median signal-to-noise must reach this for a motion measurement."""
MAX_TRACK_OFFSET_ARCSEC = 3.0
"""What is measured must stay this close to the catalogue's predicted track in every season,
or it is a different (usually static) object."""
ASTROMETRY_FLOOR_ARCSEC = 1.0
"""Per-look position floor when a view has too few reference stars to measure its own."""
SYSTEMATIC_FLOOR_ARCSEC = 0.3
"""An error that averaging does not remove, added to every motion. Measured: for seven stars
with well-known motions (Barnard's Star, Epsilon Indi B, Proxima, Wolf 359, Teegarden's Star,
RW Aurigae, R Draconis) the all-camera result differed from the catalogue by 0.2-0.6", more
than the scatter between photos and cameras explains. The cameras share the same pointing
errors and the same star, whose colour differs from the reference stars', so they are not
fully independent."""
AGREE_FACTOR = 2.45
"""Measured and predicted motion "agree" when their vector difference is within 2.45 x the
per-axis error: the 95% radius of a two-dimensional Gaussian."""
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

# --------------------------------------------------------------------------- one visit (asteroids)
MOMENT_GAP_DAYS = 0.02
"""Photos closer than this (29 minutes) are one moment: SPHEREx takes a short burst, in which
even a fast asteroid moves a tenth of a pixel. Burst photos are not independent sightings."""
VISIT_GAP_DAYS = 3.0
VISIT_MAX_DAYS = 10.0
"""A visit is searched over at most 10 days: a main-belt asteroid crosses the view in under a
day, so photos further apart can never show it three times."""
VISIT_MAX_PHOTOS = 36
VISIT_MIN_MOMENTS = 3
"""A path needs sightings in three separate moments. This is a hard floor on what the search
can find: an object in view for fewer than three moments is not findable at any brightness."""
VISIT_STRONG_MOMENTS = 4
VISIT_MIN_COMPLETENESS = 0.7
"""A "strong" track was seen in 4+ moments and in 70% of the moments where it could have been.
Three aligned leftovers alone happen by chance, so they stay "possible"."""
VISIT_DETECT_SIGMA = 5.0
VISIT_THREE_MOMENT_SIGMA = 6.0
"""A path seen in only three moments must be clear in each. Measured on a real 293-pixel
field: two chance alignments of 5-6.7 sigma leftovers appeared with a 5 sigma threshold."""
VISIT_EDGE_PX = 2
VISIT_MAX_PEAKS_PER_MOMENT = 60
VISIT_MIN_SHIFT_PX = 1.5
"""Two sightings must be this far apart to define a path: nearer, they are a star's residue."""
VISIT_MAX_SPEED_ARCSEC_H = 400.0
VISIT_LINK_TOLERANCE_PX = 1.5
VISIT_MAX_RMS_PX = 0.8
VISIT_MAX_TRACKS = 12
ASTEROID_MATCH_ARCSEC = 25.0
"""A track is named after a catalogued asteroid predicted within this distance of it (the
prediction is for Earth's centre; SPHEREx's orbit shifts main-belt objects by a few arcsec)."""
ASTEROID_FAINT_VMAG = 18.5
"""About the faintest asteroid the search recovers; fainter known ones are listed, not expected."""

# --------------------------------------------------------------------------- cache
ENGINE_VERSION = "gb4"
"""Part of every cache key. Bump it whenever the engine's output changes, or old views are
served forever."""
CACHE_PHOTOS_MAX_BYTES = 600 * 1024 * 1024
CACHE_VIEWS_MAX_BYTES = 600 * 1024 * 1024
"""The cache is trimmed, oldest first, after every build: on the host it lives in memory."""
DEGRADED_RETRY_S = 1800.0
"""A view built while a service was failing says so, and is rebuilt after this long."""
