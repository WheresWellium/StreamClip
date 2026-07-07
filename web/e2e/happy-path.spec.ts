import { test, expect } from "@playwright/test";

test.describe("Jet Stream happy path", () => {
  test.skip(
    !process.env.E2E_RUN,
    "Set E2E_RUN=1 with stack running to execute",
  );

  test("home page loads dashboard", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByText("Jet Stream")).toBeVisible();
    await expect(page.getByRole("link", { name: /start a clip job/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /view all jobs/i })).toBeVisible();
  });

  test("jobs page loads", async ({ page }) => {
    await page.goto("http://localhost:3000/jobs");
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  });

  test("new job form loads", async ({ page }) => {
    await page.goto("http://localhost:3000/jobs/new");
    await expect(page.getByRole("heading", { name: /new clip job/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /generate clips/i })).toBeVisible();
  });

  test("API health returns ok", async ({ request }) => {
    const res = await request.get("http://localhost:8000/api/health");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toMatch(/ok|degraded/);
    expect(body.database).toBe(true);
  });

  test("API meta exposes presets", async ({ request }) => {
    const res = await request.get("http://localhost:8000/api/meta");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const captionIds = body.caption_styles.map((s: { id: string } | string) =>
      typeof s === "string" ? s : s.id,
    );
    expect(captionIds).toContain("gaming_impact");
    const presetIds = body.reframe_presets.map((p: { id: string } | string) =>
      typeof p === "string" ? p : p.id,
    );
    expect(presetIds).toContain("fps_game");
  });

  test("batch endpoint exists", async ({ request }) => {
    const res = await request.post("http://localhost:8000/api/jobs/batch", {
      data: { jobs: [] },
    });
    expect(res.status()).toBe(422);
  });

  test("batch publish validates missing job or clips", async ({ request }) => {
    const res = await request.post(
      "http://localhost:8000/api/jobs/nonexistent-job/clips/batch-publish",
      {
        headers: { "X-Device-Id": "e2e-device-0001" },
        data: { platform: "youtube_shorts", clip_ids: [] },
      },
    );
    expect([400, 401, 403, 404]).toContain(res.status());
  });

  test("create job API accepts URL and returns 202", async ({ request }) => {
    const res = await request.post("http://localhost:8000/api/jobs", {
      headers: { "X-Device-Id": "e2e-device-0001" },
      data: {
        source_url: "https://example.com/sample-vod.mp4",
        target_clips: 1,
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body.id).toBeTruthy();
  });

  test("list jobs returns array after create", async ({ request }) => {
    const list = await request.get("http://localhost:8000/api/jobs", {
      headers: { "X-Device-Id": "e2e-device-0001" },
    });
    expect(list.ok()).toBeTruthy();
    const body = await list.json();
    expect(Array.isArray(body.jobs)).toBeTruthy();
  });
});
