/** The front page: what the site does, the search box, a live blink, and where to start. */
import { ArrowRight } from "lucide-react";
import { useTargets } from "../api/useResource";
import { useReadyView } from "../api/useView";
import { AsteroidList } from "../components/AsteroidList";
import { TargetList } from "../components/TargetList";
import { SearchBox } from "../components/shell/SearchBox";
import { Wordmark } from "../components/shell/Wordmark";
import { BlinkPreview } from "../components/viewport/BlinkPreview";
import { COPY, VISIT_COPY } from "../lib/copy";
import { exploreAddress } from "../lib/exploreAddress";
import { riseOrder } from "../lib/stagger";
import { Link } from "../router";

/** The target blinking in the hero, and the camera that shows it best. */
const HERO_TARGET = "barnard";
const HERO_CAMERA = "6";

function HeroPreview() {
  const targets = useTargets();
  const hero = targets.status === "ready" ? targets.data.find((t) => t.id === HERO_TARGET && t.ready) : undefined;
  const view = useReadyView(hero?.key ?? null);

  return (
    <figure className="hero__preview rise" style={riseOrder(3)}>
      <div className="hero__frame">
        {view ? (
          <BlinkPreview view={view} preferCamera={HERO_CAMERA} beat={850} showDate />
        ) : (
          <div className="sky hero__placeholder">
            <span className="sky__empty">{COPY.home.previewLoading}</span>
          </div>
        )}
      </div>
      <figcaption>
        <span className="muted">{COPY.home.previewCaption}</span>
        <Link to={exploreAddress({ kind: "target", id: HERO_TARGET })} className="hero__open">
          {COPY.home.previewOpen}
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </figcaption>
    </figure>
  );
}

export function HomePage() {
  const { headline } = COPY.home;
  return (
    <div className="page home">
      <section className="hero">
        <div className="hero__text">
          <p className="hero__brand rise" style={riseOrder(0)}>
            <Wordmark />
          </p>
          <h1 className="hero__headline display rise" style={riseOrder(1)}>
            {headline.before}
            <em>{headline.emphasis}</em>
            {headline.after}
          </h1>
          <p className="hero__lede rise" style={riseOrder(2)}>
            {COPY.home.lede}
          </p>
          <div className="rise" style={riseOrder(3)}>
            <SearchBox size="large" />
          </div>
        </div>
        <HeroPreview />
      </section>

      <section className="section" id="targets" aria-labelledby="targets-title">
        <header className="section__head">
          <p className="eyebrow">{COPY.home.targetsEyebrow}</p>
          <h2 className="section__title display" id="targets-title">
            {COPY.home.targetsTitle}
          </h2>
          <p className="muted section__lede">{COPY.home.targetsLede}</p>
        </header>
        <TargetList />
      </section>

      <section className="section" id="asteroids" aria-labelledby="asteroids-title">
        <header className="section__head">
          <p className="eyebrow">{VISIT_COPY.home.eyebrow}</p>
          <h2 className="section__title display" id="asteroids-title">
            {VISIT_COPY.home.title}
          </h2>
          <p className="muted section__lede">{VISIT_COPY.home.lede}</p>
        </header>
        <AsteroidList />
      </section>

      <section className="section" aria-labelledby="steps-title">
        <header className="section__head">
          <p className="eyebrow">{COPY.home.stepsEyebrow}</p>
          <h2 className="section__title display" id="steps-title">
            {COPY.home.stepsTitle}
          </h2>
        </header>
        <ol className="steps">
          {COPY.home.steps.map((step, i) => (
            <li key={step.title} className="panel step">
              <span className="step__number mono" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="step__title display">{step.title}</h3>
              <p className="muted">{step.body}</p>
            </li>
          ))}
        </ol>
        <Link to="/how-it-works" className="section__more">
          {COPY.home.stepsMore}
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </section>

      <section className="honesty-strip" aria-labelledby="not-title">
        <h2 className="eyebrow" id="not-title">
          {COPY.home.notTitle}
        </h2>
        <p>{COPY.home.notBody}</p>
        <Link to="/how-it-works#limits" className="pill pill--quiet">
          {COPY.home.notLink}
        </Link>
      </section>
    </div>
  );
}
