/**
 * What sits beside the picture: the name of the place, and the one result that matters, in
 * plain words. Every number behind it is further down the page.
 */
import { Check, TriangleAlert } from "lucide-react";
import type { View } from "../../api/types";
import {
  COPY,
  VISIT_COPY,
  brightnessError,
  brightnessWords,
  compassWord,
  hourlySpeed,
  isStatic,
  motionSentence,
  subjectName,
} from "../../lib/copy";
import { arcsec } from "../../lib/format";
import { brightnessHeadline } from "../panels/BrightnessPanel";

interface SummaryProps {
  view: View;
}

/** The name of the place and one line about what it is. */
export function ViewTitle({ view, searchedName }: SummaryProps & { searchedName: string | null }) {
  if (view.kind === "visit") {
    return (
      <header className="side__head">
        <h1 className="side__title">{view.label ?? VISIT_COPY.panel.unnamed}</h1>
        <p className="side__kind">{VISIT_COPY.panel.kind}</p>
      </header>
    );
  }
  const { target, subject } = view;
  const kind = subject?.kind ?? "spot";
  const title = target?.name ?? searchedName ?? view.label ?? (kind === "spot" ? COPY.subject.unnamedPlace : subjectName(view));
  return (
    <header className="side__head">
      <h1 className="side__title">{title}</h1>
      <p className="side__kind">
        {target ? target.blurb : kind === "spot" && searchedName ? COPY.subject.namedSpot(searchedName) : COPY.subject.chosen[kind]}
      </p>
    </header>
  );
}

/** Did it move, by how much, and does that match the catalogue? */
export function MotionResult({ view }: SummaryProps) {
  const motion = view.motion_combined ?? view.motion ?? null;
  if (!motion) {
    return (
      <section className="result" aria-label={COPY.motion.title}>
        <p className="result__sentence">{view.motion_reason_text ?? COPY.motion.noneTitle}</p>
        <p className="result__help">{COPY.motion.help[view.motion_reason ?? ""] ?? COPY.motion.helpFallback}</p>
      </section>
    );
  }
  const labelOf = (season: number | undefined) =>
    season === undefined ? null : (view.seasons.find((s) => s.index === season)?.label ?? null);
  const span = view.motion ?? motion;
  const still = isStatic(motion) && motion.agrees;
  const brightness = still ? brightnessHeadline(view) : null;
  // A star that stays put, as expected, has nothing to say about motion: if its brightness
  // changed, that is the result.
  if (brightness?.changed) {
    return (
      <section className="result" aria-label={COPY.brightness.title}>
        <p className="result__label">{COPY.brightness.changed}</p>
        <p className="result__figure result__figure--words">
          {brightnessWords(brightness.ratio)}
          <span className="result__error">{COPY.motion.giveOrTake(brightnessError(brightness.error))}</span>
        </p>
        <p className="verdict verdict--ok">
          <Check size={18} aria-hidden="true" />
          {COPY.motion.still}
        </p>
        <p className="result__sentence">{brightness.sentence}</p>
      </section>
    );
  }
  const cannotMeasureBrightness = still && view.brightness_change?.reason === "saturated";
  return (
    <section className="result" aria-label={COPY.motion.title}>
      <p className="result__label">{isStatic(motion) ? COPY.motion.shift : COPY.motion.moved}</p>
      <p className="result__figure">
        {arcsec(motion.measured)}
        <span className="result__error">{COPY.motion.giveOrTake(arcsec(motion.error))}</span>
      </p>
      <p className={motion.agrees ? "verdict verdict--ok" : "verdict verdict--warn"}>
        {motion.agrees ? <Check size={18} aria-hidden="true" /> : <TriangleAlert size={18} aria-hidden="true" />}
        {motion.agrees ? (isStatic(motion) ? COPY.motion.still : COPY.motion.agrees) : COPY.motion.differs}
      </p>
      <p className="result__sentence">
        {motionSentence({
          name: subjectName(view),
          firstSeason: labelOf(span.first_season),
          lastSeason: labelOf(span.last_season),
          motion,
          subject: view.subject,
          floor: view.motion?.floor,
        })}
        {cannotMeasureBrightness ? ` ${COPY.brightness.none.saturated}` : ""}
      </p>
    </section>
  );
}

/** What the asteroid search found, at a glance. */
export function VisitResult({ view }: SummaryProps) {
  const words = VISIT_COPY.result;
  const tracks = view.tracks ?? [];
  const found = tracks.filter((track) => track.confidence === "strong");
  const searched = view.search?.searched ?? view.seasons.length >= 3;
  const shown = found.length > 0 ? found : tracks;

  if (shown.length === 0) {
    return (
      <section className="result" aria-label={VISIT_COPY.movers.title}>
        <p className="result__sentence">{searched ? words.none : words.notSearched}</p>
      </section>
    );
  }
  return (
    <section className="result" aria-label={VISIT_COPY.movers.title}>
      <p className="result__figure">
        {shown.length}
        <span className="result__error">{found.length > 0 ? words.found(shown.length) : words.possibleOnly(shown.length)}</span>
      </p>
      <ul className="result__list">
        {shown.map((track) => (
          <li key={track.id}>
            <strong>{track.name ?? VISIT_COPY.movers.unnamedMover}</strong>
            <span>
              {hourlySpeed(track.speed_arcsec_per_hour)}, heading {compassWord(track.direction_deg)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
