/** The compass rose of a sky picture: north is up and east is to the LEFT, as on the sky. */
import { COPY } from "../../lib/copy";

export function Compass() {
  return (
    <svg className="compass" viewBox="0 0 64 64" role="img" aria-label={COPY.viewport.compassLabel}>
      <path d="M44 46V14M44 14l-5 8M44 14l5 8" />
      <path d="M44 46H12M12 46l8-5M12 46l8 5" />
      <text x="44" y="9" textAnchor="middle">
        {COPY.viewport.north}
      </text>
      <text x="5" y="50" textAnchor="middle">
        {COPY.viewport.east}
      </text>
    </svg>
  );
}
