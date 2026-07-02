import Link from "next/link";
import { redirect } from "next/navigation";

import { VaultClipGrid } from "@/components/vault/vault-clip-grid";
import { vaultApi } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";

export default async function VaultPage() {
  const token = await getAccessToken();
  if (!token) {
    redirect("/login?next=/vault");
  }

  let clips: Awaited<ReturnType<typeof vaultApi.list>> = [];
  let quota = { used: 0, limit: 25 };
  try {
    [clips, quota] = await Promise.all([
      vaultApi.list(token),
      vaultApi.quota(token),
    ]);
  } catch {
    clips = [];
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clip Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Saved clips ready to publish or schedule. Distinct from sticker assets in Settings.
          </p>
        </div>
        <p className="text-sm font-mono text-muted-foreground">
          {quota.used} / {quota.limit} clips
        </p>
      </div>

      {quota.used >= quota.limit * 0.8 && quota.used < quota.limit && (
        <p className="text-sm text-amber-400/90 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          Vault almost full — remove clips you no longer need.
        </p>
      )}

      {clips.length === 0 ? (
        <div className="glossy-surface rounded-lg border border-border/60 p-12 text-center space-y-4">
          <p className="text-muted-foreground">No saved clips yet.</p>
          <ButtonLink href="/">Go to Jobs</ButtonLink>
        </div>
      ) : (
        <VaultClipGrid clips={clips} />
      )}
    </main>
  );
}

function ButtonLink({ href, children }: { href: string; children: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
    >
      {children}
    </Link>
  );
}
