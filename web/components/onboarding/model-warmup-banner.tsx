"use client";

import { useEffect, useRef, useState } from "react";

import { metaApi, type ModelsHealthResponse } from "@/lib/api/client";
import { devToolsEnabled } from "@/lib/dev-tools";

const POLL_MS = 2000;
const COMPLETE_FLASH_MS = 2500;
const MAX_POLL_FAILURES = 30;

const MODEL_LABELS: Record<string, string> = {
  whisper: "Speech recognition",
  yolo: "Subject tracking",
  embedder: "Highlight scoring",
};

type BannerPhase = "hidden" | "loading" | "complete" | "failed";

function countFinished(models: Record<string, { state: string }>): number {
  return Object.values(models).filter(
    (s) => s.state === "ready" || s.state === "skipped",
  ).length;
}

function countTerminal(models: Record<string, { state: string }>): number {
  return Object.values(models).filter(
    (s) => s.state === "ready" || s.state === "skipped" || s.state === "failed",
  ).length;
}

function hasFailure(models: Record<string, { state: string }>): boolean {
  return Object.values(models).some((s) => s.state === "failed");
}

/**
 * First-run model download progress (desktop profile, MASTER_TODO §4.8).
 *
 * Polls /api/health/models until models are warm. On Docker (empty models +
 * ready) the banner stays hidden. Retries when the sidecar is still booting
 * instead of giving up on the first failed fetch.
 *
 * Every model state is terminal once reached (ready/skipped/failed), so `ready`
 * ends the poll loop. Reaching it after a visible download flashes a short
 * confirmation and then hides; reaching it on the first poll shows nothing.
 */
export function ModelWarmupBanner() {
  const [status, setStatus] = useState<ModelsHealthResponse | null>(null);
  const [phase, setPhase] = useState<BannerPhase>("hidden");
  const [retrying, setRetrying] = useState(false);
  const failuresRef = useRef(0);
  const sawLoadingRef = useRef(false);
  const settledRef = useRef(false);
  const completeTimerRef = useRef<number | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);

  const stopPolling = () => {
    settledRef.current = true;
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const poll = async () => {
    if (settledRef.current) return;
    try {
      const res = await metaApi.modelsHealth();
      if (cancelledRef.current || settledRef.current) return;
      failuresRef.current = 0;

      const entries = Object.entries(res.models);
      if (entries.length === 0) {
        // Docker / no prefetch — nothing to show.
        setPhase("hidden");
        stopPolling();
        return;
      }

      setStatus(res);

      // A failed model is terminal, so `ready` goes true even on failure.
      // Surface a persistent, actionable banner instead of hiding silently (F6).
      if (hasFailure(res.models)) {
        sawLoadingRef.current = true;
        setPhase("failed");
        stopPolling();
        return;
      }

      if (res.ready) {
        const terminal = countTerminal(res.models);
        if (
          terminal === entries.length &&
          countFinished(res.models) === entries.length
        ) {
          stopPolling();
          if (!sawLoadingRef.current) {
            // Models were already warm on mount — never announce anything.
            setPhase("hidden");
            return;
          }
          setPhase("complete");
          completeTimerRef.current = window.setTimeout(() => {
            if (!cancelledRef.current) setPhase("hidden");
          }, COMPLETE_FLASH_MS);
        } else {
          setPhase("hidden");
          stopPolling();
        }
        return;
      }

      sawLoadingRef.current = true;
      setPhase("loading");
    } catch {
      failuresRef.current += 1;
      if (failuresRef.current >= MAX_POLL_FAILURES) {
        if (!cancelledRef.current) setPhase("hidden");
        stopPolling();
      }
    }
  };

  const startPolling = () => {
    settledRef.current = false;
    failuresRef.current = 0;
    void poll();
    if (pollTimerRef.current === null) {
      pollTimerRef.current = window.setInterval(() => void poll(), POLL_MS);
    }
  };

  const onRetry = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      await metaApi.modelsRetry();
      setPhase("loading");
      startPolling();
    } catch {
      // Stay on the failed banner; the user can try again.
    } finally {
      setRetrying(false);
    }
  };

  useEffect(() => {
    cancelledRef.current = false;
    startPolling();
    return () => {
      cancelledRef.current = true;
      if (pollTimerRef.current !== null) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (completeTimerRef.current !== null) {
        window.clearTimeout(completeTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (phase === "hidden" || !status) return null;

  const entries = Object.entries(status.models);
  const total = entries.length;
  const finished = countFinished(status.models);
  const isComplete = phase === "complete" && status.ready;
  const isFailed = phase === "failed";
  const failHint =
    status.hint ||
    "Model download failed. Click Retry; if it keeps failing, open a GitHub beta bug report.";

  if (isFailed) {
    return (
      <div
        className="border-b border-red-400/30 bg-red-950/50 px-4 py-2 text-sm text-red-100"
        role="alert"
        aria-live="assertive"
      >
        <div className="container flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-medium">
            AI models didn&apos;t finish downloading ({finished}/{total})
          </span>
          <span className="text-red-100/80">{failHint}</span>
          <button
            type="button"
            onClick={() => void onRetry()}
            disabled={retrying}
            className="rounded-md border border-red-300/40 px-3 py-1 text-xs font-medium text-red-50 transition hover:border-red-200 disabled:opacity-60"
          >
            {retrying ? "Retrying…" : "Retry"}
          </button>
          {devToolsEnabled
            ? entries.map(([name, s]) => (
                <span key={name} className="text-red-200/70">
                  {MODEL_LABELS[name] ?? name}: {s.state}
                </span>
              ))
            : null}
        </div>
      </div>
    );
  }

  return (
    <div
      className={
        isComplete
          ? "border-b border-emerald-400/30 bg-emerald-950/50 px-4 py-2 text-sm text-emerald-100"
          : "border-b border-sky-400/30 bg-sky-950/60 px-4 py-2 text-sm text-sky-100"
      }
      role="status"
      aria-live="polite"
    >
      <div className="container flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-medium">
          {isComplete
            ? `AI models ready (${finished}/${total})`
            : `Preparing AI models (${finished}/${total})…`}
        </span>
        {devToolsEnabled
          ? entries.map(([name, s]) => (
              <span
                key={name}
                className={
                  isComplete ? "text-emerald-200/80" : "text-sky-200/80"
                }
              >
                {MODEL_LABELS[name] ?? name}:{" "}
                {s.state === "downloading" ? (
                  <span className="animate-pulse">downloading</span>
                ) : (
                  s.state
                )}
              </span>
            ))
          : null}
        {!isComplete ? (
          <span className="text-sky-200/60">
            You can browse while this finishes — first job waits for models.
          </span>
        ) : null}
      </div>
    </div>
  );
}
