/** Device ID helpers — 32-char hex to match DB `String(32)` columns. */

export function normalizeDeviceId(id: string): string {
  return id.replace(/-/g, "").slice(0, 32);
}

export function newDeviceId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}
