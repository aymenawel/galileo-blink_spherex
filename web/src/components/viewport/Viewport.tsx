/**
 * The hero of the Explore page: the chosen camera's picture, with markers drawn on it and
 * the controls floating over it.
 */
import { useMemo, useRef, useState } from "react";
import { fileUrl } from "../../api/client";
import { bandOf, lookAt, looksOf } from "../../lib/cameras";
import { COPY, lookSummary } from "../../lib/copy";
import { formatDate } from "../../lib/format";
import { markersToDraw } from "../../lib/markers";
import type { Workspace } from "../explore/useWorkspace";
import { ChangeMap } from "./ChangeMap";
import { Compass } from "./Compass";
import { Crosshair } from "./Crosshair";
import { FlagsOverlay } from "./FlagsOverlay";
import { ImageStack } from "./ImageStack";
import { ModePills } from "./ModePills";
import { OverlayToggles } from "./OverlayToggles";
import { ScaleBar } from "./ScaleBar";
import { SkyOverlay } from "./SkyOverlay";
import { SwipeCompare } from "./SwipeCompare";
import { TransportBar } from "./TransportBar";

interface ViewportProps {
  ws: Workspace;
}

/** The two lines of the readout in the picture's corner: when, and what took it. */
function readout(ws: Workspace): { when: string; date: string; what: string } {
  const { view, camera, mode, season, a, b } = ws;
  const band = bandOf(view.cameras[camera], camera);
  const labelOf = (index: number) => view.seasons.find((s) => s.index === index)?.label ?? "";
  if (mode === "combined") {
    const photos = looksOf(view, camera).reduce((sum, look) => sum + look.n_photos, 0);
    return { when: COPY.viewport.combinedChip, date: "", what: lookSummary(camera, band, photos) };
  }
  if (mode === "compare") {
    return { when: `A ${labelOf(a)}  |  B ${labelOf(b)}`, date: "", what: lookSummary(camera, band, null) };
  }
  if (mode === "change") {
    return { when: `${labelOf(a)} − ${labelOf(b)}`, date: "", what: lookSummary(camera, band, null) };
  }
  const look = lookAt(view, camera, season);
  return {
    when: labelOf(season),
    date: look ? formatDate(look.date) : "",
    what: look ? lookSummary(camera, band, look.n_photos) : COPY.viewport.noLookFrom(camera),
  };
}

export function Viewport({ ws }: ViewportProps) {
  const { view, camera, mode, season, a, b, overlays, place } = ws;
  const sky = useRef<HTMLDivElement>(null);
  const [divider, setDivider] = useState(0.5);
  const markers = useMemo(() => markersToDraw(view.markers), [view.markers]);
  const chip = readout(ws);
  const flagsMask = mode === "blink" && overlays.flags ? lookAt(view, camera, season)?.flags_png : null;

  const overlay = (markerSeason: number | null, clipPath?: string) => (
    <SkyOverlay
      n={view.n}
      markers={markers}
      season={markerSeason}
      stars={view.stars}
      showMarkers={overlays.markers}
      showStars={overlays.stars}
      interactive
      clipPath={clipPath}
    />
  );

  return (
    <div className="viewport">
      <div className="viewport__sky sky" ref={sky}>
        {mode === "blink" && <ImageStack view={view} camera={camera} season={season} place={place} />}
        {mode === "combined" && <ImageStack view={view} camera={camera} season={null} place={place} />}
        {mode === "change" && <ChangeMap view={view} camera={camera} a={a} b={b} place={place} />}
        {mode === "compare" && (
          <SwipeCompare view={view} camera={camera} a={a} b={b} place={place} divider={divider} onDivider={setDivider} />
        )}

        {flagsMask && <FlagsOverlay mask={fileUrl(view, flagsMask)} />}

        {mode === "compare" ? (
          <>
            {overlay(a, `inset(0 ${(1 - divider) * 100}% 0 0)`)}
            {overlay(b, `inset(0 0 0 ${divider * 100}%)`)}
          </>
        ) : (
          overlay(mode === "blink" ? season : mode === "change" ? a : null)
        )}

        <Crosshair skyRef={sky} view={view} />

        <Compass />
        <ScaleBar n={view.n} pixelArcsec={view.pixel_arcsec} />
      </div>

      <div className="viewport__top">
        <ModePills mode={mode} onSelect={ws.selectMode} />
        <div className="look-chip" aria-live="off">
          <span className="look-chip__when mono">
            {chip.when}
            {chip.date && <small>{chip.date}</small>}
          </span>
          <span className="look-chip__what mono">{chip.what}</span>
        </div>
      </div>

      <div className="viewport__bottom">
        {mode === "blink" ? (
          <TransportBar
            playing={ws.playing}
            speed={ws.speed}
            enabled={ws.cameraSeasons.length > 1}
            onStep={ws.step}
            onTogglePlaying={ws.togglePlaying}
            onSpeed={ws.selectSpeed}
          />
        ) : (
          <span className="viewport__hint">{COPY.viewport.modes[mode].hint}</span>
        )}
        <OverlayToggles overlays={overlays} flagsAvailable={mode === "blink"} onToggle={ws.toggleOverlay} />
      </div>
    </div>
  );
}
