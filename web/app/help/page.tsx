import { Suspense } from "react";

import { DocsViewer } from "@/components/help/docs-viewer";

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-6xl animate-fade-in">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading help center…</p>
        }
      >
        <DocsViewer />
      </Suspense>
    </div>
  );
}
