/**
 * Heuristic virality banner — majority heuristic clips → visible status.
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

const JOB_ID = "job-e2e-heuristic";
const JOB_URL = `**/api/jobs/${JOB_ID}`;

test.describe("Heuristic virality banner", () => {
  test.beforeEach(async ({ context, page, baseURL }) => {
    await seedOnboardedSession(context, baseURL ?? "http://localhost:3000");
    await installShellMocks(page);
    await page.route("**/api/templates**", (route) => json(route, []));
    await page.route("**/api/assets**", (route) => json(route, []));
  });

  test("shows when majority of clips are heuristic", async ({ page }) => {
    const job = jobFixture({
      id: JOB_ID,
      clips: [
        clipFixture({
          id: "clip-h1",
          rank: 0,
          virality_source: "heuristic",
          llm_reason: "Heuristic audio+novelty blend",
        }),
        clipFixture({
          id: "clip-h2",
          rank: 1,
          virality_source: "heuristic",
          download_url: "https://example.invalid/clip-h2.mp4",
        }),
        clipFixture({
          id: "clip-llm",
          rank: 2,
          virality_source: "llm",
          download_url: "https://example.invalid/clip-llm.mp4",
        }),
      ],
    });

    await page.route(JOB_URL, (route) => json(route, job));
    await page.route(`${JOB_URL}/progress`, (route) =>
      fulfillSse(route, sseBody([])),
    );

    await gotoApp(page, `/jobs/${JOB_ID}/clips`);

    const banner = page.getByTestId("heuristic-virality-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText(/local heuristics/i);
  });
});
