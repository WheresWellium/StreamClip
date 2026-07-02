"use server";

/**
 * StreamClip — Server Actions for Jobs
 *
 * Server Actions replace REST endpoints for in-app mutations. They run
 * on the server only — secrets stay on the server, the client just calls
 * the function. After mutation, we revalidate the relevant cache tags so
 * Server Components re-fetch on next navigation.
 */

import { revalidatePath, revalidateTag } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";

import { ApiClientError, jobsApi, settingsApi } from "@/lib/api/client";
import { getAccessToken, getDeviceId, authHeaders } from "@/lib/auth/session";
import {
  ASPECT_RATIO_IDS,
  CAPTION_STYLE_IDS,
  CONTENT_PROFILE_IDS,
  REFRAME_PRESET_IDS,
} from "@/lib/creator-option-ids";

// ─── Validation schema ────────────────────────────────────────────────────────

const CreateJobSchema = z.object({
  source_url: z.string().url().optional().nullable(),
  source_upload_key: z.string().min(1).optional().nullable(),
  target_clips: z.coerce.number().int().min(1).max(20).default(5),
  caption_style: z.enum(CAPTION_STYLE_IDS),
  reframe_preset: z.enum(REFRAME_PRESET_IDS),
  content_profile: z.enum(CONTENT_PROFILE_IDS),
  aspect_ratio: z.enum(ASPECT_RATIO_IDS),
});

export type CreateJobActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  errors?: Record<string, string[]>;
};

// ─── Server Action: create job ───────────────────────────────────────────────

export async function createJobAction(
  prevState: CreateJobActionState,
  formData: FormData,
): Promise<CreateJobActionState> {
  // Coerce form fields, treating empty strings as undefined
  const raw = {
    source_url: formData.get("source_url")?.toString().trim() || null,
    source_upload_key:
      formData.get("source_upload_key")?.toString().trim() || null,
    target_clips: formData.get("target_clips") ?? 5,
    caption_style:
      formData.get("caption_style")?.toString() ?? "gaming_impact",
    reframe_preset:
      formData.get("reframe_preset")?.toString() ?? "fps_game",
    content_profile:
      formData.get("content_profile")?.toString() ?? "gaming",
    aspect_ratio: formData.get("aspect_ratio")?.toString() || "9:16",
  };

  const parsed = CreateJobSchema.safeParse(raw);
  if (!parsed.success) {
    return {
      status: "error",
      message: "Validation failed",
      errors: parsed.error.flatten().fieldErrors,
    };
  }

  if (!parsed.data.source_url && !parsed.data.source_upload_key) {
    return {
      status: "error",
      message: "Provide a URL or upload a file",
    };
  }

  try {
    const token = await getAccessToken();
    const deviceId = await getDeviceId();
    const job = await jobsApi.create(parsed.data, token, deviceId);
    revalidateTag(`job:${job.id}`);
    revalidatePath("/");
    redirect(`/jobs/${job.id}`);
  } catch (err) {
    // `redirect` throws — let it bubble up
    if (err instanceof Error && err.message === "NEXT_REDIRECT") throw err;

    if (err instanceof ApiClientError) {
      return {
        status: "error",
        message: err.message,
      };
    }
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Unknown error",
    };
  }

  return { status: "ok" };
}

// ─── Server Action: cancel job ───────────────────────────────────────────────

export async function cancelJobAction(jobId: string): Promise<void> {
  const token = await getAccessToken();
  await jobsApi.cancel(jobId, token);
  revalidateTag(`job:${jobId}`);
  revalidatePath("/");
}

export async function regenerateClipAction(
  jobId: string,
  clipId: string,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = await getAccessToken();
    await jobsApi.regenerateClip(jobId, clipId, token);
    revalidatePath(`/jobs/${jobId}`);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { ok: false, message: err.message };
    }
    return { ok: false, message: "Could not queue re-render" };
  }
}

export async function saveTemplateAction(config: Record<string, unknown>): Promise<{
  ok: boolean;
  message?: string;
}> {
  try {
    const token = await getAccessToken();
    if (!token) return { ok: false, message: "Sign in to save templates" };
    const name = `Template ${new Date().toLocaleDateString()}`;
    const { templatesApi } = await import("@/lib/api/client");
    await templatesApi.create(name, config, token);
    revalidatePath("/");
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not save template" };
  }
}

export async function createBatchJobsAction(
  urls: string[],
): Promise<{ ok: boolean; message: string }> {
  if (!urls.length) return { ok: false, message: "Add at least one URL" };
  try {
    const token = await getAccessToken();
    const jobs = urls.slice(0, 20).map((source_url) => ({
      source_url,
      target_clips: 5,
      caption_style: "gaming_impact" as const,
      reframe_preset: "fps_game" as const,
      content_profile: "gaming" as const,
      aspect_ratio: "9:16" as const,
    }));
    const result = await jobsApi.createBatch(jobs, token);
    revalidatePath("/");
    return {
      ok: true,
      message: `Queued ${result.jobs.length} job(s).`,
    };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Batch queue failed" };
  }
}

export async function updateClipAction(
  jobId: string,
  clipId: string,
  body: Record<string, unknown>,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = await getAccessToken();
    await jobsApi.updateClip(jobId, clipId, body, token);
    revalidatePath(`/jobs/${jobId}`);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not update clip" };
  }
}

export async function spliceClipsAction(
  jobId: string,
  clipIds: string[],
  transition: "cut" | "crossfade" = "cut",
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = await getAccessToken();
    await jobsApi.spliceClips(jobId, clipIds, transition, token);
    revalidatePath(`/jobs/${jobId}`);
    return { ok: true, message: "Merge queued" };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not merge clips" };
  }
}

export async function submitClipFeedbackAction(
  clipId: string,
  rating: number,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = await getAccessToken();
    await settingsApi.submitClipFeedback(clipId, rating, token ?? undefined);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not save feedback" };
  }
}
