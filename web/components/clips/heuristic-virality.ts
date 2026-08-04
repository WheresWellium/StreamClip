import type { ClipOut } from "@/lib/api/types";

/** True when a clip's virality rank came from the local heuristic fallback. */
export function isHeuristicVirality(clip: ClipOut): boolean {
  if (clip.virality_source === "heuristic") return true;
  const reason = (clip.llm_reason || "").trim();
  return reason.startsWith("Heuristic");
}

/**
 * Show the job-level banner when a majority of clips used heuristic scoring
 * (typical when Ollama is down on desktop).
 */
export function shouldShowHeuristicViralityBanner(clips: ClipOut[]): boolean {
  if (clips.length === 0) return false;
  const heuristicCount = clips.filter(isHeuristicVirality).length;
  return heuristicCount >= Math.ceil(clips.length / 2);
}
