import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/auth/session";

const API_BASE = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const COOKIE_OPTS = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
};

/**
 * BFF token refresh: the refresh token lives in an httpOnly cookie the
 * browser can't read, so this route exchanges it server-side and rotates
 * both cookies. Takes precedence over the /api/* proxy rewrite.
 */
export async function POST() {
  const jar = await cookies();
  const refreshToken = jar.get(REFRESH_TOKEN_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.json({ refreshed: false }, { status: 401 });
  }

  const res = await fetch(`${API_BASE}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });

  if (!res.ok) {
    // Refresh token expired or revoked — drop the stale session cookies.
    jar.delete(ACCESS_TOKEN_COOKIE);
    jar.delete(REFRESH_TOKEN_COOKIE);
    return NextResponse.json({ refreshed: false }, { status: 401 });
  }

  const data = await res.json();
  jar.set(ACCESS_TOKEN_COOKIE, data.access_token, { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 });
  jar.set(REFRESH_TOKEN_COOKIE, data.refresh_token, { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 * 30 });
  return NextResponse.json({ refreshed: true });
}
