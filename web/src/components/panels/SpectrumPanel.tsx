/**
 * "Its colours": the spectrum of the subject, drawn from the same photos as the pictures.
 * States plainly how many photos could not be used and why.
 */
import { useEffect, useState } from "react";
import { fetchQuickSpectrum } from "../../api/client";
import type { Band, BrightnessPoint, CameraKey, QuickSpectrumPoint, View } from "../../api/types";
import { CAMERA_BANDS } from "../../lib/cameras";
import { COPY, brightnessLeftOutSentence, saturatedSentence } from "../../lib/copy";
import { formatFlux, formatMjd, micron, microns } from "../../lib/format";
import { Panel } from "./Panel";
import { SpectrumPlot, type MeasuredPoint } from "./SpectrumPlot";

interface SpectrumPanelProps {
  view: View;
  /** Camera bands from the server, when they have arrived. */
  bands?: Partial<Record<CameraKey, Band>>;
}

type Quick =
  | { state: "idle" | "loading" | "unavailable" | "empty" }
  | { state: "shown"; points: QuickSpectrumPoint[]; unit: string; note: string | null };

const PHOTO_UNIT = "mJy";

function isMeasured(point: BrightnessPoint): point is MeasuredPoint {
  return point.status !== "saturated" && typeof point.flux_mjy === "number" && typeof point.wavelength === "number";
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] ?? 0;
}

/**
 * Put the whole-sky map's spectrum on the photos' brightness axis. When the map uses another
 * unit, only its shape can be compared, so it is scaled to the level of the dots.
 */
function alignQuick(quick: Quick, measured: MeasuredPoint[]): { points: QuickSpectrumPoint[]; unit: string; scaled: boolean } {
  if (quick.state !== "shown") return { points: [], unit: PHOTO_UNIT, scaled: false };
  if (measured.length === 0) return { points: quick.points, unit: quick.unit, scaled: false };
  if (/^mjy$/i.test(quick.unit.trim())) return { points: quick.points, unit: PHOTO_UNIT, scaled: false };
  const level = median(quick.points.flatMap((p) => (p.flux_mjy !== null && p.flux_mjy > 0 ? [p.flux_mjy] : [])));
  const factor = level > 0 ? median(measured.map((p) => p.flux_mjy)) / level : 1;
  return {
    points: quick.points.map((p) => ({ ...p, flux_mjy: p.flux_mjy === null ? null : p.flux_mjy * factor })),
    unit: PHOTO_UNIT,
    scaled: true,
  };
}

/** The camera whose typical reading is highest, when at least two cameras have three readings each. */
function brightestCamera(points: MeasuredPoint[]): number | null {
  const byCamera = new Map<number, number[]>();
  for (const p of points) byCamera.set(p.camera, [...(byCamera.get(p.camera) ?? []), p.flux_mjy]);
  const levels = [...byCamera].filter(([, values]) => values.length >= 3).map(([camera, values]) => [camera, median(values)] as const);
  if (levels.length < 2) return null;
  return levels.reduce((best, level) => (level[1] > best[1] ? level : best))[0];
}

