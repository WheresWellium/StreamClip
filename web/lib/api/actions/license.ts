import {
  ApiClientError,
  licenseApi,
  type LicenseActivationsResult,
  type LicenseReleaseResult,
  type LicenseStatus,
} from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { LICENSE_MAX_SEATS_HINT } from "@/lib/license-seats";

export type LicenseActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  code?: string;
  license?: LicenseStatus;
};

export type LicenseSeatsActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  code?: string;
  seats?: LicenseActivationsResult;
  release?: LicenseReleaseResult;
};

/** Map backend license error codes to actionable copy. */
export function friendlyLicenseError(err: ApiClientError): string {
  switch (err.code) {
    case "invalid_license_key":
      return "That license key isn't valid. Check for typos — keys look like SCPRO-XXXX-XXXX-XXXX-XXXX.";
    case "license_revoked":
      return "This license key has been revoked. Contact support if you believe this is a mistake.";
    case "activation_limit_reached":
      return `This key is already active on ${LICENSE_MAX_SEATS_HINT} devices. Manage seats below to free one, then activate this device.`;
    case "http_404":
      return "That device seat is no longer active. Refresh the list and try again.";
    case "http_429":
      return "Too many attempts. Wait a minute and try again.";
    default:
      return err.message || "Activation failed. Try again.";
  }
}

export async function getLicenseStatusAction(
  machineId: string,
): Promise<LicenseActionState> {
  try {
    const license = await licenseApi.status(machineId, getClientAccessToken());
    return { status: "ok", license };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", code: err.code, message: err.message };
    }
    return { status: "error", message: "Could not load license status." };
  }
}

export async function activateLicenseAction(
  licenseKey: string,
  machineId: string,
): Promise<LicenseActionState> {
  try {
    const result = await licenseApi.activate(
      licenseKey.trim(),
      machineId,
      getClientAccessToken(),
    );
    return {
      status: "ok",
      license: {
        active: true,
        tier: result.tier,
        expires_at: result.expires_at,
        machine_id: machineId,
      },
    };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", code: err.code, message: friendlyLicenseError(err) };
    }
    return { status: "error", message: "Activation failed. Check your connection and try again." };
  }
}

export async function listLicenseSeatsAction(
  licenseKey: string,
  machineId: string,
): Promise<LicenseSeatsActionState> {
  try {
    const seats = await licenseApi.activations(
      licenseKey.trim(),
      machineId,
      getClientAccessToken(),
    );
    return { status: "ok", seats };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", code: err.code, message: friendlyLicenseError(err) };
    }
    return { status: "error", message: "Could not load device seats." };
  }
}

export async function releaseLicenseSeatAction(
  licenseKey: string,
  machineId: string,
  targetMachineId: string,
): Promise<LicenseSeatsActionState> {
  try {
    const release = await licenseApi.releaseActivation(
      licenseKey.trim(),
      machineId,
      targetMachineId,
      getClientAccessToken(),
    );
    const seats = await licenseApi.activations(
      licenseKey.trim(),
      machineId,
      getClientAccessToken(),
    );
    return { status: "ok", release, seats };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", code: err.code, message: friendlyLicenseError(err) };
    }
    return { status: "error", message: "Could not release that seat. Try again." };
  }
}
