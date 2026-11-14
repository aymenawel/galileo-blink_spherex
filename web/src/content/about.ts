/** The text of the "About" page: the challenge, the team, and everyone whose work this stands on. */

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
  place: "Arlington, Virginia — virtual event",
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
      detail: "NASA/JPL-Caltech. Served by the NASA/IPAC Infrared Science Archive (IRSA). NASA mission data is free to use with credit.",
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
  ] satisfies Credit[],
};

export const LIBRARIES = {
  title: "Open-source software",
  note: "Galileo Blink is itself open source under the Apache-2.0 licence, and is built on these projects.",
  engine: {
    title: "The engine (Python)",
    items: ["Astropy", "NumPy", "SciPy", "reproject", "Pillow", "Requests", "FastAPI", "Uvicorn"],
  },
  site: {
    title: "This site",
    items: ["React", "Vite", "lucide"],
  },
  fonts: {
    title: "Typefaces (SIL Open Font License)",
    items: ["Instrument Serif", "Instrument Sans", "DM Mono"],
  },
};

export const SOURCE = {
  title: "Source code",
  body: "Everything is on GitHub: the engine that reads NASA's archive, this site, and the tests.",
  link: "Open the repository",
};
