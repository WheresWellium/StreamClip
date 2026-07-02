/**
 * Format elapsed/ETA seconds as compact human-readable durations (e.g. "2m 14s").
 */

export function formatDurationSeconds(
  secs: number | null | undefined,
): string {
  if (secs == null || !Number.isFinite(secs) || secs < 0) return "—";
  const total = Math.floor(secs);
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** "~3m remaining" — returns null when ETA is unknown or non-positive. */
export function formatEtaRemaining(
  secs: number | null | undefined,
  options?: { lowConfidence?: boolean },
): string | null {
  if (secs == null || !Number.isFinite(secs) || secs <= 0) return null;
  const total = Math.floor(secs);
  if (options?.lowConfidence) {
    const low = Math.max(1, Math.floor(total * 0.75));
    const high = Math.max(low + 1, Math.ceil(total * 1.25));
    return `~${formatDurationSeconds(low)}–${formatDurationSeconds(high)} remaining`;
  }
  return `~${formatDurationSeconds(total)} remaining`;
}

/** Alias used by live-progress and job UI. */
export const formatElapsedSeconds = formatDurationSeconds;

/** "~3m remaining" as a display string (empty when unknown). */
export function formatEtaSeconds(
  secs: number | null | undefined,
  options?: { lowConfidence?: boolean },
): string {
  return formatEtaRemaining(secs, options) ?? "";
}

/** Parse ingest sub-progress from SSE message (URL download or upload copy). */
export function parseIngestSubProgress(message: string): number | null {
  const match = message.match(/(?:Downloading|Copying upload)\s+(\d+)%/i);
  if (!match) return null;
  const pct = Number.parseInt(match[1], 10);
  if (!Number.isFinite(pct) || pct < 0 || pct > 100) return null;
  return pct;
}
