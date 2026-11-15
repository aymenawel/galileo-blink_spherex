/**
 * What is drawn on top of a sky picture: a reticle on every catalogued moving object, the
 * line of its positions across the seasons, and optionally the Gaia stars.
 *
 * The drawing uses the view's own pixel grid (`0..n` in both directions, y down), so a
 * position from the server needs only the half-pixel shift described in `lib/geometry`.
 */
import { useId, useState } from "react";
import type { StarDot } from "../../api/types";
import { markerSpeed } from "../../lib/copy";
import { pixelToFraction } from "../../lib/geometry";
import { positionAt, type DrawnMarker } from "../../lib/markers";

interface SkyOverlayProps {
  /** Width of the view in SPHEREx pixels. */
  n: number;
  markers: readonly DrawnMarker[];
  /** The date whose positions to mark, or `null` for the latest. */
  season: number | null;
  stars?: readonly StarDot[];
  showMarkers?: boolean;
  showStars?: boolean;
  /** Markers can be hovered and focused to read their labels. Off for small previews. */
  interactive?: boolean;
  /** A CSS clip-path, for showing only one side of a split picture. */
  clipPath?: string;
}

/** Reticle radius as a share of the picture's width, so it looks the same at any field of view. */
const SUBJECT_RADIUS = 0.045;
const OTHER_RADIUS = 0.027;

function catalogueLine(drawn: DrawnMarker): string {
  const { marker, alsoKnownAs } = drawn;
  if (marker.catalog && marker.catalog !== "preset") return marker.catalog;
  return alsoKnownAs[0] ?? marker.source ?? "";
}

function speedLine(drawn: DrawnMarker): string {
  return drawn.marker.speed_text ?? markerSpeed(drawn.marker.pm);
}

function describe(drawn: DrawnMarker): string {
  return [drawn.marker.name, catalogueLine(drawn), speedLine(drawn)].filter(Boolean).join(", ");
}

/** Brighter stars get slightly larger dots. Gaia G magnitudes run from about 6 to 18.5 here. */
function starRadius(gmag: number, n: number): number {
  const brightness = Math.max(0, Math.min(1, (18.5 - gmag) / 10));
  return n * (0.0045 + 0.006 * brightness);
}

interface ReticleProps {
  drawn: DrawnMarker;
  n: number;
  season: number | null;
  interactive: boolean;
  onActive: (active: boolean) => void;
}

function Reticle({ drawn, n, season, interactive, onActive }: ReticleProps) {
  const maskId = useId();
  const { marker } = drawn;
  const position = positionAt(marker, season);
  if (!position) return null;

  const toSvg = (p: { x: number; y: number }) => ({ x: p.x + 0.5, y: n - 0.5 - p.y });
  const centre = toSvg(position);
  const radius = n * (marker.subject ? SUBJECT_RADIUS : OTHER_RADIUS);
  const tick = radius * 0.6;
  const stops = marker.track.map(toSvg);
  const travelled = stops.some((p) => Math.hypot(p.x - centre.x, p.y - centre.y) > radius);

  return (
    <g
      className={marker.subject ? "reticle reticle--subject" : "reticle"}
      tabIndex={interactive ? 0 : undefined}
      role={interactive ? "img" : undefined}
      aria-label={interactive ? describe(drawn) : undefined}
      onPointerEnter={interactive ? () => onActive(true) : undefined}
      onPointerLeave={interactive ? () => onActive(false) : undefined}
      onFocus={interactive ? () => onActive(true) : undefined}
      onBlur={interactive ? () => onActive(false) : undefined}
    >
      {travelled && (
        <>
          {/* The track is cut away inside the ring so it never covers the object itself. */}
          <mask id={maskId} maskUnits="userSpaceOnUse" x={0} y={0} width={n} height={n}>
            <rect width={n} height={n} fill="white" />
            <circle cx={centre.x} cy={centre.y} r={radius} fill="black" />
          </mask>
          <g mask={`url(#${maskId})`}>
            <polyline className="reticle__track" points={stops.map((p) => `${p.x},${p.y}`).join(" ")} />
            {stops.map((p, i) => (
              <circle key={i} className="reticle__stop" cx={p.x} cy={p.y} r={n * 0.005} />
            ))}
          </g>
        </>
      )}
      <circle className="reticle__ring" cx={centre.x} cy={centre.y} r={radius} />
      <path
        className="reticle__ticks"
        d={`M${centre.x} ${centre.y - radius}v${-tick}M${centre.x} ${centre.y + radius}v${tick}M${centre.x - radius} ${centre.y}h${-tick}M${centre.x + radius} ${centre.y}h${tick}`}
      />
      {interactive && <circle className="reticle__hit" cx={centre.x} cy={centre.y} r={radius + tick} />}
    </g>
  );
}

export function SkyOverlay({
  n,
  markers,
  season,
  stars = [],
  showMarkers = true,
  showStars = false,
  interactive = false,
  clipPath,
}: SkyOverlayProps) {
  const [active, setActive] = useState<DrawnMarker | null>(null);
  const activePosition = active ? positionAt(active.marker, season) : undefined;
  const labelAt = activePosition ? pixelToFraction(activePosition.x, activePosition.y, n) : null;

  return (
    <div className="overlay" style={clipPath ? { clipPath } : undefined}>
      <svg
        className="overlay__drawing"
        viewBox={`0 0 ${n} ${n}`}
        preserveAspectRatio="none"
        role={interactive ? "group" : undefined}
        aria-label={interactive ? "Catalogued moving objects" : undefined}
        aria-hidden={interactive ? undefined : true}
      >
        {showStars &&
          stars.map(([x, y, gmag], i) => (
            <circle key={i} className="overlay__star" cx={x + 0.5} cy={n - 0.5 - y} r={starRadius(gmag, n)} />
          ))}
        {showMarkers &&
          markers.map((drawn, i) => (
            <Reticle
              key={`${i}-${drawn.marker.name}`}
              drawn={drawn}
              n={n}
              season={season}
              interactive={interactive}
              onActive={(on) => setActive((current) => (on ? drawn : current === drawn ? null : current))}
            />
          ))}
      </svg>
      {showMarkers && active && labelAt && (
        <div
          className={`marker-label${labelAt.top < 0.25 ? " marker-label--below" : ""}${
            labelAt.left > 0.68 ? " marker-label--left" : labelAt.left < 0.32 ? " marker-label--right" : ""
          }`}
          style={{ left: `${labelAt.left * 100}%`, top: `${labelAt.top * 100}%` }}
          aria-hidden="true"
        >
          <strong>{active.marker.name}</strong>
          {catalogueLine(active) && <span>{catalogueLine(active)}</span>}
          <span className="marker-label__speed">{speedLine(active)}</span>
        </div>
      )}
    </div>
  );
}
