/**
 * The home page's first screen: NASA's SPHEREx all-sky map fills it behind the words. The
 * five test targets sit on the map as rings, and Barnard's Star is pulled out of it as a large
 * blinking eyepiece, joined to its ring by a cone of light like a lens lifted off a chart.
 * Pointing at the sky reads its position; clicking opens that place.
 *
 * On a narrow screen the map stands upright (turned a quarter turn), so the whole sky fills a
 * phone instead of shrinking to a strip, and a tap picks a place before anything opens.
 */
import { ArrowRight, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type MouseEvent, type PointerEvent } from "react";
import { useTargets } from "../../api/useResource";
import { COPY } from "../../lib/copy";
import { exploreAddress } from "../../lib/exploreAddress";
import { formatDec, formatRa } from "../../lib/format";
import { setPreviewsPaused, usePreviewsPaused } from "../../lib/previewMotion";
import { mapToSky, skyToMap } from "../../lib/skyMap";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { Link, navigate } from "../../router";
import { Eyepiece } from "../SkyIndex";
import { SearchBox } from "../shell/SearchBox";

const WORDS = COPY.home.skyHero;

/* ------------------------------------------------------------------ the picture */
const IMAGE_URL = "/sky/allsky.webp";
const IMAGE_WIDTH = 2000;
const IMAGE_HEIGHT = 1000;
const LENS_TARGET = "barnard";
/** Where Barnard's Star sits before the target list arrives, so the cone draws at once. */
const LENS_FALLBACK = { ra: 269.4464, dec: 4.7686 };

interface Spot {
  x: number;
  y: number;
  ra: number;
  dec: number;
}

interface Cone {
  /** The ring on the map and the lens, in pixels of the hero. */
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  r2: number;
  /** The two tangent lines, ring side first. */
  a: [number, number, number, number];
  b: [number, number, number, number];
}

const RING_RADIUS = 12;
/** The thin ring drawn around the lens sits this far outside the picture. */
const RIM_GAP = 10;

/** The two outer tangent lines of a small circle (the ring) and a large one (the lens). */
function coneBetween(x1: number, y1: number, x2: number, y2: number, r2: number): Cone | null {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const d = Math.hypot(dx, dy);
  if (d <= r2 + RING_RADIUS) return null;
  const ux = dx / d;
  const uy = dy / d;
  const cos = (r2 - RING_RADIUS) / d;
  const sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const line = (sign: number): [number, number, number, number] => {
    const nx = ux * cos - sign * uy * sin;
    const ny = uy * cos + sign * ux * sin;
    return [x1 - RING_RADIUS * nx, y1 - RING_RADIUS * ny, x2 - r2 * nx, y2 - r2 * ny];
  };
  return { x1, y1, x2, y2, r2, a: line(1), b: line(-1) };
}

function placeAddress(ra: number, dec: number): string {
  const r = Number(ra.toFixed(4)) % 360;
  return `/explore?ra=${r.toFixed(4)}&dec=${dec.toFixed(4)}`;
}

/** The map stands upright below this width; a tap only picks a place where there is no pointer to hover with. */
const UPRIGHT = "(max-width: 760px)";
const TOUCH = "(hover: none)";

/** True while a media query matches. */
function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = () => setMatches(list.matches);
    onChange();
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

interface Point {
  x: number;
  y: number;
}

/** Where a point of the map picture is drawn: as it is, or a quarter turn clockwise when the map stands upright. */
function drawn(at: Point, upright: boolean): Point {
  return upright ? { x: 1 - at.y, y: at.x } : at;
}

/** The reverse: a point of the drawn map, back on the picture. */
function pictured(at: Point, upright: boolean): Point {
  return upright ? { x: at.y, y: 1 - at.x } : at;
}

function spotAt(event: { clientX: number; clientY: number }, frame: HTMLElement, upright: boolean): Spot | null {
  const box = frame.getBoundingClientRect();
  if (box.width === 0 || box.height === 0) return null;
  const x = (event.clientX - box.left) / box.width;
  const y = (event.clientY - box.top) / box.height;
  const onPicture = pictured({ x, y }, upright);
  const sky = mapToSky(onPicture.x, onPicture.y);
  return sky ? { x, y, ...sky } : null;
}

