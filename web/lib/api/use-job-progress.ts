"use client";

import * as React from "react";

import { jobsApi } from "@/lib/api/client";
import type { ProgressEvent } from "@/lib/api/types";

type SSEState =
  | { status: "connecting" }
  | { status: "open"; lastEvent: ProgressEvent | null }
  | { status: "done"; lastEvent: ProgressEvent }
  | { status: "error"; message: string };

/**
 * Subscribe to a job's SSE progress stream. Returns the latest event and
 * connection status. Closes automatically when the job emits `done` or
 * `error`, or when the component unmounts.
 *
 * EventSource auto-reconnects with exponential backoff via `Last-Event-Id`,
 * so a brief network blip doesn't lose the stream.
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

    const source = new EventSource(jobsApi.progressUrl(jobId));

    source.addEventListener("open", () => {
      setState((prev) =>
        prev.status === "open"
          ? prev
          : { status: "open", lastEvent: null },
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
      } else if (source.readyState === EventSource.CLOSED) {
        setState({ status: "error", message: "Connection closed" });
      }
      source.close();
    });

    return () => source.close();
  }, [jobId, enabled]);

  return state;
}
