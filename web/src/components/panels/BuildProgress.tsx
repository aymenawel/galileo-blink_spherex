/**
 * Shown while a view is being built, and when a build fails. Calm and honest: what is
 * happening now, how far along it is, and when it fails, whose side the failure is on.
 */
import { RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { ErrorKind, ViewStatus } from "../../api/types";
import { COPY } from "../../lib/copy";
import { formatSeconds } from "../../lib/format";

const FACT_EVERY_MS = 4200;

/** One line about what is happening behind the progress bar, changing every few seconds. */
function useRotatingFact(): string {
  const facts = COPY.build.facts;
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((current) => (current + 1) % facts.length), FACT_EVERY_MS);
    return () => window.clearInterval(timer);
  }, [facts.length]);
  return facts[index] ?? facts[0];
}

interface BuildProgressProps {
  /** The latest progress report, or `null` before the first one arrives. */
  status: ViewStatus | null;
}

export function BuildProgress({ status }: BuildProgressProps) {
  const fact = useRotatingFact();
  const fraction = Math.max(0, Math.min(1, status?.fraction ?? 0));
  const percent = Math.round(fraction * 100);
  const stage = status?.stage ?? (status ? COPY.build.queued : COPY.explore.opening);

  return (
    <section className="build" aria-labelledby="build-title">
      <h1 className="build__stage" id="build-title" aria-live="polite">
        {stage}
      </h1>

      <div
        className="build__bar"
        role="progressbar"
        aria-label={COPY.build.progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <span className="build__fill" style={{ width: `${Math.max(percent, 2)}%` }} />
      </div>

      <dl className="build__readouts">
        <div>
          <dt>{COPY.build.progress}</dt>
          <dd>{percent}%</dd>
        </div>
        <div>
          <dt>{COPY.build.elapsed}</dt>
          <dd>{formatSeconds(status?.seconds ?? 0)}</dd>
        </div>
      </dl>

      <p className="build__fact">{fact}</p>
      <p className="muted build__typical">{COPY.build.typical}</p>
    </section>
  );
}

interface BuildFailedProps {
  message: string;
  kind: ErrorKind;
  onRetry: () => void;
}

export function BuildFailed({ message, kind, onRetry }: BuildFailedProps) {
  return (
    <section className="build build--failed" role="alert">
      <h1 className="build__stage">{message}</h1>
      <p className="muted build__side">{COPY.errors.side[kind]}</p>
      <button type="button" className="button button--primary" onClick={onRetry}>
        <RotateCw size={16} aria-hidden="true" />
        {COPY.errors.retry}
      </button>
    </section>
  );
}
