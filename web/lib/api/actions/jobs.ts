import { z } from "zod";

import { ApiClientError, jobsApi, settingsApi, templatesApi } from "@/lib/api/client";
import type { ClipWord } from "@/lib/api/types";
import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";
import {
  ASPECT_RATIO_IDS,
  CAPTION_STYLE_IDS,
  CONTENT_PROFILE_IDS,
  REFRAME_PRESET_IDS,
} from "@/lib/creator-option-ids";
import { normalizeSourceUrl } from "@/lib/uploads/source-url";

const CreateJobSchema = z.object({
  source_url: z.string().url().optional().nullable(),
  source_upload_key: z.string().min(1).optional().nullable(),
  display_title: z.string().max(512).optional().nullable(),
  target_clips: z.coerce.number().int().min(1).max(20).default(5),
  caption_style: z.enum(CAPTION_STYLE_IDS),
  reframe_preset: z.enum(REFRAME_PRESET_IDS),
  content_profile: z.enum(CONTENT_PROFILE_IDS),
  aspect_ratio: z.enum(ASPECT_RATIO_IDS),
  profanity_filter: z.boolean().default(false),
  profanity_mode: z.enum(["mask", "bleep", "omit"]).default("mask"),
  asset_pack_id: z.string().min(1).optional().nullable(),
});

export type CreateJobActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  errors?: Record<string, string[]>;
  jobId?: string;
};

export async function createJobAction(
  prevState: CreateJobActionState,
  formData: FormData,
): Promise<CreateJobActionState> {
  const raw = {
    source_url: normalizeSourceUrl(formData.get("source_url")?.toString()) || null,
    source_upload_key:
      formData.get("source_upload_key")?.toString().trim() || null,
    display_title: formData.get("display_title")?.toString().trim() || null,
    target_clips: formData.get("target_clips") ?? 5,
    caption_style:
      formData.get("caption_style")?.toString() ?? "gaming_impact",
    reframe_preset:
      formData.get("reframe_preset")?.toString() ?? "fps_game",
    content_profile:
      formData.get("content_profile")?.toString() ?? "gaming",
    aspect_ratio: formData.get("aspect_ratio")?.toString() || "9:16",
    profanity_filter: formData.get("profanity_filter") === "on",
    profanity_mode: formData.get("profanity_mode")?.toString() || "mask",
    asset_pack_id: formData.get("asset_pack_id")?.toString().trim() || null,
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
    const token = getClientAccessToken();
    const deviceId = getClientDeviceId();
    const job = await jobsApi.create(parsed.data, token, deviceId);
    return { status: "ok", jobId: job.id };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return {
      status: "error",
      message: err instanceof Error ? err.message : "Unknown error",
    };
  }
}

export async function cancelJobAction(jobId: string): Promise<void> {
  const token = getClientAccessToken();
  await jobsApi.cancel(jobId, token);
}

export async function updateJobTitleAction(
  jobId: string,
  displayTitle: string | null,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    const deviceId = getClientDeviceId();
    await jobsApi.update(jobId, { display_title: displayTitle }, token, deviceId);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { ok: false, message: err.message };
    }
    return { ok: false, message: "Could not update job title" };
  }
}

export async function regenerateClipAction(
  jobId: string,
  clipId: string,
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    await jobsApi.regenerateClip(jobId, clipId, token);
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
    const token = getClientAccessToken();
    if (!token) return { ok: false, message: "Sign in to save templates" };
    const name = `Template ${new Date().toLocaleDateString()}`;
    await templatesApi.create(name, config, token);
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
    const token = getClientAccessToken();
    const jobs = urls.slice(0, 20).map((source_url) => ({
      source_url,
      target_clips: 5,
      caption_style: "gaming_impact" as const,
      reframe_preset: "fps_game" as const,
      content_profile: "gaming" as const,
      aspect_ratio: "9:16" as const,
    }));
    const result = await jobsApi.createBatch(jobs, token);
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
    const token = getClientAccessToken();
    await jobsApi.updateClip(jobId, clipId, body, token);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not update clip" };
  }
}

export async function getClipWordsAction(
  jobId: string,
  clipId: string,
): Promise<
  { ok: true; words: ClipWord[] } | { ok: false; message: string }
> {
  try {
    const token = getClientAccessToken();
    const result = await jobsApi.clipWords(jobId, clipId, token);
    return { ok: true, words: result.words };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not load transcript words" };
  }
}

export async function getJobWaveformAction(
  jobId: string,
): Promise<{ ok: true; url: string } | { ok: false }> {
  try {
    const token = getClientAccessToken();
    const result = await jobsApi.waveform(jobId, token);
    return { ok: true, url: result.url };
  } catch {
    return { ok: false };
  }
}

export async function spliceClipsAction(
  jobId: string,
  clipIds: string[],
  transition: "cut" | "crossfade" = "cut",
): Promise<{ ok: boolean; message?: string }> {
  try {
    const token = getClientAccessToken();
    await jobsApi.spliceClips(jobId, clipIds, transition, token);
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
    const token = getClientAccessToken();
    await settingsApi.submitClipFeedback(clipId, rating, token ?? undefined);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiClientError) return { ok: false, message: err.message };
    return { ok: false, message: "Could not save feedback" };
  }
}
