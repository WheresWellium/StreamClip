"use server";

import { ApiClientError, settingsApi, type WebhookSettings } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";

export type WebhookActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  settings?: WebhookSettings;
};

export async function getWebhookSettingsAction(): Promise<WebhookActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in to configure a webhook." };
  }
  try {
    const settings = await settingsApi.getWebhook(token);
    return { status: "ok", settings };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not load webhook settings." };
  }
}

export async function updateWebhookSettingsAction(
  webhookUrl: string | null,
  webhookSecret: string | null,
): Promise<WebhookActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in to configure a webhook." };
  }
  try {
    const settings = await settingsApi.updateWebhook(webhookUrl, webhookSecret, token);
    return { status: "ok", settings };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not save webhook settings." };
  }
}
