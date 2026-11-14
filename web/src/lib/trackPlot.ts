/** The numbers behind the motion plot: the predicted path and where each look found the object. */
import type { PathPoint, TrackPoint } from "../api/types";

export interface Offset {
  /** Arcseconds east of where the object was at the first season. */
  east: number;
  /** Arcseconds north of where the object was at the first season. */
  north: number;
}

export interface MeasuredPosition extends Offset {
  season: number;
  /** One-sigma error of the position, arcseconds. */
  error: number;
  /** Where the catalogue says the object should be on that date. */
  predicted: Offset;
}

/**
 * The predicted position on a date, read off the path. Between two path points it is a
 * straight line; just outside the path it continues the nearest segment, because a camera
 * can look a few days before the first season's date or after the last one's.
 */
export function pathAt(path: readonly PathPoint[], mjd: number): Offset {
  const first = path[0];
  if (!first) return { east: 0, north: 0 };
  if (path.length === 1) return { east: first.east, north: first.north };
  let i = 1;
  while (i < path.length - 1 && path[i]!.mjd < mjd) i += 1;
  const a = path[i - 1]!;
  const b = path[i]!;
  const span = b.mjd - a.mjd;
  const t = span === 0 ? 0 : (mjd - a.mjd) / span;
  return { east: a.east + (b.east - a.east) * t, north: a.north + (b.north - a.north) * t };
}

/** Each look's measured position: the predicted position on that date plus the measured offset. */
export function measuredPositions(
  path: readonly PathPoint[],
  track: readonly TrackPoint[],
): MeasuredPosition[] {
  return track.map((point) => {
    const predicted = pathAt(path, point.mjd);
    return {
      season: point.season,
      east: predicted.east + point.east,
      north: predicted.north + point.north,
      error: point.error,
      predicted,
    };
  });
}
