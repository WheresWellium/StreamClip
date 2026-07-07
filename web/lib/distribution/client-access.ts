import { LICENSE_MACHINE_ID } from "@/lib/license-machine-id";
import { getClientAuth } from "@/lib/auth/client-session";

const PRO_TIERS = new Set(["pro", "admin"]);

export type DistributionSession =
  | { ok: true; token: string }
  | { ok: false; message: string };

/** Auth + Pro gate for client mutations (browser / static export). */
export async function requireDistributionClientSession(
  proMessage = "Pro license required.",
): Promise<DistributionSession> {
  const token = getClientAuth().token;
  if (!token) {
    return { ok: false, message: "Sign in required." };
  }
  const hasPro = await hasDistributionAccessClient(token);
  if (!hasPro) {
    return { ok: false, message: proMessage };
  }
  return { ok: true, token };
}

export async function hasDistributionAccessClient(
  token?: string,
): Promise<boolean> {
  const authToken = token ?? getClientAuth().token;

  // Try JWT/user-tier check first; skip safely when no token is present.
  if (authToken) {
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${authToken}` },
        cache: "no-store",
      });
      if (res.ok) {
        const user = (await res.json()) as { tier?: string };
        if (user.tier && PRO_TIERS.has(user.tier)) return true;
      }
    } catch {
      /* fall through to install-license check */
    }
  }

  try {
    const res = await fetch(
      `/api/license/status?machine_id=${encodeURIComponent(LICENSE_MACHINE_ID)}`,
      { cache: "no-store" },
    );
    if (res.ok) {
      const status = (await res.json()) as { active?: boolean; tier?: string };
      if (status.active && status.tier && PRO_TIERS.has(status.tier)) return true;
    }
  } catch {
    /* no pro access */
  }

  return false;
}

/** Aliases used by distribution action modules. */
export const requireDistributionSession = requireDistributionClientSession;
export const hasDistributionAccess = hasDistributionAccessClient;
