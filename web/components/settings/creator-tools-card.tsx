import Link from "next/link";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function CreatorToolsCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Creator tools</CardTitle>
        <CardDescription>
          Reuse job presets and manage overlay assets for your clips.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3 text-sm">
        <Link href="/settings/templates" className="text-sky-400 hover:underline">
          Job templates →
        </Link>
        <Link href="/settings/assets" className="text-sky-400 hover:underline">
          Overlay assets →
        </Link>
      </CardContent>
    </Card>
  );
}
