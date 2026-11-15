/**
 * A crosshair that follows the mouse over a sky picture, with the sky coordinates under it.
 * Listens on the picture's own element, so only this small component redraws as the mouse moves.
 */
import { useEffect, useState, type RefObject } from "react";
import type { View } from "../../api/types";
import { COPY } from "../../lib/copy";
import { formatDec, formatDegrees, formatRa } from "../../lib/format";
import { fractionToPixel, pixelToSky, type ScreenFraction } from "../../lib/geometry";

interface CrosshairProps {
  skyRef: RefObject<HTMLElement>;
  view: View;
}

export function Crosshair({ skyRef, view }: CrosshairProps) {
  const [at, setAt] = useState<ScreenFraction | null>(null);

  useEffect(() => {
    const sky = skyRef.current;
    if (!sky) return;
    const move = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const box = sky.getBoundingClientRect();
      const left = (event.clientX - box.left) / box.width;
      const top = (event.clientY - box.top) / box.height;
      setAt(left >= 0 && left <= 1 && top >= 0 && top <= 1 ? { left, top } : null);
    };
    const leave = () => setAt(null);
    sky.addEventListener("pointermove", move);
    sky.addEventListener("pointerleave", leave);
    return () => {
      sky.removeEventListener("pointermove", move);
      sky.removeEventListener("pointerleave", leave);
    };
  }, [skyRef]);

  if (!at) return null;
  const pixel = fractionToPixel(at.left, at.top, view.n);
  const sky = pixelToSky(pixel.x, pixel.y, view);
  const flipX = at.left > 0.6;
  const flipY = at.top > 0.7;

  return (
    <div className="crosshair" aria-hidden="true">
      <span className="crosshair__v" style={{ left: `${at.left * 100}%` }} />
      <span className="crosshair__h" style={{ top: `${at.top * 100}%` }} />
      <div
        className="crosshair__readout"
        style={{
          left: `${at.left * 100}%`,
          top: `${at.top * 100}%`,
          transform: `translate(${flipX ? "calc(-100% - 14px)" : "14px"}, ${flipY ? "calc(-100% - 14px)" : "14px"})`,
        }}
        title={COPY.viewport.pointerReadout}
      >
        <span>
          <i>RA</i> {formatRa(sky.ra)} <small>{formatDegrees(sky.ra)}</small>
        </span>
        <span>
          <i>Dec</i> {formatDec(sky.dec)} <small>{formatDegrees(sky.dec)}</small>
        </span>
      </div>
    </div>
  );
}
