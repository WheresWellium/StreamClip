"use client";

import { CheckCircle2, CircleAlert, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/format";

export type StackHealthSnapshot = {
  status: string;
  checks: Record<string, boolean>;
  worker?: boolean | null;
};

type CheckRow = {
  id: string;
  label: string;
  ok: boolean | null;
  hint?: string;
};

const CHECK_LABELS: Record<string, { label: string; hint: string }> = {
  database: {
    label: "Database",
    hint: "Postgres or SQLite must accept connections.",
  },
  redis: {
    label: "Redis / queue broker",
    hint: "Required for Docker beta; skipped in desktop in-process mode.",
  },
  storage: {
    label: "Object storage",
    hint: "MinIO or local storage for uploads and renders.",
  },
  ollama: {
    label: "LLM (Ollama)",
    hint: "Optional — virality scoring falls back without it.",
  },
  cuda: {
    label: "CUDA (NVIDIA GPU)",
    hint: "Optional — CPU path works but is slower.",
  },
  nvenc: {
    label: "NVENC encode",
    hint: "Optional on Windows/Linux Docker with NVIDIA.",
  },
  mps: {
    label: "MPS (Apple Silicon)",
    hint: "Optional — Metal ML on macOS desktop; Docker on Mac uses CPU.",
  },
};

function rowsFromSnapshot(data: StackHealthSnapshot | null): CheckRow[] {
  if (!data) return [];
  const rows: CheckRow[] = [];
  for (const [key, meta] of Object.entries(CHECK_LABELS)) {
    if (!(key in data.checks)) continue;
    rows.push({
      id: key,
      label: meta.label,
      ok: data.checks[key] ?? false,
      hint: meta.hint,
    });
  }
  if (data.worker != null) {
    rows.push({
      id: "worker",
      label: "Celery worker",
      ok: data.worker,
      hint: "Processes clip jobs off the API queue.",
    });
  }
  return rows;
}

type Props = {
  data: StackHealthSnapshot | null;
  loading?: boolean;
  onRetry?: () => void;
};

export function HealthChecklist({ data, loading, onRetry }: Props) {
  const rows = rowsFromSnapshot(data);
  const allRequiredOk =
    data != null &&
    data.status === "ok" &&
    rows.filter((r) => r.id !== "ollama" && r.id !== "cuda" && r.id !== "nvenc" && r.id !== "mps").every((r) => r.ok);

  return (
    <div className="space-y-4">
      {loading && (
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Checking services…
        </p>
      )}

      {!loading && data && (
        <>
          <p
            className={cn(
              "text-sm font-medium",
              allRequiredOk ? "text-emerald-400" : "text-amber-300",
            )}
          >
            {allRequiredOk
              ? "Core services look good — you can create a job."
              : "Some services need attention before your first job."}
          </p>
          <ul className="space-y-2">
            {rows.map((row) => (
              <li
                key={row.id}
                className="flex items-start gap-2 rounded-sm border border-frame/15 px-3 py-2 text-sm"
              >
                {row.ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <CircleAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="font-medium">{row.label}</p>
                  {row.hint && (
                    <p className="text-xs text-muted-foreground mt-0.5">{row.hint}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} disabled={loading}>
          Re-check
        </Button>
      )}

      <p className="text-xs text-muted-foreground">
        GPU checks are optional. See{" "}
        <a
          href="https://streamclip-henna.vercel.app/tutorials/TUTORIAL_GPU_SETUP/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-foreground"
        >
          GPU setup
        </a>{" "}
        or{" "}
        <a
          href="https://streamclip-henna.vercel.app/tutorials/TUTORIAL_TROUBLESHOOTING/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-foreground"
        >
          troubleshooting
        </a>
        .
      </p>
    </div>
  );
}
