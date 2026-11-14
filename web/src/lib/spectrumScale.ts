/** How brightness is laid out on the vertical axis of the spectrum plot. */
import { decadeTicks, niceTicks } from "./ticks";

export interface BrightnessScale {
  kind: "linear" | "log";
  /** Brightness at the bottom and top of the plot, in mJy. */
  low: number;
  high: number;
  /** Position of a brightness between 0 (bottom) and 1 (top). On a log axis values at or below `low` sit at 0. */
  position: (mjy: number) => number;
  ticks: number[];
}

/** Beyond this ratio between brightest and faintest, equal steps would squash the faint points. */
const LOG_ABOVE_RATIO = 30;
/** A log axis shows at most this many powers of ten below the brightest point. */
const LOG_MAX_DECADES = 4;

/**
 * Choose the axis for a set of brightness values. Faint objects can measure slightly below
 * zero (that is noise, not negative light); such values keep a linear axis honest, and on a
 * log axis they are pinned to the bottom edge.
 */
export function brightnessScale(values: readonly number[]): BrightnessScale | null {
  const finite = values.filter((v) => Number.isFinite(v));
  if (finite.length === 0) return null;
  const max = Math.max(...finite);
  const min = Math.min(...finite);
  const positive = finite.filter((v) => v > 0);
  const smallestPositive = positive.length > 0 ? Math.min(...positive) : 0;

  if (max > 0 && smallestPositive > 0 && max / smallestPositive > LOG_ABOVE_RATIO) {
    const floor = Math.max(smallestPositive, max / 10 ** LOG_MAX_DECADES);
    const low = 10 ** (Math.log10(floor) - 0.15);
    const high = 10 ** (Math.log10(max) + 0.15);
    const span = Math.log10(high) - Math.log10(low);
    return {
      kind: "log",
      low,
      high,
      position: (mjy) => (mjy <= low ? 0 : Math.min(1, (Math.log10(mjy) - Math.log10(low)) / span)),
      ticks: decadeTicks(low, high),
    };
  }

  const pad = max === min ? Math.max(Math.abs(max) * 0.1, 1e-3) : (max - min) * 0.08;
  const low = min >= 0 && min - pad < 0 ? 0 : min - pad;
  const high = max + pad;
  return {
    kind: "linear",
    low,
    high,
    position: (mjy) => (mjy - low) / (high - low),
    ticks: niceTicks(low, high, 4),
  };
}
