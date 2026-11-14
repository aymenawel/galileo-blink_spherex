# Galileo Blink

**Watch the infrared sky move.**

NASA's SPHEREx telescope photographs the entire sky every six months in 102 infrared colours.
Things that move reveal themselves by shifting between those photos: nearby stars, brown
dwarfs, asteroids. The data is public, but it sits in an archive of 1.6 million files that
takes real expertise to use.

Galileo Blink opens it to everyone. Type a place in the sky, watch it blink across the dates
like a short video, and see what moved. No code, no downloads, no astronomy degree.

Built by **Team Galileo** for the 2026 NASA Space Apps Challenge, *Planet X and SPHEREx*.

## What it does

| You want to... | Galileo Blink gives you |
|---|---|
| Look at any place | Type coordinates (decimal, sexagesimal, or NASA's own "Right Ascension 08h55m10.831s, declination -7d14m42.53s") or an object name |
| See what moved | A blink of every six-month season SPHEREx has seen, aligned north-up, in all six cameras at once |
| Know where things *should* be | Markers from Gaia DR3 and CatWISE2020, carried to each date with proper motion and parallax |
| Measure it | The motion of the central object versus its catalogue prediction, per camera, with error bars measured from the stars that do not move |
| Compare dates | Swipe between two dates, subtract one from another, or add everything together |
| Find asteroids | One visit, moment by moment: the sky that stays put is subtracted and what is left moving is tracked, then named from the asteroid catalogue. Type an asteroid's name to watch it cross |
| See its colours | A spectrum from the photos themselves, and a 102-colour quick look anywhere from NASA's all-sky cube |
| Trust it | NASA's quality flags shown on the image; every limit stated in plain words |
| Share it | Everything is in the URL |

NASA's five test targets (Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis)
and five asteroid examples are prebuilt and open instantly. Any other place is built live, in
well under a minute.

**What it is not.** Galileo Blink does not claim discoveries. A distant planet beyond Neptune
would be too faint for a single SPHEREx photo and would jump 10 to 25 arcminutes between
looks rather than creep; this tool cannot find one by itself. It gives everyone the means to
look.

## Checked against the catalogues

Measured by the engine from SPHEREx photos, compared with what Gaia DR3 (or, for WISE 0855,
Luhman & Esplin 2016) predicts for the same dates. Errors are one sigma.

| Target | Measured | Catalogue predicts | Cameras | Verdict |
|---|---|---|---|---|
| Barnard's Star | 10.27 ± 0.46″ | 10.29″ | 6 | agrees |
| Epsilon Indi B | 4.25 ± 0.39″ | 4.61″ | 6 | agrees |
| WISE 0855 | 9.02 ± 1.43″ | 8.07″ | 1 (camera 5 only: it is invisible at shorter wavelengths) | agrees |
| RW Aurigae | 0.47 ± 0.40″ | 0.03″ | 6 | does not move, as expected |
| R Draconis | 1.30 ± 0.69″ | 0.02″ | saturated in every photo; measured from its wings | does not move, as expected |

Reproduce them with `python scripts/prebuild_targets.py`.

The asteroid search, run blind on real visits, finds and names Eugenia, Bamberga, Hygiea, Iris
and the faint Steins (magnitude 17.5), each as the single strong track in its field.

## How it fits together

```
web/                    The interface (React + TypeScript, built with Vite). Pictures and
                        numbers only: no astronomy happens in the browser.
galileo_blink/
  server/               The web layer (FastAPI). Thin: routes, the background build queue,
    app.py              honest error states. No astronomy here either.
    jobs.py
  engine/               The science. Pure Python, no web code; usable from a script or notebook.
    constants.py        Every number that changes a result, with its reason, in one place.
    flags.py            NASA's per-pixel quality flags in plain words.
    archive/            Getting the data.
      photos.py           Which photos cover a place (IRSA Simple Image Access).
      remote_fits.py      Reads a small cutout out of a 65 MB exposure with partial reads.
      store.py            Cloud copy first, IRSA as fallback, validated disk cache.
      http.py, cache.py   Deadlines and retries on every request; atomic cache writes.
    image/              Working with pixels.
      grid.py             Puts every photo on one north-up grid.
      stack.py            Adds photos together; subtracts one date from another.
      measure.py          Position and brightness of a star (profile fit; wing fit if saturated).
      render.py           PNGs for the browser; "no data" stays visibly no data.
    sky/                Working with the sky.
      coords.py           What a person typed -> a place (and follows fast stars to today).
      catalogues.py       Gaia DR3 (NASA MAST) and CatWISE2020 (NASA/IPAC IRSA).
      asteroids.py        Known asteroids in a field (IMCCE SkyBoT); a named one's photos (IRSA MOST).
      motion.py           Where a catalogued object is on a given date.
      targets.py          NASA's five test targets.
    looks/              The six-month view.
      seasons.py          Groups photos into looks and seasons.
      astrometry.py       Registration on field stars; measured vs predicted motion.
      build.py            The whole job: one place -> pictures + view.json.
    visit/              The asteroid view (one visit, moment by moment).
      detect.py           Image subtraction, then linking leftovers into straight paths.
      build.py            The whole job: one visit -> pictures, tracks, named asteroids.
    spectrum/
      cube.py             A 102-colour quick-look spectrum from the DR1 all-sky cube.
data/                   Catalogue values for the five test targets; the asteroid examples.
prebuilt/               Ready-made views, shipped with the site so they open instantly.
scripts/                prebuild_targets.py
tests/                  Offline tests (synthetic photos with known truth) and live checks.
```

**One request, end to end.** The browser asks `/api/view?ra=..&dec=..`. The server answers at
once with a key and starts a background build. The engine asks IRSA which photos cover the
place (about a second), picks up to four per camera per season, and reads each one's cutout
straight out of NASA's cloud copy of the archive with HTTP range requests (about 2 MB instead
of 65 MB each), while Gaia and CatWISE are queried in parallel. Each photo is masked with
NASA's flags, resampled north-up, and stacked per camera and season. Field stars correct each
photo's astrometry; the central object is measured in every photo and compared with its
catalogue prediction. The result is a folder of PNGs and one `view.json`. The browser polls
until it is ready, then only ever loads pictures and JSON.

