/**
 * The Explore page once a view is ready. The first screen is the picture, as tall as the
 * window, with its dates in a rail beside it and the one result that matters; every number
 * behind it is further down, under "The details". Keeps the address bar in step with what
 * is on screen.
 */
import { Telescope } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ViewRequest } from "../../api/client";
import type { View } from "../../api/types";
import { useAbout } from "../../api/useResource";
import { firstLookFor } from "../../content/firstLooks";
import { COPY, VISIT_COPY, viewTitle } from "../../lib/copy";
import { exploreAddress, type ExploreChoices } from "../../lib/exploreAddress";
import { useReducedMotion } from "../../lib/useReducedMotion";
import { Link, navigate } from "../../router";
import { BrightnessPanel } from "../panels/BrightnessPanel";
import { FlagsPanel } from "../panels/FlagsPanel";
import { HonestyPanel } from "../panels/HonestyPanel";
import { MotionPanel } from "../panels/MotionPanel";
import { MoversPanel } from "../panels/MoversPanel";
import { SearchMethodPanel } from "../panels/SearchMethodPanel";
import { SpectrumPanel } from "../panels/SpectrumPanel";
import { SubjectPanel } from "../panels/SubjectPanel";
import { VisitPanel } from "../panels/VisitPanel";
import { CameraStrip } from "../viewport/CameraStrip";
import { DatePair } from "../viewport/DatePair";
import { SeasonTimeline } from "../viewport/SeasonTimeline";
import { ModePills } from "../viewport/ModePills";
import { TransportBar } from "../viewport/TransportBar";
import { LookReadout, Viewport } from "../viewport/Viewport";
import { FirstLook, showStep } from "./FirstLook";
import { MotionResult, ViewTitle, VisitResult } from "./Summary";
import { CameraPicker, ShowPicker, ViewActions } from "./ViewControls";
import { useWorkspace, type Workspace } from "./useWorkspace";

interface ExploreWorkspaceProps {
  view: View;
  request: ViewRequest;
  /** The name the visitor searched for, when the place is not a test target. */
  name: string | null;
  /** Choices read from the address when the page was opened. */
  initial: ExploreChoices;
}

const TYPING_TARGETS = "input, textarea, select, [contenteditable], [role=slider]";
const PRESSABLE_TARGETS = "button, a, summary";

/** One line about what the picture shows and what to look for, for every way of looking. */
function noteFor(mode: Workspace["mode"], visit: boolean): string {
  if (mode === "blink") return visit ? VISIT_COPY.modes.blink.hint : COPY.viewport.blinkNote;
  if (visit) return mode === "change" ? VISIT_COPY.subtractedNote : VISIT_COPY.staticNote;
  if (mode === "compare") return COPY.viewport.compareNote;
  if (mode === "change") return COPY.viewport.changeNote;
  return COPY.viewport.combinedNote;
}

/** Arrow keys step through the dates and Space plays or pauses, unless the visitor is typing. */
function useBlinkKeys(ws: Workspace): void {
  const { stepping, step, togglePlaying } = ws;
  useEffect(() => {
    if (!stepping) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest(TYPING_TARGETS)) return;
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        event.preventDefault();
        step(event.key === "ArrowRight" ? 1 : -1);
      } else if (event.key === " " && !target?.closest(PRESSABLE_TARGETS)) {
        event.preventDefault();
        togglePlaying();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stepping, step, togglePlaying]);
}

/**
 * Write the visitor's choices into the address, so the page can be shared as it is. While
 * the blink is playing the date is left out: a link should not depend on the instant it was copied.
 */
function useAddressSync(ws: Workspace, request: ViewRequest, name: string | null): void {
  const { camera, mode, a, b, playing } = ws;
  const address = exploreAddress(request, name, { camera, mode, a, b, season: playing ? null : ws.season });
  useEffect(() => navigate(address, { replace: true }), [address]);
}

