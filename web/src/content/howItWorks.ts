/** The text of the "How it works" page. Plain language first; the limits are stated, not hidden. */

export interface Definition {
  term: string;
  meaning: string;
}

export interface Section {
  /** Used in the address, as in /how-it-works#limits. */
  id: string;
  title: string;
  paragraphs: string[];
  definitions?: Definition[];
}

export const HOW_IT_WORKS_INTRO = {
  eyebrow: "How it works",
  title: { before: "From NASA's archive to a picture that ", emphasis: "blinks", after: "." },
  lede: "Nothing here is hidden behind a button. This page explains every step between typing a place and seeing it move, and it ends with what the tool cannot do.",
};

export const SECTIONS: Section[] = [
  {
    id: "spherex",
    title: "What SPHEREx is",
    paragraphs: [
      "SPHEREx is a NASA space telescope launched in March 2025. It photographs the entire sky about every six months in infrared light: colours redder than the eye can see, from 0.75 to 5 microns. It is not built for sharp close-ups. It is built to see everything, again and again, in many colours.",
      "Every photo it takes is public. NASA's infrared archive (IRSA, at Caltech's IPAC) holds them, and Galileo Blink reads them from there each time you open a place. A single photo is a 65 MB file; the tool reads only the small piece that covers your place.",
    ],
  },
  {
    id: "seasons",
    title: "Looks and seasons",
    paragraphs: [
      "SPHEREx sweeps past most places about every six months and takes a handful of photos within a few days. We call one such visit a look.",
      "The six cameras do not pass over a place on exactly the same days. So the screen steps through seasons: one step per visit, shared by all six cameras. When a camera took nothing in a season, its tile says \"No photos this season\" instead of quietly showing an older picture.",
      "Near the poles of SPHEREx's survey pattern the telescope passes far more often, so places there have many more seasons.",
    ],
  },
  {
    id: "north-up",
    title: "Why every photo is turned north-up",
    paragraphs: [
      "The telescope rolls as it orbits. The same patch of sky arrives rotated differently in every photo, and each camera sees it on a different part of its detector.",
      "Before anything can be compared, every photo is redrawn onto one grid: north up, east to the left, the same scale everywhere. Only then does a star stay in the same place from one date to the next, and only then does something that moved stand out.",
    ],
  },
  {
    id: "stacking",
    title: "Why photos are stacked",
    paragraphs: [
      "A single SPHEREx photo is noisy, and parts of it are damaged by cosmic rays or dead pixels. First each photo's own background glow (sunlight scattered by dust in the solar system) is removed. Then the photos of one look are combined pixel by pixel, keeping the middle value. Real objects appear in every photo and survive; a blemish that appears in only one photo is ignored.",
      "Pixels NASA marks as unusable are left out. Where no photo has good data, the picture shows a hatch pattern. The tool never invents a value to fill a gap.",
    ],
  },
  {
    id: "cameras",
    title: "Six cameras, 102 colours",
    paragraphs: [
      "SPHEREx has six cameras, each sensitive to its own slice of the infrared. In front of each sits a filter whose colour changes smoothly from one edge to the other. So a photo is not one colour: where an object lands on the detector decides which colour it is seen in.",
      "Over many photos an object is seen in up to 102 colours. That is why the brightness dots on the Explore page draw a spectrum. It is also why cold objects such as brown dwarfs, which glow only at long wavelengths, show up in cameras 5 and 6 and are invisible in camera 1.",
    ],
  },
  {
    id: "markers",
    title: "Markers and predictions",
    paragraphs: [
      "The reticles on a picture mark catalogued objects that are known to move: stars from ESA's Gaia catalogue and cold objects from the CatWISE catalogue that cross at least half an arcsecond of sky a year. For each one the tool computes where it should be on every date, and draws a faint line through those positions.",
      "The predicted path in the motion plot is two things added together: a steady drift, and a small yearly loop.",
    ],
    definitions: [
      {
        term: "Arcsecond (″)",
        meaning: "1/3600 of a degree. The full Moon is about 1,800 arcseconds across.",
      },
      {
        term: "Proper motion",
        meaning:
          "The steady drift of a star across the sky, year after year, because it and the Sun move through the galaxy at different speeds. Measured in arcseconds per year.",
      },
      {
        term: "Parallax",
        meaning:
          "A small yearly loop a nearby star appears to trace, because Earth (and SPHEREx with it) circles the Sun. The closer the star, the bigger the loop.",
      },
    ],
  },
  {
    id: "measuring",
    title: "How motion is measured",
    paragraphs: [
      "In each photo the tool finds the centre of the object's light. A photo's stated pointing can be off by a fraction of a pixel, so the same is done for ordinary stars in the field that Gaia says barely move. Each photo is then nudged until those reference stars land where they should. Only after that is the object's position compared between looks.",
      "Error bars are measured, not assumed. The whole procedure is also run on the reference stars, which should not move at all. However far they appear to shift is the floor of that view: a motion smaller than the floor means nothing, and the page says so.",
      "When two looks are about a year apart, the parallax loop is at the same point in both and cancels out. The tool prefers such pairs.",
    ],
  },
  {
    id: "flags",
    title: "NASA's quality flags",
    paragraphs: [
      "NASA marks every pixel it knows to be suspect, and says why. Some flags mean a pixel holds no usable light; those pixels are left blank and appear hatched. The other flags are kept in the picture, because they often sit on real bright stars, but you can overlay them at any time to check whether a surprising dot is only a blemish.",
    ],
  },
];

export const LIMITS = {
  id: "limits",
  title: "What this tool cannot do",
  lede: "A measurement is only worth as much as its limits are understood. These are ours.",
  items: [
    {
      title: "It cannot see small motions",
      body: "SPHEREx pixels are 6.15″ across. Anything that moves less than about 0.5″ between looks cannot be seen to move, and two objects closer together than a pixel blend into one.",
    },
    {
      title: "It cannot measure very bright stars",
      body: "Bright stars saturate: their light overflows the detector. Their brightness cannot be measured at all, and their position is less certain.",
    },
    {
      title: "Brightness changes need care",
      body: "Each photo is taken at a different wavelength. A star can look brighter on one date only because that photo caught it in a brighter colour. Compare dots at the same wavelength, never two pictures. Change maps leave faint rings on stars for the same reason.",
    },
    {
      title: "A marker is not proof",
      body: "A reticle shows where a catalogue says an object should be. It does not prove that the dot beneath it is that object, and catalogues have gaps and mistakes.",
    },
    {
      title: "It cannot find a distant planet by itself",
      body: "A planet far beyond Neptune would be too faint for a single SPHEREx photo. It would also not creep across a small view: because Earth circles the Sun, it would appear to jump 10 to 25 arcminutes between two looks six months apart, far outside the frame. This tool has not found such a planet and cannot find one alone. It lets people look, carefully.",
    },
  ],
};

export const FLAGS_TABLE = {
  flag: "Flag",
  meaning: "What it means",
  treatment: "In the picture",
  blank: "Left blank (hatched)",
  kept: "Kept; shown in the overlay",
  loading: "Loading NASA's list of flags.",
  failed: "The list of flags could not be loaded right now.",
};

export const CAMERA_TABLE = {
  camera: "Camera",
  band: "Wavelengths",
  caption: "The six cameras, from the shortest wavelength to the longest.",
};
