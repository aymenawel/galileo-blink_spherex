/**
 * The words on the screen.
 *
 * Short labels live in `COPY`; sentences that depend on numbers are the functions below it.
 * The long explanations of the "How it works" and "About" pages are in `src/content`.
 *
 * House rules: plain language first, every number says what it means, and when something
 * cannot be measured the text says so and why.
 */
import type { ErrorKind, Motion, Subject, SubjectKind, View } from "../api/types";
import { arcsec, arcsecNumber, formatCount, microns, plural, roundSignificant } from "./format";

export const REPOSITORY_URL = "https://github.com/aymenawel/galileo-blink_spherex";

/** Below this predicted motion (arcseconds) an object counts as standing still for SPHEREx. */
export const STATIC_BELOW_ARCSEC = 0.3;

/** Below this catalogue speed (arcseconds per year) a target is described as not moving. */
const STATIC_BELOW_ARCSEC_PER_YEAR = 0.3;

export const COPY = {
  brand: {
    name: "Galileo Blink",
    tagline: "Watch the infrared sky move",
  },

  nav: {
    label: "Main",
    explore: "Explore",
    targets: "Targets",
    asteroids: "Asteroids",
    how: "How it works",
    menu: "Menu",
    about: "About",
    skip: "Skip to content",
  },

  search: {
    label: "A place in the sky: a name or coordinates",
    placeholder: 'Try "Barnard\'s Star" or 17h57m48s +04d41m36s',
    submit: "Look",
    busy: "Finding that place",
    busySlow: "Still asking the star catalogues. This can take ten seconds.",
    empty: "Type a star's name or a pair of coordinates first.",
    timeScale: "Time between pictures",
    looks: "Every six months",
    visit: "Within one visit",
    looksHint: "For stars: one picture from each SPHEREx visit, months apart.",
    visitHint: "For asteroids: the pictures of one visit, hours apart, searched for anything moving.",
    field: "Field of view",
    camera: "Camera",
    cameraAuto: "Best camera for this place",
    cameraOption: (key: string, band: string) => `Camera ${key} · ${band}`,
  },

  errors: {
    unexpected: "Something unexpected happened. Please try again.",
    network: "Your browser could not reach Galileo Blink. Check your connection and try again.",
    side: {
      request: "Something about the place you asked for cannot be shown. Check the coordinates, or try another place.",
      service: "NASA's archive is busy. This is not about what you typed: try again in a minute.",
      busy: "Galileo Blink is very busy right now. Try again in a moment.",
      internal: "This one is on Galileo Blink, not on you and not on NASA. Trying again may work.",
      network: "Check your internet connection, then try again.",
    } satisfies Record<ErrorKind, string>,
    retry: "Try again",
    notFoundTitle: "There is nothing at this address",
    notFoundBody: "The page you asked for does not exist. The sky is still there, though.",
    goHome: "Back to the start",
  },

  home: {
    headline: "Watch the infrared sky move.",
    lede: "NASA's SPHEREx telescope photographs the whole sky every six months. Type any place and flip through the dates: whatever moved, shows.",
    previewCaption: "Barnard's Star, the fastest-moving star in the sky",
    previewOpen: "Open this view",
    previewsPause: "Pause the pictures",
    previewsPlay: "Play the pictures",
    skyTitle: "The whole sky",
    skyLede:
      "Every direction SPHEREx has looked, in infrared light. The bright band is our own galaxy, the Milky Way, seen from inside. Click anywhere to open that place.",
    skyAlt:
      "The whole sky in infrared as an oval map: the Milky Way is a bright band across the middle, with its glowing centre in the middle of the oval.",
    sky: {
      label: "Map of the whole sky",
      hint: "Point at the sky to read its position. Click to open that place.",
      readout: (ra: string, dec: string) => `${ra}   ${dec}`,
      target: (name: string) => `${name}: open its blink`,
    },
    skyCredit: "SPHEREx all-sky map, 4.4 to 5.0 microns: NASA/JPL-Caltech, NASA/IPAC Infrared Science Archive.",
    targetsTitle: "NASA's five test targets",
    targetsLede: "The challenge names five objects to try a tool like this on. Each one is ready to open.",
    targetsFailed: "The list of test targets could not be loaded right now. You can still search for any place above.",
    stepsTitle: "How it works, in three steps",
    steps: [
      {
        title: "Type a place",
        body: "A star's name or a pair of coordinates. Galileo Blink asks NASA's archive for every SPHEREx photo that covers it.",
      },
      {
        title: "The photos are lined up",
        body: "The telescope rolls between visits, so raw photos arrive rotated. Each one is turned north-up and stacked with the others taken in the same season.",
      },
      {
        title: "Blink through the dates",
        body: "Step from season to season. Stars stay put. Anything that moved, brightened or faded jumps out, and the tool measures how far it moved.",
      },
    ],
    stepsMore: "Read the full explanation",
    notTitle: "What this is not",
    notBody:
      "Galileo Blink does not announce discoveries, and it has not found a ninth planet. It lines up NASA's public photos so that anyone can look carefully, and it says plainly what it can and cannot measure.",
    notLink: "Read the limits",
  },

  footer: {
    dataTitle: "Data",
    data: [
      "SPHEREx images: NASA/JPL-Caltech, served by NASA/IPAC IRSA",
      "Gaia DR3 star catalogue: ESA, served by NASA MAST",
      "CatWISE2020 catalogue: served by NASA/IPAC IRSA",
    ],
    licence: "Apache-2.0",
    repository: "Source code",
    team: "Team Galileo — NASA Space Apps Challenge 2026",
    disclaimer: "An independent student project. Not an official NASA product.",
  },

  explore: {
    title: "Explore",
    emptyTitle: "Pick a place to watch",
    emptyBody: "Search for any star or any coordinates above, or start with one of NASA's five test targets.",
    fieldLabel: "Field of view",
    share: "Copy link",
    shareDone: "Link copied",
    detailsTitle: "The details",
    detailsLede: "Every number behind the picture, how it was measured, and what this view cannot tell you.",
    detailsLink: "See the numbers behind this",
    wordsLink: "What the words mean",
    cameraLabel: "Camera",
    showLabel: "Show on the picture",
    viewLabel: "This view",
    shareFailed: "Copy the address from the address bar to share this view",
    opening: "Opening this view",
  },

  firstLook: {
    label: "A guided first look",
    start: "Show me what to look for",
    count: (step: number, of: number) => `Step ${step} of ${of}`,
    back: "Previous step",
    next: "Next",
    done: "Done",
    close: "Close the guide",
  },

  viewport: {
    modesLabel: "What the picture shows",
    modes: {
      blink: { label: "Blink", hint: "Step through the dates. Things that moved jump." },
      compare: { label: "Compare", hint: "Two dates side by side. Drag the divider." },
      change: { label: "Change", hint: "One date minus another. Only what changed is left." },
      combined: { label: "Combined", hint: "Every photo added together: faintest things show best." },
    },
    previous: "Previous season",
    next: "Next season",
    play: "Play",
    pause: "Pause",
    speed: "Blink speed",
    speeds: { slow: "Slow", normal: "Normal", fast: "Fast" },
    overlays: "Overlays",
    markers: "Markers",
    stars: "Gaia stars",
    saveGif: "Save GIF",
    saveGifHint: "Download this camera's blink as an animated picture you can share.",
    catwise: "CatWISE",
    catwiseHint:
      "Objects the CatWISE catalogue lists as moving fast. Many are false alarms near bright stars, so they are hidden until you ask.",
    flags: "Flags",
    flagsOnlyInBlink: "Flags are shown for one date at a time. Switch to Blink to see them.",
    noLook: "No photos this season",
    noLookFrom: (camera: string) => `Camera ${camera} took no photos here this season`,
    noCamera: "This camera has no usable photos of this place",
    noData: "Hatched areas have no data",
    north: "N",
    east: "E",
    compassLabel: "North is up, east is to the left",
    seasonA: "Date A",
    seasonB: "Date B",
    swap: "Swap date A and date B",
    compareHandle: "Divider between date A (left) and date B (right)",
    compareValue: (percent: number, a: string, b: string) => `${percent}% of the picture shows ${a}, the rest ${b}`,
    changeLoading: "Subtracting the two dates",
    changeFailed: "This change map could not be made. Pick two other dates.",
    changeLegend: {
      label: "Colours of the change map",
      brighter: (date: string) => `Brighter in ${date}`,
      fainter: (date: string) => `Fainter in ${date}`,
      same: "No change",
    },
    changeNote:
      "A star that moved leaves green where it is now and pink where it was. Still stars leave faint traces, because each photo is taken at a slightly different wavelength.",
    blinkNote: "Watch the centre as the dates change. Stars that stay put hold still; anything that moved jumps.",
    compareNote: "The markers on each side show where the catalogue places each object on that date.",
    combinedNote: "A moving object appears once for every date, as a short row of dots.",
    combinedChip: "All dates",
    keyboardHint: "Arrow keys step through the dates. Space plays and pauses.",
    pointerReadout: "Sky position under the pointer",
  },

  timeline: {
    label: "Seasons",
    leftOut: (count: number) =>
      `${plural(count, "earlier or sparser season")} ${count === 1 ? "is" : "are"} not shown, to keep this view quick to build.`,
    noLookTitle: (camera: string) => `Camera ${camera} has no photos this season`,
  },

  cameras: {
    title: "The same date in all six cameras",
    line: "Six cameras, six slices of infrared. The coldest objects appear only in the long-wavelength cameras.",
    hint: "Each camera sees its own slice of infrared light, measured in microns (µm). Higher numbers see colder things.",
    camera: (key: string) => `Camera ${key}`,
    select: (key: string, band: string) => `Show camera ${key}, ${band}`,
  },

  subject: {
    title: "Where and when",
    position: "Position",
    field: "Field of view",
    dataThrough: "SPHEREx data through",
    photosUsed: "Photos used",
    photosInArchive: (count: number) => `of ${formatCount(count)} in NASA's archive`,
    catalogueSpeed: "Catalogue speed",
    perYear: "per year",
    chosen: {
      target: "One of NASA's five test targets.",
      mover: "The fast-moving catalogued star at the centre.",
      star: "The catalogued star at the centre.",
      spot: "No catalogued object sits exactly here — this view watches the spot itself.",
    } satisfies Record<SubjectKind, string>,
    namedSpot: (name: string) =>
      `${name} is not in the star catalogues this tool measures against (very bright stars and galaxies are missing from them), so no motion is measured. You can still blink the pictures and look for changes.`,
    unnamedPlace: "This place in the sky",
    elsewhere: "The same place in other tools",
    elsewhereLinks: {
      spherex: "NASA's SPHEREx all-sky viewer",
      wiseview: "WiseView (NASA's WISE telescope, 2010 to today)",
      simbad: "SIMBAD: what is known about objects here",
      legacy: "Legacy Surveys sky viewer (visible light)",
    },
  },

  motion: {
    eyebrow: "Motion",
    title: "Did it move?",
    moved: "Moved",
    shift: "Measured shift",
    predicted: "Catalogue predicted",
    agrees: "Matches the catalogue",
    still: "Does not move, as expected",
    giveOrTake: (amount: string) => `give or take ${amount}`,
    differs: "Differs from the catalogue",
    agreesWhy: "The measured motion and the predicted motion agree in size and direction, within the measurement error.",
    differsWhy:
      "The difference is larger than the measurement error. A neighbouring star blended into the same pixel, or an out-of-date catalogue entry, can cause this.",
    showNumbers: "Show the numbers",
    numbersLabel: "Table of the motion measured in each camera",
    noneTitle: "No motion could be measured here.",
    plotAlt: (count: number, camera: string) =>
      `Path across the sky, north up and east left: the catalogue's predicted path as a line, and ${plural(count, "measured position")} from camera ${camera} as dots with error bars.`,
    plotEmpty: (camera: string) => `Camera ${camera} has no position measurements for this object. Choose another camera to see its dots.`,
    legendPredicted: "Predicted path",
    legendMeasured: "Measured, with error bar",
    axisEast: "← east · arcseconds · west →",
    axisNorth: "north ↑ (arcseconds)",
    pixelBox: "1 SPHEREx pixel",
    table: {
      camera: "Camera",
      seasons: "Seasons compared",
      measured: "Measured",
      predicted: "Predicted",
      difference: "Difference",
      agrees: "Agrees",
      yes: "Yes",
      no: "No",
      together: "Together",
    },
    help: {
      no_target:
        "Try a place with a fast-moving star, or open one of NASA's test targets. You can still blink the pictures and look for changes by eye.",
      catalogue_down: "The catalogue is usually back within minutes. This view is rebuilt automatically; reload the page later.",
      one_season: "SPHEREx returns to most places about every six months. Come back after its next visit.",
      too_faint:
        "Faint objects need many photos added together. Try the Combined picture, and the long-wavelength cameras for cold objects.",
      off_track:
        "Look at the picture: if another star sits under the marker, the two are blended at SPHEREx's sharpness, and no measurement is better than a wrong one.",
    } as Record<string, string>,
    helpFallback: "You can still blink the pictures and look for changes by eye.",
  },

  spectrum: {
    eyebrow: "Spectrum from the photos",
    title: "Its colours",
    caption:
      "Each dot is one photo. SPHEREx's filter changes across its field, so every photo catches the object at a different infrared colour — together they draw its spectrum. Dots from different seasons at the same colour should overlap; if they clearly don't, beyond their scatter, the object may have changed brightness.",
    axisWavelength: "Wavelength: shorter is bluer, longer shows colder things",
    reading: (camera: number, band: string) =>
      `Read it like this: the dots are highest in camera ${camera} (${band}), so that is where this object gives off most of its light. Hot stars are brightest in cameras 1 and 2, cool stars in cameras 2 to 4, and the coldest or dustiest objects in cameras 5 and 6.`,
    bandName: (camera: string) => `cam ${camera}`,
    wavelengthTick: (microns: number) => `${microns} µm`,
    axisBrightness: (unit: string) => `Brightness (${unit})`,
    plotAlt: (count: number) =>
      `Brightness against wavelength from 0.75 to 5 microns: ${plural(count, "photo")}, one dot each, coloured by season.`,
    logNote: "The brightness axis is stretched (each step is ten times brighter) so faint and bright dots both fit.",
    hollow: "Hollow dot: part of the object fell on damaged pixels, so the value is less certain",
    belowAxis: "Arrow at the bottom: too faint to place on this axis",
    allSaturated: "Every photo of this star is saturated: it is too bright for SPHEREx to measure its brightness.",
    nothing: "There is no single object at the centre of this view to measure the brightness of.",
    noneUsable: "None of the photos gave a usable brightness for this object.",
    quickButton: "Quick spectrum of the whole-sky map here",
    quickLoading: "Asking the whole-sky map",
    quickUnavailable: "The quick whole-sky spectrum is not available right now.",
    quickEmpty: "The whole-sky map has no spectrum at this exact place.",
    quickLegend: "Whole-sky map",
    quickScaled: (unit: string) =>
      `The whole-sky map is in ${unit}, not mJy, so its line is scaled to the level of the dots: compare its shape, not its height.`,
    showNumbers: "Show the numbers",
    numbersLabel: "Table of every brightness measurement",
    table: { date: "Date", camera: "Camera", wavelength: "Wavelength", brightness: "Brightness", note: "Note" },
    statusNote: { ok: "", partial: "Partly on damaged pixels", saturated: "Saturated: too bright" },
  },

  brightness: {
    title: "Did its brightness change?",
    eyebrow: "Each camera compared with itself",
    changed: "Brightness changed",
    steady: "Brightness steady",
    resultLabel: "Brightness",
    showNumbers: "Show the numbers",
    numbersLabel: "Table of the brightness change in each camera",
    method:
      "Every photo catches the object at a slightly different infrared colour, so brightness is only ever compared inside one camera, where the colours are alike. The first date with photos counts as 1; later dates are measured against it.",
    floor: (percent: number, stars: number) =>
      `Stars that do not vary appear to change by about ${percent}% in this view (${plural(stars, "ordinary star")} checked). That is added to every error here.`,
    floorDefault: "Too few ordinary stars were available to check the cameras' steadiness here, so a cautious 10% is added to every error.",
    notProof:
      "A change this tool calls real is larger than three times its error. It is a measurement, not an explanation: this view cannot say why the light changed.",
    none: {
      saturated: "Every photo of this object is saturated: it is too bright for SPHEREx, so a change in its brightness cannot be measured here.",
      too_faint: "This object is too faint in single photos for its brightness to be compared between dates.",
      one_season: "Brightness can be compared only between two or more dates, and this place has photos from one so far.",
      no_subject: "There is no single object at the centre of this view to follow.",
    } as Record<string, string>,
    noneFallback: "The photos here did not give enough clean readings to compare brightness between dates.",
    plotAlt: (cameras: number) =>
      `Brightness on each date compared with the first date, one line for each of ${plural(cameras, "camera")}, with error bars.`,
    axis: "Compared with the first date",
    same: "same",
    legend: (camera: string, band: string) => `Camera ${camera} · ${band}`,
    table: { camera: "Camera", dates: "Dates compared", change: "Change", verdict: "Real change?", yes: "Yes", no: "Within error" },
  },

  flags: {
    eyebrow: "Quality flags",
    title: "NASA's quality flags on this date",
    line: "Blemishes like cosmic rays and satellite trails can look like new objects. NASA marks them; we show them.",
    show: "Show flagged pixels on the picture",
    hide: "Hide flagged pixels",
    none: "No pixels are flagged on this date.",
    noLook: "This camera took no photos this season, so there are no flags to list.",
    notInThisMode: "Flags belong to one date. Switch to Blink to see them for the date on screen.",
    pixels: "pixels",
    noData: "left blank",
    noDataTitle: "Pixels with this flag are treated as having no data",
    unknown: "A flag this version of the site has no description for",
    more: (count: number) => `${count} more ${count === 1 ? "flag" : "flags"}`,
  },

  honesty: {
    eyebrow: "Limits",
    title: "What this view can't tell you",
    pixel: (pixelArcsec: number) =>
      `SPHEREx pixels are ${pixelArcsec}″ wide. Two stars closer together than that look like one, and a motion smaller than about 1 arcsecond between looks cannot be told apart from no motion.`,
    floor: (floor: number) =>
      `Stars that don't move appear to shift about ${arcsec(floor)} in this view, and each measurement has its own error (the "give or take" number). A shift counts only when it is larger than both.`,
    wavelength:
      "Each photo is a different wavelength. A star can look brighter on one date only because that photo caught it in a brighter colour.",
    seasons: (count: number) =>
      `${plural(count, "season")} of photos ${count === 1 ? "was" : "were"} left out to keep the view quick to build.`,
    catwise:
      "CatWISE's fast movers are hidden by default: most are false alarms. Its entries within 4 arcminutes of a bright star are never marked, so a real faint mover there would be missed.",
    markersLeftOut: (count: number) =>
      `${plural(count, "more catalogued moving object")} in this field ${count === 1 ? "is" : "are"} not marked, to keep the picture readable.`,
    noDiscovery: "A new dot is not a discovery. Check the flags first: most surprises are blemishes.",
    more: "How the measurements are made",
  },

  build: {
    title: "Building this view",
    queued: "Waiting for a free builder",
    elapsed: "Elapsed",
    progress: "Progress",
    typical: "A new place usually takes under a minute. Asking NASA's archive which photos exist is the slowest part.",
    failedTitle: "This view could not be built",
    facts: [
      "SPHEREx photos arrive rotated; each one is turned north-up.",
      "Each SPHEREx photo is 65 MB. Only the small piece that covers your place is read.",
      "SPHEREx comes back to most places about every six months.",
      "One SPHEREx pixel is 6.15 arcseconds wide: about 1/300 of the full Moon.",
      "Stars that don't move are used to check how well each photo is lined up.",
      "Pixels that NASA marks as damaged are left blank, never guessed.",
      "Every photo sees the sky through a filter whose colour changes from one edge to the other.",
    ],
  },
} as const;

