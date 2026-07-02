"use client";

import { Archive, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils/format";

export type ClipPublishStatus = {
  platform: string;
  status: string;
  publish_job_id: string;
  external_url?: string | null;
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube_shorts: "YouTube",
  tiktok: "TikTok",
};

function statusMeta(status: string): {
  label: string;
  className: string;
  icon: React.ReactNode;
} {
  switch (status) {
    case "published":
      return {
        label: "Published",
        className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
        icon: <CheckCircle2 className="h-3 w-3" aria-hidden />,
      };
    case "failed":
      return {
        label: "Failed",
        className: "border-red-500/40 bg-red-500/10 text-red-300",
        icon: <XCircle className="h-3 w-3" aria-hidden />,
      };
    case "scheduled":
      return {
        label: "Scheduled",
        className: "border-amber-500/40 bg-amber-500/10 text-amber-300",
        icon: <Clock className="h-3 w-3" aria-hidden />,
      };
    case "publishing":
    case "pending":
      return {
        label: status === "publishing" ? "Uploading" : "Queued",
        className: "border-sky-500/40 bg-sky-500/10 text-sky-300",
        icon: <Loader2 className="h-3 w-3 animate-spin" aria-hidden />,
      };
    case "cancelled":
      return {
        label: "Cancelled",
        className: "border-border/60 bg-muted/40 text-muted-foreground",
        icon: <XCircle className="h-3 w-3" aria-hidden />,
      };
    default:
      return {
        label: status,
        className: "border-border/60 bg-muted/40 text-muted-foreground",
        icon: null,
      };
  }
}

type Props = {
  statuses: ClipPublishStatus[];
  showVaultChip?: boolean;
  className?: string;
};

export function PublishStatusBadge({ statuses, showVaultChip, className }: Props) {
  if (statuses.length === 0 && !showVaultChip) return null;

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {showVaultChip && (
        <span className="inline-flex items-center gap-1 rounded border border-violet-500/40 bg-violet-500/10 px-1.5 py-0.5 text-[10px] text-violet-200">
          <Archive className="h-3 w-3" aria-hidden />
          In Vault
        </span>
      )}
      {statuses.map((row) => {
        const meta = statusMeta(row.status);
        const platformLabel = PLATFORM_LABELS[row.platform] ?? row.platform;
        const chip = (
          <span
            key={`${row.platform}-${row.publish_job_id}`}
            className={cn(
              "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px]",
              meta.className,
            )}
          >
            {meta.icon}
            <span>
              {platformLabel}: {meta.label}
            </span>
          </span>
        );
        if (row.status === "published" && row.external_url) {
          return (
            <Link
              key={`${row.platform}-${row.publish_job_id}`}
              href={row.external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-90"
            >
              {chip}
            </Link>
          );
        }
        if (row.status === "failed" || row.status === "scheduled" || row.status === "pending") {
          return (
            <Link
              key={`${row.platform}-${row.publish_job_id}`}
              href="/distribution"
              className="hover:opacity-90"
            >
              {chip}
            </Link>
          );
        }
        return chip;
      })}
    </div>
  );
}
