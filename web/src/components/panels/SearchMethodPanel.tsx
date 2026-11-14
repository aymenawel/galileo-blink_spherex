/** How the asteroid search works, in five plain steps, beside the result it produced. */
import { VISIT_COPY } from "../../lib/copy";
import { Link } from "../../router";
import { COPY } from "../../lib/copy";
import { Panel } from "./Panel";

export function SearchMethodPanel() {
  const words = VISIT_COPY.how;
  return (
    <Panel eyebrow={words.eyebrow} title={words.title} className="search-method">
      <ol className="search-method__steps">
        {words.steps.map((step, i) => (
          <li key={step}>
            <span className="search-method__number mono" aria-hidden="true">
              {String(i + 1).padStart(2, "0")}
            </span>
            {step}
          </li>
        ))}
      </ol>
      <p className="muted">{words.why}</p>
      <Link to="/how-it-works#limits" className="honesty__more">
        {COPY.honesty.more} →
      </Link>
    </Panel>
  );
}
