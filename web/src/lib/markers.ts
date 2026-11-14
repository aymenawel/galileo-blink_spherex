/** Catalogued moving objects: which ones to draw, and where each sits in a given season. */
import type { Marker, MarkerPosition } from "../api/types";

/** A marker ready to draw, with the other catalogue names of the same object. */
export interface DrawnMarker {
  marker: Marker;
  alsoKnownAs: string[];
}

/** Two catalogue entries closer than this in every season are the same dot to SPHEREx. */
const SAME_OBJECT_PIXELS = 0.75;

function sameObject(a: Marker, b: Marker): boolean {
  if (a.track.length === 0 || a.track.length !== b.track.length) return false;
  return a.track.every((p, i) => {
    const q = b.track[i];
    return q !== undefined && Math.hypot(p.x - q.x, p.y - q.y) < SAME_OBJECT_PIXELS;
  });
}

/**
 * The markers to draw. The view's subject is often listed twice, once under its familiar
 * name and once under its catalogue number; the second entry is folded into the first so
 * two reticles are never drawn on one star. The subject is drawn last, on top.
 */
export function markersToDraw(markers: readonly Marker[] | undefined): DrawnMarker[] {
  const all = markers ?? [];
  const subject = all.find((marker) => marker.subject);
  const others: DrawnMarker[] = [];
  const aliases: string[] = [];
  for (const marker of all) {
    if (marker === subject) continue;
    if (subject && sameObject(subject, marker)) {
      if (marker.name !== subject.name) aliases.push(marker.name);
    } else {
      others.push({ marker, alsoKnownAs: [] });
    }
  }
  return subject ? [...others, { marker: subject, alsoKnownAs: aliases }] : others;
}

/**
 * Where a marker sits in a season. With no season (a picture that adds every date
 * together) it is the latest position.
 */
export function positionAt(marker: Marker, season: number | null): MarkerPosition | undefined {
  if (season === null) return marker.track[marker.track.length - 1];
  return marker.track.find((position) => position.season === season);
}
