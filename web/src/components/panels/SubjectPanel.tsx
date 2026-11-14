/** "What you're looking at": the object or the spot this view watches, and the basic facts of the view. */
import type { View } from "../../api/types";
import { COPY, subjectName } from "../../lib/copy";
import { arcsec, formatCount, formatDate, formatDec, formatDegrees, formatField, formatRa } from "../../lib/format";
import { Panel } from "./Panel";
import { Readout } from "./Readout";

interface SubjectPanelProps {
  view: View;
  /** The name the visitor searched for, when the place is not a test target. */
  searchedName: string | null;
}

export function SubjectPanel({ view, searchedName }: SubjectPanelProps) {
  const { target, subject } = view;
  const kind = subject?.kind ?? "spot";
  const title = target?.name ?? searchedName ?? view.label ?? (kind === "spot" ? COPY.subject.unnamedPlace : subjectName(view));
  const catalogueName = !target && kind !== "spot" && subject?.name && subject.name !== title ? subject.name : null;
  const photosUsed = view.stats?.photos_used;

  return (
    <Panel eyebrow={COPY.subject.title} title={title} className="subject">
      {target ? (
        <>
          <p className="subject__kind">{target.kind}</p>
          <p className="muted">{target.blurb}</p>
        </>
      ) : (
        <p className="muted">
          {COPY.subject.chosen[kind]}
          {catalogueName && <span className="mono subject__catalogue"> {catalogueName}</span>}
        </p>
      )}

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
