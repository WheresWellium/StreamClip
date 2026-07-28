import Link from "next/link";
import { Film, List, Plus, Settings } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 animate-fade-in">
      <section className="space-y-3 pt-1">
        <div className="inline-flex items-center gap-2 px-2 py-0.5 rounded-sm border border-sky-400/40 bg-sky-400/10 font-mono text-[10px] uppercase tracking-[0.14em] text-sky-400">
          qClip — all-in-one clip studio
        </div>
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
          Clip any length.{" "}
          <span className="text-sky-400">Frame any ratio.</span> Rank what wins.
        </h1>
        <p className="text-muted-foreground max-w-xl text-sm leading-relaxed">
          Paste a URL or upload a file. We find the moments, reframe to any aspect
          ratio, and score each clip so you know which cuts should outperform the rest.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="border-sky-400/25 bg-sky-400/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Plus className="h-4 w-4 text-sky-400" />
              New job
            </CardTitle>
            <CardDescription>
              Paste a URL or upload — long, medium, or short form. Any platform source.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="lg" className="w-full">
              <Link href="/jobs/new">Start a clip job</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <List className="h-4 w-4 text-muted-foreground" />
              Your jobs
            </CardTitle>
            <CardDescription>
              Track pipeline progress, then open clips when rendering completes.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline" size="lg" className="w-full">
              <Link href="/jobs">View all jobs</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-frame/15">
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium">Workflow</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3 text-sm">
          <div className="space-y-1">
            <p className="font-medium text-foreground">1 · Create</p>
            <p className="text-muted-foreground text-xs leading-relaxed">
              Pick source, aspect ratio, and content type. Crop and caption presets
              stay tucked away until you need them.
            </p>
          </div>
          <div className="space-y-1">
            <p className="font-medium text-foreground">2 · Monitor</p>
            <p className="text-muted-foreground text-xs leading-relaxed">
              Live pipeline progress only — no clip grid competing for attention.
            </p>
          </div>
          <div className="space-y-1 flex flex-col">
            <p className="font-medium text-foreground flex items-center gap-1.5">
              <Film className="h-3.5 w-3.5" />
              3 · Rank & ship
            </p>
            <p className="text-muted-foreground text-xs leading-relaxed">
              Compare scores, approve the winners, then publish or vault from one workspace.
            </p>
          </div>
        </CardContent>
      </Card>

      <p className="text-center text-xs text-muted-foreground">
        <Settings className="inline h-3.5 w-3.5 mr-1 align-text-bottom" />
        Vault, distribution, and license settings live under{" "}
        <Link href="/settings" className="text-sky-400 hover:underline">
          Settings
        </Link>
        .
      </p>
    </div>
  );
}
