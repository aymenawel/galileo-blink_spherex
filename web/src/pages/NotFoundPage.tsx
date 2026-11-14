/** Shown for an address that is not a page of this site. */
import { COPY } from "../lib/copy";
import { Link } from "../router";

export function NotFoundPage() {
  return (
    <div className="page not-found">
      <p className="eyebrow">404</p>
      <h1 className="display not-found__title">{COPY.errors.notFoundTitle}</h1>
      <p className="muted">{COPY.errors.notFoundBody}</p>
      <Link to="/" className="pill pill--primary">
        {COPY.errors.goHome}
      </Link>
    </div>
  );
}
