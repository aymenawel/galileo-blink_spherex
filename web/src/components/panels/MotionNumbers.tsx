/** The precise numbers behind the motion verdict: one row per camera, then how they were obtained. */
import type { ReactNode } from "react";
import type { Motion, View } from "../../api/types";
import { CAMERA_KEYS } from "../../lib/cameras";
import { COPY, floorNote, parallaxNote, referenceStarsNote } from "../../lib/copy";
import { arcsec } from "../../lib/format";

interface MotionNumbersProps {
  view: View;
  /** The measurement shown in the panel's headline. */
  headline: Motion;
}

export function MotionNumbers({ view, headline }: MotionNumbersProps) {
  const labelOf = (season: number | undefined) =>
    season === undefined ? "" : (view.seasons.find((s) => s.index === season)?.label ?? "");
  const seasonsOf = (motion: Motion) =>
    motion.first_season !== undefined ? `${labelOf(motion.first_season)} → ${labelOf(motion.last_season)}` : "";
  const table = COPY.motion.table;

  const row = (label: ReactNode, motion: Motion, key: string, emphasised = false) => (
    <tr key={key} className={emphasised ? "numbers__total" : undefined}>
      <th scope="row">{label}</th>
      <td>{seasonsOf(motion) || seasonsOf(view.motion ?? motion)}</td>
      <td>
        {arcsec(motion.measured, 2)} ± {arcsec(motion.error, 2)}
      </td>
      <td>{arcsec(motion.predicted, 2)}</td>
      <td>{motion.residual !== undefined ? arcsec(motion.residual, 2) : ""}</td>
      <td className={motion.agrees ? "numbers__yes" : "numbers__no"}>
        <span aria-hidden="true">{motion.agrees ? "✓" : "✗"}</span>
        <span className="visually-hidden">{motion.agrees ? table.yes : table.no}</span>
      </td>
    </tr>
  );

  const floor = view.motion?.floor ?? headline.floor;
  const referenceStars = view.reference_stars?.median_used ?? view.motion?.n_reference_stars;

  return (
    <div className="numbers">
      <div className="numbers__scroll" tabIndex={0} role="group" aria-label={COPY.motion.numbersLabel}>
        <table className="numbers__table">
          <thead>
            <tr>
              <th scope="col">{table.camera}</th>
              <th scope="col">{table.seasons}</th>
              <th scope="col">{table.measured}</th>
              <th scope="col">{table.predicted}</th>
              <th scope="col">{table.difference}</th>
              <th scope="col">{table.agrees}</th>
            </tr>
          </thead>
          <tbody>
            {CAMERA_KEYS.map((key) => {
              const motion = view.motion_by_camera?.[key];
              return motion
                ? row(key, motion, key) : null;
            })}
            {view.motion_combined && row(table.together, view.motion_combined, "together", true)}
          </tbody>
        </table>
      </div>
      <ul className="numbers__notes">
        {floor !== undefined && <li>{floorNote(floor)}</li>}
        {referenceStars !== undefined && <li>{referenceStarsNote(referenceStars, view.reference_stars?.available)}</li>}
        <li>{parallaxNote(headline.same_time_of_year)}</li>
      </ul>
    </div>
  );
}
