"use client";

import { Check, Download, Pencil, Share2, Trash2, X } from "lucide-react";

import { PublishStatusBadge } from "@/components/clips/publish-status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import type { VaultClip } from "@/lib/api/client";
import { formatDuration } from "@/lib/utils/format";

type Props = {
  clip: VaultClip;
  renaming: boolean;
  renameValue: string;
  renamePending: boolean;
  onRenameValueChange: (value: string) => void;
  onStartRename: () => void;
  onCancelRename: () => void;
  onSaveRename: () => void;
  onRemove: () => void;
  onShare: () => void;
};

export function VaultClipListRow({
  clip,
  renaming,
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
    <div className="flex items-center gap-4 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-frame/5 transition-colors">
      <div
        className="relative shrink-0 w-14 h-[74px] rounded bg-black overflow-hidden"
        style={{ aspectRatio: "9/16" }}
      >
        {clip.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={clip.thumbnail_url}
            alt={clip.title}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 grid place-items-center text-[10px] text-muted-foreground">
            {clip.status === "copying" ? "…" : "—"}
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        {renaming ? (
          <div className="flex items-center gap-1">
            <Input
              className="h-8 text-sm"
              value={renameValue}
              maxLength={255}
              autoFocus
              onChange={(e) => onRenameValueChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSaveRename();
                if (e.key === "Escape") onCancelRename();
              }}
              aria-label="Clip title"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              disabled={renamePending || !renameValue.trim()}
              onClick={onSaveRename}
              aria-label="Save title"
            >
              <Check className="h-3.5 w-3.5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={onCancelRename}
              aria-label="Cancel rename"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <div className="flex items-start gap-1">
            <p className="text-sm font-medium truncate flex-1">{clip.title || "Untitled"}</p>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground shrink-0"
              onClick={onStartRename}
              aria-label="Rename clip"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
          <span className="font-mono">{formatDuration(clip.duration_secs)}</span>
          <span aria-hidden>·</span>
          <span className="capitalize">{clip.status}</span>
          {clip.publish_statuses && clip.publish_statuses.length > 0 ? (
            <PublishStatusBadge statuses={clip.publish_statuses} />
          ) : null}
        </div>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {clip.status === "ready" && (
          <Button type="button" variant="outline" size="sm" onClick={onShare}>
            <Share2 className="h-3.5 w-3.5" />
          </Button>
        )}
        {clip.video_url && (
          <Button asChild variant="outline" size="sm">
            <a href={clip.video_url} download>
              <Download className="h-3.5 w-3.5" />
            </a>
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRemove}
          aria-label="Remove from vault"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
