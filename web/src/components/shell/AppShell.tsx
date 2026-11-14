/** The frame around every page: navigation rail, the page itself, and the credits. */
import type { ReactNode } from "react";
import { COPY } from "../../lib/copy";
import { Footer } from "./Footer";
import { Rail } from "./Rail";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="shell">
      <a className="skip-link" href="#content">
        {COPY.nav.skip}
      </a>
      <Rail />
      <div className="shell__page">
        <main id="content" tabIndex={-1}>
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
}
