/** Switches for what is drawn on top of the picture. */
import { Crosshair, Flag, Sparkles } from "lucide-react";
import { COPY } from "../../lib/copy";
import type { OverlayName, Overlays } from "../explore/useWorkspace";

interface OverlayTogglesProps {
  overlays: Overlays;
  /** Flags belong to a single date, so they can only be shown in Blink. */
  flagsAvailable: boolean;
  onToggle: (name: OverlayName) => void;
}

export function OverlayToggles({ overlays, flagsAvailable, onToggle }: OverlayTogglesProps) {
  return (
    <div className="toggles" role="group" aria-label={COPY.viewport.overlays}>
      <button type="button" className="toggle" aria-pressed={overlays.markers} onClick={() => onToggle("markers")}>
        <Crosshair size={15} aria-hidden="true" />
        {COPY.viewport.markers}
      </button>
      <button type="button" className="toggle" aria-pressed={overlays.stars} onClick={() => onToggle("stars")}>
        <Sparkles size={15} aria-hidden="true" />
        {COPY.viewport.stars}
      </button>
      <button
        type="button"
        className="toggle toggle--flags"
        aria-pressed={overlays.flags && flagsAvailable}
        disabled={!flagsAvailable}
        title={flagsAvailable ? undefined : COPY.viewport.flagsOnlyInBlink}
        onClick={() => onToggle("flags")}
      >
        <Flag size={15} aria-hidden="true" />
        {COPY.viewport.flags}
      </button>
    </div>
  );
}
