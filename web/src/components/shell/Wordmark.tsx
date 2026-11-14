/** The site's name and its mark: an open reticle, the same shape drawn on moving objects. */
import { COPY } from "../../lib/copy";
import { Link } from "../../router";

export function ReticleMark({ size = 28 }: { size?: number }) {
  return (
    <svg className="reticle-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3v6M16 23v6M3 16h6M23 16h6" />
      <circle cx="16" cy="16" r="7.5" />
      <circle className="reticle-mark__star" cx="16" cy="16" r="1.5" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link to="/" className="wordmark">
      {COPY.brand.name}
    </Link>
  );
}
