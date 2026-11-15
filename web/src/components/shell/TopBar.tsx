/**
 * The bar across the top of every page: the name, the pages, and (while a view is open) a
 * search box, so another place is always one line of typing away.
 */
import { useEffect, useState } from "react";
import { COPY } from "../../lib/copy";
import { Link, useRoute, type Route } from "../../router";
import { SearchBox } from "./SearchBox";
import { Wordmark } from "./Wordmark";

interface BarLink {
  to: string;
  label: string;
  isCurrent: (route: Route) => boolean;
}

const LINKS: readonly BarLink[] = [
  { to: "/#targets", label: COPY.nav.targets, isCurrent: (route) => route.path === "/" && route.hash === "targets" },
  { to: "/#asteroids", label: COPY.nav.asteroids, isCurrent: (route) => route.path === "/" && route.hash === "asteroids" },
  { to: "/how-it-works", label: COPY.nav.how, isCurrent: (route) => route.path === "/how-it-works" },
  { to: "/about", label: COPY.nav.about, isCurrent: (route) => route.path === "/about" },
];

export function TopBar() {
  const route = useRoute();
  const [open, setOpen] = useState(false);
  const exploring = route.path === "/explore";
  const searched = exploring ? (route.query.get("name") ?? "") : "";

  // The menu closes whenever the visitor arrives somewhere.
  useEffect(() => setOpen(false), [route.path, route.hash]);

  return (
    <header className={exploring ? "bar bar--search" : "bar"}>
      <Wordmark />
      {exploring && <SearchBox size="compact" key={searched} initialText={searched} />}
      <button
        type="button"
        className="bar__menu"
        aria-expanded={open}
        aria-controls="bar-links"
        onClick={() => setOpen((current) => !current)}
      >
        {COPY.nav.menu}
      </button>
      <nav id="bar-links" className={open ? "bar__links is-open" : "bar__links"} aria-label={COPY.nav.label}>
        {LINKS.map(({ to, label, isCurrent }) => (
          <Link key={to} to={to} aria-current={isCurrent(route) ? "page" : undefined}>
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
