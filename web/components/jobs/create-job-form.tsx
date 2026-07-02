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
} from "@/app/actions/jobs";
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
};

export function CreateJobForm({ meta, templates, isAuthenticated, defaultSourceUrl }: Props) {
  const [state, formAction] = React.useActionState(createJobAction, INITIAL_STATE);
  const [mode, setMode] = React.useState<"url" | "upload">("url");
  const [uploadKey, setUploadKey] = React.useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = React.useState(false);
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
  const [targetClips, setTargetClips] = React.useState(5);
  const [templateMsg, setTemplateMsg] = React.useState<string | null>(null);

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
  }

  async function handleSaveTemplate() {
    setTemplateMsg(null);
    const result = await saveTemplateAction({
      content_profile: contentProfile,
      reframe_preset: reframePreset,
      caption_style: captionStyle,
      aspect_ratio: aspectRatio,
      target_clips: targetClips,
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
          Paste a URL or upload a video — we&apos;ll find the best moments and render social-ready clips.
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
                <Label>Upload (MP4 / MOV / MKV)</Label>
                <DirectUpload
                  currentKey={uploadKey}
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

          {/* Step 3 — Output style (pre-configured by the content type) */}
          <div className="space-y-5 border-l-2 border-frame/15 pl-4">
            <div className="space-y-1">
              <StepLabel
                n={3}
                title="Output style"
                tip="Aspect ratio, cropping, and captions. Pre-configured by your content type — override anything."
              />
              {selectedProfile && (
                <p className="text-xs text-muted-foreground pl-[30px]">
                  Configured for <span className="text-sky-400">{selectedProfile.label}</span> —
                  change anything below.
                </p>
              )}
            </div>

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

          {/* Clip count — collapsed by default */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-180")}
              />
              <span>More options</span>
              <span className="text-xs text-silver">{targetClips} clips</span>
            </button>

            {showAdvanced && (
              <div className="p-3 rounded-sm glossy-surface-light space-y-1.5">
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
            )}
          </div>

          {state.status === "error" && state.message && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {state.message}
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
