/** NASA's five test targets as a row of cards, with honest loading and failure states. */
import { useTargets } from "../api/useResource";
import { COPY } from "../lib/copy";
import { TargetCard } from "./TargetCard";

export function TargetList() {
  const targets = useTargets();

  if (targets.status === "failed") {
    return (
      <p className="note" role="alert">
        {COPY.home.targetsFailed}
      </p>
    );
  }
  if (targets.status === "loading") {
    return (
      <div className="target-list" aria-busy="true">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="target-card target-card--loading" aria-hidden="true" />
        ))}
      </div>
    );
  }
  return (
    <div className="target-list">
      {targets.data.map((target, i) => (
        <TargetCard key={target.id} target={target} order={i} />
      ))}
    </div>
  );
}
