/**
 * T66 — core UI journey: create → progress → review → destinations.
 *
 * Runs against the web server only; every `/api/*` call is mocked, so the
 * journey is deterministic and needs no GPU, no worker, and no minutes of
 * pipeline wall clock. Pipeline correctness itself is covered by pytest —
 * these specs cover what pytest cannot: what the browser renders and what a
 * user can actually click.
 */

import { expect, test } from "@playwright/test";

import {
  apiError,
  clipFixture,
  fulfillSse,
  gotoApp,
  installShellMocks,
  jobFixture,
  json,
  seedOnboardedSession,
  seedSignedIn,
  sseBody,
} from "./support/mock-api";

const JOB_ID = "job-e2e-1";
const JOB_URL = `**/api/jobs/${JOB_ID}`;

/** Quiet SSE stream so progress hooks connect without emitting events. */
async function routeQuietProgress(page: import("@playwright/test").Page) {
  await page.route(`${JOB_URL}/progress`, (route) => fulfillSse(route, sseBody([])));
}

test.describe("Create → progress → review journey", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    await installShellMocks(page);
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
    await page.route(`${JOB_URL}/title-suggestions**`, (route) =>
      json(route, { suggestions: [] }),
    );
  });

  test("submits the create form and lands on the new job", async ({ page }) => {
    let createdPayload: Record<string, unknown> | null = null;

    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );
    await page.route("**/api/jobs", async (route) => {
      if (route.request().method() === "POST") {
        createdPayload = route.request().postDataJSON();
        await json(route, { id: JOB_ID, status: "queued" }, 202);
        return;
      }
      await json(route, { jobs: [], total: 0, limit: 50, offset: 0 });
    });
    await page.route(JOB_URL, (route) =>
      json(
        route,
        jobFixture({
          status: "processing",
          progress: 0.35,
          current_stage: "transcribe",
          finished_at: null,
          clips: [],
        }),
      ),
    );
    await routeQuietProgress(page);

    await gotoApp(page, "/jobs/new");
    await expect(page.locator("h1", { hasText: /new clip job/i })).toBeVisible();

    await page.fill("#source_url", "https://www.twitch.tv/videos/123456");
    await page.fill("#display_title", "Saturday ranked grind");
    await page.getByRole("button", { name: /generate clips/i }).click();

    await page.waitForURL(new RegExp(`/jobs/${JOB_ID}$`));

    // The form sent exactly what the user typed.
    expect(createdPayload).toMatchObject({
      source_url: "https://www.twitch.tv/videos/123456",
      display_title: "Saturday ranked grind",
    });

    await expect(page.getByText("processing").first()).toBeVisible();
    await expect(
      page.getByText(/clips appear here when the pipeline finishes/i),
    ).toBeVisible();
  });

  test("renders live progress from SSE and reveals the review CTA when done", async ({
    page,
  }) => {
    await page.route(JOB_URL, (route) => json(route, jobFixture()));
    await page.route(`${JOB_URL}/progress`, (route) =>
      fulfillSse(
        route,
        sseBody([
          {
            event: "progress",
            data: {
              job_id: JOB_ID,
              stage: "process_clip",
              progress: 0.8,
              message: "Rendering clip 1 of 1",
              status: "processing",
            },
          },
          {
            event: "done",
            data: {
              job_id: JOB_ID,
              stage: "done",
              progress: 1,
              message: "Job complete",
              status: "done",
            },
          },
        ]),
      ),
    );

    await gotoApp(page, `/jobs/${JOB_ID}`);

    await expect(page.getByRole("progressbar").first()).toBeVisible();
    await expect(page.getByText("1 clips ready to review")).toBeVisible();
    await expect(page.getByRole("link", { name: /review clips/i })).toBeVisible();
  });

  test("clips workspace renders the clip with its approval control", async ({ page }) => {
    await page.route(JOB_URL, (route) => json(route, jobFixture()));
    await routeQuietProgress(page);

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);

    await expect(page.getByRole("heading", { name: /^Clips/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Insane 1v5 clutch" })).toBeVisible();
    await expect(page.getByText(/1 clips · approve and publish/i)).toBeVisible();

    const approval = page.getByRole("radiogroup", { name: "Approval status" }).first();
    await expect(approval).toBeVisible();
    await expect(approval.getByRole("radio", { name: "Draft" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("approving a clip PATCHes approval and confirms to the user", async ({ page }) => {
    let patched: Record<string, unknown> | null = null;

    await page.route(JOB_URL, (route) => json(route, jobFixture()));
    await routeQuietProgress(page);
    await page.route(`${JOB_URL}/clips/clip-1/approval`, async (route) => {
      patched = route.request().postDataJSON();
      await json(route, { clip_id: "clip-1", approval_status: "approved" });
    });

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);

    const approval = page.getByRole("radiogroup", { name: "Approval status" }).first();
    await approval.getByRole("radio", { name: "Approved" }).click();

    await expect.poll(() => patched, { timeout: 10_000 }).not.toBeNull();
    expect(patched).toMatchObject({ approval_status: "approved" });
    await expect(approval.getByRole("radio", { name: "Approved" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("destinations drawer asks an anonymous user to sign in, not to buy Pro", async ({
    page,
  }) => {
    await page.route(JOB_URL, (route) =>
      json(route, jobFixture({ clips: [clipFixture({ approval_status: "approved" })] })),
    );
    await routeQuietProgress(page);

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);
    await page.getByRole("button", { name: /^Destinations$/ }).first().click();

    // Regression lock for GAP T71.
    await expect(page.getByText(/sign in to publish clips/i)).toBeVisible();
    await expect(page.getByText(/publishing requires pro/i)).toHaveCount(0);
  });

  test("Pro user gets a platform picker and a schedule field that blocks past dates", async ({
    page,
  }) => {
    await seedSignedIn(page);
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "pro@example.com", tier: "pro" }),
    );
    await page.route("**/api/distribution/platforms", (route) =>
      json(route, [
        { id: "youtube_shorts", label: "YouTube Shorts", enabled: true, connected: true },
        { id: "tiktok", label: "TikTok", enabled: true, connected: false },
      ]),
    );
    await page.route("**/api/distribution/connections", (route) =>
      json(route, [{ platform: "youtube_shorts", account_label: "My channel" }]),
    );
    await page.route(JOB_URL, (route) =>
      json(route, jobFixture({ clips: [clipFixture({ approval_status: "approved" })] })),
    );
    await routeQuietProgress(page);

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);
    await page.getByRole("button", { name: /^Destinations$/ }).first().click();

    await expect(page.locator("#platform")).toBeVisible();
    await page.getByRole("button", { name: "Schedule", exact: true }).click();

    // Regression lock for GAP T71 — no past scheduling.
    const scheduled = page.locator("#sched-at");
    await expect(scheduled).toBeVisible();
    const min = await scheduled.getAttribute("min");
    expect(min).toBeTruthy();
    expect(new Date(min as string).getTime()).toBeGreaterThan(
      Date.now() - 48 * 3600 * 1000,
    );
  });

  test("Pro user can publish an approved clip from the drawer", async ({ page }) => {
    let publishBody: Record<string, unknown> | null = null;

    await seedSignedIn(page);
    await page.route("**/api/auth/me", (route) =>
      json(route, { id: "u1", email: "pro@example.com", tier: "pro" }),
    );
    await page.route("**/api/distribution/platforms", (route) =>
      json(route, [
        { id: "youtube_shorts", label: "YouTube Shorts", enabled: true, connected: true },
      ]),
    );
    await page.route("**/api/distribution/connections", (route) =>
      json(route, [{ platform: "youtube_shorts", account_label: "My channel" }]),
    );
    await page.route("**/api/distribution/publish", async (route) => {
      publishBody = route.request().postDataJSON();
      await json(route, { id: "pj-1", status: "queued" }, 202);
    });
    await page.route(JOB_URL, (route) =>
      json(route, jobFixture({ clips: [clipFixture({ approval_status: "approved" })] })),
    );
    await routeQuietProgress(page);

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);
    await page.getByRole("button", { name: /^Destinations$/ }).first().click();
    await expect(page.locator("#platform")).toBeVisible();

    // The tab and the submit share a name; the submit is the later one.
    await page.getByRole("button", { name: "Publish now" }).last().click();

    await expect.poll(() => publishBody, { timeout: 10_000 }).not.toBeNull();
    expect(publishBody).toMatchObject({
      clip_id: "clip-1",
      platform: "youtube_shorts",
    });
  });

  test("a failed job surfaces a human-readable reason", async ({ page }) => {
    await page.route(JOB_URL, (route) =>
      json(
        route,
        jobFixture({
          status: "error",
          progress: 0.4,
          current_stage: "ingest",
          error_code: "ingest_failed",
          error_message: "yt-dlp: video is private",
          clips: [],
        }),
      ),
    );
    await routeQuietProgress(page);

    await gotoApp(page, `/jobs/${JOB_ID}`);

    await expect(page.getByText("Job failed")).toBeVisible();
    // Raw pipeline text is replaced by mapped operator copy (user-errors.ts).
    await expect(
      page.getByText(/could not download the source video/i),
    ).toBeVisible();
    await expect(page.getByText(/yt-dlp/i)).toHaveCount(0);
  });

  test("empty jobs list still offers a create path", async ({ page }) => {
    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );

    await gotoApp(page, "/jobs");

    await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: /new job/i }).first()).toBeVisible();
  });

  test("jobs list shows a job and links to its detail page", async ({ page }) => {
    await page.route("**/api/jobs?*", (route) =>
      json(route, {
        jobs: [
          {
            id: JOB_ID,
            source_title: "Saturday ranked grind",
            display_title: null,
            source_duration_secs: 3600,
            status: "done",
            progress: 1,
            created_at: "2026-07-28T12:00:00Z",
            clip_count: 1,
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    );

    await gotoApp(page, "/jobs");

    await expect(page.getByText("Saturday ranked grind").first()).toBeVisible();
    await expect(page.locator(`a[href*="/jobs/${JOB_ID}"]`).first()).toBeVisible();
  });

  test("create form shows field-level validation errors", async ({ page }) => {
    await page.route("**/api/jobs", (route) => apiError(route, 500));

    await gotoApp(page, "/jobs/new");
    await page.fill("#source_url", "https://www.twitch.tv/videos/123456");
    // Set the value past the 512-char schema limit directly: `maxlength` caps
    // typing, so only a scripted/pasted value reaches the schema. The field is
    // uncontrolled, so FormData picks up exactly what we set.
    await page.evaluate(() => {
      const el = document.querySelector<HTMLInputElement>("#display_title");
      if (!el) throw new Error("display_title input missing");
      el.removeAttribute("maxlength");
      el.value = "x".repeat(600);
      el.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await page.getByRole("button", { name: /generate clips/i }).click();

    // Regression lock for GAP T72 — field errors reach the user (not only a
    // generic banner). Prefer test id; fall back to copy if HMR lags.
    const banner = page.getByTestId("create-job-error").or(
      page.getByText("Validation failed"),
    );
    await expect(banner.first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/display_title/i)).toBeVisible();
  });
});
