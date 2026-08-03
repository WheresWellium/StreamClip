"use client";

import * as React from "react";

import { removeVaultClipAction, renameVaultClipAction } from "@/lib/api/actions/vault";
import { useToastSafe } from "@/components/providers/toast-provider";
import { VaultClipGrid } from "@/components/vault/vault-clip-grid";
import { VaultClipListRow } from "@/components/vault/vault-clip-list-row";
import { VaultDestinationsDrawer } from "@/components/vault/vault-destinations-drawer";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import type { VaultClip } from "@/lib/api/client";
import {
  readViewMode,
  VAULT_VIEW_STORAGE_KEY,
  writeViewMode,
  type ViewMode,
} from "@/lib/view-mode";

type Props = {
  clips: VaultClip[];
  onClipsChange: (clips: VaultClip[]) => void;
};

export function VaultClipsView({ clips, onClipsChange }: Props) {
  const { push: toast } = useToastSafe();
  const [mode, setMode] = React.useState<ViewMode>("card");
  const [hydrated, setHydrated] = React.useState(false);
  const [destinationsClip, setDestinationsClip] = React.useState<VaultClip | null>(null);
  const [renamingId, setRenamingId] = React.useState<string | null>(null);
  const [renameValue, setRenameValue] = React.useState("");
  const [renamePending, setRenamePending] = React.useState(false);

  React.useEffect(() => {
    setMode(readViewMode(VAULT_VIEW_STORAGE_KEY, "card"));
    setHydrated(true);
  }, []);

  const handleModeChange = (next: ViewMode) => {
    setMode(next);
    writeViewMode(VAULT_VIEW_STORAGE_KEY, next);
  };

  async function remove(id: string) {
    const result = await removeVaultClipAction(id);
    if (result.status === "ok") {
      toast("Removed", "Clip removed from Vault.");
      onClipsChange(clips.filter((c) => c.id !== id));
    } else {
      toast("Remove failed", result.message ?? "Could not remove");
    }
  }

  function startRename(clip: VaultClip) {
    setRenamingId(clip.id);
    setRenameValue(clip.title || "");
  }

  async function saveRename(id: string) {
    setRenamePending(true);
    const result = await renameVaultClipAction(id, renameValue);
    setRenamePending(false);
    if (result.status === "ok") {
      const trimmed = renameValue.trim();
      onClipsChange(
        clips.map((c) => (c.id === id ? { ...c, title: trimmed } : c)),
      );
      setRenamingId(null);
      toast("Renamed", "Vault clip title updated.");
    } else {
      toast("Rename failed", result.message ?? "Could not rename");
    }
  }

  const toggle = hydrated ? (
    <ViewModeToggle mode={mode} onChange={handleModeChange} />
  ) : (
    <div className="h-8 w-28 skeleton rounded-sm" />
  );

  if (mode === "card") {
    return (
      <div className="space-y-4">
        <div className="flex justify-end">{toggle}</div>
        <VaultClipGrid
          clips={clips}
          renamingId={renamingId}
          renameValue={renameValue}
          renamePending={renamePending}
          onRenameValueChange={setRenameValue}
          onStartRename={startRename}
          onCancelRename={() => setRenamingId(null)}
          onSaveRename={(id) => void saveRename(id)}
          onRemove={(id) => void remove(id)}
          onShare={setDestinationsClip}
        />
        {destinationsClip && (
          <VaultDestinationsDrawer
            clip={destinationsClip}
            open={Boolean(destinationsClip)}
            onClose={() => setDestinationsClip(null)}
          />
        )}
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-end mb-3">{toggle}</div>
      <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
        {clips.map((clip) => (
          <VaultClipListRow
            key={clip.id}
            clip={clip}
            renaming={renamingId === clip.id}
            renameValue={renameValue}
            renamePending={renamePending}
            onRenameValueChange={setRenameValue}
            onStartRename={() => startRename(clip)}
            onCancelRename={() => setRenamingId(null)}
            onSaveRename={() => void saveRename(clip.id)}
            onRemove={() => void remove(clip.id)}
            onShare={() => setDestinationsClip(clip)}
          />
        ))}
      </div>

      {destinationsClip && (
        <VaultDestinationsDrawer
          clip={destinationsClip}
          open={Boolean(destinationsClip)}
          onClose={() => setDestinationsClip(null)}
        />
      )}
    </>
  );
}
