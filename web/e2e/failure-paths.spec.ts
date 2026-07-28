/**
 * T66 — failure-path UI coverage.
 *
 * These are the states a healthy stack can never produce, which is exactly why
 * they regressed unnoticed (GAP T61/T62/T63). Each test locks in one fix.
 */

import { expect, test, type Page } from "@playwright/test";

import {
  apiError,
  clipFixture,
  E2E_DEVICE_ID,
  E2E_TOKEN,
  fulfillSse,
  gotoApp,
  installShellMocks,
  jobFixture,
  json,
  META_FIXTURE,
  seedOnboardedSession,
  seedSignedIn,
  sseBody,
} from "./support/mock-api";

const JOB_ID = "job-e2e-1";

/** Prefer copy-based alerts; Next.js mounts an empty route announcer with role=alert. */
function pageAlert(page: Page, text: RegExp | string) {
  return page.getByRole("alert").filter({ hasText: text });
}

test.describe("API-down and not-found paths", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    // Meta owned per-test — a successful shell mock would hide the T61 path.
    await installShellMocks(page, { meta: false });
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
  });

  test("create page shows a retryable error instead of hanging on Loading", async ({
    page,
  }) => {
    // React Strict Mode remounts effects — a one-shot 503 can be overwritten by a
    // second META success before the error UI commits. Gate on an explicit flag.
    let allowMeta = false;
    await page.route("**/api/meta", async (route) => {
      if (!allowMeta) {
        await apiError(route, 503, "unavailable", "API is starting");
        return;
      }
      await json(route, META_FIXTURE);
    });

    await gotoApp(page, "/jobs/new");

    // Regression lock for GAP T61 — no infinite "Loading…".
    await expect(pageAlert(page, /studio api is unreachable|api is starting/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /^Retry$/ })).toBeVisible();

    allowMeta = true;
    await page.getByRole("button", { name: /^Retry$/ }).click();
    await expect(page.locator("h1", { hasText: /new clip job/i })).toBeVisible();
  });

  test("onboarding shows a retryable error when the API is down", async ({
    context,
    page,
    baseURL,
  }) => {
    // First run: no onboarding cookie.
    await context.clearCookies();
    const domain = new URL(baseURL ?? "http://localhost:3000").hostname;
    await context.addCookies([
      { name: "streamclip_device_id", value: "e2e-first-run", domain, path: "/" },
    ]);
    await page.route("**/api/meta", (route) =>
      apiError(route, 503, "unavailable", "API is starting"),
    );

    await gotoApp(page, "/onboarding");

    // Regression lock for GAP T61 — the very first screen must not hang.
    await expect(pageAlert(page, /api is starting|studio api is unreachable/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /^Retry$/ })).toBeVisible();
  });

  test("missing job renders not-found in place rather than silently redirecting", async ({
    page,
  }) => {
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
    await page.route(`**/api/jobs/${JOB_ID}`, (route) =>
      apiError(route, 404, "not_found", "Job not found"),
    );

    await gotoApp(page, `/jobs/${JOB_ID}`);

    // Regression lock for GAP T63 — user stays put and is told why.
    await expect(page.getByRole("heading", { name: /job not found/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /back to jobs/i })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(`/jobs/${JOB_ID}`);
  });

  test("missing job on the clips route also renders not-found in place", async ({
    page,
  }) => {
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
    await page.route(`**/api/jobs/${JOB_ID}`, (route) =>
      apiError(route, 404, "not_found", "Job not found"),
    );

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);

    await expect(page.getByRole("heading", { name: /job not found/i })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(`/jobs/${JOB_ID}/clips`);
  });

  test("vault surfaces a load error instead of a fake empty state", async ({ page }) => {
    await seedSignedIn(page);
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "u@example.com", tier: "free" }),
    );
    await page.route("**/api/vault/clips**", (route) => apiError(route, 500));
    await page.route("**/api/vault/quota**", (route) => apiError(route, 500));

    await gotoApp(page, "/vault");

    // Regression lock for GAP T61 — "No saved clips yet" would be a lie here.
    await expect(page.getByText("Upstream failure")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/no saved clips yet/i)).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Retry$/ })).toBeVisible();
  });

  test("destinations drawer reports a distribution load failure with a retry", async ({
    page,
  }) => {
    await seedSignedIn(page);
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "pro@example.com", tier: "pro" }),
    );
    await page.route(`**/api/jobs/${JOB_ID}`, (route) =>
      json(route, jobFixture({ clips: [clipFixture({ approval_status: "approved" })] })),
    );
    await page.route(`**/api/jobs/${JOB_ID}/progress`, (route) =>
      fulfillSse(route, sseBody([{ event: "done", data: { progress: 1 } }])),
    );
    await page.route("**/api/distribution/**", (route) => apiError(route, 500));

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);
    await page.getByRole("button", { name: /^Destinations$/ }).first().click();

    await expect(
      page.getByText(/upstream failure|could not load distribution/i),
    ).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /^Retry$/ })).toBeVisible();
  });

  test("stalled job warns the user when progress goes quiet", async ({ page }) => {
    test.slow();
    let jobGets = 0;
    let progressPollsFail = false;
    await page.route("**/api/meta", (route) => json(route, META_FIXTURE));
    // SSE never opens → client falls back to REST polling after SSE_FALLBACK_MS.
    await page.route(`**/api/jobs/${JOB_ID}/progress`, (route) => apiError(route, 500));
    await page.route(`**/api/jobs/${JOB_ID}`, async (route) => {
      jobGets += 1;
      // Allow a few successful GETs so React Strict Mode remounts + initial paint
      // do not replace the page with a hard load error before polling starts.
      if (!progressPollsFail || jobGets <= 4) {
        await json(
          route,
          jobFixture({
            status: "running",
            progress: 0.35,
            current_stage: "transcribe",
            clips: [],
          }),
        );
        return;
      }
      await apiError(route, 503, "unavailable", "progress backend down");
    });

    await gotoApp(page, `/jobs/${JOB_ID}`);
    // Page must show the running job before we start failing poll GETs.
    await expect(page.getByText(/transcribe|processing|running/i).first()).toBeVisible({
      timeout: 15_000,
    });
    progressPollsFail = true;

    await expect(
      page.getByText(/no progress updates for a few minutes/i),
    ).toBeVisible({
      timeout: 90_000,
    });
  });
});