### Rules the engine keeps

1. **Never mask the flags that mark movers.** NASA's OUTLIER flag marks pixels that differ
   between exposures, which is exactly what a moving object is. Only dead, hot, cold, missing
   and failed pixels are treated as "no data" (`constants.MASK_BITS`; a test pins the list).
2. **Reproject before blinking.** SPHEREx rolls with the ecliptic, so raw photos of one place
   arrive in two orientations. Every photo is resampled onto one north-up grid.
3. **Measure in native pixels with a pixel-integrated profile.** SPHEREx's star image is
   narrower than two pixels. Saturated stars are measured from their unsaturated wings.
4. **Compare motion as vectors, and always carry an error.** The error comes from the view's
   own stars that do not move.
5. **Every network call has a deadline; every outage is stated.** A view built while a service
   was failing says what failed and is rebuilt later.
6. **Only data that parsed is cached.** Bump `constants.ENGINE_VERSION` when output changes.

## Run it

Requirements: Python 3.11+, Node 20+.

```bash
python -m pip install -e ".[dev]"
python -m uvicorn galileo_blink.server.app:app --port 8000
```

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5173. For a production-style run, `npm run build` in `web/` and open
http://localhost:8000 (the Python server serves the built interface).

## Test it

```bash
python -m pytest
```

```bash
python -m pytest -m live tests/live
```

The first runs offline against synthetic SPHEREx-like photos with known truth. The second
talks to NASA's live services and checks, among other things, that a cutout read from the
cloud copy equals IRSA's own cutout service pixel for pixel.

## Deploy it

One container serves everything:

```bash
docker build -t galileo-blink .
```

```bash
docker run -p 8080:8080 galileo-blink
```

It runs anywhere containers do. A US-East region is the natural home: NASA's cloud copy of
the archive lives there, so photos arrive fastest. Set `GALILEO_BLINK_CACHE` to a persistent folder to keep
built views between restarts.

## New data releases

SPHEREx data arrives continuously. Three places know about releases, each one line:
`SPHEREX_COLLECTIONS` in `engine/constants.py` (image collections), `CUBE_PREFIX` in
`engine/spectrum/cube.py` (the all-sky cube), and `ENGINE_VERSION` to retire cached views.
Then rerun `python scripts/prebuild_targets.py --ship`.

## Data and credits

- **SPHEREx** Level-2 images and the DR1 all-sky spectral cube: NASA/JPL-Caltech, served by
  the NASA/IPAC Infrared Science Archive (IRSA) and its public cloud copy on AWS Open Data.
- **Gaia DR3**: ESA/Gaia/DPAC, served by NASA's Mikulski Archive for Space Telescopes (MAST).
- **CatWISE2020** (Marocco et al. 2021): served by IRSA.
- WISE 0855 proper motion and parallax: Luhman & Esplin 2016, AJ 152, 78.
- Object names: CDS Sesame (SIMBAD) and the NASA/IPAC Extragalactic Database.
- Asteroids: IMCCE SkyBoT (Berthier et al. 2006) and the NASA/IPAC Moving Object Search Tool.

Every library, dataset and font used is listed in [docs/REFERENCES.md](docs/REFERENCES.md).
How each number is measured, and what the tool cannot do, is in
[docs/HOW_IT_MEASURES.md](docs/HOW_IT_MEASURES.md).

## Licence

Apache-2.0. See [LICENSE](LICENSE).
