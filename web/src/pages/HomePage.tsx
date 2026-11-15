/** The front page: what the site does, the search box, a live blink, and where to start. */
import { useTargets } from "../api/useResource";
import { AsteroidIndex, Eyepiece, TargetIndex } from "../components/SkyIndex";
import { SearchBox } from "../components/shell/SearchBox";
import { COPY, VISIT_COPY } from "../lib/copy";
import { exploreAddress } from "../lib/exploreAddress";
import { Link } from "../router";

/** The target blinking in the hero. */
const HERO_TARGET = "barnard";

function HeroPreview() {
  const targets = useTargets();
  const hero = targets.status === "ready" ? targets.data.find((t) => t.id === HERO_TARGET && t.ready) : undefined;

  return (
    <figure className="hero__preview">
      <Eyepiece viewKey={hero?.key ?? null} beat={850} showDate />
      <figcaption>
        {COPY.home.previewCaption}.{" "}
        <Link to={exploreAddress({ kind: "target", id: HERO_TARGET })}>{COPY.home.previewOpen}</Link>
      </figcaption>
    </figure>
  );
}

export function HomePage() {
  return (
    <div className="home">
      <section className="hero">
        <h1 className="hero__headline">{COPY.home.headline}</h1>
        <div className="hero__text">
          <p className="hero__lede">{COPY.home.lede}</p>
          <SearchBox size="large" />
        </div>
        <HeroPreview />
      </section>

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
