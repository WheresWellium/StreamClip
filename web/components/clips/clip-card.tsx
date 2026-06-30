"use client";

import { Download, Play } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/form";
import type { Clip } from "@/lib/api/types";
import {
  cn,
  emotionColors,
  formatDuration,
  formatScore,
} from "@/lib/utils/format";

interface ClipCardProps {
  clip: Clip;
}

export function ClipCard({ clip }: ClipCardProps) {
  const [playing, setPlaying] = React.useState(false);

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
            )}
          </>
        )}

        {/* Score corner badge */}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur">
            #{clip.rank + 1}
          </span>
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur">
            {formatScore(clip.ensemble_score)}
          </span>
        </div>

        <div className="absolute top-2 right-2">
          <Badge
            className={cn(
              emotionColors[clip.emotion] ?? emotionColors.neutral,
              "backdrop-blur shadow-sm",
            )}
          >
            {clip.emotion}
          </Badge>
        </div>

        <div className="absolute bottom-2 right-2">
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-black/70 text-white backdrop-blur">
            {formatDuration(clip.duration_secs)}
          </span>
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

        {/* Score breakdown */}
        <ScoreBreakdown clip={clip} />

        {clip.download_url && (
          <Button asChild variant="outline" size="sm" className="w-full mt-2">
            <a href={clip.download_url} download>
              <Download className="h-3.5 w-3.5" />
              Download
            </a>
          </Button>
        )}
      </div>
    </div>
  );
}

function ScoreBreakdown({ clip }: { clip: Clip }) {
  const scores = [
    { label: "LLM", value: clip.llm_score / 100 },
    { label: "Audio", value: clip.audio_score },
    { label: "Novelty", value: clip.spectral_score },
    { label: "Motion", value: clip.flow_score },
  ];

  return (
    <div className="grid grid-cols-4 gap-1 pt-1">
      {scores.map((s) => (
        <div key={s.label} className="flex flex-col items-center gap-0.5">
          <div className="h-1 w-full bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary/70"
              style={{ width: `${Math.min(100, s.value * 100)}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground font-mono">
            {s.label}
          </span>
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