// ---------------------------------------------------------------------------- sizes people can picture

const ARCSEC_IN_RADIANS = Math.PI / 648_000;
/** A typical coin is about 24 mm across. */
const COIN_METRES = 0.024;
/** The full Moon is about 31 arcminutes across. */
const MOON_ARCSEC = 1865;

/**
 * An everyday comparison for a small angle on the sky, for example
 * "about the width of a coin seen from 500 metres" for 10 arcseconds.
 */
export function analogy(arcseconds: number): string {
  if (!(arcseconds > 0)) return "";
  if (arcseconds >= MOON_ARCSEC) {
    return `about ${roundSignificant(arcseconds / MOON_ARCSEC, 2)} times the width of the full Moon`;
  }
  if (arcseconds >= 90) {
    return `about 1/${Math.round(MOON_ARCSEC / arcseconds)} of the width of the full Moon`;
  }
  const metres = COIN_METRES / (arcseconds * ARCSEC_IN_RADIANS);
  if (metres >= 1000) {
    return `about the width of a coin seen from ${roundSignificant(metres / 1000, 2)} kilometres`;
  }
  return `about the width of a coin seen from ${formatCount(roundSignificant(metres, 2))} metres`;
}

// ---------------------------------------------------------------------------- naming things

/** A name fit for a sentence. Catalogue numbers are not names anyone says aloud. */
export function subjectName(view: Pick<View, "target" | "subject" | "label">): string {
  if (view.target?.name) return view.target.name;
  const name = view.subject?.name ?? "";
  const isCatalogueNumber = /^(Gaia|CatWISE|AllWISE|2MASS|WISE[AJ ])/i.test(name) && /\d{6,}/.test(name);
  if (view.subject?.kind === "spot" || !name) return view.label ?? "this spot";
  return isCatalogueNumber ? (view.label ?? "this star") : name;
}

