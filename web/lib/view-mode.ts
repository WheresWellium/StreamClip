export type ViewMode = "list" | "card";

export const JOBS_VIEW_STORAGE_KEY = "streamclip.jobs.view";
export const VAULT_VIEW_STORAGE_KEY = "streamclip.vault.view";

export function readViewMode(key: string, fallback: ViewMode = "list"): ViewMode {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(key);
  return raw === "card" || raw === "list" ? raw : fallback;
}

export function writeViewMode(key: string, mode: ViewMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, mode);
}
