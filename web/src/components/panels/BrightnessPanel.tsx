/**
 * "Did its brightness change?": each camera's brightness on every date, compared with that
 * camera's first date. Says plainly when nothing can be measured, and how steady ordinary
 * stars look in the same view.
 */
import { Check, Minus } from "lucide-react";
import type { BrightnessChange, CameraBrightnessChange, CameraKey, View } from "../../api/types";
import { CAMERA_KEYS, bandOf, cameraColour } from "../../lib/cameras";
import { COPY, brightnessError, brightnessSentence, brightnessWords, subjectName } from "../../lib/copy";
import { microns } from "../../lib/format";
import { useElementWidth } from "../../lib/useElementWidth";
import { Panel } from "./Panel";

interface BrightnessPanelProps {
  view: View;
}

type Measured = Array<[CameraKey, CameraBrightnessChange]>;

function measuredCameras(change: BrightnessChange): Measured {
  return CAMERA_KEYS.flatMap((key) => {
    const camera = change.cameras[key];
    return camera && camera.points.length > 1 ? [[key, camera] as [CameraKey, CameraBrightnessChange]] : [];
  });
}

/** The words for the view's clearest brightness measurement, or null when there is none. */
export function brightnessHeadline(view: View): { sentence: string; ratio: number; error: number; changed: boolean } | null {
  const best = view.brightness_change?.best;
  if (!best) return null;
  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";
  const key = `${best.camera}` as CameraKey;
  return {
    ratio: best.ratio,
    error: best.error,
    changed: best.changed,
    sentence: brightnessSentence({
      name: subjectName(view),
      first: labelOf(best.first_season),
      last: labelOf(best.last_season),
      camera: best.camera,
      band: microns(bandOf(view.cameras[key], key)),
      ratio: best.ratio,
      error: best.error,
      changed: best.changed,
    }),
  };
}

const MARGIN = { top: 14, right: 16, bottom: 34, left: 58 };
const HEIGHT = 260;
/** The axis always shows at least from two thirds to one and a half times the first date. */
const MIN_SPAN = Math.log(1.5);

