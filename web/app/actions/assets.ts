"use server";

import { revalidatePath } from "next/cache";

import { ApiClientError, assetsApi, type OverlayAsset } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";

export type AssetActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
};

export async function createAssetAction(body: {
  name: string;
  asset_type: OverlayAsset["asset_type"];
  storage_key: string;
  description: string;
  tags?: string[];
  default_duration_secs?: number;
}): Promise<AssetActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in to upload overlay assets." };
  }
  try {
    await assetsApi.create(body, token);
    revalidatePath("/settings/assets");
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not save asset." };
  }
}

export async function removeAssetAction(assetId: string): Promise<AssetActionState> {
  const token = await getAccessToken();
  if (!token) {
    return { status: "error", message: "Sign in required." };
  }
  try {
    await assetsApi.remove(assetId, token);
    revalidatePath("/settings/assets");
    return { status: "ok" };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not remove asset." };
  }
}
