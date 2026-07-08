/**
 * Client-side session storage for static export / desktop UI.
 *
 * Tokens live in localStorage (remember me) or sessionStorage (browser session);
 * access token and device id are mirrored to same-site cookies so EventSource
 * (SSE) can authenticate without headers.
 */

import { newDeviceId, normalizeDeviceId } from "@/lib/auth/device-id";
import {
  ACCESS_TOKEN_COOKIE,
  DEVICE_CLAIMED_KEY,
  DEVICE_ID_COOKIE,
  ONBOARDING_COOKIE,
  REFRESH_TOKEN_COOKIE,
} from "@/lib/auth/credentials";

const LS_ACCESS = "streamclip_access_token";
const LS_REFRESH = "streamclip_refresh_token";
const LS_DEVICE = "streamclip_device_id";
const LS_REMEMBER = "streamclip_remember_me";

export type ClientAuth = {
  token?: string;
  refreshToken?: string;
  deviceId?: string;
};

export type SetAuthTokensOptions = {
  rememberMe?: boolean;
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function readCookie(name: string): string | undefined {
  if (!isBrowser()) return undefined;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : undefined;
}

function writeCookie(name: string, value: string, maxAgeSecs: number): void {
  if (!isBrowser()) return;
  const secure = window.location.protocol === "https:" ? "; secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSecs}; samesite=lax${secure}`;
}

function writeSessionCookie(name: string, value: string): void {
  if (!isBrowser()) return;
  const secure = window.location.protocol === "https:" ? "; secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; samesite=lax${secure}`;
}

function deleteCookie(name: string): void {
  if (!isBrowser()) return;
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

function tokenStorage(rememberMe: boolean): Storage | null {
  if (!isBrowser()) return null;
  return rememberMe ? localStorage : sessionStorage;
}

function readStoredToken(key: string): string | undefined {
  if (!isBrowser()) return undefined;
  return (
    localStorage.getItem(key) ??
    sessionStorage.getItem(key) ??
    undefined
  );
}

export function getRememberMe(): boolean {
  if (!isBrowser()) return true;
  const flag = localStorage.getItem(LS_REMEMBER);
  if (flag === "0") return false;
  if (flag === "1") return true;
  // Legacy sessions: tokens in sessionStorage imply no remember-me.
  if (sessionStorage.getItem(LS_REFRESH) && !localStorage.getItem(LS_REFRESH)) {
    return false;
  }
  return true;
}

export function getClientAuth(): ClientAuth {
  if (!isBrowser()) return {};
  const token =
    readStoredToken(LS_ACCESS) ?? readCookie(ACCESS_TOKEN_COOKIE) ?? undefined;
  const refreshToken =
    readStoredToken(LS_REFRESH) ??
    readCookie(REFRESH_TOKEN_COOKIE) ??
    undefined;
  const rawDevice =
    localStorage.getItem(LS_DEVICE) ?? readCookie(DEVICE_ID_COOKIE) ?? undefined;
  return {
    token: token || undefined,
    refreshToken: refreshToken || undefined,
    deviceId: rawDevice ? normalizeDeviceId(rawDevice) : undefined,
  };
}

export function getClientAccessToken(): string | undefined {
  return getClientAuth().token;
}

export function getClientRefreshToken(): string | undefined {
  return getClientAuth().refreshToken;
}

export function getClientDeviceId(): string | undefined {
  return getClientAuth().deviceId;
}

export function ensureClientDeviceId(): string {
  const existing = getClientDeviceId();
  if (existing) return existing;
  const id = newDeviceId();
  setClientDeviceId(id);
  return normalizeDeviceId(id);
}

export function setClientDeviceId(deviceId: string): void {
  const normalized = normalizeDeviceId(deviceId);
  localStorage.setItem(LS_DEVICE, normalized);
  writeCookie(DEVICE_ID_COOKIE, normalized, 60 * 60 * 24 * 365 * 5);
}

export function setAuthTokens(
  accessToken: string,
  refreshToken: string,
  options?: SetAuthTokensOptions,
): void {
  const rememberMe = options?.rememberMe ?? getRememberMe();
  const store = tokenStorage(rememberMe);
  if (!store) return;

  localStorage.setItem(LS_REMEMBER, rememberMe ? "1" : "0");
  localStorage.removeItem(LS_ACCESS);
  localStorage.removeItem(LS_REFRESH);
  sessionStorage.removeItem(LS_ACCESS);
  sessionStorage.removeItem(LS_REFRESH);

  store.setItem(LS_ACCESS, accessToken);
  store.setItem(LS_REFRESH, refreshToken);

  if (rememberMe) {
    writeCookie(ACCESS_TOKEN_COOKIE, accessToken, 60 * 60 * 24);
    writeCookie(REFRESH_TOKEN_COOKIE, refreshToken, 60 * 60 * 24 * 30);
  } else {
    writeSessionCookie(ACCESS_TOKEN_COOKIE, accessToken);
    writeSessionCookie(REFRESH_TOKEN_COOKIE, refreshToken);
  }
  window.dispatchEvent(new Event("auth-changed"));
}

export function clearAuthTokens(): void {
  localStorage.removeItem(LS_ACCESS);
  localStorage.removeItem(LS_REFRESH);
  localStorage.removeItem(LS_REMEMBER);
  sessionStorage.removeItem(LS_ACCESS);
  sessionStorage.removeItem(LS_REFRESH);
  deleteCookie(ACCESS_TOKEN_COOKIE);
  deleteCookie(REFRESH_TOKEN_COOKIE);
  window.dispatchEvent(new Event("auth-changed"));
}

export function isClientAuthenticated(): boolean {
  return Boolean(getClientAccessToken());
}

export function isDeviceClaimed(): boolean {
  if (!isBrowser()) return false;
  return localStorage.getItem(DEVICE_CLAIMED_KEY) === "1";
}

export function markDeviceClaimed(): void {
  if (!isBrowser()) return;
  localStorage.setItem(DEVICE_CLAIMED_KEY, "1");
}

export function markOnboardingComplete(): void {
  if (!isBrowser()) return;
  writeCookie(ONBOARDING_COOKIE, "1", 60 * 60 * 24 * 365 * 5);
  localStorage.setItem(ONBOARDING_COOKIE, "1");
}
