import type { StreamClipMeta } from "@/lib/api/meta-types";

export function normalizeStreamClipMeta(raw: Record<string, unknown>): StreamClipMeta {
  const asOptions = (items: unknown) =>
    Array.isArray(items)
      ? items.map((item) => {
          if (typeof item === "string") {
            return { id: item, label: item };
          }
          const row = item as Record<string, unknown>;
          return {
            id: String(row.id),
            label: String(row.label ?? row.id),
            description: typeof row.description === "string" ? row.description : undefined,
            best_for: typeof row.best_for === "string" ? row.best_for : undefined,
            aspect_ratio: typeof row.aspect_ratio === "string" ? row.aspect_ratio : undefined,
            output_resolution:
              typeof row.output_resolution === "string" ? row.output_resolution : undefined,
            platforms: Array.isArray(row.platforms) ? row.platforms.map(String) : undefined,
            preview_hint: typeof row.preview_hint === "string" ? row.preview_hint : undefined,
            category: typeof row.category === "string" ? row.category : undefined,
            tags: Array.isArray(row.tags) ? row.tags.map(String) : undefined,
          };
        })
      : [];

  return {
    version: String(raw.version ?? "1.0.0"),
    processing_profile: raw.processing_profile === "gpu" ? "gpu" : "cpu",
    content_profiles: asOptions(raw.content_profiles),
    caption_styles: asOptions(raw.caption_styles),
    reframe_presets: asOptions(raw.reframe_presets),
    emotion_labels: Array.isArray(raw.emotion_labels)
      ? raw.emotion_labels.map(String)
      : [],
  };
}
