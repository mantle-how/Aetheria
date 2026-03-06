const { test, expect } = require("playwright/test");

test.describe("Aetheria Web UI", () => {
  test("topdown and dashboard should render with live snapshots", async ({ page }) => {
    const consoleErrors = [];
    const pageErrors = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", (err) => {
      pageErrors.push(String(err));
    });

    await page.goto("http://127.0.0.1:8000/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("#topdownCanvas")).toBeVisible();
    await expect(page.locator("#dashboardCanvas")).toBeVisible();

    await page.waitForFunction(() => {
      const status = document.querySelector("#statusLine");
      if (!status) {
        return false;
      }
      const text = status.textContent || "";
      return text.includes("Tick ");
    }, null, { timeout: 10000 });

    await page.waitForTimeout(800);

    const metrics = await page.evaluate(() => {
      const topdown = document.querySelector("#topdownCanvas");
      const dashboard = document.querySelector("#dashboardCanvas");
      if (!topdown || !dashboard) {
        return null;
      }
      const topCtx = topdown.getContext("2d");
      const dashCtx = dashboard.getContext("2d");
      if (!topCtx || !dashCtx) {
        return null;
      }

      const topSample = topCtx.getImageData(0, 0, Math.min(64, topdown.width), Math.min(64, topdown.height)).data;
      const dashSample = dashCtx.getImageData(0, 0, Math.min(64, dashboard.width), Math.min(64, dashboard.height)).data;

      const topNonZero = Array.from(topSample).some((v) => v !== 0);
      const dashNonZero = Array.from(dashSample).some((v) => v !== 0);

      return {
        statusText: document.querySelector("#statusLine")?.textContent || "",
        topdownWidth: topdown.width,
        topdownHeight: topdown.height,
        dashboardWidth: dashboard.width,
        dashboardHeight: dashboard.height,
        topNonZero,
        dashNonZero,
      };
    });

    expect(metrics).not.toBeNull();
    expect(metrics.topdownWidth).toBeGreaterThan(100);
    expect(metrics.topdownHeight).toBeGreaterThan(100);
    expect(metrics.dashboardWidth).toBeGreaterThan(100);
    expect(metrics.dashboardHeight).toBeGreaterThan(100);
    expect(metrics.topNonZero).toBeTruthy();
    expect(metrics.dashNonZero).toBeTruthy();
    expect(metrics.statusText).toContain("Tick ");

    expect(consoleErrors, `console errors: ${consoleErrors.join("\n")}`).toHaveLength(0);
    expect(pageErrors, `page errors: ${pageErrors.join("\n")}`).toHaveLength(0);
  });
});