/** Whose prediction a measurement is compared with. */
export function catalogueName(subject: Subject | null | undefined): string {
  if (subject?.predicted_by === "Gaia DR3") return "Gaia's catalogue";
  if (subject?.predicted_by === "CatWISE2020") return "The CatWISE catalogue";
  const source = `${subject?.catalog ?? ""} ${subject?.source ?? ""}`;
  if (/gaia/i.test(source)) return "Gaia's catalogue";
  if (/catwise/i.test(source)) return "The CatWISE catalogue";
  return "Published measurements";
}

/** The chip on a target card: how fast it crosses the sky, or that it does not. */
export function speedChip(arcsecPerYear: number): string {
  return arcsecPerYear >= STATIC_BELOW_ARCSEC_PER_YEAR
    ? `${arcsec(arcsecPerYear)} per year`
    : "doesn't move — changes brightness";
}

/** The label of a marker: "moves 10.4″ per year". */
export function markerSpeed(arcsecPerYear: number | null | undefined): string {
  if (arcsecPerYear === null || arcsecPerYear === undefined) return "catalogued as moving";
  return arcsecPerYear >= 0.05 ? `moves ${arcsec(arcsecPerYear)} per year` : "barely moves";
}

/** The readout on the picture: "camera 6 · 4.4–5.0 µm · 6 photos stacked". */
export function lookSummary(camera: string, band: readonly [number, number], photos: number | null): string {
  const base = `camera ${camera} · ${microns(band)}`;
  return photos === null ? base : `${base} · ${plural(photos, "photo")} stacked`;
}

