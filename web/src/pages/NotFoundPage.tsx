/** Shown for an address that is not a page of this site. */
import { COPY } from "../lib/copy";
import { Link } from "../router";

export function NotFoundPage() {
  return (
    <div className="page not-found">
      <h1 className="doc__title">{COPY.errors.notFoundTitle}</h1>
      <p className="muted">{COPY.errors.notFoundBody}</p>
      <Link to="/" className="button button--primary">
        {COPY.errors.goHome}
      </Link>
    </div>
  );
}
