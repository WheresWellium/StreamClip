"use client";

import { Download, RefreshCw } from "lucide-react";
import * as React from "react";
import { useTransition } from "react";

import { regenerateClipAction } from "@/app/actions/jobs";
import { Button } from "@/components/ui/button";
import { HelpTip } from "@/components/ui/help-tip";
import { jobsApi } from "@/lib/api/client";
interface JobClipsToolbarProps {
  jobId: string;
  clipCount: number;
  jobStatus: string;
  contentProfile?: string | null;
}

export function JobClipsToolbar({
  jobId,
  clipCount,
  jobStatus,
  contentProfile,
}: JobClipsToolbarProps) {
  const ready = jobStatus === "done" && clipCount > 0;

  return (
    <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-medium">
          {clipCount} clip{clipCount === 1 ? "" : "s"}
        </h2>
        {contentProfile && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground capitalize">
            {contentProfile.replace("_", " ")}
          </span>
        )}
      </div>
      {ready && (
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <a href={jobsApi.clipsZipUrl(jobId)} download>
              <Download className="h-3.5 w-3.5" />
              Download all (ZIP)
            </a>
          </Button>
          <HelpTip
            content="Downloads every finished clip in one ZIP file, ranked by score."
            label="Download all help"
          />
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
