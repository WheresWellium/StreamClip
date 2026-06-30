import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

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
        <div className="min-h-screen bg-background">
          <header className="border-b border-border/40 bg-background/60 backdrop-blur sticky top-0 z-40">
            <div className="container flex h-14 items-center justify-between">
              <a
                href="/"
                className="flex items-center gap-2 text-sm font-medium"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
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
                <a
                  href="/"
                  className="text-muted-foreground hover:text-foreground"
                >
                  Jobs
                </a>
                <a
                  href="/docs"
                  className="text-muted-foreground hover:text-foreground"
                  target="_blank"
                  rel="noreferrer"
                >
                  API
                </a>
              </nav>
            </div>
          </header>
          <main className="container py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
