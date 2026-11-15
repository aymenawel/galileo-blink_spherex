/** The plain-language explainer: every step from NASA's archive to the blink, and the limits. */
import { useAbout } from "../api/useResource";
import type { CameraKey } from "../api/types";
import { CAMERA_TABLE, FLAGS_TABLE, HOW_IT_WORKS_INTRO, LIMITS, SECTIONS, type Section } from "../content/howItWorks";
import { CAMERA_BANDS, CAMERA_KEYS } from "../lib/cameras";
import { COPY } from "../lib/copy";
import { microns } from "../lib/format";

function CameraTable() {
  const about = useAbout();
  const bandOf = (key: CameraKey) => (about.status === "ready" ? about.data.cameras[key] : undefined) ?? CAMERA_BANDS[key];
  return (
    <table className="doc-table">
      <caption className="visually-hidden">{CAMERA_TABLE.caption}</caption>
      <thead>
        <tr>
          <th scope="col">{CAMERA_TABLE.camera}</th>
          <th scope="col">{CAMERA_TABLE.band}</th>
        </tr>
      </thead>
      <tbody>
        {CAMERA_KEYS.map((key) => (
          <tr key={key}>
            <th scope="row">{COPY.cameras.camera(key)}</th>
            <td>{microns(bandOf(key))}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FlagsTable() {
  const about = useAbout();
  if (about.status === "loading") return <p className="muted">{FLAGS_TABLE.loading}</p>;
  if (about.status === "failed") return <p className="note">{FLAGS_TABLE.failed}</p>;
  return (
    <div className="doc-table__scroll">
      <table className="doc-table">
        <thead>
          <tr>
            <th scope="col">{FLAGS_TABLE.flag}</th>
            <th scope="col">{FLAGS_TABLE.meaning}</th>
            <th scope="col">{FLAGS_TABLE.treatment}</th>
          </tr>
        </thead>
        <tbody>
          {about.data.flags.map((flag) => (
            <tr key={flag.name}>
              <th scope="row">
                {flag.name}
              </th>
              <td>{flag.meaning}</td>
              <td className={flag.treated_as_no_data ? "doc-table__blank" : "muted"}>
                {flag.treated_as_no_data ? FLAGS_TABLE.blank : FLAGS_TABLE.kept}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocSection({ section }: { section: Section }) {
  return (
    <section className="doc-section" id={section.id} aria-labelledby={`${section.id}-title`}>
      <div className="doc-section__body">
        <h2 className="doc-section__title" id={`${section.id}-title`}>
          {section.title}
        </h2>
        {section.paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        {section.definitions && (
          <dl className="definitions">
            {section.definitions.map((definition) => (
              <div key={definition.term} className="definitions__item">
                <dt>{definition.term}</dt>
                <dd>{definition.meaning}</dd>
              </div>
            ))}
          </dl>
        )}
        {section.id === "cameras" && <CameraTable />}
        {section.id === "flags" && <FlagsTable />}
      </div>
    </section>
  );
}

export function HowItWorksPage() {
  const { title } = HOW_IT_WORKS_INTRO;
  return (
    <div className="page doc">
      <header className="doc__head">
        <h1 className="doc__title">
          {title.before}
          {title.emphasis}
          {title.after}
        </h1>
        <p className="doc__lede">
          {HOW_IT_WORKS_INTRO.lede}
        </p>
      </header>

      {SECTIONS.map((section) => (
        <DocSection key={section.id} section={section} />
      ))}

      <section className="limits" id={LIMITS.id} aria-labelledby="limits-title">
        <h2 className="limits__title" id="limits-title">
          {LIMITS.title}
        </h2>
        <p className="limits__lede">{LIMITS.lede}</p>
        <ul className="limits__list">
          {LIMITS.items.map((limit) => (
            <li key={limit.title} className="limits__item">
              <h3>{limit.title}</h3>
              <p>{limit.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
