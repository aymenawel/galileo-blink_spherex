/**
 * The search box: type a name or coordinates, and it opens the view of that place.
 * The server decides what the text means; anything it cannot understand comes back as a
 * sentence that is shown under the box.
 */
import { LoaderCircle, Search } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { ApiError, resolvePlace } from "../../api/client";
import type { ResolvedPlace } from "../../api/types";
import { COPY, movedNote } from "../../lib/copy";
import { DEFAULT_FIELD, exploreAddress } from "../../lib/exploreAddress";
import { navigate } from "../../router";

interface SearchBoxProps {
  size: "large" | "compact";
  /** Text to start with, such as the name of the place on screen. */
  initialText?: string;
}

/** What the Explore page is told about a search, beyond what belongs in a shareable address. */
export interface SearchArrival {
  note: string;
}

/** What to call the object that moved: its name if one was typed or it is a test target. */
function movedName(place: ResolvedPlace): string {
  return place.kind === "name" || place.target_id ? place.label : (place.follows ?? "");
}

function openPlace(place: ResolvedPlace): void {
  const arrival: SearchArrival | null =
    place.moved_arcmin !== null && place.moved_arcmin > 0
      ? { note: movedNote(movedName(place), place.moved_arcmin, place.kind === "name") }
      : null;
  const address = place.target_id
    ? exploreAddress({ kind: "target", id: place.target_id })
    : exploreAddress(
        { kind: "place", ra: place.ra, dec: place.dec, size: DEFAULT_FIELD },
        place.kind === "name" ? place.label : null,
      );
  navigate(address, { state: arrival });
}

export function SearchBox({ size, initialText = "" }: SearchBoxProps) {
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
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
      .then(openPlace, (cause: unknown) => setProblem(cause instanceof ApiError ? cause.message : COPY.errors.unexpected))
      .finally(() => setBusy(false));
  };

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
        <button type="submit" className="pill pill--primary search__submit" disabled={busy}>
          {busy ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : null}
          <span>{busy ? COPY.search.busy : COPY.search.submit}</span>
        </button>
      </div>
      {problem && (
        <p className="search__problem" id={problemId} role="alert">
          {problem}
        </p>
      )}
    </form>
  );
}
