/**
 * The whole infrared sky in one picture: NASA's SPHEREx all-sky map, drawn once by
 * scripts/make_sky_map.py and shipped with the site. Pointing at the oval reads off the sky
 * position underneath; a click or tap opens that place. NASA's test targets are marked with
 * small rings that are ordinary links.
 *
 * Every visible word comes from the caller (`words`), so the site's copy stays in one file.
 */
import { useCallback, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import { formatDec, formatRa } from "../lib/format";
import { mapToSky, skyToMap, type SkyPosition } from "../lib/skyMap";
import { Link, navigate } from "../router";

/** The picture, in web/public/sky/. */
const IMAGE_URL = "/sky/allsky.webp";
const IMAGE_WIDTH = 2000;
const IMAGE_HEIGHT = 1000;

export interface SkyMapWords {
  /** Names the map for assistive technology, e.g. "Map of the whole sky". */
  label: string;
  /** The line under the map while nothing is pointed at. */
  hint: string;
  /** The line under the map while pointing at a place: its right ascension and declination. */
  readout: (ra: string, dec: string) => string;
  /** The line under the map while pointing at (or focused on) a marked target. */
  target: (name: string) => string;
}

export interface SkyMapTarget {
  id: string;
  name: string;
  ra: number;
  dec: number;
}

export interface SkyMapProps {
  /** What the picture shows, for readers who cannot see it. */
  alt: string;
  targets: readonly SkyMapTarget[];
  words: SkyMapWords;
}

interface Spot extends SkyPosition {
  /** Fractions across and down the picture. */
  x: number;
  y: number;
}

/** The place under the pointer, or null when it is off the oval. */
function spotAt(event: { clientX: number; clientY: number }, frame: HTMLElement): Spot | null {
  const box = frame.getBoundingClientRect();
  if (box.width === 0 || box.height === 0) return null;
  const x = (event.clientX - box.left) / box.width;
  const y = (event.clientY - box.top) / box.height;
  const sky = mapToSky(x, y);
  return sky ? { x, y, ...sky } : null;
}

/** The Explore address of a place, four decimals each way. */
function placeAddress(ra: number, dec: number): string {
  const r = Number(ra.toFixed(4)) % 360;
  return `/explore?ra=${r.toFixed(4)}&dec=${dec.toFixed(4)}`;
}

export function SkyMap({ alt, targets, words }: SkyMapProps) {
  const frame = useRef<HTMLDivElement>(null);
  const [spot, setSpot] = useState<Spot | null>(null);
  const [focused, setFocused] = useState<string | null>(null);

  const onPointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => {
    if (!frame.current) return;
    setSpot(spotAt(event, frame.current));
  }, []);

  const onClick = useCallback((event: MouseEvent<HTMLDivElement>) => {
    if (!frame.current || event.defaultPrevented) return;
    const here = spotAt(event, frame.current);
    if (here) navigate(placeAddress(here.ra, here.dec));
  }, []);

  const pointedTarget = targets.find((t) => t.id === focused) ?? null;
  let line = words.hint;
  if (pointedTarget) line = words.target(pointedTarget.name);
  else if (spot) line = words.readout(formatRa(spot.ra), formatDec(spot.dec));

  return (
    <figure className="skymap" aria-label={words.label}>
      <div
        ref={frame}
        className={`skymap__frame${spot ? " skymap__frame--on-sky" : ""}`}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setSpot(null)}
        onClick={onClick}
      >
        <img
          className="skymap__image"
          src={IMAGE_URL}
          width={IMAGE_WIDTH}
          height={IMAGE_HEIGHT}
          alt={alt}
          decoding="async"
          loading="lazy"
          draggable={false}
        />

        {spot && !pointedTarget && (
          <span
            className="skymap__ring skymap__ring--pointer"
            style={{ left: `${spot.x * 100}%`, top: `${spot.y * 100}%` }}
            aria-hidden="true"
          />
        )}

        <ul className="skymap__targets">
          {targets.map((target) => {
            const at = skyToMap(target.ra, target.dec);
            const nameOnLeft = at.x > 0.8;
            return (
              <li key={target.id}>
                <Link
                  to={`/explore?target=${encodeURIComponent(target.id)}`}
                  className={`skymap__target${nameOnLeft ? " skymap__target--name-left" : ""}`}
                  style={{ left: `${at.x * 100}%`, top: `${at.y * 100}%` }}
                  onClick={(event) => event.stopPropagation()}
                  onPointerEnter={() => setFocused(target.id)}
                  onPointerLeave={() => setFocused(null)}
                  onFocus={() => setFocused(target.id)}
                  onBlur={() => setFocused(null)}
                >
                  <span className="skymap__ring" aria-hidden="true" />
                  <span className="skymap__name">{target.name}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
      <figcaption className="skymap__readout">
        {line}
      </figcaption>
    </figure>
  );
}