test.describe("Auth resilience", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    await installShellMocks(page);
    await seedSignedIn(page);
  });

  test("a 5xx on token refresh does not silently sign the user out", async ({ page }) => {
    let refreshHits = 0;
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "u@example.com", tier: "pro" }),
    );
    await page.route("**/api/auth/refresh", async (route) => {
      refreshHits += 1;
      await apiError(route, 502, "bad_gateway");
    });
    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );

    await gotoApp(page, "/jobs");
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();

    // Re-seed after navigation in case a load-time focus refresh raced the mock.
    await page.evaluate(
      ([token, device]) => {
        localStorage.setItem("streamclip_access_token", token);
        localStorage.setItem("streamclip_refresh_token", `${token}-refresh`);
        localStorage.setItem("streamclip_device_id", device);
        localStorage.setItem("streamclip_remember_me", "1");
        localStorage.setItem("device_claimed", "1");
      },
      [E2E_TOKEN, E2E_DEVICE_ID] as [string, string],
    );

    const tokenBefore = await page.evaluate(() =>
      localStorage.getItem("streamclip_access_token"),
    );
    expect(tokenBefore).toBeTruthy();

    await page.evaluate(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await expect.poll(() => refreshHits, { timeout: 10_000 }).toBeGreaterThan(0);

    // Regression lock for GAP T64 — tokens survive a transient server error.
    const token = await page.evaluate(() =>
      localStorage.getItem("streamclip_access_token"),
    );
    expect(token).toBeTruthy();
  });

  test("a 401 on token refresh does clear the session", async ({ page }) => {
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "u@example.com", tier: "pro" }),
    );
    await page.route("**/api/auth/refresh", (route) =>
      apiError(route, 401, "unauthorized", "Refresh token expired"),
    );
    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );

    await gotoApp(page, "/jobs");
    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();

    await page.evaluate(() => window.dispatchEvent(new Event("focus")));

    await expect
      .poll(
        () => page.evaluate(() => localStorage.getItem("streamclip_access_token")),
        { timeout: 10_000 },
      )
      .toBeNull();
  });
});
