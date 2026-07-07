"use client";

import { useEffect, useState } from "react";

import { metaApi, type ModelsHealthResponse } from "@/lib/api/client";

const POLL_MS = 4000;

const MODEL_LABELS: Record<string, string> = {
  whisper: "Speech recognition",
  yolo: "Subject tracking",
  embedder: "Highlight scoring",
};

/**
 * First-run model download progress (desktop profile, MASTER_TODO §4.8).
 *
 * The sidecar prefetches ML models in the background at boot; this banner
 * polls /api/health/models and shows per-model progress until everything is
 * ready. On Docker (models baked into the image) the endpoint reports
 * ready with no models, so the banner never renders.
 */
export function ModelWarmupBanner() {
  const [status, setStatus] = useState<ModelsHealthResponse | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await metaApi.modelsHealth();
        if (cancelled) return;
        setStatus(res);
        if (res.ready) setDone(true);
      } catch {
        // Endpoint unreachable (older sidecar or API down) — stay hidden.
        if (!cancelled) setDone(true);
      }
    };

    void poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [done]);

  if (done || !status || status.ready) return null;

  const entries = Object.entries(status.models);
  const readyCount = entries.filter(
    ([, s]) => s.state === "ready" || s.state === "skipped",
  ).length;

  return (
    <div
      className="border-b border-sky-400/30 bg-sky-950/60 px-4 py-2 text-sm text-sky-100"
      role="status"
      aria-live="polite"
    >
      <div className="container flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-medium">
          Preparing AI models ({readyCount}/{entries.length})…
        </span>
        {entries.map(([name, s]) => (
          <span key={name} className="text-sky-200/80">
            {MODEL_LABELS[name] ?? name}:{" "}
            {s.state === "downloading" ? (
              <span className="animate-pulse">downloading</span>
            ) : (
              s.state
            )}
          </span>
        ))}
        <span className="text-sky-200/60">
          You can browse while this finishes — first job waits for models.
        </span>
      </div>
    </div>
  );
}
