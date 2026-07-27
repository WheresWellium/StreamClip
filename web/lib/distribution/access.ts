import { getAccessToken } from "@/lib/auth/session";
import { LICENSE_MACHINE_ID } from "@/lib/license-machine-id";

const API_BASE = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const PRO_TIERS = new Set(["pro", "admin"]);

export type DistributionSession =
  | { ok: true; token: string }
  | { ok: false; message: string };

function hasPublisherCapability(status: {
  active?: boolean;
  tier?: string;
  capabilities?: string[];
}): boolean {
  if (!status.active) return false;
  if (status.capabilities?.includes("publisher")) return true;
  return Boolean(status.tier && PRO_TIERS.has(status.tier));
}

/** Auth + Pro gate for distribution server actions (matches backend `require_distribution_access`). */
export async function requireDistributionSession(
  proMessage = "Publisher license required.",
): Promise<DistributionSession> {
  const token = await getAccessToken();
  if (!token) {
    return { ok: false, message: "Sign in required." };
  }
  const hasPro = await hasDistributionAccess(token);
  if (!hasPro) {
    return { ok: false, message: proMessage };
  }
  return { ok: true, token };
}

/** Matches backend `require_distribution_access` — user Pro tier or install license. */
export async function hasDistributionAccess(token?: string): Promise<boolean> {
  const authToken = token ?? (await getAccessToken());
  if (!authToken) return false;

  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
      cache: "no-store",
    });
    if (res.ok) {
      const user = (await res.json()) as { tier?: string };
      if (user.tier && PRO_TIERS.has(user.tier)) return true;
    }
  } catch {
    /* try install license */
  }

  try {
    const res = await fetch(
      `${API_BASE}/api/license/status?machine_id=${encodeURIComponent(LICENSE_MACHINE_ID)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const status = (await res.json()) as {
        active?: boolean;
        tier?: string;
        capabilities?: string[];
      };
      if (hasPublisherCapability(status)) return true;
    }
  } catch {
    /* no pro access */
  }

  return false;
}
