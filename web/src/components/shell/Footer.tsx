/** Credits: where the data comes from, the licence, the source code and the team. */
import { COPY, REPOSITORY_URL } from "../../lib/copy";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__data">
        <p className="eyebrow">{COPY.footer.dataTitle}</p>
        <ul>
          {COPY.footer.data.map((credit) => (
            <li key={credit}>{credit}</li>
          ))}
        </ul>
      </div>
      <div className="footer__meta">
        <p>{COPY.footer.team}</p>
        <p>
          <a href={REPOSITORY_URL} target="_blank" rel="noreferrer">
            {COPY.footer.repository}
          </a>
          <span aria-hidden="true"> · </span>
          <span className="mono">{COPY.footer.licence}</span>
        </p>
        <p className="footer__disclaimer">{COPY.footer.disclaimer}</p>
      </div>
    </footer>
  );
}
