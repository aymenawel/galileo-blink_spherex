/** Turning numbers into text. Every helper here is pure: same input, same words. */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MS_PER_DAY = 86_400_000;
const MJD_OF_UNIX_EPOCH = 40_587;

/** "1 photo", "6 photos". */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${formatCount(count)} ${count === 1 ? one : many}`;
}

/** 12345 → "12,345". */
export function formatCount(count: number): string {
  return Math.round(count).toLocaleString("en-US");
}

/** An angle in arcseconds with its symbol: 10.249 → "10.2″". */
export function arcsec(value: number, digits = 1): string {
  return `${value.toFixed(digits)}″`;
}

/** Just the digits of an angle, for sentences that spell out the unit. */
export function arcsecNumber(value: number, digits = 1): string {
  return value.toFixed(digits);
}

/** A wavelength range: [4.42, 5.0] → "4.4–5.0 µm". */
export function microns(band: readonly [number, number]): string {
  return `${band[0].toFixed(1)}–${band[1].toFixed(1)} µm`;
}

/** One wavelength: 4.9285 → "4.93 µm". */
export function micron(value: number): string {
  return `${value.toFixed(2)} µm`;
}

/** "2025-08-26" → "26 Aug 2025". Anything that is not such a date is returned unchanged. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) return iso;
  const month = MONTHS[Number(match[2]) - 1];
  return month ? `${Number(match[3])} ${month} ${match[1]}` : iso;
}

/** A Modified Julian Date (the day count astronomers use) as "26 Aug 2025". */
export function formatMjd(mjd: number): string {
  const date = new Date((mjd - MJD_OF_UNIX_EPOCH) * MS_PER_DAY);
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

function pad(value: number, width: number): string {
  return String(value).padStart(width, "0");
}

/**
 * Split a non-negative quantity into whole units, whole sixtieths and seconds rounded to
 * `digits`, carrying correctly so the seconds never read "60".
 */
function sexagesimal(value: number, digits: number): [number, number, string] {
  const scale = 10 ** digits;
  const total = Math.round(value * 3600 * scale);
  const seconds = (total % (60 * scale)) / scale;
  const minutes = Math.floor(total / (60 * scale)) % 60;
  const units = Math.floor(total / (3600 * scale));
  const whole = Math.floor(seconds);
  const text = digits > 0 ? `${pad(whole, 2)}.${pad(Math.round((seconds - whole) * scale), digits)}` : pad(whole, 2);
  return [units, minutes, text];
}

/** Right ascension the way catalogues print it: 269.4464° → "17h 57m 47.1s". */
export function formatRa(degrees: number): string {
  const [h, m, s] = sexagesimal((((degrees % 360) + 360) % 360) / 15, 1);
  return `${pad(h % 24, 2)}h ${pad(m, 2)}m ${s}s`;
}

/** Declination the way catalogues print it: 4.7686° → "+04° 46′ 07″". */
export function formatDec(degrees: number): string {
  const [d, m, s] = sexagesimal(Math.abs(degrees), 0);
  return `${degrees < 0 ? "−" : "+"}${pad(d, 2)}° ${pad(m, 2)}′ ${s}″`;
}

/** An angle in plain degrees: 269.4464 → "269.4464°". */
export function formatDegrees(degrees: number, digits = 4): string {
  return `${degrees < 0 ? "−" : ""}${Math.abs(degrees).toFixed(digits)}°`;
}

/** A field of view both ways: 0.15 → "0.15° (9 arcminutes)". */
export function formatField(degrees: number): string {
  const arcminutes = degrees * 60;
  const rounded = Number.isInteger(Math.round(arcminutes * 10) / 10) ? arcminutes.toFixed(0) : arcminutes.toFixed(1);
  return `${degrees}° (${rounded} arcminutes)`;
}

/**
 * Brightness in millijanskys with digits that suit its size: 3500.3 → "3,500 mJy",
 * 13.4089 → "13.4 mJy", 0.0914 → "0.091 mJy".
 */
export function formatFlux(mjy: number): string {
  return `${fluxNumber(mjy)} mJy`;
}

/** The digits of `formatFlux`, without the unit. */
export function fluxNumber(mjy: number): string {
  const size = Math.abs(mjy);
  if (size >= 1000) return formatCount(mjy);
  if (size >= 100) return mjy.toFixed(0);
  if (size >= 10) return mjy.toFixed(1);
  if (size >= 1) return mjy.toFixed(2);
  return mjy.toFixed(3);
}

/** Round to a few significant figures: (495, 1) → 500, (1151, 2) → 1200. */
export function roundSignificant(value: number, figures: number): number {
  if (value === 0 || !Number.isFinite(value)) return value;
  return Number(value.toPrecision(figures));
}

/** Seconds as a short duration: 8.4 → "8 s", 75 → "1 min 15 s". */
export function formatSeconds(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return whole < 60 ? `${whole} s` : `${Math.floor(whole / 60)} min ${whole % 60} s`;
}
