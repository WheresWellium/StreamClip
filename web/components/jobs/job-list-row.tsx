"use client";

import Link from "next/link";

import { Progress } from "@/components/ui/form";
import { HelpTip } from "@/components/ui/help-tip";
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
      className="group flex items-center gap-4 px-6 py-3 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
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
        <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
          <span className="inline-flex items-center gap-0.5">
            <RelativeTime iso={job.created_at} />
            <HelpTip
              content="When this job was submitted."
              label="Created time help"
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
            />
          </span>
          <span>·</span>
          <span className="inline-flex items-center gap-0.5">
            {formatDuration(job.source_duration_secs)}
            <HelpTip
              content="Length of the original source video."
              label="Source duration help"
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
            />
          </span>
          {job.clip_count > 0 && (
            <>
              <span>·</span>
              <span className="inline-flex items-center gap-0.5">
                {job.clip_count} clips
                <HelpTip
                  content="Number of rendered clips in this job."
                  label="Clip count help"
                  className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
                />
              </span>
            </>
          )}
        </div>
      </div>
      {job.status !== "done" &&
        job.status !== "error" &&
        job.status !== "cancelled" && (
          <div className="w-24 shrink-0 flex items-center gap-1">
            <Progress value={job.progress} />
            <HelpTip
              content="Overall pipeline completion for this job."
              label="Job progress help"
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
            />
          </div>
        )}
      <span className="text-muted-foreground group-hover:text-foreground transition-colors text-xs font-mono inline-flex items-center gap-0.5">
        {job.id.slice(0, 8)}
        <HelpTip
          content="Short job ID — open for full details and downloads."
          label="Job ID help"
          className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
        />
      </span>
    </Link>
  );
}
