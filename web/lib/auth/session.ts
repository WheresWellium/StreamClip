import { cookies } from "next/headers";

import { normalizeDeviceId } from "@/lib/auth/device-id";
import {
  ACCESS_TOKEN_COOKIE,
  DEVICE_ID_COOKIE,
  REFRESH_TOKEN_COOKIE,
  authHeaders,
} from "@/lib/auth/credentials";

export {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  DEVICE_ID_COOKIE,
  authHeaders,
} from "@/lib/auth/credentials";

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
