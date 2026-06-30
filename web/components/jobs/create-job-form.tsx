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
import { DirectUpload } from "@/components/upload/direct-upload";

const INITIAL_STATE: CreateJobActionState = { status: "idle" };

export function CreateJobForm() {
  const [state, formAction] = React.useActionState(
    createJobAction,
    INITIAL_STATE,
  );

  const [mode, setMode] = React.useState<"url" | "upload">("url");
  const [uploadKey, setUploadKey] = React.useState<string | null>(null);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          New clip job
        </CardTitle>
        <CardDescription>
          Paste a Twitch/YouTube URL or upload a video file. We'll handle the
          rest.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="space-y-5">
          {/* Source mode toggle */}
          <div className="flex gap-1 p-1 rounded-md bg-secondary/60 w-fit">
            <button
              type="button"
              onClick={() => setMode("url")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mode === "url"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground"
              }`}
            >
              URL
            </button>
            <button
              type="button"
              onClick={() => setMode("upload")}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mode === "upload"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground"
              }`}
            >
              Upload
            </button>
          </div>

          {/* Source input */}
          {mode === "url" ? (
            <div className="space-y-1.5">
              <Label htmlFor="source_url">Video URL</Label>
              <Input
                id="source_url"
                name="source_url"
                type="url"
                placeholder="https://www.twitch.tv/videos/..."
                required={mode === "url"}
              />
              <p className="text-xs text-muted-foreground">
                Twitch VOD, YouTube, Kick, or direct .mp4 URL
              </p>
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label>Upload</Label>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="target_clips">Clips</Label>
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
              <Label htmlFor="reframe_preset">Game preset</Label>
              <Select
                id="reframe_preset"
                name="reframe_preset"
                defaultValue="fps_game"
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
              <Label htmlFor="caption_style">Caption style</Label>
              <Select
                id="caption_style"
                name="caption_style"
                defaultValue="gaming_impact"
              >
                <option value="gaming_impact">Gaming impact</option>
                <option value="tiktok_pop">TikTok pop</option>
                <option value="minimal_white">Minimal</option>
                <option value="podcast_clean">Podcast clean</option>
              </Select>
            </div>
          </div>

          {/* Virality slider */}
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="min_virality_score">Minimum virality score</Label>
              <ViralityValue />
            </div>
            <input
              id="min_virality_score"
              name="min_virality_score"
              type="range"
              min={0}
              max={100}
              defaultValue={55}
              className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
            />
            <p className="text-xs text-muted-foreground">
              Higher = fewer, sharper clips. Lower = more candidates considered.
            </p>
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

function ViralityValue() {
  const [value, setValue] = React.useState(55);
  React.useEffect(() => {
    const input = document.getElementById(
      "min_virality_score",
    ) as HTMLInputElement | null;
    if (!input) return;
    const handler = () => setValue(Number(input.value));
    input.addEventListener("input", handler);
    return () => input.removeEventListener("input", handler);
  }, []);
  return (
    <span className="text-xs font-mono text-muted-foreground">{value}</span>
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
    <Button type="submit" disabled={disabled} className="w-full">
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
