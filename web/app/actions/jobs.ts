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
  min_virality_score: z.coerce.number().int().min(0).max(100).default(55),
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
    min_virality_score: formData.get("min_virality_score") ?? 55,
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
    const job = await jobsApi.create(parsed.data);
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
  await jobsApi.cancel(jobId);
  revalidateTag(`job:${jobId}`);
  revalidatePath("/");
}
