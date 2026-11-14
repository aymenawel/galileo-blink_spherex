/** The four ways to look at a place: blink, compare, change, combined. */
import { COPY } from "../../lib/copy";
import { MODES, type Mode } from "../../lib/exploreAddress";

interface ModePillsProps {
  mode: Mode;
  onSelect: (mode: Mode) => void;
}

export function ModePills({ mode, onSelect }: ModePillsProps) {
  return (
    <div className="segmented" role="group" aria-label={COPY.viewport.modesLabel}>
      {MODES.map((option) => (
        <button
          key={option}
          type="button"
          className="segmented__item"
          aria-pressed={option === mode}
          title={COPY.viewport.modes[option].hint}
          onClick={() => onSelect(option)}
        >
          {COPY.viewport.modes[option].label}
        </button>
      ))}
    </div>
  );
}
