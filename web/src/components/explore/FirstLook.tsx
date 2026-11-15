/**
 * "Show me what to look for": the short guide beside the picture. While it is open it takes
 * the place of the result, and each step sets the page (mode, camera, markers) to match
 * its words.
 */
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { FirstLookShow, FirstLookStep } from "../../content/firstLooks";
import { looksOf, seasonsWithLooks } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import type { Workspace } from "./useWorkspace";

/** Put the page in the state a step describes. */
export function showStep(ws: Workspace, show: FirstLookShow | undefined, reducedMotion: boolean): void {
  if (!show) return;
  const camera = show.camera && looksOf(ws.view, show.camera).length > 0 ? show.camera : ws.camera;
  if (camera !== ws.camera) ws.selectCamera(camera);
  if (show.markers !== undefined) ws.setOverlay("markers", show.markers);
  // An asteroid view has no two-date comparison; its modes are Blink, Subtracted and Static sky.
  if (show.mode && !(ws.visit && show.mode === "compare")) ws.selectMode(show.mode);

  const seasons = seasonsWithLooks(ws.view, camera);
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  if (show.mode === "change" && !ws.visit && first !== undefined && last !== undefined && first !== last) {
    ws.selectA(last);
    ws.selectB(first);
  }
  // Someone who asked their device for less motion gets the last date held still instead.
  const blink = show.blink === "play" && reducedMotion ? "last" : show.blink;
  if (blink === "play") ws.setPlaying(true);
  else if (blink === "first" && first !== undefined) ws.selectSeason(first);
  else if (blink === "last" && last !== undefined) ws.selectSeason(last);
}

interface FirstLookProps {
  steps: FirstLookStep[];
  /** The open step. */
  index: number;
  onIndex: (index: number) => void;
  onClose: () => void;
}

export function FirstLook({ steps, index, onIndex, onClose }: FirstLookProps) {
  const step = steps[index];
  const heading = useRef<HTMLHeadingElement>(null);
  // Each new step is announced and becomes the place the keyboard is.
  useEffect(() => heading.current?.focus({ preventScroll: true }), [index]);
  if (!step) return null;
  const isLast = index === steps.length - 1;

  return (
    <section className="firstlook" aria-label={COPY.firstLook.label}>
      <p className="firstlook__count">
        <span className="firstlook__dots" aria-hidden="true">
          {steps.map((_, i) => (
            <i key={i} data-on={i === index} data-done={i < index} />
          ))}
        </span>
        {COPY.firstLook.count(index + 1, steps.length)}
      </p>
      <h2 className="firstlook__title" ref={heading} tabIndex={-1}>
        {step.title}
      </h2>
      <p className="firstlook__text">{step.text}</p>
      <div className="firstlook__nav">
        {index > 0 && (
          <button type="button" className="icon-button" onClick={() => onIndex(index - 1)} aria-label={COPY.firstLook.back}>
            <ArrowLeft size={18} aria-hidden="true" />
          </button>
        )}
        {isLast ? (
          <button type="button" className="button button--primary" onClick={onClose}>
            {COPY.firstLook.done}
          </button>
        ) : (
          <button type="button" className="button button--primary" onClick={() => onIndex(index + 1)}>
            {COPY.firstLook.next}
            <ArrowRight size={18} aria-hidden="true" />
          </button>
        )}
        {!isLast && (
          <button type="button" className="firstlook__close" onClick={onClose}>
            <X size={16} aria-hidden="true" />
            {COPY.firstLook.close}
          </button>
        )}
      </div>
    </section>
  );
}
