/**
 * "Show me what to look for": a few short steps beside the picture that point out what is
 * on screen and why it matters. Each of NASA's five test targets has its own; every other
 * place, and every asteroid view, gets a general one.
 *
 * A step may ask the page to show something (a mode, a camera, the markers) so the words
 * and the picture always match. Numbers in the words come from the view's own measurement.
 */
import type { CameraKey, Motion, View } from "../api/types";
import { bandOf } from "../lib/cameras";
import { analogy, brightnessSentence, compassWord } from "../lib/copy";
import type { Mode } from "../lib/exploreAddress";
import { arcsecNumber, fieldWords, microns } from "../lib/format";

/** What the page shows while a step is open. Anything left out stays as the visitor had it. */
export interface FirstLookShow {
  mode?: Mode;
  /** Used only when this camera has pictures of the place. */
  camera?: CameraKey;
  /** In Blink: play through the dates, or hold on the camera's first or last one. */
  blink?: "play" | "first" | "last";
  /** The catalogue's rings on the picture. */
  markers?: boolean;
}

export interface FirstLookStep {
  title: string;
  text: string;
  show?: FirstLookShow;
}

type Steps = (view: View) => FirstLookStep[];

function motionOf(view: View): Motion | null {
  return view.motion_combined ?? view.motion ?? null;
}

function seasonLabel(view: View, index: number | undefined): string | null {
  return index === undefined ? null : (view.seasons.find((season) => season.index === index)?.label ?? null);
}

