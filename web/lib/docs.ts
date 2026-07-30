/**
 * Product docs (MkDocs on Vercel). Prefer in-app `/help` routes so desktop
 * users stay inside qClip instead of bouncing to a browser.
 *
 * Henna publishes a single customer page (download + how to use).
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

/** In-app Help anchors on the single henna home page. */
export const HELP_TOPICS: HelpTopic[] = [
  {
    id: "download",
    label: "Download",
    description: "Get the Windows or Mac installer.",
    docsPath: "/#download",
  },
  {
    id: "use",
    label: "How to use",
    description: "Install, activate, and make a clip.",
    docsPath: "/#use",
  },
];

/**
 * Demoted / retired henna paths → home (or a section anchor).
 * Keep in sync with vercel.json redirects.
 */
export const LEGACY_HELP_DOCS_PATHS: Record<string, string> = {
  "/BETA_DOWNLOAD/": "/#download",
  "/BETA_TESTER_QUICKSTART/": "/#use",
  "/BETA_FAQ/": "/",
  "/BETA_KNOWN_ISSUES/": "/",
  "/tutorials/TUTORIAL_INSTALL/": "/#download",
  "/tutorials/TUTORIAL_FIRST_JOB/": "/#use",
  "/tutorials/TUTORIAL_GPU_SETUP/": "/",
  "/tutorials/TUTORIAL_EDIT_APPROVE/": "/#use",
  "/tutorials/TUTORIAL_PUBLISH_YOUTUBE/": "/#use",
  "/tutorials/TUTORIAL_VAULT/": "/#use",
  "/tutorials/TUTORIAL_TROUBLESHOOTING/": "/",
  "/BETA_TESTER_PLAN/": "/#use",
  "/MACOS_INSTALLER/": "/#download",
};

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
  // Preserve hash-only section links on home (e.g. /#download).
  if (trimmed.startsWith("/#")) return trimmed;
  const [pathname, hash] = trimmed.split("#", 2);
  const withSlash =
    !pathname || pathname === "/"
      ? "/"
      : pathname.endsWith("/")
        ? pathname
        : `${pathname}/`;
  return hash ? `${withSlash}#${hash}` : withSlash;
}

function pathnameOnly(path: string): string {
  const withoutHash = path.split("#", 1)[0] ?? path;
  const withoutQuery = withoutHash.split("?", 1)[0] ?? withoutHash;
  return withoutQuery || "/";
}

function hashOnly(path: string): string {
  const idx = path.indexOf("#");
  if (idx < 0) return "";
  return path.slice(idx);
}

/** Remap demoted docs paths before the public allow-list clamp. */
export function remapLegacyHelpDocsPath(path: string): string {
  const hash = hashOnly(path);
  const normalized = normalizeDocsPath(pathnameOnly(path));
  if (normalized === "/") {
    return hash ? `/#${hash.slice(1)}` : "/";
  }
  const remapped = LEGACY_HELP_DOCS_PATHS[normalized];
  if (remapped) return remapped;
  return hash ? `${normalized}${hash}` : normalized;
}

/** Paths allowed in external (non–dev-tools) Help embeds. */
export function isPublicHelpDocsPath(path: string): boolean {
  const normalized = normalizeDocsPath(path);
  if (normalized === "/" || normalized.startsWith("/#")) return true;
  return HELP_TOPICS.some((topic) => normalizeDocsPath(topic.docsPath) === normalized);
}

export function clampHelpDocsPathForProduct(
  path: string,
  allowOperatorPaths: boolean,
): string {
  const remapped = remapLegacyHelpDocsPath(path);
  if (allowOperatorPaths) {
    // Even with operator tools on, retired henna pages no longer exist.
    if (LEGACY_HELP_DOCS_PATHS[normalizeDocsPath(pathnameOnly(path))]) {
      return remapped;
    }
    return remapped;
  }
  if (!isPublicHelpDocsPath(remapped)) return "/";
  return remapped;
}

export function resolveHelpDocsPath(raw: string | null | undefined): string {
  if (!raw || !raw.trim()) return "/";
  let path = raw.trim();
  let hash = "";
  try {
    if (path.startsWith("http://") || path.startsWith("https://")) {
      const url = new URL(path);
      if (url.origin === new URL(DOCS_BASE).origin) {
        path = url.pathname || "/";
        hash = url.hash || "";
      } else {
        return "/";
      }
    } else {
      const hashIdx = path.indexOf("#");
      if (hashIdx >= 0) {
        hash = path.slice(hashIdx);
        path = path.slice(0, hashIdx) || "/";
      }
      const qIdx = path.indexOf("?");
      if (qIdx >= 0) {
        path = path.slice(0, qIdx) || "/";
      }
    }
  } catch {
    return "/";
  }
  if (!path.startsWith("/")) path = `/${path}`;
  const withHash = hash ? `${path}${hash}` : path;
  return clampHelpDocsPathForProduct(withHash, devToolsEnabled);
}
