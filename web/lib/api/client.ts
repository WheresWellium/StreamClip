/**
 * StreamClip — API Client
 *
 * Two base URLs:
 *   • Server-side (RSC, Server Actions, Route Handlers): API_INTERNAL_URL
 *     This goes pod-to-pod inside docker network — `http://api:8000`.
 *
 *   • Client-side (browser): NEXT_PUBLIC_API_URL OR same-origin via rewrite
 *     In dev with rewrites configured, just use `/api/...` and Next.js
 *     proxies to FastAPI. No CORS preflight, no env var leaks.
 *
 * The helpers below auto-pick the right base depending on whether they
 * run on the server (typeof window === 'undefined') or the client.
 */

import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";

import type {
  ClipWords,
  CreateJobRequest,
  Job,
  JobListResponse,
  UploadInitRequest,
  UploadInitResponse,
} from "./types";

// ─── Base URL resolution ──────────────────────────────────────────────────────

function apiBase(): string {
  if (typeof window === "undefined") {
    // Server context — use the internal docker hostname
    return process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  }
  // Browser — same-origin via Next rewrite (avoids CORS)
  return "";
}

// ─── Low-level fetch wrapper with typed errors ───────────────────────────────

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public payload?: unknown,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { authToken?: string; deviceId?: string },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = init?.authToken ?? (typeof window !== "undefined" ? getClientAccessToken() : undefined);
  const deviceId = init?.deviceId ?? (typeof window !== "undefined" ? getClientDeviceId() : undefined);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (deviceId) {
    headers.set("X-Device-Id", deviceId);
  }

  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers,
    // Server Components: don't cache mutations or job state
    cache: init?.method && init.method !== "GET" ? "no-store" : init?.cache,
  });

  if (!res.ok) {
    let payload: { code?: string; message?: string } = {};
    try {
      payload = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiClientError(
      res.status,
      payload.code ?? `http_${res.status}`,
      payload.message ?? res.statusText,
      payload,
    );
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

// ─── Jobs ─────────────────────────────────────────────────────────────────────

export const jobsApi = {
  list: (
    limit = 50,
    offset = 0,
    authToken?: string,
    filters?: { status?: string; search?: string },
    deviceId?: string,
  ) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (filters?.status) params.set("status", filters.status);
    if (filters?.search) params.set("search", filters.search);
    return request<JobListResponse>(`/api/jobs?${params}`, { authToken, deviceId });
  },

  get: (jobId: string, authToken?: string, deviceId?: string) =>
    request<Job>(`/api/jobs/${jobId}`, {
      authToken,
      deviceId,
      next: { tags: [`job:${jobId}`] },
    }),

  create: (body: CreateJobRequest, authToken?: string, deviceId?: string) =>
    request<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
      deviceId,
    }),

  update: (
    jobId: string,
    body: { display_title?: string | null },
    authToken?: string,
    deviceId?: string,
  ) =>
    request<Job>(`/api/jobs/${jobId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      authToken,
      deviceId,
    }),

  createBatch: (jobs: CreateJobRequest[], authToken?: string) =>
    request<{ jobs: Job[] }>("/api/jobs/batch", {
      method: "POST",
      body: JSON.stringify({ jobs }),
      authToken,
    }),

  updateClip: (
    jobId: string,
    clipId: string,
    body: Record<string, unknown>,
    authToken?: string,
  ) =>
    request<Job>(`/api/jobs/${jobId}/clips/${clipId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      authToken,
    }),

  spliceClips: (
    jobId: string,
    clipIds: string[],
    transition: "cut" | "crossfade",
    authToken?: string,
  ) =>
    request<{ clip_id: string; job_id: string; status: string }>(
      `/api/jobs/${jobId}/clips/splice`,
      {
        method: "POST",
        body: JSON.stringify({ clip_ids: clipIds, transition }),
        authToken,
      },
    ),

  batchPublishClips: (
    jobId: string,
    body: { platform: string; clip_ids?: string[]; title?: string; description?: string },
    authToken?: string,
  ) =>
    request<{ jobs: PublishJob[]; skipped: number }>(
      `/api/jobs/${jobId}/clips/batch-publish`,
      { method: "POST", body: JSON.stringify(body), authToken },
    ),

  updateClipApproval: (
    jobId: string,
    clipId: string,
    approval_status: "draft" | "approved" | "rejected",
    authToken?: string,
    deviceId?: string,
  ) =>
    request<{ clip_id: string; approval_status: string }>(
      `/api/jobs/${jobId}/clips/${clipId}/approval`,
      {
        method: "PATCH",
        body: JSON.stringify({ approval_status }),
        authToken,
        deviceId,
      },
    ),

  cancel: (jobId: string, authToken?: string) =>
    request<void>(`/api/jobs/${jobId}`, {
      method: "DELETE",
      authToken,
    }),

  regenerateClip: (jobId: string, clipId: string, authToken?: string) =>
    request<{ clip_id: string; status: string }>(
      `/api/jobs/${jobId}/clips/${clipId}/regenerate`,
      { method: "POST", authToken },
    ),

  clipWords: (jobId: string, clipId: string, authToken?: string) =>
    request<ClipWords>(`/api/jobs/${jobId}/clips/${clipId}/words`, {
      authToken,
    }),

  waveform: (jobId: string, authToken?: string) =>
    request<{ url: string }>(`/api/jobs/${jobId}/waveform`, { authToken }),

  clipsZipUrl: (jobId: string): string => `/api/jobs/${jobId}/clips.zip`,

  // SSE via same-origin BFF route (forwards auth cookies)
  progressUrl: (jobId: string): string => `/api/jobs/${jobId}/progress`,
};

