"use client";

import { Download, Link2, Play } from "lucide-react";
import * as React from "react";

import { RegenerateClipButton } from "@/components/clips/job-clips-toolbar";
import { Button } from "@/components/ui/button";
import { HelpTip } from "@/components/ui/help-tip";
import { LegendBadge, LegendLabel } from "@/components/ui/legend-badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ClipOut } from "@/lib/api/types";
import { CLIP_SCORE_LEGEND, legendForEmotion } from "@/lib/help/legends";
import {
  cn,
  emotionColors,
  formatDuration,
  formatScore,
} from "@/lib/utils/format";

interface ClipCardProps {
  clip: ClipOut;
  jobId: string;
  jobDone?: boolean;
}

export function ClipCard({ clip, jobId, jobDone = false }: ClipCardProps) {
  const [playing, setPlaying] = React.useState(false);
  const [showTranscript, setShowTranscript] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  async function copyLink() {
    if (!clip.download_url) return;
    await navigator.clipboard.writeText(clip.download_url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="group rounded-lg border border-border/60 bg-card overflow-hidden flex flex-col hover:border-border transition-colors">
      {/* Vertical 9:16 video preview */}
      <div className="relative bg-black" style={{ aspectRatio: "9/16" }}>
        {playing && clip.download_url ? (
          <video
            src={clip.download_url}
            controls
            autoPlay
            className="absolute inset-0 w-full h-full"
            playsInline
          />
        ) : (
          <>
            {clip.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={clip.thumbnail_url}
                alt={clip.title || `Clip ${clip.rank + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center text-muted-foreground/40 text-xs">
                No preview
              </div>
            )}
            {clip.download_url && (
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
                  Play this vertical clip in the browser with sound.
                </TooltipContent>
              </Tooltip>
            )}
          </>
        )}

        {/* Score corner badge */}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur inline-flex items-center gap-0.5">
            #{clip.rank + 1}
            <HelpTip
              content={CLIP_SCORE_LEGEND.rank}
              label="Rank help"
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5 text-white/80 hover:text-white"
            />
          </span>
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur inline-flex items-center gap-0.5">
            {formatScore(clip.ensemble_score)}
            <HelpTip
              content={CLIP_SCORE_LEGEND.ensemble}
              label="Ensemble score help"
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5 text-white/80 hover:text-white"
            />
          </span>
        </div>

        <div className="absolute top-2 right-2">
          <LegendBadge
            className={cn(
              emotionColors[clip.emotion] ?? emotionColors.neutral,
              "backdrop-blur shadow-sm",
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
            className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur"
          >
            {formatDuration(clip.duration_secs)}
          </LegendLabel>
        </div>
      </div>

      {/* Metadata footer */}
      <div className="p-3 space-y-2">
        <div className="flex items-center gap-1">
          <h3 className="text-sm font-medium line-clamp-1 flex-1">
            {clip.title || `Clip ${clip.rank + 1}`}
          </h3>
          <HelpTip content={CLIP_SCORE_LEGEND.title} label="Title help" />
        </div>
        <div className="flex items-start gap-1">
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed h-8 flex-1">
            {clip.hook || "—"}
          </p>
          <HelpTip content={CLIP_SCORE_LEGEND.hook} label="Hook help" />
        </div>

        <div className="flex items-center gap-1 pt-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
            Scores
          </span>
          <HelpTip
            content="Signal breakdown for this clip. Virality is scored after creation."
            label="Score section help"
          />
        </div>

        {/* Score breakdown */}
        <ScoreBreakdown clip={clip} />

        {clip.overlays && clip.overlays.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
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
          <p className="text-[10px] text-muted-foreground leading-snug line-clamp-2" title={clip.llm_reason}>
            {clip.llm_reason}
          </p>
        )}

        {clip.transcript_text && (
          <div>
            <button
              type="button"
              className="text-[10px] text-primary hover:underline"
              onClick={() => setShowTranscript((v) => !v)}
            >
              {showTranscript ? "Hide transcript" : "Show transcript"}
            </button>
            {showTranscript && (
              <p className="text-[10px] text-muted-foreground mt-1 max-h-24 overflow-y-auto leading-relaxed">
                {clip.transcript_text}
              </p>
            )}
          </div>
        )}

        <div className="flex gap-2">
          {clip.download_url && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="flex-1"
              tooltip="Download the rendered MP4 to your device."
            >
              <a href={clip.download_url} download>
                <Download className="h-3.5 w-3.5" />
                Download
              </a>
            </Button>
          )}
          {clip.download_url && (
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

        {jobDone && clip.status === "done" && (
          <RegenerateClipButton jobId={jobId} clipId={clip.id} />
        )}
      </div>
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
          <div className="h-1 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary/70"
              style={{ width: `${Math.min(100, s.value * 100)}%` }}
            />
          </div>
          <div className="flex items-center gap-0.5">
            <span className="text-[10px] text-muted-foreground font-mono">
              {s.label}
            </span>
            <HelpTip
              content={s.tip}
              label={`${s.label} score help`}
              className="h-3 w-3 [&_svg]:h-2.5 [&_svg]:w-2.5"
            />
          </div>
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
