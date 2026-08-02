/**
 * Pure decision logic for the sidecar startup-error page (taxonomy F4).
 *
 * Extracted from main.ts so it is unit-testable without an Electron runtime.
 * Given what the supervisor observed about the sidecar process, produce the
 * human-readable reason shown on startup-error.html. The invariant this guards:
 * a crashed/failed sidecar must always yield a legible message (never an empty
 * string, never a blank window).
 */
export interface SidecarExitInfo {
  code: number | null;
  signal: string | null;
}

/**
 * Prefer an actionable FATAL line from the engine log (writable-path, migrate)
 * over a bare exit code so the error page is useful without opening the log.
 */
export function failureReasonFor(
  spawnError: string | null,
  exitInfo: SidecarExitInfo | null,
  fatalFromLog: string | null = null,
): string {
  if (spawnError) return spawnError;
  const fatal = fatalFromLog?.trim();
  if (fatal) {
    return fatal.replace(/^FATAL:\s*/i, "").trim();
  }
  if (exitInfo) {
    return `Local engine exited (code ${exitInfo.code ?? "unknown"}) before it finished starting. Open the engine log for details.`;
  }
  return "Local engine did not respond in time.";
}

/**
 * True when the supervisor has enough evidence that the engine died and cannot
 * recover on its own — the signal main.ts uses to stop waiting and show the
 * error page rather than spinning until the boot timeout.
 */
export function shouldShowErrorPage(
  procAlive: boolean,
  spawnError: string | null,
  exitInfo: SidecarExitInfo | null,
): boolean {
  return !procAlive && (spawnError !== null || exitInfo !== null);
}

/** Pull the last FATAL line from a sidecar log body (newest match wins). */
export function extractFatalFromLog(logText: string | null | undefined): string | null {
  if (!logText) return null;
  const matches = logText.match(/^.*FATAL:.*$/gim);
  if (!matches || matches.length === 0) return null;
  return matches[matches.length - 1].trim();
}