/** Each camera's line: brightness against date, on an axis where doubling and halving are equal steps. */
function BrightnessPlot({ view, cameras }: { view: View; cameras: Measured }) {
  const [frame, width] = useElementWidth<HTMLDivElement>(640);
  const seasons = [...new Set(cameras.flatMap(([, camera]) => camera.points.map((p) => p.season)))].sort((a, b) => a - b);
  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";
  const logs = cameras.flatMap(([, camera]) =>
    camera.points.flatMap((p) => [Math.log(Math.max(p.ratio - p.error, 0.05)), Math.log(p.ratio + p.error)]),
  );
  const top = Math.max(MIN_SPAN, ...logs) * 1.08;
  const bottom = Math.min(-MIN_SPAN, ...logs) * 1.08;
  const plotWidth = Math.max(160, width - MARGIN.left - MARGIN.right);
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const x = (season: number) =>
    MARGIN.left + (seasons.length < 2 ? 0.5 : seasons.indexOf(season) / (seasons.length - 1)) * (plotWidth - 40) + 20;
  const y = (ratio: number) => MARGIN.top + ((top - Math.log(Math.max(ratio, 0.05))) / (top - bottom)) * plotHeight;
  const ticks = [0.25, 0.5, 0.67, 1, 1.5, 2, 4].filter((t) => Math.log(t) < top && Math.log(t) > bottom);
  const tickLabel = (t: number) => (t === 1 ? COPY.brightness.same : t > 1 ? `+${Math.round((t - 1) * 100)}%` : `−${Math.round((1 - t) * 100)}%`);

  return (
    <div className="plot brightness__plot" ref={frame}>
      <svg width={width} height={HEIGHT} role="img" aria-label={COPY.brightness.plotAlt(cameras.length)}>
        {ticks.map((t) => (
          <g key={t}>
            <line className={t === 1 ? "plot__expected" : "plot__grid"} x1={MARGIN.left} x2={MARGIN.left + plotWidth} y1={y(t)} y2={y(t)} />
            <text className="plot__tick" x={MARGIN.left - 8} y={y(t) + 4} textAnchor="end">
              {tickLabel(t)}
            </text>
          </g>
        ))}
        {seasons.map((season) => (
          <text key={season} className="plot__tick" x={x(season)} y={HEIGHT - 12} textAnchor="middle">
            {labelOf(season)}
          </text>
        ))}
        {cameras.map(([key, camera], index) => {
          const colour = cameraColour(key);
          // Cameras sit a few pixels apart sideways, so error bars on the same date can be told apart.
          const nudge = (index - (cameras.length - 1) / 2) * 5;
          return (
            <g key={key} stroke={colour} fill={colour}>
              <polyline
                fill="none"
                strokeWidth={1.6}
                points={camera.points.map((p) => `${x(p.season) + nudge},${y(p.ratio)}`).join(" ")}
              />
              {camera.points.map((p) => (
                <g key={p.season}>
                  {p.error > 0 && (
                    <line
                      strokeWidth={1.2}
                      x1={x(p.season) + nudge}
                      x2={x(p.season) + nudge}
                      y1={y(p.ratio + p.error)}
                      y2={y(Math.max(p.ratio - p.error, 0.05))}
                    />
                  )}
                  <circle cx={x(p.season) + nudge} cy={y(p.ratio)} r={4} stroke="none" />
                </g>
              ))}
            </g>
          );
        })}
      </svg>
      <ul className="plot__legend">
        {cameras.map(([key]) => (
          <li key={key}>
            <i style={{ background: cameraColour(key) }} aria-hidden="true" />
            {COPY.brightness.legend(key, microns(bandOf(view.cameras[key], key)))}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BrightnessPanel({ view }: BrightnessPanelProps) {
  const change = view.brightness_change;
  if (!change) return null;
  const cameras = measuredCameras(change);
  const words = COPY.brightness;
  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";

  if (cameras.length === 0) {
    return (
      <Panel title={words.title} context={words.eyebrow} className="brightness">
        <p className="brightness__none">{words.none[change.reason ?? ""] ?? words.noneFallback}</p>
      </Panel>
    );
  }

  const headline = brightnessHeadline(view);
  const verdict = headline && (
    <span className={headline.changed ? "verdict verdict--ok" : "verdict"}>
      {headline.changed ? <Check size={16} aria-hidden="true" /> : <Minus size={16} aria-hidden="true" />}
      {headline.changed ? words.changed : words.steady}
    </span>
  );
  const floors = cameras.flatMap(([, camera]) => (camera.floor_measured && camera.floor !== undefined ? [camera.floor] : []));
  const stars = Math.max(0, ...cameras.map(([, camera]) => camera.n_reference_stars ?? 0));
  const typicalFloor = floors.length > 0 ? [...floors].sort((a, b) => a - b)[Math.floor(floors.length / 2)]! : null;

  return (
    <Panel title={words.title} context={words.eyebrow} className="brightness" aside={verdict}>
      {headline && <p className="brightness__sentence">{headline.sentence}</p>}
      <BrightnessPlot view={view} cameras={cameras} />
      <ul className="spectrum__facts">
        <li>{words.method}</li>
        <li>{typicalFloor !== null ? words.floor(Math.max(1, Math.round(typicalFloor * 100)), stars) : words.floorDefault}</li>
        <li>{words.notProof}</li>
      </ul>
      <details className="disclosure">
        <summary>{words.showNumbers}</summary>
        <div className="numbers__scroll" tabIndex={0} role="group" aria-label={words.numbersLabel}>
          <table className="numbers__table">
            <thead>
              <tr>
                <th scope="col">{words.table.camera}</th>
                <th scope="col">{words.table.dates}</th>
                <th scope="col">{words.table.change}</th>
                <th scope="col">{words.table.verdict}</th>
              </tr>
            </thead>
            <tbody>
              {cameras.flatMap(([key, camera]) =>
                camera.points
                  .filter((p) => p.season !== camera.first_season)
                  .map((p) => (
                    <tr key={`${key}-${p.season}`}>
                      <td>{key}</td>
                      <td>
                        {labelOf(camera.first_season)} → {labelOf(p.season)}
                      </td>
                      <td>
                        {brightnessWords(p.ratio)} ± {brightnessError(p.error)}
                      </td>
                      <td>{p.changed ? words.table.yes : words.table.no}</td>
                    </tr>
                  )),
              )}
            </tbody>
          </table>
        </div>
      </details>
    </Panel>
  );
}
