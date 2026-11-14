/**
 * The Explore page's address: everything on screen that is worth sharing is written into
 * the URL, and read back from it when a shared link is opened.
 */
import type { ViewRequest } from "../api/client";
import type { CameraKey } from "../api/types";
import { toCameraKey } from "./cameras";

export type Mode = "blink" | "compare" | "change" | "combined";

export const MODES: readonly Mode[] = ["blink", "compare", "change", "combined"];

/** Fields of view offered for places that are not test targets, in degrees. */
export const FIELD_CHOICES: readonly number[] = [0.1, 0.15, 0.25, 0.4];
export const DEFAULT_FIELD = 0.15;

/** What the visitor has chosen to look at inside a view. */
export interface ExploreChoices {
  camera: CameraKey | null;
  season: number | null;
  mode: Mode | null;
  /** The two dates of Compare and Change. */
  a: number | null;
  b: number | null;
}

export interface ExploreAddress extends ExploreChoices {
  request: ViewRequest | null;
  /** The name the visitor searched for, when the place is not a test target. */
  name: string | null;
}

function numberOrNull(text: string | null): number | null {
  if (text === null || text.trim() === "") return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

function seasonOrNull(text: string | null): number | null {
  const value = numberOrNull(text);
  return value !== null && Number.isInteger(value) && value >= 0 ? value : null;
}

function readRequest(query: URLSearchParams): ViewRequest | null {
  const target = query.get("target");
  if (target) return { kind: "target", id: target };
  const ra = numberOrNull(query.get("ra"));
  const dec = numberOrNull(query.get("dec"));
  if (ra === null || dec === null) return null;
  return { kind: "place", ra, dec, size: numberOrNull(query.get("size")) ?? DEFAULT_FIELD };
}

export function readExploreAddress(query: URLSearchParams): ExploreAddress {
  const mode = query.get("mode");
  return {
    request: readRequest(query),
    name: query.get("name"),
    camera: toCameraKey(query.get("cam")),
    season: seasonOrNull(query.get("season")),
    mode: MODES.find((m) => m === mode) ?? null,
    a: seasonOrNull(query.get("a")),
    b: seasonOrNull(query.get("b")),
  };
}

/** The address of a view, with any choices worth keeping. */
export function exploreAddress(
  request: ViewRequest,
  name?: string | null,
  choices?: Partial<ExploreChoices>,
): string {
  const query = new URLSearchParams();
  if (request.kind === "target") {
    query.set("target", request.id);
  } else {
    query.set("ra", String(request.ra));
    query.set("dec", String(request.dec));
    query.set("size", String(request.size));
    if (name) query.set("name", name);
  }
  if (choices?.camera) query.set("cam", choices.camera);
  if (choices?.mode) query.set("mode", choices.mode);
  if (choices?.mode === "compare" || choices?.mode === "change") {
    if (choices.a !== null && choices.a !== undefined) query.set("a", String(choices.a));
    if (choices.b !== null && choices.b !== undefined) query.set("b", String(choices.b));
  } else if (choices?.season !== null && choices?.season !== undefined) {
    query.set("season", String(choices.season));
  }
  return `/explore?${query.toString()}`;
}
