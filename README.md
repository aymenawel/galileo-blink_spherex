# Galileo Blink

**Watch the infrared sky move.**

NASA's SPHEREx telescope photographs the entire sky every six months in 102 infrared colours.
Things that move reveal themselves by shifting between those photos: nearby stars, brown
dwarfs, asteroids. The data is public, but it sits in an archive of 1.6 million files that
takes real expertise to use.

Galileo Blink opens it to everyone. Type a place in the sky, watch it blink across the dates
like a short video, and see what moved. No code, no downloads, no astronomy degree.

**Try it: https://galileoblink.earth** (also at https://galileo-blink-802043035343.us-east4.run.app)

Built by **Team Galileo** for the 2026 NASA Space Apps Challenge, *Planet X and SPHEREx*.
An independent student project. Not an official NASA product.

## What it does

| You want to... | Galileo Blink gives you |
|---|---|
| Start from the whole sky | An all-sky infrared map made from SPHEREx's own mosaic: click anywhere to open that place |
| Look at any place | Type coordinates (decimal, sexagesimal, or NASA's own "Right Ascension 08h55m10.831s, declination -7d14m42.53s") or an object name |
| Choose how to look | Pictures months apart (for stars) or hours apart (for asteroids), the width of the view in fractions of the Moon, and the camera of an asteroid search |
| See what moved | A blink of every six-month season SPHEREx has seen, aligned north-up, in all six cameras at once |
| Know where things *should* be | Markers from Gaia DR3 and CatWISE2020, carried to each date with proper motion and parallax |
| Be shown what to look for | A short guided first look on every view: a few steps that set the picture and say in plain words what moved and why it matters |
| Measure it | The motion of the central object versus its catalogue prediction, per camera, with error bars measured from the stars that do not move |
| Compare dates | Swipe between two dates, subtract one from another, or add everything together |
| See if it changed brightness | Each camera compared with itself from date to date, with the apparent change of ordinary stars in the same view as the error floor |
| Find asteroids | One visit, moment by moment: the sky that stays put is subtracted and what is left moving is tracked, then named from the asteroid catalogue. Type an asteroid's name to watch it cross |
| See its colours | A spectrum from the photos themselves, and a 102-colour quick look anywhere from NASA's all-sky cube |
| Trust it | NASA's quality flags shown on the image; every limit stated in plain words |
| Check it elsewhere | Links to the same place in NASA's SPHEREx viewer, WiseView, SIMBAD and the Legacy Surveys |
| Understand the words | Fifteen terms explained in one sentence each, linked from every view |
| Share it | Everything is in the URL, coordinates included, and any view can be embedded in another page with an `<iframe>` |
| Save it | Any camera's blink as an animated GIF, or one picture with the measurement written on it |

NASA's five test targets (Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis)
and five asteroid examples are prebuilt and open instantly. Any other place is built live, usually
in under a minute (about 40 seconds on the public site, half of it waiting for NASA's
archive to list the photos).

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
| Epsilon Indi B | 4.25 ± 0.39″ | 4.61″ | 5 | agrees |
| WISE 0855 | 9.02 ± 1.43″ | 8.07″ | 1 (camera 5, May 2025 to May 2026; its May 2026 photo is blended with a faint star, see HOW_IT_MEASURES. Camera 6 saw it only from November 2025: 3.11 ± 1.43″ against 4.51″) | agrees |
| RW Aurigae | 0.47 ± 0.40″ | 0.03″ | 6 | does not move, as expected |
| R Draconis | 1.30 ± 0.69″ | 0.02″ | 2 (saturated in every photo; measured from its wings) | consistent with no motion (large error: saturated) |
| Proxima Centauri (typed, built live) | 3.66 ± 0.48″ | 3.84″ | 6 | agrees |
| Wolf 359 (typed, built live) | 4.52 ± 0.41″ | 4.78″ | 6 | agrees |
| Teegarden's Star (typed, built live) | 5.33 ± 0.38″ | 5.15″ | 6 | agrees |

The five test targets are reproduced with `python scripts/prebuild_targets.py`; the three
typed rows by typing the star's name on the site.

The table is measured on each target's 9-arcminute view. Every target is also shipped at 6,
15, 24 and 30 arcminutes, so it opens and resizes without waiting for a build, and the site
opens each one wider than the table's view (Barnard's Star at 30 arcminutes, WISE 0855 at
15, the others at 24) to show more of the sky around it. A wider view is registered on
different reference stars, so its measurement differs a little (Barnard's Star: 10.05″ to
10.27″ across the five sizes, 10.16″ at the size it opens at), always by less than the
stated error. Choose 9 arcminutes in the view's size menu to see the table's numbers.

