/**
 * The spectrum drawn from the photos: brightness against wavelength, one dot per photo,
 * one colour per season. The six camera bands are shaded along the wavelength axis.
 */
import { useState, type PointerEvent } from "react";
import type { Band, BrightnessPoint, CameraKey, QuickSpectrumPoint, View } from "../../api/types";
import { CAMERA_KEYS, seasonColour } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import { formatCount, formatFlux, formatMjd, micron } from "../../lib/format";
import { brightnessScale, type BrightnessScale } from "../../lib/spectrumScale";
import { useElementWidth } from "../../lib/useElementWidth";

interface SpectrumPlotProps {
  view: View;
  bands: Record<CameraKey, Band>;
  /** Photos with a measured brightness and a known wavelength. */
  points: readonly MeasuredPoint[];
  /** The whole-sky map's spectrum here, already in the units of the brightness axis. */
  quick: readonly QuickSpectrumPoint[];
  /** Unit written on the brightness axis. */
  unit: string;
}

export interface MeasuredPoint extends BrightnessPoint {
  wavelength: number;
  flux_mjy: number;
}

const MARGIN = { top: 12, right: 14, bottom: 50, left: 58 };
const HEIGHT = 290;
/** SPHEREx sees 0.75 to 5.0 microns; the axis leaves a little room on both sides. */
const WAVELENGTH_RANGE: Band = [0.68, 5.08];
const WAVELENGTH_TICKS = [1, 2, 3, 4, 5];
/** A camera band narrower than this many pixels is labelled with its number alone. */
const BAND_NAME_NEEDS = 38;
/** The pointer picks up the nearest dot within this many pixels. */
const HOVER_REACH = 16;

/** Tick labels that all carry the same number of decimals, so the axis reads as a ruler. */
function tickLabels(scale: BrightnessScale): string[] {
  if (scale.kind === "log") return scale.ticks.map((tick) => (tick >= 1 ? formatCount(tick) : String(tick)));
  const step = scale.ticks.length > 1 ? scale.ticks[1]! - scale.ticks[0]! : 1;
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  return scale.ticks.map((tick) => (decimals === 0 ? formatCount(tick) : tick.toFixed(decimals)));
}

