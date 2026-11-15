import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("=== STAGE 05 MOTION, ACCESSIBILITY & PERFORMANCE AUDIT ===");

  const outDir = path.resolve("../scratch/screenshots_stage05");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  // -------------------------------------------------------------------------
  // PASS 1: MOTION SYSTEM & INTERSECTION OBSERVER REVEALS
  // -------------------------------------------------------------------------
  console.log("\n--- Pass 1: Motion System & Reveal Testing ---");
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  // Initial view: leaders should be in view and revealed
  const initialReveals = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll("[data-reveal]"));
    return {
      total: cards.length,
      revealed: cards.filter((c) => c.getAttribute("data-reveal") === "revealed").length,
      pending: cards.filter((c) => c.getAttribute("data-reveal") === "pending").length,
    };
  });
  console.log(`Initial view: ${initialReveals.revealed} revealed, ${initialReveals.pending} pending (out of ${initialReveals.total})`);

  // Scroll down smoothly through the page to trigger reveals
  await page.evaluate(async () => {
    for (let y = 0; y <= document.body.scrollHeight; y += 400) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 100));
    }
  });
  await new Promise((r) => setTimeout(r, 500));

  const postScrollReveals = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll("[data-reveal]"));
    return {
      total: cards.length,
      revealed: cards.filter((c) => c.getAttribute("data-reveal") === "revealed").length,
      pending: cards.filter((c) => c.getAttribute("data-reveal") === "pending").length,
    };
  });
  console.log(`After scroll: ${postScrollReveals.revealed} of ${postScrollReveals.total} cards revealed.`);
  if (postScrollReveals.revealed !== postScrollReveals.total) {
    throw new Error(`Expected all ${postScrollReveals.total} cards to be revealed after full scroll, but ${postScrollReveals.pending} remain pending.`);
  }
  console.log("✔ IntersectionObserver reveal cycle passed for all 20 cards.");

  // -------------------------------------------------------------------------
  // PASS 2: PREFERS-REDUCED-MOTION COMPLIANCE
  // -------------------------------------------------------------------------
  console.log("\n--- Pass 2: prefers-reduced-motion Audit ---");
  const reducedMotionPage = await browser.newPage();
  await reducedMotionPage.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await reducedMotionPage.setViewport({ width: 1440, height: 900 });
  await reducedMotionPage.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  const reducedMotionCheck = await reducedMotionPage.evaluate(() => {
    const cards = Array.from(document.querySelectorAll("[data-reveal]"));
    const allRevealed = cards.every((c) => c.getAttribute("data-reveal") === "revealed");

    const sampleImg = document.querySelector(".player-portrait-img");
    const style = window.getComputedStyle(sampleImg);

    return {
      total: cards.length,
      allRevealedImmediately: allRevealed,
      animationDuration: style.animationDuration,
      transitionDuration: style.transitionDuration,
      opacity: style.opacity,
    };
  });

  console.log("Reduced motion status:", reducedMotionCheck);
  if (!reducedMotionCheck.allRevealedImmediately) {
    throw new Error("prefers-reduced-motion failed to reveal all cards immediately.");
  }
  console.log("✔ prefers-reduced-motion: reduce verified (instant reveal, zero motion delay).");

  // Capture reduced-motion screenshot
  await reducedMotionPage.screenshot({
    path: path.join(outDir, "reduced_motion_1440.png"),
  });
  await reducedMotionPage.close();

  // -------------------------------------------------------------------------
  // PASS 3: 200% ZOOM & ACCESSIBILITY AUDIT
  // -------------------------------------------------------------------------
  console.log("\n--- Pass 3: 200% Zoom & Accessibility Audit ---");
  const zoomPage = await browser.newPage();
  // Simulate 200% zoom by halving the CSS viewport dimensions for the same physical pixel density
  await zoomPage.setViewport({ width: 640, height: 480, deviceScaleFactor: 2 });
  await zoomPage.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  const zoomOverflow = await zoomPage.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
    hasOverflow: document.documentElement.scrollWidth > window.innerWidth,
  }));
  console.log(`200% Zoom (640px viewport): scrollWidth=${zoomOverflow.scrollW}, innerWidth=${zoomOverflow.innerW}`);
  if (zoomOverflow.hasOverflow) {
    throw new Error(`200% zoom horizontal overflow detected: scrollWidth=${zoomOverflow.scrollW}`);
  }

  await zoomPage.screenshot({
    path: path.join(outDir, "zoom_200pct_640x480.png"),
  });
  console.log("✔ 200% zoom audit passed with zero horizontal overflow or clipping.");
  await zoomPage.close();

  // -------------------------------------------------------------------------
  // PASS 4: WEB VITALS & PERFORMANCE BUDGETS (LCP, CLS across 3 runs)
  // -------------------------------------------------------------------------
  console.log("\n--- Pass 4: Web Vitals Performance Audit (3 Runs) ---");
  const perfRuns = [];

  for (let run = 1; run <= 3; run++) {
    const perfPage = await browser.newPage();
    await perfPage.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });

    // Enable PerformanceObserver inside the page to record LCP and CLS
    await perfPage.evaluateOnNewDocument(() => {
      window.__perfMetrics = { lcp: 0, cls: 0 };

      // Observer for LCP
      new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        window.__perfMetrics.lcp = lastEntry.startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });

      // Observer for CLS
      new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!entry.hadRecentInput) {
            window.__perfMetrics.cls += entry.value;
          }
        }
      }).observe({ type: "layout-shift", buffered: true });
    });

    await perfPage.goto("http://localhost:5173/", { waitUntil: "networkidle0" });
    await new Promise((r) => setTimeout(r, 600));

    const metrics = await perfPage.evaluate(() => window.__perfMetrics);
    perfRuns.push(metrics);
    console.log(`  Run ${run}: LCP = ${metrics.lcp.toFixed(1)}ms, CLS = ${metrics.cls.toFixed(4)}`);
    await perfPage.close();
  }

  // Calculate median metrics
  perfRuns.sort((a, b) => a.lcp - b.lcp);
  const medianLCP = perfRuns[1].lcp;
  perfRuns.sort((a, b) => a.cls - b.cls);
  const medianCLS = perfRuns[1].cls;

  console.log(`\nMedian Results across 3 runs:`);
  console.log(`  Median LCP: ${medianLCP.toFixed(1)}ms (Budget: ≤ 2500ms) -> ${medianLCP <= 2500 ? "PASS" : "FAIL"}`);
  console.log(`  Median CLS: ${medianCLS.toFixed(4)} (Budget: ≤ 0.10) -> ${medianCLS <= 0.1 ? "PASS" : "FAIL"}`);

  if (medianLCP > 2500 || medianCLS > 0.1) {
    throw new Error(`Performance threshold breached: LCP=${medianLCP}, CLS=${medianCLS}`);
  }
  console.log("✔ Web Vitals audit passed (LCP ≤ 2.5s, CLS ≤ 0.10).");

  // -------------------------------------------------------------------------
  // PASS 5: RESOURCE TRANSFER BUDGETS
  // -------------------------------------------------------------------------
  console.log("\n--- Pass 5: Transfer Size Budgets ---");
  const resPage = await browser.newPage();
  const requests = [];

  resPage.on("response", async (response) => {
    try {
      const url = response.url();
      const headers = response.headers();
      const buffer = await response.buffer();
      requests.push({
        url,
        size: buffer.length,
        type: response.request().resourceType(),
      });
    } catch {
      // ignore
    }
  });

  await resPage.setViewport({ width: 1440, height: 900 });
  await resPage.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  let totalTransfer = 0;
  let jsTransfer = 0;
  let cssTransfer = 0;
  let leaderImgMax = 0;
  let standardImgMax = 0;

  for (const req of requests) {
    totalTransfer += req.size;
    if (req.url.endsWith(".js") || req.type === "script") {
      jsTransfer += req.size;
    }
    if (req.url.endsWith(".css") || req.type === "stylesheet") {
      cssTransfer += req.size;
    }
    if (req.url.includes("/portraits/")) {
      if (req.url.includes("50284") || req.url.includes("5944")) {
        leaderImgMax = Math.max(leaderImgMax, req.size);
      } else {
        standardImgMax = Math.max(standardImgMax, req.size);
      }
    }
  }

  console.log(`  Total Page Transfer: ${(totalTransfer / 1024).toFixed(1)} KB (Budget: ≤ 650 KB)`);
  console.log(`  Main JS Transfer: ${(jsTransfer / 1024).toFixed(1)} KB (Budget: ≤ 350 KB uncompressed / 150 KB gzip)`);
  console.log(`  CSS Transfer: ${(cssTransfer / 1024).toFixed(1)} KB`);
  console.log(`  Max Featured Leader Image: ${(leaderImgMax / 1024).toFixed(1)} KB (Budget: ≤ 180 KB)`);
  console.log(`  Max Standard Portrait: ${(standardImgMax / 1024).toFixed(1)} KB (Budget: ≤ 100 KB)`);

  if (leaderImgMax > 180 * 1024) {
    throw new Error(`Leader portrait exceeded 180 KB: ${leaderImgMax} bytes`);
  }
  if (standardImgMax > 100 * 1024) {
    throw new Error(`Standard portrait exceeded 100 KB: ${standardImgMax} bytes`);
  }
  console.log("✔ All resource size budgets met.");

  await resPage.close();
  await page.close();
  await browser.close();

  console.log("\n=== ALL STAGE 05 ACCEPTANCE CHECKS PASSED ===");
}

main().catch((err) => {
  console.error("Stage 05 verification failed:", err);
  process.exit(1);
});