export function ExploreWorkspace({ view: built, request, name, initial }: ExploreWorkspaceProps) {
  // A view is shared by everyone who opens that place, so it carries no searched name;
  // the name this visitor typed is put on their copy, for titles and sentences.
  const view = useMemo(() => (name && !built.target && !built.label ? { ...built, label: name } : built), [built, name]);
  const ws = useWorkspace(view, initial);
  const about = useAbout();
  useBlinkKeys(ws);
  useAddressSync(ws, request, name);

  // The browser tab names the place, so several open views can be told apart.
  const tabTitle = ws.visit ? ws.place : viewTitle(view, name);
  useEffect(() => {
    document.title = `${tabTitle} · ${COPY.brand.name}`;
  }, [tabTitle]);

  const picksDates = !ws.visit && (ws.mode === "compare" || ws.mode === "change");
  const leftOut = view.seasons_left_out ?? 0;
  const modeNote = noteFor(ws.mode, ws.visit);
  const seasonLabel = (index: number) => view.seasons.find((s) => s.index === index)?.label ?? "";

  // The guide: closed until asked for, and closed again when another place is opened.
  const reducedMotion = useReducedMotion();
  const guide = useMemo(() => firstLookFor(view), [view]);
  const [guideStep, setGuideStep] = useState<number | null>(null);
  useEffect(() => setGuideStep(null), [view.key]);
  const viewer = useRef<HTMLDivElement>(null);
  const openGuideStep = (index: number) => {
    // On a narrow screen the guide sits right under the picture: bring both into view once.
    if (guideStep === null && window.matchMedia("(max-width: 999px)").matches) {
      window.requestAnimationFrame(() => viewer.current?.scrollIntoView({ block: "start" }));
    }
    setGuideStep(index);
    showStep(ws, guide[index]?.show, reducedMotion);
  };

  const flagsPanel = (
    <FlagsPanel
      view={view}
      camera={ws.camera}
      season={ws.shownSeason}
      flags={about.status === "ready" ? about.data.flags : undefined}
      overlayOn={ws.overlays.flags}
      overlayAvailable={ws.mode === "blink"}
      onToggleOverlay={() => ws.toggleOverlay("flags")}
    />
  );

  return (
    <>
      <div className={guideStep === null ? "viewer" : "viewer viewer--guided"} ref={viewer}>
        <div className="viewer__modes">
          <ModePills mode={ws.mode} visit={ws.visit} onSelect={ws.selectMode} />
        </div>

        <figure className="viewer__sky">
          <Viewport ws={ws} />
          <figcaption>
            <LookReadout ws={ws} />
          </figcaption>
        </figure>

        <div className="rail">
          {ws.stepping && (
            <SeasonTimeline
              view={view}
              season={ws.season}
              cameraSeasons={ws.cameraSeasons}
              camera={ws.camera}
              onSelect={ws.selectSeason}
            />
          )}
          {picksDates && (
            <DatePair
              view={view}
              cameraSeasons={ws.cameraSeasons}
              a={ws.a}
              b={ws.b}
              onA={ws.selectA}
              onB={ws.selectB}
              onSwap={ws.swapDates}
            />
          )}
          {ws.mode === "change" && !ws.visit && (
            <ul className="change-legend" aria-label={COPY.viewport.changeLegend.label}>
              <li className="change-legend__warm">{COPY.viewport.changeLegend.brighter(seasonLabel(ws.a))}</li>
              <li className="change-legend__cool">{COPY.viewport.changeLegend.fainter(seasonLabel(ws.a))}</li>
              <li className="change-legend__dark">{COPY.viewport.changeLegend.same}</li>
            </ul>
          )}
          <p className="rail__note">{modeNote}</p>
          {ws.stepping && (
            <TransportBar
              playing={ws.playing}
              speed={ws.speed}
              enabled={ws.cameraSeasons.length > 1}
              onStep={ws.step}
              onTogglePlaying={ws.togglePlaying}
              onSpeed={ws.selectSpeed}
            />
          )}
        </div>

        <aside className="side">
          <ViewTitle view={view} searchedName={name} />
          {guideStep === null ? (
            <div className="side__result">
              {ws.visit ? <VisitResult view={view} /> : <MotionResult view={view} />}
              <div className="side__next">
                <button type="button" className="button button--quiet" onClick={() => openGuideStep(0)}>
                  <Telescope size={16} aria-hidden="true" />
                  {COPY.firstLook.start}
                </button>
                <a className="side__more" href="#details">
                  {COPY.explore.detailsLink}
                </a>
              </div>
            </div>
          ) : (
            <FirstLook steps={guide} index={guideStep} onIndex={openGuideStep} onClose={() => setGuideStep(null)} />
          )}
        </aside>
      </div>

      <div className="tools">
        {!ws.visit && <CameraPicker ws={ws} />}
        <ShowPicker ws={ws} />
        <ViewActions ws={ws} request={request} name={name} />
        <p className="tools__note">
          {ws.stepping ? `${ws.visit ? VISIT_COPY.keyboardHint : COPY.viewport.keyboardHint} ` : ""}
          {COPY.viewport.noData}.
          {leftOut > 0 && ws.mode === "blink" ? ` ${COPY.timeline.leftOut(leftOut)}` : ""}
        </p>
      </div>

      <section className="details" id="details" aria-labelledby="details-title">
        <header className="details__head">
          <h2 className="details__title" id="details-title">
            {COPY.explore.detailsTitle}
          </h2>
          <p className="details__lede">
            {COPY.explore.detailsLede}{" "}
            <Link to="/how-it-works#words">{COPY.explore.wordsLink}</Link>
          </p>
        </header>
        {ws.visit ? (
          <div className="details__grid">
            <MoversPanel view={view} />
            <VisitPanel view={view} />
            <SearchMethodPanel />
            <HonestyPanel view={view} />
            <div className="details__wide">{flagsPanel}</div>
          </div>
        ) : (
          <div className="details__grid">
            <MotionPanel view={view} camera={ws.camera} />
            <SubjectPanel view={view} />
            {view.brightness_change && (
              <div className="details__wide">
                <BrightnessPanel view={view} />
              </div>
            )}
            <div className="details__wide">
              <SpectrumPanel view={view} bands={about.status === "ready" ? about.data.cameras : undefined} />
            </div>
            <div className="details__wide">
              <CameraStrip ws={ws} />
            </div>
            {flagsPanel}
            <HonestyPanel view={view} />
          </div>
        )}
      </section>
    </>
  );
}
