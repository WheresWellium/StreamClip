import { ApiClientError, jobsApi, metaApi } from "@/lib/api/client";
import type { JobOut } from "@/lib/api/types";
import { getAccessToken } from "@/lib/auth/session";
import { hasDistributionAccess } from "@/lib/distribution/access";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";
import type { AspectRatioOption, MetaOption } from "@/lib/api/meta-types";
import { notFound } from "next/navigation";

export type JobPageContext = {
  job: JobOut;
  captionStyleOptions: MetaOption[];
  reframePresetOptions: MetaOption[];
  aspectRatioCatalog: AspectRatioOption[];
  hasDistribution: boolean;
};

export async function loadJobPageContext(jobId: string): Promise<JobPageContext> {
  let job: JobOut;
  let captionStyleOptions = normalizeStreamClipMeta({}).caption_styles;
  let reframePresetOptions = normalizeStreamClipMeta({}).reframe_presets;
  let aspectRatioCatalog = normalizeStreamClipMeta({}).aspect_ratios;
  let hasDistribution = false;

  try {
    const token = await getAccessToken();
    hasDistribution = token ? await hasDistributionAccess(token) : false;
    job = await jobsApi.get(jobId, token);
    const rawMeta = await metaApi.meta();
    const meta = normalizeStreamClipMeta(rawMeta as Record<string, unknown>);
    captionStyleOptions = meta.caption_styles;
    reframePresetOptions = meta.reframe_presets;
    aspectRatioCatalog = meta.aspect_ratios;
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  return {
    job,
    captionStyleOptions,
    reframePresetOptions,
    aspectRatioCatalog: aspectRatioCatalog ?? [],
    hasDistribution,
  };
}
