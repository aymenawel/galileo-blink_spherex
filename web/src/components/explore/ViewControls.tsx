/**
 * The few controls beside the picture: which camera, what to draw on the picture, and the
 * choices of the view itself (time scale, field of view), with saving and sharing.
 */
import { Download, Link2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { blinkGifUrl, type ViewRequest } from "../../api/client";
import { CAMERA_KEYS, bandOf, looksOf } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import { DEFAULT_FIELD, DEFAULT_VISIT_FIELD, FIELD_CHOICES, exploreAddress } from "../../lib/exploreAddress";
import { microns } from "../../lib/format";
import { navigate } from "../../router";
import { SearchSettings, type TimeScale } from "../shell/SearchSettings";
import { Toast } from "../shell/Toast";
import { OverlayToggles } from "../viewport/OverlayToggles";
import { SPEED_MS, type Workspace } from "./useWorkspace";

interface ControlsProps {
  ws: Workspace;
}

/** Six cameras, six slices of infrared: pick the one in the main picture. */
export function CameraPicker({ ws }: ControlsProps) {
  const { view, camera } = ws;
  return (
    <div className="control">
      <p className="control__label">
        {COPY.cameras.camera(camera)} <span>{microns(bandOf(view.cameras[camera], camera))}</span>
      </p>
      <div className="camera-picker" role="group" aria-label={COPY.explore.cameraLabel}>
        {CAMERA_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            className="camera-picker__item"
            aria-pressed={key === camera}
            aria-label={COPY.cameras.select(key, microns(bandOf(view.cameras[key], key)))}
            disabled={looksOf(view, key).length === 0}
            onClick={() => ws.selectCamera(key)}
          >
            {key}
          </button>
        ))}
      </div>
      <p className="control__hint">{COPY.cameras.hint}</p>
    </div>
  );
}

/** What is drawn on top of the picture. */
export function ShowPicker({ ws }: ControlsProps) {
  const { view, mode, overlays } = ws;
  const hasCatwise = useMemo(
    () => (view.markers ?? []).some((marker) => marker.catalog === "CatWISE2020" && !marker.subject),
    [view.markers],
  );
  return (
    <div className="control">
      <p className="control__label">{COPY.explore.showLabel}</p>
      <OverlayToggles
        overlays={overlays}
        flagsAvailable={mode === "blink"}
        catwiseAvailable={hasCatwise}
        starsAvailable={(view.stars?.length ?? 0) > 0}
        onToggle={ws.toggleOverlay}
      />
    </div>
  );
}

async function copyAddress(): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(window.location.href);
    return true;
  } catch {
    return false;
  }
}

interface ViewActionsProps extends ControlsProps {
  request: ViewRequest;
  /** The name the visitor searched for, when the place is not a test target. */
  name: string | null;
}

/** The view's own choices, and taking it away: as a link, or as an animated picture. */
export function ViewActions({ ws, request, name }: ViewActionsProps) {
  const [toast, setToast] = useState<string | null>(null);
  const clearToast = useCallback(() => setToast(null), []);
  const share = () => {
    void copyAddress().then((copied) => setToast(copied ? COPY.explore.shareDone : COPY.explore.shareFailed));
  };

  // Ready-made views (test targets, asteroid examples) have no choices to change.
  const sized = request.kind === "place" || request.kind === "visit" ? request : null;
  const sizes = sized && !FIELD_CHOICES.includes(sized.size) ? [...FIELD_CHOICES, sized.size].sort((a, b) => a - b) : FIELD_CHOICES;
  const open = (next: ViewRequest) => navigate(exploreAddress(next, name));
  // The same place can be watched over six months (stars) or within one visit (asteroids).
  const setScale = (scale: TimeScale) => {
    if (!sized || (scale === "visit") === (sized.kind === "visit")) return;
    open(
      scale === "visit"
        ? { kind: "visit", ra: sized.ra, dec: sized.dec, size: Math.max(sized.size, DEFAULT_VISIT_FIELD) }
        : { kind: "place", ra: sized.ra, dec: sized.dec, size: Math.min(sized.size, DEFAULT_FIELD) },
    );
  };
  const canSave = ws.stepping && ws.cameraSeasons.length > 1;

  return (
    <div className="control">
      {sized && (
        <>
          <p className="control__label">{COPY.explore.viewLabel}</p>
          <SearchSettings
            scale={sized.kind === "visit" ? "visit" : "looks"}
            size={sized.size}
            camera={sized.kind === "visit" ? (sized.camera ?? null) : null}
            sizes={sizes}
            onScale={setScale}
            onSize={(size) => open({ ...sized, size })}
            onCamera={(camera) => {
              if (sized.kind !== "visit") return;
              open({ kind: "visit", ra: sized.ra, dec: sized.dec, size: sized.size, ...(camera ? { camera } : {}) });
            }}
          />
        </>
      )}
      <div className="control__actions">
        {canSave && (
          <a
            className="button button--quiet"
            href={blinkGifUrl(ws.view, Number(ws.camera), ws.mode === "change" ? "change" : "photo", SPEED_MS[ws.speed])}
            download
            title={COPY.viewport.saveGifHint}
          >
            <Download size={16} aria-hidden="true" />
            {COPY.viewport.saveGif}
          </a>
        )}
        <button type="button" className="button button--quiet" onClick={share}>
          <Link2 size={16} aria-hidden="true" />
          {COPY.explore.share}
        </button>
      </div>
      <Toast message={toast} onDone={clearToast} />
    </div>
  );
}
