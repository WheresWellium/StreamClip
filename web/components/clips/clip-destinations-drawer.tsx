"use client";

import { Archive, Calendar, Loader2, Send } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import {
  getDistributionContextAction,
  publishClipAction,
  scheduleClipAction,
} from "@/lib/api/actions/distribution";
import { saveToVaultAction } from "@/lib/api/actions/vault";
import { ProGateModal } from "@/components/distribution/pro-gate-modal";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/form";
import type { ClipOut } from "@/lib/api/types";
import { cn } from "@/lib/utils/format";
import { DISTRIBUTION_SETTINGS_HREF } from "@/lib/distribution/routes";
import { getClientAccessToken } from "@/lib/auth/client-session";

type Tab = "publish" | "schedule" | "vault";

type Props = {
  clip: ClipOut;
  jobId: string;
  open: boolean;
  onClose: () => void;
};

export function ClipDestinationsDrawer({ clip, jobId, open, onClose }: Props) {
  const { push: toast } = useToastSafe();
  const [tab, setTab] = React.useState<Tab>("publish");
  const [saving, setSaving] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [platform, setPlatform] = React.useState("youtube_shorts");
  const [title, setTitle] = React.useState(clip.title || "");
  const [description, setDescription] = React.useState(clip.hook || "");
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [ctx, setCtx] = React.useState<
    Awaited<ReturnType<typeof getDistributionContextAction>> | null
  >(null);
  const [loadingCtx, setLoadingCtx] = React.useState(false);
  const [proGateOpen, setProGateOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setTitle(clip.title || "");
    setDescription(clip.hook || "");
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, clip.title, clip.hook]);

  React.useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingCtx(true);
    void getDistributionContextAction().then((data) => {
      if (!cancelled) {
        setCtx(data);
        const connected = data.platforms.find((p) => p.connected && p.enabled);
        if (connected) setPlatform(connected.id);
      }
      if (!cancelled) setLoadingCtx(false);
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  const connectedPlatforms =
    ctx?.platforms.filter((p) => p.enabled && p.connected) ?? [];
  const canPublish = clip.approval_status === "approved" && ctx?.hasPro;

  async function handleSaveVault() {
    setSaving(true);
    try {
      const result = await saveToVaultAction(clip.id);
      if (result.status === "ok") {
        toast("Saving to Vault", "Your clip will appear in Vault when the copy finishes.");
        onClose();
      } else {
        toast("Save failed", result.message ?? "Could not save to vault");
      }
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (!ctx?.hasPro) {
      setProGateOpen(true);
      return;
    }
    if (!canPublish) return;
    setSubmitting(true);
    try {
      const result = await publishClipAction(clip.id, platform, title, description);
      if (result.status === "ok") {
        toast("Publish queued", "Track progress in Settings → Distribution.");
        onClose();
      } else {
        toast("Publish failed", result.message ?? "Could not publish.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSchedule() {
    if (!ctx?.hasPro) {
      setProGateOpen(true);
      return;
    }
    if (!canPublish || !scheduledAt) return;
    setSubmitting(true);
    try {
      const iso = new Date(scheduledAt).toISOString();
      const result = await scheduleClipAction(
        clip.id,
        platform,
        iso,
        title,
        description,
      );
      if (result.status === "ok") {
        toast("Scheduled", "View the publish queue in Settings → Distribution.");
        onClose();
      } else {
        toast("Schedule failed", result.message ?? "Could not schedule.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/50"
        aria-label="Close destinations"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-labelledby="destinations-title"
        className="fixed right-0 top-0 z-50 h-full w-full max-w-md glossy-surface border-l border-border/60 shadow-xl flex flex-col animate-fade-in"
      >
        <div className="p-4 border-b border-border/60">
          <h2 id="destinations-title" className="text-sm font-medium">
            Clip destinations
          </h2>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
            {clip.title || `Clip ${clip.rank + 1}`}
          </p>
          <div className="flex mt-3 rounded-md border border-border/60 overflow-hidden text-xs">
            {(
              [
                { id: "publish" as const, label: "Publish now", icon: Send },
                { id: "schedule" as const, label: "Schedule", icon: Calendar },
                { id: "vault" as const, label: "Save to Vault", icon: Archive },
              ] as const
            ).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                aria-label={label}
                aria-pressed={tab === id}
                className={cn(
                  "flex-1 flex items-center justify-center gap-1 px-2 py-2 min-h-[44px]",
                  tab === id ? "bg-sky-600/25 text-sky-100" : "text-muted-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          {tab === "vault" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Save a durable copy to your Clip Vault. Vault clips survive job
                cleanup and can be published later.
              </p>
              <Button
                className="w-full"
                disabled={saving || clip.approval_status !== "approved"}
                onClick={handleSaveVault}
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Archive className="h-4 w-4" />
                )}
                Save to Clip Vault
              </Button>
              {clip.approval_status !== "approved" && (
                <p className="text-xs text-amber-400/90">
                  Approve this clip before saving to Vault.
                </p>
              )}
            </div>
          )}

          {(tab === "publish" || tab === "schedule") && (
            <div className="space-y-4">
              {loadingCtx ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : ctx?.loadError ? (
                <div className="space-y-3 text-sm text-destructive" role="alert">
                  <p>{ctx.loadError}</p>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setLoadingCtx(true);
                      void getDistributionContextAction().then((data) => {
                        setCtx(data);
                        setLoadingCtx(false);
                      });
                    }}
                  >
                    Retry
                  </Button>
                </div>
              ) : !getClientAccessToken() ? (
                <div className="space-y-3 text-sm text-muted-foreground">
                  <p>Sign in to publish clips.</p>
                  <Button asChild variant="outline" className="w-full">
                    <Link href="/login">Sign in</Link>
                  </Button>
                </div>
              ) : !ctx?.hasPro ? (
                <div className="space-y-3 text-sm text-muted-foreground">
                  <p>Publishing requires Pro.</p>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => setProGateOpen(true)}
                  >
                    Learn about Pro
                  </Button>
                </div>
              ) : connectedPlatforms.length === 0 ? (
                <div className="space-y-3 text-sm text-muted-foreground">
                  <p>Connect YouTube or TikTok in Distribution before publishing.</p>
                  <Button asChild variant="outline" className="w-full">
                    <Link href={DISTRIBUTION_SETTINGS_HREF}>Open publish queue</Link>
                  </Button>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground" htmlFor="platform">
                      Platform
                    </label>
                    <select
                      id="platform"
                      className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                      value={platform}
                      onChange={(e) => setPlatform(e.target.value)}
                    >
                      {connectedPlatforms.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                    {platform === "tiktok" && (
                      <p className="text-xs text-muted-foreground">
                        TikTok uploads land in your TikTok app inbox — open the
                        notification there to finish posting.
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground" htmlFor="pub-title">
                      Title
                    </label>
                    <Input
                      id="pub-title"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      maxLength={100}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground" htmlFor="pub-desc">
                      Description
                    </label>
                    <textarea
                      id="pub-desc"
                      className="w-full min-h-[80px] rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </div>
                  {tab === "schedule" && (
                    <div className="space-y-2">
                      <label className="text-xs text-muted-foreground" htmlFor="sched-at">
                        Publish at
                      </label>
                      <Input
                        id="sched-at"
                        type="datetime-local"
                        value={scheduledAt}
                        min={new Date(Date.now() - new Date().getTimezoneOffset() * 60_000)
                          .toISOString()
                          .slice(0, 16)}
                        onChange={(e) => setScheduledAt(e.target.value)}
                      />
                    </div>
                  )}
                  {clip.approval_status !== "approved" && (
                    <p className="text-xs text-amber-400/90">
                      Approve this clip before publishing.
                    </p>
                  )}
                  <Button
                    className="w-full"
                    disabled={!canPublish || submitting || (tab === "schedule" && !scheduledAt)}
                    onClick={tab === "publish" ? handlePublish : handleSchedule}
                  >
                    {submitting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : tab === "publish" ? (
                      <Send className="h-4 w-4" />
                    ) : (
                      <Calendar className="h-4 w-4" />
                    )}
                    {tab === "publish" ? "Publish now" : "Schedule publish"}
                  </Button>
                </>
              )}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-border/60">
          <Button variant="outline" className="w-full" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>

      <ProGateModal open={proGateOpen} onClose={() => setProGateOpen(false)} />
    </>
  );
}
