/**
 * The search box: type a name or coordinates, and it opens the view of that place.
 * The server decides what the text means; anything it cannot understand comes back as a
 * sentence that is shown under the box. The large box also offers the choices that go with
 * a place: months or hours between pictures, how much sky, and which camera.
 */
import { LoaderCircle, Search } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { ApiError, resolvePlace, type ViewRequest } from "../../api/client";
import type { ResolvedPlace } from "../../api/types";
import { COPY, movedNote } from "../../lib/copy";
import { DEFAULT_FIELD, DEFAULT_VISIT_FIELD, FIELD_CHOICES, exploreAddress } from "../../lib/exploreAddress";
import { navigate } from "../../router";
import { SearchSettings, type TimeScale } from "./SearchSettings";

interface SearchBoxProps {
  size: "large" | "compact";
  /** Text to start with, such as the name of the place on screen. */
  initialText?: string;
}

/** What the Explore page is told about a search, beyond what belongs in a shareable address. */
export interface SearchArrival {
  note: string;
}

interface Choices {
  scale: TimeScale;
  field: number;
  camera: number | null;
}

/** What to call the object that moved: its name if one was typed or it is a test target. */
function movedName(place: ResolvedPlace): string {
  return place.kind === "name" || place.target_id ? place.label : (place.follows ?? "");
}

/** The view to open for a place, given the visitor's choices. */
function requestFor(place: ResolvedPlace, choices: Choices): ViewRequest {
  if (choices.scale === "visit") {
    return { kind: "visit", ra: place.ra, dec: place.dec, size: choices.field, ...(choices.camera ? { camera: choices.camera } : {}) };
  }
  // NASA's test targets have a ready-made view, unless another field of view was asked for.
  if (place.target_id && choices.field === DEFAULT_FIELD) return { kind: "target", id: place.target_id };
  return { kind: "place", ra: place.ra, dec: place.dec, size: choices.field };
}

function openPlace(place: ResolvedPlace, choices: Choices): void {
  const arrival: SearchArrival | null =
    place.moved_arcmin !== null && place.moved_arcmin > 0
      ? { note: movedNote(movedName(place), place.moved_arcmin, place.kind === "name") }
      : null;
  const named = place.kind === "name" || place.target_id ? place.label : null;
  navigate(exploreAddress(requestFor(place, choices), named), { state: arrival });
}

export function SearchBox({ size, initialText = "" }: SearchBoxProps) {
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [choices, setChoices] = useState<Choices>({ scale: "looks", field: DEFAULT_FIELD, camera: null });
  const problemId = useId();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const query = text.trim();
    if (busy) return;
    if (!query) {
      setProblem(COPY.search.empty);
      return;
    }
    setBusy(true);
    setProblem(null);
    resolvePlace(query)
      .then(
        (place) => openPlace(place, choices),
        (cause: unknown) => setProblem(cause instanceof ApiError ? cause.message : COPY.errors.unexpected),
      )
      .finally(() => setBusy(false));
  };

  // Asteroids cross a narrow view in hours, so switching the time scale also changes the usual width.
  const setScale = (scale: TimeScale) =>
    setChoices((current) => ({
      ...current,
      scale,
      field:
        current.field === (scale === "visit" ? DEFAULT_FIELD : DEFAULT_VISIT_FIELD)
          ? scale === "visit"
            ? DEFAULT_VISIT_FIELD
            : DEFAULT_FIELD
          : current.field,
    }));

  return (
    <form className={`search search--${size}`} role="search" onSubmit={submit} noValidate>
      <div className="search__field">
        <Search className="search__icon" size={size === "large" ? 22 : 18} aria-hidden="true" />
        <input
          className="search__input"
          type="text"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          value={text}
          placeholder={COPY.search.placeholder}
          aria-label={COPY.search.label}
          aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? problemId : undefined}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit" className="button button--primary search__submit" disabled={busy}>
          {busy ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : null}
          <span>{busy ? COPY.search.busy : COPY.search.submit}</span>
        </button>
      </div>
      {problem && (
        <p className="search__problem" id={problemId} role="alert">
          {problem}
        </p>
      )}
      {size === "large" && (
        <SearchSettings
          scale={choices.scale}
          size={choices.field}
          camera={choices.camera}
          sizes={FIELD_CHOICES}
          onScale={setScale}
          onSize={(field) => setChoices((current) => ({ ...current, field }))}
          onCamera={(camera) => setChoices((current) => ({ ...current, camera }))}
        />
      )}
    </form>
  );
}
