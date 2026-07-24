"use client";

import Link from "next/link";

import { LicensePanel } from "@/components/settings/license-panel";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const TIERS = [
  {
    name: "Free",
    clips: "25",
    storage: "10 GB",
    jobs: "30 / month",
    highlights: "Core clip pipeline, vault saves within quota",
  },
  {
    name: "Pro",
    clips: "500",
    storage: "50 GB",
    jobs: "500 / month",
    highlights: "Distribution, higher quotas, OAuth integrations",
  },
  {
    name: "Enterprise",
    clips: "5,000",
    storage: "500 GB",
    jobs: "Custom",
    highlights: "Dedicated limits — contact sales (coming soon)",
  },
] as const;

export function BillingPanel() {
  return (
    <div className="space-y-6">
      <LicensePanel />

      <Card>
        <CardHeader>
          <CardTitle>Plan comparison</CardTitle>
          <CardDescription>Vault clip and storage limits by tier.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b border-border/60">
                <th className="pb-2 pr-4 font-medium">Plan</th>
                <th className="pb-2 pr-4 font-medium">Vault clips</th>
                <th className="pb-2 pr-4 font-medium">Storage</th>
                <th className="pb-2 pr-4 font-medium">Jobs</th>
                <th className="pb-2 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody>
              {TIERS.map((tier) => (
                <tr key={tier.name} className="border-b border-border/40 last:border-0">
                  <td className="py-3 pr-4 font-medium">{tier.name}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{tier.clips}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{tier.storage}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{tier.jobs}</td>
                  <td className="py-3 text-muted-foreground text-xs">{tier.highlights}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">
        Need a key? Check{" "}
        <Link href="/settings?section=license" className="text-sky-400 hover:underline">
          License
        </Link>{" "}
        or your purchase email from Lemon Squeezy.
      </p>
    </div>
  );
}
