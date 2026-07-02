import Link from "next/link";
import { redirect } from "next/navigation";

import { AssetVaultPanel } from "@/components/settings/asset-vault-panel";
import { assetsApi } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";

export default async function AssetsSettingsPage() {
  const token = await getAccessToken();
  if (!token) {
    redirect("/login?next=/settings/assets");
  }

  let assets: Awaited<ReturnType<typeof assetsApi.list>> = [];
  try {
    assets = await assetsApi.list(token);
  } catch {
    assets = [];
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <Link href="/settings" className="text-sm text-sky-400 hover:underline">
          ← Settings
        </Link>
        <h1 className="text-2xl font-semibold mt-2">Overlay assets</h1>
        <p className="text-muted-foreground text-sm">
          Meme GIFs, stickers, and clips the overlay engine matches to your highlights.
          Distinct from the Clip Vault of finished clips.
        </p>
      </div>

      <AssetVaultPanel assets={assets} />
    </div>
  );
}