// ---------------------------------------------------------------------------- motion in words

export interface MotionWords {
  name: string;
  firstSeason: string | null;
  lastSeason: string | null;
  motion: Motion;
  subject: Subject | null | undefined;
  /** How far stars that do not move appear to shift in this view, in arcseconds. */
  floor?: number;
}

/** True when the catalogue expects no motion SPHEREx could see. */
export function isStatic(motion: Motion): boolean {
  return motion.predicted < STATIC_BELOW_ARCSEC;
}

function between(first: string | null, last: string | null): string {
  return first && last ? `Between ${first} and ${last}, ` : "";
}

/** The plain-language account of a motion measurement. */
export function motionSentence({ name, firstSeason, lastSeason, motion, subject, floor }: MotionWords): string {
  const measured = `${arcsec(motion.measured)}, give or take ${arcsec(motion.error)},`;
  if (isStatic(motion)) {
    if (!motion.agrees) {
      return `This star is not expected to move measurably, yet the photos show a shift of ${measured} more than the measurement error explains. A bright or blended star can pull a measurement this much; treat it with caution.`;
    }
    return floor !== undefined && motion.measured <= floor
      ? `This star is not expected to move measurably, and it didn't: ${measured} is within what stars that don't move show here.`
      : `This star is not expected to move measurably. The photos show a shift of ${measured} small enough to be measurement error: no real motion is seen.`;
  }
  const lead = between(firstSeason, lastSeason);
  const moved = `${name} moved ${arcsecNumber(motion.measured)} arcseconds across the sky — ${analogy(motion.measured)}.`;
  const sentence = lead ? `${lead}${moved}` : moved.charAt(0).toUpperCase() + moved.slice(1);
  return `${sentence} ${catalogueName(subject)} predicted ${arcsecNumber(motion.predicted)}.`;
}

