/**
 * The site's navigation: a slim rail of icons down the left edge on wide screens, a tab bar
 * along the bottom on phones.
 */
import { BookOpen, Info, Target, Telescope, type LucideIcon } from "lucide-react";
import { COPY } from "../../lib/copy";
import { Link, useRoute, type Route } from "../../router";
import { ReticleMark } from "./Wordmark";

interface RailItem {
  to: string;
  label: string;
  icon: LucideIcon;
  isCurrent: (route: Route) => boolean;
}

const ITEMS: readonly RailItem[] = [
  {
    to: "/",
    label: COPY.nav.explore,
    icon: Telescope,
    isCurrent: (route) => (route.path === "/" && route.hash !== "targets") || route.path === "/explore",
  },
  {
    to: "/#targets",
    label: COPY.nav.targets,
    icon: Target,
    isCurrent: (route) => route.path === "/" && route.hash === "targets",
  },
  { to: "/how-it-works", label: COPY.nav.how, icon: BookOpen, isCurrent: (route) => route.path === "/how-it-works" },
  { to: "/about", label: COPY.nav.about, icon: Info, isCurrent: (route) => route.path === "/about" },
];

export function Rail() {
  const route = useRoute();
  return (
    <nav className="rail" aria-label={COPY.nav.label}>
      <Link to="/" className="rail__mark" aria-label={`${COPY.brand.name}: ${COPY.brand.tagline}`}>
        <ReticleMark />
      </Link>
      <ul className="rail__items">
        {ITEMS.map(({ to, label, icon: Icon, isCurrent }) => (
          <li key={to}>
            <Link to={to} className="rail__item" aria-current={isCurrent(route) ? "page" : undefined}>
              <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
              <span className="rail__label">{label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