// ─── Uploads ─────────────────────────────────────────────────────────────────

export const uploadsApi = {
  init: (body: UploadInitRequest, authToken?: string, deviceId?: string) =>
    request<UploadInitResponse>("/api/uploads/init", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
      deviceId,
    }),

  /**
   * Upload a File directly to the presigned URL (browser only).
   * Uses the server action for init so httpOnly device cookies reach the API.
   * Returns the storage_key to reference when creating a job.
   */
  uploadFile: async (
    file: File,
    onProgress?: (pct: number) => void,
    authToken?: string,
    deviceId?: string,
  ): Promise<string> => {
    const init = await uploadsApi.init(
      {
        filename: file.name,
        content_type: file.type || "video/mp4",
        size_bytes: file.size,
      },
      authToken,
      deviceId,
    );

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", init.upload_url);
      xhr.setRequestHeader("Content-Type", file.type || "video/mp4");
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(e.loaded / e.total);
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(init.storage_key);
        } else {
          reject(
            new ApiClientError(xhr.status, "upload_failed", xhr.statusText),
          );
        }
      };
      xhr.onerror = () =>
        reject(new ApiClientError(0, "network_error", "Upload network error"));
      xhr.send(file);
    });
  },
};

// ─── Meta / Health ───────────────────────────────────────────────────────────

export const metaApi = {
  health: () => request<Record<string, unknown>>("/api/health"),
  meta: () => request<Record<string, unknown>>("/api/meta"),
};

export const templatesApi = {
  list: (authToken?: string) =>
    request<Array<{ id: string; name: string; config_json: Record<string, unknown> }>>(
      "/api/templates",
      { authToken },
    ),
  create: (
    name: string,
    config_json: Record<string, unknown>,
    authToken?: string,
  ) =>
    request<{ id: string; name: string; config_json: Record<string, unknown> }>(
      "/api/templates",
      { method: "POST", body: JSON.stringify({ name, config_json }), authToken },
    ),
  delete: (id: string, authToken?: string) =>
    request<void>(`/api/templates/${id}`, { method: "DELETE", authToken }),
};

