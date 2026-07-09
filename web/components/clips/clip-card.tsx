"use client";

import { Download, Link2, Loader2, Play, Share2 } from "lucide-react";
import * as React from "react";

import { useToastSafe } from "@/components/providers/toast-provider";

import { updateClipApprovalAction } from "@/lib/api/actions/approval";
import { refreshClipMediaAction } from "@/lib/api/actions/jobs";
import { ApprovalToggle, type ApprovalValue } from "@/components/clips/approval-toggle";
import { ClipDestinationsDrawer } from "@/components/clips/clip-destinations-drawer";
import { PublishStatusBadge } from "@/components/clips/publish-status-badge";
import { ClipEditor } from "@/components/clips/clip-editor";
import { ClipFeedbackButtons } from "@/components/clips/clip-feedback";
import { RegenerateClipButton } from "@/components/clips/job-clips-toolbar";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/form";
import { LegendBadge, LegendLabel } from "@/components/ui/legend-badge";
import { SectionLegend } from "@/components/ui/section-legend";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ClipOut } from "@/lib/api/types";
import { userFacingErrorMessage } from "@/lib/help/user-errors";
import type { AspectRatioOption, MetaOption } from "@/lib/api/meta-types";
import { CAPTION_STYLE_IDS, REFRAME_PRESET_IDS } from "@/lib/creator-option-ids";
import { CLIP_SCORE_LEGEND, legendForEmotion } from "@/lib/help/legends";
import {
  cn,
  emotionColors,
  formatDuration,
  formatScore,
} from "@/lib/utils/format";
import { downloadBlob } from "@/lib/utils/download";

interface ClipCardProps {
  clip: ClipOut;
  jobId: string;
  jobDone?: boolean;
  sourceDurationSecs?: number | null;
  captionStyleOptions?: MetaOption[];
  reframePresetOptions?: MetaOption[];
  jobAspectRatio?: string | null;
  aspectRatioCatalog?: AspectRatioOption[];
}

