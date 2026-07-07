"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AssetVaultPanel } from "@/components/settings/asset-vault-panel";
import { assetsApi } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";

export default function AssetsSettingsPage() {
  const router = useRouter();
  const [assets, setAssets] = useState<Awaited<ReturnType<typeof assetsApi.list>>>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getClientAccessToken();
    if (!token) {
      router.replace("/login?next=/settings/assets");
      return;
    }
    void assetsApi
      .list(token)
      .then(setAssets)
      .catch(() => setAssets([]))
      .finally(() => setReady(true));
  }, [router]);

  if (!ready) {
    return <p className="text-sm text-muted-foreground py-8">Loading assets…</p>;
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