The asteroid search, run blind on real visits, recovers and names the known asteroids
Eugenia, Bamberga, Hygiea, Iris and the faint Steins (magnitude 17.5), each as the single
strong track in its field.

## How it fits together

```
web/                    The interface (React + TypeScript, built with Vite). Pictures and
                        numbers only: every measurement and prediction comes from the
                        engine; the browser only converts picture positions to coordinates
                        for the pointer readout.
  src/api/              Talking to the server: requests, response types, the view cache.
  src/components/       The pieces of the screen: the viewer, the panels, the page frame.
  src/pages/            One file per page: Home, Explore, How it works, About, Not found.
  src/lib/              Shared helpers: wording, coordinates, number formats, plot scales.
  src/content/          The text of the longer pages.
  src/styles/           The stylesheets.
galileo_blink/
  server/               The web layer (FastAPI). Thin: routes, the background build queue,
    app.py              honest error states. No astronomy here either.
    jobs.py
  engine/               The science. Pure Python, no web code; usable from a script or notebook.
    constants.py        The main tuning numbers, each with its reason. Numbers that belong
                        to one step are named at the top of that step's module.
    errors.py           The engine's error types: a bad request, a service that did not
                        answer, a place SPHEREx has not photographed.
    flags.py            NASA's per-pixel quality flags in plain words.
    archive/            Getting the data.
      photos.py           Which photos cover a place (IRSA Simple Image Access).
      remote_fits.py      Reads a small cutout out of a 65 MB exposure with partial reads.
      store.py            Cloud copy first, IRSA as fallback, validated disk cache.
      http.py, cache.py   Deadlines and retries on every request; atomic cache writes.
    image/              Working with pixels.
      frames.py           Fetches one photo and readies it: aligned, quality-checked, flags counted.
      grid.py             Puts every photo on one north-up grid.
      stack.py            Adds photos together; subtracts one date from another.
      measure.py          Position and brightness of a star (profile fit; wing fit if saturated).
      render.py           PNGs for the browser; "no data" stays visibly no data.
      card.py             One still picture with the result written under it, to save and share.
    sky/                Working with the sky.
      coords.py           What a person typed -> a place (and follows fast stars to today).
      catalogues.py       Gaia DR3 (NASA MAST) and CatWISE2020 (NASA/IPAC IRSA).
      asteroids.py        Known asteroids in a field (IMCCE SkyBoT); a named one's photos (IRSA MOST).
      motion.py           Where a catalogued object is on a given date.
      targets.py          NASA's five test targets.
    looks/              The six-month view.
      seasons.py          Groups photos into looks and seasons.
      astrometry.py       Registration on field stars; measured vs predicted motion.
      variability.py      Did the brightness change? Each camera against itself, with a floor
                          from the stars that do not vary.
      build.py            The whole job: one place -> pictures + view.json.
    visit/              The asteroid view (one visit, moment by moment).
      detect.py           Image subtraction, then linking leftovers into straight paths.
      build.py            The whole job: one visit -> pictures, tracks, named asteroids.
    spectrum/
      cube.py             A 102-colour quick-look spectrum from the DR1 all-sky cube.
data/                   Catalogue values for the five test targets; the asteroid examples.
prebuilt/               Ready-made views, shipped with the site so they open instantly.
scripts/                prebuild_targets.py; make_sky_map.py (the home page's all-sky picture)
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
until it is ready, then only ever loads pictures and JSON. Every route of the web API is
described at `/api/docs` on a running server.

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

Requirements: Python 3.11+, Node 22.18+ (`npm test` runs the `.ts` test files directly
with `node --test`).

```bash
python -m pip install -e ".[dev]"
python -m uvicorn galileo_blink.server.app:app --port 8000
```

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5173. For a production-style run, `npm run build` in `web/` and open
http://localhost:8000 (the Python server serves the built interface). The server looks for
`web/dist` when it starts, so restart it after building.

## Test it

```bash
python -m pytest
```

```bash
python -m pytest -m live tests/live
```

```bash
cd web && npm test && npm run typecheck
```

The first runs offline against synthetic SPHEREx-like photos with known truth. The second
talks to NASA's live services and checks, among other things, that a cutout read from the
cloud copy equals IRSA's own cutout service pixel for pixel. The third runs the interface's
own tests and checks its TypeScript.

## Deploy it

One container serves everything:

```bash
docker build -t galileo-blink .
```

```bash
docker run -p 8080:8080 galileo-blink
```

It runs anywhere containers do. The public site runs on Google Cloud Run in a US-East region,
next to NASA's cloud copy of the archive, so photos arrive fastest:

```bash
gcloud run deploy galileo-blink --source . --region us-east4 --cpu 4 --memory 4Gi --min-instances 1 --max-instances 1 --no-cpu-throttling --allow-unauthenticated
```

Views are built in background threads and the table of build jobs lives in memory, so the
service needs one instance that is always on (`--min-instances 1 --max-instances 1`) with
CPU that stays allocated between requests (`--no-cpu-throttling`). Set
`GALILEO_BLINK_CACHE` to a persistent folder to keep built views between restarts.

## New data releases

SPHEREx data arrives continuously. Three places know about releases, each one line:
`SPHEREX_COLLECTIONS` in `engine/constants.py` (image collections), `CUBE_PREFIX` in
`engine/spectrum/cube.py` (the all-sky cube), and `ENGINE_VERSION` to retire cached views.
Then delete `prebuilt/` and rerun `python scripts/prebuild_targets.py --ship`. Deleting
first matters: an asteroid view's folder name includes the engine version, so after a bump
the old folders would otherwise be left behind next to the new ones.

## Use of AI

Galileo Blink was built with an AI coding assistant, Anthropic's Claude, under the team's direction. It wrote most of the code, the documentation and the site's text, and designed the interface. The demo video was animated in code the same way, with an AI-generated voice and music (ElevenLabs). No AI-generated images are used.

## Data and credits

- **SPHEREx** Level-2 images and the DR1 all-sky spectral cube: NASA/JPL-Caltech, served by
  the NASA/IPAC Infrared Science Archive (IRSA) and its public cloud copy on AWS Open Data.
  Datasets: DR1 spectral images (doi:10.26131/IRSA678), QR3 spectral images
  (doi:10.26131/IRSA662), DR1 spectral all-sky cube (doi:10.26131/IRSA679).
- **Gaia DR3**: ESA/Gaia/DPAC, served by NASA's Mikulski Archive for Space Telescopes (MAST).
- **CatWISE2020** (Marocco et al. 2021): served by IRSA.
- WISE 0855 proper motion and parallax: Luhman & Esplin 2016, AJ 152, 78.
- Object names: CDS Sesame (SIMBAD) and the NASA/IPAC Extragalactic Database.
- Asteroids: IMCCE SkyBoT (Berthier et al. 2006) and the NASA/IPAC Moving Object Search Tool.

Every library, dataset and font used is listed in [docs/REFERENCES.md](docs/REFERENCES.md).
How each number is measured, and what the tool cannot do, is in
[docs/HOW_IT_MEASURES.md](docs/HOW_IT_MEASURES.md).

## Acknowledgements

This research has made use of the NASA/IPAC Infrared Science Archive, which is funded by the
National Aeronautics and Space Administration and operated by the California Institute of
Technology.

This publication makes use of data products from the Spectro-Photometer for the History of
the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of
the Jet Propulsion Laboratory and the California Institute of Technology, and is funded by the
National Aeronautics and Space Administration.

This work has made use of data from the European Space Agency (ESA) mission Gaia
(https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis
Consortium (DPAC, https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the DPAC
has been provided by national institutions, in particular the institutions participating in
the Gaia Multilateral Agreement.

This publication makes use of data products from the Wide-field Infrared Survey Explorer,
which is a joint project of the University of California, Los Angeles, and the Jet Propulsion
Laboratory/California Institute of Technology, funded by the National Aeronautics and Space
Administration. This publication also makes use of data products from NEOWISE, which is a
project of the Jet Propulsion Laboratory/California Institute of Technology, funded by the
Planetary Science Division of the National Aeronautics and Space Administration. The CatWISE2020
catalogue built from them is described by Marocco et al. 2021, ApJS 253, 8.

This research has made use of IMCCE's SkyBoT VO tool (Berthier et al. 2006, ASP Conf. Ser.
351, 367).

This research has made use of the NASA/IPAC Extragalactic Database (NED), which is funded by
the National Aeronautics and Space Administration and operated by the California Institute of
Technology.

This research has made use of the SIMBAD database, operated at CDS, Strasbourg, France
(Wenger et al. 2000, A&AS 143, 9), through the CDS Sesame name resolver.

This research made use of Astropy, a community-developed core Python package and an ecosystem
of tools and resources for astronomy (Astropy Collaboration 2013, 2018, 2022).

## Licence

Apache-2.0. See [LICENSE](LICENSE).
