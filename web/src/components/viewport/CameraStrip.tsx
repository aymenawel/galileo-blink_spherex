/**
 * The six cameras side by side, each showing the same date as the main picture, so the
 * blink runs in all six at once. Choosing a tile puts that camera in the main picture.
 */
import type { CameraKey } from "../../api/types";
import { CAMERA_KEYS, bandOf } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import { microns } from "../../lib/format";
import type { Workspace } from "../explore/useWorkspace";
import { ImageStack } from "./ImageStack";

interface CameraStripProps {
  ws: Workspace;
}

export function CameraStrip({ ws }: CameraStripProps) {
  const { view, shownSeason, place } = ws;

  const tile = (key: CameraKey) => {
    const band = microns(bandOf(view.cameras[key], key));
    return (
      <li key={key}>
        <button
          type="button"
          className="camera-tile"
          aria-pressed={key === ws.camera}
          aria-label={COPY.cameras.select(key, band)}
          onClick={() => ws.selectCamera(key)}
        >
          <span className="camera-tile__sky sky">
            <ImageStack view={view} camera={key} season={shownSeason} place={place} />
          </span>
          <span className="camera-tile__label">
            <span className="camera-tile__name">{COPY.cameras.camera(key)}</span>
            <span className="camera-tile__band">{band}</span>
          </span>
        </button>
      </li>
    );
  };

  return (
    <section className="panel camera-strip" aria-labelledby="camera-strip-title">
      <div className="camera-strip__head">
        <h3 className="panel__title" id="camera-strip-title">
          {COPY.cameras.title}
        </h3>
        <p className="muted">{COPY.cameras.line}</p>
      </div>
      <ul className="camera-strip__tiles">{CAMERA_KEYS.map(tile)}</ul>
    </section>
  );
}
