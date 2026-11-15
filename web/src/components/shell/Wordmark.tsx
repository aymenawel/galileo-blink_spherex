/**
 * The site's name and its mark. The mark is a blink in one drawing: an open ring where a
 * star was, and a filled dot where it is now.
 */
import { COPY } from "../../lib/copy";
import { Link } from "../../router";

export function BlinkMark({ size = 26 }: { size?: number }) {
  return (
    <svg className="mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle className="mark__was" cx="11" cy="20" r="6.5" />
      <circle className="mark__is" cx="21.5" cy="11.5" r="6.5" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link to="/" className="brand" aria-label={`${COPY.brand.name}: ${COPY.brand.tagline}`}>
      <BlinkMark />
      <span>{COPY.brand.name}</span>
    </Link>
  );
}
