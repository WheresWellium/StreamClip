/** Shared auth cookie / storage key names (server + client). */

import { normalizeDeviceId } from "@/lib/auth/device-id";

export const ACCESS_TOKEN_COOKIE = "streamclip_access_token";
export const REFRESH_TOKEN_COOKIE = "streamclip_refresh_token";
export const DEVICE_ID_COOKIE = "streamclip_device_id";
export const DEVICE_CLAIMED_KEY = "device_claimed";
export const ONBOARDING_COOKIE = "onboarding_complete";

export function authHeaders(token?: string, deviceId?: string): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (deviceId) headers["X-Device-Id"] = normalizeDeviceId(deviceId);
  return headers;
}
