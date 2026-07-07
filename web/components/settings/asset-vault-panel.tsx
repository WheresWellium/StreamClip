"use client";

import { Loader2, Trash2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { createAssetAction, removeAssetAction } from "@/lib/api/actions/assets";
import { useToastSafe } from "@/components/providers/toast-provider";
import { Button } from "@/components/ui/button";
import { Badge, Input, Label } from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { uploadsApi, type OverlayAsset } from "@/lib/api/client";

const ACCEPTED = {
  "image/gif": "gif",
  "image/png": "png",
  "video/mp4": "mp4",
} as const;

const MAX_ASSET_BYTES = 25 * 1024 * 1024;

export function AssetVaultPanel({ assets }: { assets: OverlayAsset[] }) {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [file, setFile] = React.useState<File | null>(null);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [removingId, setRemovingId] = React.useState<string | null>(null);

  const assetType = file ? ACCEPTED[file.type as keyof typeof ACCEPTED] : undefined;

  function pickFile(f: File | null) {
    if (f && !(f.type in ACCEPTED)) {
      toast("Unsupported file", "Use a GIF, PNG, or MP4.");
      return;
    }
    if (f && f.size > MAX_ASSET_BYTES) {
      toast("File too large", "Overlay assets are capped at 25 MB.");
      return;
    }
    setFile(f);
    if (f && !name) setName(f.name.replace(/\.[^.]+$/, ""));
  }

  async function upload() {
    if (!file || !assetType) return;
    if (description.trim().length < 3) {
      toast("Description needed", "Describe the moment this overlay fits — it drives matching.");
      return;
    }
    setBusy(true);
    try {
      const storageKey = await uploadsApi.uploadFile(file);
      const result = await createAssetAction({
        name: name.trim() || file.name,
        asset_type: assetType,
        storage_key: storageKey,
        description: description.trim(),
      });
      if (result.status === "ok") {
        toast("Asset added", "It will be considered for overlays on your next render.");
        setFile(null);
        setName("");
        setDescription("");
        if (fileRef.current) fileRef.current.value = "";
        router.refresh();
      } else {
        toast("Upload failed", result.message ?? "Could not save asset.");
      }
    } catch {
      toast("Upload failed", "Could not upload the file.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setRemovingId(id);
    const result = await removeAssetAction(id);
    setRemovingId(null);
    if (result.status === "ok") {
      router.refresh();
    } else {
      toast("Remove failed", result.message ?? "Could not remove asset.");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload overlay asset</CardTitle>
          <CardDescription>
            GIFs, PNG stickers, or short MP4s. The description is embedded semantically and
            matched against each clip&apos;s hook — write it like the moment it belongs to
            (&quot;unbelievable clutch play, shocked, let&apos;s go&quot;).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="asset-file">File</Label>
            <Input
              id="asset-file"
              ref={fileRef}
              type="file"
              accept=".gif,.png,.mp4"
              disabled={busy}
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="asset-name">Name</Label>
            <Input
              id="asset-name"
              value={name}
              maxLength={255}
              placeholder="Hype airhorn"
              disabled={busy}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="asset-description">Matches moments like…</Label>
            <Input
              id="asset-description"
              value={description}
              placeholder="absolute hype, incredible win, clutch victory"
              disabled={busy}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <Button type="button" disabled={!file || busy} onClick={() => void upload()}>
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <UploadCloud className="h-4 w-4" />
            )}
            {busy ? "Uploading…" : "Add asset"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your assets</CardTitle>
          <CardDescription>
            {assets.length === 0
              ? "Only the built-in starter pack is used until you add your own."
              : `${assets.length} asset${assets.length === 1 ? "" : "s"} available to the overlay engine.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {assets.length === 0 ? (
            <p className="text-sm text-muted-foreground">No custom assets yet.</p>
          ) : (
            <ul className="divide-y divide-white/5">
              {assets.map((asset) => (
                <li key={asset.id} className="flex items-center gap-3 py-2.5">
                  <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                    {asset.asset_type}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{asset.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{asset.description}</p>
                  </div>
                  {asset.is_public ? (
                    <span className="shrink-0 text-[10px] font-mono uppercase text-muted-foreground">
                      built-in
                    </span>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0"
                      disabled={removingId === asset.id}
                      onClick={() => void remove(asset.id)}
                      aria-label={`Remove ${asset.name}`}
                    >
                      {removingId === asset.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