export function ClipCard({
  clip,
  jobId,
  jobDone = false,
  sourceDurationSecs,
  captionStyleOptions,
  reframePresetOptions,
  jobAspectRatio,
  aspectRatioCatalog,
}: ClipCardProps) {
  const captionOptions =
    captionStyleOptions ??
    CAPTION_STYLE_IDS.map((id) => ({ id, label: id.replace(/_/g, " ") }));
  const reframeOptions =
    reframePresetOptions ??
    REFRAME_PRESET_IDS.map((id) => ({ id, label: id.replace(/_/g, " ") }));
  const { push: toast } = useToastSafe();
  const [playing, setPlaying] = React.useState(false);
  const [showTranscript, setShowTranscript] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [destinationsOpen, setDestinationsOpen] = React.useState(false);
  const approval = (clip.approval_status ?? "draft") as ApprovalValue;
  const [approvalLocal, setApprovalLocal] = React.useState<ApprovalValue>(approval);
  const [downloadUrl, setDownloadUrl] = React.useState(clip.download_url ?? null);
  const [thumbnailUrl, setThumbnailUrl] = React.useState(clip.thumbnail_url ?? null);
  const refreshingRef = React.useRef(false);
  const retriedVideoRef = React.useRef(false);
  const retriedThumbRef = React.useRef(false);

  React.useEffect(() => {
    setApprovalLocal((clip.approval_status ?? "draft") as ApprovalValue);
  }, [clip.approval_status]);

  React.useEffect(() => {
    setDownloadUrl(clip.download_url ?? null);
    setThumbnailUrl(clip.thumbnail_url ?? null);
    retriedVideoRef.current = false;
    retriedThumbRef.current = false;
  }, [clip.download_url, clip.thumbnail_url]);

  const refreshMedia = React.useCallback(async () => {
    if (refreshingRef.current) return null;
    refreshingRef.current = true;
    try {
      const result = await refreshClipMediaAction(jobId, clip.id);
      if (result.ok) {
        setDownloadUrl(result.download_url);
        setThumbnailUrl(result.thumbnail_url);
        return result;
      }
      toast("Couldn't refresh clip media", result.message ?? "The link may have expired.");
      return null;
    } finally {
      refreshingRef.current = false;
    }
  }, [jobId, clip.id, toast]);

  async function onVideoError() {
    if (retriedVideoRef.current) {
      toast("Playback failed", "Couldn't reload this clip's video. Try refreshing the page.");
      return;
    }
    retriedVideoRef.current = true;
    await refreshMedia();
  }

  async function onThumbnailError() {
    if (retriedThumbRef.current) return;
    retriedThumbRef.current = true;
    await refreshMedia();
  }

  async function onDownloadClick() {
    const url = downloadUrl;
    if (!url) return;
    const filename = (clip.title || `clip-${clip.rank + 1}`) + ".mp4";
    try {
      const res = await fetch(url, { method: "HEAD" });
      if (!res.ok) throw new Error(`status ${res.status}`);
      await downloadBlob(url, filename);
    } catch {
      const result = await refreshMedia();
      if (result?.download_url) {
        await downloadBlob(result.download_url, filename);
      } else {
        toast("Download failed", "Couldn't refresh the download link. Try again shortly.");
      }
    }
  }

  const isProcessing = clip.status === "processing";
  const canEdit = jobDone && (clip.status === "done" || clip.status === "processing");

  async function onApprovalChange(value: ApprovalValue) {
    setApprovalLocal(value);
    const result = await updateClipApprovalAction(jobId, clip.id, value);
    if (result.status === "ok") {
      if (value === "approved") {
        toast("Clip approved", "Ready to publish, schedule, or save to Vault.");
      }
    } else {
      setApprovalLocal(approval);
      toast("Approval failed", result.message ?? "Could not update approval");
    }
  }

  async function copyLink() {
    if (!downloadUrl) return;
    await navigator.clipboard.writeText(downloadUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div
      className={cn(
        "group rounded-lg border border-border/60 bg-card overflow-hidden flex flex-col hover:border-border transition-colors",
        isProcessing && "ring-1 ring-sky-500/30",
      )}
    >
      {/* Vertical 9:16 video preview */}
      <div className="relative bg-black" style={{ aspectRatio: "9/16" }}>
        {playing && downloadUrl ? (
          <video
            src={downloadUrl}
            controls
            autoPlay
            className="absolute inset-0 w-full h-full"
            playsInline
            onError={onVideoError}
          />
        ) : (
          <>
            {thumbnailUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={thumbnailUrl}
                alt={clip.title || `Clip ${clip.rank + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
                onError={onThumbnailError}
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center text-muted-foreground/40 text-xs">
                No preview
              </div>
            )}
            {downloadUrl && !isProcessing && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => setPlaying(true)}
                    className="absolute inset-0 grid place-items-center bg-black/0 hover:bg-black/40 transition-colors"
                    aria-label="Play clip"
                  >
                    <div className="rounded-full bg-white/90 text-black p-3 opacity-90 group-hover:opacity-100 group-hover:scale-110 transition-all">
                      <Play className="h-6 w-6 fill-current" />
                    </div>
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  Play this clip in the browser with sound.
                </TooltipContent>
              </Tooltip>
            )}
          </>
        )}

        {isProcessing && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-black/60 backdrop-blur-sm">
            <Loader2 className="h-8 w-8 animate-spin text-sky-400" />
            <Badge className="border-sky-500/40 bg-sky-500/20 text-sky-100">
              Re-rendering
            </Badge>
          </div>
        )}

        {/* Score corner badge */}
        <div className="absolute top-2 left-2 flex items-center gap-1">
          <LegendLabel
            tip={CLIP_SCORE_LEGEND.rank}
            tipLabel="Rank help"
            className="text-[11px] font-mono font-medium px-1.5 py-0.5 rounded-sm bg-black/50 text-white border border-frame/20"
          >
            #{clip.rank + 1}
          </LegendLabel>
          <LegendLabel
            tip={CLIP_SCORE_LEGEND.ensemble}
            tipLabel="Ensemble score help"
            className="text-[11px] font-mono font-medium px-1.5 py-0.5 rounded-sm bg-black/50 text-white border border-frame/20"
          >
            {formatScore(clip.ensemble_score)}
          </LegendLabel>
        </div>

        <div className="absolute top-2 right-2">
          <LegendBadge
            className={cn(
              emotionColors[clip.emotion] ?? emotionColors.neutral,
              "bg-black/50",
            )}
            tip={legendForEmotion(clip.emotion)}
            tipLabel="Emotion help"
          >
            {clip.emotion}
          </LegendBadge>
        </div>

        <div className="absolute bottom-2 right-2">
          <LegendLabel
            tip={CLIP_SCORE_LEGEND.duration}
            tipLabel="Duration help"
            className="text-[11px] font-mono font-medium px-1.5 py-0.5 rounded-sm bg-black/50 text-white border border-frame/20"
          >
            {formatDuration(clip.duration_secs)}
          </LegendLabel>
        </div>
      </div>

      {/* Metadata footer */}
      <div className="p-3 space-y-2">
        <h3 className="text-sm font-medium line-clamp-1">
          {clip.title || `Clip ${clip.rank + 1}`}
        </h3>
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed h-8">
          {clip.hook || "—"}
        </p>

        {clip.publish_statuses && clip.publish_statuses.length > 0 && (
          <PublishStatusBadge statuses={clip.publish_statuses} />
        )}

        <div className="flex gap-2 pt-1">
          {downloadUrl && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1"
              tooltip="Download the rendered MP4 to your device."
              onClick={() => void onDownloadClick()}
            >
              <Download className="h-3.5 w-3.5" />
              Download
            </Button>
          )}
          {jobDone && clip.status === "done" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => setDestinationsOpen(true)}
              tooltip="Publish, schedule, or save to Clip Vault"
            >
              <Share2 className="h-3.5 w-3.5" />
              Destinations
            </Button>
          )}
          {downloadUrl && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={copyLink}
              aria-label="Copy download link"
            >
              <Link2 className="h-3.5 w-3.5" />
              {copied ? "Copied" : ""}
            </Button>
          )}
        </div>

        {canEdit && clip.status === "done" && (
          <ApprovalToggle
            value={approvalLocal}
            onChange={onApprovalChange}
            disabled={isProcessing}
          />
        )}

        <CollapsibleSection
          title="Scores & details"
          summary={`Ensemble ${formatScore(clip.ensemble_score)} · ${clip.emotion}`}
        >
          <div className="space-y-3">
            <SectionLegend
              title="Scores"
              tip="Signal breakdown for this clip. Virality is scored after creation."
              className="pt-0"
            />
            <ScoreBreakdown clip={clip} />
            {clip.overlays && clip.overlays.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {clip.overlays.map((ov) => (
                  <span
                    key={ov.id}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                    title={`${ov.matched_keyword} @ ${ov.trigger_time_secs.toFixed(1)}s`}
                  >
                    {ov.matched_keyword || "overlay"}
                  </span>
                ))}
              </div>
            )}
            {clip.llm_reason && (
              <p className="text-xs text-muted-foreground leading-snug">{clip.llm_reason}</p>
            )}
            {clip.transcript_text && (
              <div>
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => setShowTranscript((v) => !v)}
                >
                  {showTranscript ? "Hide transcript" : "Show transcript"}
                </button>
                {showTranscript && (
                  <p className="text-xs text-muted-foreground mt-1 max-h-32 overflow-y-auto leading-relaxed">
                    {clip.transcript_text}
                  </p>
                )}
              </div>
            )}
          </div>
        </CollapsibleSection>

        {canEdit && (
          <CollapsibleSection title="Edit clip" summary="Boundaries, captions, re-render">
            <div className="space-y-3">
              <ClipEditor
                clip={clip}
                jobId={jobId}
                sourceDurationSecs={sourceDurationSecs}
                captionStyleOptions={captionOptions}
                reframePresetOptions={reframeOptions}
                jobAspectRatio={jobAspectRatio}
                aspectRatioCatalog={aspectRatioCatalog}
                disabled={isProcessing}
              />
              {clip.status === "done" && (
                <>
                  <ClipFeedbackButtons clipId={clip.id} />
                  <RegenerateClipButton jobId={jobId} clipId={clip.id} />
                </>
              )}
            </div>
          </CollapsibleSection>
        )}

        {jobDone && clip.status === "error" && (
          <p className="text-[10px] text-destructive">
            {userFacingErrorMessage(clip.error_message, null, "Render failed")}
          </p>
        )}
      </div>

      <ClipDestinationsDrawer
        clip={{ ...clip, approval_status: approvalLocal }}
        jobId={jobId}
        open={destinationsOpen}
        onClose={() => setDestinationsOpen(false)}
      />
    </div>
  );
}

function ScoreBreakdown({ clip }: { clip: ClipOut }) {
  const scores: Array<{ label: string; value: number; tip: string }> = [
    {
      label: "Virality",
      value: clip.llm_score / 100,
      tip: CLIP_SCORE_LEGEND.virality,
    },
    {
      label: "Audio",
      value: clip.audio_score,
      tip: CLIP_SCORE_LEGEND.audio,
    },
    {
      label: "Novelty",
      value: clip.spectral_score,
      tip: CLIP_SCORE_LEGEND.novelty,
    },
    {
      label: "Motion",
      value: clip.flow_score,
      tip: CLIP_SCORE_LEGEND.motion,
    },
  ];
  if ((clip.chat_score ?? 0) > 0) {
    scores.push({
      label: "Chat",
      value: clip.chat_score ?? 0,
      tip: "Twitch chat spike intensity in this window.",
    });
  }

  return (
    <div className={cn("grid gap-1 pt-1", scores.length > 4 ? "grid-cols-5" : "grid-cols-4")}>
      {scores.map((s) => (
        <div key={s.label} className="flex flex-col items-center gap-0.5">
          <div className="h-1 w-full bg-secondary overflow-hidden">
            <div
              className="h-full bg-primary/70"
              style={{ width: `${Math.min(100, s.value * 100)}%` }}
            />
          </div>
          <LegendLabel
            tip={s.tip}
            tipLabel={`${s.label} score help`}
            className="text-[10px] text-muted-foreground font-mono"
          >
            {s.label}
          </LegendLabel>
        </div>
      ))}
    </div>
  );
}

export function ClipCardSkeleton() {
  return (
    <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
      <div className="skeleton" style={{ aspectRatio: "9/16" }} />
      <div className="p-3 space-y-2">
        <div className="h-4 w-2/3 skeleton rounded" />
        <div className="h-3 w-full skeleton rounded" />
      </div>
    </div>
  );
}
