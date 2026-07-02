import { cookies } from "next/headers";

import { normalizeDeviceId } from "@/lib/auth/device-id";

export const ACCESS_TOKEN_COOKIE = "streamclip_access_token";
export const REFRESH_TOKEN_COOKIE = "streamclip_refresh_token";
export const DEVICE_ID_COOKIE = "streamclip_device_id";

export async function getAccessToken(): Promise<string | undefined> {
  const jar = await cookies();
  return jar.get(ACCESS_TOKEN_COOKIE)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  const jar = await cookies();
  return jar.get(REFRESH_TOKEN_COOKIE)?.value;
}

export async function getDeviceId(): Promise<string | undefined> {
  const jar = await cookies();
  const raw = jar.get(DEVICE_ID_COOKIE)?.value;
  return raw ? normalizeDeviceId(raw) : undefined;
}

export function authHeaders(token?: string, deviceId?: string): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (deviceId) headers["X-Device-Id"] = normalizeDeviceId(deviceId);
  return headers;
}
