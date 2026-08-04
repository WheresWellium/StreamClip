/**
 * Merge toolbar selection — locks the controlled-checkbox count gate.
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

const JOB_ID = "job-e2e-merge";
const JOB_URL = `**/api/jobs/${JOB_ID}`;

test.describe("Merge clips selection", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    await installShellMocks(page);
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
  });

  test("checking two clips enables Merge selected (2)", async ({ page }) => {
    const job = jobFixture({
      id: JOB_ID,
      clips: [
        clipFixture({ id: "clip-a", rank: 0, title: "Clip A" }),
        clipFixture({
          id: "clip-b",
          rank: 1,
          title: "Clip B",
          download_url: "https://example.invalid/clip-b.mp4",
        }),
        clipFixture({
          id: "clip-c",
          rank: 2,
          title: "Clip C",
          download_url: "https://example.invalid/clip-c.mp4",
        }),
      ],
    });

    await page.route(JOB_URL, (route) => json(route, job));
    await page.route(`${JOB_URL}/progress`, (route) =>
      fulfillSse(route, sseBody([])),
    );

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);

    await expect(page.getByText("Merge clips")).toBeVisible();
    const mergeBtn = page.getByRole("button", { name: /Merge selected \(0\)/i });
    await expect(mergeBtn).toBeVisible();
    await expect(mergeBtn).toBeDisabled();

    const boxes = page.locator('label:has-text("#") input[type="checkbox"]');
    await expect(boxes).toHaveCount(3);
    await boxes.nth(0).check();
    await boxes.nth(2).check();

    const enabled = page.getByRole("button", { name: /Merge selected \(2\)/i });
    await expect(enabled).toBeVisible();
    await expect(enabled).toBeEnabled();
  });
});
