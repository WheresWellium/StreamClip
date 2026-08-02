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

export function failureReasonFor(
  spawnError: string | null,
  exitInfo: SidecarExitInfo | null,
): string {
  if (spawnError) return spawnError;
  if (exitInfo) {
    return `Local engine exited (code ${exitInfo.code ?? "unknown"}) before it finished starting.`;
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
