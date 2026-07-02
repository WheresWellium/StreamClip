"use client";

import * as React from "react";

import { jobsApi } from "@/lib/api/client";
import type { ProgressEvent } from "@/lib/api/types";

type SSEState =
  | { status: "connecting" }
  | { status: "open"; lastEvent: ProgressEvent | null }
  | { status: "done"; lastEvent: ProgressEvent }
  | { status: "error"; message: string };

const POLL_INTERVAL_MS = 4000;

/**
 * Subscribe to job progress via same-origin BFF SSE route (auth cookies forwarded).
 * Falls back to polling GET /api/jobs/:id when SSE is unavailable.
 */
export function useJobProgress(
  jobId: string | null,
  options: { enabled?: boolean } = {},
): SSEState {
  const { enabled = true } = options;
  const [state, setState] = React.useState<SSEState>({
    status: "connecting",
  });

  React.useEffect(() => {
    if (!jobId || !enabled) return;

    let closed = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (pollTimer) return;
      pollTimer = setInterval(async () => {
        try {
          const job = await jobsApi.get(jobId);
          const terminal = job.status === "done" || job.status === "error" || job.status === "cancelled";
          const event: ProgressEvent = {
            job_id: jobId,
            stage: job.current_stage,
            progress: job.progress,
            message: job.error_message ?? "",
            status: job.status === "done" ? "done" : job.status === "error" ? "error" : "processing",
            ts: Date.now() / 1000,
          };
          setState({
            status: terminal && job.status === "done" ? "done" : terminal ? "error" : "open",
            lastEvent: event,
          } as SSEState);
          if (terminal && pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
        } catch {
          /* keep polling */
        }
      }, POLL_INTERVAL_MS);
    };

    const bffUrl = `/api/jobs/${jobId}/progress`;
    const source = new EventSource(bffUrl);

    source.addEventListener("open", () => {
      setState((prev) =>
        prev.status === "open" ? prev : { status: "open", lastEvent: null },
      );
    });

    const handleEvent = (event: MessageEvent, terminal = false) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setState({
          status: terminal && data.status === "done" ? "done" : "open",
          lastEvent: data,
        });
        if (terminal) {
          source.close();
        }
      } catch (err) {
        console.warn("SSE parse error", err);
      }
    };

    source.addEventListener("progress", (e) =>
      handleEvent(e as MessageEvent, false),
    );
    source.addEventListener("done", (e) =>
      handleEvent(e as MessageEvent, true),
    );
    source.addEventListener("error", (e) => {
      const ev = e as MessageEvent;
      if (ev.data) {
        try {
          const data = JSON.parse(ev.data) as ProgressEvent;
          setState({
            status: "error",
            message: data.message || "Pipeline error",
          });
        } catch {
          setState({ status: "error", message: "Stream error" });
        }
        source.close();
      } else if (source.readyState === EventSource.CLOSED) {
        source.close();
        if (!closed) startPolling();
      }
    });

    return () => {
      closed = true;
      source.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [jobId, enabled]);

  return state;
}
