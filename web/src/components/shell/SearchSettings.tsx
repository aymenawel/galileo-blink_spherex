/**
 * The choices that go with a place: how far apart the pictures are (months, for stars; hours,
 * for asteroids), how much sky to show, and for an asteroid search which camera to use.
 */
import { CAMERA_BANDS, CAMERA_KEYS } from "../../lib/cameras";
import { COPY } from "../../lib/copy";
import { fieldWords, microns } from "../../lib/format";

export type TimeScale = "looks" | "visit";

interface SearchSettingsProps {
  scale: TimeScale;
  /** Field of view in degrees. */
  size: number;
  /** The camera of an asteroid search, or `null` to let the site pick the best one. */
  camera: number | null;
  /** Fields of view to offer, in degrees. */
  sizes: readonly number[];
  onScale: (scale: TimeScale) => void;
  onSize: (size: number) => void;
  onCamera: (camera: number | null) => void;
}

export function SearchSettings({ scale, size, camera, sizes, onScale, onSize, onCamera }: SearchSettingsProps) {
  const words = COPY.search;
  return (
    <div className="settings">
      <div className="segmented" role="group" aria-label={words.timeScale}>
        <button type="button" className="segmented__item" aria-pressed={scale === "looks"} title={words.looksHint} onClick={() => onScale("looks")}>
          {words.looks}
        </button>
        <button type="button" className="segmented__item" aria-pressed={scale === "visit"} title={words.visitHint} onClick={() => onScale("visit")}>
          {words.visit}
        </button>
      </div>
      <label className="settings__field">
        <span className="visually-hidden">{words.field}</span>
        <select className="select" value={size} onChange={(event) => onSize(Number(event.target.value))}>
          {sizes.map((option) => (
            <option key={option} value={option}>
              {fieldWords(option)}
            </option>
          ))}
        </select>
      </label>
      {scale === "visit" && (
        <label className="settings__field">
          <span className="visually-hidden">{words.camera}</span>
          <select
            className="select"
            value={camera ?? ""}
            onChange={(event) => onCamera(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">{words.cameraAuto}</option>
            {CAMERA_KEYS.map((key) => (
              <option key={key} value={key}>
                {words.cameraOption(key, microns(CAMERA_BANDS[key]))}
              </option>
            ))}
          </select>
        </label>
      )}
      <p className="settings__hint">{scale === "visit" ? words.visitHint : words.looksHint}</p>
    </div>
  );
}
