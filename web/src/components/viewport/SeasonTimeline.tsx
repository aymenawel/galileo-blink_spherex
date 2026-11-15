/** One chip per season: the time steps of the blink. The current one is lit. */
import { useEffect, useRef } from "react";
import type { View } from "../../api/types";
import { COPY } from "../../lib/copy";
import { formatDate } from "../../lib/format";

interface SeasonTimelineProps {
  view: View;
  season: number;
  /** Seasons in which the chosen camera has a picture; the others are dimmed. */
  cameraSeasons: readonly number[];
  camera: string;
  onSelect: (season: number) => void;
}

/**
 * Keep the lit date in sight when the list is longer than its space. Only the list itself
 * is scrolled, never the page, so a blink left playing does not pull the reader back up.
 */
function useLitInSight(season: number) {
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = list.current;
    const lit = box?.querySelector<HTMLElement>('[aria-pressed="true"]');
    if (!box || !lit) return;
    const frame = box.getBoundingClientRect();
    const chip = lit.getBoundingClientRect();
    if (chip.top < frame.top) box.scrollTop -= frame.top - chip.top;
    else if (chip.bottom > frame.bottom) box.scrollTop += chip.bottom - frame.bottom;
    if (chip.left < frame.left) box.scrollLeft -= frame.left - chip.left;
    else if (chip.right > frame.right) box.scrollLeft += chip.right - frame.right;
  }, [season]);
  return list;
}

export function SeasonTimeline({ view, season, cameraSeasons, camera, onSelect }: SeasonTimelineProps) {
  const list = useLitInSight(season);
  return (
    <div className="timeline" role="group" aria-label={COPY.timeline.label} ref={list}>
      {view.seasons.map((step) => {
        const hasLook = cameraSeasons.includes(step.index);
        return (
          <button
            key={step.index}
            type="button"
            className={`timeline__chip${hasLook ? "" : " timeline__chip--empty"}`}
            aria-pressed={step.index === season}
            title={hasLook ? formatDate(step.date) : COPY.timeline.noLookTitle(camera)}
            onClick={() => onSelect(step.index)}
          >
            <span className="timeline__dot" aria-hidden="true" />
            {step.label}
          </button>
        );
      })}
    </div>
  );
}
