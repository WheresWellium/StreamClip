import { cookies } from "next/headers";

import { TokenRefreshProvider } from "@/components/providers/token-refresh";
import { ClaimDeviceModal } from "@/components/auth/claim-device-modal";
import { getAccessToken, getDeviceId } from "@/lib/auth/session";

export async function AuthExtras() {
  const token = await getAccessToken();
  const deviceId = await getDeviceId();
  const jar = await cookies();
  const showClaim = Boolean(token && deviceId && !jar.get("device_claimed")?.value);

  return showClaim && deviceId ? <ClaimDeviceModal deviceId={deviceId} /> : null;
}
