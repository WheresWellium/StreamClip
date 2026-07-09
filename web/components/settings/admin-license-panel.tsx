"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/form";
import { useToastSafe } from "@/components/providers/toast-provider";
import { getClientAccessToken } from "@/lib/auth/client-session";
import { readApiErrorMessage } from "@/lib/api/read-api-error";

async function revokeLicense(licenseId: string, token: string) {
  const res = await fetch(`/api/admin/licenses/${encodeURIComponent(licenseId)}/revoke`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(readApiErrorMessage(payload, "Could not revoke license"));
  }
  return payload as { status: string; license_id: string };
}

/** Admin-only license revoke (Settings → Advanced). */
export function AdminLicensePanel() {
  const toast = useToastSafe();
  const [licenseId, setLicenseId] = useState("");
  const [busy, setBusy] = useState(false);

  const onRevoke = async () => {
    const id = licenseId.trim();
    if (!id) {
      toast("License id required", "Paste the install_licenses row id from ops tools.");
      return;
    }
    const token = getClientAccessToken();
    if (!token) {
      toast("Sign in required", "Admin actions need an authenticated admin account.");
      return;
    }
    setBusy(true);
    try {
      const result = await revokeLicense(id, token);
      toast("License revoked", `Status: ${result.status}`);
      setLicenseId("");
    } catch (err) {
      toast("Revoke failed", err instanceof Error ? err.message : "Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 max-w-md">
      <p className="text-sm text-muted-foreground">
        Revoke a commerce-issued license by database id. Use{" "}
        <code className="text-xs">scripts/list_support_reports.py</code> or DB tools to
        look up ids.
      </p>
      <div className="space-y-2">
        <Label htmlFor="admin-license-id">License id</Label>
        <Input
          id="admin-license-id"
          value={licenseId}
          onChange={(e) => setLicenseId(e.target.value)}
          placeholder="uuid from install_licenses"
        />
      </div>
      <Button variant="destructive" disabled={busy} onClick={() => void onRevoke()}>
        {busy ? "Revoking…" : "Revoke license"}
      </Button>
    </div>
  );
}
