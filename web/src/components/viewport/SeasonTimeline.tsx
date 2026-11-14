/** One chip per season: the time steps of the blink. The current one is lit. */
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

export function SeasonTimeline({ view, season, cameraSeasons, camera, onSelect }: SeasonTimelineProps) {
  return (
    <div className="timeline" role="group" aria-label={COPY.timeline.label}>
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
