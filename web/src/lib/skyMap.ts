/**
 * The all-sky map's geometry: a place in the picture to a place in the sky, and back.
 *
 * The picture (web/public/sky/allsky.webp, drawn by scripts/make_sky_map.py) is a Mollweide
 * oval in Galactic coordinates: the centre of the Milky Way in the middle, Galactic longitude
 * growing to the left, the Galaxy's plane along the horizontal axis. Positions in the picture
 * are fractions 0..1 across (left to right) and down (top to bottom). Sky positions are
 * right ascension and declination in degrees (ICRS). Pure arithmetic, no React.
 */

export interface SkyPosition {
  ra: number;
  dec: number;
}

export interface MapPosition {
  /** 0 at the left edge of the picture, 1 at the right. */
  x: number;
  /** 0 at the top edge of the picture, 1 at the bottom. */
  y: number;
}

/** The picture is twice as wide as it is tall. */
export const SKY_MAP_ASPECT = 2;

const SQRT2 = Math.SQRT2;
const DEG = Math.PI / 180;

/** ICRS to Galactic rotation (Hipparcos, ESA 1997). Its transpose goes back. */
const ICRS_TO_GALACTIC = [
  [-0.0548755604162154, -0.873437090234885, -0.4838350155487132],
  [0.4941094278755837, -0.4448296299600112, 0.7469822444972189],
  [-0.8676661490190047, -0.1980763734312015, 0.4559837761750669],
] as const;

function toVector(lonDeg: number, latDeg: number): [number, number, number] {
  const lon = lonDeg * DEG;
  const lat = latDeg * DEG;
  return [Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat)];
}

function fromVector([x, y, z]: readonly [number, number, number]): [number, number] {
  const lon = (((Math.atan2(y, x) / DEG) % 360) + 360) % 360;
  const lat = Math.asin(Math.max(-1, Math.min(1, z))) / DEG;
  return [lon, lat];
}

/** Right ascension and declination to Galactic longitude and latitude, in degrees. */
export function equatorialToGalactic(ra: number, dec: number): { l: number; b: number } {
  const v = toVector(ra, dec);
  const m = ICRS_TO_GALACTIC;
  const [l, b] = fromVector([
    m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
    m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
    m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
  ]);
  return { l, b };
}

/** Galactic longitude and latitude to right ascension and declination, in degrees. */
export function galacticToEquatorial(l: number, b: number): SkyPosition {
  const v = toVector(l, b);
  const m = ICRS_TO_GALACTIC;
  const [ra, dec] = fromVector([
    m[0][0] * v[0] + m[1][0] * v[1] + m[2][0] * v[2],
    m[0][1] * v[0] + m[1][1] * v[1] + m[2][1] * v[2],
    m[0][2] * v[0] + m[1][2] * v[1] + m[2][2] * v[2],
  ]);
  return { ra, dec };
}

/**
 * A point of the picture (fractions 0..1 across and down) to the sky, or null outside the
 * oval. Inverse Mollweide, then Galactic to equatorial.
 */
export function mapToSky(x: number, y: number): SkyPosition | null {
  const mx = (x * 2 - 1) * 2 * SQRT2;
  const my = (1 - y * 2) * SQRT2;
  if ((mx * mx) / 8 + (my * my) / 2 > 1 + 1e-12) return null; // a hair of slack for the rim
  const theta = Math.asin(Math.max(-1, Math.min(1, my / SQRT2)));
  const b = Math.asin(Math.max(-1, Math.min(1, (2 * theta + Math.sin(2 * theta)) / Math.PI))) / DEG;
  const cosTheta = Math.cos(theta);
  // At the very poles every longitude is the same place.
  const east = cosTheta < 1e-12 ? 0 : (Math.PI * mx) / (2 * SQRT2 * cosTheta) / DEG;
  const l = (((-east % 360) + 360) % 360);
  return galacticToEquatorial(l, b);
}

/** A place in the sky to its point in the picture (fractions 0..1 across and down). */
export function skyToMap(ra: number, dec: number): MapPosition {
  const { l, b } = equatorialToGalactic(ra, dec);
  const phi = b * DEG;
  // Mollweide's auxiliary angle: solve 2θ + sin 2θ = π sin φ (Newton's method).
  let theta = phi;
  if (Math.abs(Math.abs(phi) - Math.PI / 2) > 1e-9) {
    for (let i = 0; i < 50; i++) {
      const step = (2 * theta + Math.sin(2 * theta) - Math.PI * Math.sin(phi)) / (2 + 2 * Math.cos(2 * theta));
      theta -= step;
      if (Math.abs(step) < 1e-12) break;
    }
  }
  const lon = ((((l + 180) % 360) + 360) % 360) - 180; // -180..180, centre at 0
  const mx = ((-2 * SQRT2) / Math.PI) * lon * DEG * Math.cos(theta);
  const my = SQRT2 * Math.sin(theta);
  return { x: (mx / (2 * SQRT2) + 1) / 2, y: (1 - my / SQRT2) / 2 };
}
