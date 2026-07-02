import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { ClientProviders } from "@/components/providers/client-providers";
import { HeaderNavWrapper } from "@/components/layout/header-nav-wrapper";
import { AuthExtras } from "@/components/auth/auth-extras";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "StreamClip — AI clip generator",
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
      <body className={`${inter.variable} font-sans antialiased`}>
        <ClientProviders>
          <AuthExtras />
          <div className="min-h-screen hero-gradient">
          <header className="border-b border-white/10 bg-background/40 backdrop-blur-xl sticky top-0 z-40">
            <div className="container flex h-14 items-center justify-between">
              <a
                href="/"
                className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-sky-400 transition-colors"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  className="text-sky-400"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M7 4v16l13-8z" />
                </svg>
                StreamClip
              </a>
              <nav className="flex items-center gap-4 text-sm">
                <HeaderNavWrapper />
              </nav>
            </div>
          </header>
          <main className="container py-8">{children}</main>
          </div>
        </ClientProviders>
      </body>
    </html>
  );
}
