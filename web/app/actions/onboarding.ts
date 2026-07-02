"use server";

import { devicesApi } from "@/lib/api/client";
import { getDeviceId } from "@/lib/auth/session";

/**
 * Marks onboarding complete server-side (the device id lives in an
 * httpOnly cookie the browser can't forward itself). The UI cookie is
 * still set client-side so navigation unblocks immediately.
 */
export async function completeOnboardingAction(): Promise<void> {
  const deviceId = await getDeviceId();
  if (!deviceId) return;
  try {
    await devicesApi.completeOnboarding(deviceId);
  } catch {
    // Non-fatal: the middleware cookie already unblocks the app.
  }
}
