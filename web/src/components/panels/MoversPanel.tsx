/**
 * "What moved?": the result of the asteroid search. Every path it found, how sure it is,
 * and what the asteroid catalogue says should have been there.
 */
import { Check, CircleHelp } from "lucide-react";
import type { KnownAsteroid, View, VisitTrack } from "../../api/types";
import { VISIT_COPY, compassWord, knownAsteroidNote } from "../../lib/copy";
import { arcsec } from "../../lib/format";
import { Panel } from "./Panel";
import { Readout } from "./Readout";

interface MoversPanelProps {
  view: View;
}

const words = VISIT_COPY.movers;
/** The catalogue often lists dozens of faint asteroids in one field; the brightest few are named. */
const KNOWN_LISTED = 6;

function Mover({ track, moments }: { track: VisitTrack; moments: number }) {
  const strong = track.confidence === "strong";
  return (
    <li className={strong ? "mover mover--strong" : "mover"}>
      <header className="mover__head">
        <h4 className="mover__name">{track.name ?? words.unnamedMover}</h4>
        <span className={strong ? "verdict verdict--ok" : "verdict verdict--warn"}>
          {strong ? <Check size={16} aria-hidden="true" /> : <CircleHelp size={16} aria-hidden="true" />}
          {strong ? words.strong : words.possible}
        </span>
      </header>
      <p className="muted mover__kind">{track.name ? words.identified : words.unidentified}</p>
      <dl className="readouts readouts--tight">
        <Readout
          label={words.speed}
          value={arcsec(track.speed_arcsec_per_hour, track.speed_arcsec_per_hour < 10 ? 1 : 0)}
          suffix={words.perHour}
          tone={strong ? "measured" : "plain"}
        />
        <Readout label={words.heading} value={compassWord(track.direction_deg)} />
        <Readout label={words.seen} value={words.ofMoments(track.n_moments, moments)} />
      </dl>
    </li>
  );
}

function Known({ asteroid }: { asteroid: KnownAsteroid }) {
  return (
    <li className={asteroid.found ? "known known--found" : "known"}>
      <span className="known__name">{asteroid.name}</span>
      <span className="muted">{knownAsteroidNote(asteroid.note, asteroid.vmag, asteroid.moments_in_view)}</span>
    </li>
  );
}

export function MoversPanel({ view }: MoversPanelProps) {
  const tracks = view.tracks ?? [];
  const known = view.known_asteroids ?? [];
  const moments = view.seasons.length;
  const searched = view.search?.searched ?? moments >= 3;
  const catalogueDown = (view.degraded ?? []).includes("asteroid_catalogue");
  const hasPossible = tracks.some((track) => track.confidence === "possible");
  const hasUnidentified = tracks.some((track) => track.confidence === "strong" && !track.name);

  return (
    <Panel title={words.title} className="movers">
      {!searched && <p className="note">{words.notSearched(moments)}</p>}
      {searched && tracks.length === 0 && <p className="muted">{words.none}</p>}
      {tracks.length > 0 && (
        <ul className="movers__list">
          {tracks.map((track) => (
            <Mover key={track.id} track={track} moments={moments} />
          ))}
        </ul>
      )}
      {hasPossible && <p className="muted movers__note">{words.possibleNote}</p>}
      {hasUnidentified && <p className="muted movers__note">{words.unidentifiedNote}</p>}

      <h4 className="movers__known-title">{words.knownTitle}</h4>
      {catalogueDown ? (
        <p className="note">{words.catalogueDown}</p>
      ) : known.length === 0 ? (
        <p className="muted">{words.knownNone}</p>
      ) : (
        <>
          <ul className="movers__known">
            {known.slice(0, KNOWN_LISTED).map((asteroid) => (
              <Known key={asteroid.name} asteroid={asteroid} />
            ))}
          </ul>
          {known.length > KNOWN_LISTED && (
            <p className="muted movers__note">{words.knownMore(known.length - KNOWN_LISTED)}</p>
          )}
        </>
      )}
    </Panel>
  );
}
