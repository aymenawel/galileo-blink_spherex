/** The front page: the whole sky with the search on it, then where to start and how it works. */
import { SkyHero } from "../components/home/SkyHero";
import { AsteroidIndex, TargetIndex } from "../components/SkyIndex";
import { COPY, VISIT_COPY } from "../lib/copy";
import { Link } from "../router";

export function HomePage() {
  return (
    <div className="home">
      <SkyHero />

      <section className="section" id="targets" aria-labelledby="targets-title">
        <header className="section__head">
          <h2 className="section__title" id="targets-title">
            {COPY.home.targetsTitle}
          </h2>
          <p className="section__lede">{COPY.home.targetsLede}</p>
        </header>
        <TargetIndex />
      </section>

      <section className="section" id="asteroids" aria-labelledby="asteroids-title">
        <header className="section__head">
          <h2 className="section__title" id="asteroids-title">
            {VISIT_COPY.home.title}
          </h2>
          <p className="section__lede">{VISIT_COPY.home.lede}</p>
        </header>
        <AsteroidIndex />
      </section>

      <section className="section" aria-labelledby="steps-title">
        <header className="section__head">
          <h2 className="section__title" id="steps-title">
            {COPY.home.stepsTitle}
          </h2>
        </header>
        <ol className="steps">
          {COPY.home.steps.map((step) => (
            <li key={step.title} className="step">
              <h3 className="step__title">{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
        <Link to="/how-it-works" className="button button--quiet">
          {COPY.home.stepsMore}
        </Link>
      </section>

      <section className="field-section" aria-labelledby="not-title">
        <h2 className="section__title" id="not-title">
          {COPY.home.notTitle}
        </h2>
        <div>
          <p className="field-section__body">{COPY.home.notBody}</p>
          <Link to="/how-it-works#limits" className="button button--ink">
            {COPY.home.notLink}
          </Link>
        </div>
      </section>
    </div>
  );
}
