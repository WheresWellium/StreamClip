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

import type {
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
  init?: RequestInit & { authToken?: string },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (init?.authToken) {
    headers.set("Authorization", `Bearer ${init.authToken}`);
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
  list: (limit = 50, offset = 0, authToken?: string) =>
    request<JobListResponse>(
      `/api/jobs?limit=${limit}&offset=${offset}`,
      { authToken },
    ),

  get: (jobId: string, authToken?: string) =>
    request<Job>(`/api/jobs/${jobId}`, {
      authToken,
      next: { tags: [`job:${jobId}`] },
    }),

  create: (body: CreateJobRequest, authToken?: string) =>
    request<Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
    }),

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

  clipsZipUrl: (jobId: string): string => `/api/jobs/${jobId}/clips.zip`,

  // SSE URL for client-side EventSource (browser only)
  progressUrl: (jobId: string): string => `/api/jobs/${jobId}/progress`,
};

// ─── Uploads ─────────────────────────────────────────────────────────────────

export const uploadsApi = {
  init: (body: UploadInitRequest, authToken?: string) =>
    request<UploadInitResponse>("/api/uploads/init", {
      method: "POST",
      body: JSON.stringify(body),
      authToken,
    }),

  /**
   * Upload a File directly to the presigned URL (browser only).
   * Returns the storage_key to reference when creating a job.
   */
  uploadFile: async (
    file: File,
    onProgress?: (pct: number) => void,
    authToken?: string,
  ): Promise<string> => {
    const init = await uploadsApi.init(
      {
        filename: file.name,
        content_type: file.type || "video/mp4",
        size_bytes: file.size,
      },
      authToken,
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
