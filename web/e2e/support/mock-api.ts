/**
 * Shared route mocks + fixtures for UI journey e2e.
 *
 * Why mocks: the real pipeline needs a GPU and minutes of wall clock, so a
 * live create→render→publish run is not a viable UI test. Pipeline correctness
 * is covered by pytest; these specs cover what pytest cannot — what the browser
 * actually renders and what a user can actually click, including the failure
 * states that have no reachable fixture on a healthy stack.
 *
 * Only the web server is required. Every `/api/*` call is intercepted.
 */

import type { BrowserContext, Page, Route } from "@playwright/test";

export const E2E_DEVICE_ID = "e2e-device-ui-0001";
export const E2E_TOKEN = "e2e-access-token";

export type JsonBody = Record<string, unknown> | unknown[];

/** Fulfill a route with JSON. */
export async function json(route: Route, body: JsonBody, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

/** Fulfill a route with an API-shaped error envelope. */
export async function apiError(
  route: Route,
  status: number,
  code = "server_error",
  message = "Upstream failure",
): Promise<void> {
  await json(route, { code, message }, status);
}

// ─── Fixtures ────────────────────────────────────────────────────────────────

export const META_FIXTURE = {
  reframe_presets: [
    { id: "fps_game", label: "FPS game" },
    { id: "irl", label: "IRL / podcast" },
  ],
  caption_styles: [
    { id: "gaming_impact", label: "Gaming impact" },
    { id: "minimal_white", label: "Minimal white" },
  ],
  content_profiles: [
    {
      id: "gaming",
      label: "Gaming",
      recommended_reframe: "fps_game",
      recommended_captions: "gaming_impact",
    },
    {
      id: "podcast",
      label: "Podcast",
      recommended_reframe: "irl",
      recommended_captions: "minimal_white",
    },
  ],
  aspect_ratios: [
    { id: "9:16", label: "9:16 Vertical" },
    { id: "1:1", label: "1:1 Square" },
  ],
  emotions: ["hype", "funny"],
  features: { audio_ingest: true },
};

export function clipFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "clip-1",
    rank: 0,
    title: "Insane 1v5 clutch",
    hook: "You will not believe the last round",
    emotion: "hype",
    start_secs: 120.5,
    end_secs: 148.5,
    duration_secs: 28,
    ensemble_score: 0.91,
    llm_score: 0.88,
    audio_score: 0.79,
    spectral_score: 0.7,
    flow_score: 0.66,
    chat_score: 0.0,
    status: "done",
    error_message: null,
    render_time_secs: 41.2,
    file_size_bytes: 8_400_000,
    transcript_text: "no way no way that just happened",
    llm_reason: "Peak crowd reaction with a clean payoff.",
    meme_keywords: ["clutch"],
    overlays: [],
    kind: "discovery",
    parent_clip_ids: [],
    render_overrides: {},
    approval_status: "draft",
    download_url: "https://example.invalid/clip-1.mp4",
    thumbnail_url: null,
    publish_statuses: [],
    ...overrides,
  };
}

export function jobFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-e2e-1",
    source_url: "https://www.twitch.tv/videos/123456",
    source_title: "Saturday ranked grind",
    display_title: null,
    source_duration_secs: 3600,
    status: "done",
    progress: 1,
    current_stage: "done",
    error_code: null,
    error_message: null,
    created_at: "2026-07-28T12:00:00Z",
    started_at: "2026-07-28T12:00:05Z",
    pipeline_started_at: "2026-07-28T12:00:06Z",
    finished_at: "2026-07-28T12:04:00Z",
    stage_durations_json: {
      ingest: 22.4,
      transcribe: 61.9,
      highlights: 8.1,
      virality: 12.6,
      process_clip: 41.2,
    },
    content_profile: "gaming",
    aspect_ratio: "9:16",
    clips: [clipFixture()],
    title_audit_id: null,
    ...overrides,
  };
}

// ─── Base mocks (app shell) ──────────────────────────────────────────────────

export type ShellMockOptions = {
  /**
   * When false, leave `/api/meta` unmocked so a test can own the first-failure
   * path (GAP T61). Default true — most pages need meta to leave Loading….
   */
  meta?: boolean;
};

/**
 * Mocks the shell endpoints every page hits: sidecar health gate, model warmup
 * banner, and /api/meta. Without these the SidecarReadyGate blocks the UI.
 */
export async function installShellMocks(
  page: Page,
  options: ShellMockOptions = {},
): Promise<void> {
  const { meta = true } = options;
  await page.route("**/api/health", (route) =>
    json(route, { status: "ok", database: true, redis: true }),
  );
  await page.route("**/api/health/models", (route) =>
    json(route, { status: "ready", models: {} }),
  );
  await page.route("**/api/health/stack", (route) =>
    json(route, { status: "ok", checks: {}, worker: true }),
  );
  if (meta) {
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
  }
  // Device endpoints used by the claim-device prompt on signed-in loads.
  await page.route("**/api/devices/**", (route) =>
    json(route, { device_id: E2E_DEVICE_ID, onboarding_complete: true, claimed: 0 }),
  );
  // Anonymous by default; auth specs override this route.
  await page.route("**/api/auth/me", (route) => apiError(route, 401, "unauthorized", "No session"));
}

/** Cookies that let the app render without the onboarding redirect. */
export async function seedOnboardedSession(
  context: BrowserContext,
  baseURL: string,
): Promise<void> {
  const domain = new URL(baseURL).hostname;
  await context.addCookies([
    { name: "onboarding_complete", value: "1", domain, path: "/" },
    { name: "streamclip_device_id", value: E2E_DEVICE_ID, domain, path: "/" },
  ]);
}

/**
 * Signed-in browser state (localStorage mirrors what auth-form writes).
 *
 * `device_claimed` is pre-set so the claim-jobs modal does not cover the page —
 * it renders a full-screen overlay that swallows every click.
 */
export async function seedSignedIn(page: Page): Promise<void> {
  await page.addInitScript(
    ([token, device]) => {
      localStorage.setItem("streamclip_access_token", token);
      localStorage.setItem("streamclip_refresh_token", `${token}-refresh`);
      localStorage.setItem("streamclip_device_id", device);
      localStorage.setItem("streamclip_remember_me", "1");
      localStorage.setItem("device_claimed", "1");
    },
    [E2E_TOKEN, E2E_DEVICE_ID],
  );
}

/**
 * Navigate and wait for the boot gate to release the UI.
 *
 * The app renders a full-viewport loading shell until /api/health answers; it
 * swallows pointer events while visible, so every interaction must wait for it.
 */
export async function gotoApp(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page
    .getByTestId("app-loading-screen")
    .waitFor({ state: "hidden", timeout: 30_000 })
    .catch(() => {
      /* Loader may already be gone before the first check. */
    });
}

/** An SSE stream that emits the given events once, then ends. */
export function sseBody(events: Array<{ event: string; data: unknown; id?: number }>): string {
  return (
    events
      .map(
        (e, i) =>
          `id: ${e.id ?? i + 1}\nevent: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`,
      )
      .join("") || ": keep-alive\n\n"
  );
}

export async function fulfillSse(route: Route, body: string): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
    body,
  });
}
