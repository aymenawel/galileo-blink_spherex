/** SPHEREx's six cameras: their order, their colours, and finding their pictures in a view. */
import type { Band, CameraKey, CameraView, Look, View } from "../api/types";

export const CAMERA_KEYS: readonly CameraKey[] = ["1", "2", "3", "4", "5", "6"];

/** An infrared ramp, shortest wavelength (camera 1) to longest (camera 6). */
export const CAMERA_COLOURS: Record<CameraKey, string> = {
  "1": "#F4E3B1",
  "2": "#F6C177",
  "3": "#F59E5B",
  "4": "#EE7A4B",
  "5": "#DC5546",
  "6": "#B8323F",
};

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

/** Colours that tell seasons apart in a plot. They repeat after ten seasons. */
const SEASON_COLOURS = [
  "#6CC4FF",
  "#FFB24A",
  "#7BD88F",
  "#F28FB1",
  "#C9B3FF",
  "#F4E3B1",
  "#4FD1C5",
  "#FF7A6B",
  "#A9B4C2",
  "#E3D45C",
];

export function seasonColour(season: number): string {
  return SEASON_COLOURS[season % SEASON_COLOURS.length]!;
}
