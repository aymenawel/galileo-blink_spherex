/**
 * Where things are: conversions between a view's pixel grid, the picture on screen and
 * the sky.
 *
 * A view is `n` SPHEREx pixels wide, north up and east to the LEFT. The server gives
 * positions in view pixels with y pointing UP and pixel centres at whole numbers, so the
 * centre of the bottom-left pixel is (0, 0) and the picture spans -0.5 to n - 0.5.
 */

export interface ScreenFraction {
  /** 0 at the left edge of the picture, 1 at the right edge. */
  left: number;
  /** 0 at the top edge of the picture, 1 at the bottom edge. */
  top: number;
}

export interface PixelPosition {
  x: number;
  y: number;
}

export interface SkyPosition {
  /** Right ascension in degrees, 0 to 360. */
  ra: number;
  /** Declination in degrees. */
  dec: number;
}

export interface ViewFrame {
  ra: number;
  dec: number;
  n: number;
  pixel_arcsec: number;
}

/** A view-pixel position as a fraction of the picture, measured from its top-left corner. */
export function pixelToFraction(x: number, y: number, n: number): ScreenFraction {
  return { left: (x + 0.5) / n, top: (n - 0.5 - y) / n };
}

/** The reverse of `pixelToFraction`. */
export function fractionToPixel(left: number, top: number, n: number): PixelPosition {
  return { x: left * n - 0.5, y: n - 0.5 - top * n };
}

/**
 * Sky coordinates of a view-pixel position. Good to a small fraction of a pixel across the
 * fields this site shows (at most half a degree), which is all a readout needs.
 */
export function pixelToSky(x: number, y: number, view: ViewFrame): SkyPosition {
  const centre = (view.n - 1) / 2;
  const degreesPerPixel = view.pixel_arcsec / 3600;
  const dec = view.dec + (y - centre) * degreesPerPixel;
  const shrink = Math.max(Math.cos((view.dec * Math.PI) / 180), 1e-6);
  const ra = view.ra - ((x - centre) * degreesPerPixel) / shrink;
  return { ra: ((ra % 360) + 360) % 360, dec: Math.max(-90, Math.min(90, dec)) };
}

export interface ScaleBar {
  /** Length of the bar on the sky. */
  arcminutes: number;
  /** Length of the bar as a fraction of the picture's width. */
  fraction: number;
}

const SCALE_BAR_CHOICES = [1, 2, 5, 10];
const SCALE_BAR_MIN_FRACTION = 0.08;

/** The shortest round length that is still easy to see on a picture `n` pixels wide. */
export function chooseScaleBar(n: number, pixelArcsec: number): ScaleBar {
  const pixelsPerArcminute = 60 / pixelArcsec;
  const arcminutes =
    SCALE_BAR_CHOICES.find((length) => (length * pixelsPerArcminute) / n >= SCALE_BAR_MIN_FRACTION) ??
    SCALE_BAR_CHOICES[SCALE_BAR_CHOICES.length - 1]!;
  return { arcminutes, fraction: (arcminutes * pixelsPerArcminute) / n };
}

/** Keep a number inside a range. */
export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}
