/** The plain-language explainer: every step from NASA's archive to the blink, and the limits. */
import { useAbout } from "../api/useResource";
import type { CameraKey } from "../api/types";
import { CAMERA_TABLE, FLAGS_TABLE, HOW_IT_WORKS_INTRO, LIMITS, SECTIONS, type Section } from "../content/howItWorks";
import { CAMERA_BANDS, CAMERA_COLOURS, CAMERA_KEYS } from "../lib/cameras";
import { COPY } from "../lib/copy";
import { microns } from "../lib/format";
import { riseOrder } from "../lib/stagger";

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
            <th scope="row">
              <span className="camera-dot" style={{ background: CAMERA_COLOURS[key] }} aria-hidden="true" />
              {COPY.cameras.camera(key)}
            </th>
            <td className="mono">{microns(bandOf(key))}</td>
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
              <th scope="row" className="mono">
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

function DocSection({ section, number }: { section: Section; number: number }) {
  return (
    <section className="doc-section" id={section.id} aria-labelledby={`${section.id}-title`}>
      <p className="doc-section__number mono" aria-hidden="true">
        {String(number).padStart(2, "0")}
      </p>
      <div className="doc-section__body">
        <h2 className="doc-section__title display" id={`${section.id}-title`}>
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
        <p className="eyebrow rise" style={riseOrder(0)}>
          {HOW_IT_WORKS_INTRO.eyebrow}
        </p>
        <h1 className="doc__title display rise" style={riseOrder(1)}>
          {title.before}
          <em>{title.emphasis}</em>
          {title.after}
        </h1>
        <p className="doc__lede rise" style={riseOrder(2)}>
          {HOW_IT_WORKS_INTRO.lede}
        </p>
      </header>

      {SECTIONS.map((section, i) => (
        <DocSection key={section.id} section={section} number={i + 1} />
      ))}

      <section className="limits" id={LIMITS.id} aria-labelledby="limits-title">
        <p className="eyebrow">{String(SECTIONS.length + 1).padStart(2, "0")}</p>
        <h2 className="limits__title display" id="limits-title">
          {LIMITS.title}
        </h2>
        <p className="muted limits__lede">{LIMITS.lede}</p>
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
