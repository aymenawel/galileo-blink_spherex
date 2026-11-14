/**
 * The Explore page once a view is ready: the main picture with its controls, and the
 * panels that explain what it shows. Keeps the address bar in step with what is on screen.
 */
import { useEffect, useMemo } from "react";
import type { ViewRequest } from "../../api/client";
import type { View } from "../../api/types";
import { useAbout } from "../../api/useResource";
import { COPY, VISIT_COPY } from "../../lib/copy";
import { exploreAddress, type ExploreChoices } from "../../lib/exploreAddress";
import { riseOrder } from "../../lib/stagger";
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
import { Viewport } from "../viewport/Viewport";
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

function sixMonthNote(mode: Workspace["mode"]): string {
  if (mode === "blink") return COPY.viewport.keyboardHint;
  if (mode === "compare") return COPY.viewport.compareNote;
  if (mode === "change") return COPY.viewport.changeNote;
  return COPY.viewport.combinedNote;
}

function visitNote(mode: Workspace["mode"]): string {
  if (mode === "change") return VISIT_COPY.subtractedNote;
  if (mode === "combined") return VISIT_COPY.staticNote;
  return VISIT_COPY.keyboardHint;
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

  return (
    <div className="bento">
      <div className="bento__left">
        <section className="panel stage rise" aria-label={COPY.viewport.stageLabel} style={riseOrder(0)}>
          <Viewport ws={ws} />
          <div className="stage__below">
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
            <p className="stage__note muted">
              {ws.visit ? visitNote(ws.mode) : sixMonthNote(ws.mode)}{" "}
              {COPY.viewport.noData}.{leftOut > 0 && ws.mode === "blink" ? ` ${COPY.timeline.leftOut(leftOut)}` : ""}
            </p>
          </div>
        </section>
        <div className="rise" style={riseOrder(2)}>
          {ws.visit ? <SearchMethodPanel /> : <CameraStrip ws={ws} />}
        </div>
      </div>

      <div className="bento__right">
        <div className="rise" style={riseOrder(1)}>
          {ws.visit ? <VisitPanel view={view} /> : <SubjectPanel view={view} searchedName={name} />}
        </div>
        <div className="rise bento__grow" style={riseOrder(3)}>
          {ws.visit ? <MoversPanel view={view} /> : <MotionPanel view={view} camera={ws.camera} />}
        </div>
      </div>

      {!ws.visit && (
        <div className="bento__spectrum">
          <SpectrumPanel view={view} bands={about.status === "ready" ? about.data.cameras : undefined} />
        </div>
      )}
      <div className={ws.visit ? "bento__flags bento__flags--wide" : "bento__flags"}>
        <FlagsPanel
          view={view}
          camera={ws.camera}
          season={ws.shownSeason}
          flags={about.status === "ready" ? about.data.flags : undefined}
          overlayOn={ws.overlays.flags}
          overlayAvailable={ws.mode === "blink"}
          onToggleOverlay={() => ws.toggleOverlay("flags")}
        />
      </div>
      <div className="bento__honesty">
        <HonestyPanel view={view} />
      </div>
    </div>
  );
}
