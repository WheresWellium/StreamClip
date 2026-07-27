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

const PLANS = [
  {
    name: "Evaluation",
    includes: "Limited sample workflow on the same app",
    clips: "25",
    storage: "10 GB",
    jobs: "30 / month",
  },
  {
    name: "Studio",
    includes: "Clip pipeline, captions, vault, templates, exports",
    clips: "500",
    storage: "50 GB",
    jobs: "500 / month",
  },
  {
    name: "Publisher add-on",
    includes: "Connected accounts, schedule queue, local OAuth",
    clips: "Same as Studio",
    storage: "Same as Studio",
    jobs: "Same as Studio",
  },
  {
    name: "Audio add-on",
    includes: "Audio-to-video / slate workflow",
    clips: "Same as Studio",
    storage: "Same as Studio",
    jobs: "Same as Studio",
  },
] as const;

export function BillingPanel() {
  return (
    <div className="space-y-6">
      <LicensePanel />

      <Card>
        <CardHeader>
          <CardTitle>Licenses & capabilities</CardTitle>
          <CardDescription>
            One qClip executable — a license unlocks capabilities, not a different app.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b border-border/60">
                <th className="pb-2 pr-4 font-medium">License</th>
                <th className="pb-2 pr-4 font-medium">Includes</th>
                <th className="pb-2 pr-4 font-medium">Vault clips</th>
                <th className="pb-2 pr-4 font-medium">Storage</th>
                <th className="pb-2 font-medium">Jobs</th>
              </tr>
            </thead>
            <tbody>
              {PLANS.map((plan) => (
                <tr key={plan.name} className="border-b border-border/40 last:border-0">
                  <td className="py-3 pr-4 font-medium">{plan.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground text-xs">{plan.includes}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{plan.clips}</td>
                  <td className="py-3 pr-4 font-mono text-xs">{plan.storage}</td>
                  <td className="py-3 font-mono text-xs">{plan.jobs}</td>
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
        or your purchase email from Lemon Squeezy. Existing Pro keys unlock Studio + Publisher.
      </p>
    </div>
  );
}
