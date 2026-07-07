import { ApiClientError, vaultApi } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";

export type VaultActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export async function saveToVaultAction(
  clipId: string,
  title?: string,
): Promise<VaultActionState> {
  const token = getClientAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in to save clips to your Vault." };
  }
  try {
    await vaultApi.save(clipId, title, token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not save to vault." };
  }
}

export async function renameVaultClipAction(
  vaultClipId: string,
  title: string,
): Promise<VaultActionState> {
  const token = getClientAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in required." };
  }
  const trimmed = title.trim();
  if (!trimmed) {
    return { status: "error", message: "Title cannot be empty." };
  }
  try {
    await vaultApi.rename(vaultClipId, trimmed, token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not rename clip." };
  }
}

export async function removeVaultClipAction(vaultClipId: string): Promise<VaultActionState> {
  const token = getClientAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in required." };
  }
  try {
    await vaultApi.remove(vaultClipId, token);
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not remove clip." };
  }
}
