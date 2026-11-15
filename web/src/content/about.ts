/** The text of the "About" page: the challenge, the team, how AI was used, and everyone whose work this stands on. */

export const ABOUT_INTRO = {
  eyebrow: "About",
  title: { before: "A student tool for ", emphasis: "looking", after: " at the sky." },
  lede: "Galileo Blink was built for the 2026 NASA Space Apps Challenge, for the challenge \"Planet X and SPHEREx\".",
};

export const CHALLENGE = {
  title: "The challenge",
  paragraphs: [
    "SPHEREx photographs the whole sky again and again. Anything that moves between visits (a nearby star, a brown dwarf, perhaps something not yet catalogued) changes place from one set of images to the next. The challenge asks teams to help people explore those repeated images, and it names five known objects to test a tool on.",
    "Our answer is a blink viewer: the oldest trick in astronomy for finding things that move, made for SPHEREx and for people who have never opened an archive. It does not claim discoveries. It shows NASA's images honestly, measures what can be measured, and says what cannot.",
  ],
};

export const TEAM = {
  title: "The team",
  name: "Team Galileo",
  members: ["Adam", "Aymen", "Rami", "Akram"],
  place: "Arlington, Virginia (virtual event)",
};

export const AI_USE = {
  title: "Use of AI",
  paragraphs: [
    "Galileo Blink was built with an AI coding assistant: Anthropic's Claude, used through Claude Code. It is the only AI tool the team used. Working under the team's direction, it wrote most of the code (the engine, the web server, the interface and the tests), drafted the documentation and the words on the site, designed the interface, including the two-circle mark, and ran the deployments. It was also used to audit the project before submission.",
    "The team chose the challenge and the idea, set the goals and the limits, decided what the site may and may not claim, and directed and reviewed the work.",
    "No image-generation tool was used. Every sky picture is made from NASA SPHEREx data by the project's own code, and nothing on the site uses or imitates NASA's logos or branding.",
  ],
};

export interface Credit {
  name: string;
  detail: string;
}

export const DATA_SOURCES = {
  title: "Data sources and licences",
  note: "All data shown on this site is public. Galileo Blink reads it live from the services below and does not alter the measurements it is given.",
  items: [
    {
      name: "SPHEREx images",
      detail: "NASA/JPL-Caltech. Served by the NASA/IPAC Infrared Science Archive (IRSA). NASA mission data is free to use with credit. DR1 spectral images (doi:10.26131/IRSA678) and QR3 spectral images (doi:10.26131/IRSA662).",
    },
    {
      name: "SPHEREx all-sky cube",
      detail: "The DR1 spectral all-sky cube (doi:10.26131/IRSA679), all 102 colours at any place, used for the quick spectrum. NASA/JPL-Caltech, served by IRSA.",
    },
    {
      name: "NASA's cloud copy of SPHEREx",
      detail: "IRSA's public copy of the SPHEREx archive on AWS Open Data. Photos and cube tiles are read from it first, with IRSA's own servers as the fallback.",
    },
    {
      name: "Gaia DR3 star catalogue",
      detail: "European Space Agency (ESA), Gaia Data Processing and Analysis Consortium. Served by NASA's MAST archive. Free to use with acknowledgement.",
    },
    {
      name: "CatWISE2020 catalogue",
      detail: "Built from NASA's WISE and NEOWISE surveys. Served by NASA/IPAC IRSA. Free to use with credit.",
    },
    {
      name: "Object names",
      detail: "Names typed in the search box are looked up with the CDS Sesame service (Strasbourg) and NASA's NED.",
    },
    {
      name: "Known asteroids",
      detail: "IMCCE's SkyBoT service (Paris Observatory) says which catalogued asteroids should be in a field at a given moment. NASA/IPAC's Moving Object Search Tool (MOST) finds the SPHEREx photos that caught an asteroid you name.",
    },
  ] satisfies Credit[],
};

export const ACKNOWLEDGEMENTS = {
  title: "Acknowledgements",
  note: "The sentences the data providers ask users to include.",
  items: [
    "This research has made use of the NASA/IPAC Infrared Science Archive, which is funded by the National Aeronautics and Space Administration and operated by the California Institute of Technology.",
    "This publication makes use of data products from the Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of the Jet Propulsion Laboratory and the California Institute of Technology, and is funded by the National Aeronautics and Space Administration.",
    "This work has made use of data from the European Space Agency (ESA) mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC, https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the DPAC has been provided by national institutions, in particular the institutions participating in the Gaia Multilateral Agreement.",
    "This publication makes use of data products from the Wide-field Infrared Survey Explorer, which is a joint project of the University of California, Los Angeles, and the Jet Propulsion Laboratory/California Institute of Technology, funded by the National Aeronautics and Space Administration. This publication also makes use of data products from NEOWISE, which is a project of the Jet Propulsion Laboratory/California Institute of Technology, funded by the Planetary Science Division of the National Aeronautics and Space Administration. The CatWISE2020 catalogue built from them is described by Marocco et al. 2021.",
    "This research has made use of IMCCE's SkyBoT VO tool (Berthier et al. 2006, ASP Conf. Ser. 351, 367).",
    "This research has made use of the NASA/IPAC Extragalactic Database (NED), which is funded by the National Aeronautics and Space Administration and operated by the California Institute of Technology.",
    "This research has made use of the SIMBAD database, operated at CDS, Strasbourg, France (Wenger et al. 2000).",
    "This research made use of Astropy, a community-developed core Python package and an ecosystem of tools and resources for astronomy (Astropy Collaboration 2013, 2018, 2022).",
  ],
};

export const LIBRARIES = {
  title: "Open-source software",
  note: "Galileo Blink is itself open source under the Apache-2.0 licence, and is built on these projects.",
  engine: {
    title: "The engine (Python)",
    items: ["Astropy", "astropy-healpix", "NumPy", "SciPy", "reproject", "Pillow", "Requests", "FastAPI", "Uvicorn"],
  },
  site: {
    title: "This site",
    items: ["React", "TypeScript", "Vite", "lucide"],
  },
  fonts: {
    title: "Typefaces (SIL Open Font License)",
    items: ["Hanken Grotesk"],
  },
  full: {
    body: "Every library, dataset, font and service, with its licence, is listed in the repository.",
    link: "Full list of references and licences",
    href: "https://github.com/aymenawel/galileo-blink_spherex/blob/main/docs/REFERENCES.md",
  },
};

export const SOURCE = {
  title: "Source code",
  body: "Everything is on GitHub: the engine that reads NASA's archive, this site, and the tests.",
  link: "Open the repository",
};
