"use client";

import { Pencil, Check, X } from "lucide-react";
import * as React from "react";
import { useRouter } from "next/navigation";

import { updateJobTitleAction } from "@/lib/api/actions/jobs";
import { getEffectiveJobTitle } from "@/lib/jobs/title";
import { cn } from "@/lib/utils/format";

type Props = {
  jobId: string;
  displayTitle?: string | null;
  sourceTitle?: string | null;
  /** Larger typography on job detail header */
  variant?: "row" | "header";
};

export function EditableJobTitle({
  jobId,
  displayTitle,
  sourceTitle,
  variant = "row",
}: Props) {
  const router = useRouter();
  const [editing, setEditing] = React.useState(false);
  const [value, setValue] = React.useState(displayTitle ?? "");
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const effective = getEffectiveJobTitle({
    display_title: displayTitle,
    source_title: sourceTitle,
  });

  React.useEffect(() => {
    if (editing) {
      setValue(displayTitle ?? "");
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing, displayTitle]);

  async function save() {
    setSaving(true);
    setError(null);
    const trimmed = value.trim();
    const result = await updateJobTitleAction(jobId, trimmed || null);
    setSaving(false);
    if (!result.ok) {
      setError(result.message ?? "Could not save title");
      return;
    }
    setEditing(false);
    router.refresh();
  }

  function cancel() {
    setEditing(false);
    setError(null);
    setValue(displayTitle ?? "");
  }

  if (editing) {
    return (
      <div
        className="flex items-center gap-1 min-w-0 flex-1"
        onClick={(e) => e.preventDefault()}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          maxLength={512}
          disabled={saving}
          className={cn(
            "min-w-0 flex-1 rounded border border-frame/30 bg-background px-2 py-0.5",
            variant === "header" ? "text-2xl font-semibold" : "text-sm font-medium",
          )}
          onKeyDown={(e) => {
            if (e.key === "Enter") void save();
            if (e.key === "Escape") cancel();
          }}
        />
        <button
          type="button"
          aria-label="Save title"
          disabled={saving}
          className="shrink-0 p-1 text-sky-400 hover:text-sky-300"
          onClick={() => void save()}
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          type="button"
          aria-label="Cancel edit"
          disabled={saving}
          className="shrink-0 p-1 text-muted-foreground hover:text-foreground"
          onClick={cancel}
        >
          <X className="h-4 w-4" />
        </button>
        {error ? (
          <span className="text-xs text-destructive truncate">{error}</span>
        ) : null}
      </div>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 min-w-0 group/title">
      <span
        className={cn(
          "truncate",
          variant === "header" ? "text-2xl font-semibold tracking-tight" : "text-sm font-medium",
        )}
      >
        {effective}
      </span>
      <button
        type="button"
        aria-label="Edit job title"
        className={cn(
          "shrink-0 p-0.5 text-muted-foreground opacity-0 group-hover/title:opacity-100",
          "hover:text-foreground transition-opacity",
        )}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setEditing(true);
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    </span>
  );
}
