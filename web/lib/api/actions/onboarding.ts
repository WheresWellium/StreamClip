import { devicesApi } from "@/lib/api/client";
import { ensureClientDeviceId } from "@/lib/auth/client-session";

export async function completeOnboardingAction(): Promise<void> {
  const deviceId = ensureClientDeviceId();
  if (!deviceId) return;
  try {
    await devicesApi.completeOnboarding(deviceId);
  } catch {
    // Non-fatal: the onboarding cookie already unblocks the app.
  }
}
