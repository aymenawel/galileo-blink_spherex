/** The bar across the top of the Explore page: name, search, field of view and sharing. */
import { Share2 } from "lucide-react";
import { useCallback, useState } from "react";
import type { ViewRequest } from "../../api/client";
import { COPY, VISIT_COPY } from "../../lib/copy";
import { DEFAULT_FIELD, DEFAULT_VISIT_FIELD, FIELD_CHOICES, exploreAddress } from "../../lib/exploreAddress";
import { formatField } from "../../lib/format";
import { navigate } from "../../router";
import { SearchBox } from "../shell/SearchBox";
import { Toast } from "../shell/Toast";
import { Wordmark } from "../shell/Wordmark";

interface ExploreTopBarProps {
  request: ViewRequest | null;
  /** The name the visitor searched for, when the place is not a test target. */
  name: string | null;
}

async function copyAddress(): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(window.location.href);
    return true;
  } catch {
    return false;
  }
}

export function ExploreTopBar({ request, name }: ExploreTopBarProps) {
  const [toast, setToast] = useState<string | null>(null);
  const clearToast = useCallback(() => setToast(null), []);

  const share = () => {
    void copyAddress().then((copied) => setToast(copied ? COPY.explore.shareDone : COPY.explore.shareFailed));
  };

  // A size the address asks for is offered even when it is not one of the usual choices.
  const sized = request?.kind === "place" || request?.kind === "visit" ? request : null;
  const fields =
    sized && !FIELD_CHOICES.includes(sized.size) ? [...FIELD_CHOICES, sized.size].sort((a, b) => a - b) : FIELD_CHOICES;
  // The same place can be watched over six months (stars) or within one visit (asteroids).
  const switchTo = (kind: "place" | "visit") => {
    if (!sized || sized.kind === kind) return;
    const size = kind === "visit" ? Math.max(sized.size, DEFAULT_VISIT_FIELD) : Math.min(sized.size, DEFAULT_FIELD);
    navigate(exploreAddress({ kind, ra: sized.ra, dec: sized.dec, size }, name));
  };

  return (
    <header className="topbar">
      <Wordmark />
      <SearchBox size="compact" key={name ?? ""} initialText={name ?? ""} />
      <div className="topbar__tools">
        {sized && (
          <div className="segmented segmented--quiet" role="group" aria-label={VISIT_COPY.switch.label}>
            <button type="button" className="segmented__item" aria-pressed={sized.kind === "place"} onClick={() => switchTo("place")}>
              {VISIT_COPY.switch.looks}
            </button>
            <button type="button" className="segmented__item" aria-pressed={sized.kind === "visit"} onClick={() => switchTo("visit")}>
              {VISIT_COPY.switch.visit}
            </button>
          </div>
        )}
        {sized && (
          <label className="topbar__field">
            <span className="eyebrow">{COPY.explore.fieldLabel}</span>
            <select
              className="select"
              value={sized.size}
              onChange={(event) => navigate(exploreAddress({ ...sized, size: Number(event.target.value) }, name))}
            >
              {fields.map((size) => (
                <option key={size} value={size}>
                  {formatField(size)}
                </option>
              ))}
            </select>
          </label>
        )}
        {request && (
          <button type="button" className="pill" onClick={share}>
            <Share2 size={16} aria-hidden="true" />
            {COPY.explore.share}
          </button>
        )}
      </div>
      <Toast message={toast} onDone={clearToast} />
    </header>
  );
}
