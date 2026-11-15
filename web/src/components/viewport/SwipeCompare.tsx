/**
 * Two dates of the same camera, one on each side of a divider that can be dragged or moved
 * with the arrow keys. Date A is on the left, date B on the right.
 */
import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { fileUrl } from "../../api/client";
import type { CameraKey, View } from "../../api/types";
import { bandOf, lookAt } from "../../lib/cameras";
import { COPY, lookAlt } from "../../lib/copy";
import { clamp } from "../../lib/geometry";

interface SwipeCompareProps {
  view: View;
  camera: CameraKey;
  a: number;
  b: number;
  place: string;
  /** Where the divider is: 0 at the left edge, 1 at the right edge. */
  divider: number;
  onDivider: (position: number) => void;
}

const KEY_STEP = 0.04;

export function SwipeCompare({ view, camera, a, b, place, divider, onDivider }: SwipeCompareProps) {
  const frame = useRef<HTMLDivElement>(null);
  const band = bandOf(view.cameras[camera], camera);
  const lookA = lookAt(view, camera, a);
  const lookB = lookAt(view, camera, b);
  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";

  const drag = (event: PointerEvent<HTMLDivElement>) => {
    const box = frame.current?.getBoundingClientRect();
    if (box && event.buttons === 1) onDivider(clamp((event.clientX - box.left) / box.width, 0, 1));
  };

  const nudge = (event: KeyboardEvent<HTMLDivElement>) => {
    const to =
      event.key === "ArrowLeft"
        ? divider - KEY_STEP
        : event.key === "ArrowRight"
          ? divider + KEY_STEP
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? 1
              : null;
    if (to === null) return;
    event.preventDefault();
    event.stopPropagation();
    onDivider(clamp(to, 0, 1));
  };

  if (!lookA || !lookB) return <span className="sky__empty">{COPY.viewport.noLook}</span>;

  return (
    <div className="swipe" ref={frame}>
      <img src={fileUrl(view, lookB.png)} alt={lookAlt(place, camera, band, labelOf(b))} draggable={false} />
      <div className="swipe__a" style={{ clipPath: `inset(0 ${(1 - divider) * 100}% 0 0)` }}>
        <img src={fileUrl(view, lookA.png)} alt={lookAlt(place, camera, band, labelOf(a))} draggable={false} />
      </div>
      <span className="swipe__tag swipe__tag--a">A · {labelOf(a)}</span>
      <span className="swipe__tag swipe__tag--b">B · {labelOf(b)}</span>
      <div
        className="swipe__divider"
        style={{ left: `${divider * 100}%` }}
        role="slider"
        tabIndex={0}
        aria-label={COPY.viewport.compareHandle}
        aria-orientation="horizontal"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(divider * 100)}
        aria-valuetext={COPY.viewport.compareValue(Math.round(divider * 100), labelOf(a), labelOf(b))}
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          event.preventDefault();
        }}
        onPointerMove={drag}
        onKeyDown={nudge}
      >
        <span className="swipe__grip" aria-hidden="true" />
      </div>
    </div>
  );
}
