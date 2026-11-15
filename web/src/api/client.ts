/** Every request the interface makes to the Galileo Blink server, in one place. */
import { COPY } from "../lib/copy";
import type {
  About,
  AsteroidExample,
  ErrorKind,
  QuickSpectrum,
  ResolvedPlace,
  Target,
  View,
  ViewStatus,
} from "./types";

/**
 * What to open: one of NASA's test targets or any spot in the sky (the six-month view), or
 * an asteroid example, an asteroid by name, or any spot searched for movers (one visit).
 */
export type ViewRequest =
  | { kind: "target"; id: string }
  | { kind: "place"; ra: number; dec: number; size: number }
  | { kind: "asteroid"; id: string }
  | { kind: "asteroidName"; name: string }
  | { kind: "visit"; ra: number; dec: number; size: number; camera?: number };

/** A failed request, with a sentence fit to show and whose side the failure is on. */
export class ApiError extends Error {
  readonly kind: ErrorKind;
  readonly status: number;

  constructor(message: string, kind: ErrorKind, status: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

interface ErrorBody {
  error?: unknown;
  error_kind?: unknown;
  detail?: unknown;
}

const ERROR_KINDS: readonly ErrorKind[] = ["request", "service", "busy", "internal", "network"];

function kindFromStatus(status: number): ErrorKind {
  if (status === 503) return "busy";
  if (status >= 500) return "service";
  return "request";
}

async function errorFrom(response: Response): Promise<ApiError> {
  let body: ErrorBody = {};
  try {
    body = (await response.json()) as ErrorBody;
  } catch {
    // The body was not JSON; the status alone decides the message.
  }
  const sentence =
    typeof body.error === "string"
      ? body.error
      : typeof body.detail === "string"
        ? body.detail
        : COPY.errors.unexpected;
  const kind = ERROR_KINDS.find((k) => k === body.error_kind) ?? kindFromStatus(response.status);
  return new ApiError(sentence, kind, response.status);
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(COPY.errors.network, "network", 0);
  }
  if (!response.ok) throw await errorFrom(response);
  return (await response.json()) as T;
}

export function fetchTargets(signal?: AbortSignal): Promise<Target[]> {
  return getJson<Target[]>("/api/targets", signal);
}

export function fetchAsteroids(signal?: AbortSignal): Promise<AsteroidExample[]> {
  return getJson<AsteroidExample[]>("/api/asteroids", signal);
}

export function fetchAbout(signal?: AbortSignal): Promise<About> {
  return getJson<About>("/api/about", signal);
}

export function resolvePlace(text: string, signal?: AbortSignal): Promise<ResolvedPlace> {
  return getJson<ResolvedPlace>(`/api/resolve?q=${encodeURIComponent(text)}`, signal);
}

/** Ask for a view; the server starts building it if it does not exist yet. */
export function openView(request: ViewRequest, signal?: AbortSignal): Promise<ViewStatus> {
  return getJson<ViewStatus>(openAddress(request), signal);
}

function openAddress(request: ViewRequest): string {
  switch (request.kind) {
    case "target":
      return `/api/view?target=${encodeURIComponent(request.id)}`;
    case "place":
      return `/api/view?ra=${request.ra}&dec=${request.dec}&size=${request.size}`;
    case "asteroid":
      return `/api/asteroids/${encodeURIComponent(request.id)}`;
    case "asteroidName":
      return `/api/asteroid?name=${encodeURIComponent(request.name)}`;
    case "visit":
      return `/api/visit?ra=${request.ra}&dec=${request.dec}&size=${request.size}${request.camera ? `&camera=${request.camera}` : ""}`;
  }
}

/** Progress of a view; includes the view itself once it is ready. */
export function fetchViewStatus(key: string, signal?: AbortSignal): Promise<ViewStatus> {
  return getJson<ViewStatus>(`/api/view/${encodeURIComponent(key)}`, signal);
}

/** The whole-sky map's spectrum at a point. The server may not offer this yet. */
export function fetchQuickSpectrum(ra: number, dec: number, signal?: AbortSignal): Promise<QuickSpectrum> {
  return getJson<QuickSpectrum>(`/api/spectrum?ra=${ra}&dec=${dec}`, signal);
}

/** Address of a picture named inside a view. */
export function fileUrl(view: Pick<View, "key">, name: string): string {
  return `/files/${encodeURIComponent(view.key)}/${encodeURIComponent(name)}`;
}

/** Address of one camera's blink as an animated GIF, to save or share. */
export function blinkGifUrl(view: Pick<View, "key">, camera: number, layer: "photo" | "change", frameMs: number): string {
  return `/api/view/${encodeURIComponent(view.key)}/blink.gif?camera=${camera}&layer=${layer}&ms=${frameMs}`;
}

/** Address of one still picture of a view, with its measurement written under it, to save or share. */
export function cardUrl(view: Pick<View, "key">, camera: number, season: number, layer: "photo" | "change"): string {
  return `/api/view/${encodeURIComponent(view.key)}/card.png?camera=${camera}&season=${season}&layer=${layer}`;
}

/** Address of a change map (season `a` minus season `b`) made on request. */
export function changeMapUrl(view: Pick<View, "key">, camera: number, a: number, b: number): string {
  return `/api/view/${encodeURIComponent(view.key)}/compare?camera=${camera}&a=${a}&b=${b}&op=subtract`;
}
