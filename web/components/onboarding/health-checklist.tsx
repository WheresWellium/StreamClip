"use client";

import Link from "next/link";
import { CheckCircle2, CircleAlert, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { devToolsEnabled } from "@/lib/dev-tools";
import { helpHref } from "@/lib/docs";
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
    hint: "Job history and clip metadata must be reachable.",
  },
  redis: {
    label: "Job queue",
    hint: "Required for multi-service installs; skipped in desktop mode.",
  },
  storage: {
    label: "Cloud storage",
    hint: "Uploads and finished renders need storage.",
  },
  ollama: {
    label: "AI scoring (optional)",
    hint: "Optional — virality scoring falls back without it.",
  },
  cuda: {
    label: "GPU acceleration (optional)",
    hint: "Optional — CPU path works but is slower.",
  },
  nvenc: {
    label: "Fast video encode (optional)",
    hint: "Optional on Windows/Linux with a supported GPU.",
  },
  mps: {
    label: "Apple GPU (optional)",
    hint: "Optional — Metal acceleration on macOS desktop builds.",
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
      label: "Background worker",
      ok: data.worker,
      hint: "Processes clip jobs off the main app.",
    });
  }
  return rows;
}

function coreServicesOk(data: StackHealthSnapshot, rows: CheckRow[]): boolean {
  return (
    data.status === "ok" &&
    rows
      .filter(
        (r) =>
          r.id !== "ollama" &&
          r.id !== "cuda" &&
          r.id !== "nvenc" &&
          r.id !== "mps",
      )
      .every((r) => r.ok)
  );
}

type Props = {
  data: StackHealthSnapshot | null;
  loading?: boolean;
  onRetry?: () => void;
  /** Product builds use a single Ready / Needs attention status. */
  compact?: boolean;
};

export function HealthChecklist({ data, loading, onRetry, compact }: Props) {
  const isCompact = compact ?? !devToolsEnabled;
  const rows = rowsFromSnapshot(data);
  const allRequiredOk = data != null && coreServicesOk(data, rows);

  if (isCompact) {
    return (
      <div className="space-y-4">
        {loading && (
          <p className="text-sm text-muted-foreground flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Checking services…
          </p>
        )}

        {!loading && data && (
          <p
            className={cn(
              "text-sm font-medium flex items-center gap-2",
              allRequiredOk ? "text-emerald-400" : "text-amber-300",
            )}
          >
            {allRequiredOk ? (
              <>
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Ready — you can create a job.
              </>
            ) : (
              <>
                <CircleAlert className="h-4 w-4 shrink-0" />
                Needs attention — check Help before your first job.
              </>
            )}
          </p>
        )}

        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry} disabled={loading}>
            Re-check
          </Button>
        )}

        <p className="text-xs text-muted-foreground">
          <Link
            href={helpHref("/tutorials/TUTORIAL_TROUBLESHOOTING/")}
            className="underline hover:text-foreground"
          >
            How to fix common issues
          </Link>{" "}
          in the Help center.
        </p>
      </div>
    );
  }

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
        GPU checks are optional. CPU-only is supported but slower — see{" "}
        <Link
          href={helpHref("/BETA_KNOWN_ISSUES/")}
          className="underline hover:text-foreground"
        >
          known issues
        </Link>{" "}
        or{" "}
        <Link
          href={helpHref("/tutorials/TUTORIAL_TROUBLESHOOTING/")}
          className="underline hover:text-foreground"
        >
          troubleshooting
        </Link>
        .
      </p>
    </div>
  );
}
