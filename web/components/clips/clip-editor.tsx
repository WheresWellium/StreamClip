"use client";

import { Loader2, Pencil, RotateCcw, Save, X } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { refreshClipMediaAction, updateClipAction } from "@/lib/api/actions/jobs";
import { SafeZoneOverlay } from "@/components/clips/safe-zone-overlay";
import { TranscriptEditPanel } from "@/components/clips/transcript-edit-panel";
import { TrimTimeline } from "@/components/clips/trim-timeline";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Badge, Input, Label, Progress } from "@/components/ui/form";
import {
  AspectRatioSelect,
  aspectRatioCss,
} from "@/components/jobs/aspect-ratio-select";
import { CreatorOptionCards } from "@/components/jobs/creator-option-cards";
import { useJobProgress } from "@/lib/api/use-job-progress";
import type { ClipOut, TranscriptEdits } from "@/lib/api/types";
import type { AspectRatioOption, MetaOption } from "@/lib/api/meta-types";
import { cn, formatDuration } from "@/lib/utils/format";

type ClipWithOverrides = ClipOut & {
  render_overrides?: Record<string, unknown>;
  kind?: string;
};

type EditorForm = {
  title: string;
  hook: string;
  start: number;
  end: number;
  captionStyle: string;
  reframePreset: string;
  aspectRatio: string;
  overlayEnabled: boolean;
  transcriptEdits: TranscriptEdits;
  wordsPerGroup: number;
  captionPrimaryColor: string;
  captionOutlineColor: string;
  reframePanX: number;
  reframeZoom: number;
};

const DEFAULT_WORDS_PER_GROUP = 3;
const DEFAULT_CAPTION_PRIMARY = "#FFFFFF";
const DEFAULT_CAPTION_OUTLINE = "#000000";
const DEFAULT_REFRAME_PAN_X = 0.5;
const DEFAULT_REFRAME_ZOOM = 1.0;

/** ASS PrimaryColour is &HAABBGGRR — mirror core/captions.py defaults for honest samples. */
const STYLE_COLOR_DEFAULTS: Record<string, { primary: string; outline: string }> = {
  gaming_impact: { primary: "#FFFFFF", outline: "#000000" },
  tiktok_pop: { primary: "#00FFFF", outline: "#000000" },
  minimal_white: { primary: "#FFFFFF", outline: "#000000" },
  podcast_clean: { primary: "#FFFFFF", outline: "#333333" },
  shorts_bold: { primary: "#FFFF00", outline: "#000000" },
  karaoke_highlight: { primary: "#FFFFFF", outline: "#000000" },
  accessibility_clean: { primary: "#FFFFFF", outline: "#000000" },
};

function styleColorDefaults(styleId: string): { primary: string; outline: string } {
  return (
    STYLE_COLOR_DEFAULTS[styleId] ?? {
      primary: DEFAULT_CAPTION_PRIMARY,
      outline: DEFAULT_CAPTION_OUTLINE,
    }
  );
}

function readHexColor(value: unknown, fallback: string): string {
  if (typeof value === "string" && /^#[0-9A-Fa-f]{6}$/.test(value)) {
    return value.toUpperCase();
  }
  return fallback;
}

