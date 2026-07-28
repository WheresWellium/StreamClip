import { test, expect } from "@playwright/test";

/**
 * Boot loader UI checks. Skipped unless E2E_RUN=1 (same gate as happy-path).
 * Delays /api/health so the cinematic loader is observable.
 */
test.describe("Cinematic boot loader", () => {
  test.skip(
    !process.env.E2E_RUN,
    "Set E2E_RUN=1 with stack running to execute",
  );

  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      {
        name: "onboarding_complete",
        value: "1",
        domain: "localhost",
        path: "/",
      },
      {
        name: "streamclip_device_id",
        value: "e2e-device-loader",
        domain: "localhost",
        path: "/",
      },
    ]);
  });

  test("shows loading screen then reveals app", async ({ page }) => {
    await page.route("**/api/health", async (route) => {
      await new Promise((r) => setTimeout(r, 1200));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", database: true }),
      });
    });

    await page.goto("/");

    const loader = page.getByTestId("app-loading-screen");
    await expect(loader).toBeVisible();
    await expect(loader.getByRole("heading", { name: "qClip" })).toBeVisible();
    await expect(loader.getByText("all-in-one clip studio")).toBeVisible();
    await expect(loader.getByRole("progressbar")).toBeVisible();
    await expect(loader.getByRole("status")).toBeVisible();
    await expect(loader).toHaveAttribute("data-loading-phase", /boot|entering|loading/);

    await expect(loader).toBeHidden({ timeout: 15_000 });
    await expect(page.getByRole("link", { name: "qClip" })).toBeVisible();
  });

  test("respects prefers-reduced-motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.route("**/api/health", async (route) => {
      await new Promise((r) => setTimeout(r, 900));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok", database: true }),
      });
    });

    await page.goto("/");
    const loader = page.getByTestId("app-loading-screen");
    await expect(loader).toBeVisible();
    await expect(loader).toHaveClass(/sc-loading--reduced/);
    await expect(loader).toBeHidden({ timeout: 15_000 });
  });

  test("cover art asset is reachable", async ({ request }) => {
    const res = await request.get("/loading/cover.svg");
    expect(res.ok()).toBeTruthy();
    const body = await res.text();
    expect(body).toContain("<svg");
    expect(body).toContain("aria-hidden");
  });
});
