"use client";

import * as React from "react";

import { jobsApi } from "@/lib/api/client";
import type { ProgressEvent } from "@/lib/api/types";
import { userFacingErrorMessage } from "@/lib/help/user-errors";

type SSEState =
  | { status: "connecting"; lastEvent: ProgressEvent | null }
  | { status: "reconnecting"; lastEvent: ProgressEvent | null }
  | { status: "open"; lastEvent: ProgressEvent | null }
  | { status: "polling"; lastEvent: ProgressEvent | null }
  | { status: "done"; lastEvent: ProgressEvent }
  | { status: "error"; message: string; lastEvent?: ProgressEvent | null };

export type JobProgressState = SSEState & {
  /** True when no progress events for STALL_AFTER_MS while job is still running. */
  stalled: boolean;
};

const POLL_INTERVAL_MS = 4000;
/** Fall back to REST polling only after SSE stays down this long. */
const SSE_FALLBACK_MS = 20_000;
/** No progress activity while non-terminal ⇒ show stalled hint. */
const STALL_AFTER_MS = 3 * 60_000;

function prevLastEvent(prev: SSEState): ProgressEvent | null {
  return "lastEvent" in prev ? (prev.lastEvent ?? null) : null;
}

/**
 * Subscribe to job progress via same-origin BFF SSE route (auth cookies forwarded).
 * EventSource auto-reconnects with Last-Event-Id; polling is a last resort.
 */
export function useJobProgress(
  jobId: string | null,
  options: { enabled?: boolean } = {},
): JobProgressState {
  const { enabled = true } = options;
  const [state, setState] = React.useState<SSEState>({
    status: "connecting",
    lastEvent: null,
  });
  const [stalled, setStalled] = React.useState(false);
  const lastActivityRef = React.useRef(Date.now());

  React.useEffect(() => {
    if (!jobId || !enabled) return;

    let closed = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
    let stallTimer: ReturnType<typeof setInterval> | null = null;
    let sawTerminal = false;
    let pollFailures = 0;
    lastActivityRef.current = Date.now();
    setStalled(false);

    const markActivity = () => {
      lastActivityRef.current = Date.now();
      setStalled(false);
      pollFailures = 0;
    };

    const clearFallback = () => {
      if (fallbackTimer) {
        clearTimeout(fallbackTimer);
        fallbackTimer = null;
      }
    };

    const startPolling = () => {
      if (pollTimer || closed || sawTerminal) return;
      setState((prev) =>
        prev.status === "done" || prev.status === "error"
          ? prev
          : {
              status: "polling",
              lastEvent: prevLastEvent(prev),
            },
      );
      pollTimer = setInterval(async () => {
        try {
          const job = await jobsApi.get(jobId);
          const terminal =
            job.status === "done" ||
            job.status === "error" ||
            job.status === "cancelled";
          const event: ProgressEvent = {
            job_id: jobId,
            stage: job.current_stage,
            progress: job.progress,
            message: userFacingErrorMessage(
              job.error_message,
              job.error_code,
              "",
            ),
            status:
              job.status === "done" || job.status === "cancelled"
                ? "done"
                : job.status === "error"
                  ? "error"
                  : "processing",
            ts: Date.now() / 1000,
          };
          if (job.status === "done") {
            sawTerminal = true;
            markActivity();
            setState({ status: "done", lastEvent: event });
          } else if (job.status === "cancelled") {
            sawTerminal = true;
            markActivity();
            setState({ status: "done", lastEvent: event });
          } else if (job.status === "error") {
            sawTerminal = true;
            markActivity();
            setState({
              status: "error",
              message: userFacingErrorMessage(
                job.error_message,
                job.error_code,
                "Job failed.",
              ),
              lastEvent: event,
            });
          } else {
            markActivity();
            setState({ status: "polling", lastEvent: event });
          }
          if (terminal && pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
        } catch {
          pollFailures += 1;
          if (pollFailures >= 3) {
            setStalled(true);
          }
        }
      }, POLL_INTERVAL_MS);
    };

    const schedulePollingFallback = () => {
      if (fallbackTimer || pollTimer || closed || sawTerminal) return;
      fallbackTimer = setTimeout(() => {
        fallbackTimer = null;
        if (!closed && !sawTerminal) startPolling();
      }, SSE_FALLBACK_MS);
    };

    const bffUrl = `/api/jobs/${jobId}/progress`;
    const source = new EventSource(bffUrl);

    source.addEventListener("open", () => {
      clearFallback();
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      setState((prev) => ({
        status: "open",
        lastEvent: prevLastEvent(prev),
      }));
    });

    const handleEvent = (event: MessageEvent, terminal = false) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        markActivity();
        if (terminal || data.status === "done" || data.status === "error") {
          sawTerminal = true;
          clearFallback();
        }
        if (data.status === "error") {
          setState({
            status: "error",
            message: userFacingErrorMessage(
              data.message,
              data.extra && typeof data.extra === "object"
                ? String((data.extra as Record<string, unknown>).code ?? "")
                : null,
              "Pipeline error",
            ),
            lastEvent: data,
          });
          source.close();
          return;
        }
        setState({
          status: terminal || data.status === "done" ? "done" : "open",
          lastEvent: data,
        });
        if (terminal || data.status === "done") {
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
          sawTerminal = true;
          clearFallback();
          setState({
            status: "error",
            message: userFacingErrorMessage(
              data.message,
              data.extra && typeof data.extra === "object"
                ? String((data.extra as Record<string, unknown>).code ?? "")
                : null,
              "Pipeline error",
            ),
            lastEvent: data,
          });
        } catch {
          setState({ status: "error", message: "Stream error", lastEvent: null });
        }
        source.close();
        return;
      }
      // Transient disconnect — keep EventSource alive for auto-reconnect + Last-Event-Id.
      setState((prev) => {
        if (prev.status === "done" || prev.status === "error") return prev;
        return {
          status: "reconnecting",
          lastEvent: "lastEvent" in prev ? prev.lastEvent : null,
        };
      });
      schedulePollingFallback();
    });

    stallTimer = setInterval(() => {
      if (closed || sawTerminal) return;
      if (Date.now() - lastActivityRef.current >= STALL_AFTER_MS) {
        setStalled(true);
      }
    }, 15_000);

    return () => {
      closed = true;
      source.close();
      clearFallback();
      if (pollTimer) clearInterval(pollTimer);
      if (stallTimer) clearInterval(stallTimer);
    };
  }, [jobId, enabled]);

  return { ...state, stalled };
}
