/**
 * API types — generated from OpenAPI (see lib/api/openapi.ts).
 * Regenerate: see CONTRIBUTING.md
 */
export type { components, paths } from "./openapi";

import type { components } from "./openapi";
import type {
  CAPTION_STYLE_IDS,
  CONTENT_PROFILE_IDS,
  REFRAME_PRESET_IDS,
} from "@/lib/creator-option-ids";

type OpenApiCreateJob = components["schemas"]["CreateJobRequest"];

export type CreateJobRequest = Omit<
  OpenApiCreateJob,
  | "caption_style"
  | "reframe_preset"
  | "content_profile"
  | "profanity_filter"
  | "profanity_mode"
> & {
  caption_style?: (typeof CAPTION_STYLE_IDS)[number];
  reframe_preset?: (typeof REFRAME_PRESET_IDS)[number];
  content_profile?: (typeof CONTENT_PROFILE_IDS)[number];
  // Server defaults these; clients only send them when overriding.
  profanity_filter?: OpenApiCreateJob["profanity_filter"];
  profanity_mode?: OpenApiCreateJob["profanity_mode"];
};

export type JobOut = components["schemas"]["JobOut"];
export type Job = JobOut;
export type JobListItem = components["schemas"]["JobListItem"];
export type JobListResponse = components["schemas"]["JobListResponse"];
export type ClipOut = components["schemas"]["ClipOut"] & {
  approval_status?: "draft" | "approved" | "rejected";
  publish_statuses?: Array<{
    platform: string;
    status: string;
    publish_job_id: string;
    external_url?: string | null;
  }>;
  /** Present on API responses; optional for older mocks/fixtures. */
  virality_source?: "llm" | "heuristic" | "unavailable";
};

/** One caption word with clip-relative timing (GET .../clips/{id}/words). */
export type ClipWord = {
  index: number;
  text: string;
  start: number;
  end: number;
};

export type ClipWords = {
  clip_id: string;
  words: ClipWord[];
};

/** Word-index → replacement text ("" removes the word). */
export type TranscriptEdits = Record<string, string>;

export type UploadInitRequest = components["schemas"]["UploadInitRequest"];
export type UploadInitResponse = components["schemas"]["UploadInitResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];

/** Completed stage → seconds (canonical keys: ingest, transcribe, highlights, virality, process_clip). */
export type StageDurations = Record<string, number>;

/** SSE payload from GET /api/jobs/{id}/progress */
export type ClipFeedEventName = "clip_discovered" | "clip_processing" | "clip_done";

export type ClipFeedExtra = {
  event: ClipFeedEventName;
  clip_id: string;
  rank: number;
  title?: string | null;
};

export type ClipFeedItem = {
  clip_id: string;
  rank: number;
  title: string | null;
  feedStatus: "discovered" | "processing" | "done" | "error";
};

export type ProgressEvent = {
  job_id: string;
  stage: string;
  progress: number;
  message?: string;
  status: "processing" | "done" | "error";
  ts: number;
  event_id?: string;
  stage_elapsed_secs?: number | null;
  total_elapsed_secs?: number | null;
  eta_secs?: number | null;
  stage_durations?: StageDurations | null;
  extra?: ClipFeedExtra | null;
};

/** FastAPI StreamClipError JSON body */
export type ApiError = {
  code: string;
  message?: string;
  errors?: unknown;
};

export type CaptionStyle = (typeof CAPTION_STYLE_IDS)[number];
export type ReframePreset = (typeof REFRAME_PRESET_IDS)[number];
export type JobStatus = JobOut["status"];
