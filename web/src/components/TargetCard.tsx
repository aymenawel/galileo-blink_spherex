/** A card for one of NASA's five test targets: what it is, how fast it moves, and a live blink of it. */
import { ArrowUpRight } from "lucide-react";
import type { Target } from "../api/types";
import { useReadyView } from "../api/useView";
import { COPY, speedChip, STATIC_BELOW_ARCSEC } from "../lib/copy";
import { exploreAddress } from "../lib/exploreAddress";
import { riseOrder } from "../lib/stagger";
import { Link } from "../router";
import { BlinkPreview } from "./viewport/BlinkPreview";

interface TargetCardProps {
  target: Target;
  /** Position in the list, for the staggered entrance. */
  order?: number;
}

export function TargetCard({ target, order = 0 }: TargetCardProps) {
  const view = useReadyView(target.ready ? target.key : null);
  const moves = target.pm >= STATIC_BELOW_ARCSEC;

  return (
    <Link
      to={exploreAddress({ kind: "target", id: target.id })}
      className="target-card rise"
      style={riseOrder(order)}
    >
      <div className="target-card__thumb">
        {view ? <BlinkPreview view={view} beat={1000} /> : <div className="sky target-card__placeholder" aria-hidden="true" />}
      </div>
      <div className="target-card__text">
        <p className="eyebrow">{target.kind}</p>
        <h3 className="target-card__name display">{target.name}</h3>
        <p className="muted">{target.blurb}</p>
        <p className="target-card__foot">
          <span className={moves ? "chip chip--ember" : "chip chip--ice"}>{speedChip(target.pm)}</span>
          <span className="target-card__open">
            {target.ready ? COPY.home.targetOpen : COPY.home.targetBuilding}
            <ArrowUpRight size={16} aria-hidden="true" />
          </span>
        </p>
      </div>
    </Link>
  );
}
