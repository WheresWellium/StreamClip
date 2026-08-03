"use client";

import {
  ChevronDown,
  Dumbbell,
  Gamepad2,
  GraduationCap,
  Loader2,
  Mic2,
  Music2,
  Radio,
  Save,
  Sparkles,
  Trophy,
  Upload,
  Link2,
  Video,
} from "lucide-react";
import * as React from "react";
import { useFormStatus } from "react-dom";

import {
  createJobAction,
  saveTemplateAction,
  type CreateJobActionState,
} from "@/lib/api/actions/jobs";
import { assetsApi, type OverlayAsset } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { navigateToJob } from "@/lib/jobs/job-route-id";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/form";
import { SectionLegend } from "@/components/ui/section-legend";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DirectUpload } from "@/components/upload/direct-upload";
import { AspectRatioSelect } from "@/components/jobs/aspect-ratio-select";
import { CreatorOptionCards } from "@/components/jobs/creator-option-cards";
import { CollapsibleSection } from "@/components/ui/collapsible-section";
import { FORM_SECTION_LEGEND } from "@/lib/help/legends";
import type { JobTemplate, MetaOption, StreamClipMeta } from "@/lib/api/meta-types";
import { cn } from "@/lib/utils/format";

const INITIAL_STATE: CreateJobActionState = { status: "idle" };

const PROFILE_ICONS: Record<string, React.ElementType> = {
  gaming: Gamepad2,
  esports: Trophy,
  irl: Radio,
  vlog: Video,
  podcast: Mic2,
  education: GraduationCap,
  sports: Dumbbell,
  music: Music2,
  general: Sparkles,
};

const PROFANITY_MODES = [
  { id: "mask", label: "Mask (f***)" },
  { id: "bleep", label: "Bleep (•••)" },
  { id: "omit", label: "Omit (remove word)" },
] as const;

const REFRAME_PLATFORM_NOTE =
  "Presets control how we crop and track the subject — the export aspect ratio sets the output frame.";

function StepLabel({ n, title, tip }: { n: number; title: string; tip?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center border border-sky-400/50 bg-sky-400/10 font-mono text-[10px] text-sky-400"
        aria-hidden
      >
        {n}
      </span>
      {tip ? (
        <SectionLegend title={title} tip={tip} />
      ) : (
        <span className="term-label">{title}</span>
      )}
    </div>
  );
}

type Props = {
  meta: StreamClipMeta;
  templates: JobTemplate[];
  isAuthenticated: boolean;
  defaultSourceUrl?: string;
  /** Called before navigating to the new job (e.g. mark onboarding complete). */
  onJobCreated?: (jobId: string) => void | Promise<void>;
};

