/** User-facing job title — display_title overrides ingest metadata. */

export type JobTitleFields = {
  display_title?: string | null;
  source_title?: string | null;
};

export function getEffectiveJobTitle(job: JobTitleFields): string {
  const custom = job.display_title?.trim();
  if (custom) return custom;
  const source = job.source_title?.trim();
  if (source) return source;
  return "Untitled job";
}