/** How the measurement was made: how many cameras, over how long. */
export function motionMethod(motion: Motion): string {
  const cameras =
    motion.n_cameras && motion.n_cameras > 1
      ? `${plural(motion.n_cameras, "camera")} measured together`
      : motion.camera
        ? `Measured in camera ${motion.camera}`
        : "Measured in one camera";
  const years = motion.years ? ` over ${motion.years.toFixed(2)} years` : "";
  return `${cameras}${years}.`;
}

/** Why the yearly wobble does or does not matter for this measurement. */
export function parallaxNote(sameTimeOfYear: boolean | undefined): string {
  return sameTimeOfYear
    ? "The two looks were taken at the same time of year, so the yearly wobble (parallax) cancels."
    : "The two looks were taken at different times of year, so the yearly wobble (parallax) is part of both the measurement and the prediction.";
}

export function floorNote(floor: number): string {
  return `Stars that don't move appear to shift ${arcsec(floor)} here. A motion must be well above this, and above its own error, to count.`;
}

export function referenceStarsNote(used: number, available: number | undefined): string {
  const pool = available !== undefined && available >= used ? ` of ${formatCount(available)} available` : "";
  return `${plural(used, "reference star")}${pool} lined up each photo.`;
}

// ---------------------------------------------------------------------------- what was left out, and why

