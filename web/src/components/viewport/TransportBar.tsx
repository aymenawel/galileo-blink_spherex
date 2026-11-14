/** Blink controls: previous date, play or pause, next date, and how fast to blink. */
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { COPY } from "../../lib/copy";
import type { Speed } from "../explore/useWorkspace";

interface TransportBarProps {
  playing: boolean;
  speed: Speed;
  /** False when the camera has fewer than two dates: there is nothing to step through. */
  enabled: boolean;
  onStep: (direction: 1 | -1) => void;
  onTogglePlaying: () => void;
  onSpeed: (speed: Speed) => void;
}

const SPEEDS: readonly Speed[] = ["slow", "normal", "fast"];

export function TransportBar({ playing, speed, enabled, onStep, onTogglePlaying, onSpeed }: TransportBarProps) {
  return (
    <div className="transport">
      <button type="button" className="icon-button" aria-label={COPY.viewport.previous} disabled={!enabled} onClick={() => onStep(-1)}>
        <ChevronLeft size={18} aria-hidden="true" />
      </button>
      <button
        type="button"
        className="icon-button icon-button--primary"
        aria-label={playing ? COPY.viewport.pause : COPY.viewport.play}
        disabled={!enabled}
        onClick={onTogglePlaying}
      >
        {playing ? <Pause size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
      </button>
      <button type="button" className="icon-button" aria-label={COPY.viewport.next} disabled={!enabled} onClick={() => onStep(1)}>
        <ChevronRight size={18} aria-hidden="true" />
      </button>
      <select
        className="select select--compact"
        aria-label={COPY.viewport.speed}
        value={speed}
        disabled={!enabled}
        onChange={(event) => onSpeed(SPEEDS.find((s) => s === event.target.value) ?? "normal")}
      >
        {SPEEDS.map((option) => (
          <option key={option} value={option}>
            {COPY.viewport.speeds[option]}
          </option>
        ))}
      </select>
    </div>
  );
}
