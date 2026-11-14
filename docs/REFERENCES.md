# References

Every external resource Galileo Blink uses: data, services, software and fonts.

## NASA data and services

| Resource | Used for | Link |
|---|---|---|
| SPHEREx Level-2 spectral images (DR1, QR3), NASA/JPL-Caltech | Every image shown | https://irsa.ipac.caltech.edu/Missions/spherex.html |
| SPHEREx DR1 all-sky spectral cube (HiPS) | Quick-look spectra | https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube |
| NASA/IPAC Infrared Science Archive (IRSA): Simple Image Access, file server | Finding and reading photos | https://irsa.ipac.caltech.edu |
| IRSA public cloud copy of SPHEREx (AWS Open Data, bucket `nasa-irsa-spherex`) | Fast partial reads of photos and cube tiles | https://irsa.ipac.caltech.edu/cloud_access/ |
| IRSA catalogue service (Gator): CatWISE2020 | Brown dwarfs and other objects Gaia cannot see | https://irsa.ipac.caltech.edu/applications/Gator/ |
| NASA Mikulski Archive for Space Telescopes (MAST): Gaia DR3 cone search | Star positions, proper motions, parallaxes | https://archive.stsci.edu/missions-and-data/gaia |
| NASA/IPAC Extragalactic Database (NED) object lookup | Object names (fallback) | https://ned.ipac.caltech.edu |
| SPHEREx Explanatory Supplement and IRSA SPHEREx tutorial notebooks | File formats, flags, the wavelength lookup table | https://caltech-ipac.github.io/irsa-tutorials/spherex/ |
| NASA/IPAC Moving Object Search Tool (MOST) | Which SPHEREx photos contain a named asteroid | https://irsa.ipac.caltech.edu/applications/MOST/ |
| WiseView (Backyard Worlds) | The model: a blink tool for an earlier NASA mission | http://byw.tools/wiseview |

## Other data and services

| Resource | Used for | Link |
|---|---|---|
| Gaia Data Release 3, ESA/Gaia/DPAC (Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1) | Catalogue predictions | https://www.cosmos.esa.int/gaia |
| CatWISE2020 (Marocco et al. 2021, ApJS 253, 8) | Catalogue predictions | https://catwise.github.io |
| AllWISE Source Catalog (Cutri et al. 2013) | WISE 0855 reference position | https://wise2.ipac.caltech.edu/docs/release/allwise/ |
| Luhman & Esplin 2016, AJ 152, 78 | WISE 0855 proper motion and parallax | https://doi.org/10.3847/0004-6256/152/3/78 |
| IMCCE SkyBoT cone search (Berthier et al. 2006, ASPC 351, 367) | Known asteroids in a field at a moment | https://ssp.imcce.fr/webservices/skybot/ |
| CDS Sesame name resolver (SIMBAD; Wenger et al. 2000), via the CDS and CfA mirrors | Object names | https://cds.unistra.fr/cgi-bin/Sesame |

## Software

| Library | Licence | Used for |
|---|---|---|
| Astropy (Astropy Collaboration 2013, 2018, 2022) | BSD-3-Clause | FITS, world coordinates, time, ephemerides |
| astropy-healpix | BSD-3-Clause | Locating all-sky cube tiles |
| reproject | BSD-3-Clause | Resampling photos onto a north-up grid |
| NumPy | BSD-3-Clause | Arrays |
| SciPy | BSD-3-Clause | Interpolation, special functions |
| Pillow | MIT-CMU | Writing PNGs |
| Requests | Apache-2.0 | HTTP |
| FastAPI, Starlette | MIT, BSD-3-Clause | The web API |
| Uvicorn | BSD-3-Clause | The web server |
| pytest, HTTPX | MIT, BSD-3-Clause | Tests |
| React, React DOM | MIT | The interface |
| Vite, TypeScript | MIT, Apache-2.0 | Building the interface |
| Lucide | ISC | Icons |

## Fonts

| Font | Licence |
|---|---|
| Instrument Serif | SIL Open Font License 1.1 |
| Instrument Sans | SIL Open Font License 1.1 |
| DM Mono | SIL Open Font License 1.1 |

All three are self-hosted from the Fontsource packages.
