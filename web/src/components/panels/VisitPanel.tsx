/** "What you're looking at" for an asteroid view: the place, the camera, and how long the visit lasted. */
import type { View } from "../../api/types";
import { CAMERA_BANDS, toCameraKey } from "../../lib/cameras";
import { COPY, VISIT_COPY } from "../../lib/copy";
import { formatCount, formatDec, formatDegrees, formatField, formatRa, microns } from "../../lib/format";
import { Panel } from "./Panel";
import { Readout } from "./Readout";

interface VisitPanelProps {
  view: View;
}

export function VisitPanel({ view }: VisitPanelProps) {
  const words = VISIT_COPY.panel;
  const camera = toCameraKey(view.camera);
  const band = camera ? (view.cameras[camera]?.band ?? CAMERA_BANDS[camera]) : null;
  const first = view.seasons[0];
  const last = view.seasons[view.seasons.length - 1];
  const photosUsed = view.stats?.photos_used;

  return (
    <Panel eyebrow={words.eyebrow} title={view.label ?? words.unnamed} className="subject">
      <p className="subject__kind">{words.kind}</p>
      <p className="muted">{words.explain}</p>

      <dl className="readouts">
        <Readout
          label={COPY.subject.position}
          value={
            <>
              {formatRa(view.ra)}
              <br />
              {formatDec(view.dec)}
            </>
          }
          suffix={`${formatDegrees(view.ra)}, ${formatDegrees(view.dec)}`}
        />
        <Readout label={COPY.subject.field} value={formatField(view.size_deg)} />
        {camera && band && <Readout label={words.camera} value={camera} suffix={microns(band)} />}
        <Readout
          label={words.moments}
          value={formatCount(view.seasons.length)}
          suffix={view.span_hours !== undefined ? words.over(view.span_hours) : undefined}
        />
        {first && <Readout label={words.from} value={first.label} suffix="UTC" />}
        {last && last !== first && <Readout label={words.until} value={last.label} suffix="UTC" />}
        {photosUsed !== undefined && (
          <Readout
            label={COPY.subject.photosUsed}
            value={formatCount(photosUsed)}
            suffix={view.photos_in_archive ? COPY.subject.photosInArchive(view.photos_in_archive) : undefined}
          />
        )}
      </dl>
    </Panel>
  );
}
