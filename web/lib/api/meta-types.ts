export type MetaOption = {
  id: string;
  label: string;
  description?: string;
  best_for?: string;
  aspect_ratio?: string;
  output_resolution?: string;
  platforms?: string[];
  preview_hint?: string;
  category?: string;
  tags?: string[];
};

export type AspectRatioOption = {
  id: string;
  label: string;
  width: number;
  height: number;
  output_resolution: string;
  aspect_ratio: string;
  description?: string;
  platforms?: string[];
};

export type StreamClipMeta = {
  version: string;
  processing_profile?: "cpu" | "gpu";
  content_profiles: MetaOption[];
  caption_styles: MetaOption[];
  reframe_presets: MetaOption[];
  aspect_ratios?: AspectRatioOption[];
  emotion_labels: string[];
};

export type JobTemplate = {
  id: string;
  name: string;
  config_json: Record<string, unknown>;
};

export type UpdateClipBody = {
  start_secs?: number;
  end_secs?: number;
  caption_style?: string;
  reframe_preset?: string;
  aspect_ratio?: string;
  overlay_enabled?: boolean;
  rerender?: boolean;
};
