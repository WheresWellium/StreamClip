/**
 * Product docs (MkDocs on Vercel). Prefer in-app `/help` routes so desktop
 * users stay inside qClip instead of bouncing to a browser.
 *
 * Paths MUST match pages published by mkdocs.yml (customer henna set).
 */
import { devToolsEnabled } from "@/lib/dev-tools";
export const DOCS_BASE =
  process.env.NEXT_PUBLIC_DOCS_URL ?? "https://streamclip-henna.vercel.app";

export type HelpTopic = {
  id: string;
  label: string;
  description: string;
  /** Path on the docs site, including leading slash and trailing slash when MkDocs uses them. */
  docsPath: string;
};

/** Mirrors henna nav: Home → Install → First clip → Help. */
export const HELP_TOPICS: HelpTopic[] = [
  {
    id: "install",
    label: "Install",
    description: "Windows installer or Mac Docker — get qClip running.",
    docsPath: "/BETA_DOWNLOAD/",
  },
  {
    id: "first-clip",
    label: "First clip",
    description: "Create a job, wait for clips, approve, and publish.",
    docsPath: "/BETA_TESTER_QUICKSTART/",
  },
  {
    id: "faq",
    label: "FAQ",
    description: "Short answers for license, SmartScreen, Mac, and upgrades.",
    docsPath: "/BETA_FAQ/",
  },
  {
    id: "known-issues",
    label: "Known issues",
    description: "Beta.6 fixes and limits (TikTok, CPU speed, SmartScreen).",
    docsPath: "/BETA_KNOWN_ISSUES/",
  },
  {
    id: "troubleshooting",
    label: "Troubleshooting",
    description: "Symptom → fix for desktop and Docker setups.",
    docsPath: "/tutorials/TUTORIAL_TROUBLESHOOTING/",
  },
];

/** Build an in-app help URL that opens the embedded docs viewer. */
export function helpHref(docsPath = "/"): string {
  const normalized = docsPath.startsWith("/") ? docsPath : `/${docsPath}`;
  if (normalized === "/" || normalized === "") return "/help";
  return `/help?path=${encodeURIComponent(normalized)}`;
}

/** Absolute docs URL (for rare cases that must leave the app). */
export function docsAbsoluteUrl(docsPath: string): string {
  const base = DOCS_BASE.replace(/\/$/, "");
  const path = docsPath.startsWith("/") ? docsPath : `/${docsPath}`;
  return `${base}${path}`;
}

function normalizeDocsPath(path: string): string {
  if (!path || path === "/") return "/";
  const trimmed = path.trim();
  if (!trimmed.startsWith("/")) return `/${trimmed}`;
  return trimmed.endsWith("/") ? trimmed : `${trimmed}/`;
}

/** Paths allowed in external (non–dev-tools) Help embeds. */
export function isPublicHelpDocsPath(path: string): boolean {
  const normalized = normalizeDocsPath(path);
  if (normalized === "/") return true;
  return HELP_TOPICS.some((topic) => normalizeDocsPath(topic.docsPath) === normalized);
}

export function clampHelpDocsPathForProduct(
  path: string,
  allowOperatorPaths: boolean,
): string {
  if (allowOperatorPaths) return path;
  if (!isPublicHelpDocsPath(path)) return "/";
  return path;
}

export function resolveHelpDocsPath(raw: string | null | undefined): string {
  if (!raw || !raw.trim()) return "/";
  let path = raw.trim();
  try {
    if (path.startsWith("http://") || path.startsWith("https://")) {
      const url = new URL(path);
      if (url.origin === new URL(DOCS_BASE).origin) {
        path = `${url.pathname}${url.search}${url.hash}` || "/";
      } else {
        return "/";
      }
    }
  } catch {
    return "/";
  }
  if (!path.startsWith("/")) path = `/${path}`;
  return clampHelpDocsPathForProduct(path, devToolsEnabled);
}