export function SpectrumPlot({ view, bands, points, quick, unit }: SpectrumPlotProps) {
  const [frame, width] = useElementWidth<HTMLDivElement>(560);
  const [hovered, setHovered] = useState<number | null>(null);

  const quickValues = quick.flatMap((p) => (p.flux_mjy === null ? [] : [p.flux_mjy]));
  const scale = brightnessScale([...points.map((p) => p.flux_mjy), ...quickValues]);
  if (!scale) return null;

  const labels = tickLabels(scale);
  const plotWidth = Math.max(120, width - MARGIN.left - MARGIN.right);
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const bottom = MARGIN.top + plotHeight;
  const x = (wavelength: number) =>
    MARGIN.left + ((wavelength - WAVELENGTH_RANGE[0]) / (WAVELENGTH_RANGE[1] - WAVELENGTH_RANGE[0])) * plotWidth;
  const y = (flux: number) => bottom - scale.position(flux) * plotHeight;
  const belowAxis = (flux: number) => scale.kind === "log" && flux <= scale.low;

  const nearest = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - box.left;
    const py = event.clientY - box.top;
    let best: number | null = null;
    let reach = HOVER_REACH;
    points.forEach((p, i) => {
      const distance = Math.hypot(x(p.wavelength) - px, y(p.flux_mjy) - py);
      if (distance < reach) {
        reach = distance;
        best = i;
      }
    });
    setHovered(best);
  };

  const active = hovered === null ? undefined : points[hovered];
  const quickLine = quick
    .filter((p): p is QuickSpectrumPoint & { flux_mjy: number } => p.flux_mjy !== null && !belowAxis(p.flux_mjy))
    .sort((a, b) => a.wavelength - b.wavelength)
    .map((p) => `${x(p.wavelength)},${y(p.flux_mjy)}`)
    .join(" ");

  return (
    <figure className="plot plot--spectrum" ref={frame}>
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={COPY.spectrum.plotAlt(points.length)}
        onPointerMove={nearest}
        onPointerLeave={() => setHovered(null)}
      >
        <rect className="plot__frame" x={MARGIN.left} y={MARGIN.top} width={plotWidth} height={plotHeight} rx={10} />

        {CAMERA_KEYS.map((key) => {
          const [low, high] = bands[key];
          return (
            <g key={key}>
              {/* Every other camera's range is shaded, so the six ranges read as six. */}
              <rect x={x(low)} y={MARGIN.top} width={x(high) - x(low)} height={plotHeight} fill="#fff" opacity={Number(key) % 2 ? 0.035 : 0} />
              <text className="plot__band" x={(x(low) + x(high)) / 2} y={bottom + 17} textAnchor="middle">
                {x(high) - x(low) >= BAND_NAME_NEEDS ? COPY.spectrum.bandName(key) : key}
              </text>
            </g>
          );
        })}

        {scale.ticks.map((tick, i) => (
          <g key={tick}>
            <line className="plot__grid" x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={y(tick)} y2={y(tick)} />
            <text className="plot__tick" x={MARGIN.left - 8} y={y(tick) + 4} textAnchor="end">
              {labels[i]}
            </text>
          </g>
        ))}
        {WAVELENGTH_TICKS.map((tick) => (
          <text key={tick} className="plot__tick" x={x(tick)} y={bottom + 31} textAnchor="middle">
            {COPY.spectrum.wavelengthTick(tick)}
          </text>
        ))}
        <text className="plot__axis" x={MARGIN.left + plotWidth / 2} y={HEIGHT - 4} textAnchor="middle">
          {COPY.spectrum.axisWavelength}
        </text>
        <text className="plot__axis" x={13} y={MARGIN.top + plotHeight / 2} textAnchor="middle" transform={`rotate(-90 13 ${MARGIN.top + plotHeight / 2})`}>
          {COPY.spectrum.axisBrightness(unit)}
        </text>

        {quickLine && <polyline className="plot__quick" points={quickLine} />}

        {points.map((p, i) => {
          const colour = seasonColour(p.season);
          const cx = x(p.wavelength);
          if (belowAxis(p.flux_mjy)) {
            return <path key={i} d={`M${cx - 3.5} ${bottom - 8}h7l-3.5 6z`} fill={colour} opacity={0.75} />;
          }
          return (
            <circle
              key={i}
              className={i === hovered ? "plot__dot plot__dot--active" : "plot__dot"}
              cx={cx}
              cy={y(p.flux_mjy)}
              r={i === hovered ? 5.5 : 3.6}
              fill={p.status === "partial" ? "var(--panel)" : colour}
              stroke={colour}
            />
          );
        })}
      </svg>

      {active && (
        <div
          className={`plot__tip mono${x(active.wavelength) > width * 0.6 ? " plot__tip--left" : ""}`}
          style={{ left: x(active.wavelength), top: Math.max(MARGIN.top, y(active.flux_mjy)) }}
          aria-hidden="true"
        >
          <strong>{formatFlux(active.flux_mjy)}</strong>
          <span>{micron(active.wavelength)}</span>
          <span>
            {COPY.cameras.camera(String(active.camera))} · {formatMjd(active.mjd)}
          </span>
          {active.status === "partial" && <span className="plot__tip-note">{COPY.spectrum.statusNote.partial}</span>}
        </div>
      )}

      <figcaption className="plot__legend">
        {view.seasons
          .filter((season) => points.some((p) => p.season === season.index))
          .map((season) => (
            <span key={season.index} className="legend legend--dot" style={{ color: seasonColour(season.index) }}>
              <span>{season.label}</span>
            </span>
          ))}
        {quickLine && <span className="legend legend--quick">{COPY.spectrum.quickLegend}</span>}
        {scale.kind === "log" && <span className="plot__legend-note muted">{COPY.spectrum.logNote}</span>}
        {points.some((p) => belowAxis(p.flux_mjy)) && <span className="plot__legend-note muted">{COPY.spectrum.belowAxis}.</span>}
      </figcaption>
    </figure>
  );
}
