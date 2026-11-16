/**
 * The text of the "How it works" page: a short version in six steps, then every step in detail,
 * the words used, and the limits. Plain language first; the limits are stated, not hidden.
 */

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

/** The short version: six steps anyone can follow, and the labels around them. */
export const SHORT_VERSION = {
  eyebrow: "How it works",
  lede: "Six steps take a place in the sky from NASA's archive to a picture that blinks. The short version comes first. The details follow, for anyone who wants them.",
  shortTitle: "The short version",
  steps: [
    {
      title: "A telescope photographs the whole sky",
      body: [
        "SPHEREx is a NASA space telescope launched in March 2025. About every six months it photographs the whole sky in infrared light, from 0.75 to 5 microns.",
        "It has six cameras that together see 102 colours. Every photo is public, kept at NASA's IRSA archive.",
      ],
    },
    {
      title: "You pick a place",
      body: [
        "Type the name of a star, or a position in the sky. Each SPHEREx photo is a 65 MB file; the tool reads only the small piece that covers your place.",
        "One pixel is 6.15 arcseconds, about 1/300 of the full Moon. A new place is built in under a minute.",
      ],
    },
    {
      title: "The photos are turned north-up and stacked",
      body: [
        "Photos arrive rotated, because the telescope rolls as it orbits. Each one is turned north-up onto the same grid.",
        "Then the photos from one camera and one date are stacked into a single, clearer picture.",
      ],
    },
    {
      title: "Blink",
      body: [
        "The pictures from each date are shown one after another, in the same spot.",
        "Stars stay put. Anything that moved jumps.",
      ],
    },
    {
      title: "Check it against a catalogue",
      body: [
        "A ring marks where a star catalogue says a moving object should be on that date: Gaia, a European star-mapping space telescope, or CatWISE.",
        "The tool measures the motion in the photos itself, then compares. For Barnard's Star, in one year:",
      ],
    },
    {
      title: "Subtract two dates",
      body: [
        "Change subtracts one date from another, so everything that stayed put disappears. What is left is what changed.",
        "The tool also measures whether an object's brightness changed, camera by camera.",
      ],
    },
  ],
  measured: "10.3",
  measuredUnit: "arcseconds",
  measuredError: "give or take 0.5",
  predicted: "Catalogue predicted 10.3",
  greenNow: "Where it is now",
  pinkThen: "Where it was",
  coda: "The same idea finds asteroids inside a single visit: the sky that stays put is subtracted, and the leftover dots are joined into a straight path. The tool does not announce discoveries. It lets people look.",
  skyAlt: "The whole sky as SPHEREx sees it in infrared, an oval with the Milky Way as a bright band across the middle.",
  skyCaption: "The whole sky, with the Milky Way across the middle",
  placeCaption: "Barnard's Star, and the small piece of sky the tool reads",
  stackCaption: (camera: string, date: string, photos: number) => `Camera ${camera}, ${date}: ${photos} photos stacked`,
  stackDrawing: "Drawing: three photos, each tilted a different way, turn north-up and settle into one picture.",
  blinkCaption: "Barnard's Star, every date in turn",
  ringCaption: "The ring: where the catalogue says it should be",
  changeCaption: (camera: string, a: string, b: string) => `Camera ${camera}, ${a} minus ${b}`,
  moreTitle: "For the curious",
  moreLede: "Every step in detail, with the numbers. Open any row; nothing here is needed to use the tool.",
  moreJump: "Jump to",
  moreWords: "The words",
  moreLimits: "The limits",
  tryLine: "Pick a place and watch it blink.",
  tryButton: "Try it on Barnard's Star",
};

