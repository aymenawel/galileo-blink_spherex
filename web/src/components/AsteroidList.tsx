/**
 * The ready-made asteroid examples as cards, each blinking through its visit, plus a box
 * to find any other asteroid by name.
 */
import { ArrowUpRight, LoaderCircle, Orbit } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { AsteroidExample } from "../api/types";
import { useAsteroids } from "../api/useResource";
import { useReadyView } from "../api/useView";
import { VISIT_COPY } from "../lib/copy";
import { exploreAddress } from "../lib/exploreAddress";
import { riseOrder } from "../lib/stagger";
import { Link, navigate } from "../router";
import { BlinkPreview } from "./viewport/BlinkPreview";

const words = VISIT_COPY.home;
/** Fainter than this, an asteroid is a real test of the search. */
const FAINT_VMAG = 16;

function AsteroidCard({ asteroid, order }: { asteroid: AsteroidExample; order: number }) {
  const view = useReadyView(asteroid.ready ? asteroid.key : null);
  return (
    <Link to={exploreAddress({ kind: "asteroid", id: asteroid.id })} className="target-card rise" style={riseOrder(order)}>
      <div className="target-card__thumb">
        {view ? <BlinkPreview view={view} beat={700} /> : <div className="sky target-card__placeholder" aria-hidden="true" />}
      </div>
      <div className="target-card__text">
        <p className="eyebrow">{asteroid.vmag >= FAINT_VMAG ? words.faintNote : words.magnitude(asteroid.vmag)}</p>
        <h3 className="target-card__name display">{asteroid.name}</h3>
        <p className="muted">{asteroid.blurb}</p>
        <p className="target-card__foot">
          <span className="chip chip--ember">{`camera ${asteroid.camera}`}</span>
          <span className="target-card__open">
            {asteroid.ready ? words.open : words.building}
            <ArrowUpRight size={16} aria-hidden="true" />
          </span>
        </p>
      </div>
    </Link>
  );
}

/** Find any asteroid by name: NASA's moving-object search says where SPHEREx caught it. */
function AsteroidSearch() {
  const [text, setText] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const name = text.trim();
    if (!name) {
      setProblem(words.searchEmpty);
      return;
    }
    setProblem(null);
    navigate(exploreAddress({ kind: "asteroidName", name }));
  };

  return (
    <form className="search search--compact asteroid-search" role="search" onSubmit={submit} noValidate>
      <div className="search__field">
        <Orbit className="search__icon" size={18} aria-hidden="true" />
        <input
          className="search__input"
          type="text"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          value={text}
          placeholder={words.searchPlaceholder}
          aria-label={words.searchLabel}
          aria-invalid={problem ? true : undefined}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit" className="pill pill--primary search__submit">
          {words.searchSubmit}
        </button>
      </div>
      {problem && (
        <p className="search__problem" role="alert">
          {problem}
        </p>
      )}
    </form>
  );
}

export function AsteroidList() {
  const asteroids = useAsteroids();

  if (asteroids.status === "failed") {
    return (
      <p className="note" role="alert">
        {words.failed}
      </p>
    );
  }
  return (
    <>
      <div className="target-list" aria-busy={asteroids.status === "loading"}>
        {asteroids.status === "loading"
          ? Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="target-card target-card--loading" aria-hidden="true">
                <LoaderCircle className="spin" size={18} />
              </div>
            ))
          : asteroids.data.map((asteroid, i) => <AsteroidCard key={asteroid.id} asteroid={asteroid} order={i} />)}
      </div>
      <AsteroidSearch />
    </>
  );
}
