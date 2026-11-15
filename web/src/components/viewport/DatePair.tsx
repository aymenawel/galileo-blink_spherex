/** Choosing the two dates of Compare and Change. */
import { ArrowLeftRight } from "lucide-react";
import type { View } from "../../api/types";
import { COPY } from "../../lib/copy";

interface DatePairProps {
  view: View;
  /** Seasons in which the chosen camera has a picture. */
  cameraSeasons: readonly number[];
  a: number;
  b: number;
  onA: (season: number) => void;
  onB: (season: number) => void;
  onSwap: () => void;
}

export function DatePair({ view, cameraSeasons, a, b, onA, onB, onSwap }: DatePairProps) {
  const options = view.seasons.filter((season) => cameraSeasons.includes(season.index));
  const picker = (label: string, value: number, onChange: (season: number) => void) => (
    <label className="date-pair__field">
      <span className="date-pair__label">{label}</span>
      <select className="select" value={value} onChange={(event) => onChange(Number(event.target.value))}>
        {options.map((season) => (
          <option key={season.index} value={season.index}>
            {season.label}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="date-pair">
      {picker(COPY.viewport.seasonA, a, onA)}
      <button type="button" className="icon-button" aria-label={COPY.viewport.swap} onClick={onSwap}>
        <ArrowLeftRight size={16} aria-hidden="true" />
      </button>
      {picker(COPY.viewport.seasonB, b, onB)}
    </div>
  );
}
