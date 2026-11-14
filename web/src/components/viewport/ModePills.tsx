/** The ways to look at a place: blink, compare, change, combined (an asteroid view has three). */
import { COPY, VISIT_COPY } from "../../lib/copy";
import { MODES, type Mode } from "../../lib/exploreAddress";

interface ModePillsProps {
  mode: Mode;
  /** An asteroid view: its moments are too close in time for a two-date comparison. */
  visit?: boolean;
  onSelect: (mode: Mode) => void;
}

const VISIT_MODES: ReadonlyArray<Exclude<Mode, "compare">> = ["blink", "change", "combined"];

export function ModePills({ mode, visit = false, onSelect }: ModePillsProps) {
  const options = visit
    ? VISIT_MODES.map((option) => ({ option, words: VISIT_COPY.modes[option] }))
    : MODES.map((option) => ({ option, words: COPY.viewport.modes[option] }));
  return (
    <div className="segmented" role="group" aria-label={COPY.viewport.modesLabel}>
      {options.map(({ option, words }) => (
        <button
          key={option}
          type="button"
          className="segmented__item"
          aria-pressed={option === mode}
          title={words.hint}
          onClick={() => onSelect(option)}
        >
          {words.label}
        </button>
      ))}
    </div>
  );
}