export function SpectrumPanel({ view, bands }: SpectrumPanelProps) {
  const [quick, setQuick] = useState<Quick>({ state: "idle" });
  useEffect(() => setQuick({ state: "idle" }), [view.key]);

  const all = view.brightness ?? [];
  const measured = all.filter(isMeasured).sort((p, q) => p.wavelength - q.wavelength);
  const saturated = all.filter((p) => p.status === "saturated").length;
  const leftOut = view.brightness_left_out ?? 0;
  const aligned = alignQuick(quick, measured);
  const cameraBands = { ...CAMERA_BANDS, ...bands };
  const brightest = brightestCamera(measured);

  const askQuick = () => {
    setQuick({ state: "loading" });
    fetchQuickSpectrum(view.ra, view.dec).then(
      (answer) => {
        const points = (answer.points ?? []).filter((p) => typeof p.wavelength === "number");
        setQuick(
          points.some((p) => p.flux_mjy !== null)
            ? { state: "shown", points, unit: answer.unit ?? PHOTO_UNIT, note: answer.note ?? null }
            : { state: "empty" },
        );
      },
      () => setQuick({ state: "unavailable" }),
    );
  };

  // At an empty spot there is nothing to measure: scattered readings of the background are not a spectrum.
  const isSpot = view.subject?.kind === "spot";
  const emptyReason =
    isSpot && saturated === 0
      ? COPY.spectrum.nothing
      : measured.length > 0
      ? null
      : all.length === 0
        ? view.subject?.kind === "spot"
          ? COPY.spectrum.nothing
          : COPY.spectrum.noneUsable
        : saturated === all.length
          ? COPY.spectrum.allSaturated
          : COPY.spectrum.noneUsable;

  return (
    <Panel title={COPY.spectrum.title} context={COPY.spectrum.eyebrow} className="spectrum">
      {emptyReason && <p className="spectrum__empty">{emptyReason}</p>}

      {((measured.length > 0 && !emptyReason) || aligned.points.length > 0) && (
        <SpectrumPlot view={view} bands={cameraBands} points={emptyReason ? [] : measured} quick={aligned.points} unit={aligned.unit} />
      )}

      {brightest && !emptyReason && <p className="spectrum__reading">{COPY.spectrum.reading(brightest, microns(cameraBands[`${brightest}` as CameraKey]))}</p>}
      {measured.length > 0 && !emptyReason && <p className="muted spectrum__caption">{COPY.spectrum.caption}</p>}

      <ul className="spectrum__facts">
        {measured.some((p) => p.status === "partial") && <li>{COPY.spectrum.hollow}.</li>}
        {saturated > 0 && measured.length > 0 && <li>{saturatedSentence(saturated)}</li>}
        {leftOut > 0 && <li>{brightnessLeftOutSentence(leftOut)}</li>}
        {aligned.scaled && quick.state === "shown" && <li>{COPY.spectrum.quickScaled(quick.unit)}</li>}
        {quick.state === "shown" && quick.note && <li>{quick.note}</li>}
      </ul>

      <div className="spectrum__actions">
        <button type="button" className="button button--quiet" onClick={askQuick} disabled={quick.state === "loading" || quick.state === "shown"}>
          {quick.state === "loading" ? COPY.spectrum.quickLoading : COPY.spectrum.quickButton}
        </button>
        <span className="muted" role="status">
          {quick.state === "unavailable" && COPY.spectrum.quickUnavailable}
          {quick.state === "empty" && COPY.spectrum.quickEmpty}
        </span>
      </div>

      {all.length > 0 && (
        <details className="disclosure">
          <summary>{COPY.spectrum.showNumbers}</summary>
          <div className="numbers__scroll numbers__scroll--tall" tabIndex={0} role="group" aria-label={COPY.spectrum.numbersLabel}>
            <table className="numbers__table">
              <thead>
                <tr>
                  <th scope="col">{COPY.spectrum.table.date}</th>
                  <th scope="col">{COPY.spectrum.table.camera}</th>
                  <th scope="col">{COPY.spectrum.table.wavelength}</th>
                  <th scope="col">{COPY.spectrum.table.brightness}</th>
                  <th scope="col">{COPY.spectrum.table.note}</th>
                </tr>
              </thead>
              <tbody>
                {[...all]
                  .sort((p, q) => (p.wavelength ?? 0) - (q.wavelength ?? 0))
                  .map((p, i) => (
                    <tr key={i}>
                      <td>{formatMjd(p.mjd)}</td>
                      <td>{p.camera}</td>
                      <td>{typeof p.wavelength === "number" ? micron(p.wavelength) : ""}</td>
                      <td>{isMeasured(p) ? formatFlux(p.flux_mjy) : ""}</td>
                      <td>{COPY.spectrum.statusNote[p.status] ?? ""}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </Panel>
  );
}
