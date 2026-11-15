/** The challenge, the team, and credit to everyone whose data and software this site stands on. */
import { ArrowUpRight } from "lucide-react";
import { ABOUT_INTRO, ACKNOWLEDGEMENTS, AI_USE, CHALLENGE, DATA_SOURCES, LIBRARIES, SOURCE, TEAM } from "../content/about";
import { COPY, REPOSITORY_URL } from "../lib/copy";

function NameList({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <div className="credits__group">
      <h3 className="credits__title">{title}</h3>
      <ul className="credits__names">
        {items.map((item) => (
          <li key={item}>
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
        <h1 className="doc__title">
          {title.before}
          {title.emphasis}
          {title.after}
        </h1>
        <p className="doc__lede">
          {ABOUT_INTRO.lede}
        </p>
      </header>

      <div className="about__grid">
        <section className="about__section about__challenge" aria-labelledby="challenge-title">
          <h2 className="doc-section__title" id="challenge-title">
            {CHALLENGE.title}
          </h2>
          {CHALLENGE.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
          <p className="about__tagline">{COPY.brand.tagline}.</p>
        </section>

        <section className="about__section about__team" aria-labelledby="team-title">
          <h2 className="doc-section__title" id="team-title">
            {TEAM.title}
          </h2>
          <p className="about__team-name">{TEAM.name}</p>
          <ul className="about__members">
            {TEAM.members.map((member) => (
              <li key={member}>{member}</li>
            ))}
          </ul>
          <p className="muted">{TEAM.place}</p>
        </section>

        <section className="about__section about__ai" aria-labelledby="ai-title">
          <h2 className="doc-section__title" id="ai-title">
            {AI_USE.title}
          </h2>
          {AI_USE.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </section>

        <section className="about__section about__data" aria-labelledby="data-title">
          <h2 className="doc-section__title" id="data-title">
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

        <section className="about__section about__acknowledgements" aria-labelledby="acknowledgements-title">
          <h2 className="doc-section__title" id="acknowledgements-title">
            {ACKNOWLEDGEMENTS.title}
          </h2>
          <p className="muted">{ACKNOWLEDGEMENTS.note}</p>
          {ACKNOWLEDGEMENTS.items.map((sentence) => (
            <p key={sentence}>{sentence}</p>
          ))}
        </section>

        <section className="about__section about__software" aria-labelledby="software-title">
          <h2 className="doc-section__title" id="software-title">
            {LIBRARIES.title}
          </h2>
          <p className="muted">{LIBRARIES.note}</p>
          <NameList title={LIBRARIES.engine.title} items={LIBRARIES.engine.items} />
          <NameList title={LIBRARIES.site.title} items={LIBRARIES.site.items} />
          <NameList title={LIBRARIES.fonts.title} items={LIBRARIES.fonts.items} />
          <p className="muted">
            {LIBRARIES.full.body}{" "}
            <a href={LIBRARIES.full.href} target="_blank" rel="noreferrer">
              {LIBRARIES.full.link}
            </a>
          </p>
        </section>

        <section className="about__section about__source" aria-labelledby="source-title">
          <h2 className="doc-section__title" id="source-title">
            {SOURCE.title}
          </h2>
          <p className="muted">{SOURCE.body}</p>
          <a className="button button--primary" href={REPOSITORY_URL} target="_blank" rel="noreferrer">
            {SOURCE.link}
            <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </section>
      </div>
    </div>
  );
}
