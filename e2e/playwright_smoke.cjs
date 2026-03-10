const fs = require("fs");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const REPO_ROOT = path.resolve(__dirname, "..");
const ARTIFACT_DIR = path.join(__dirname, "artifacts");
const SCREENSHOT_PATH = path.join(ARTIFACT_DIR, "web-home.png");
const TARGET_URL = "http://127.0.0.1:8000/";
const SERVER_ARGS = ["-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000"];

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

function parseStatus(text) {
  const source = text || "";
  const revisionMatch = source.match(/世界\s+(\d+)/);
  const tickMatch = source.match(/Tick\s+(\d+)/);
  return {
    text: source,
    worldRevision: revisionMatch ? Number(revisionMatch[1]) : null,
    tick: tickMatch ? Number(tickMatch[1]) : null,
  };
}

function probeServer() {
  return new Promise((resolve) => {
    const request = http.get(TARGET_URL, (response) => {
      response.resume();
      resolve(true);
    });
    request.on("error", () => resolve(false));
    request.setTimeout(1000, () => {
      request.destroy();
      resolve(false);
    });
  });
}

async function waitForServer(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await probeServer()) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}

async function ensureServer() {
  if (await probeServer()) {
    return { process: null, logs: [], started: false };
  }

  const logs = [];
  const serverProcess = spawn("python", SERVER_ARGS, {
    cwd: REPO_ROOT,
    stdio: ["ignore", "pipe", "pipe"],
  });
  serverProcess.stdout.on("data", (chunk) => logs.push(String(chunk).trim()));
  serverProcess.stderr.on("data", (chunk) => logs.push(String(chunk).trim()));

  const ready = await waitForServer(20000);
  if (!ready) {
    serverProcess.kill();
    throw new Error(`Server did not become ready. Logs: ${logs.join(" | ")}`);
  }

  return { process: serverProcess, logs, started: true };
}

async function stopServer(serverProcess) {
  if (!serverProcess) {
    return;
  }
  serverProcess.kill();
  await new Promise((resolve) => setTimeout(resolve, 500));
}

async function readStatus(page) {
  const text = await page.evaluate(() => document.querySelector("#statusLine")?.textContent || "");
  return parseStatus(text);
}

async function run() {
  ensureDir(ARTIFACT_DIR);

  let server = { process: null, logs: [], started: false };
  let browser = null;
  let context = null;
  const consoleErrors = [];
  const pageErrors = [];
  const wsEvents = [];

  try {
    server = await ensureServer();

    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const page = await context.newPage();

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

    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForSelector("#topdownCanvas", { state: "visible", timeout: 10000 });
    await page.waitForSelector("#dashboardCanvas", { state: "visible", timeout: 10000 });
    await page.waitForFunction(() => {
      const status = document.querySelector("#statusLine");
      if (!status) {
        return false;
      }
      const text = status.textContent || "";
      return text.includes("Tick ") && text.includes("世界 ");
    }, null, { timeout: 15000 });

    await page.waitForTimeout(800);

    await page.click("#playPauseBtn");
    await page.waitForFunction(() => {
      const text = document.querySelector("#statusLine")?.textContent || "";
      return text.includes("已暫停");
    }, null, { timeout: 5000 });

    const pausedStatus = await readStatus(page);
    await page.waitForTimeout(400);
    const pausedLaterStatus = await readStatus(page);
    if (pausedLaterStatus.tick !== pausedStatus.tick) {
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
      fail("Tick advanced while runtime was paused", {
        pausedStatus,
        pausedLaterStatus,
        consoleErrors,
        pageErrors,
        serverLogs: server.logs,
        wsEvents,
        screenshot: SCREENSHOT_PATH,
      });
      return;
    }

    await page.click("#stepBtn");
    await page.waitForFunction((tick) => {
      const text = document.querySelector("#statusLine")?.textContent || "";
      const match = text.match(/Tick\s+(\d+)/);
      return Boolean(match) && Number(match[1]) > tick;
    }, pausedStatus.tick, { timeout: 5000 });

    await page.click("#playPauseBtn");
    await page.waitForFunction(() => {
      const text = document.querySelector("#statusLine")?.textContent || "";
      return text.includes("播放中");
    }, null, { timeout: 5000 });

    const beforeReset = await readStatus(page);
    await page.click("#resetBtn");
    await page.waitForFunction((previousRevision) => {
      const text = document.querySelector("#statusLine")?.textContent || "";
      const match = text.match(/世界\s+(\d+)/);
      return Boolean(match) && Number(match[1]) > previousRevision;
    }, beforeReset.worldRevision, { timeout: 5000 });
    await page.waitForTimeout(400);

    const afterReset = await readStatus(page);
    if (afterReset.worldRevision <= beforeReset.worldRevision) {
      await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true });
      fail("World revision did not advance after reset", {
        beforeReset,
        afterReset,
        consoleErrors,
        pageErrors,
        serverLogs: server.logs,
        wsEvents,
        screenshot: SCREENSHOT_PATH,
      });
      return;
    }

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
      if (!metrics.statusText.includes("Tick ") || !metrics.statusText.includes("世界 ")) {
        checks.push(`status text missing expected fields: ${metrics.statusText}`);
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
        serverLogs: server.logs,
        wsEvents,
        screenshot: SCREENSHOT_PATH,
      });
      return;
    }

    console.log(
      JSON.stringify(
        {
          ok: true,
          beforeReset,
          afterReset,
          metrics,
          serverStarted: server.started,
          wsEvents,
          screenshot: SCREENSHOT_PATH,
        },
        null,
        2
      )
    );
  } finally {
    if (context) {
      await context.close();
    }
    if (browser) {
      await browser.close();
    }
    await stopServer(server.process);
  }
}

run().catch((error) => {
  fail("Unexpected Playwright runtime error", {
    error: String(error),
  });
});
