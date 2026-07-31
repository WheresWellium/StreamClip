"use client";

import { useEffect, useState } from "react";

import { ClaimDeviceModal } from "@/components/auth/claim-device-modal";
import { ensureClientDeviceId } from "@/lib/auth/client-session";

/** Fire this to open the "Link local jobs" modal (e.g. from Settings). */
export const OPEN_CLAIM_EVENT = "qclip:open-claim";

export function AuthExtras() {
  const [showClaim, setShowClaim] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  useEffect(() => {
    // Never auto-open on load — linking jobs is opt-in via Settings, not a
    // modal that ambushes the user the moment the app starts.
    const open = () => {
      setDeviceId(ensureClientDeviceId());
      setShowClaim(true);
    };
    window.addEventListener(OPEN_CLAIM_EVENT, open);
    return () => window.removeEventListener(OPEN_CLAIM_EVENT, open);
  }, []);

  if (!showClaim || !deviceId) return null;
  return <ClaimDeviceModal deviceId={deviceId} onClose={() => setShowClaim(false)} />;
}
