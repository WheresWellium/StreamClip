/**
 * StreamClip — API Type Definitions
 *
 * These types mirror the Pydantic schemas in `backend/api/schemas.py`.
 * Keep them in sync — when the API changes, update both files together.
 *
 * For end-to-end type safety against a Python backend we use hand-written
 * types here. The alternative (generating from OpenAPI) is heavier weight
 * than the contract surface warrants for this app.
 */

export type CaptionStyle =
  | "gaming_impact"
  | "tiktok_pop"
  | "minimal_white"
  | "podcast_clean";

export type ReframePreset =
  | "fps_game"
  | "moba"
  | "battle_royale"
  | "irl"
  | "podcast"
  | "auto";

export type JobStatus =
  | "queued"
  | "ingesting"
  | "transcribing"
  | "detecting"
  | "processing"
  | "done"
  | "error"
  | "cancelled";

export type ClipStatus = "pending" | "processing" | "done" | "error";

export type Emotion =
  | "hype"
  | "rage"
  | "funny"
  | "clutch"
  | "fail"
  | "weird"
  | "neutral";

// ─── Requests ─────────────────────────────────────────────────────────────────

export interface CreateJobRequest {
  source_url?: string | null;
  source_upload_key?: string | null;
  target_clips: number;
  caption_style: CaptionStyle;
  reframe_preset: ReframePreset;
  min_virality_score: number;
}

export interface UploadInitRequest {
  filename: string;
  content_type: string;
  size_bytes?: number | null;
}

export interface UploadInitResponse {
  upload_id: string;
  upload_url: string;
  storage_key: string;
  expires_in: number;
}

// ─── Responses ────────────────────────────────────────────────────────────────

export interface ClipOverlay {
  id: string;
  trigger_time_secs: number;
  duration_secs: number;
  position: string;
  similarity_score: number;
  matched_keyword: string;
}

export interface Clip {
  id: string;
  rank: number;
  title: string;
  hook: string;
  emotion: Emotion;
  start_secs: number;
  end_secs: number;
  duration_secs: number;
  ensemble_score: number;
  llm_score: number;
  audio_score: number;
  spectral_score: number;
  flow_score: number;
  status: ClipStatus;
  error_message: string | null;
  render_time_secs: number;
  file_size_bytes: number;
  overlays: ClipOverlay[];
  download_url: string | null;
  thumbnail_url: string | null;
}

export interface Job {
  id: string;
  source_url: string | null;
  source_title: string | null;
  source_duration_secs: number | null;
  status: JobStatus;
  progress: number;
  current_stage: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  clips: Clip[];
}

export interface JobListItem {
  id: string;
  source_title: string | null;
  source_duration_secs: number | null;
  status: JobStatus;
  progress: number;
  created_at: string;
  clip_count: number;
}

export interface JobListResponse {
  jobs: JobListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProgressEvent {
  job_id: string;
  stage: string;
  progress: number;
  message: string;
  status: "processing" | "done" | "error";
  ts: number;
}

export interface ApiError {
  code: string;
  message: string;
  retryable?: boolean;
  context?: Record<string, unknown>;
}