/** One phrase per technical topic, shown while its row is closed. */
export const TOPIC_SUMMARY: Record<string, string> = {
  spherex: "The telescope, and where its photos live",
  seasons: "One visit about every six months, shared by six cameras",
  "north-up": "Every photo redrawn onto one grid",
  stacking: "The middle value of each pixel, gaps left blank",
  cameras: "Six slices of infrared, and their wavelengths",
  markers: "Rings from Gaia and CatWISE, and predicted paths",
  measuring: "Reference stars, error bars and parallax",
  asteroids: "Subtract the still sky, join the dots",
  spectra: "Dots from the photos, and NASA's all-sky map",
  flags: "NASA's marks on suspect pixels, the full list",
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
    id: "words",
    title: "Words used on this site",
    paragraphs: ["Fifteen terms appear across Galileo Blink. Each one in a sentence:"],
    definitions: [
      {
        term: "Arcsecond (″)",
        meaning: "1/3600 of a degree. The full Moon is about 1,800 arcseconds across. An arcminute (′) is 60 arcseconds.",
      },
      {
        term: "Proper motion",
        meaning:
          "The steady drift of a star across the sky, year after year, because it and the Sun move through the galaxy at different speeds. Measured in arcseconds per year.",
      },
      {
        term: "Parallax",
        meaning:
          "A small yearly loop a nearby star appears to trace, because Earth (and SPHEREx with it) circles the Sun. The closer the star, the bigger the loop. Comparing dates a year apart cancels it.",
      },
      {
        term: "Give or take (±)",
        meaning: "The measurement's error bar: the true value very likely lies within that distance of the number shown.",
      },
      {
        term: "Catalogue",
        meaning:
          "A published list of stars with their positions and motions. Two are used here: Gaia, from a European space telescope, and CatWISE, from NASA's WISE telescope.",
      },
      {
        term: "Infrared",
        meaning: "Light redder than the eye can see. Cool things, from brown dwarfs to dust, glow mostly in infrared.",
      },
      {
        term: "Micron (µm)",
        meaning: "A thousandth of a millimetre. Used here for the wavelength, or colour, of infrared light.",
      },
      {
        term: "Camera",
        meaning: "SPHEREx has six, each seeing its own slice of infrared, from camera 1 (shortest wavelengths) to camera 6 (longest).",
      },
      {
        term: "Date, or season",
        meaning: "One SPHEREx visit to a place: a few days of photos, usually about six months after the last visit.",
      },
      {
        term: "Spectrum",
        meaning: "How bright an object is at each colour. Its shape tells how hot the object is and what it is made of.",
      },
      {
        term: "Millijansky (mJy)",
        meaning: "A unit for how much light reaches us at one colour. Bigger is brighter.",
      },
      {
        term: "Magnitude",
        meaning: "An older brightness scale that runs backwards: bigger numbers are fainter. The eye alone sees down to about 6.",
      },
      {
        term: "Saturated",
        meaning: "Too bright for the camera: the pixels overflow and cannot be measured.",
      },
      {
        term: "Quality flag",
        meaning: "NASA's mark on a pixel it knows is suspect, such as a cosmic-ray hit, a dead pixel or a satellite trail.",
      },
      {
        term: "Brown dwarf",
        meaning: "An object bigger than a planet but too small to shine like a star. It glows faintly in infrared as it cools.",
      },
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
      "Over many photos an object is seen in up to 102 colours. That is why the brightness dots on the Explore page draw a spectrum. It is also why the coldest brown dwarfs, such as WISE 0855, which glow only beyond about 3.8 microns, show up in cameras 5 and 6 and are invisible in cameras 1 to 4.",
    ],
  },
  {
    id: "markers",
    title: "Markers and predictions",
    paragraphs: [
      "The reticles on a picture mark catalogued objects that are known to move: stars from ESA's Gaia catalogue that cross at least half an arcsecond of sky a year, and cold objects from the CatWISE catalogue that cross at least 2 arcseconds a year. For each one the tool computes where it should be on every date, and draws a faint line through those positions.",
      "The predicted path in the motion plot is two things added together: a steady drift, and a small yearly loop.",
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
    id: "asteroids",
    title: "Finding asteroids within one visit",
    paragraphs: [
      "Stars take months to shift. An asteroid crosses the picture in hours. So the asteroid search works inside a single visit: one camera, a few days, each short burst of photos kept apart as one moment.",
      "For every pixel, the middle value across the moments is taken. That is the sky that stays put: stars and galaxies. It is subtracted from each moment, which leaves only what was different then. An asteroid is left as a dot in a different place each time; a faint asteroid passing in front of a star, invisible as a slightly brighter star, becomes obvious once the star is gone.",
      "Leftover dots are joined when they fall on one straight path at a steady speed, in at least three moments. A path seen in four or more moments, in most of those where it could have been seen, is marked as found. The asteroid catalogue (IMCCE's SkyBoT) is then asked what should be in the field, and a path that lies on a catalogued asteroid's predicted positions gets its name. NASA's moving-object search tells the tool where SPHEREx caught any asteroid you name.",
    ],
  },
  {
    id: "spectra",
    title: "Where the spectra come from",
    paragraphs: [
      "The dots in the brightness plot are measured in the view's own photos: one dot per photo, at the colour that photo happened to catch the object in. Because every dot has a date, dots from different seasons at the same colour show whether the object changed.",
      "The quick spectrum comes from somewhere else: NASA's map of the whole sky in all 102 colours. The tool reads the few pixels around your place in every colour, in about two seconds. That map adds every date together and its pixels are twice as coarse, so it shows the shape of a spectrum but cannot show change.",
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
      body: "SPHEREx pixels are 6.15″ across. Motion smaller than about 1″ between looks (2″ to 3″ in one camera, or for faint or saturated objects) cannot be told apart from no motion, and two objects closer together than a pixel blend into one.",
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
      title: "Its error bars include what averaging cannot remove",
      body: "Stars that do not move still appear to shift 0.2″ to 0.4″ between looks, and the six cameras share the same pointing errors. For stars with well-known motions the all-camera result differed from the catalogue by 0.3″ to 0.7″ (1.3″ for R Draconis, which is saturated in every photo), so 0.3″ is added to every motion's error. That allowance was set using these same stars, so their results show consistency, not an independent test of the error bars.",
    },
    {
      title: "It cannot find every asteroid",
      body: "An asteroid in view for fewer than three moments cannot be found, however bright. Single SPHEREx photos are not deep, so asteroids fainter than about magnitude 18.5 are not expected to be found. Three faint leftovers can line up by chance (cosmic-ray hits do), so such paths are only ever marked \"possible\".",
    },
    {
      title: "CatWISE's fast movers are mostly false alarms",
      body: "They are hidden until you switch them on, and those within 4 arcminutes of a bright star are never marked. A real faint mover that close to a bright star would be missed.",
    },
    {
      title: "A marker is not proof",
      body: "A reticle shows where a catalogue says an object should be. It does not prove that the dot beneath it is that object, and catalogues have gaps and mistakes.",
    },
    {
      title: "It cannot find a distant planet by itself",
      body: "A planet far beyond Neptune would be too faint for a single SPHEREx photo. It would also not creep across a small view: because Earth circles the Sun, it would appear to jump 10 to 25 arcminutes between two looks six months apart, outside the default 9-arcminute view. This tool has not found such a planet and cannot find one alone. It lets people look, carefully.",
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
