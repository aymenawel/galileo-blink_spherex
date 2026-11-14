/**
 * The shapes the Galileo Blink server sends.
 *
 * Almost every field is optional or nullable on purpose: a view is assembled from several
 * outside services, and any of them can be missing on a given day. Code that reads a view
 * must cope with a field not being there.
 */

/** Camera numbers are 1 to 6; the server uses them as text keys ("1".."6"). */
export type CameraKey = "1" | "2" | "3" | "4" | "5" | "6";

/** A wavelength range in microns: [shortest, longest]. */
export type Band = [number, number];

/** Whose side a failure is on. */
export type ErrorKind = "request" | "service" | "busy" | "internal" | "network";

// ---------------------------------------------------------------------------- /api/targets

/** One of NASA's five test targets. */
export interface Target {
  id: string;
  name: string;
  kind: string;
  blurb: string;
  /** Key of the ready-made view of this target. */
  key: string;
  ra: number;
  dec: number;
  /** Catalogue speed across the sky, arcseconds per year. */
  pm: number;
  /** True when the view is already built and can be shown at once. */
  ready: boolean;
}

// ---------------------------------------------------------------------------- /api/resolve

/** What the server made of the text typed in the search box. */
export interface ResolvedPlace {
  ra: number;
  dec: number;
  label: string;
  kind: "coordinates" | "name";
  target_id: string | null;
  /** Set when the typed position was an old catalogue position of a test target. */
  moved_arcmin: number | null;
}

// ---------------------------------------------------------------------------- /api/about

export interface FlagInfo {
  bit: number;
  name: string;
  meaning: string;
  treated_as_no_data: boolean;
}

export interface About {
  pixel_arcsec: number;
  cameras: Partial<Record<CameraKey, Band>>;
  field: { min: number; max: number; default: number };
  flags: FlagInfo[];
  min_marked_motion?: number;
  engine?: string;
}

// ---------------------------------------------------------------------------- /api/spectrum

export interface QuickSpectrumPoint {
  wavelength: number;
  flux: number | null;
  camera?: number;
}

export interface QuickSpectrum {
  points: QuickSpectrumPoint[];
  unit?: string;
  note?: string;
}

// ---------------------------------------------------------------------------- /api/view

export type BuildState = "ready" | "queued" | "building" | "failed";

/** Progress of a view: what `/api/view` and `/api/view/{key}` answer. */
export interface ViewStatus {
  key: string;
  state: BuildState;
  stage?: string;
  /** 0 to 1. */
  fraction?: number;
  error?: string | null;
  error_kind?: ErrorKind | null;
  seconds?: number;
  /** Present once `state` is "ready". */
  view?: View;
}

/** One time step of the screen. The six cameras look on slightly different days. */
export interface Season {
  index: number;
  label: string;
  date: string;
  mjd: number;
}

/** One camera's stacked picture of one season. */
export interface Look {
  season: number;
  png: string;
  /** White-on-transparent mask of flagged pixels. */
  flags_png?: string | null;
  /** Ready-made change map versus this camera's first look. */
  change?: string | null;
  n_photos: number;
  date: string;
  mjd: number;
  wavelength?: Band | null;
  files?: string[];
  flag_counts?: Record<string, number>;
}

export interface CameraView {
  camera: number;
  band: Band;
  /** Every photo of this camera added together. */
  combined?: string | null;
  looks: Look[];
  empty?: "no_photos" | "no_data";
}

export interface MarkerPosition {
  season: number;
  /** View-pixel coordinates, y up, pixel centres at whole numbers. */
  x: number;
  y: number;
}

/** A catalogued moving object drawn on the picture. */
export interface Marker {
  name: string;
  catalog?: string | null;
  source?: string | null;
  /** Arcseconds per year. */
  pm?: number | null;
  parallax_mas?: number | null;
  gmag?: number | null;
  subject?: boolean;
  track: MarkerPosition[];
}

