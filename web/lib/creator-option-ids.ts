export type CreatorMetaOption = {
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

export const CONTENT_PROFILE_IDS = [
  "gaming",
  "esports",
  "irl",
  "vlog",
  "podcast",
  "education",
  "sports",
  "music",
  "general",
] as const;

export const REFRAME_PRESET_IDS = [
  "fps_game",
  "moba",
  "battle_royale",
  "sports_action",
  "irl",
  "podcast",
  "presentation",
  "cinematic_wide",
  "auto",
] as const;

export const CAPTION_STYLE_IDS = [
  "gaming_impact",
  "shorts_bold",
  "tiktok_pop",
  "karaoke_highlight",
  "minimal_white",
  "podcast_clean",
  "accessibility_clean",
  "none",
] as const;