/** "between Aug 2025 and Aug 2026", from the two dates the motion was measured between. */
function between(view: View): string {
  const span = view.motion ?? motionOf(view);
  const first = seasonLabel(view, span?.first_season) ?? view.seasons[0]?.label;
  const last = seasonLabel(view, span?.last_season) ?? view.seasons[view.seasons.length - 1]?.label;
  return first && last && first !== last ? `between ${first} and ${last}` : "between the dates";
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** The direction of the measured motion in words: "north", "south-east". */
function heading(motion: Motion | null): string | null {
  if (!motion || motion.measured_east === undefined || motion.measured_north === undefined) return null;
  return compassWord((Math.atan2(motion.measured_east, motion.measured_north) * 180) / Math.PI);
}

/** The closing step of every moving target: the number, what it was checked against, and its size in everyday terms. */
function measurementStep(view: View, name: string, why: string): FirstLookStep {
  const motion = motionOf(view);
  if (!motion) {
    return {
      title: "The measurement",
      text: `${view.motion_reason_text ?? "No motion could be measured in this view."} ${why}`,
      show: { mode: "blink", blink: "play", markers: true },
    };
  }
  const cameras = motion.n_cameras && motion.n_cameras > 1 ? `${COUNT_WORDS[motion.n_cameras] ?? motion.n_cameras} cameras together` : "One camera";
  return {
    title: "How far did it go?",
    text: `${cameras} measured ${arcsecNumber(motion.measured)} arcseconds, give or take ${arcsecNumber(motion.error)}: ${analogy(motion.measured)}. The catalogue predicted ${arcsecNumber(motion.predicted)} for ${name}. ${why}`,
    show: { mode: "blink", blink: "play", markers: true },
  };
}

const COUNT_WORDS: Record<number, string> = { 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six" };

const CHANGE_STEP_TEXT =
  "Stars that stayed put cancel out. Anything that moved leaves a pair: pink where it was, green where it is now.";

const TARGETS: Record<string, Steps> = {
  barnard: (view) => [
    {
      title: "Find the one that moves",
      text: `Every dot here is a star. Watch the bright one in the middle: ${between(view)} it steps ${heading(motionOf(view)) ?? "north"}, up the picture, while its neighbours stay where they are.`,
      show: { mode: "blink", blink: "play", markers: false },
    },
    {
      title: "The ring is a prediction",
      text: "The ring is not drawn from the picture. It marks where Gaia, a European star-mapping telescope, says Barnard's Star should be on each date. The star lands inside it every time.",
      show: { mode: "blink", blink: "play", markers: true },
    },
    {
      title: "Subtract one date from another",
      text: `Change shows the last date minus the first. ${CHANGE_STEP_TEXT}`,
      show: { mode: "change", markers: true },
    },
    measurementStep(view, "Barnard's Star", "It looks so fast because it is so close: 6 light-years away."),
  ],

  epsindib: (view) => [
    {
      title: "A dot that is not a star",
      text: "The dot in the ring is a pair of brown dwarfs: bodies too small to shine like stars, glowing in infrared. The glare at the right edge is Epsilon Indi, the star they orbit, just outside the picture.",
      show: { mode: "blink", blink: "first", markers: true },
    },
    {
      title: "Watch it drift",
      text: `Now the dates play. ${capital(between(view))} the dot slides ${heading(motionOf(view)) ?? "south-east"}, toward the lower left, and its ring, predicted from Gaia, slides with it.`,
      show: { mode: "blink", blink: "play", markers: true },
    },
    {
      title: "Subtract one date from another",
      text: `Change shows the last date minus the first. ${CHANGE_STEP_TEXT}`,
      show: { mode: "change", markers: true },
    },
    measurementStep(view, "the pair", "They travel with the star Epsilon Indi, 12 light-years away."),
  ],

  wise0855: (view) => [
    {
      title: "Nothing to see, at first",
      text: "This is camera 1, SPHEREx's shortest infrared wavelengths. The ring marks where WISE 0855 should be, and it is empty: this object is as cold as the North Pole and gives off no light at these wavelengths.",
      show: { mode: "blink", blink: "first", camera: "1", markers: true },
    },
    {
      title: "It appears near 4 microns",
      text: "Camera 5 sees longer wavelengths, and now there is a faint glow inside the ring. That is the coldest brown dwarf known, 7 light-years away.",
      show: { mode: "blink", blink: "first", camera: "5", markers: true },
    },
    {
      title: "Watch it creep",
      text: `Now the dates play. ${capital(between(view))} the glow shifts a little to the right, which is west, and the ring from the catalogue moves with it.`,
      show: { mode: "blink", blink: "play", camera: "5", markers: true },
    },
    measurementStep(view, "WISE 0855", "Only one camera can see it, so the error is larger than for a bright star."),
  ],

  rwaur: (view) => {
    const best = view.brightness_change?.best;
    const camera = best ? (`${best.camera}` as CameraKey) : "5";
    const fainter = !best || best.ratio < 1;
    const steps: FirstLookStep[] = [
      {
        title: "A star that stays put",
        text: "RW Aurigae is a young star still gathering gas and dust from a disk around it. Watch the centre as the dates play: it stays inside its ring.",
        show: { mode: "blink", blink: "play", markers: true },
      },
      {
        title: "But it does not stay the same",
        text: `Change shows the last date minus the first, here in camera ${camera}. A steady star would cancel out. ${fainter ? "Pink" : "Green"} at the centre means it was ${fainter ? "fainter" : "brighter"} on the later date.`,
        show: { mode: "change", camera, markers: true },
      },
    ];
    if (best?.changed) {
      steps.push({
        title: "How much?",
        text: `${brightnessSentence({
          name: "it",
          first: seasonLabel(view, best.first_season) ?? "the first date",
          last: seasonLabel(view, best.last_season) ?? "the last date",
          camera: best.camera,
          band: microns(bandOf(view.cameras[camera], camera)),
          ratio: best.ratio,
          error: best.error,
          changed: true,
        })} Other cameras tell a different story: every one is plotted under "Did its brightness change?" further down.`,
        show: { mode: "change", camera, markers: true },
      });
    }
    steps.push(measurementStep(view, "RW Aurigae", "A shift that small is no motion at all: the star is 500 light-years away."));
    return steps;
  },

  rdra: (view) => [
    {
      title: "Too bright for the camera",
      text: "R Draconis is a red giant that swells and shrinks over about eight months. It is so bright in infrared that its image overflows the detector: the white disc is glare, far wider than the star itself.",
      show: { mode: "blink", blink: "first", markers: true },
    },
    {
      title: "Watch the dates",
      text: "Play through the dates. The star stays in its ring. Its glare grows and shrinks from date to date, partly because the star itself changes and partly because each photo is a different wavelength.",
      show: { mode: "blink", blink: "play", markers: true },
    },
    {
      title: "An honest limit",
      text: "Because the star overflows the detector, its true brightness cannot be read from these photos. Galileo Blink says so instead of guessing; its position is still measured from the fainter light around it.",
      show: { mode: "blink", blink: "play", markers: true },
    },
    measurementStep(view, "R Draconis", "For a star this far away, that means it did not move."),
  ],
};

const PLACE: Steps = (view) => {
  const motion = motionOf(view);
  const steps: FirstLookStep[] = [
    {
      title: "A real photo from space",
      text: `This is what NASA's SPHEREx telescope saw here in infrared light. North is up and east is left. The picture is ${fieldWords(view.size_deg).replace(" · ", " wide: ")}.`,
      show: { mode: "blink", blink: "first" },
    },
    {
      title: "Blink through the dates",
      text: "SPHEREx comes back to most places about every six months. As the dates play, stars that stay put hold still. Anything that moved appears to jump.",
      show: { mode: "blink", blink: "play" },
    },
  ];
  if ((view.markers?.length ?? 0) > 0) {
    steps.push({
      title: "Rings are predictions",
      text: "A ring marks where a star catalogue says a moving object should be on each date. When the dot stays inside its ring, the catalogue and SPHEREx agree.",
      show: { mode: "blink", blink: "play", markers: true },
    });
  }
  steps.push(
    {
      title: "Subtract one date from another",
      text: `Change shows one date minus another. ${CHANGE_STEP_TEXT}`,
      show: { mode: "change" },
    },
    {
      title: "Six cameras, six kinds of infrared",
      text: "Each camera sees a different slice of infrared light. Cold objects show only in cameras 5 and 6. Pick a camera under the picture to compare.",
      show: { mode: "blink", blink: "play" },
    },
  );
  if (motion) steps.push(measurementStep(view, "it", "The numbers behind this are further down the page."));
  return steps;
};

const VISIT: Steps = (view) => {
  const found = (view.tracks ?? []).filter((track) => track.confidence === "strong");
  const named = found.find((track) => track.name)?.name ?? null;
  return [
    {
      title: "One visit, hour by hour",
      text: "SPHEREx passed over this place several times within a few days. Each step is one of those moments. Stars hold still; an asteroid is somewhere new every time.",
      show: { mode: "blink", blink: "play" },
    },
    {
      title: "Take away the sky that stays",
      text: "Subtracted shows each moment minus everything that never changed. The stars vanish, and what is left is light that was there only at that moment.",
      show: { mode: "change", blink: "play" },
    },
    {
      title: found.length > 0 ? "A path across the picture" : "What the search found",
      text:
        found.length > 0
          ? `Leftover dots that line up on one straight path, at a steady speed, are a moving object. ${named ? `This one matches ${named} in the asteroid catalogue.` : "This one matches nothing in the asteroid catalogue, which is a reason to look closer, not a discovery."}`
          : "Nothing lined up into a steady path here. That is a result too: no object bright enough for a single SPHEREx photo crossed this view.",
      show: { mode: "blink", blink: "play", markers: true },
    },
  ];
};

/** The steps for a view. Always at least two. */
export function firstLookFor(view: View): FirstLookStep[] {
  if (view.kind === "visit") return VISIT(view);
  const own = view.target ? TARGETS[view.target.id] : undefined;
  return (own ?? PLACE)(view);
}
