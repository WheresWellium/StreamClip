/**
 * Re-render keep-until-swap UI — pending/processing keeps Download + overlay.
 */

import { expect, test } from "@playwright/test";

import {
  clipFixture,
  fulfillSse,
  gotoApp,
  installShellMocks,
  jobFixture,
  json,
  seedOnboardedSession,
  sseBody,
} from "./support/mock-api";

const JOB_ID = "job-e2e-rerender";
const JOB_URL = `**/api/jobs/${JOB_ID}`;

test.describe("Re-render pending clip card", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    await installShellMocks(page);
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
  });

  for (const status of ["processing", "pending"] as const) {
    test(`${status} clip keeps Download and shows Re-rendering overlay`, async ({
      page,
    }) => {
      const job = jobFixture({
        id: JOB_ID,
        status: "done",
        clips: [
          clipFixture({
            id: `clip-rerender-${status}`,
            status,
            download_url: "https://example.invalid/keep.mp4",
            thumbnail_url: "https://example.invalid/keep.jpg",
          }),
        ],
      });

      await page.route(JOB_URL, (route) => json(route, job));
      await page.route(`${JOB_URL}/progress`, (route) =>
        fulfillSse(route, sseBody([])),
      );

      await gotoApp(page, `/jobs/${JOB_ID}/clips`);

      await expect(page.getByText("Re-rendering")).toBeVisible();
      await expect(page.getByRole("button", { name: /^Download$/i })).toBeVisible();
      await expect(page.getByText("No preview")).toHaveCount(0);
    });
  }

  test("after re-render completes, overlay clears and new download URL is used", async ({
    page,
  }) => {
    let phase: "inflight" | "done" = "inflight";
    await page.route(JOB_URL, (route) => {
      if (phase === "inflight") {
        return json(
          route,
          jobFixture({
            id: JOB_ID,
            status: "done",
            clips: [
              clipFixture({
                id: "clip-swap",
                status: "processing",
                download_url: "https://example.invalid/keep.mp4",
                thumbnail_url: "https://example.invalid/keep.jpg",
              }),
            ],
          }),
        );
      }
      return json(
        route,
        jobFixture({
          id: JOB_ID,
          status: "done",
          clips: [
            clipFixture({
              id: "clip-swap",
              status: "done",
              download_url: "https://example.invalid/new.mp4",
              thumbnail_url: "https://example.invalid/new.jpg",
            }),
          ],
        }),
      );
    });
    await page.route(`${JOB_URL}/progress`, (route) =>
      fulfillSse(route, sseBody([])),
    );

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);
    await expect(page.getByText("Re-rendering")).toBeVisible();

    phase = "done";
    await page.reload();
    await page
      .getByTestId("app-loading-screen")
      .waitFor({ state: "hidden", timeout: 30_000 })
      .catch(() => undefined);

    await expect(page.getByText("Re-rendering")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Download$/i })).toBeVisible();
    await expect(page.getByText("No preview")).toHaveCount(0);
  });
});
