"use client";

import { useEffect, useState } from "react";

import { ClaimDeviceModal } from "@/components/auth/claim-device-modal";
import {
  ensureClientDeviceId,
  getClientAccessToken,
  isDeviceClaimed,
} from "@/lib/auth/client-session";

export function AuthExtras() {
  const [showClaim, setShowClaim] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  useEffect(() => {
    const id = ensureClientDeviceId();
    setDeviceId(id);
    const token = getClientAccessToken();
    setShowClaim(Boolean(token && id && !isDeviceClaimed()));
  }, []);

  if (!showClaim || !deviceId) return null;
  return <ClaimDeviceModal deviceId={deviceId} />;
}