export const devicesApi = {
  completeOnboarding: (deviceId: string) =>
    request<{ device_id: string; onboarding_complete: boolean }>(
      "/api/devices/onboarding-complete",
      { method: "POST", body: JSON.stringify({}), deviceId },
    ),
};

export type WebhookSettings = {
  webhook_url: string | null;
  configured: boolean;
};

export const settingsApi = {
  submitClipFeedback: (clipId: string, rating: number, authToken?: string) =>
    request<{ clip_id: string; rating: number }>(
      `/api/settings/clips/${clipId}/feedback`,
      { method: "POST", body: JSON.stringify({ rating }), authToken },
    ),
  getWebhook: (authToken?: string) =>
    request<WebhookSettings>("/api/settings/webhook", { authToken }),
  getPrivacy: (authToken?: string) =>
    request<{ data_contribution_opt_in: boolean }>("/api/settings/privacy", {
      authToken,
    }),
  updatePrivacy: (optIn: boolean, authToken?: string) =>
    request<{ data_contribution_opt_in: boolean }>("/api/settings/privacy", {
      method: "PUT",
      body: JSON.stringify({ data_contribution_opt_in: optIn }),
      authToken,
    }),
  updateWebhook: (
    webhookUrl: string | null,
    webhookSecret: string | null,
    authToken?: string,
  ) =>
    request<WebhookSettings>("/api/settings/webhook", {
      method: "PUT",
      body: JSON.stringify({ webhook_url: webhookUrl, webhook_secret: webhookSecret }),
      authToken,
    }),
};

export type VaultClip = {
  id: string;
  title: string;
  hook: string;
  duration_secs: number;
  status: string;
  source_clip_id: string | null;
  source_job_id: string | null;
  saved_at: string;
  metadata_json: Record<string, unknown>;
  video_url: string | null;
  thumbnail_url: string | null;
  publish_statuses?: ClipPublishStatus[];
};

export type ClipPublishStatus = {
  platform: string;
  status: string;
  publish_job_id: string;
  external_url?: string | null;
};

export type DistributionPlatform = {
  id: string;
  label: string;
  enabled: boolean;
  connected: boolean;
};

export type PlatformConnection = {
  id: string;
  platform: string;
  account_label: string;
  is_active: boolean;
};

export type OAuthAppConfig = {
  platform: string;
  client_id: string;
  redirect_uri: string;
  configured: boolean;
};

export type PublishJob = {
  id: string;
  clip_id: string | null;
  vault_clip_id: string | null;
  platform: string;
  status: string;
  scheduled_at: string | null;
  published_at: string | null;
  external_id: string | null;
  external_url: string | null;
  title: string;
  error_message: string | null;
  last_error_code: string | null;
  created_at: string | null;
};

