import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

import { ClientProviders } from "@/components/providers/client-providers";
import { HeaderNavWrapper } from "@/components/layout/header-nav-wrapper";
import { AuthExtras } from "@/components/auth/auth-extras";

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
  title: "Jet Stream — AI clip generator",
  description:
    "Self-hosted AI pipeline for turning streams into vertical short-form clips.",
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
          <div className="min-h-screen hero-gradient">
          <header className="border-b border-white/25 bg-background/85 backdrop-blur-sm sticky top-0 z-40">
            <div className="container flex h-12 items-center justify-between">
              <a
                href="/"
                className="flex items-center gap-2 font-mono text-sm font-medium uppercase tracking-[0.12em] text-foreground hover:text-sky-400 transition-colors"
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
                Jet Stream
              </a>
              <nav className="flex items-center gap-4 text-sm">
                <HeaderNavWrapper />
              </nav>
            </div>
          </header>
          <main className="container py-6">{children}</main>
          </div>
        </ClientProviders>
      </body>
    </html>
  );
}
