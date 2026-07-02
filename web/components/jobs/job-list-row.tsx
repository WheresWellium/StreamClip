"use client";

import Link from "next/link";

import { Progress } from "@/components/ui/form";
import { LegendBadge } from "@/components/ui/legend-badge";
import { RelativeTime } from "@/components/ui/relative-time";
import type { JobListItem } from "@/lib/api/types";
import { legendForStatus } from "@/lib/help/legends";
import {
  formatDuration,
  statusColors,
} from "@/lib/utils/format";

export function JobListRow({ job }: { job: JobListItem }) {
  return (
    <Link
      href={`/jobs/${job.id}`}
      className="group flex items-center gap-4 px-4 py-2.5 hover:bg-frame/5 transition-colors border-b border-frame/10 last:border-0"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <p className="text-sm font-medium truncate">
            {job.source_title ?? "Untitled job"}
          </p>
          <LegendBadge
            className={statusColors[job.status] ?? statusColors.queued}
            tip={legendForStatus(job.status)}
            tipLabel="Job status help"
          >
            {job.status}
          </LegendBadge>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground flex-wrap">
          <RelativeTime iso={job.created_at} />
          <span aria-hidden>/</span>
          <span>{formatDuration(job.source_duration_secs)}</span>
          {job.clip_count > 0 && (
            <>
              <span aria-hidden>/</span>
              <span>{job.clip_count} clips</span>
            </>
          )}
        </div>
      </div>
      {job.status !== "done" &&
        job.status !== "error" &&
        job.status !== "cancelled" && (
          <div className="w-24 shrink-0">
            <Progress value={job.progress} />
          </div>
        )}
      <span className="text-muted-foreground group-hover:text-foreground transition-colors text-[11px] font-mono">
        {job.id.slice(0, 8)}
      </span>
    </Link>
  );
}
