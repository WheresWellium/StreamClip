"use client";

import Link from "next/link";

import { shouldShowHeuristicViralityBanner } from "@/components/clips/heuristic-virality";
import type { ClipOut } from "@/lib/api/types";
import { helpHref } from "@/lib/docs";
import { CLIP_SCORE_LEGEND } from "@/lib/help/legends";

/**
 * Shown when most clips on a job used local heuristic scoring (Ollama down).
 */
export function HeuristicViralityBanner({ clips }: { clips: ClipOut[] }) {
  if (!shouldShowHeuristicViralityBanner(clips)) return null;

  return (
    <div
      className="rounded-md border border-amber-500/35 bg-amber-500/10 px-3 py-2 text-sm text-amber-100/95"
      role="status"
      data-testid="heuristic-virality-banner"
    >
      <p className="font-medium">Scores are local heuristics (LLM unavailable)</p>
      <p className="mt-0.5 text-xs text-amber-100/75 leading-relaxed">
        {CLIP_SCORE_LEGEND.virality_source_heuristic} Start Ollama with your
        configured model for LLM virality ranks.{" "}
        <Link href={helpHref("/")} className="underline hover:text-amber-50">
          Help
        </Link>
      </p>
    </div>
  );
}
