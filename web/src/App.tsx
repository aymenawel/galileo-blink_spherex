/** Chooses the page for the current address. */
import { useEffect, type ReactElement } from "react";
import { AppShell } from "./components/shell/AppShell";
import { COPY } from "./lib/copy";
import { AboutPage } from "./pages/AboutPage";
import { ExplorePage } from "./pages/ExplorePage";
import { HomePage } from "./pages/HomePage";
import { HowItWorksPage } from "./pages/HowItWorksPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { useRoute } from "./router";

interface Page {
  /** Shown in the browser tab before the site's name. */
  title: string | null;
  render: () => ReactElement;
}

const PAGES: Record<string, Page> = {
  "/": { title: null, render: () => <HomePage /> },
  "/explore": { title: COPY.nav.explore, render: () => <ExplorePage /> },
  "/how-it-works": { title: COPY.nav.how, render: () => <HowItWorksPage /> },
  "/about": { title: COPY.nav.about, render: () => <AboutPage /> },
};

const NOT_FOUND: Page = { title: COPY.errors.notFoundTitle, render: () => <NotFoundPage /> };

export function App() {
  const { path, hash } = useRoute();
  const page = PAGES[path] ?? NOT_FOUND;

  useEffect(() => {
    document.title = page.title
      ? `${page.title} · ${COPY.brand.name}`
      : `${COPY.brand.name}: ${COPY.brand.tagline.toLowerCase()}`;
  }, [page.title]);

  // A shared link such as /how-it-works#limits opens at that part of the page.
  useEffect(() => {
    if (hash) document.getElementById(hash)?.scrollIntoView({ block: "start" });
    // Runs once, when the site first appears; later moves are handled by the router.
  }, []);

  return <AppShell>{page.render()}</AppShell>;
}
