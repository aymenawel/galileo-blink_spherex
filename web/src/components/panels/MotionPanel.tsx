/**
 * The headline result: did the object move, by how much, and does that match the catalogue?
 * Plain words first; the full numbers are one click away.
 */
import { Check, TriangleAlert } from "lucide-react";
import type { CameraKey, Motion, View } from "../../api/types";
import { COPY, isStatic, motionMethod, motionSentence, subjectName } from "../../lib/copy";
import { arcsec } from "../../lib/format";
import { MotionNumbers } from "./MotionNumbers";
import { Panel } from "./Panel";
import { Readout } from "./Readout";
import { TrackPlot } from "./TrackPlot";

interface MotionPanelProps {
  view: View;
  /** The camera chosen in the main picture; the plot shows its measured positions. */
  camera: CameraKey;
}

/** Several cameras together when the view has that; otherwise the best single camera. */
function headlineMotion(view: View): Motion | null {
  return view.motion_combined ?? view.motion ?? null;
}

function Unmeasured({ view }: { view: View }) {
  const reason = view.motion_reason ?? "";
  return (
    <div className="motion__none">
      <p className="motion__sentence">{view.motion_reason_text ?? COPY.motion.noneTitle}</p>
      <p className="muted">{COPY.motion.help[reason] ?? COPY.motion.helpFallback}</p>
    </div>
  );
}

export function MotionPanel({ view, camera }: MotionPanelProps) {
  const motion = headlineMotion(view);
  if (!motion) {
    return (
      <Panel title={COPY.motion.title} className="motion">
        <Unmeasured view={view} />
      </Panel>
    );
  }

  const labelOf = (season: number | undefined) =>
    season === undefined ? null : (view.seasons.find((s) => s.index === season)?.label ?? null);
  const span = view.motion ?? motion;
  const verdict = motion.agrees ? (
    <span className="verdict verdict--ok">
      <Check size={16} aria-hidden="true" />
      {isStatic(motion) ? COPY.motion.still : COPY.motion.agrees}
    </span>
  ) : (
    <span className="verdict verdict--warn">
      <TriangleAlert size={16} aria-hidden="true" />
      {COPY.motion.differs}
    </span>
  );

  return (
    <Panel title={COPY.motion.title} className="motion" aside={verdict}>
      <dl className="motion__readouts">
        <Readout
          label={isStatic(motion) ? COPY.motion.shift : COPY.motion.moved}
          value={arcsec(motion.measured)}
          suffix={`± ${arcsec(motion.error)}`}
          tone="measured"
          size="large"
        />
        <Readout
          label={COPY.motion.predicted}
          value={arcsec(motion.predicted, motion.predicted < 1 ? 2 : 1)}
          size="large"
        />
      </dl>

      <p className="motion__sentence">
        {motionSentence({
          name: subjectName(view),
          firstSeason: labelOf(span.first_season),
          lastSeason: labelOf(span.last_season),
          motion,
          subject: view.subject,
          floor: view.motion?.floor,
        })}
      </p>
      <p className="muted motion__why">
        {motion.agrees ? COPY.motion.agreesWhy : COPY.motion.differsWhy} {motionMethod(motion)}
      </p>

      {(view.path?.length ?? 0) > 0 && <TrackPlot view={view} camera={camera} />}

      <details className="disclosure">
        <summary>{COPY.motion.showNumbers}</summary>
        <MotionNumbers view={view} headline={motion} />
      </details>
    </Panel>
  );
}
