"use server";

import { revalidatePath } from "next/cache";

import { ApiClientError, vaultApi } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";

export type VaultActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export async function saveToVaultAction(
  clipId: string,
  title?: string,
): Promise<VaultActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in to save clips to your Vault." };
  }
  try {
    await vaultApi.save(clipId, title, token);
    revalidatePath("/vault");
    revalidatePath("/");
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
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in required." };
  }
  const trimmed = title.trim();
  if (!trimmed) {
    return { status: "error", message: "Title cannot be empty." };
  }
  try {
    await vaultApi.rename(vaultClipId, trimmed, token);
    revalidatePath("/vault");
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not rename clip." };
  }
}

export async function removeVaultClipAction(vaultClipId: string): Promise<VaultActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in required." };
  }
  try {
    await vaultApi.remove(vaultClipId, token);
    revalidatePath("/vault");
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not remove clip." };
  }
}
