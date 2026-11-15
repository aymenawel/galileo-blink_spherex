/** A titled section of "The details": a heading, an optional line of context, then whatever it holds. */
import { useId, type ReactNode } from "react";

interface PanelProps {
  title: string;
  /** A short line under the title saying what the section is about right now. */
  context?: string;
  /** Something to sit at the right of the heading, such as a verdict or a button. */
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Panel({ title, context, aside, className, children }: PanelProps) {
  const titleId = useId();
  return (
    <section className={className ? `panel ${className}` : "panel"} aria-labelledby={titleId}>
      <header className="panel__head">
        <div>
          <h3 className="panel__title" id={titleId}>
            {title}
          </h3>
          {context && <p className="panel__context">{context}</p>}
        </div>
        {aside}
      </header>
      {children}
    </section>
  );
}
