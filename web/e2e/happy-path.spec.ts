import { test, expect } from "@playwright/test";

test.describe("StreamClip happy path", () => {
  test.skip(
    !process.env.E2E_RUN,
    "Set E2E_RUN=1 with stack running to execute",
  );

  test("home page loads", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await expect(page.getByText("StreamClip")).toBeVisible();
    await expect(page.getByText(/recent jobs/i)).toBeVisible();
  });
});
