/**
 * API types — generated from OpenAPI (see lib/api/openapi.ts).
 * Regenerate: see CONTRIBUTING.md
 */
export type { components, paths } from "./openapi";

import type { components } from "./openapi";

export type JobOut = components["schemas"]["JobOut"];
export type Job = JobOut;
export type JobListItem = components["schemas"]["JobListItem"];
export type JobListResponse = components["schemas"]["JobListResponse"];
export type ClipOut = components["schemas"]["ClipOut"];
export type CreateJobRequest = components["schemas"]["CreateJobRequest"];
export type UploadInitRequest = components["schemas"]["UploadInitRequest"];
export type UploadInitResponse = components["schemas"]["UploadInitResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];

/** SSE payload from GET /api/jobs/{id}/progress */
export type ProgressEvent = {
  job_id: string;
  stage: string;
  progress: number;
  message?: string;
  status: "processing" | "done" | "error";
  ts: number;
  event_id?: string;
};

/** FastAPI StreamClipError JSON body */
export type ApiError = {
  code: string;
  message?: string;
  errors?: unknown;
};

export type CaptionStyle = CreateJobRequest["caption_style"];
export type ReframePreset = CreateJobRequest["reframe_preset"];
export type JobStatus = JobOut["status"];
