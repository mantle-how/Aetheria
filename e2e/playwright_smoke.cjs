const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ARTIFACT_DIR = path.join(__dirname, "artifacts");
const SCREENSHOT_PATH = path.join(ARTIFACT_DIR, "web-home.png");
const TARGET_URL = "http://127.0.0.1:8000/";

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function fail(message, context = {}) {
  console.error(
    JSON.stringify(
      {
        ok: false,
        message,
        ...context,
      },
      null,
      2
    )
  );
  process.exitCode = 1;
}

async function run() {
  ensureDir(ARTIFACT_DIR);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const wsEvents = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });
  page.on("pageerror", (err) => {
    pageErrors.push(String(err));
  });
  page.on("websocket", (ws) => {
    wsEvents.push(`open:${ws.url()}`);
    ws.on("framesent", (event) => wsEvents.push(`sent:${String(event.payload).slice(0, 120)}`));
    ws.on("framereceived", (event) => wsEvents.push(`recv:${String(event.payload).slice(0, 120)}`));
    ws.on("close", () => wsEvents.push("close"));
    ws.on("socketerror", (error) => wsEvents.push(`socketerror:${String(error)}`));
  });

  try {
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForSelector("#topdownCanvas", { state: "visible", timeout: 10000 });
    await page.waitForSelector("#dashboardCanvas", { state: "visible", timeout: 10000 });
    try {
      await page.waitForFunction(() => {
        const status = document.querySelector("#statusLine");
        if (!status) {
          return false;
        }
        return (status.textContent || "").includes("Tick ");
      }, null, { timeout: 15000 });
    } catch (error) {
      const statusText = await page.evaluate(() => {
        const status = document.querySelector("#statusLine");
        return status ? status.textContent || "" : "";
      });
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
      fail("Frontend did not receive Tick snapshot within timeout", {
        error: String(error),
        statusText,
        consoleErrors,
        pageErrors,
        wsEvents,
        screenshot: SCREENSHOT_PATH,
      });
      return;
    }
    await page.waitForTimeout(1200);

    const metrics = await page.evaluate(() => {
      const topdown = document.querySelector("#topdownCanvas");
      const dashboard = document.querySelector("#dashboardCanvas");
      if (!topdown || !dashboard) {
        return { found: false };
      }
      const topCtx = topdown.getContext("2d");
      const dashCtx = dashboard.getContext("2d");
      if (!topCtx || !dashCtx) {
        return { found: false };
      }

      const topSample = topCtx.getImageData(
        0,
        0,
        Math.min(100, topdown.width || 1),
        Math.min(100, topdown.height || 1)
      ).data;
      const dashSample = dashCtx.getImageData(
        0,
        0,
        Math.min(100, dashboard.width || 1),
        Math.min(100, dashboard.height || 1)
      ).data;

      const topHasInk = Array.from(topSample).some((v) => v !== 0);
      const dashHasInk = Array.from(dashSample).some((v) => v !== 0);
      const status = document.querySelector("#statusLine");

      return {
        found: true,
        topdownSize: [topdown.width, topdown.height],
        dashboardSize: [dashboard.width, dashboard.height],
        topHasInk,
        dashHasInk,
        statusText: status ? status.textContent || "" : "",
      };
    });

    await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });

    const checks = [];
    if (!metrics.found) {
      checks.push("canvas not found");
    } else {
      if (metrics.topdownSize[0] < 100 || metrics.topdownSize[1] < 100) {
        checks.push(`topdown size too small: ${metrics.topdownSize}`);
      }
      if (metrics.dashboardSize[0] < 100 || metrics.dashboardSize[1] < 100) {
        checks.push(`dashboard size too small: ${metrics.dashboardSize}`);
      }
      if (!metrics.topHasInk) {
        checks.push("topdown canvas has no drawn pixels");
      }
      if (!metrics.dashHasInk) {
        checks.push("dashboard canvas has no drawn pixels");
      }
      if (!metrics.statusText.includes("Tick ")) {
        checks.push(`status did not include Tick: ${metrics.statusText}`);
      }
    }
    if (consoleErrors.length > 0) {
      checks.push(`console errors: ${consoleErrors.join(" | ")}`);
    }
    if (pageErrors.length > 0) {
      checks.push(`page errors: ${pageErrors.join(" | ")}`);
    }

    if (checks.length > 0) {
      fail("Frontend smoke test failed", {
        checks,
        metrics,
        consoleErrors,
        pageErrors,
        wsEvents,
        screenshot: SCREENSHOT_PATH,
      });
      return;
    }

    console.log(
      JSON.stringify(
        {
          ok: true,
          metrics,
          wsEvents,
          screenshot: SCREENSHOT_PATH,
        },
        null,
        2
      )
    );
  } finally {
    await context.close();
    await browser.close();
  }
}

run().catch((error) => {
  fail("Unexpected Playwright runtime error", {
    error: String(error),
  });
});
