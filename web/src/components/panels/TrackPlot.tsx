/**
 * The object's path across the sky: the catalogue's prediction as a line (with the yearly
 * parallax wobble), and where each look actually found it as dots with error bars.
 * North is up and east is to the left, as in the pictures; both axes share one scale.
 */
import type { CameraKey, View } from "../../api/types";
import { COPY } from "../../lib/copy";
import { arcsec } from "../../lib/format";
import { niceTicks } from "../../lib/ticks";
import { measuredPositions, type Offset } from "../../lib/trackPlot";
import { useElementWidth } from "../../lib/useElementWidth";

interface TrackPlotProps {
  view: View;
  /** The camera whose measured positions to draw. */
  camera: CameraKey;
}

const MARGIN = { top: 10, right: 12, bottom: 40, left: 46 };
/** The plot never zooms in further than this half-width, in arcseconds, so noise is not blown up. */
const MIN_HALF_SPAN = 1.2;
const MAX_SIDE = 320;
/** Room the "1 SPHEREx pixel" label needs, in pixels. */
const PIXEL_LABEL_WIDTH = 96;
/** Labels of dots closer together than this many pixels would overlap, so they are left off. */
const LABEL_CLEARANCE = 30;

export function TrackPlot({ view, camera }: TrackPlotProps) {
  const [frame, width] = useElementWidth<HTMLDivElement>(360);
  const path = view.path ?? [];
  const points = measuredPositions(path, view.track?.[camera] ?? []);
  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";

  // One scale for both axes, centred on everything that will be drawn.
  const easts = [0, ...path.map((p) => p.east), ...points.flatMap((p) => [p.east - p.error, p.east + p.error])];
  const norths = [0, ...path.map((p) => p.north), ...points.flatMap((p) => [p.north - p.error, p.north + p.error])];
  const centre: Offset = {
    east: (Math.min(...easts) + Math.max(...easts)) / 2,
    north: (Math.min(...norths) + Math.max(...norths)) / 2,
  };
  const half = Math.max(
    MIN_HALF_SPAN,
    ((Math.max(...easts) - Math.min(...easts)) / 2) * 1.18,
    ((Math.max(...norths) - Math.min(...norths)) / 2) * 1.18,
  );

  const side = Math.max(140, Math.min(MAX_SIDE, width - MARGIN.left - MARGIN.right));
  const height = side + MARGIN.top + MARGIN.bottom;
  const left = Math.max(MARGIN.left, (width - side) / 2);
  // East grows to the LEFT on the sky, so the horizontal axis is reversed.
  const x = (east: number) => left + ((centre.east + half - east) / (2 * half)) * side;
  const y = (north: number) => MARGIN.top + ((centre.north + half - north) / (2 * half)) * side;
  const scale = side / (2 * half);

  const eastTicks = niceTicks(centre.east - half, centre.east + half, 4);
  const northTicks = niceTicks(centre.north - half, centre.north + half, 4);
  const pixel = view.pixel_arcsec;
  const showPixelBox = half * 2 > pixel * 0.7;
  // The box's label goes in whichever of its left corners is inside the plot, or nowhere.
  const pixelLabel = [
    { x: x(pixel / 2) + 6, y: y(-pixel / 2) - 6 },
    { x: x(pixel / 2) + 6, y: y(pixel / 2) + 14 },
  ].find((at) => at.x > left && at.x < left + side - PIXEL_LABEL_WIDTH && at.y > MARGIN.top + 10 && at.y < MARGIN.top + side);

  const isCrowded = (index: number) =>
    points.some(
      (other, i) =>
        i !== index && Math.hypot(x(other.east) - x(points[index]!.east), y(other.north) - y(points[index]!.north)) < LABEL_CLEARANCE,
    );

  return (
    <figure className="plot" ref={frame}>
      <svg width={width} height={height} role="img" aria-label={COPY.motion.plotAlt(points.length, camera)}>
        <defs>
          <clipPath id={`track-clip-${view.key}`}>
            <rect x={left} y={MARGIN.top} width={side} height={side} />
          </clipPath>
        </defs>

        <rect className="plot__frame" x={left} y={MARGIN.top} width={side} height={side} rx={10} />

        {eastTicks.map((tick) => (
          <g key={`e${tick}`}>
            <line className="plot__grid" x1={x(tick)} x2={x(tick)} y1={MARGIN.top} y2={MARGIN.top + side} />
            <text className="plot__tick" x={x(tick)} y={MARGIN.top + side + 15} textAnchor="middle">
              {tick}
            </text>
          </g>
        ))}
        {northTicks.map((tick) => (
          <g key={`n${tick}`}>
            <line className="plot__grid" x1={left} x2={left + side} y1={y(tick)} y2={y(tick)} />
            <text className="plot__tick" x={left - 8} y={y(tick) + 4} textAnchor="end">
              {tick}
            </text>
          </g>
        ))}
        <text className="plot__axis" x={left + side / 2} y={height - 6} textAnchor="middle">
          {COPY.motion.axisEast}
        </text>
        <text className="plot__axis" x={12} y={MARGIN.top + side / 2} textAnchor="middle" transform={`rotate(-90 12 ${MARGIN.top + side / 2})`}>
          {COPY.motion.axisNorth}
        </text>

        <g clipPath={`url(#track-clip-${view.key})`}>
          {showPixelBox && (
            <>
              <rect
                className="plot__pixel"
                x={x(pixel / 2)}
                y={y(pixel / 2)}
                width={pixel * scale}
                height={pixel * scale}
              />
              {pixelLabel && (
                <text className="plot__pixel-label" x={pixelLabel.x} y={pixelLabel.y}>
                  {COPY.motion.pixelBox}
                </text>
              )}
            </>
          )}

          {path.length > 1 && (
            <polyline className="plot__path" points={path.map((p) => `${x(p.east)},${y(p.north)}`).join(" ")} />
          )}

          {points.map((p) => (
            <g key={p.season}>
              <circle className="plot__expected" cx={x(p.predicted.east)} cy={y(p.predicted.north)} r={3.5} />
              <line className="plot__error" x1={x(p.east - p.error)} x2={x(p.east + p.error)} y1={y(p.north)} y2={y(p.north)} />
              <line className="plot__error" x1={x(p.east)} x2={x(p.east)} y1={y(p.north - p.error)} y2={y(p.north + p.error)} />
              <circle className="plot__measured" cx={x(p.east)} cy={y(p.north)} r={4}>
                <title>{`${labelOf(p.season)}: measured ± ${arcsec(p.error, 2)}`}</title>
              </circle>
            </g>
          ))}
        </g>

        {points.map((p, i) =>
          isCrowded(i) ? null : (
            <text
              key={p.season}
              className="plot__label"
              x={x(p.east) + (x(p.east) > left + side * 0.6 ? -9 : 9)}
              y={y(p.north) + 4}
              textAnchor={x(p.east) > left + side * 0.6 ? "end" : "start"}
            >
              {labelOf(p.season)}
            </text>
          ),
        )}
      </svg>

      <figcaption className="plot__legend">
        <span className="legend legend--path">{COPY.motion.legendPredicted}</span>
        <span className="legend legend--measured">{COPY.motion.legendMeasured}</span>
        {points.length === 0 && <span className="muted">{COPY.motion.plotEmpty(camera)}</span>}
      </figcaption>
    </figure>
  );
}
