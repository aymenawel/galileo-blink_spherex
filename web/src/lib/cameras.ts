/** SPHEREx's six cameras: their order, their wavelengths, and finding their pictures in a view. */
import type { Band, CameraKey, CameraView, Look, StarDot, View } from "../api/types";

export const CAMERA_KEYS: readonly CameraKey[] = ["1", "2", "3", "4", "5", "6"];

/** The wavelengths each camera covers, in microns, used until the server's own list arrives. */
export const CAMERA_BANDS: Record<CameraKey, Band> = {
  "1": [0.75, 1.09],
  "2": [1.1, 1.62],
  "3": [1.63, 2.41],
  "4": [2.42, 3.82],
  "5": [3.83, 4.41],
  "6": [4.42, 5.0],
};

/** When several cameras are equally good, the long-wavelength ones win: cold objects show there. */
const CAMERA_PREFERENCE: readonly CameraKey[] = ["6", "5", "2", "3", "4", "1"];

export function toCameraKey(camera: number | string | null | undefined): CameraKey | null {
  const text = String(camera);
  return CAMERA_KEYS.find((key) => key === text) ?? null;
}

export function looksOf(view: View, camera: CameraKey): Look[] {
  return view.cameras[camera]?.looks ?? [];
}

/** The picture one camera took in one season, if it took one. */
export function lookAt(view: View, camera: CameraKey, season: number): Look | undefined {
  return looksOf(view, camera).find((look) => look.season === season);
}

/** The seasons in which a camera has a picture, earliest first. */
export function seasonsWithLooks(view: View, camera: CameraKey): number[] {
  return looksOf(view, camera)
    .map((look) => look.season)
    .sort((a, b) => a - b);
}

export function bandOf(camera: CameraView | undefined, key: CameraKey): Band {
  return camera?.band ?? CAMERA_BANDS[key];
}

/**
 * The camera to show first: the one the motion was measured in, otherwise the one with the
 * most seasons.
 */
export function defaultCamera(view: View): CameraKey {
  const measured = toCameraKey(view.motion?.camera);
  if (measured && looksOf(view, measured).length > 0) return measured;
  let best: CameraKey = CAMERA_PREFERENCE[0]!;
  for (const key of CAMERA_PREFERENCE) {
    if (looksOf(view, key).length > looksOf(view, best).length) best = key;
  }
  return best;
}

/** One colour per camera for plots, running from blue (shortest wavelengths) to pink (longest). */
const CAMERA_COLOURS: Record<CameraKey, string> = {
  "1": "#6CC4FF",
  "2": "#4FD1C5",
  "3": "#A4F05C",
  "4": "#E8E26A",
  "5": "#F2A0BE",
  "6": "#FF60AA",
};

export function cameraColour(camera: CameraKey): string {
  return CAMERA_COLOURS[camera];
}

/** Colours that tell seasons apart in a plot. They repeat after ten seasons. */
const SEASON_COLOURS = [
  "#A4F05C",
  "#FF60AA",
  "#6CC4FF",
  "#F0D264",
  "#C9B3FF",
  "#4FD1C5",
  "#F2A0BE",
  "#A9B4C2",
  "#E8E26A",
  "#7BD8C0",
];

export function seasonColour(season: number): string {
  return SEASON_COLOURS[season % SEASON_COLOURS.length]!;
}

/**
 * The faintest Gaia star (G magnitude) that still shows as a dot in each camera's picture.
 * Measured on the test targets' pictures: about nine marked stars in ten are visible down to
 * these values, and fewer than two in three half a magnitude fainter. Most stars fade toward
 * longer wavelengths, so the limit is brighter in the long-wavelength cameras.
 */
export const STAR_MARK_LIMIT: Record<CameraKey, number> = { "1": 15.5, "2": 15.5, "3": 15, "4": 14.5, "5": 13.5, "6": 12.5 };

/** The catalogued stars worth marking in a camera's picture: only those it can show. */
export function starsToMark(view: { stars?: StarDot[] | null }, camera: CameraKey): StarDot[] {
  return (view.stars ?? []).filter((star) => (star[2] ?? 99) <= STAR_MARK_LIMIT[camera]);
}