/**
 * Where a spot's position is written, as class names. Beside the spot on a wide screen; on the
 * upright map above it (or below, near the top), kept inside the screen's edges, so it never
 * lands under the lens at the lower left.
 */
function readoutPlace(spot: Point, upright: boolean): string {
  if (!upright) return spot.x > 0.78 ? " skyhero-pointer__read--left" : "";
  const across = spot.x < 0.35 ? "start" : spot.x > 0.65 ? "end" : "mid";
  return ` skyhero-pointer__read--${spot.y > 0.1 ? "above" : "below"} skyhero-pointer__read--${across}`;
}

export function SkyHero() {
  const upright = useMedia(UPRIGHT);
  const touch = useMedia(TOUCH);
  const targets = useTargets();
  const list = targets.status === "ready" ? targets.data : [];
  const lensTarget = list.find((t) => t.id === LENS_TARGET);
  const lensKey = lensTarget?.ready ? lensTarget.key : null;
  const lensAt = drawn(skyToMap(lensTarget?.ra ?? LENS_FALLBACK.ra, lensTarget?.dec ?? LENS_FALLBACK.dec), upright);

  const paused = usePreviewsPaused();
  const reducedMotion = useReducedMotion();
  const moving = !paused && !reducedMotion;

  const section = useRef<HTMLElement>(null);
  const map = useRef<HTMLDivElement>(null);
  const lens = useRef<HTMLDivElement>(null);
  const [spot, setSpot] = useState<Spot | null>(null);
  const [cone, setCone] = useState<Cone | null>(null);

  // The cone is measured, not laid out: it joins two things that the grid places independently.
  useLayoutEffect(() => {
    const root = section.current;
    const frame = map.current;
    const glass = lens.current;
    if (!root || !frame || !glass) return;
    const measure = () => {
      // The sky spans the window exactly: 100vw would include the scroll bar and overflow.
      root.style.setProperty("--skyhero-vw", `${document.documentElement.clientWidth}px`);
      const s = root.getBoundingClientRect();
      // A target that sits under the words keeps its ring but shows its name only when asked.
      const words = Array.from(
        root.querySelectorAll<HTMLElement>(".skyhero-title__line, .skyhero-lede, .skyhero-search .search__field, .skyhero-search .settings, .skyhero-lens__caption"),
      ).map((el) => el.getBoundingClientRect());
      const g = glass.getBoundingClientRect();
      const lensDisc = { x: g.left + g.width / 2, y: g.top + g.height / 2, r: g.width / 2 + RIM_GAP };
      /** Whether a box touches the words, or the round lens (a circle, not its bounding box). */
      const screenWidth = document.documentElement.clientWidth;
      const covered = (r: DOMRect) => {
        // A name that would run off the side of the screen counts as covered too.
        if (r.left < 4 || r.right > screenWidth - 4) return true;
        if (words.some((w) => r.right > w.left && r.left < w.right && r.bottom > w.top && r.top < w.bottom)) return true;
        const nx = Math.max(r.left, Math.min(lensDisc.x, r.right));
        const ny = Math.max(r.top, Math.min(lensDisc.y, r.bottom));
        return Math.hypot(nx - lensDisc.x, ny - lensDisc.y) < lensDisc.r;
      };
      root.querySelectorAll<HTMLElement>(".skyhero-target:not(.skyhero-target--lensed)").forEach((link) => {
        const ring = link.querySelector(".skyhero-target__ring")?.getBoundingClientRect();
        const label = link.querySelector(".skyhero-target__name");
        if (!ring || !label) return;
        // A name that runs into the words moves to the other side of its ring before it hides.
        link.classList.remove("skyhero-target--under", "skyhero-target--flip");
        if (covered(label.getBoundingClientRect())) link.classList.add("skyhero-target--flip");
        if (covered(label.getBoundingClientRect())) link.classList.remove("skyhero-target--flip");
        link.classList.toggle("skyhero-target--under", covered(ring) || covered(label.getBoundingClientRect()));
      });
      const core = root.querySelector<HTMLElement>(".skyhero-core__label");
      if (core) {
        core.classList.remove("skyhero-core__label--hidden");
        const c = core.getBoundingClientRect();
        core.classList.toggle("skyhero-core__label--hidden", covered(c));
      }
      const m = frame.getBoundingClientRect();
      const l = glass.getBoundingClientRect();
      if (m.width === 0 || l.width === 0) return;
      // Measured boxes include any transform on the page; the SVG is drawn in the hero's own pixels.
      const k = root.offsetWidth ? s.width / root.offsetWidth : 1;
      setCone(
        coneBetween(
          (m.left - s.left + lensAt.x * m.width) / k,
          (m.top - s.top + lensAt.y * m.height) / k,
          (l.left - s.left + l.width / 2) / k,
          (l.top - s.top + l.height / 2) / k,
          l.width / 2 / k + RIM_GAP,
        ),
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(root);
    observer.observe(frame);
    observer.observe(glass);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [lensAt.x, lensAt.y, list.length, upright]);

  const onPointerMove = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!map.current || event.pointerType === "touch") return;
      setSpot(spotAt(event, map.current, upright));
    },
    [upright],
  );

  // With a pointer, a click opens the place under it. On a touch screen a tap only picks the
  // place (a tap is easy to make by accident while scrolling); the button beside it opens it.
  const onClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (!map.current || event.defaultPrevented) return;
      const here = spotAt(event, map.current, upright);
      if (touch) setSpot(here);
      else if (here) navigate(placeAddress(here.ra, here.dec));
    },
    [upright, touch],
  );

  const core = drawn(skyToMap(266.405, -28.936), upright); // Sagittarius A*, the centre of the Galaxy

  return (
    <section ref={section} className={`skyhero${moving ? " skyhero--moving" : ""}`} aria-labelledby="skyhero-title">
      {/* The whole sky, behind everything. */}
      <div
        className={`skyhero-sky${spot ? " skyhero-sky--on" : ""}`}
        onPointerMove={onPointerMove}
        onPointerLeave={(event) => {
          if (event.pointerType !== "touch") setSpot(null);
        }}
        onClick={onClick}
      >
        <div ref={map} className="skyhero-map" role="group" aria-label={WORDS.mapLabel}>
          <img
            className="skyhero-map__image"
            src={IMAGE_URL}
            width={IMAGE_WIDTH}
            height={IMAGE_HEIGHT}
            alt={WORDS.mapAlt}
            decoding="async"
            draggable={false}
            onLoad={(event) => event.currentTarget.classList.add("is-loaded")}
          />

          <span className="skyhero-core" style={{ left: `${core.x * 100}%`, top: `${core.y * 100}%` }} aria-hidden="true">
            <span className="skyhero-core__label">{WORDS.coreLabel}</span>
          </span>

          {spot && (
            <span
              className={`skyhero-pointer${touch ? " skyhero-pointer--picked" : ""}`}
              style={{ left: `${spot.x * 100}%`, top: `${spot.y * 100}%` }}
              aria-hidden={touch ? undefined : true}
            >
              <span className={`skyhero-pointer__read${readoutPlace(spot, upright)}`}>
                <span>{formatRa(spot.ra)}</span>
                <span>{formatDec(spot.dec)}</span>
                {touch && (
                  <button
                    type="button"
                    className="skyhero-pointer__open"
                    onClick={(event) => {
                      event.stopPropagation();
                      navigate(placeAddress(spot.ra, spot.dec));
                    }}
                  >
                    {WORDS.openPlace}
                    <ArrowRight size={14} aria-hidden="true" />
                  </button>
                )}
              </span>
            </span>
          )}

          <ul className="skyhero-targets">
            {list.map((target) => {
              const at = drawn(skyToMap(target.ra, target.dec), upright);
              const side = at.x > (upright ? 0.6 : 0.8) ? " skyhero-target--left" : "";
              const lensed = target.id === LENS_TARGET ? " skyhero-target--lensed" : "";
              return (
                <li key={target.id}>
                  <Link
                    to={exploreAddress({ kind: "target", id: target.id })}
                    className={`skyhero-target${side}${lensed}`}
                    style={{ left: `${at.x * 100}%`, top: `${at.y * 100}%` }}
                    aria-label={WORDS.targetLinkLabel(target.name)}
                    onClick={(event) => event.stopPropagation()}
                  >
                    <span className="skyhero-target__ring" aria-hidden="true" />
                    <span className="skyhero-target__name" aria-hidden="true">
                      {target.name}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      {/* The lens pulled out of the map: a cone from Barnard's ring to the eyepiece. */}
      {cone && (
        <svg className="skyhero-cone" aria-hidden="true" focusable="false">
          <defs>
            <linearGradient id="skyhero-cone-fill" gradientUnits="userSpaceOnUse" x1={cone.x1} y1={cone.y1} x2={cone.x2} y2={cone.y2}>
              <stop offset="0" className="skyhero-cone__stop-near" />
              <stop offset="1" className="skyhero-cone__stop-far" />
            </linearGradient>
          </defs>
          <polygon
            className="skyhero-cone__fill"
            points={`${cone.a[0]},${cone.a[1]} ${cone.a[2]},${cone.a[3]} ${cone.x2},${cone.y2} ${cone.b[2]},${cone.b[3]} ${cone.b[0]},${cone.b[1]}`}
          />
          <line className="skyhero-cone__edge" x1={cone.a[0]} y1={cone.a[1]} x2={cone.a[2]} y2={cone.a[3]} />
          <line className="skyhero-cone__edge" x1={cone.b[0]} y1={cone.b[1]} x2={cone.b[2]} y2={cone.b[3]} />
          <circle className="skyhero-cone__rim" cx={cone.x2} cy={cone.y2} r={cone.r2} />
          {[0, 90, 180, 270].map((angle) => {
            const rad = (angle * Math.PI) / 180;
            const inner = cone.r2 - 6;
            const outer = cone.r2 + 8;
            return (
              <line
                key={angle}
                className="skyhero-cone__tick"
                x1={cone.x2 + Math.cos(rad) * inner}
                y1={cone.y2 + Math.sin(rad) * inner}
                x2={cone.x2 + Math.cos(rad) * outer}
                y2={cone.y2 + Math.sin(rad) * outer}
              />
            );
          })}
        </svg>
      )}

      <h1 className="skyhero-title" id="skyhero-title">
        <span className="skyhero-title__line">{WORDS.headlineA}</span>{" "}
        <span className="skyhero-title__line skyhero-title__line--b">{WORDS.headlineB}</span>
      </h1>

      <div className="skyhero-intro">
        <p className="skyhero-lede">
          {WORDS.ledeA} <span className="skyhero-lede__b">{WORDS.ledeB}</span>
        </p>
        <div className="skyhero-search">
          <SearchBox size="large" />
        </div>
      </div>

      <figure className="skyhero-lens">
        <div ref={lens} className="skyhero-lens__glass">
          <Link to={exploreAddress({ kind: "target", id: LENS_TARGET })} className="skyhero-lens__link" aria-label={WORDS.lensLinkLabel}>
            <Eyepiece viewKey={lensKey} beat={850} showDate />
          </Link>
        </div>
        <figcaption className="skyhero-lens__caption">
          <span className="skyhero-lens__name">{WORDS.lensName}</span>
          <span className="skyhero-lens__line">{WORDS.lensLine}</span>
          <span className="skyhero-lens__actions">
            <Link to={exploreAddress({ kind: "target", id: LENS_TARGET })}>{WORDS.lensOpen}</Link>
            {!reducedMotion && (
              <button type="button" className="skyhero-pause" onClick={() => setPreviewsPaused(!paused)}>
                {paused ? <Play size={14} aria-hidden="true" /> : <Pause size={14} aria-hidden="true" />}
                {paused ? COPY.home.previewsPlay : COPY.home.previewsPause}
              </button>
            )}
          </span>
        </figcaption>
      </figure>

      <div className="skyhero-foot">
        <p className="skyhero-hint">
          <span className="skyhero-hint__point">{WORDS.hint}</span>
          <span className="skyhero-hint__touch">{WORDS.hintTouch}</span>
        </p>
        <p className="skyhero-credit">{WORDS.credit}</p>
      </div>
    </section>
  );
}
