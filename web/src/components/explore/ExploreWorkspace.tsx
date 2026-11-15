/**
 * The Explore page once a view is ready. The first screen is the picture, as tall as the
 * window, with its dates in a rail beside it and the one result that matters; every number
 * behind it is further down, under "The details". Keeps the address bar in step with what
 * is on screen.
 */
import { useEffect, useMemo } from "react";
import type { ViewRequest } from "../../api/client";
import type { View } from "../../api/types";
import { useAbout } from "../../api/useResource";
import { COPY, VISIT_COPY } from "../../lib/copy";
import { exploreAddress, type ExploreChoices } from "../../lib/exploreAddress";
import { navigate } from "../../router";
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

/** One line about what the picture shows, for every way of looking except the plain blink. */
function noteFor(mode: Workspace["mode"], visit: boolean): string | null {
  if (mode === "blink") return null;
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

  const picksDates = !ws.visit && (ws.mode === "compare" || ws.mode === "change");
  const leftOut = view.seasons_left_out ?? 0;
  const modeNote = noteFor(ws.mode, ws.visit);

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
      <div className="viewer">
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
              <li className="change-legend__warm">{COPY.viewport.changeLegend.brighter}</li>
              <li className="change-legend__cool">{COPY.viewport.changeLegend.fainter}</li>
              <li className="change-legend__dark">{COPY.viewport.changeLegend.same}</li>
            </ul>
          )}
          {modeNote && <p className="rail__note">{modeNote}</p>}
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
          <div className="side__result">
            {ws.visit ? <VisitResult view={view} /> : <MotionResult view={view} />}
            <a className="side__more" href="#details">
              {COPY.explore.detailsLink}
            </a>
          </div>
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
          <p className="details__lede">{COPY.explore.detailsLede}</p>
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
