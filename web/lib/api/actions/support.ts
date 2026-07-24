import { ApiClientError, settingsApi, supportApi } from "@/lib/api/client";
import {
  ensureClientDeviceId,
  getClientAccessToken,
} from "@/lib/auth/client-session";

export type BugReportInput = {
  message: string;
  categories: string[];
  severity: "low" | "medium" | "high" | "critical";
  jobId?: string | null;
  environment?: Record<string, string>;
};

export async function submitBugReportAction(
  input: BugReportInput,
): Promise<{
  ok: boolean;
  message?: string;
  emailNotification?: string;
  opsNotification?: string;
}> {
  if (input.message.trim().length < 10) {
    return { ok: false, message: "Please describe the issue (at least 10 characters)." };
  }
  if (input.categories.length === 0) {
    return { ok: false, message: "Pick at least one category." };
  }
  try {
    const token = getClientAccessToken();
    const deviceId = ensureClientDeviceId();
    const result = await supportApi.submitBugReport(
      {
        message: input.message.trim(),
        categories: input.categories,
        severity: input.severity,
        job_id: input.jobId ?? null,
        environment: input.environment ?? null,
      },
      token,
      deviceId,
    );
    return {
      ok: true,
      emailNotification: result.email_notification,
      opsNotification: result.ops_notification,
    };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not submit the bug report." };
  }
}

export type BetaFeedbackInput = {
  message: string;
  topic: "question" | "idea" | "help" | "other";
  environment?: Record<string, string>;
};

export async function submitBetaFeedbackAction(
  input: BetaFeedbackInput,
): Promise<{ ok: boolean; message?: string; opsNotification?: string }> {
  if (input.message.trim().length < 10) {
    return { ok: false, message: "Please write at least 10 characters." };
  }
  try {
    const token = getClientAccessToken();
    const deviceId = ensureClientDeviceId();
    const result = await supportApi.submitBetaFeedback(
      {
        message: input.message.trim(),
        topic: input.topic,
        environment: input.environment ?? null,
      },
      token,
      deviceId,
    );
    return { ok: true, opsNotification: result.ops_notification };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not send feedback." };
  }
}

export async function updatePrivacyOptInAction(
  optIn: boolean,
): Promise<{ ok: boolean; optIn?: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    if (!token) {
      return { ok: false, message: "Sign in to change privacy settings." };
    }
    const result = await settingsApi.updatePrivacy(optIn, token);
    return { ok: true, optIn: result.data_contribution_opt_in };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not update privacy settings." };
  }
}

export async function updateMemoryPreferencesAction(
  memoryEnabled: boolean,
): Promise<{ ok: boolean; memoryEnabled?: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    if (!token) {
      return { ok: false, message: "Sign in to change preferences." };
    }
    const result = await settingsApi.updatePreferences({ memory_enabled: memoryEnabled }, token);
    return { ok: true, memoryEnabled: result.memory_enabled };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not update preferences." };
  }
}

export async function wipeUserPreferencesAction(): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    if (!token) {
      return { ok: false, message: "Sign in to wipe preferences." };
    }
    await settingsApi.wipePreferences(token);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not wipe preferences." };
  }
}
