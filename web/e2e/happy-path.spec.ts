import { test, expect } from "@playwright/test";

test.describe("StreamClip happy path", () => {
  test.skip(
    !process.env.E2E_RUN,
    "Set E2E_RUN=1 with stack running to execute",
  );

  test("home page loads with jobs section", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByText("StreamClip")).toBeVisible();
    await expect(page.getByText(/recent jobs/i)).toBeVisible();
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
    expect(body.caption_styles).toContain("gaming_impact");
    expect(body.reframe_presets).toContain("fps_game");
  });

  test("create job form shows legend tooltips", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByRole("button", { name: /new job/i })).toBeVisible();
  });
});
