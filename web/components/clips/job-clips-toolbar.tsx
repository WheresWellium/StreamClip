"use client";

import { Download, Loader2, RefreshCw, Send } from "lucide-react";
import * as React from "react";
import { useTransition } from "react";

import { batchPublishClipsAction, getDistributionContextAction } from "@/lib/api/actions/distribution";
import { regenerateClipAction } from "@/lib/api/actions/jobs";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { jobsApi } from "@/lib/api/client";

interface JobClipsToolbarProps {
  jobId: string;
  clipCount: number;
  approvedClipCount: number;
  jobStatus: string;
  contentProfile?: string | null;
  hasDistribution?: boolean;
}

export function JobClipsToolbar({
  jobId,
  clipCount,
  approvedClipCount,
  jobStatus,
  contentProfile,
  hasDistribution = false,
}: JobClipsToolbarProps) {
  const { push: toast } = useToastSafe();
  const [pending, startTransition] = useTransition();
  const [platform, setPlatform] = React.useState("youtube_shorts");
  const [connectedPlatforms, setConnectedPlatforms] = React.useState<
    { id: string; label: string }[]
  >([]);

  React.useEffect(() => {
    if (!hasDistribution) {
      setConnectedPlatforms([]);
      return;
    }
    let cancelled = false;
    void getDistributionContextAction().then((ctx) => {
      if (cancelled) return;
      const connected = ctx.platforms.filter((p) => p.enabled && p.connected);
      setConnectedPlatforms(connected.map((p) => ({ id: p.id, label: p.label })));
      if (connected[0]) setPlatform(connected[0].id);
    });
    return () => {
      cancelled = true;
    };
  }, [hasDistribution]);

  const ready = jobStatus === "done" && clipCount > 0;
  const canBatchPublish =
    ready && approvedClipCount > 0 && hasDistribution && connectedPlatforms.length > 0;

  function handleBatchPublish() {
    startTransition(async () => {
      const result = await batchPublishClipsAction(jobId, platform);
      if (result.status === "ok") {
        toast(
          "Batch publish queued",
          `${result.queued ?? 0} clip(s) queued${result.skipped ? `, ${result.skipped} skipped` : ""}.`,
        );
      } else {
        toast("Batch publish failed", result.message ?? "Could not publish clips.");
      }
    });
  }

  return (
    <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-medium">
          {clipCount} clip{clipCount === 1 ? "" : "s"}
        </h2>
        {contentProfile && (
          <span className="font-mono text-[10px] uppercase tracking-wide px-1.5 py-px rounded-sm border border-frame/15 bg-muted text-muted-foreground">
            {contentProfile.replace("_", " ")}
          </span>
        )}
      </div>
      {ready && (
        <div className="flex items-center gap-2 flex-wrap">
          {canBatchPublish && (
            <>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="h-7 rounded-sm border border-frame/20 bg-input px-2 text-xs"
                aria-label="Publish platform"
              >
                {connectedPlatforms.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={pending}
                onClick={handleBatchPublish}
                tooltip="Queues all approved, finished clips to the selected platform."
              >
                {pending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Send className="h-3.5 w-3.5" />
                )}
                Publish approved ({approvedClipCount})
              </Button>
            </>
          )}
          <Button
            asChild
            variant="outline"
            size="sm"
            tooltip="Downloads every finished clip in one ZIP file, ranked by score."
          >
            <a href={jobsApi.clipsZipUrl(jobId)} download>
              <Download className="h-3.5 w-3.5" />
              Download all (ZIP)
            </a>
          </Button>
        </div>
      )}
    </div>
  );
}

interface RegenerateClipButtonProps {
  jobId: string;
  clipId: string;
  disabled?: boolean;
}

export function RegenerateClipButton({
  jobId,
  clipId,
  disabled,
}: RegenerateClipButtonProps) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = React.useState<string | null>(null);

  function handleRegenerate() {
    setMessage(null);
    startTransition(async () => {
      const result = await regenerateClipAction(jobId, clipId);
      setMessage(
        result.ok ? "Re-render queued — refresh shortly." : result.message ?? "Failed",
      );
    });
  }

  return (
    <div className="space-y-1">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-full"
        disabled={disabled || pending}
        onClick={handleRegenerate}
      >
        <RefreshCw className={`h-3.5 w-3.5 ${pending ? "animate-spin" : ""}`} />
        Re-render clip
      </Button>
      {message && (
        <p className="text-[10px] text-muted-foreground text-center">{message}</p>
      )}
    </div>
  );
}
