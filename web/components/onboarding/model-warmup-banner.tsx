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

type BannerPhase = "hidden" | "loading" | "complete";

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

/**
 * First-run model download progress (desktop profile, MASTER_TODO §4.8).
 *
 * Polls /api/health/models until models are warm. When the models map is empty
 * (already warm or prefetch disabled) the banner stays hidden. Retries when
 * the sidecar is still booting instead of giving up on the first failed fetch.
 */
export function ModelWarmupBanner() {
  const [status, setStatus] = useState<ModelsHealthResponse | null>(null);
  const [phase, setPhase] = useState<BannerPhase>("hidden");
  const failuresRef = useRef(0);
  const completeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await metaApi.modelsHealth();
        if (cancelled) return;
        failuresRef.current = 0;

        const entries = Object.entries(res.models);
        if (entries.length === 0) {
          // Models already warm or prefetch disabled — nothing to show.
          setPhase("hidden");
          return;
        }

        setStatus(res);

        if (res.ready) {
          const terminal = countTerminal(res.models);
          if (terminal === entries.length && countFinished(res.models) === entries.length) {
            setPhase("complete");
            if (completeTimerRef.current !== null) {
              window.clearTimeout(completeTimerRef.current);
            }
            completeTimerRef.current = window.setTimeout(() => {
              if (!cancelled) setPhase("hidden");
            }, COMPLETE_FLASH_MS);
          } else {
            setPhase("hidden");
          }
          return;
        }

        setPhase("loading");
      } catch {
        failuresRef.current += 1;
        if (failuresRef.current >= MAX_POLL_FAILURES) {
          if (!cancelled) setPhase("hidden");
        }
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      if (completeTimerRef.current !== null) {
        window.clearTimeout(completeTimerRef.current);
      }
    };
  }, []);

  if (phase === "hidden" || !status) return null;

  const entries = Object.entries(status.models);
  const total = entries.length;
  const finished = countFinished(status.models);
  const isComplete = phase === "complete" && status.ready;

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
                className={isComplete ? "text-emerald-200/80" : "text-sky-200/80"}
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
