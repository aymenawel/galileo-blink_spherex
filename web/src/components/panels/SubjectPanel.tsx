/** "Where and when": the basic facts of this view. */
import type { View } from "../../api/types";
import { COPY } from "../../lib/copy";
import { arcsec, formatCount, formatDate, formatDec, formatDegrees, formatField, formatRa } from "../../lib/format";
import { Panel } from "./Panel";
import { Readout } from "./Readout";

interface SubjectPanelProps {
  view: View;
}

export function SubjectPanel({ view }: SubjectPanelProps) {
  const { subject } = view;
  const kind = subject?.kind ?? "spot";
  const photosUsed = view.stats?.photos_used;
  const catalogueName = !view.target && kind !== "spot" ? subject?.name : null;

  return (
    <Panel title={COPY.subject.title} context={catalogueName ?? undefined} className="subject">
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
        {subject?.pm !== null && subject?.pm !== undefined && kind !== "spot" && (
          <Readout label={COPY.subject.catalogueSpeed} value={arcsec(subject.pm, subject.pm < 1 ? 2 : 1)} suffix={COPY.subject.perYear} />
        )}
        {view.data_through && <Readout label={COPY.subject.dataThrough} value={formatDate(view.data_through)} />}
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
