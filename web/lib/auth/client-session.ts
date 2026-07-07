/**
 * Client-side session storage for static export / desktop UI.
 *
 * Tokens live in localStorage; access token and device id are mirrored to
 * same-site cookies so EventSource (SSE) can authenticate without headers.
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

export type ClientAuth = {
  token?: string;
  refreshToken?: string;
  deviceId?: string;
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

function deleteCookie(name: string): void {
  if (!isBrowser()) return;
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

export function getClientAuth(): ClientAuth {
  if (!isBrowser()) return {};
  const token =
    localStorage.getItem(LS_ACCESS) ?? readCookie(ACCESS_TOKEN_COOKIE) ?? undefined;
  const refreshToken =
    localStorage.getItem(LS_REFRESH) ??
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

export function setAuthTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(LS_ACCESS, accessToken);
  localStorage.setItem(LS_REFRESH, refreshToken);
  writeCookie(ACCESS_TOKEN_COOKIE, accessToken, 60 * 60 * 24);
  writeCookie(REFRESH_TOKEN_COOKIE, refreshToken, 60 * 60 * 24 * 30);
  window.dispatchEvent(new Event("auth-changed"));
}

export function clearAuthTokens(): void {
  localStorage.removeItem(LS_ACCESS);
  localStorage.removeItem(LS_REFRESH);
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
