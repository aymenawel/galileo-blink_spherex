# References

Every external resource Galileo Blink uses: data, services, software and fonts.

## The challenge

| Resource | Used for | Link |
|---|---|---|
| NASA Space Apps Challenge 2026, "Planet X and SPHEREx" | The challenge statement and its five test targets | https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/ |

## NASA data and services

| Resource | Used for | Link |
|---|---|---|
| SPHEREx Level-2 spectral images (DR1, doi:10.26131/IRSA678; QR3, doi:10.26131/IRSA662), NASA/JPL-Caltech | Every image shown | https://irsa.ipac.caltech.edu/Missions/spherex.html |
| SPHEREx DR1 spectral all-sky cube (HiPS, doi:10.26131/IRSA679) | Quick-look spectra, and the all-sky picture on the home page (made by `scripts/make_sky_map.py` from the cube's 4.4 to 5.0 micron previews) | https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube |
| NASA/IPAC Infrared Science Archive (IRSA): Simple Image Access, file server | Finding and reading photos | https://irsa.ipac.caltech.edu |
| IRSA public cloud copy of SPHEREx (AWS Open Data, bucket `nasa-irsa-spherex`) | Fast partial reads of photos and cube tiles | https://irsa.ipac.caltech.edu/cloud_access/ |
| IRSA catalogue service (Gator): CatWISE2020 | Brown dwarfs and other objects Gaia cannot see | https://irsa.ipac.caltech.edu/applications/Gator/ |
| NASA Mikulski Archive for Space Telescopes (MAST): Gaia DR3 cone search | Star positions, proper motions, parallaxes | https://archive.stsci.edu/missions-and-data/gaia |
| NASA/IPAC Extragalactic Database (NED) object lookup | Object names (fallback) | https://ned.ipac.caltech.edu |
| SPHEREx Explanatory Supplement and IRSA SPHEREx tutorial notebooks | File formats, flags, the wavelength lookup table | https://caltech-ipac.github.io/irsa-tutorials/spherex/ |
| NASA/IPAC Moving Object Search Tool (MOST) | Which SPHEREx photos contain a named asteroid | https://irsa.ipac.caltech.edu/applications/MOST/ |
| WiseView (Backyard Worlds) | The design model for a blink viewer, from an earlier NASA mission; no code used | http://byw.tools/wiseview |

## Other data and services

| Resource | Used for | Link |
|---|---|---|
| Gaia Data Release 3, ESA/Gaia/DPAC (Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1) | Catalogue predictions | https://www.cosmos.esa.int/gaia |
| CatWISE2020 (Marocco et al. 2021, ApJS 253, 8), built from WISE and NEOWISE | Catalogue predictions | https://catwise.github.io |
| AllWISE Source Catalog (Cutri et al. 2013) | WISE 0855 reference position | https://wise2.ipac.caltech.edu/docs/release/allwise/ |
| Luhman & Esplin 2016, AJ 152, 78 | WISE 0855 proper motion and parallax | https://doi.org/10.3847/0004-6256/152/3/78 |
| IMCCE SkyBoT cone search (Berthier et al. 2006, ASPC 351, 367) | Known asteroids in a field at a moment | https://ssp.imcce.fr/webservices/skybot/ |
| CDS Sesame name resolver (SIMBAD; Wenger et al. 2000, A&AS 143, 9) | Object names | https://cds.unistra.fr/cgi-bin/Sesame |
| CfA mirror of CDS Sesame | Object names (asked first; CDS itself is the second choice) | https://vizier.cfa.harvard.edu |

## Software

| Library | Licence | Used for |
|---|---|---|
| Python | PSF-2.0 | The engine and the server |
| Astropy (Astropy Collaboration 2013, 2018, 2022) | BSD-3-Clause | FITS, world coordinates, time, ephemerides |
| pyerfa, astropy-iers-data (with Astropy) | BSD-3-Clause | Astronomical time and Earth-orientation calculations inside Astropy |
| astropy-healpix | BSD-3-Clause | Locating all-sky cube tiles |
| reproject | BSD-3-Clause | Resampling photos onto a north-up grid |
| NumPy | BSD-3-Clause | Arrays |
| SciPy | BSD-3-Clause | Interpolation, special functions |
| Pillow | MIT-CMU | Writing PNGs and animated GIFs |
| Requests | Apache-2.0 | HTTP |
| certifi, urllib3, idna, charset-normalizer (with Requests) | MPL-2.0, MIT, BSD-3-Clause, MIT | Secure connections, character sets, internet names |
| FastAPI | MIT | The web API |
| Starlette | BSD-3-Clause | The web framework under FastAPI |
| Pydantic | MIT | Data models for the web API |
| Swagger UI (loaded by FastAPI's API reference page at `/api/docs`) | Apache-2.0 | The API reference page |
| Uvicorn, with its standard extras (httptools, websockets, watchfiles, python-dotenv, PyYAML, uvloop on Linux) | BSD-3-Clause; extras MIT or BSD-3-Clause | The web server |
| Packages installed with the above (for example dask, zarr, numcodecs, fsspec and cloudpickle with reproject; AnyIO with Starlette; h11 and Click with Uvicorn; packaging with Astropy) | BSD-3-Clause, MIT or Apache-2.0 | Support for the libraries above; not called by Galileo Blink directly |
| pytest, HTTPX | MIT, BSD-3-Clause | Tests |
| Node.js and npm | MIT, Artistic-2.0 | Building and testing the interface |
| React, React DOM | MIT | The interface |
| Vite | MIT | Building the interface |
| @vitejs/plugin-react | MIT | React support in Vite |
| TypeScript | Apache-2.0 | The interface's language and type checks |
| @types/react, @types/react-dom, @types/node (DefinitelyTyped) | MIT | Type definitions |
| Lucide (lucide-react) | ISC | Icons |
| Fontsource (@fontsource-variable/hanken-grotesk) | MIT (the package; the font has its own licence below) | Self-hosting the typeface |

## Fonts

| Font | Licence | Used for |
|---|---|---|
| Hanken Grotesk | SIL Open Font License 1.1 | All text on the site; self-hosted from the Fontsource package |
| Aileron Regular (bundled with Pillow) | CC0 | The captions drawn into saved GIFs |

## AI tools

| Tool | Used for | Link |
|---|---|---|
| Claude (Anthropic), through Claude Code | AI coding assistant; see "Use of AI" in the README | https://www.anthropic.com/claude-code |

## Hosting and build

| Service | Used for | Link |
|---|---|---|
| Google Cloud Run and Cloud Build | Building the container and hosting the public site | https://cloud.google.com/run |
| Docker official images `node:22-slim` and `python:3.12-slim` | The two stages of the container build | https://hub.docker.com/_/node, https://hub.docker.com/_/python |
| GitHub | Source hosting | https://github.com/aymenawel/galileo-blink_spherex |
