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

import { ApiClientError, jobsApi } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import type {
  CaptionStyle,
  ReframePreset,
} from "@/lib/api/types";

// ─── Validation schema ────────────────────────────────────────────────────────

const CreateJobSchema = z.object({
  source_url: z.string().url().optional().nullable(),
  source_upload_key: z.string().min(1).optional().nullable(),
  target_clips: z.coerce.number().int().min(1).max(20).default(5),
  caption_style: z.enum([
    "gaming_impact",
    "tiktok_pop",
    "minimal_white",
    "podcast_clean",
  ]),
  reframe_preset: z.enum([
    "fps_game",
    "moba",
    "battle_royale",
    "irl",
    "podcast",
    "auto",
  ]),
  content_profile: z.enum([
    "gaming",
    "irl",
    "podcast",
    "esports",
    "general",
  ]),
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
      (formData.get("caption_style")?.toString() as CaptionStyle) ??
      "gaming_impact",
    reframe_preset:
      (formData.get("reframe_preset")?.toString() as ReframePreset) ??
      "fps_game",
    content_profile:
      formData.get("content_profile")?.toString() ?? "gaming",
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
    const job = await jobsApi.create(parsed.data, token);
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