const LEFT_OUT: Record<string, (count: number) => string> = {
  off_frame: (n) => `${plural(n, "photo")} only grazed this place: it fell off the edge of the detector.`,
  not_received: (n) => `${plural(n, "photo")} did not arrive from NASA's archive.`,
  unreadable: (n) => `${plural(n, "photo")} arrived damaged and could not be read.`,
  poor_astrometry: (n) => `${plural(n, "photo")} ${n === 1 ? "was" : "were"} left out because NASA marks ${n === 1 ? "its" : "their"} pointing as unreliable.`,
  partial_coverage: (n) => `${plural(n, "photo")} ${n === 1 ? "covers" : "cover"} only part of this view and ${n === 1 ? "was" : "were"} left out.`,
};

export function leftOutSentence(reason: string, count: number): string {
  const sentence = LEFT_OUT[reason];
  return sentence ? sentence(count) : `${plural(count, "photo")} could not be used.`;
}

const DEGRADED: Record<string, string> = {
  gaia: "The Gaia star catalogue did not answer while this view was built, so markers may be missing and motion could not be checked. It will be rebuilt automatically.",
  catwise:
    "The CatWISE catalogue did not answer while this view was built, so some cold, faint moving objects may not be marked. It will be rebuilt automatically.",
  photo_list: "NASA's archive did not answer, so this view uses a saved list of photos. The newest photos may be missing.",
  photos: "Some photos did not arrive from NASA's archive. The view will be rebuilt automatically to fetch them.",
  asteroid_catalogue:
    "The asteroid catalogue did not answer while this view was built, so movers could not be named. It will be rebuilt automatically.",
};

