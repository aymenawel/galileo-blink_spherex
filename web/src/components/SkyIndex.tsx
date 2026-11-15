/**
 * Lists of ready-made views for the home page. Each row is a link with a small round,
 * blinking picture of the place: the view through an eyepiece. The targets list also shows
 * the row being pointed at in a large eyepiece beside it.
 */
import { useState, type FormEvent } from "react";
import { useAsteroids, useTargets } from "../api/useResource";
import { useReadyView } from "../api/useView";
import { COPY, VISIT_COPY, speedChip } from "../lib/copy";
import { exploreAddress } from "../lib/exploreAddress";
import { Link, navigate } from "../router";
import { BlinkPreview } from "./viewport/BlinkPreview";

interface IndexItem {
  id: string;
  name: string;
  /** One plain sentence about the object. */
  line: string;
  /** A short fact shown at the end of the row. */
  fact: string;
  /** The ready-made view to preview, when it exists. */
  viewKey: string | null;
  to: string;
}

/** A round, blinking picture of a ready-made view, or an empty eyepiece while it loads. */
export function Eyepiece({ viewKey, beat, showDate = false }: { viewKey: string | null; beat: number; showDate?: boolean }) {
  const view = useReadyView(viewKey);
  return (
    <div className="eyepiece">
      {view ? <BlinkPreview view={view} beat={beat} showDate={showDate} /> : <div className="sky" aria-hidden="true" />}
    </div>
  );
}

function IndexRow({ item, beat, active, onActive }: { item: IndexItem; beat: number; active: boolean; onActive: () => void }) {
  return (
    <li>
      <Link to={item.to} className={active ? "index-row is-active" : "index-row"} onPointerEnter={onActive} onFocus={onActive}>
        <span className="index-row__thumb">
          <Eyepiece viewKey={item.viewKey} beat={beat} />
        </span>
        <span className="index-row__text">
          <span className="index-row__name">{item.name}</span>
          <span className="index-row__line">{item.line}</span>
        </span>
        <span className="index-row__fact">{item.fact}</span>
      </Link>
    </li>
  );
}

/** NASA's five test targets: rows of names, with the pointed-at one blinking large beside them. */
export function TargetIndex() {
  const targets = useTargets();
  const [activeId, setActiveId] = useState<string | null>(null);

  if (targets.status === "failed") {
    return (
      <p className="note" role="alert">
        {COPY.home.targetsFailed}
      </p>
    );
  }
  if (targets.status === "loading") return <div className="index index--loading" aria-busy="true" />;

  const items: IndexItem[] = targets.data.map((target) => ({
    id: target.id,
    name: target.name,
    line: target.blurb,
    fact: speedChip(target.pm),
    viewKey: target.ready ? target.key : null,
    to: exploreAddress({ kind: "target", id: target.id }),
  }));
  const active = items.find((item) => item.id === activeId) ?? items[0];

  return (
    <div className="index index--preview">
      <div className="index__preview" aria-hidden="true">
        {active && <Eyepiece key={active.id} viewKey={active.viewKey} beat={800} showDate />}
      </div>
      <ul className="index__rows">
        {items.map((item) => (
          <IndexRow key={item.id} item={item} beat={1000} active={item === active} onActive={() => setActiveId(item.id)} />
        ))}
      </ul>
    </div>
  );
}

/** Find any asteroid by name: NASA's moving-object search says where SPHEREx caught it. */
function AsteroidSearch() {
  const words = VISIT_COPY.home;
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
        <button type="submit" className="button button--primary search__submit">
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

/** The ready-made asteroid examples in two columns, and a box to find any other asteroid. */
export function AsteroidIndex() {
  const words = VISIT_COPY.home;
  const asteroids = useAsteroids();

  if (asteroids.status === "failed") {
    return (
      <p className="note" role="alert">
        {words.failed}
      </p>
    );
  }
  const items: IndexItem[] =
    asteroids.status === "ready"
      ? asteroids.data.map((asteroid) => ({
          id: asteroid.id,
          name: asteroid.name,
          line: asteroid.blurb,
          fact: words.magnitude(asteroid.vmag),
          viewKey: asteroid.ready ? asteroid.key : null,
          to: exploreAddress({ kind: "asteroid", id: asteroid.id }),
        }))
      : [];

  return (
    <div className="index index--columns" aria-busy={asteroids.status === "loading"}>
      <ul className="index__rows">
        {items.map((item) => (
          <IndexRow key={item.id} item={item} beat={700} active={false} onActive={() => undefined} />
        ))}
        <li className="index__search">
          <AsteroidSearch />
        </li>
      </ul>
    </div>
  );
}
