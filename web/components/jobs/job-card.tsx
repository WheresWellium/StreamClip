"use client";

import { useRouter } from "next/navigation";
import { Film } from "lucide-react";

import { EditableJobTitle } from "@/components/jobs/editable-job-title";
import { LegendBadge } from "@/components/ui/legend-badge";
import { Progress } from "@/components/ui/form";
import { RelativeTime } from "@/components/ui/relative-time";
import type { JobListItem } from "@/lib/api/types";
import { legendForStatus } from "@/lib/help/legends";
import {
  formatDuration,
  statusColors,
} from "@/lib/utils/format";

export function JobCard({ job }: { job: JobListItem }) {
  const router = useRouter();
  const showProgress =
    job.status !== "done" &&
    job.status !== "error" &&
    job.status !== "cancelled";

  function openJob() {
    router.push(`/jobs/${job.id}`);
  }

  return (
    <article
      className="group rounded-lg border border-border/60 bg-card overflow-hidden flex flex-col hover:border-sky-400/30 transition-colors cursor-pointer"
      role="link"
      tabIndex={0}
      onClick={openJob}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openJob();
        }
      }}
      aria-label={`Open job ${job.display_title ?? job.source_title ?? job.id.slice(0, 8)}`}
    >
      <div className="relative bg-black/80" style={{ aspectRatio: "16/9" }}>
        <div className="absolute inset-0 grid place-items-center text-muted-foreground">
          <Film className="h-8 w-8 opacity-40" />
        </div>
        <span className="absolute top-2 left-2">
          <LegendBadge
            className={statusColors[job.status] ?? statusColors.queued}
            tip={legendForStatus(job.status)}
            tipLabel="Job status help"
          >
            {job.status}
          </LegendBadge>
        </span>
        {job.source_duration_secs ? (
          <span className="absolute bottom-2 right-2 text-[10px] font-mono bg-black/70 px-1.5 py-0.5 rounded">
            {formatDuration(job.source_duration_secs)}
          </span>
        ) : null}
      </div>

      <div className="p-3 space-y-2 flex-1 flex flex-col">
        <div
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <EditableJobTitle
            jobId={job.id}
            displayTitle={job.display_title}
            sourceTitle={job.source_title}
          />
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground flex-wrap">
          <RelativeTime iso={job.created_at} />
          {job.clip_count > 0 ? (
            <>
              <span aria-hidden>·</span>
              <span>{job.clip_count} clips</span>
            </>
          ) : null}
        </div>
        {showProgress ? (
          <div className="pt-1">
            <Progress value={job.progress} />
          </div>
        ) : null}
        <span className="text-[10px] font-mono text-muted-foreground group-hover:text-foreground transition-colors mt-auto">
          {job.id.slice(0, 8)}
        </span>
      </div>
    </article>
  );
}