/** A Gaia star: [x, y, G magnitude], same coordinates as markers. */
export type StarDot = [number, number, number];

export type SubjectKind = "target" | "mover" | "star" | "spot";

/** What the view measures. */
export interface Subject {
  kind: SubjectKind;
  name?: string | null;
  catalog?: string | null;
  source?: string | null;
  pm?: number | null;
  parallax_mas?: number | null;
  gmag?: number | null;
}

export interface TargetSummary {
  id: string;
  name: string;
  kind: string;
  blurb: string;
}

/** A motion measurement, in arcseconds. `motion_combined` carries only some of these. */
export interface Motion {
  measured: number;
  measured_east?: number;
  measured_north?: number;
  predicted: number;
  predicted_east?: number;
  predicted_north?: number;
  /** One-sigma error of `measured`. */
  error: number;
  residual?: number;
  /** The measured motion matches the catalogue prediction, as a vector. */
  agrees: boolean;
  years?: number;
  same_time_of_year?: boolean;
  first_season?: number;
  last_season?: number;
  camera?: number;
  /** How far stars that do not move appear to shift in this view. */
  floor?: number;
  n_reference_stars?: number;
  /** Only on `motion_combined`. */
  cameras?: number[];
  n_cameras?: number;
}

/** A measured offset from the predicted position, for one camera in one season. */
export interface TrackPoint {
  season: number;
  mjd: number;
  east: number;
  north: number;
  error: number;
  n?: number;
  snr?: number;
}

/** The predicted path: offsets from the position at the first season. */
export interface PathPoint {
  mjd: number;
  east: number;
  north: number;
}

export type BrightnessStatus = "ok" | "partial" | "saturated";

/** The subject's brightness in one photo. */
export interface BrightnessPoint {
  camera: number;
  season: number;
  mjd: number;
  /** Microns. */
  wavelength?: number | null;
  flux_mjy?: number | null;
  snr?: number | null;
  status: BrightnessStatus;
}

export type LeftOutReason =
  | "off_frame"
  | "not_received"
  | "unreadable"
  | "poor_astrometry"
  | "partial_coverage";

export interface LeftOutPhoto {
  file?: string;
  season?: number;
  reason: LeftOutReason | string;
}

export type DegradedService = "gaia" | "catwise" | "photo_list" | "photos";

export type MotionReason = "no_target" | "catalogue_down" | "one_season" | "too_faint" | "off_track";

export interface ViewStats {
  total_s?: number;
  photos_used?: number;
  photos_asked?: number;
  mb_downloaded?: number;
}

/** Everything the screen shows about one place in the sky. */
export interface View {
  key: string;
  ra: number;
  dec: number;
  size_deg: number;
  /** Width of the view in SPHEREx pixels. */
  n: number;
  pixel_arcsec: number;
  /** Every picture is `n * upscale` pixels square, north up, east left. */
  upscale?: number;
  label?: string | null;
  target?: TargetSummary | null;
  built_at?: string;
  /** Date of the newest SPHEREx photo of this place. */
  data_through?: string | null;
  photos_in_archive?: number;
  seasons: Season[];
  seasons_left_out?: number;
  cameras: Partial<Record<CameraKey, CameraView>>;
  subject?: Subject | null;
  markers?: Marker[];
  markers_left_out?: number;
  stars?: StarDot[];
  motion?: Motion | null;
  motion_combined?: Motion | null;
  motion_by_camera?: Partial<Record<CameraKey, Motion>>;
  motion_reason?: MotionReason | string | null;
  motion_reason_text?: string | null;
  track?: Partial<Record<CameraKey, TrackPoint[]>>;
  path?: PathPoint[];
  brightness?: BrightnessPoint[];
  /** Photos whose light at the subject belonged to a neighbouring object. */
  brightness_left_out?: number;
  reference_stars?: { available?: number; median_used?: number };
  left_out?: LeftOutPhoto[];
  degraded?: Array<DegradedService | string>;
  versions?: number[];
  stats?: ViewStats;
}
