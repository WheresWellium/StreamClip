import { cookies } from "next/headers";

export const ACCESS_TOKEN_COOKIE = "streamclip_access_token";

export async function getAccessToken(): Promise<string | undefined> {
  const jar = await cookies();
  return jar.get(ACCESS_TOKEN_COOKIE)?.value;
}
