"use client";

import { useEffect } from "react";

import { ensureClientDeviceId } from "@/lib/auth/client-session";

/** Ensures anonymous device identity exists before API calls. */
export function DeviceIdProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    ensureClientDeviceId();
  }, []);
  return <>{children}</>;
}
