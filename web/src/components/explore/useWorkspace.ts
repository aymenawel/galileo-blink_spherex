/**
 * Everything the visitor can change on the Explore page, in one place: which camera, which
 * date, which mode, whether the blink is playing, and which overlays are on.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type { CameraKey, View } from "../../api/types";
import { defaultCamera, looksOf, seasonsWithLooks } from "../../lib/cameras";
import { VISIT_COPY, subjectName } from "../../lib/copy";
import type { ExploreChoices, Mode } from "../../lib/exploreAddress";
import { useReducedMotion } from "../../lib/useReducedMotion";

export type Speed = "slow" | "normal" | "fast";

/** Time each date stays on screen while blinking, in milliseconds. */
export const SPEED_MS: Record<Speed, number> = { slow: 1300, normal: 700, fast: 350 };

export type OverlayName = "markers" | "catwise" | "stars" | "flags";
export type Overlays = Record<OverlayName, boolean>;

export interface Workspace {
  view: View;
  /** True for an asteroid view: one camera, moment by moment. */
  visit: boolean;
  /** True while the picture steps through dates (Blink, and an asteroid view's Subtracted). */
  stepping: boolean;
  /** The place's name, for sentences and picture descriptions. */
  place: string;
  camera: CameraKey;
  /** The date on screen in Blink. */
  season: number;
  mode: Mode;
  /** The two dates of Compare and Change. */
  a: number;
  b: number;
  /** The date the side panels describe: none when every date is added together. */
  shownSeason: number | null;
  /** Seasons in which the chosen camera has a picture. */
  cameraSeasons: number[];
  playing: boolean;
  speed: Speed;
  overlays: Overlays;
  selectCamera: (camera: CameraKey) => void;
  selectSeason: (season: number) => void;
  selectMode: (mode: Mode) => void;
  selectA: (season: number) => void;
  selectB: (season: number) => void;
  swapDates: () => void;
  /** Pause, and move to the chosen camera's next (+1) or previous (-1) date, wrapping around. */
  step: (direction: 1 | -1) => void;
  togglePlaying: () => void;
  /** Start or stop the blink, whatever it was doing. */
  setPlaying: (playing: boolean) => void;
  selectSpeed: (speed: Speed) => void;
  toggleOverlay: (name: OverlayName) => void;
  /** Turn one overlay on or off, whatever it was. */
  setOverlay: (name: OverlayName, on: boolean) => void;
}

function firstOf(seasons: number[], fallback: number): number {
  return seasons[0] ?? fallback;
}

function lastOf(seasons: number[], fallback: number): number {
  return seasons[seasons.length - 1] ?? fallback;
}

/** The camera's next date after (or before) `from`, wrapping around at the ends. */
function neighbour(seasons: number[], from: number, direction: 1 | -1): number {
  if (seasons.length === 0) return from;
  if (direction === 1) return seasons.find((s) => s > from) ?? seasons[0]!;
  return [...seasons].reverse().find((s) => s < from) ?? seasons[seasons.length - 1]!;
}

export function useWorkspace(view: View, initial: ExploreChoices): Workspace {
  const reducedMotion = useReducedMotion();

  const [camera, setCamera] = useState<CameraKey>(() =>
    initial.camera && looksOf(view, initial.camera).length > 0 ? initial.camera : defaultCamera(view),
  );
  const cameraSeasons = useMemo(() => seasonsWithLooks(view, camera), [view, camera]);
  const knownSeason = (season: number | null): season is number =>
    season !== null && view.seasons.some((s) => s.index === season);

  const [season, setSeason] = useState<number>(() =>
    knownSeason(initial.season) ? initial.season : firstOf(cameraSeasons, 0),
  );
  const [mode, setMode] = useState<Mode>(() =>
    initial.mode && !(view.kind === "visit" && initial.mode === "compare") ? initial.mode : "blink",
  );
  const [a, setA] = useState<number>(() => (knownSeason(initial.a) ? initial.a : lastOf(cameraSeasons, 0)));
  const [b, setB] = useState<number>(() => (knownSeason(initial.b) ? initial.b : firstOf(cameraSeasons, 0)));
  // A shared link that names a date opens paused on that date.
  const [playing, setPlaying] = useState(() => !reducedMotion && initial.season === null);
  const [speed, setSpeed] = useState<Speed>("normal");
  const [overlays, setOverlays] = useState<Overlays>({ markers: true, catwise: false, stars: false, flags: false });
  const visit = view.kind === "visit";
  const stepping = mode === "blink" || (visit && mode === "change");

  const advance = useCallback(
    (direction: 1 | -1) => setSeason((current) => neighbour(cameraSeasons, current, direction)),
    [cameraSeasons],
  );

  const blinking = playing && stepping && cameraSeasons.length > 1;
  useEffect(() => {
    if (!blinking) return;
    const timer = window.setInterval(() => advance(1), SPEED_MS[speed]);
    return () => window.clearInterval(timer);
  }, [blinking, speed, advance]);

  // Stepping by hand takes over from the automatic blink.
  const step = useCallback(
    (direction: 1 | -1) => {
      setPlaying(false);
      advance(direction);
    },
    [advance],
  );

  const selectCamera = useCallback(
    (next: CameraKey) => {
      setCamera(next);
      // Compare and Change need two dates this camera actually has.
      const seasons = seasonsWithLooks(view, next);
      setA((current) => (seasons.includes(current) ? current : lastOf(seasons, current)));
      setB((current) => (seasons.includes(current) ? current : firstOf(seasons, current)));
    },
    [view],
  );

  const selectSeason = useCallback((next: number) => {
    setSeason(next);
    setPlaying(false);
  }, []);

  const swapDates = useCallback(() => {
    setA(b);
    setB(a);
  }, [a, b]);

  const togglePlaying = useCallback(() => setPlaying((current) => !current), []);

  const toggleOverlay = useCallback(
    (name: OverlayName) => setOverlays((current) => ({ ...current, [name]: !current[name] })),
    [],
  );

  const setOverlay = useCallback(
    (name: OverlayName, on: boolean) => setOverlays((current) => (current[name] === on ? current : { ...current, [name]: on })),
    [],
  );

  const shownSeason = stepping ? season : mode === "combined" ? null : a;

  return {
    view,
    visit,
    stepping,
    place: visit ? (view.label ?? VISIT_COPY.panel.unnamed) : subjectName(view),
    camera,
    season,
    mode,
    a,
    b,
    shownSeason,
    cameraSeasons,
    playing: blinking,
    speed,
    overlays,
    selectCamera,
    selectSeason,
    selectMode: setMode,
    selectA: setA,
    selectB: setB,
    swapDates,
    step,
    togglePlaying,
    setPlaying,
    selectSpeed: setSpeed,
    toggleOverlay,
    setOverlay,
  };
}
