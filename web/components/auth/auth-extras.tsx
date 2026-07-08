"use client";

import { useEffect, useState } from "react";

import { ClaimDeviceModal } from "@/components/auth/claim-device-modal";
import {
  ensureClientDeviceId,
  getClientAccessToken,
  isDeviceClaimed,
} from "@/lib/auth/client-session";

function shouldOfferClaim(): boolean {
  const token = getClientAccessToken();
  const id = ensureClientDeviceId();
  return Boolean(token && id && !isDeviceClaimed());
}

export function AuthExtras() {
  const [showClaim, setShowClaim] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      const id = ensureClientDeviceId();
      setDeviceId(id);
      setShowClaim(shouldOfferClaim());
    };
    sync();
    window.addEventListener("auth-changed", sync);
    return () => window.removeEventListener("auth-changed", sync);
  }, []);

  if (!showClaim || !deviceId) return null;
  return <ClaimDeviceModal deviceId={deviceId} />;
}
