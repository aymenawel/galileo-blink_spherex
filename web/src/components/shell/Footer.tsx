/** The close of every page: the name, where the data comes from, the licence and the team. */
import { COPY, REPOSITORY_URL } from "../../lib/copy";
import { Link } from "../../router";

/**
 * The name as a mark of its own. Each word has an i: the dot of the first is an open ring,
 * where the star was, and the dot of the second is the star, where it is now. The letters
 * are dotless and the two dots are drawn, so the styled name is hidden from screen readers.
 */
function NameMark() {
  return (
    <span className="namemark">
      Gal{"ı"}
      <span className="namemark__dot namemark__dot--was" />
      leo Bl{"ı"}
      <span className="namemark__dot" />
      nk
    </span>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div>
        <p className="footer__name" aria-hidden="true">
          <NameMark />
        </p>
        <p className="footer__tagline">{COPY.brand.tagline}</p>
      </div>
      <div>
        <h2 className="footer__title">{COPY.footer.dataTitle}</h2>
        <ul>
          {COPY.footer.data.map((credit) => (
            <li key={credit}>{credit}</li>
          ))}
        </ul>
      </div>
      <div>
        <h2 className="footer__title">{COPY.footer.team}</h2>
        <ul>
          <li>
            <Link to="/how-it-works">{COPY.nav.how}</Link>
          </li>
          <li>
            <Link to="/about">{COPY.nav.about}</Link>
          </li>
          <li>
            <a href={REPOSITORY_URL} target="_blank" rel="noreferrer">
              {COPY.footer.repository}
            </a>{" "}
            ({COPY.footer.licence})
          </li>
        </ul>
        <p className="footer__disclaimer">{COPY.footer.disclaimer}</p>
      </div>
    </footer>
  );
}
