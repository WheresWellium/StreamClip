"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import * as React from "react";

import { submitClipFeedbackAction } from "@/app/actions/jobs";

type Props = { clipId: string };

export function ClipFeedbackButtons({ clipId }: Props) {
  const [msg, setMsg] = React.useState<string | null>(null);

  async function rate(rating: number) {
    setMsg(null);
    const result = await submitClipFeedbackAction(clipId, rating);
    setMsg(result.ok ? "Thanks!" : result.message ?? "Failed");
  }

  return (
    <div className="flex items-center gap-1 pt-1">
      <button
        type="button"
        className="p-1 rounded hover:bg-muted"
        aria-label="Thumbs up"
        onClick={() => rate(5)}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        className="p-1 rounded hover:bg-muted"
        aria-label="Thumbs down"
        onClick={() => rate(1)}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
      {msg && <span className="text-[10px] text-muted-foreground">{msg}</span>}
    </div>
  );
}