export function degradedSentence(service: string): string {
  return DEGRADED[service] ?? "One of the services this view depends on did not answer, so part of it may be missing.";
}

/** How many photos of the object could not give a brightness, and why. */
export function saturatedSentence(count: number): string {
  return `${plural(count, "photo")} ${count === 1 ? "was" : "were"} saturated — too bright to measure.`;
}

export function brightnessLeftOutSentence(count: number): string {
  return `${plural(count, "photo")} ${count === 1 ? "was" : "were"} left out because the light there belonged to a neighbouring object.`;
}

/** The note shown after searching for an old catalogue position of a test target. */
export function movedNote(label: string, arcminutes: number, typedName: boolean): string {
  const since = `It has moved about ${arcminutes.toFixed(1)} arcminutes since; this view is centred where it is now.`;
  return typedName
    ? `Catalogues list ${label} where it was years ago. ${since}`
    : `You entered an old catalogue position of ${label === "" ? "a fast-moving star" : label}. ${since}`;
}

// ---------------------------------------------------------------------------- describing pictures

export function lookAlt(place: string, camera: string, band: readonly [number, number], season: string): string {
  return `SPHEREx infrared image of ${place} from camera ${camera} (${microns(band)}), ${season}. North is up, east is left.`;
}

export function combinedAlt(place: string, camera: string, band: readonly [number, number]): string {
  return `Every SPHEREx photo of ${place} from camera ${camera} (${microns(band)}) added together.`;
}

export function changeAlt(place: string, camera: string, a: string, b: string): string {
  return `Change map of ${place} in camera ${camera}: ${a} minus ${b}. Green is brighter in ${a}, pink is fainter.`;
}

// ---------------------------------------------------------------------------- asteroids (one visit)

export const VISIT_COPY = {
  home: {
    eyebrow: "Faster movers",
    title: "Asteroids, hour by hour",
    lede: "Within a single SPHEREx visit an asteroid crosses the picture in hours. Galileo Blink subtracts the sky that stays put and finds what is left moving. These five are real asteroids in real SPHEREx photos, found by that search without being told where to look.",
    failed: "The asteroid examples could not be loaded. The server may be starting up: try again in a moment.",
    searchLabel: "An asteroid's name or number",
    searchPlaceholder: 'Any asteroid: try "Pallas" or "324"',
    searchSubmit: "Find it",
    searchEmpty: "Type an asteroid's name or number first.",
    magnitude: (vmag: number) => `magnitude ${vmag.toFixed(1)} (a bigger number is fainter)`,
  },
  switch: {
    label: "What to look for",
    looks: "Six-month blink",
    visit: "Asteroid search",
  },
  modes: {
    blink: { label: "Blink", hint: "Step through the moments. Asteroids jump from one to the next." },
    change: { label: "Subtracted", hint: "Each moment minus the sky that stays put. What is left is what moved or changed." },
    combined: { label: "Static sky", hint: "The sky that stays put: the middle value of all the moments." },
  },
  subtractedChip: "moment minus the static sky",
  staticChip: "Static sky",
  keyboardHint: "Arrow keys step through the moments. Space plays and pauses.",
  subtractedNote: "Green dots are light that was there only at that moment: an asteroid, or a cosmic-ray hit.",
  staticNote: "An asteroid is in a different place at every moment, so it vanishes from this picture.",
  panel: {
    eyebrow: "What you're looking at",
    kind: "One visit by SPHEREx, moment by moment",
    explain: "SPHEREx came back to this place several times within a few days. Each moment is a short burst of photos from one camera.",
    unnamed: "This place",
    camera: "Camera",
    moments: "Moments",
    over: (hours: number) => (hours >= 48 ? `over ${(hours / 24).toFixed(1)} days` : `over ${Math.round(hours)} hours`),
    from: "First moment",
    until: "Last moment",
  },
  result: {
    found: (count: number) => (count === 1 ? "moving object found" : "moving objects found"),
    possibleOnly: (count: number) => (count === 1 ? "possible moving object" : "possible moving objects"),
    none: "Nothing was found moving here.",
    notSearched: "Too few moments to search.",
  },
  movers: {
    eyebrow: "The search",
    title: "What moved?",
    none: "Nothing was found moving here. That suggests no object brighter than about magnitude 18.5 crossed this view in three or more moments.",
    notSearched: (moments: number) =>
      `This visit has only ${plural(moments, "moment")}. A path needs three, so the search could not run here.`,
    strong: "Found",
    possible: "Possible",
    identified: "A catalogued asteroid",
    unidentified: "Not in the asteroid catalogue",
    unnamedMover: "Unidentified mover",
    speed: "Speed",
    perHour: "per hour",
    heading: "Heading",
    seen: "Seen in",
    ofMoments: (seen: number, all: number) => `${seen} of ${all} moments`,
    possibleNote:
      "A “possible” path is three faint leftovers that line up. Cosmic-ray hits do that by chance, so it is a hint to look closer, never a discovery.",
    unidentifiedNote:
      "An unidentified mover is not a discovery either: check the flags, and remember the catalogue lookup can miss objects close to Earth.",
    knownTitle: "Catalogued asteroids predicted in this field",
    knownNone: "The asteroid catalogue lists no object in this field during the visit.",
    knownMore: (count: number) =>
      `…and ${plural(count, "fainter one")}, all far too faint for a single SPHEREx photo. Only those brighter than magnitude 19.5 are drawn on the picture.`,
    catalogueDown: "The asteroid catalogue did not answer, so movers could not be named. The view will be rebuilt automatically.",
  },
  how: {
    eyebrow: "How the search works",
    title: "Subtract what stays, keep what moves",
    steps: [
      "Line up every moment north-up, so stars fall on the same pixels.",
      "Take the middle value of each pixel across the moments: that is the sky that stays put.",
      "Subtract it from each moment. Stars vanish; an asteroid is left as a dot.",
      "Join leftover dots that fall on one straight path at a steady speed, in at least three moments.",
      "Ask the asteroid catalogue what should be there, and name what matches.",
    ],
    why: "Subtracting first matters: a faint asteroid passing over a star is invisible as a slightly brighter star, but obvious once the star is removed.",
  },
  honesty: {
    moments: (min: number) =>
      `An object in view for fewer than ${min} moments cannot be found, however bright it is.`,
    faint: (vmag: number) =>
      `Single SPHEREx photos are not deep: asteroids fainter than about magnitude ${vmag} are not expected to be found.`,
    overlap: "Movers are searched for only where at least three moments overlap; the picture's corners are often covered less.",
    chance: "Three leftovers in a line can be chance. Such paths are marked “possible”.",
    slow: "Anything that barely moves within a few days (a distant planet, a star) cancels out in the subtraction and is not found here. That is what the six-month blink is for.",
  },
} as const;

