/** "What this view can't tell you": the limits of this particular view, written from its own numbers. */
import type { View } from "../../api/types";
import { COPY, degradedSentence, leftOutSentence } from "../../lib/copy";
import { Link } from "../../router";
import { Panel } from "./Panel";

interface HonestyPanelProps {
  view: View;
}

/** How many photos were left out for each reason. */
function countReasons(view: View): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const photo of view.left_out ?? []) counts.set(photo.reason, (counts.get(photo.reason) ?? 0) + 1);
  return [...counts.entries()];
}

function limits(view: View): string[] {
  const floor = view.motion?.floor;
  return [
    ...(view.degraded ?? []).map(degradedSentence),
    floor !== undefined ? COPY.honesty.floor(floor) : COPY.honesty.pixel(view.pixel_arcsec),
    COPY.honesty.wavelength,
    ...countReasons(view).map(([reason, count]) => leftOutSentence(reason, count)),
    ...(view.seasons_left_out ? [COPY.honesty.seasons(view.seasons_left_out)] : []),
    ...(view.markers_left_out ? [COPY.honesty.markersLeftOut(view.markers_left_out)] : []),
    COPY.honesty.noDiscovery,
  ];
}

export function HonestyPanel({ view }: HonestyPanelProps) {
  return (
    <Panel eyebrow={COPY.honesty.eyebrow} title={COPY.honesty.title} className="honesty">
      <ul className="honesty__list">
        {limits(view).map((sentence) => (
          <li key={sentence}>{sentence}</li>
        ))}
      </ul>
      <Link to="/how-it-works#limits" className="honesty__more">
        {COPY.honesty.more} →
      </Link>
    </Panel>
  );
}
