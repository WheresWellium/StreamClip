"use client";

import { useRouter } from "next/navigation";
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

export function VaultClipsView({ clips }: { clips: VaultClip[] }) {
  const router = useRouter();
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
      router.refresh();
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
      setRenamingId(null);
      router.refresh();
    } else {
      toast("Rename failed", result.message ?? "Could not rename");
    }
  }

  if (mode === "card") {
    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          {hydrated ? (
            <ViewModeToggle mode={mode} onChange={handleModeChange} />
          ) : (
            <div className="h-8 w-28 skeleton rounded-sm" />
          )}
        </div>
        <VaultClipGrid clips={clips} />
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-end mb-3">
        {hydrated ? (
          <ViewModeToggle mode={mode} onChange={handleModeChange} />
        ) : (
          <div className="h-8 w-28 skeleton rounded-sm" />
        )}
      </div>
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