const KNOWN_NOTES: Record<string, (vmag: number, moments: number) => string> = {
  found: () => "found by the search",
  too_faint: (vmag) => `too faint to find (magnitude ${vmag.toFixed(1)})`,
  in_view_too_briefly: (_vmag, moments) =>
    `searchable in only ${plural(moments, "moment")}: three are needed`,
  missed: (vmag) => `bright enough (magnitude ${vmag.toFixed(1)}) but not found`,
};

/** Why a catalogued asteroid was or was not found. */
export function knownAsteroidNote(note: string, vmag: number, moments: number): string {
  return (KNOWN_NOTES[note] ?? KNOWN_NOTES.missed!)(vmag, moments);
}

const COMPASS_POINTS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];

/** A direction in degrees east of north, in words. */
export function compassWord(degrees: number): string {
  return COMPASS_POINTS[Math.round((((degrees % 360) + 360) % 360) / 45) % 8]!;
}

/** "moves 33″ per hour". */
export function hourlySpeed(arcsecPerHour: number): string {
  return `moves ${arcsec(arcsecPerHour, arcsecPerHour < 10 ? 1 : 0)} per hour`;
}

// ---------------------------------------------------------------------------- brightness in words

/** A brightness ratio as people say it: 0.51 is "49% fainter", 1.79 is "79% brighter", 2.4 is "2.4 times brighter". */
export function brightnessWords(ratio: number): string {
  if (ratio >= 2) return `${roundSignificant(ratio, 2)} times brighter`;
  const percent = Math.round(Math.abs(ratio - 1) * 100);
  if (percent === 0) return "unchanged";
  return `${percent}% ${ratio > 1 ? "brighter" : "fainter"}`;
}

/** The error of a brightness ratio, in percent of the first date's brightness. */
export function brightnessError(error: number): string {
  return `${Math.max(1, Math.round(error * 100))}%`;
}

/** One sentence on the clearest brightness measurement of a view. */
export function brightnessSentence(words: {
  name: string;
  first: string;
  last: string;
  camera: number;
  band: string;
  ratio: number;
  error: number;
  changed: boolean;
}): string {
  const where = `in camera ${words.camera} (${words.band})`;
  if (!words.changed) {
    return `Between ${words.first} and ${words.last}, ${words.name} kept the same brightness ${where}, to within ${brightnessError(words.error)}.`;
  }
  return `Between ${words.first} and ${words.last}, ${words.name} became ${brightnessWords(words.ratio)} ${where}, give or take ${brightnessError(words.error)}.`;
}
