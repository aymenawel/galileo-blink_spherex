/** How the asteroid search works, in five plain steps, beside the result it produced. */
import { VISIT_COPY } from "../../lib/copy";
import { Link } from "../../router";
import { COPY } from "../../lib/copy";
import { Panel } from "./Panel";

export function SearchMethodPanel() {
  const words = VISIT_COPY.how;
  return (
    <Panel title={words.title} className="search-method">
      <ol className="search-method__steps">
        {words.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="muted">{words.why}</p>
      <Link to="/how-it-works#limits" className="honesty__more">
        {COPY.honesty.more}
      </Link>
    </Panel>
  );
}
