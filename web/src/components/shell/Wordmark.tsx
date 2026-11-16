/**
 * The site's name and its mark. The mark is a north star, cut like a gem, with an orbit
 * threaded through it: behind the star at the top, in front of it below. The dot on the
 * orbit is the thing that moves.
 */
import { COPY } from "../../lib/copy";
import { Link } from "../../router";

const ORBIT_BACK = "M3.58 21.53A13.6 5 -24 0 1 28.42 10.47";
const ORBIT_FRONT = "M3.58 21.53A13.6 5 -24 0 0 28.42 10.47";

export function BlinkMark({ size = 26 }: { size?: number }) {
  return (
    <svg className="mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path className="mark__orbit" d={ORBIT_BACK} />
      <path className="mark__star" d="M16 16L16 1.8L18.47 13.53ZM16 16L30.2 16L18.47 18.47ZM16 16L16 30.2L13.53 18.47ZM16 16L1.8 16L13.53 13.53Z" />
      <path className="mark__shade" d="M16 16L16 1.8L13.53 13.53ZM16 16L30.2 16L18.47 13.53ZM16 16L16 30.2L18.47 18.47ZM16 16L1.8 16L13.53 18.47Z" />
      <path className="mark__gap" d={ORBIT_FRONT} />
      <path className="mark__orbit" d={ORBIT_FRONT} />
      <circle className="mark__is" cx="28.42" cy="10.47" r="2.3" />
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
