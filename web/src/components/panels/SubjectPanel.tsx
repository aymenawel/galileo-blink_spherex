/** "Where and when": the basic facts of this view, and the same place in other public tools. */
import { ArrowUpRight } from "lucide-react";
import type { View } from "../../api/types";
import { COPY } from "../../lib/copy";
import { arcsec, formatCount, formatDate, formatDec, formatDegrees, formatField, formatRa } from "../../lib/format";
import { Panel } from "./Panel";
import { Readout } from "./Readout";

/** The same patch of sky in other free tools, so a finding can be checked against other telescopes. */
function elsewhere(view: View): Array<{ label: string; href: string }> {
  const ra = view.ra.toFixed(5);
  const dec = view.dec.toFixed(5);
  const words = COPY.subject.elsewhereLinks;
  return [
    { label: words.spherex, href: `https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube/?ra=${ra}&dec=${dec}&fov=${view.size_deg}` },
    { label: words.wiseview, href: `http://byw.tools/wiseview#ra=${ra}&dec=${dec}&size=${Math.round(view.size_deg * 3600)}&band=3` },
    { label: words.simbad, href: `https://simbad.cds.unistra.fr/simbad/sim-coo?Coord=${ra}+${dec}&Radius=1&Radius.unit=arcmin` },
    { label: words.legacy, href: `https://www.legacysurvey.org/viewer?ra=${ra}&dec=${dec}&zoom=13` },
  ];
}

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
      <p className="subject__elsewhere-title">{COPY.subject.elsewhere}</p>
      <ul className="subject__elsewhere">
        {elsewhere(view).map((link) => (
          <li key={link.href}>
            <a href={link.href} target="_blank" rel="noreferrer">
              {link.label}
              <ArrowUpRight size={14} aria-hidden="true" />
            </a>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
