const VAULT_SEEN_KEY = "streamclip:vault_seen";
const QUOTA_DISMISSED_KEY = "streamclip:quota_dismissed";

export function markVaultSeen(): void {
  try {
    localStorage.setItem(VAULT_SEEN_KEY, "1");
  } catch {
    // ignore private browsing / quota errors
  }
}

export function hasSeenVault(): boolean {
  try {
    return localStorage.getItem(VAULT_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissQuotaTooltip(): void {
  try {
    localStorage.setItem(QUOTA_DISMISSED_KEY, "1");
  } catch {
    // ignore
  }
}

export function hasDismissedQuotaTooltip(): boolean {
  try {
    return localStorage.getItem(QUOTA_DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}
