/**
 * Job detail routes under static export (`NEXT_STATIC_EXPORT=1`) only pre-render
 * `jobs/_/` (see generateStaticParams). Soft client navigations to a real id
 * 404 as "Job not found" before the page mounts. Hard-navigate to the pretty
 * URL so FastAPI can serve the `_` shell, then resolve the id from the browser
 * path (never trust the baked `_` param alone).
 */

export const STATIC_JOB_ID_PLACEHOLDER = "_";
export const NAV_JOB_ID_STORAGE_KEY = "streamclip_nav_job_id";

const JOB_PATH_RE = /^\/jobs\/([^/]+)/;

export function parseJobIdFromPathname(pathname: string): string | null {
  const match = pathname.match(JOB_PATH_RE);
  if (!match) return null;
  const id = decodeURIComponent(match[1] ?? "");
  if (!id || id === STATIC_JOB_ID_PLACEHOLDER || id === "new") return null;
  return id;
}

export function isPlaceholderJobPath(pathname: string): boolean {
  const match = pathname.match(JOB_PATH_RE);
  return Boolean(match && match[1] === STATIC_JOB_ID_PLACEHOLDER);
}

export function resolveJobId(
  paramId: string | string[] | undefined | null,
  pathname: string,
): string | null {
  const fromPath = parseJobIdFromPathname(pathname);
  if (fromPath) return fromPath;

  if (typeof window !== "undefined") {
    const fromWindow = parseJobIdFromPathname(window.location.pathname);
    if (fromWindow) return fromWindow;

    const fromQuery = new URLSearchParams(window.location.search).get("id");
    if (fromQuery && fromQuery !== STATIC_JOB_ID_PLACEHOLDER && fromQuery !== "new") {
      return fromQuery;
    }

    if (isPlaceholderJobPath(window.location.pathname)) {
      try {
        const stashed = sessionStorage.getItem(NAV_JOB_ID_STORAGE_KEY);
        if (stashed) return stashed;
      } catch {
        /* private mode / blocked storage */
      }
    }
  }

  const raw = Array.isArray(paramId) ? paramId[0] : paramId;
  if (!raw || raw === STATIC_JOB_ID_PLACEHOLDER || raw === "new") return null;
  return raw;
}

export function jobOverviewPath(jobId: string): string {
  // Trailing slash matches Next static export (`trailingSlash: true`) so
  // FastAPI resolves `jobs/_/index.html` instead of falling through to home.
  // Soft-nav must never be used for these paths.
  return `/jobs/${jobId}/`;
}

export function jobClipsPath(jobId: string): string {
  return `/jobs/${jobId}/clips/`;
}

/** Full document navigation — required for desktop static export shells. */
export function navigateToJob(
  jobId: string,
  view: "overview" | "clips" = "overview",
): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(NAV_JOB_ID_STORAGE_KEY, jobId);
  } catch {
    /* ignore */
  }
  window.location.assign(view === "clips" ? jobClipsPath(jobId) : jobOverviewPath(jobId));
}

/**
 * Post-create success path: fire optional callback best-effort, then hard-nav
 * immediately. Never await the callback or gate on effect cleanup — that race
 * left users on home while the job kept running.
 */
export function afterCreateJobSuccess(
  jobId: string,
  onJobCreated?: (jobId: string) => void | Promise<void>,
): void {
  void Promise.resolve(onJobCreated?.(jobId)).catch(() => {
    /* caller failures must not trap the user */
  });
  navigateToJob(jobId);
}
