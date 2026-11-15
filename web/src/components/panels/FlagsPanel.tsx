/** NASA's quality flags in the look on screen: what was flagged, how much, and what each flag means. */
import type { CameraKey, FlagInfo, View } from "../../api/types";
import { lookAt } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import { formatCount } from "../../lib/format";
import { Panel } from "./Panel";

interface FlagsPanelProps {
  view: View;
  camera: CameraKey;
  /** The date on screen, or `null` when every date is added together. */
  season: number | null;
  /** What each flag means, when the server's list has arrived. */
  flags?: readonly FlagInfo[];
  overlayOn: boolean;
  /** False when the picture on screen is not a single date. */
  overlayAvailable: boolean;
  onToggleOverlay: () => void;
}

/** The commonest flags are listed; the rest are one click away. */
const FLAGS_SHOWN = 4;

export function FlagsPanel({ view, camera, season, flags, overlayOn, overlayAvailable, onToggleOverlay }: FlagsPanelProps) {
  const look = season === null ? undefined : lookAt(view, camera, season);
  const seasonLabel = view.seasons.find((s) => s.index === season)?.label;
  const counts = Object.entries(look?.flag_counts ?? {}).sort(([, a], [, b]) => b - a);
  const infoOf = (name: string) => flags?.find((flag) => flag.name === name);
  const item = ([name, count]: [string, number]) => {
    const info = infoOf(name);
    return (
      <li key={name} className="flags__item">
        <span className="flags__name">
          {name}
          {info?.treated_as_no_data && (
            <span className="flags__blank" title={COPY.flags.noDataTitle}>
              {COPY.flags.noData}
            </span>
          )}
        </span>
        <span className="flags__count">
          {formatCount(count)} <small>{COPY.flags.pixels}</small>
        </span>
        <span className="flags__meaning">{info?.meaning ?? (flags ? COPY.flags.unknown : "")}</span>
      </li>
    );
  };

  return (
    <Panel
      title={COPY.flags.title}
      context={look && seasonLabel ? `${COPY.cameras.camera(camera)} · ${seasonLabel}` : undefined}
      className="flags"
    >
      <p className="muted">{COPY.flags.line}</p>

      <button
        type="button"
        className="button button--quiet flags__toggle"
        aria-pressed={overlayOn && overlayAvailable}
        disabled={!overlayAvailable || !look}
        onClick={onToggleOverlay}
      >
        <span className="flags__swatch" aria-hidden="true" />
        {overlayOn && overlayAvailable ? COPY.flags.hide : COPY.flags.show}
      </button>

      {season === null || !overlayAvailable ? (
        <p className="muted flags__state">{COPY.flags.notInThisMode}</p>
      ) : !look ? (
        <p className="muted flags__state">{COPY.flags.noLook}</p>
      ) : counts.length === 0 ? (
        <p className="muted flags__state">{COPY.flags.none}</p>
      ) : (
        <>
          <ul className="flags__list">{counts.slice(0, FLAGS_SHOWN).map(item)}</ul>
          {counts.length > FLAGS_SHOWN && (
            <details className="disclosure">
              <summary>{COPY.flags.more(counts.length - FLAGS_SHOWN)}</summary>
              <ul className="flags__list">{counts.slice(FLAGS_SHOWN).map(item)}</ul>
            </details>
          )}
        </>
      )}
    </Panel>
  );
}
