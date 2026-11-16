/**
 * The "How it works" page. The short version comes first: six numbered steps, each with a real
 * SPHEREx picture of Barnard's Star or a small drawing. The technical text follows as rows that
 * open in place, then the words used on the site and the limits.
 */
import { Plus } from "lucide-react";
import { useEffect, useMemo } from "react";
import { fileUrl } from "../api/client";
import { useAbout, useTargets } from "../api/useResource";
import { useReadyView } from "../api/useView";
import type { CameraKey, View } from "../api/types";
import { Eyepiece } from "../components/SkyIndex";
import {
  CAMERA_TABLE,
  FLAGS_TABLE,
  HOW_IT_WORKS_INTRO,
  LIMITS,
  SECTIONS,
  SHORT_VERSION,
  TOPIC_SUMMARY,
} from "../content/howItWorks";
import { CAMERA_BANDS, CAMERA_KEYS, defaultCamera, looksOf } from "../lib/cameras";
import { COPY, changeAlt, lookAlt, subjectName } from "../lib/copy";
import { microns } from "../lib/format";
import { usePreviewsPaused } from "../lib/previewMotion";
import { skyToMap } from "../lib/skyMap";
import { useReducedMotion } from "../lib/useReducedMotion";
import { Link } from "../router";

/** The six cameras and their wavelengths. */
function CameraTable() {
  const about = useAbout();
  const bandOf = (key: CameraKey) => (about.status === "ready" ? about.data.cameras[key] : undefined) ?? CAMERA_BANDS[key];
  return (
    <table className="doc-table">
      <caption className="visually-hidden">{CAMERA_TABLE.caption}</caption>
      <thead>
        <tr>
          <th scope="col">{CAMERA_TABLE.camera}</th>
          <th scope="col">{CAMERA_TABLE.band}</th>
        </tr>
      </thead>
      <tbody>
        {CAMERA_KEYS.map((key) => (
          <tr key={key}>
            <th scope="row">{COPY.cameras.camera(key)}</th>
            <td>{microns(bandOf(key))}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** NASA's quality flags, what each means, and how the picture treats it. */
function FlagsTable() {
  const about = useAbout();
  if (about.status === "loading") return <p className="muted">{FLAGS_TABLE.loading}</p>;
  if (about.status === "failed") return <p className="note">{FLAGS_TABLE.failed}</p>;
  return (
    <div className="doc-table__scroll">
      <table className="doc-table">
        <thead>
          <tr>
            <th scope="col">{FLAGS_TABLE.flag}</th>
            <th scope="col">{FLAGS_TABLE.meaning}</th>
            <th scope="col">{FLAGS_TABLE.treatment}</th>
          </tr>
        </thead>
        <tbody>
          {about.data.flags.map((flag) => (
            <tr key={flag.name}>
              <th scope="row">
                {flag.name}
              </th>
              <td>{flag.meaning}</td>
              <td className={flag.treated_as_no_data ? "doc-table__blank" : "muted"}>
                {flag.treated_as_no_data ? FLAGS_TABLE.blank : FLAGS_TABLE.kept}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TOPICS = SECTIONS.filter((section) => section.id !== "words");
const GLOSSARY = SECTIONS.find((section) => section.id === "words");

// ------------------------------------------------------------------ helpers
const CHANGE_CAMERA: CameraKey = "5";

function seasonLabel(view: View, season: number): string {
  return view.seasons.find((s) => s.index === season)?.label ?? "";
}

/** The camera used for the stacked and change pictures: camera 5 when it has two looks. */
function cameraFor(view: View): CameraKey {
  return looksOf(view, CHANGE_CAMERA).length > 1 ? CHANGE_CAMERA : defaultCamera(view);
}

/** A thin eyepiece ring with four ticks, drawn around a round picture. */
function LensRing() {
  return (
    <svg className="howit-lens__ring" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="48.5" />
      <path d="M50 0.5 V4 M50 96 V99.5 M0.5 50 H4 M96 50 H99.5" />
    </svg>
  );
}

/** A round picture whose black melts into the page, inside its ring. */
function Disc({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  return (
    <div className={`howit-lens ${className}`}>
      <div className="howit-disc">{src ? <img src={src} alt={alt} loading="lazy" decoding="async" /> : null}</div>
      <LensRing />
    </div>
  );
}

function AllSky({ alt }: { alt: string }) {
  return (
    <div className="howit-sky">
      <img src="/sky/allsky.webp" alt={alt} width={2000} height={1000} loading="lazy" decoding="async" />
    </div>
  );
}

// ------------------------------------------------------------------ the six pictures
function PictureSky() {
  return (
    <figure className="howit-fig howit-fig--wide">
      <AllSky alt={SHORT_VERSION.skyAlt} />
      <figcaption>{SHORT_VERSION.skyCaption}</figcaption>
    </figure>
  );
}

function PicturePlace({ view, ra, dec }: { view: View | null; ra: number | null; dec: number | null }) {
  const at = ra != null && dec != null ? skyToMap(ra, dec) : { x: 0.42, y: 0.4 };
  // Geometry in units of the figure's width: the sky oval is 1 x 0.5 at the top; the close-up
  // is a disc of diameter 0.42 in the lower right; the figure is 0.86 tall.
  const H = 0.86;
  const ring = { x: at.x, y: at.y * 0.5 };
  const centre = { x: 0.75, y: H - 0.21 };
  const dx = centre.x - ring.x;
  const dy = centre.y - ring.y;
  const length = Math.hypot(dx, dy) || 1;
  const start = { x: ring.x + (dx / length) * 0.022, y: ring.y + (dy / length) * 0.022 };
  const end = { x: centre.x - (dx / length) * 0.216, y: centre.y - (dy / length) * 0.216 };
  const camera = view ? defaultCamera(view) : null;
  const look = view && camera ? looksOf(view, camera)[0] : undefined;
  const band = view && camera ? view.cameras[camera]?.band : undefined;
  const place = view ? subjectName(view) : "Barnard's Star";
  return (
    <figure className="howit-fig howit-place">
      <div className="howit-place__frame" style={{ aspectRatio: `1 / ${H}` }}>
        <div className="howit-place__sky">
          <AllSky alt="" />
        </div>
        <svg className="howit-place__line" aria-hidden="true">
          <line x1={`${start.x * 100}%`} y1={`${(start.y / H) * 100}%`} x2={`${end.x * 100}%`} y2={`${(end.y / H) * 100}%`} />
        </svg>
        <span className="howit-place__ring" aria-hidden="true" style={{ left: `${ring.x * 100}%`, top: `${(ring.y / H) * 100}%` }} />
        <Disc
          className="howit-place__close"
          src={view && look ? fileUrl(view, look.png) : null}
          alt={view && look && camera && band ? lookAlt(place, camera, band, seasonLabel(view, look.season)) : ""}
        />
      </div>
      <figcaption>{SHORT_VERSION.placeCaption}</figcaption>
    </figure>
  );
}

function StackDrawing({ still }: { still: boolean }) {
  const frames = [
    { r: -26, x: -26, y: -16 },
    { r: 14, x: 22, y: -22 },
    { r: 38, x: 6, y: 24 },
  ];
  return (
    <svg className={still ? "howit-stack__drawing is-still" : "howit-stack__drawing"} viewBox="0 0 200 200" role="img" aria-label={SHORT_VERSION.stackDrawing}>
      {frames.map((f, i) => (
        <rect
          key={`ghost-${i}`}
          className="howit-stack__ghost"
          x="62"
          y="62"
          width="76"
          height="76"
          rx="3"
          transform={`translate(${f.x} ${f.y}) rotate(${f.r} 100 100)`}
        />
      ))}
      {frames.map((f, i) => (
        <rect
          key={`frame-${i}`}
          className="howit-stack__frame"
          x="62"
          y="62"
          width="76"
          height="76"
          rx="3"
          style={{ ["--r" as string]: `${f.r}deg`, ["--x" as string]: `${f.x}px`, ["--y" as string]: `${f.y}px`, animationDelay: `${i * 0.18}s` }}
        />
      ))}
      <g className="howit-stack__upright">
        <rect x="62" y="62" width="76" height="76" rx="3" />
        <circle cx="100" cy="100" r="9" />
        <path d="M100 56 V36 M93 44 L100 36 L107 44" />
        <text x="100" y="27" textAnchor="middle">
          N
        </text>
      </g>
    </svg>
  );
}

function PictureStack({ view, still }: { view: View | null; still: boolean }) {
  const camera = view ? cameraFor(view) : null;
  const looks = view && camera ? looksOf(view, camera) : [];
  const look = looks[looks.length - 1];
  const band = view && camera ? view.cameras[camera]?.band : undefined;
  const place = view ? subjectName(view) : "";
  return (
    <figure className="howit-fig howit-stack">
      <div className="howit-stack__pair">
        <StackDrawing still={still} />
        <Disc
          src={view && look ? fileUrl(view, look.png) : null}
          alt={view && look && camera && band ? lookAlt(place, camera, band, seasonLabel(view, look.season)) : ""}
        />
      </div>
      <figcaption>{view && look && camera ? SHORT_VERSION.stackCaption(camera, seasonLabel(view, look.season), look.n_photos) : " "}</figcaption>
    </figure>
  );
}

function PictureBlink({ viewKey, caption, beat, showDate }: { viewKey: string | null; caption: string; beat: number; showDate: boolean }) {
  return (
    <figure className="howit-fig howit-eye">
      <div className="howit-lens">
        <Eyepiece viewKey={viewKey} beat={beat} showDate={showDate} />
        <LensRing />
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

function PictureChange({ view }: { view: View | null }) {
  const camera = view ? cameraFor(view) : null;
  const looks = view && camera ? looksOf(view, camera) : [];
  const first = looks[0];
  const last = looks[looks.length - 1];
  const place = view ? subjectName(view) : "";
  const a = view && last ? seasonLabel(view, last.season) : "";
  const b = view && first ? seasonLabel(view, first.season) : "";
  return (
    <figure className="howit-fig howit-change">
      <Disc src={view && last?.change ? fileUrl(view, last.change) : null} alt={camera ? changeAlt(place, camera, a, b) : ""} />
      <figcaption>
        <span className="howit-legend">
          <span className="howit-legend__dot howit-legend__dot--now" aria-hidden="true" />
          {SHORT_VERSION.greenNow}
        </span>
        <span className="howit-legend">
          <span className="howit-legend__dot howit-legend__dot--then" aria-hidden="true" />
          {SHORT_VERSION.pinkThen}
        </span>
        {camera && a && <span className="howit-legend howit-legend--plain">{SHORT_VERSION.changeCaption(camera, a, b)}</span>}
      </figcaption>
    </figure>
  );
}

// ------------------------------------------------------------------ the page
export function HowItWorksPage() {
  const targets = useTargets();
  const barnard = targets.status === "ready" ? targets.data.find((t) => t.id === "barnard") : undefined;
  const viewKey = barnard?.ready ? barnard.key : null;
  const view = useReadyView(viewKey);
  const reduced = useReducedMotion();
  const paused = usePreviewsPaused();
  const still = reduced || paused;
  const { title } = HOW_IT_WORKS_INTRO;

  // Open and show the part the address points at, as in /how-it-works#limits.
  useEffect(() => {
    const go = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      const details = target instanceof HTMLDetailsElement ? target : target.closest("details");
      if (details) details.open = true;
      target.scrollIntoView({ block: "start", behavior: "instant" });
    };
    // After the shell's own scroll to the top, and again once the pictures above have settled.
    const timers = [window.setTimeout(go, 120), window.setTimeout(go, 900)];
    window.addEventListener("hashchange", go);
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      window.removeEventListener("hashchange", go);
    };
  }, []);

  const pictures = useMemo(
    () => [
      <PictureSky key="sky" />,
      <PicturePlace key="place" view={view} ra={barnard?.ra ?? null} dec={barnard?.dec ?? null} />,
      <PictureStack key="stack" view={view} still={still} />,
      <PictureBlink key="blink" viewKey={viewKey} caption={SHORT_VERSION.blinkCaption} beat={900} showDate />,
      <PictureBlink key="ring" viewKey={viewKey} caption={SHORT_VERSION.ringCaption} beat={1500} showDate={false} />,
      <PictureChange key="change" view={view} />,
    ],
    [view, viewKey, barnard?.ra, barnard?.dec, still],
  );

  return (
    <div className="page howit">
      <header className="howit-head">
        <p className="howit-eyebrow">{SHORT_VERSION.eyebrow}</p>
        <h1 className="howit-title">
          {title.before}
          <em>{title.emphasis}</em>
          {title.after}
        </h1>
        <p className="howit-lede">{SHORT_VERSION.lede}</p>
      </header>

      <section className="howit-short" aria-labelledby="howit-short-title">
        <h2 className="visually-hidden" id="howit-short-title">
          {SHORT_VERSION.shortTitle}
        </h2>
        <ol className="howit-steps">
          {SHORT_VERSION.steps.map((step, index) => (
            <li key={step.title} className="howit-step">
              <div className="howit-step__text">
                <span className="howit-step__num" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="howit-step__title">
                  <span className="visually-hidden">Step {index + 1}: </span>
                  {step.title}
                </h3>
                {step.body.map((line) => (
                  <p key={line}>{line}</p>
                ))}
                {index === 4 && (
                  <p className="howit-measure">
                    <span className="howit-measure__value">
                      {SHORT_VERSION.measured}
                      <span className="howit-measure__unit"> {SHORT_VERSION.measuredUnit}</span>
                    </span>
                    <span className="howit-measure__error">{SHORT_VERSION.measuredError}</span>
                    <span className="howit-measure__predicted">{SHORT_VERSION.predicted}</span>
                  </p>
                )}
              </div>
              <div className="howit-step__pic">{pictures[index]}</div>
            </li>
          ))}
        </ol>
        <p className="howit-coda">{SHORT_VERSION.coda}</p>
      </section>

      <section className="howit-more" aria-labelledby="howit-more-title">
        <div className="howit-more__rule" aria-hidden="true">
          <span />
        </div>
        <div className="howit-more__grid">
          <div className="howit-more__head">
            <h2 className="howit-more__title" id="howit-more-title">
              {SHORT_VERSION.moreTitle}
            </h2>
            <p className="howit-more__lede">{SHORT_VERSION.moreLede}</p>
            <nav className="howit-more__jump" aria-label={SHORT_VERSION.moreJump}>
              <a href="#words">{SHORT_VERSION.moreWords}</a>
              <a href="#limits">{SHORT_VERSION.moreLimits}</a>
            </nav>
          </div>

          <ul className="howit-topics">
            {TOPICS.map((section, index) => (
              <li key={section.id}>
                <details className="howit-topic" id={section.id}>
                  <summary>
                    <span className="howit-topic__num" aria-hidden="true">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="howit-topic__title">{section.title}</span>
                    <span className="howit-topic__summary">{TOPIC_SUMMARY[section.id]}</span>
                    <span className="howit-topic__mark" aria-hidden="true">
                      <Plus size={18} strokeWidth={1.75} />
                    </span>
                  </summary>
                  <div className="howit-topic__body">
                    {section.paragraphs.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                    {section.id === "cameras" && <CameraTable />}
                    {section.id === "flags" && <FlagsTable />}
                  </div>
                </details>
              </li>
            ))}
          </ul>
        </div>

        {GLOSSARY && (
          <section className="howit-words" id={GLOSSARY.id} aria-labelledby="howit-words-title">
            <div className="howit-part-head">
              <h3 id="howit-words-title">{GLOSSARY.title}</h3>
              {GLOSSARY.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            <dl className="howit-words__list">
              {GLOSSARY.definitions?.map((definition) => (
                <div key={definition.term} className="howit-words__item">
                  <dt>{definition.term}</dt>
                  <dd>{definition.meaning}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        <section className="howit-limits" id={LIMITS.id} aria-labelledby="howit-limits-title">
          <div className="howit-part-head">
            <h3 id="howit-limits-title">{LIMITS.title}</h3>
            <p>{LIMITS.lede}</p>
          </div>
          <ol className="howit-limits__list">
            {LIMITS.items.map((limit, index) => (
              <li key={limit.title}>
                <span className="howit-limits__num" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h4>{limit.title}</h4>
                  <p>{limit.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </section>

      <div className="howit-try">
        <p>{SHORT_VERSION.tryLine}</p>
        <Link to="/explore?target=barnard" className="button button--primary">
          {SHORT_VERSION.tryButton}
        </Link>
      </div>
    </div>
  );
}
