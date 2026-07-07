import { ApiClientError, jobsApi, metaApi } from "@/lib/api/client";
import type { JobOut } from "@/lib/api/types";
import {
  getClientAccessToken,
} from "@/lib/auth/client-session";
import { hasDistributionAccess } from "@/lib/distribution/client-access";
import { normalizeStreamClipMeta } from "@/lib/normalize-meta";
import type { AspectRatioOption, MetaOption } from "@/lib/api/meta-types";

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

  const token = getClientAccessToken();
  hasDistribution = token ? await hasDistributionAccess(token) : false;
  job = await jobsApi.get(jobId, token);
  const rawMeta = await metaApi.meta();
  const meta = normalizeStreamClipMeta(rawMeta as Record<string, unknown>);
  captionStyleOptions = meta.caption_styles;
  reframePresetOptions = meta.reframe_presets;
  aspectRatioCatalog = meta.aspect_ratios;

  return {
    job,
    captionStyleOptions,
    reframePresetOptions,
    aspectRatioCatalog: aspectRatioCatalog ?? [],
    hasDistribution,
  };
}

export function isJobNotFound(err: unknown): boolean {
  return err instanceof ApiClientError && err.status === 404;
}
