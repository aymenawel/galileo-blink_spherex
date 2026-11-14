/** The bar across the top of the Explore page: name, search, field of view and sharing. */
import { Share2 } from "lucide-react";
import { useCallback, useState } from "react";
import type { ViewRequest } from "../../api/client";
import { COPY } from "../../lib/copy";
import { FIELD_CHOICES, exploreAddress } from "../../lib/exploreAddress";
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
  const fields =
    request?.kind === "place" && !FIELD_CHOICES.includes(request.size)
      ? [...FIELD_CHOICES, request.size].sort((a, b) => a - b)
      : FIELD_CHOICES;

  return (
    <header className="topbar">
      <Wordmark />
      <SearchBox size="compact" key={name ?? ""} initialText={name ?? ""} />
      <div className="topbar__tools">
        {request?.kind === "place" && (
          <label className="topbar__field">
            <span className="eyebrow">{COPY.explore.fieldLabel}</span>
            <select
              className="select"
              value={request.size}
              onChange={(event) => navigate(exploreAddress({ ...request, size: Number(event.target.value) }, name))}
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
