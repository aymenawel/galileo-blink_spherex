/**
 * One camera's pictures of a place, stacked on top of each other with only one visible.
 * Every date is loaded up front, so switching dates never flickers.
 *
 * Must sit inside an element with the `sky` class, which draws the "no data" hatch.
 */
import { fileUrl } from "../../api/client";
import type { CameraKey, View } from "../../api/types";
import { bandOf } from "../../lib/cameras";
import { COPY, combinedAlt, lookAlt } from "../../lib/copy";

interface ImageStackProps {
  view: View;
  camera: CameraKey;
  /** The date to show, or `null` for every date added together. */
  season: number | null;
  /** The place's name, for the picture's description. */
  place: string;
  /** "change" shows each date's ready-made change map instead of the photo itself. */
  layer?: "photo" | "change";
}

export function ImageStack({ view, camera, season, place, layer = "photo" }: ImageStackProps) {
  const cameraView = view.cameras[camera];
  const band = bandOf(cameraView, camera);
  const looks = cameraView?.looks ?? [];

  if (season === null) {
    return cameraView?.combined ? (
      <img src={fileUrl(view, cameraView.combined)} alt={combinedAlt(place, camera, band)} draggable={false} />
    ) : (
      <span className="sky__empty">{COPY.viewport.noCamera}</span>
    );
  }

  const shown = looks.find((look) => look.season === season);
  const seasonLabel = view.seasons.find((s) => s.index === season)?.label ?? "";

  return (
    <>
      {looks.map((look) => (
        <img
          key={look.png}
          src={fileUrl(view, layer === "change" && look.change ? look.change : look.png)}
          alt={look === shown ? lookAlt(place, camera, band, seasonLabel) : ""}
          aria-hidden={look === shown ? undefined : true}
          className={look === shown ? undefined : "is-hidden"}
          draggable={false}
        />
      ))}
      {!shown && <span className="sky__empty">{looks.length > 0 ? COPY.viewport.noLook : COPY.viewport.noCamera}</span>}
    </>
  );
}
