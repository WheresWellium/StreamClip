"use client";

import { Loader2, RotateCcw } from "lucide-react";
import * as React from "react";

import { getClipWordsAction } from "@/lib/api/actions/jobs";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/form";
import type { ClipWord, TranscriptEdits } from "@/lib/api/types";
import { cn } from "@/lib/utils/format";

type Props = {
  jobId: string;
  clipId: string;
  edits: TranscriptEdits;
  onChange: (edits: TranscriptEdits) => void;
};

/**
 * Word-level caption editor. Click a word to correct the transcription;
 * clear the text to remove the word from captions. Edits are applied on
 * the next re-render without shifting word timing.
 */
export function TranscriptEditPanel({ jobId, clipId, edits, onChange }: Props) {
  const [words, setWords] = React.useState<ClipWord[] | null>(null);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [editingIndex, setEditingIndex] = React.useState<number | null>(null);
  const [draft, setDraft] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    getClipWordsAction(jobId, clipId).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if (result.ok) {
        setWords(result.words);
      } else {
        setLoadError(result.message);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [jobId, clipId]);

  function commitDraft(index: number) {
    const original = words?.[index]?.text ?? "";
    const next = { ...edits };
    const trimmed = draft.trim();
    if (trimmed === original) {
      delete next[String(index)];
    } else {
      next[String(index)] = trimmed; // "" removes the word
    }
    onChange(next);
    setEditingIndex(null);
  }

  function revertWord(index: number) {
    const next = { ...edits };
    delete next[String(index)];
    onChange(next);
    setEditingIndex(null);
  }

  const editCount = Object.keys(edits).length;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Loading transcript…
      </div>
    );
  }

  if (loadError) {
    return (
      <p className="text-xs text-muted-foreground py-2" role="alert">
        {loadError}
      </p>
    );
  }

  if (!words || words.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        No caption words in this clip window.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Click a word to correct it — clear the text to remove it.
        </p>
        {editCount > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => onChange({})}
          >
            <RotateCcw className="h-3 w-3" />
            Reset ({editCount})
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-1 rounded-md border border-border/60 bg-background/60 p-2 max-h-44 overflow-y-auto">
        {words.map((word) => {
          const edit = edits[String(word.index)];
          const isEdited = edit !== undefined;
          const isRemoved = isEdited && edit.trim() === "";
          const display = isEdited && !isRemoved ? edit : word.text;

          if (editingIndex === word.index) {
            return (
              <input
                key={word.index}
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => commitDraft(word.index)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitDraft(word.index);
                  if (e.key === "Escape") setEditingIndex(null);
                }}
                maxLength={80}
                className="h-6 rounded border border-sky-500/60 bg-background px-1 text-xs font-mono outline-none"
                style={{ width: `${Math.max(draft.length + 2, 6)}ch` }}
                aria-label={`Edit word ${word.index + 1}`}
              />
            );
          }

          return (
            <button
              key={word.index}
              type="button"
              onClick={() => {
                setDraft(isRemoved ? "" : display);
                setEditingIndex(word.index);
              }}
              onDoubleClick={() => revertWord(word.index)}
              title={
                isEdited
                  ? `Originally "${word.text}" — double-click to revert`
                  : `${word.start.toFixed(1)}s`
              }
              className={cn(
                "rounded px-1 py-0.5 text-xs transition-colors",
                isRemoved
                  ? "bg-destructive/10 text-destructive line-through"
                  : isEdited
                    ? "bg-sky-500/15 text-sky-700 dark:text-sky-300 font-medium"
                    : "hover:bg-muted text-foreground",
              )}
            >
              {isRemoved ? word.text : display}
            </button>
          );
        })}
      </div>

      <CaptionPreview words={words} edits={edits} />
    </div>
  );
}

/**
 * Lightweight CSS mockup of how the edited caption text will read on the
 * clip — grouped roughly like the renderer, no ffmpeg round-trip.
 */
function CaptionPreview({
  words,
  edits,
}: {
  words: ClipWord[];
  edits: TranscriptEdits;
}) {
  const effective = words
    .map((w) => {
      const edit = edits[String(w.index)];
      if (edit === undefined) return w.text;
      return edit.trim() === "" ? null : edit;
    })
    .filter((t): t is string => t !== null);

  const firstGroup = effective.slice(0, 3).join(" ").toUpperCase();
  if (!firstGroup) return null;

  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground uppercase tracking-wide">
        Caption preview
      </Label>
      <div className="relative rounded-md bg-black py-6 grid place-items-center overflow-hidden">
        <span
          className="px-3 text-center font-black text-white text-lg leading-tight"
          style={{
            textShadow:
              "-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 3px 6px rgba(0,0,0,.8)",
          }}
        >
          {firstGroup}
        </span>
      </div>
    </div>
  );
}
