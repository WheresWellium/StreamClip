"use client";

import { CheckCircle2, Circle, Loader2, Radio } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useJobClipFeed } from "@/lib/api/use-job-clip-feed";
import type { ClipFeedItem } from "@/lib/api/types";
import { jobClipsPath } from "@/lib/jobs/job-route-id";
import { cn } from "@/lib/utils/format";

type Props = {
  jobId: string;
  jobStatus: string;
  initialClipCount?: number;
  showReviewLink?: boolean;
};

function ClipFeedStatusIcon({ status }: { status: ClipFeedItem["feedStatus"] }) {
  if (status === "done") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
  }
  if (status === "processing") {
    return <Loader2 className="h-4 w-4 text-sky-400 animate-spin shrink-0" />;
  }
  return <Circle className="h-4 w-4 text-muted-foreground shrink-0" />;
}

export function LiveClipFeed({
  jobId,
  jobStatus,
  initialClipCount = 0,
  showReviewLink = false,
}: Props) {
  const terminal = jobStatus === "done" || jobStatus === "error" || jobStatus === "cancelled";
  const { clips, connected } = useJobClipFeed(jobId, {
    enabled: !terminal || initialClipCount > 0,
  });

  if (clips.length === 0 && terminal) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">Live clip feed</CardTitle>
            <CardDescription>
              Clips appear here as they are discovered and rendered.
            </CardDescription>
          </div>
          {!terminal && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-wide",
                connected ? "text-emerald-400" : "text-muted-foreground",
              )}
            >
              <Radio className="h-3 w-3" />
              {connected ? "Live" : "Connecting"}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {clips.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Waiting for highlight detection…
          </p>
        ) : (
          <ul className="space-y-2">
            {clips.map((clip) => (
              <li
                key={clip.clip_id}
                className="flex items-center gap-3 rounded-md border border-border/50 px-3 py-2 text-sm"
              >
                <ClipFeedStatusIcon status={clip.feedStatus} />
                <span className="font-mono text-xs text-muted-foreground w-6 shrink-0">
                  #{clip.rank + 1}
                </span>
                <span className="flex-1 truncate">
                  {clip.title?.trim() || `Clip ${clip.rank + 1}`}
                </span>
                <span
                  className={cn(
                    "text-[10px] uppercase tracking-wide font-mono shrink-0",
                    clip.feedStatus === "done"
                      ? "text-emerald-400"
                      : clip.feedStatus === "processing"
                        ? "text-sky-400"
                        : "text-muted-foreground",
                  )}
                >
                  {clip.feedStatus}
                </span>
              </li>
            ))}
          </ul>
        )}
        {showReviewLink && clips.some((c) => c.feedStatus === "done") ? (
          <p className="text-xs text-muted-foreground mt-4">
            <a href={jobClipsPath(jobId)} className="text-sky-400 hover:underline">
              Open clips workspace →
            </a>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
