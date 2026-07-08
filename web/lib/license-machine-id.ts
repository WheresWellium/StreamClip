import {
  ensureClientDeviceId,
  getClientDeviceId,
} from "@/lib/auth/client-session";

/** SSR / server-action fallback when no browser storage is available. */
export const LICENSE_MACHINE_ID_SSR = "streamclip-local-dev";

/**
 * Stable machine id for license activation (min 8 chars).
 * Reuses the same device id as anonymous job tracking so one browser = one seat.
 */
export function getLicenseMachineId(): string {
  if (typeof window === "undefined") {
    return LICENSE_MACHINE_ID_SSR;
  }
  return ensureClientDeviceId();
}

/** Client-only; undefined during SSR. */
export function getLicenseMachineIdOptional(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  return getClientDeviceId();
}

/** @deprecated Use getLicenseMachineId() in client components. */
export const LICENSE_MACHINE_ID = LICENSE_MACHINE_ID_SSR;
