/**
 * A small, self-running blink of a ready-made view: for the home page and the target cards.
 * It shows the subject's reticle and nothing else, and stays still if the visitor prefers
 * reduced motion or has paused the previews.
 */
import { useMemo } from "react";
import type { CameraKey, View } from "../../api/types";
import { defaultCamera, looksOf, seasonsWithLooks } from "../../lib/cameras";
import { COPY, subjectName } from "../../lib/copy";
import { markersToDraw, visitMarkers } from "../../lib/markers";
import { usePreviewsPaused } from "../../lib/previewMotion";
import { useBlinkClock } from "../../lib/useBlinkClock";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { ImageStack } from "./ImageStack";
import { SkyOverlay } from "./SkyOverlay";

interface BlinkPreviewProps {
  view: View;
  /** The camera to show if it has pictures; otherwise the view's best camera. */
  preferCamera?: CameraKey;
  /** Time each date stays on screen, in milliseconds. */
  beat?: number;
  /** Show the date in a corner. */
  showDate?: boolean;
}

export function BlinkPreview({ view, preferCamera, beat = 900, showDate = false }: BlinkPreviewProps) {
  const reducedMotion = useReducedMotion();
  const camera = preferCamera && looksOf(view, preferCamera).length > 1 ? preferCamera : defaultCamera(view);
  const seasons = useMemo(() => seasonsWithLooks(view, camera), [view, camera]);
  const paused = usePreviewsPaused();
  const step = useBlinkClock(seasons.length, beat, !reducedMotion && !paused);
  const season = seasons[step] ?? 0;
  const subject = useMemo(
    () => (view.kind === "visit" ? visitMarkers(view) : markersToDraw(view.markers)).filter((drawn) => drawn.marker.subject),
    [view],
  );

  return (
    <div className="blink-preview sky">
      <ImageStack view={view} camera={camera} season={season} place={view.kind === "visit" ? (view.label ?? "") : subjectName(view)} />
      <SkyOverlay n={view.n} markers={subject} season={season} />
      {showDate && (
        <span className="blink-preview__date">
          {view.seasons.find((s) => s.index === season)?.label} · {COPY.cameras.camera(camera)}
        </span>
      )}
    </div>
  );
}
