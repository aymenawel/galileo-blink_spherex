/**
 * A change map: date A minus date B for one camera. Warm is brighter in A, cool is fainter,
 * dark is unchanged. Uses the ready-made map when B is the camera's first date; otherwise
 * asks the server to subtract the two.
 */
import { useEffect, useState } from "react";
import { changeMapUrl, fileUrl } from "../../api/client";
import type { CameraKey, View } from "../../api/types";
import { lookAt, seasonsWithLooks } from "../../lib/cameras";
import { COPY, changeAlt } from "../../lib/copy";

interface ChangeMapProps {
  view: View;
  camera: CameraKey;
  a: number;
  b: number;
  place: string;
}

function changeSource(view: View, camera: CameraKey, a: number, b: number): string {
  const ready = lookAt(view, camera, a)?.change;
  const firstSeason = seasonsWithLooks(view, camera)[0];
  return ready && b === firstSeason ? fileUrl(view, ready) : changeMapUrl(view, Number(camera), a, b);
}

export function ChangeMap({ view, camera, a, b, place }: ChangeMapProps) {
  const source = changeSource(view, camera, a, b);
  const [state, setState] = useState<"loading" | "shown" | "failed">("loading");
  useEffect(() => setState("loading"), [source]);

  const labelOf = (season: number) => view.seasons.find((s) => s.index === season)?.label ?? "";
  const possible = a !== b && lookAt(view, camera, a) && lookAt(view, camera, b);
  if (!possible) return <span className="sky__empty">{COPY.viewport.changeFailed}</span>;

  return (
    <>
      <img
        key={source}
        src={source}
        alt={changeAlt(place, camera, labelOf(a), labelOf(b))}
        className={state === "shown" ? undefined : "is-hidden"}
        onLoad={() => setState("shown")}
        onError={() => setState("failed")}
        draggable={false}
      />
      {state !== "shown" && (
        <span className="sky__empty" role="status">
          {state === "loading" ? COPY.viewport.changeLoading : COPY.viewport.changeFailed}
        </span>
      )}
    </>
  );
}
