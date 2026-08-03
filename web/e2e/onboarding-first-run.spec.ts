/**
 * T66 / T60 — first-run onboarding.
 *
 * The P0 bug this locks: creating the sample job inside the wizard navigated to
 * /jobs/{id} before the onboarding cookie was written, so middleware bounced the
 * user back to step 1 and the job vanished from view.
 */

import { expect, test } from "@playwright/test";

import {
  fulfillSse,
  gotoApp,
  installShellMocks,
  jobFixture,
  json,
  sseBody,
} from "./support/mock-api";

const JOB_ID = "job-onboarding-1";

test.describe("First-run onboarding", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    // Deliberately no onboarding_complete cookie — this is a fresh install.
    await context.clearCookies();
    const domain = new URL(baseURL ?? "http://localhost:3000").hostname;
    await context.addCookies([
      { name: "streamclip_device_id", value: "e2e-first-run", domain, path: "/" },
    ]);
    await installShellMocks(page);
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
  });

  test("protected routes redirect to onboarding until it is finished", async ({ page }) => {
    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );

    await gotoApp(page, "/jobs");

    await expect(page).toHaveURL(/\/onboarding$/);
    await expect(page.getByRole("heading", { name: /welcome to qclip/i })).toBeVisible();
  });

  test("wizard walks welcome → ready and keeps the user out of a redirect loop", async ({
    page,
  }) => {
    await page.route("**/api/devices/onboarding-complete", (route) =>
      json(route, { device_id: "e2e-first-run", onboarding_complete: true }),
    );

    await gotoApp(page, "/onboarding");

    await expect(page.getByRole("heading", { name: /welcome to qclip/i })).toBeVisible();
    await page.getByRole("button", { name: /^Continue$/ }).click();

    await expect(page.getByRole("heading", { name: /ready check/i })).toBeVisible();
    await page.getByRole("button", { name: /^Continue$/ }).click();

    await expect(page.getByRole("heading", { name: /^Storage$/ })).toBeVisible();
    await page.getByRole("button", { name: /^Continue$/ }).click();

    await expect(
      page.getByRole("heading", { name: /create your first clip/i }),
    ).toBeVisible();
    // The sample URL is prefilled so a first-timer can just submit.
    await expect(page.locator("#source_url")).not.toHaveValue("");
  });

  test("creating the first job lands on the job, not back on the wizard", async ({
    page,
  }) => {
    let completeCalled = false;

    await page.route("**/api/devices/onboarding-complete", async (route) => {
      completeCalled = true;
      await json(route, { device_id: "e2e-first-run", onboarding_complete: true });
    });
    await page.route("**/api/jobs?*", (route) =>
      json(route, { jobs: [], total: 0, limit: 50, offset: 0 }),
    );
    await page.route("**/api/jobs", async (route) => {
      if (route.request().method() === "POST") {
        await json(route, { id: JOB_ID, status: "queued" }, 202);
        return;
      }
      await json(route, { jobs: [], total: 0, limit: 50, offset: 0 });
    });
    await page.route(`**/api/jobs/${JOB_ID}`, (route) =>
      json(
        route,
        jobFixture({
          id: JOB_ID,
          status: "queued",
          progress: 0,
          current_stage: "queued",
          finished_at: null,
          clips: [],
        }),
      ),
    );
    await page.route(`**/api/jobs/${JOB_ID}/progress`, (route) =>
      fulfillSse(route, sseBody([])),
    );
    await page.route(`**/api/jobs/${JOB_ID}/title-suggestions**`, (route) =>
      json(route, { suggestions: [] }),
    );

    await gotoApp(page, "/onboarding");
    // Advance to the create step.
    for (let i = 0; i < 3; i += 1) {
      await page.getByRole("button", { name: /^Continue$/ }).click();
    }
    await expect(
      page.getByRole("heading", { name: /create your first clip/i }),
    ).toBeVisible();

    const createPost = page.waitForRequest(
      (req) =>
        req.method() === "POST" &&
        /\/api\/jobs\/?$/.test(new URL(req.url()).pathname),
      { timeout: 15_000 },
    );
    await page.getByRole("button", { name: /generate clips/i }).click();
    await createPost;

    // Regression lock for GAP T60 — we must land on the job and stay there.
    await page.waitForURL(new RegExp(`/jobs/${JOB_ID}/?$`), { timeout: 20_000 });
    await page.waitForTimeout(1500); // give middleware a chance to bounce us
    expect(new URL(page.url()).pathname).toMatch(new RegExp(`^/jobs/${JOB_ID}/?$`));

    // Onboarding was marked complete before the navigation.
    expect(completeCalled).toBe(true);
    const cookies = await page.context().cookies();
    expect(
      cookies.find((c) => c.name === "onboarding_complete")?.value,
    ).toBeTruthy();
  });
});
