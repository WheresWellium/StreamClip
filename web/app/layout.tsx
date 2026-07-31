import type { Metadata } from "next";
import Link from "next/link";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

import { ClientProviders } from "@/components/providers/client-providers";
import { HeaderBackButton } from "@/components/layout/header-back-button";
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
      <head>
        <link rel="preload" as="image" href="/loading/cover.svg" />
      </head>
      <body
        className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <ClientProviders>
          <AuthExtras />
          <SidecarReadyGate>
          <div className="min-h-screen hero-gradient">
          <header className="border-b border-white/25 bg-background/85 backdrop-blur-sm sticky top-0 z-40">
            <div className="container flex h-12 items-center gap-3 sm:gap-4">
              <HeaderBackButton />
              <Link
                href="/"
                className="flex shrink-0 items-center gap-2 font-mono text-sm font-medium uppercase tracking-[0.12em] text-foreground hover:text-sky-400 transition-colors"
              >
                <span
                  className="flex h-5 w-5 items-center justify-center border border-sky-400 text-sky-400"
                  aria-hidden="true"
                >
                  <svg
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
                  </svg>
                </span>
                <span className="hidden sm:inline">qClip</span>
              </Link>
              <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
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
