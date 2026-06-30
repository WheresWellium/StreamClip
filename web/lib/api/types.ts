/**
 * API types — generated from OpenAPI (see lib/api/openapi.ts).
 * Regenerate: see CONTRIBUTING.md
 */
export type { components, paths } from "./openapi";

import type { components } from "./openapi";

export type JobOut = components["schemas"]["JobOut"];
export type ClipOut = components["schemas"]["ClipOut"];
export type CreateJobRequest = components["schemas"]["CreateJobRequest"];
export type UploadInitRequest = components["schemas"]["UploadInitRequest"];
export type UploadInitResponse = components["schemas"]["UploadInitResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type ApiError = components["schemas"]["ErrorResponse"];

export type CaptionStyle = CreateJobRequest["caption_style"];
export type ReframePreset = CreateJobRequest["reframe_preset"];
export type JobStatus = JobOut["status"];
