/** The close of every page: the name, where the data comes from, the licence and the team. */
import { COPY, REPOSITORY_URL } from "../../lib/copy";
import { Link } from "../../router";
import { BlinkMark } from "./Wordmark";

export function Footer() {
  return (
    <footer className="footer">
      <p className="footer__name" aria-hidden="true">
        <BlinkMark size={64} />
        {COPY.brand.name}
      </p>
      <div className="footer__columns">
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
      </div>
    </footer>
  );
}
