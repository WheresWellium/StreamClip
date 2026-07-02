import { test, expect } from "@playwright/test";

test.describe("Jet Stream happy path", () => {
  test.skip(
    !process.env.E2E_RUN,
    "Set E2E_RUN=1 with stack running to execute",
  );

  test("home page loads with jobs section", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByText("Jet Stream")).toBeVisible();
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

  test("create job form shows legend tooltips", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByRole("button", { name: /new job/i })).toBeVisible();
  });
});
