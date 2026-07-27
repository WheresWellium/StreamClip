import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

import { ClientProviders } from "@/components/providers/client-providers";
import { HeaderNavWrapper } from "@/components/layout/header-nav-wrapper";
import { HeaderHelpMenu } from "@/components/layout/header-help-menu";
import { SidecarReadyGate } from "@/components/layout/sidecar-ready-gate";
import { AuthExtras } from "@/components/auth/auth-extras";
import { ModelWarmupBanner } from "@/components/onboarding/model-warmup-banner";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600"],
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "qClip — all-in-one clip studio",
  description:
    "Clip any length. Frame any ratio. Rank what wins — auto-reframe, captions, overlays, vault, and publish in one studio.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  ),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <ClientProviders>
          <AuthExtras />
          <SidecarReadyGate>
          <div className="min-h-screen hero-gradient">
          <header className="border-b border-white/25 bg-background/85 backdrop-blur-sm sticky top-0 z-40 desktop-titlebar-drag">
            <div className="container flex h-12 items-center gap-4 pt-[env(titlebar-area-height,0px)]">
              <a
                href="/"
                className="flex shrink-0 items-center gap-2 font-mono text-sm font-medium uppercase tracking-[0.12em] text-foreground hover:text-sky-400 transition-colors desktop-titlebar-no-drag"
              >
                <span
                  className="flex h-5 w-5 items-center justify-center border border-sky-400 text-sky-400 text-[11px] font-semibold lowercase tracking-normal"
                  aria-hidden="true"
                >
                  q
                </span>
                <span className="hidden sm:inline">qClip</span>
              </a>
              <div className="flex min-w-0 flex-1 items-center justify-end gap-2 desktop-titlebar-no-drag">
                <HeaderNavWrapper />
                <HeaderHelpMenu />
              </div>
            </div>
          </header>
          <ModelWarmupBanner />
          <main className="container py-6">{children}</main>
          </div>
          </SidecarReadyGate>
        </ClientProviders>
      </body>
    </html>
  );
}
