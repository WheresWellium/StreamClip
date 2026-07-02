"use client";

import { Merge } from "lucide-react";
import * as React from "react";

import { spliceClipsAction } from "@/app/actions/jobs";
import { Button } from "@/components/ui/button";
import type { ClipOut } from "@/lib/api/types";

type Props = {
  jobId: string;
  clips: ClipOut[];
  jobDone: boolean;
};

export function SpliceClipsToolbar({ jobId, clips, jobDone }: Props) {
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [transition, setTransition] = React.useState<"cut" | "crossfade">("cut");
  const [message, setMessage] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);

  const eligible = clips.filter(
    (c) => c.status === "done" && !("kind" in c && c.kind === "splice"),
  );

  if (!jobDone || eligible.length < 2) return null;

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleMerge() {
    if (selected.size < 2) return;
    setPending(true);
    const result = await spliceClipsAction(jobId, Array.from(selected), transition);
    setPending(false);
    setMessage(result.ok ? result.message ?? "Queued" : result.message ?? "Failed");
    if (result.ok) setSelected(new Set());
  }

  return (
    <div className="mb-4 rounded-md border border-border/60 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium flex items-center gap-2">
          <Merge className="h-4 w-4" />
          Merge clips
        </p>
        <div className="flex items-center gap-2">
          <select
            aria-label="Transition between clips"
            className="rounded-md border border-border/60 bg-background px-2 py-1 text-xs"
            value={transition}
            onChange={(e) => setTransition(e.target.value as "cut" | "crossfade")}
          >
            <option value="cut">Hard cut</option>
            <option value="crossfade">Crossfade</option>
          </select>
          <Button
            type="button"
            size="sm"
            disabled={selected.size < 2 || pending}
            onClick={handleMerge}
          >
            Merge selected ({selected.size})
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {eligible.map((c) => (
          <label
            key={c.id}
            className="text-xs flex items-center gap-1.5 px-2 py-1 rounded border border-border/60 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(c.id)}
              onChange={() => toggle(c.id)}
            />
            #{c.rank + 1}
          </label>
        ))}
      </div>
      {message && <p className="text-xs text-muted-foreground">{message}</p>}
    </div>
  );
}
