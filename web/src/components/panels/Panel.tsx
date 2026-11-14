/** A titled card of the bento grid: a small label, a serif title, then whatever it holds. */
import { useId, type ReactNode } from "react";

interface PanelProps {
  /** Small uppercase label above the title. */
  eyebrow: string;
  title: string;
  /** Something to sit at the right of the heading, such as a chip or a button. */
  aside?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Panel({ eyebrow, title, aside, className, children }: PanelProps) {
  const titleId = useId();
  return (
    <section className={className ? `panel ${className}` : "panel"} aria-labelledby={titleId}>
      <header className="panel__head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 className="panel__title" id={titleId}>
            {title}
          </h2>
        </div>
        {aside}
      </header>
      {children}
    </section>
  );
}
