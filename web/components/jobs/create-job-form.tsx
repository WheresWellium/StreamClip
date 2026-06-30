"use client";

import { Loader2, Sparkles } from "lucide-react";
import * as React from "react";
import { useFormStatus } from "react-dom";

import { createJobAction, type CreateJobActionState } from "@/app/actions/jobs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/form";
import { HelpTip, LabelWithTip } from "@/components/ui/help-tip";
import { SectionLegend } from "@/components/ui/section-legend";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DirectUpload } from "@/components/upload/direct-upload";
import { FORM_SECTION_LEGEND } from "@/lib/help/legends";

const INITIAL_STATE: CreateJobActionState = { status: "idle" };

const REFRAME_PRESET_TIPS: Record<string, string> = {
  fps_game:
    "Fast-action shooters — tracks the player with HUD protection for health and ammo bars.",
  moba: "MOBA / strategy — slower, wider framing with minimap area reserved at the bottom.",
  battle_royale:
    "Battle royale — follows the player aggressively; suited to fast repositioning.",
  irl: "IRL / talking head — tight face crop with very stable, minimal camera movement.",
  podcast:
    "Podcast / interview — stable speaker framing with no gameplay HUD reserves.",
  auto: "Automatically picks FPS or IRL framing based on each clip's detected emotion.",
};

const CAPTION_STYLE_TIPS: Record<string, string> = {
  gaming_impact:
    "Bold animated captions with per-word karaoke sync and keyword highlights.",
  tiktok_pop:
    "Punchy pop-in text styled for TikTok, Reels, and Shorts.",
  minimal_white: "Clean white subtitles with minimal visual noise.",
  podcast_clean: "Readable lower-third captions suited to dialogue-heavy content.",
};

export function CreateJobForm() {
  const [state, formAction] = React.useActionState(
    createJobAction,
    INITIAL_STATE,
  );

  const [mode, setMode] = React.useState<"url" | "upload">("url");
  const [uploadKey, setUploadKey] = React.useState<string | null>(null);
  const [reframePreset, setReframePreset] =
    React.useState<keyof typeof REFRAME_PRESET_TIPS>("fps_game");
  const [captionStyle, setCaptionStyle] =
    React.useState<keyof typeof CAPTION_STYLE_TIPS>("gaming_impact");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          New clip job
        </CardTitle>
        <CardDescription>
          Paste a Twitch/YouTube URL or upload a video file. We&apos;ll handle the
          rest.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="space-y-5">
          {/* Source mode toggle */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-medium">Source</span>
              <HelpTip
                label="Source mode help"
                content="Choose whether to paste a public video URL or upload a file from your device."
              />
            </div>
            <div className="flex gap-1 p-1 rounded-md bg-secondary/60 w-fit">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => setMode("url")}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      mode === "url"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    URL
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  Paste a Twitch VOD, clip, YouTube, Kick, or direct MP4 link.
                  We download and process it automatically.
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => setMode("upload")}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      mode === "upload"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Upload
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  Upload MP4, MOV, or MKV from your device. Files go straight to
                  storage — the API never handles the video bytes.
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Source input */}
          {mode === "url" ? (
            <div className="space-y-1.5">
              <LabelWithTip
                htmlFor="source_url"
                tip="Public link to a VOD, clip, or hosted MP4. Twitch, YouTube, Kick, and direct URLs are supported."
                tipLabel="Video URL help"
              >
                Video URL
              </LabelWithTip>
              <Input
                id="source_url"
                name="source_url"
                type="url"
                placeholder="https://www.twitch.tv/videos/..."
                required={mode === "url"}
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <LabelWithTip
                tip="Drag and drop or browse for a local video. Upload must finish before you can start the job."
                tipLabel="Upload help"
              >
                Upload
              </LabelWithTip>
              <DirectUpload
                currentKey={uploadKey}
                onUploaded={(key) => setUploadKey(key)}
                onCleared={() => setUploadKey(null)}
              />
              <input
                type="hidden"
                name="source_upload_key"
                value={uploadKey ?? ""}
              />
            </div>
          )}

          {/* Settings row */}
          <div className="space-y-2">
            <SectionLegend title="Settings" tip={FORM_SECTION_LEGEND.settings} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5 md:col-span-2">
              <LabelWithTip
                htmlFor="content_profile"
                tip="Tunes highlight detection for your content type — gaming favors motion and chat; podcast favors dialogue peaks."
                tipLabel="Content type help"
              >
                Content type
              </LabelWithTip>
              <Select id="content_profile" name="content_profile" defaultValue="gaming">
                <option value="gaming">Gaming / Twitch</option>
                <option value="irl">IRL / Just Chatting</option>
                <option value="podcast">Podcast / Interview</option>
                <option value="esports">Esports / Casted</option>
                <option value="general">General / Mixed</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <LabelWithTip
                htmlFor="target_clips"
                tip="How many highlight clips to extract from this source (1–20). More clips take longer to render."
                tipLabel="Clip count help"
              >
                Clips
              </LabelWithTip>
              <Input
                id="target_clips"
                name="target_clips"
                type="number"
                defaultValue={5}
                min={1}
                max={20}
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Label htmlFor="reframe_preset">Game preset</Label>
                <HelpTip
                  content={REFRAME_PRESET_TIPS[reframePreset]}
                  label="Game preset help"
                />
              </div>
              <Select
                id="reframe_preset"
                name="reframe_preset"
                value={reframePreset}
                onChange={(e) =>
                  setReframePreset(
                    e.target.value as keyof typeof REFRAME_PRESET_TIPS,
                  )
                }
              >
                <option value="fps_game">FPS</option>
                <option value="moba">MOBA</option>
                <option value="battle_royale">Battle royale</option>
                <option value="irl">IRL / talking head</option>
                <option value="podcast">Podcast</option>
                <option value="auto">Auto-detect</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Label htmlFor="caption_style">Caption style</Label>
                <HelpTip
                  content={CAPTION_STYLE_TIPS[captionStyle]}
                  label="Caption style help"
                />
              </div>
              <Select
                id="caption_style"
                name="caption_style"
                value={captionStyle}
                onChange={(e) =>
                  setCaptionStyle(
                    e.target.value as keyof typeof CAPTION_STYLE_TIPS,
                  )
                }
              >
                <option value="gaming_impact">Gaming impact</option>
                <option value="tiktok_pop">TikTok pop</option>
                <option value="minimal_white">Minimal</option>
                <option value="podcast_clean">Podcast clean</option>
              </Select>
            </div>
            </div>
          </div>

          {/* Error */}
          {state.status === "error" && state.message && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {state.message}
            </div>
          )}

          <SubmitButton mode={mode} uploadReady={!!uploadKey} />
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
    <Button
      type="submit"
      disabled={disabled}
      className="w-full"
      tooltip="Start the pipeline: ingest → transcribe → discover clips → render vertical output."
    >
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