export const distributionApi = {
  platforms: (authToken?: string) =>
    request<DistributionPlatform[]>("/api/distribution/platforms", { authToken }),

  connections: (authToken?: string) =>
    request<PlatformConnection[]>("/api/distribution/connections", { authToken }),

  publishJobs: (authToken?: string) =>
    request<PublishJob[]>("/api/distribution/publish-jobs", { authToken }),

  publish: (
    body: {
      clip_id?: string;
      vault_clip_id?: string;
      platform: string;
      title?: string;
      description?: string;
      scheduled_at?: string;
      idempotency_key?: string;
    },
    authToken?: string,
  ) =>
    request<PublishJob>("/api/distribution/publish", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
    }),

  schedule: (
    body: {
      clip_id?: string;
      vault_clip_id?: string;
      platform: string;
      scheduled_at: string;
      title?: string;
      description?: string;
    },
    authToken?: string,
  ) =>
    request<PublishJob>("/api/distribution/schedule", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
    }),

  getPublishJob: (publishJobId: string, authToken?: string) =>
    request<PublishJob>(`/api/distribution/publish-jobs/${publishJobId}`, { authToken }),

  retryPublishJob: (publishJobId: string, authToken?: string) =>
    request<PublishJob>(`/api/distribution/publish-jobs/${publishJobId}/retry`, {
      method: "POST",
      authToken,
    }),

  cancelPublishJob: (publishJobId: string, authToken?: string) =>
    request<PublishJob>(`/api/distribution/publish-jobs/${publishJobId}/cancel`, {
      method: "POST",
      authToken,
    }),

  updatePublishJob: (
    publishJobId: string,
    body: { title?: string; description?: string; scheduled_at?: string },
    authToken?: string,
  ) =>
    request<PublishJob>(`/api/distribution/publish-jobs/${publishJobId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      authToken,
    }),

  publishProgressUrl: (publishJobId: string): string =>
    `/api/distribution/publish-jobs/${publishJobId}/progress`,

  oauthApps: (authToken?: string) =>
    request<OAuthAppConfig[]>("/api/distribution/oauth-apps", { authToken }),

  updateOAuthApp: (
    platform: string,
    body: { client_id: string; client_secret: string; redirect_uri?: string },
    authToken?: string,
  ) =>
    request<OAuthAppConfig>(`/api/distribution/oauth-apps/${platform}`, {
      method: "PUT",
      body: JSON.stringify(body),
      authToken,
    }),

  oauthStart: (platform: string, authToken?: string) =>
    request<{ auth_url: string; platform: string }>(
      `/api/distribution/oauth/${platform}/start`,
      { authToken },
    ),

  disconnect: (connectionId: string, authToken?: string) =>
    request<void>(`/api/distribution/connections/${connectionId}`, {
      method: "DELETE",
      authToken,
    }),
};

export type OverlayAsset = {
  id: string;
  name: string;
  asset_type: "gif" | "png" | "mp4";
  storage_key: string;
  sfx_storage_key: string | null;
  description: string;
  tags: string[];
  default_duration_secs: number;
  is_public: boolean;
  use_count: number;
};

export const assetsApi = {
  list: (authToken?: string) =>
    request<OverlayAsset[]>("/api/assets", { authToken }),

  create: (
    body: {
      name: string;
      asset_type: OverlayAsset["asset_type"];
      storage_key: string;
      sfx_storage_key?: string;
      description: string;
      tags?: string[];
      default_duration_secs?: number;
    },
    authToken?: string,
  ) =>
    request<OverlayAsset>("/api/assets", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
    }),

  remove: (assetId: string, authToken?: string) =>
    request<void>(`/api/assets/${assetId}`, {
      method: "DELETE",
      authToken,
    }),
};

export const vaultApi = {
  list: (authToken?: string) =>
    request<VaultClip[]>("/api/vault/clips", { authToken }),

  quota: (authToken?: string) =>
    request<{ used: number; limit: number }>("/api/vault/quota", { authToken }),

  save: (clipId: string, title?: string, authToken?: string) =>
    request<VaultClip>("/api/vault/clips", {
      method: "POST",
      body: JSON.stringify({ clip_id: clipId, title }),
      authToken,
    }),

  rename: (vaultClipId: string, title: string, authToken?: string) =>
    request<VaultClip>(`/api/vault/clips/${vaultClipId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
      authToken,
    }),

  remove: (vaultClipId: string, authToken?: string) =>
    request<void>(`/api/vault/clips/${vaultClipId}`, {
      method: "DELETE",
      authToken,
    }),
};

// ─── Support ─────────────────────────────────────────────────────────────────

export type BugReportPayload = {
  message: string;
  categories: string[];
  severity: "low" | "medium" | "high" | "critical";
  job_id?: string | null;
  environment?: Record<string, string> | null;
};

export const supportApi = {
  submitBugReport: (
    payload: BugReportPayload,
    authToken?: string,
    deviceId?: string,
  ) =>
    request<{ id: string; status: string }>("/api/support/bug-reports", {
      method: "POST",
      body: JSON.stringify(payload),
      authToken,
      deviceId,
    }),
};