export function CreateJobForm({
  meta,
  templates,
  isAuthenticated,
  defaultSourceUrl,
  onJobCreated,
}: Props) {
  const [state, formAction] = React.useActionState(createJobAction, INITIAL_STATE);
  const [mode, setMode] = React.useState<"url" | "upload">("url");
  const [uploadKey, setUploadKey] = React.useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const [showOutputStyle, setShowOutputStyle] = React.useState(false);
  const [reframePreset, setReframePreset] = React.useState(
    meta.reframe_presets[0]?.id ?? "fps_game",
  );
  const [captionStyle, setCaptionStyle] = React.useState(
    meta.caption_styles[0]?.id ?? "gaming_impact",
  );
  const [contentProfile, setContentProfile] = React.useState(
    meta.content_profiles[0]?.id ?? "gaming",
  );
  const [aspectRatio, setAspectRatio] = React.useState("9:16");
  const audioIngestEnabled = meta.features?.audio_ingest !== false;
  const [targetClips, setTargetClips] = React.useState(5);
  const [profanityFilter, setProfanityFilter] = React.useState(false);
  const [profanityMode, setProfanityMode] = React.useState<
    (typeof PROFANITY_MODES)[number]["id"]
  >("mask");
  const [assetPackId, setAssetPackId] = React.useState("");
  const [assets, setAssets] = React.useState<OverlayAsset[]>([]);
  const [templateMsg, setTemplateMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    void assetsApi
      .list(getClientAccessToken() ?? undefined)
      .then((list) => {
        if (!cancelled) setAssets(list);
      })
      .catch(() => {
        // Overlay packs are optional — the field is simply hidden if unavailable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    if (state.status !== "ok" || !state.jobId) return;
    let cancelled = false;
    void (async () => {
      try {
        await onJobCreated?.(state.jobId!);
      } catch {
        // Navigation still proceeds — caller failures must not trap the user.
      }
      // Full document navigation: static export only prebuilds jobs/_/ so
      // Next soft-nav to a real id shows "Job not found" instantly.
      if (!cancelled) navigateToJob(state.jobId!);
    })();
    return () => {
      cancelled = true;
    };
  }, [state.status, state.jobId, onJobCreated]);

  const selectedProfile = meta.content_profiles.find((p) => p.id === contentProfile);

  /** Choosing a content type also configures its matching crop + caption presets. */
  function selectContentProfile(profile: MetaOption) {
    setContentProfile(profile.id);
    if (profile.recommended_reframe) setReframePreset(profile.recommended_reframe);
    if (profile.recommended_captions) setCaptionStyle(profile.recommended_captions);
  }

  function applyTemplate(templateId: string) {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    const c = tpl.config_json;
    if (typeof c.content_profile === "string") setContentProfile(c.content_profile);
    if (typeof c.reframe_preset === "string") setReframePreset(c.reframe_preset);
    if (typeof c.caption_style === "string") setCaptionStyle(c.caption_style);
    if (typeof c.aspect_ratio === "string") setAspectRatio(c.aspect_ratio);
    if (typeof c.target_clips === "number") setTargetClips(c.target_clips);
    if (typeof c.profanity_filter === "boolean") setProfanityFilter(c.profanity_filter);
    if (
      typeof c.profanity_mode === "string" &&
      PROFANITY_MODES.some((m) => m.id === c.profanity_mode)
    ) {
      setProfanityMode(c.profanity_mode as (typeof PROFANITY_MODES)[number]["id"]);
    }
    if (typeof c.asset_pack_id === "string") setAssetPackId(c.asset_pack_id);
  }

  async function handleSaveTemplate() {
    setTemplateMsg(null);
    const result = await saveTemplateAction({
      content_profile: contentProfile,
      reframe_preset: reframePreset,
      caption_style: captionStyle,
      aspect_ratio: aspectRatio,
      target_clips: targetClips,
      profanity_filter: profanityFilter,
      profanity_mode: profanityMode,
      ...(assetPackId ? { asset_pack_id: assetPackId } : {}),
    });
    setTemplateMsg(result.ok ? "Template saved" : result.message ?? "Could not save");
  }

  return (
    <Card>
      <CardHeader className="pb-3 border-b border-frame/10">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-4 w-4 text-sky-400" />
          New clip job
        </CardTitle>
        <CardDescription>
          Paste a URL or upload a video — we find the best moments, reframe to any
          aspect ratio, and rank clips so you know what to ship first.
          {meta.processing_profile === "cpu" && (
            <span className="block mt-1 text-sky-400/80 text-xs">
              CPU mode — transcribe and render may take longer. Enable GPU profile for faster jobs.
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        {isAuthenticated && templates.length > 0 && (
          <div className="mb-5 space-y-1.5 p-3 rounded-sm glossy-surface-light">
            <Label htmlFor="template_select" className="text-muted-foreground text-xs">
              Quick start from template
            </Label>
            <Select
              id="template_select"
              defaultValue=""
              onChange={(e) => e.target.value && applyTemplate(e.target.value)}
            >
              <option value="">Choose a saved template…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </Select>
          </div>
        )}

        <form action={formAction} className="space-y-6">
          {/* Step 1 — Source */}
          <div className="space-y-3">
            <StepLabel n={1} title="Source" tip={FORM_SECTION_LEGEND.source} />
            <div className="grid grid-cols-2 border border-frame/25 rounded-sm overflow-hidden">
              {(["url", "upload"] as const).map((m) => {
                const Icon = m === "url" ? Link2 : Upload;
                const active = mode === m;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    aria-pressed={active}
                    className={cn(
                      "flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-colors first:border-r first:border-frame/25",
                      active
                        ? "bg-sky-400/10 text-sky-400"
                        : "text-muted-foreground hover:text-foreground hover:bg-frame/5",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {m === "url" ? "Paste URL" : "Upload file"}
                  </button>
                );
              })}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="display_title">Job name (optional)</Label>
              <Input
                id="display_title"
                name="display_title"
                maxLength={512}
                placeholder="e.g. Saturday stream highlights"
              />
            </div>

            {mode === "url" ? (
              <div className="space-y-1.5">
                <Label htmlFor="source_url">Video URL</Label>
                <Input
                  id="source_url"
                  name="source_url"
                  defaultValue={defaultSourceUrl ?? ""}
                  type="url"
                  placeholder="https://www.twitch.tv/videos/..."
                  required={mode === "url"}
                  autoFocus
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label>
                  Upload video{audioIngestEnabled ? " or audio" : ""} (MP4 / MOV / MKV
                  {audioIngestEnabled ? " / MP3 / WAV / M4A" : ""})
                </Label>
                {!audioIngestEnabled ? (
                  <p className="text-xs text-muted-foreground">
                    Audio-to-clip is disabled on this server — upload video only.
                  </p>
                ) : null}
                <DirectUpload
                  currentKey={uploadKey}
                  allowAudio={audioIngestEnabled}
                  onUploaded={(key) => setUploadKey(key)}
                  onCleared={() => setUploadKey(null)}
                />
                <input type="hidden" name="source_upload_key" value={uploadKey ?? ""} />
              </div>
            )}
          </div>

          {/* Step 2 — Content type */}
          <div className="space-y-3">
            <StepLabel
              n={2}
              title="Content type"
              tip="Tunes highlight detection for your vertical and pre-selects the matching crop and caption presets below. Pick the closest match."
            />
            <input type="hidden" name="content_profile" value={contentProfile} />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {meta.content_profiles.map((profile) => {
                const Icon = PROFILE_ICONS[profile.id] ?? Sparkles;
                const selected = contentProfile === profile.id;
                return (
                  <Tooltip key={profile.id}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => selectContentProfile(profile)}
                        className={cn(
                          "flex flex-col items-start gap-1.5 p-3 rounded-lg text-left transition-all border",
                          selected
                            ? "border-sky-400/50 bg-sky-400/10 text-foreground sky-glow"
                            : "border-frame/15 bg-black/20 hover:border-frame/30 hover:bg-frame/5",
                        )}
                      >
                        <div className="flex items-center gap-2 w-full">
                          <Icon
                            className={cn(
                              "h-4 w-4 shrink-0",
                              selected ? "text-sky-400" : "text-muted-foreground",
                            )}
                          />
                          <span className="text-sm font-medium truncate">{profile.label}</span>
                        </div>
                        {profile.description && (
                          <span className="text-xs text-muted-foreground line-clamp-2">
                            {profile.description}
                          </span>
                        )}
                        {profile.best_for && (
                          <span className="text-[10px] text-muted-foreground line-clamp-1">
                            Best for {profile.best_for}
                          </span>
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="max-w-xs">
                      {profile.description ?? profile.label}
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          <input type="hidden" name="reframe_preset" value={reframePreset} />
          <input type="hidden" name="caption_style" value={captionStyle} />
          <input type="hidden" name="aspect_ratio" value={aspectRatio} />
          <input
            type="hidden"
            name="profanity_filter"
            value={profanityFilter ? "on" : "off"}
          />
          <input type="hidden" name="profanity_mode" value={profanityMode} />
          <input type="hidden" name="asset_pack_id" value={assetPackId} />

          {/* Step 3 — Output style (collapsed until expanded) */}
          <CollapsibleSection
            title="Output style"
            summary={
              selectedProfile
                ? `${aspectRatio} · ${selectedProfile.label} defaults`
                : `${aspectRatio} · tap to customize crop & captions`
            }
            open={showOutputStyle}
            onOpenChange={setShowOutputStyle}
            className="border-frame/20"
          >
            <div className="space-y-5">
              {selectedProfile && (
                <p className="text-xs text-muted-foreground">
                  Pre-configured for{" "}
                  <span className="text-sky-400">{selectedProfile.label}</span> — override
                  anything below.
                </p>
              )}

              <AspectRatioSelect
                value={aspectRatio}
                onChange={setAspectRatio}
                options={meta.aspect_ratios}
              />

              <CreatorOptionCards
                title="Reframe preset"
                tip={`How we crop landscape source into social-ready clips. ${REFRAME_PLATFORM_NOTE}`}
                options={meta.reframe_presets}
                value={reframePreset}
                onChange={setReframePreset}
                columns={2}
                showAspectBadge
                showPlatformChips
                aspectRatioId={aspectRatio}
                aspectRatioCatalog={meta.aspect_ratios}
                recommendedId={selectedProfile?.recommended_reframe}
              />

              <CreatorOptionCards
                title="Caption style"
                tip="Burned-in text style on every clip. Choose No Captions if you add subtitles elsewhere."
                options={meta.caption_styles}
                value={captionStyle}
                onChange={setCaptionStyle}
                columns={2}
                recommendedId={selectedProfile?.recommended_captions}
              />
            </div>
          </CollapsibleSection>

          {/* Clip count — collapsed by default */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              aria-expanded={showAdvanced}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-180")}
              />
              <span>More options</span>
              <span className="text-xs text-silver">{targetClips} clips</span>
            </button>

            {showAdvanced && (
              <div className="p-3 rounded-sm glossy-surface-light space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="target_clips">Clips to generate (1–20)</Label>
                  <Input
                    id="target_clips"
                    name="target_clips"
                    type="number"
                    value={targetClips}
                    onChange={(e) => setTargetClips(Number(e.target.value))}
                    min={1}
                    max={20}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={profanityFilter}
                    onChange={(e) => setProfanityFilter(e.target.checked)}
                    className="accent-sky-500"
                  />
                  <span>
                    Filter profanity
                    <span className="block text-xs text-muted-foreground">
                      Censors swear words in captions and clip titles
                    </span>
                  </span>
                </label>
                {profanityFilter && (
                  <div className="space-y-1.5 pl-6">
                    <Label htmlFor="profanity_mode_select">Censor style</Label>
                    <Select
                      id="profanity_mode_select"
                      value={profanityMode}
                      onChange={(e) =>
                        setProfanityMode(
                          e.target.value as (typeof PROFANITY_MODES)[number]["id"],
                        )
                      }
                    >
                      {PROFANITY_MODES.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}
                {assets.length > 0 && (
                  <div className="space-y-1.5">
                    <Label htmlFor="asset_pack_select">Overlay asset pack</Label>
                    <Select
                      id="asset_pack_select"
                      value={assetPackId}
                      onChange={(e) => setAssetPackId(e.target.value)}
                    >
                      <option value="">None</option>
                      {assets.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name} ({a.asset_type})
                        </option>
                      ))}
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Meme overlays are matched from this pack during rendering.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {state.status === "error" && state.message && (
            <div
              role="alert"
              data-testid="create-job-error"
              className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive space-y-1"
            >
              <p>{state.message}</p>
              {state.errors
                ? Object.entries(state.errors).map(([field, msgs]) => (
                    <p key={field} className="text-xs opacity-90">
                      {field}: {msgs.join(", ")}
                    </p>
                  ))
                : null}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <SubmitButton mode={mode} uploadReady={!!uploadKey} />
            {isAuthenticated && (
              <Button type="button" variant="outline" onClick={handleSaveTemplate}>
                <Save className="h-4 w-4" />
                Save template
              </Button>
            )}
          </div>
          {templateMsg && (
            <p className="text-xs text-muted-foreground">{templateMsg}</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

function SubmitButton({
  mode,
  uploadReady,
}: {
  mode: "url" | "upload";
  uploadReady: boolean;
}) {
  const { pending } = useFormStatus();
  const disabled = pending || (mode === "upload" && !uploadReady);

  return (
    <Button type="submit" disabled={disabled} size="lg" className="w-full sm:flex-1">
      {pending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Starting…
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          Generate clips
        </>
      )}
    </Button>
  );
}