function readBoundedNumber(
  value: unknown,
  fallback: number,
  min: number,
  max: number,
): number {
  if (typeof value !== "number" || Number.isNaN(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

function readTranscriptEdits(overrides: Record<string, unknown>): TranscriptEdits {
  const raw = overrides.transcript_edits;
  if (!raw || typeof raw !== "object") return {};
  const result: TranscriptEdits = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value === "string") result[key] = value;
  }
  return result;
}

function editsEqual(a: TranscriptEdits, b: TranscriptEdits): boolean {
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every((k) => a[k] === b[k]);
}

function dirtyPreviewHint(
  before: EditorForm,
  after: EditorForm,
  isSplice: boolean,
): string {
  const parts: string[] = [];
  if (!isSplice) {
    if (
      Math.abs(before.start - after.start) >= 0.05 ||
      Math.abs(before.end - after.end) >= 0.05
    ) {
      parts.push("trim");
    }
    if (
      before.captionPrimaryColor !== after.captionPrimaryColor ||
      before.captionOutlineColor !== after.captionOutlineColor ||
      before.captionStyle !== after.captionStyle ||
      before.wordsPerGroup !== after.wordsPerGroup ||
      !editsEqual(before.transcriptEdits, after.transcriptEdits)
    ) {
      parts.push("captions");
    }
    const panZoomDirty =
      Math.abs(before.reframePanX - after.reframePanX) >= 0.001 ||
      Math.abs(before.reframeZoom - after.reframeZoom) >= 0.001;
    if (before.reframePreset !== after.reframePreset || panZoomDirty) {
      parts.push("reframe");
    }
    if (before.aspectRatio !== after.aspectRatio) parts.push("aspect");
    if (before.overlayEnabled !== after.overlayEnabled) parts.push("overlays");
    // Pan/zoom already CSS-preview; don't claim the video is stale for that alone.
    if (
      parts.length === 1 &&
      parts[0] === "reframe" &&
      before.reframePreset === after.reframePreset &&
      panZoomDirty
    ) {
      return "Preview shows pan/zoom nudge — save to burn into the clip";
    }
  }
  if (before.title !== after.title || before.hook !== after.hook) {
    parts.push("title");
  }
  const label = parts.length ? parts.slice(0, 3).join(" / ") : "edits";
  return `Showing last render — save to apply ${label}`;
}

type Props = {
  clip: ClipOut;
  jobId: string;
  sourceDurationSecs?: number | null;
  captionStyleOptions: MetaOption[];
  reframePresetOptions: MetaOption[];
  jobAspectRatio?: string | null;
  aspectRatioCatalog?: AspectRatioOption[];
  disabled?: boolean;
};

const MIN_CLIP_SECS = 3;

function readOverrides(clip: ClipWithOverrides) {
  return clip.render_overrides ?? {};
}

function formFromClip(
  clip: ClipWithOverrides,
  captionStyleOptions: MetaOption[],
  reframePresetOptions: MetaOption[],
  jobAspectRatio?: string | null,
): EditorForm {
  const overrides = readOverrides(clip);
  const captionIds = captionStyleOptions.map((o) => o.id);
  const presetIds = reframePresetOptions.map((o) => o.id);
  const captionStyle =
    typeof overrides.caption_style === "string" &&
    captionIds.includes(overrides.caption_style)
      ? overrides.caption_style
      : captionIds[0] ?? "gaming_impact";
  const styleColors = styleColorDefaults(captionStyle);
  return {
    title: clip.title || `Clip ${clip.rank + 1}`,
    hook: clip.hook || "",
    start: clip.start_secs,
    end: clip.end_secs,
    captionStyle,
    reframePreset:
      typeof overrides.reframe_preset === "string" &&
      presetIds.includes(overrides.reframe_preset)
        ? overrides.reframe_preset
        : presetIds[0] ?? "fps_game",
    aspectRatio:
      typeof overrides.aspect_ratio === "string"
        ? overrides.aspect_ratio
        : jobAspectRatio || "9:16",
    overlayEnabled:
      typeof overrides.overlay_enabled === "boolean"
        ? overrides.overlay_enabled
        : true,
    transcriptEdits: readTranscriptEdits(overrides),
    wordsPerGroup:
      typeof overrides.caption_words_per_group === "number" &&
      overrides.caption_words_per_group >= 1 &&
      overrides.caption_words_per_group <= 8
        ? overrides.caption_words_per_group
        : DEFAULT_WORDS_PER_GROUP,
    captionPrimaryColor: readHexColor(
      overrides.caption_primary_color,
      styleColors.primary,
    ),
    captionOutlineColor: readHexColor(
      overrides.caption_outline_color,
      styleColors.outline,
    ),
    reframePanX: readBoundedNumber(
      overrides.reframe_pan_x,
      DEFAULT_REFRAME_PAN_X,
      0,
      1,
    ),
    reframeZoom: readBoundedNumber(
      overrides.reframe_zoom,
      DEFAULT_REFRAME_ZOOM,
      1,
      1.4,
    ),
  };
}

function formsEqual(a: EditorForm, b: EditorForm): boolean {
  return (
    a.title === b.title &&
    a.hook === b.hook &&
    Math.abs(a.start - b.start) < 0.05 &&
    Math.abs(a.end - b.end) < 0.05 &&
    a.captionStyle === b.captionStyle &&
    a.reframePreset === b.reframePreset &&
    a.aspectRatio === b.aspectRatio &&
    a.overlayEnabled === b.overlayEnabled &&
    editsEqual(a.transcriptEdits, b.transcriptEdits) &&
    a.wordsPerGroup === b.wordsPerGroup &&
    a.captionPrimaryColor === b.captionPrimaryColor &&
    a.captionOutlineColor === b.captionOutlineColor &&
    Math.abs(a.reframePanX - b.reframePanX) < 0.001 &&
    Math.abs(a.reframeZoom - b.reframeZoom) < 0.001
  );
}

/** True when save must re-run process_clip (trim/style/captions). Title/hook alone do not. */
function needsRerender(before: EditorForm, after: EditorForm): boolean {
  return (
    Math.abs(before.start - after.start) >= 0.05 ||
    Math.abs(before.end - after.end) >= 0.05 ||
    before.captionStyle !== after.captionStyle ||
    before.reframePreset !== after.reframePreset ||
    before.aspectRatio !== after.aspectRatio ||
    before.overlayEnabled !== after.overlayEnabled ||
    !editsEqual(before.transcriptEdits, after.transcriptEdits) ||
    before.wordsPerGroup !== after.wordsPerGroup ||
    before.captionPrimaryColor !== after.captionPrimaryColor ||
    before.captionOutlineColor !== after.captionOutlineColor ||
    Math.abs(before.reframePanX - after.reframePanX) >= 0.001 ||
    Math.abs(before.reframeZoom - after.reframeZoom) >= 0.001
  );
}

const PANEL_WIDTH_MIN = 360;
const PANEL_WIDTH_MAX = 720;
const PANEL_WIDTH_DEFAULT = 420;

function validateForm(
  form: EditorForm,
  sourceDurationSecs?: number | null,
): string | null {
  if (!form.title.trim()) return "Title is required.";
  if (form.end <= form.start) return "End time must be after start time.";
  if (form.end - form.start < MIN_CLIP_SECS) {
    return `Clip must be at least ${MIN_CLIP_SECS} seconds.`;
  }
  if (form.start < 0) return "Start time cannot be negative.";
  if (
    sourceDurationSecs != null &&
    sourceDurationSecs > 0 &&
    form.end > sourceDurationSecs + 0.5
  ) {
    return `End time exceeds source duration (${formatDuration(sourceDurationSecs)}).`;
  }
  return null;
}

export function ClipEditor({
  clip,
  jobId,
  sourceDurationSecs,
  captionStyleOptions,
  reframePresetOptions,
  jobAspectRatio,
  aspectRatioCatalog,
  disabled = false,
}: Props) {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const clipExt = clip as ClipWithOverrides;

  const isSplice = clipExt.kind === "splice";
  const [open, setOpen] = React.useState(false);
  const [pending, setPending] = React.useState(false);
  const [rerendering, setRerendering] = React.useState(
    () => clip.status === "processing",
  );
  const [error, setError] = React.useState<string | null>(null);
  const [panelWidth, setPanelWidth] = React.useState(PANEL_WIDTH_DEFAULT);
  const resizeDragRef = React.useRef<{ startX: number; startW: number } | null>(
    null,
  );
  const prevClipStatusRef = React.useRef(clip.status);
  const [previewDownloadUrl, setPreviewDownloadUrl] = React.useState(clip.download_url ?? null);
  const [previewThumbnailUrl, setPreviewThumbnailUrl] = React.useState(clip.thumbnail_url ?? null);
  const previewRetriedRef = React.useRef(false);

  React.useEffect(() => {
    setPreviewDownloadUrl(clip.download_url ?? null);
    setPreviewThumbnailUrl(clip.thumbnail_url ?? null);
    previewRetriedRef.current = false;
  }, [clip.download_url, clip.thumbnail_url]);

  async function onPreviewMediaError() {
    if (previewRetriedRef.current) return;
    previewRetriedRef.current = true;
    const result = await refreshClipMediaAction(jobId, clip.id);
    if (result.ok) {
      setPreviewDownloadUrl(result.download_url);
      setPreviewThumbnailUrl(result.thumbnail_url);
    } else {
      toast("Couldn't refresh preview", result.message ?? "The link may have expired.");
    }
  }
  const [showSafeZones, setShowSafeZones] = React.useState(false);

  const savedRef = React.useRef(
    formFromClip(clipExt, captionStyleOptions, reframePresetOptions, jobAspectRatio),
  );
  const [form, setForm] = React.useState<EditorForm>(savedRef.current);

  const jobProgress = useJobProgress(jobId, { enabled: rerendering });

  const isProcessing = clip.status === "processing" || rerendering;
  const isDirty = !formsEqual(form, savedRef.current);
  const willRerender = !isSplice && needsRerender(savedRef.current, form);
  const validationError = isSplice
    ? form.title.trim()
      ? null
      : "Title is required."
    : validateForm(form, sourceDurationSecs);
  const canSave = isDirty && !validationError && !pending && !isProcessing;

  React.useEffect(() => {
    function onMove(ev: PointerEvent) {
      const drag = resizeDragRef.current;
      if (!drag) return;
      const next = Math.min(
        PANEL_WIDTH_MAX,
        Math.max(PANEL_WIDTH_MIN, drag.startW + (drag.startX - ev.clientX)),
      );
      setPanelWidth(next);
    }
    function onUp() {
      resizeDragRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  // Toast + clear only on clip.status transitions — job SSE stays "done"
  // after finalise, so it must not fake a successful re-render.
  React.useEffect(() => {
    const prev = prevClipStatusRef.current;
    prevClipStatusRef.current = clip.status;
    if (clip.status === "processing") {
      setRerendering(true);
      return;
    }
    if (prev === "processing" && clip.status === "done") {
      setRerendering(false);
      toast("Clip re-rendered", "Your edits are now live.");
      return;
    }
    if (prev === "processing" && clip.status === "error") {
      setRerendering(false);
      toast(
        "Re-render failed",
        "Open Edit clip and try Save again, or Regenerate this clip.",
      );
      return;
    }
    if (clip.status === "done" || clip.status === "error") {
      setRerendering(false);
    }
  }, [clip.status, toast]);

  // Soft-refresh while a clip re-render is in flight so status/media update.
  React.useEffect(() => {
    if (!rerendering) return;
    const id = window.setInterval(() => router.refresh(), 2500);
    return () => window.clearInterval(id);
  }, [rerendering, router]);

  React.useEffect(() => {
    if (!open) return;
    const next = formFromClip(
      clip as ClipWithOverrides,
      captionStyleOptions,
      reframePresetOptions,
      jobAspectRatio,
    );
    savedRef.current = next;
    setForm(next);
    setError(null);
  }, [
    clip.id,
    clip.status,
    clip.title,
    clip.hook,
    clip.start_secs,
    clip.end_secs,
    open,
    captionStyleOptions,
    reframePresetOptions,
    jobAspectRatio,
    clip,
  ]);

  function patch<K extends keyof EditorForm>(key: K, value: EditorForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setError(null);
  }

  function handleDiscard(opts?: { confirmIfDirty?: boolean }) {
    if (opts?.confirmIfDirty && isDirty) {
      const ok = window.confirm("Discard unsaved edits?");
      if (!ok) return;
    }
    setForm(savedRef.current);
    setError(null);
    setOpen(false);
  }

  React.useEffect(() => {
    if (!open) return;
    function onKey(ev: KeyboardEvent) {
      if (ev.key !== "Escape") return;
      ev.preventDefault();
      handleDiscard({ confirmIfDirty: true });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // handleDiscard closes over latest isDirty/form via this effect's deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional open/dirty gate
  }, [open, isDirty]);

  async function handleSave() {
    const err = isSplice
      ? form.title.trim()
        ? null
        : "Title is required."
      : validateForm(form, sourceDurationSecs);
    if (err) {
      setError(err);
      return;
    }
    const rerender = willRerender;
    setPending(true);
    setError(null);
    const saved = savedRef.current;
    const payload: Record<string, unknown> = {
      title: form.title.trim(),
      hook: form.hook.trim(),
      start_secs: form.start,
      end_secs: form.end,
      caption_style: form.captionStyle,
      reframe_preset: form.reframePreset,
      aspect_ratio: form.aspectRatio,
      overlay_enabled: form.overlayEnabled,
      transcript_edits: form.transcriptEdits,
      caption_words_per_group: form.wordsPerGroup,
      rerender,
    };
    // Only persist color/pan/zoom when dirty so metadata-only saves do not
    // lock editor defaults (#FFFFFF / 0.5 / 1.0) over style presets.
    if (saved.captionPrimaryColor !== form.captionPrimaryColor) {
      payload.caption_primary_color = form.captionPrimaryColor;
    }
    if (saved.captionOutlineColor !== form.captionOutlineColor) {
      payload.caption_outline_color = form.captionOutlineColor;
    }
    if (Math.abs(saved.reframePanX - form.reframePanX) >= 0.001) {
      payload.reframe_pan_x = form.reframePanX;
    }
    if (Math.abs(saved.reframeZoom - form.reframeZoom) >= 0.001) {
      payload.reframe_zoom = form.reframeZoom;
    }
    const result = await updateClipAction(jobId, clip.id, payload);
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "Could not save changes");
      toast("Save failed", result.message ?? "Could not update clip.");
      return;
    }
    savedRef.current = { ...form };
    setOpen(false);
    if (rerender) {
      setRerendering(true);
      toast("Re-render queued", "Processing your clip edits…");
    } else {
      toast("Saved", "Saved — no re-render needed.");
    }
    router.refresh();
  }

  const trimMax =
    sourceDurationSecs && sourceDurationSecs > 0
      ? sourceDurationSecs
      : Math.max(form.end + 60, 300);
  const liveStage =
    "lastEvent" in jobProgress ? jobProgress.lastEvent?.stage ?? null : null;
  const liveMessage =
    "lastEvent" in jobProgress ? jobProgress.lastEvent?.message ?? null : null;

  return (
    <>
      <div className="pt-2 border-t border-border/40 space-y-1.5">
        {isProcessing && (
          <Badge className="w-full justify-center border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300">
            <Loader2 className="h-3 w-3 animate-spin mr-1" />
            Re-rendering…
          </Badge>
        )}
        {isDirty && !isProcessing && open === false && (
          <Badge className="w-full justify-center border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200">
            Unsaved edits
          </Badge>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-full border-sky-500/20 hover:border-sky-500/40 hover:bg-sky-500/5"
          disabled={disabled || isProcessing}
          onClick={() => setOpen(true)}
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit clip
        </Button>
        {rerendering && liveMessage && (
          <p className="text-[10px] text-muted-foreground text-center truncate">
            {liveStage ? `${liveStage}: ` : ""}
            {liveMessage}
          </p>
        )}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          role="dialog"
          aria-modal="true"
          aria-label="Edit clip"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            aria-label="Close editor"
            onClick={() => handleDiscard({ confirmIfDirty: true })}
          />
          <div
            className="relative z-10 flex h-full flex-col border-l border-border/60 bg-card shadow-2xl animate-in slide-in-from-right duration-200"
            style={{ width: `min(100vw, ${panelWidth}px)` }}
          >
            <button
              type="button"
              aria-label="Resize editor panel"
              title="Drag to resize"
              className="absolute left-0 top-0 z-20 h-full w-1.5 -translate-x-1/2 cursor-ew-resize bg-transparent hover:bg-sky-500/40"
              onPointerDown={(ev) => {
                ev.preventDefault();
                resizeDragRef.current = {
                  startX: ev.clientX,
                  startW: panelWidth,
                };
                document.body.style.cursor = "ew-resize";
                document.body.style.userSelect = "none";
              }}
            />
            <header className="flex items-center justify-between gap-3 border-b border-border/60 bg-gradient-to-r from-muted/80 to-sky-500/5 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  Edit clip #{clip.rank + 1}
                  {isSplice ? " (merged)" : ""}
                </p>
                <p className="text-xs text-muted-foreground">
                  {isSplice
                    ? "Rename merged clip (video edits unavailable)"
                    : "Trim, restyle, and re-render"}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="shrink-0"
                onClick={() => handleDiscard({ confirmIfDirty: true })}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
              {/* Preview */}
              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-muted-foreground uppercase tracking-wide">
                    Preview
                  </Label>
                  <button
                    type="button"
                    onClick={() => setShowSafeZones((v) => !v)}
                    className={cn(
                      "text-[10px] px-2 py-0.5 rounded-full border transition-colors",
                      showSafeZones
                        ? "border-red-400/60 bg-red-400/10 text-red-300"
                        : "border-border/60 text-muted-foreground hover:text-foreground",
                    )}
                    aria-pressed={showSafeZones}
                  >
                    Safe zones
                  </button>
                </div>
                <div
                  className="relative mx-auto rounded-lg overflow-hidden bg-black border border-border/60"
                  style={{
                    aspectRatio: aspectRatioCss(form.aspectRatio),
                    maxHeight: 220,
                    maxWidth: "100%",
                  }}
                >
                  {previewDownloadUrl ? (
                    <video
                      key={previewDownloadUrl}
                      src={previewDownloadUrl}
                      controls
                      playsInline
                      className="absolute inset-0 w-full h-full object-contain"
                      style={{
                        transform: `scale(${form.reframeZoom}) translateX(${(0.5 - form.reframePanX) * 14}%)`,
                        transformOrigin: "center center",
                        transition: "transform 80ms linear",
                      }}
                      onError={onPreviewMediaError}
                    />
                  ) : previewThumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={previewThumbnailUrl}
                      alt=""
                      className="absolute inset-0 w-full h-full object-cover opacity-80"
                      style={{
                        transform: `scale(${form.reframeZoom}) translateX(${(0.5 - form.reframePanX) * 14}%)`,
                        transformOrigin: "center center",
                        transition: "transform 80ms linear",
                      }}
                      onError={onPreviewMediaError}
                    />
                  ) : (
                    <div className="absolute inset-0 grid place-items-center text-xs text-muted-foreground">
                      No preview yet
                    </div>
                  )}
                  <SafeZoneOverlay visible={showSafeZones} />
                  {isDirty && (
                    <div className="absolute bottom-0 inset-x-0 bg-amber-500/90 text-amber-950 text-[10px] px-2 py-1 text-center">
                      {dirtyPreviewHint(savedRef.current, form, isSplice)}
                      {!isSplice
                        ? ` (${formatDuration(form.end - form.start)})`
                        : ""}
                    </div>
                  )}
                </div>
              </section>

              {/* Trim timeline (not for merged/splice clips) */}
              {!isSplice && <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Trim boundaries</Label>
                  <span className="text-xs font-mono text-muted-foreground">
                    {formatDuration(form.end - form.start)}
                  </span>
                </div>
                <TrimTimeline
                  jobId={jobId}
                  maxSecs={trimMax}
                  start={form.start}
                  end={form.end}
                  minClipSecs={MIN_CLIP_SECS}
                  disabled={isProcessing}
                  onChange={(s, e) => {
                    setForm((prev) => ({
                      ...prev,
                      start: Number(s.toFixed(2)),
                      end: Number(e.toFixed(2)),
                    }));
                    setError(null);
                  }}
                />
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor={`start-${clip.id}`} className="text-xs">
                      Start (s)
                    </Label>
                    <Input
                      id={`start-${clip.id}`}
                      type="number"
                      step="0.1"
                      min={0}
                      max={form.end - MIN_CLIP_SECS}
                      value={Number(form.start.toFixed(2))}
                      onChange={(e) => patch("start", Number(e.target.value))}
                      className="h-8 text-xs font-mono"
                    />
                    <input
                      type="range"
                      min={0}
                      max={Math.max(form.end - MIN_CLIP_SECS, 0)}
                      step={0.1}
                      value={form.start}
                      onChange={(e) => patch("start", Number(e.target.value))}
                      className="w-full accent-sky-500"
                      aria-label="Start time slider"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor={`end-${clip.id}`} className="text-xs">
                      End (s)
                    </Label>
                    <Input
                      id={`end-${clip.id}`}
                      type="number"
                      step="0.1"
                      min={form.start + MIN_CLIP_SECS}
                      max={trimMax}
                      value={Number(form.end.toFixed(2))}
                      onChange={(e) => patch("end", Number(e.target.value))}
                      className="h-8 text-xs font-mono"
                    />
                    <input
                      type="range"
                      min={form.start + MIN_CLIP_SECS}
                      max={trimMax}
                      step={0.1}
                      value={form.end}
                      onChange={(e) => patch("end", Number(e.target.value))}
                      className="w-full accent-sky-500"
                      aria-label="End time slider"
                    />
                  </div>
                </div>
              </section>}

              {/* Title & hook */}
              <section className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor={`title-${clip.id}`}>Title</Label>
                  <Input
                    id={`title-${clip.id}`}
                    value={form.title}
                    onChange={(e) => patch("title", e.target.value)}
                    maxLength={200}
                    className="h-9"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`hook-${clip.id}`}>Hook text</Label>
                  <textarea
                    id={`hook-${clip.id}`}
                    value={form.hook}
                    onChange={(e) => patch("hook", e.target.value)}
                    maxLength={500}
                    rows={3}
                    className={cn(
                      "flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                      "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                    )}
                  />
                </div>
              </section>

              {!isSplice && (
                <>
              {/* Transcript & captions */}
              <section className="space-y-2">
                <Label className="text-xs text-muted-foreground uppercase tracking-wide">
                  Caption words
                </Label>
                <TranscriptEditPanel
                  jobId={jobId}
                  clipId={clip.id}
                  edits={form.transcriptEdits}
                  onChange={(edits) => patch("transcriptEdits", edits)}
                />
              </section>

              {/* Style */}
              <section className="space-y-4">
                <AspectRatioSelect
                  value={form.aspectRatio}
                  onChange={(id) => patch("aspectRatio", id)}
                  options={aspectRatioCatalog}
                  compact
                />
                <CreatorOptionCards
                  title="Caption style"
                  options={captionStyleOptions}
                  value={form.captionStyle}
                  onChange={(id) => {
                    setForm((prev) => {
                      const oldDefaults = styleColorDefaults(prev.captionStyle);
                      const atStyleDefault =
                        prev.captionPrimaryColor === oldDefaults.primary &&
                        prev.captionOutlineColor === oldDefaults.outline;
                      const nextDefaults = styleColorDefaults(id);
                      return {
                        ...prev,
                        captionStyle: id,
                        ...(atStyleDefault
                          ? {
                              captionPrimaryColor: nextDefaults.primary,
                              captionOutlineColor: nextDefaults.outline,
                            }
                          : {}),
                      };
                    });
                    setError(null);
                  }}
                  columns={1}
                />
                <CreatorOptionCards
                  title="Reframe preset"
                  tip="Controls subject tracking and crop behavior for the chosen aspect ratio."
                  options={reframePresetOptions}
                  value={form.reframePreset}
                  onChange={(id) => patch("reframePreset", id)}
                  columns={1}
                  showAspectBadge
                  aspectRatioId={form.aspectRatio}
                  aspectRatioCatalog={aspectRatioCatalog}
                />
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Label htmlFor={`wpg-${clip.id}`} className="text-xs">
                      Caption words per group
                    </Label>
                    <span className="text-xs font-mono text-muted-foreground">
                      {form.wordsPerGroup}
                    </span>
                  </div>
                  <input
                    id={`wpg-${clip.id}`}
                    type="range"
                    min={1}
                    max={8}
                    step={1}
                    value={form.wordsPerGroup}
                    onChange={(e) =>
                      patch("wordsPerGroup", Number(e.target.value))
                    }
                    className="w-full accent-sky-500"
                    aria-label="Caption words per group"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Fewer words = punchier captions; more words = calmer pacing.
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label className="text-xs text-muted-foreground uppercase tracking-wide">
                      Caption colors
                    </Label>
                    <button
                      type="button"
                      className="text-[10px] text-sky-400 hover:underline"
                      onClick={() => {
                        const defaults = styleColorDefaults(form.captionStyle);
                        setForm((prev) => ({
                          ...prev,
                          captionPrimaryColor: defaults.primary,
                          captionOutlineColor: defaults.outline,
                        }));
                        setError(null);
                      }}
                    >
                      Reset to style
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label htmlFor={`cap-primary-${clip.id}`} className="text-xs">
                        Fill
                      </Label>
                      <div className="flex items-center gap-2">
                        <input
                          id={`cap-primary-${clip.id}`}
                          type="color"
                          value={form.captionPrimaryColor}
                          onChange={(e) =>
                            patch(
                              "captionPrimaryColor",
                              e.target.value.toUpperCase(),
                            )
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-input bg-background"
                          aria-label="Caption fill color"
                        />
                        <span className="text-xs font-mono text-muted-foreground">
                          {form.captionPrimaryColor}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor={`cap-outline-${clip.id}`} className="text-xs">
                        Outline
                      </Label>
                      <div className="flex items-center gap-2">
                        <input
                          id={`cap-outline-${clip.id}`}
                          type="color"
                          value={form.captionOutlineColor}
                          onChange={(e) =>
                            patch(
                              "captionOutlineColor",
                              e.target.value.toUpperCase(),
                            )
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-input bg-background"
                          aria-label="Caption outline color"
                        />
                        <span className="text-xs font-mono text-muted-foreground">
                          {form.captionOutlineColor}
                        </span>
                      </div>
                    </div>
                  </div>
                  <p
                    className="rounded-md border border-border/50 bg-black px-3 py-2 text-center text-sm font-semibold uppercase tracking-wide"
                    style={{
                      color: form.captionPrimaryColor,
                      textShadow: `
                        -2px -2px 0 ${form.captionOutlineColor},
                         2px -2px 0 ${form.captionOutlineColor},
                        -2px  2px 0 ${form.captionOutlineColor},
                         2px  2px 0 ${form.captionOutlineColor}
                      `,
                    }}
                  >
                    Sample caption
                  </p>
                </div>
                <div className="space-y-3">
                  <Label className="text-xs text-muted-foreground uppercase tracking-wide">
                    Reframe nudge
                  </Label>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <Label htmlFor={`pan-${clip.id}`} className="text-xs">
                        Pan
                      </Label>
                      <span className="text-xs font-mono text-muted-foreground">
                        {form.reframePanX.toFixed(2)}
                      </span>
                    </div>
                    <input
                      id={`pan-${clip.id}`}
                      type="range"
                      min={0}
                      max={1}
                      step={0.01}
                      value={form.reframePanX}
                      onChange={(e) =>
                        patch("reframePanX", Number(e.target.value))
                      }
                      className="w-full accent-sky-500"
                      aria-label="Reframe horizontal pan"
                    />
                    <p className="text-[10px] text-muted-foreground">
                      0 = left · 0.5 = center · 1 = right
                    </p>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <Label htmlFor={`zoom-${clip.id}`} className="text-xs">
                        Zoom
                      </Label>
                      <span className="text-xs font-mono text-muted-foreground">
                        {form.reframeZoom.toFixed(2)}×
                      </span>
                    </div>
                    <input
                      id={`zoom-${clip.id}`}
                      type="range"
                      min={1}
                      max={1.4}
                      step={0.01}
                      value={form.reframeZoom}
                      onChange={(e) =>
                        patch("reframeZoom", Number(e.target.value))
                      }
                      className="w-full accent-sky-500"
                      aria-label="Reframe zoom"
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.overlayEnabled}
                    onChange={(e) => patch("overlayEnabled", e.target.checked)}
                    className="accent-sky-500"
                  />
                  Meme overlays
                </label>
              </section>
                </>
              )}

              {(error || validationError) && (
                <p className="text-xs text-destructive" role="alert">
                  {error ?? validationError}
                </p>
              )}

              {isDirty && !validationError && (
                <div className="rounded-md border border-sky-500/20 bg-sky-500/5 px-3 py-2 text-xs text-muted-foreground space-y-1">
                  <p className="font-medium text-foreground">Pending changes</p>
                  <ChangeSummary before={savedRef.current} after={form} />
                </div>
              )}
            </div>

            <footer className="border-t border-border/60 bg-muted/30 px-4 py-3 flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                disabled={pending}
                onClick={() => handleDiscard()}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Discard
              </Button>
              <Button
                type="button"
                className="flex-1 bg-sky-600 hover:bg-sky-700 text-white"
                disabled={!canSave}
                onClick={handleSave}
              >
                {pending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                {willRerender ? "Save & re-render" : "Save"}
              </Button>
            </footer>

            {rerendering && jobProgress.status === "open" && jobProgress.lastEvent && (
              <div className="px-4 pb-3">
                <Progress value={jobProgress.lastEvent.progress} />
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function ChangeSummary({
  before,
  after,
}: {
  before: EditorForm;
  after: EditorForm;
}) {
  const lines: string[] = [];
  if (before.title !== after.title) {
    lines.push(`Title → "${after.title}"`);
  }
  if (before.hook !== after.hook) {
    lines.push("Hook text updated");
  }
  if (
    Math.abs(before.start - after.start) >= 0.05 ||
    Math.abs(before.end - after.end) >= 0.05
  ) {
    lines.push(
      `Trim ${after.start.toFixed(1)}s – ${after.end.toFixed(1)}s (${formatDuration(after.end - after.start)})`,
    );
  }
  if (before.captionStyle !== after.captionStyle) {
    lines.push(`Captions → ${after.captionStyle.replace(/_/g, " ")}`);
  }
  if (before.reframePreset !== after.reframePreset) {
    lines.push(`Reframe → ${after.reframePreset.replace(/_/g, " ")}`);
  }
  if (before.aspectRatio !== after.aspectRatio) {
    lines.push(`Aspect ratio → ${after.aspectRatio}`);
  }
  if (before.overlayEnabled !== after.overlayEnabled) {
    lines.push(after.overlayEnabled ? "Overlays on" : "Overlays off");
  }
  if (!editsEqual(before.transcriptEdits, after.transcriptEdits)) {
    const count = Object.keys(after.transcriptEdits).length;
    lines.push(
      count === 0
        ? "Caption edits cleared"
        : `${count} caption word${count === 1 ? "" : "s"} edited`,
    );
  }
  if (before.wordsPerGroup !== after.wordsPerGroup) {
    lines.push(`Words per group → ${after.wordsPerGroup}`);
  }
  if (
    before.captionPrimaryColor !== after.captionPrimaryColor ||
    before.captionOutlineColor !== after.captionOutlineColor
  ) {
    lines.push(
      `Caption colors → ${after.captionPrimaryColor} / ${after.captionOutlineColor}`,
    );
  }
  if (Math.abs(before.reframePanX - after.reframePanX) >= 0.001) {
    lines.push(`Pan → ${after.reframePanX.toFixed(2)}`);
  }
  if (Math.abs(before.reframeZoom - after.reframeZoom) >= 0.001) {
    lines.push(`Zoom → ${after.reframeZoom.toFixed(2)}×`);
  }
  if (lines.length === 0) return null;
  return (
    <ul className="list-disc list-inside space-y-0.5">
      {lines.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}
