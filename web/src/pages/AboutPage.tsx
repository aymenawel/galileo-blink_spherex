/** The challenge, the team, and credit to everyone whose data and software this site stands on. */
import { ArrowUpRight } from "lucide-react";
import { ABOUT_INTRO, CHALLENGE, DATA_SOURCES, LIBRARIES, SOURCE, TEAM } from "../content/about";
import { COPY, REPOSITORY_URL } from "../lib/copy";
import { riseOrder } from "../lib/stagger";

function NameList({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <div className="credits__group">
      <h3 className="eyebrow">{title}</h3>
      <ul className="credits__names">
        {items.map((item) => (
          <li key={item} className="chip">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AboutPage() {
  const { title } = ABOUT_INTRO;
  return (
    <div className="page doc about">
      <header className="doc__head">
        <p className="eyebrow rise" style={riseOrder(0)}>
          {ABOUT_INTRO.eyebrow}
        </p>
        <h1 className="doc__title display rise" style={riseOrder(1)}>
          {title.before}
          <em>{title.emphasis}</em>
          {title.after}
        </h1>
        <p className="doc__lede rise" style={riseOrder(2)}>
          {ABOUT_INTRO.lede}
        </p>
      </header>

      <div className="about__grid">
        <section className="panel about__challenge" aria-labelledby="challenge-title">
          <h2 className="panel__title" id="challenge-title">
            {CHALLENGE.title}
          </h2>
          {CHALLENGE.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          <p className="about__tagline display">{COPY.brand.tagline}.</p>
        </section>

        <section className="panel about__team" aria-labelledby="team-title">
          <h2 className="panel__title" id="team-title">
            {TEAM.title}
          </h2>
          <p className="about__team-name display">{TEAM.name}</p>
          <ul className="about__members">
            {TEAM.members.map((member) => (
              <li key={member}>{member}</li>
            ))}
          </ul>
          <p className="muted">{TEAM.place}</p>
        </section>

        <section className="panel about__data" aria-labelledby="data-title">
          <h2 className="panel__title" id="data-title">
            {DATA_SOURCES.title}
          </h2>
          <p className="muted">{DATA_SOURCES.note}</p>
          <dl className="definitions">
            {DATA_SOURCES.items.map((source) => (
              <div key={source.name} className="definitions__item">
                <dt>{source.name}</dt>
                <dd>{source.detail}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="panel about__software" aria-labelledby="software-title">
          <h2 className="panel__title" id="software-title">
            {LIBRARIES.title}
          </h2>
          <p className="muted">{LIBRARIES.note}</p>
          <NameList title={LIBRARIES.engine.title} items={LIBRARIES.engine.items} />
          <NameList title={LIBRARIES.site.title} items={LIBRARIES.site.items} />
          <NameList title={LIBRARIES.fonts.title} items={LIBRARIES.fonts.items} />
        </section>

        <section className="panel about__source" aria-labelledby="source-title">
          <h2 className="panel__title" id="source-title">
            {SOURCE.title}
          </h2>
          <p className="muted">{SOURCE.body}</p>
          <a className="pill pill--primary" href={REPOSITORY_URL} target="_blank" rel="noreferrer">
            {SOURCE.link}
            <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </section>
      </div>
    </div>
  );
}
