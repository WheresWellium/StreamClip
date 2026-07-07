import { ApiClientError, distributionApi, jobsApi } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";
import {
  hasDistributionAccess,
  requireDistributionSession,
} from "@/lib/distribution/client-access";

export type DistributionActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export type DistributionContext = {
  platforms: Awaited<ReturnType<typeof distributionApi.platforms>>;
  connections: Awaited<ReturnType<typeof distributionApi.connections>>;
  hasPro: boolean;
};

export async function getDistributionContextAction(): Promise<DistributionContext> {
  const token = getClientAccessToken();
  const hasPro = await hasDistributionAccess(token);
  if (!token) {
    return { platforms: [], connections: [], hasPro };
  }
  try {
    const [platforms, connections] = await Promise.all([
      distributionApi.platforms(token),
      distributionApi.connections(token),
    ]);
    return { platforms, connections, hasPro };
  } catch {
    return { platforms: [], connections: [], hasPro };
  }
}

export async function startOAuthAction(platform: string): Promise<{ url?: string; error?: string }> {
  const session = await requireDistributionSession(
    "Pro license required to connect platforms.",
  );
  if (!session.ok) {
    if (session.message === "Sign in required.") {
      return { error: "login_required" };
    }
    return { error: "pro_required" };
  }
  try {
    const { auth_url } = await distributionApi.oauthStart(platform, session.token);
    return { url: auth_url };
  } catch (err) {
    const code =
      err instanceof ApiClientError ? err.code : "oauth_start_failed";
    return { error: code };
  }
}

export async function disconnectPlatformAction(
  connectionId: string,
): Promise<DistributionActionState> {
  const session = await requireDistributionSession(
    "Pro license required to manage connections.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    await distributionApi.disconnect(connectionId, session.token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not remove connection." };
  }
}

export async function updateOAuthAppAction(
  platform: string,
  _prev: DistributionActionState,
  formData: FormData,
): Promise<DistributionActionState> {
  const session = await requireDistributionSession(
    "Pro license required to configure OAuth apps.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }

  const clientId = formData.get("client_id")?.toString().trim() ?? "";
  const clientSecret = formData.get("client_secret")?.toString().trim() ?? "";
  const redirectUri = formData.get("redirect_uri")?.toString().trim() || undefined;

  if (!clientId || !clientSecret) {
    return { status: "error", message: "Client ID and secret are required." };
  }

  try {
    await distributionApi.updateOAuthApp(
      platform,
      { client_id: clientId, client_secret: clientSecret, redirect_uri: redirectUri },
      session.token,
    );
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not save OAuth app settings." };
  }
}

export async function publishClipAction(
  clipId: string,
  platform: string,
  title?: string,
  description?: string,
): Promise<DistributionActionState & { publishJobId?: string }> {
  const session = await requireDistributionSession(
    "Pro license required to publish.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    const job = await distributionApi.publish(
      { clip_id: clipId, platform, title, description },
      session.token,
    );
    return { status: "ok", publishJobId: job.id };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not queue publish." };
  }
}

export async function scheduleClipAction(
  clipId: string,
  platform: string,
  scheduledAt: string,
  title?: string,
  description?: string,
): Promise<DistributionActionState & { publishJobId?: string }> {
  const session = await requireDistributionSession(
    "Pro license required to schedule.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    const job = await distributionApi.schedule(
      {
        clip_id: clipId,
        platform,
        scheduled_at: scheduledAt,
        title,
        description,
      },
      session.token,
    );
    return { status: "ok", publishJobId: job.id };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not schedule publish." };
  }
}

export async function publishVaultClipAction(
  vaultClipId: string,
  platform: string,
  title?: string,
  description?: string,
): Promise<DistributionActionState & { publishJobId?: string }> {
  const session = await requireDistributionSession(
    "Pro license required to publish.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    const job = await distributionApi.publish(
      { vault_clip_id: vaultClipId, platform, title, description },
      session.token,
    );
    return { status: "ok", publishJobId: job.id };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not queue publish." };
  }
}

export async function scheduleVaultClipAction(
  vaultClipId: string,
  platform: string,
  scheduledAt: string,
  title?: string,
  description?: string,
): Promise<DistributionActionState & { publishJobId?: string }> {
  const session = await requireDistributionSession(
    "Pro license required to schedule.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    const job = await distributionApi.schedule(
      {
        vault_clip_id: vaultClipId,
        platform,
        scheduled_at: scheduledAt,
        title,
        description,
      },
      session.token,
    );
    return { status: "ok", publishJobId: job.id };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not schedule publish." };
  }
}

export async function retryPublishJobAction(
  publishJobId: string,
): Promise<DistributionActionState> {
  const session = await requireDistributionSession(
    "Pro license required to retry publishes.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    await distributionApi.retryPublishJob(publishJobId, session.token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not retry publish." };
  }
}

export async function updatePublishJobAction(
  publishJobId: string,
  edits: { title?: string; description?: string; scheduledAt?: string },
): Promise<DistributionActionState> {
  const session = await requireDistributionSession(
    "Pro license required to edit publishes.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    await distributionApi.updatePublishJob(
      publishJobId,
      {
        title: edits.title,
        description: edits.description,
        scheduled_at: edits.scheduledAt,
      },
      session.token,
    );
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not update publish." };
  }
}

export async function cancelPublishJobAction(
  publishJobId: string,
): Promise<DistributionActionState> {
  const session = await requireDistributionSession(
    "Pro license required to cancel publishes.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    await distributionApi.cancelPublishJob(publishJobId, session.token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not cancel publish." };
  }
}

export async function batchPublishClipsAction(
  jobId: string,
  platform: string,
): Promise<DistributionActionState & { queued?: number; skipped?: number }> {
  const session = await requireDistributionSession(
    "Pro license required to batch publish.",
  );
  if (!session.ok) {
    return { status: "error", message: session.message };
  }
  try {
    const result = await jobsApi.batchPublishClips(jobId, { platform }, session.token);
    return {
      status: "ok",
      queued: result.jobs.length,
      skipped: result.skipped,
    };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not batch publish." };
  }
}
