import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { newDeviceId, normalizeDeviceId } from "@/lib/auth/device-id";

const DEVICE_COOKIE = "streamclip_device_id";
const ONBOARDING_COOKIE = "onboarding_complete";

const PUBLIC_PATHS = [
  "/onboarding",
  "/login",
  "/register",
  "/api/",
];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p),
  );
}

function setDeviceCookie(response: NextResponse, deviceId: string) {
  response.cookies.set(DEVICE_COOKIE, deviceId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365 * 5,
  });
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const response = NextResponse.next();

  const rawDeviceId = request.cookies.get(DEVICE_COOKIE)?.value;
  let deviceId = rawDeviceId ? normalizeDeviceId(rawDeviceId) : newDeviceId();

  if (!rawDeviceId || rawDeviceId !== deviceId) {
    setDeviceCookie(response, deviceId);
  }

  const onboardingDone =
    request.cookies.get(ONBOARDING_COOKIE)?.value === "1" ||
    request.cookies.get(ONBOARDING_COOKIE)?.value === "true";

  if (
    !onboardingDone &&
    !isPublicPath(pathname) &&
    !pathname.startsWith("/_next") &&
    !pathname.includes(".")
  ) {
    const url = request.nextUrl.clone();
    url.pathname = "/onboarding";
    const redirect = NextResponse.redirect(url);
    setDeviceCookie(redirect, deviceId);
    return redirect;
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
