"use client";

import { Check, Download, Pencil, Share2, Trash2, X } from "lucide-react";
import * as React from "react";

import { PublishStatusBadge } from "@/components/clips/publish-status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import type { VaultClip } from "@/lib/api/client";
import { formatDuration } from "@/lib/utils/format";

type Props = {
  clips: VaultClip[];
  renamingId: string | null;
  renameValue: string;
  renamePending: boolean;
  onRenameValueChange: (value: string) => void;
  onStartRename: (clip: VaultClip) => void;
  onCancelRename: () => void;
  onSaveRename: (id: string) => void;
  onRemove: (id: string) => void;
  onShare: (clip: VaultClip) => void;
};

export function VaultClipGrid({
  clips,
  renamingId,
  renameValue,
  renamePending,
  onRenameValueChange,
  onStartRename,
  onCancelRename,
  onSaveRename,
  onRemove,
  onShare,
}: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {clips.map((clip) => (
        <div
          key={clip.id}
          className="rounded-lg border border-border/60 bg-card overflow-hidden flex flex-col"
        >
          <div className="relative bg-black" style={{ aspectRatio: "9/16" }}>
            {clip.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={clip.thumbnail_url}
                alt={clip.title}
                className="absolute inset-0 w-full h-full object-cover"
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center text-xs text-muted-foreground">
                {clip.status === "copying" ? "Copying…" : "No preview"}
              </div>
            )}
            <span className="absolute bottom-2 right-2 text-[10px] font-mono bg-black/70 px-1.5 py-0.5 rounded">
              {formatDuration(clip.duration_secs)}
            </span>
          </div>

          <div className="p-3 space-y-2 flex-1 flex flex-col">
            {renamingId === clip.id ? (
              <div className="flex items-center gap-1">
                <Input
                  className="h-7 text-xs"
                  value={renameValue}
                  maxLength={255}
                  autoFocus
                  onChange={(e) => onRenameValueChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSaveRename(clip.id);
                    if (e.key === "Escape") onCancelRename();
                  }}
                  aria-label="Clip title"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  disabled={renamePending || !renameValue.trim()}
                  onClick={() => onSaveRename(clip.id)}
                  aria-label="Save title"
                >
                  <Check className="h-3.5 w-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={onCancelRename}
                  aria-label="Cancel rename"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ) : (
              <div className="flex items-start gap-1">
                <p className="text-xs font-medium line-clamp-2 flex-1">
                  {clip.title || "Untitled"}
                </p>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground shrink-0"
                  onClick={() => onStartRename(clip)}
                  aria-label="Rename clip"
                >
                  <Pencil className="h-3 w-3" />
                </button>
              </div>
            )}
            <p className="text-[10px] text-muted-foreground capitalize">{clip.status}</p>
            {clip.publish_statuses && clip.publish_statuses.length > 0 && (
              <PublishStatusBadge statuses={clip.publish_statuses} />
            )}
            <div className="flex gap-2 mt-auto pt-2">
              {clip.status === "ready" && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => onShare(clip)}
                >
                  <Share2 className="h-3.5 w-3.5" />
                </Button>
              )}
              {clip.video_url && (
                <Button asChild variant="outline" size="sm" className="flex-1">
                  <a href={clip.video_url} download>
                    <Download className="h-3.5 w-3.5" />
                  </a>
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onRemove(clip.id)}
                aria-label="Remove from vault"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
