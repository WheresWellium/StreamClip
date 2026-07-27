import { test, expect } from "@playwright/test";

test.describe("Cinematic loading screen", () => {
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
        value: "e2e-device-0001",
        domain: "localhost",
        path: "/",
      },
    ]);
  });

  test("boot loader announces status then yields to app chrome", async ({
    page,
  }) => {
    await page.goto("http://localhost:3000", { waitUntil: "domcontentloaded" });

    const status = page.getByRole("status");
    // Loader may already have exited on a warm stack; either phase is valid.
    const loaderVisible = await status
      .first()
      .isVisible()
      .catch(() => false);

    if (loaderVisible) {
      await expect(status.first()).toContainText(/Jet Stream|Loading/i);
    }

    await expect(
      page.getByRole("link", { name: "Jet Stream" }),
    ).toBeVisible({ timeout: 30_000 });
  });
});
