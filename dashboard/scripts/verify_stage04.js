import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  console.log("=== STAGE 04 AUTOMATED VERIFICATION ===");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  // 1. Two-Speed Read Check
  const fastReadSteps = await page.$$eval(".fast-read-card .step-card", (els) =>
    els.map((el) => ({
      num: el.querySelector(".step-num")?.textContent.trim(),
      title: el.querySelector(".step-title")?.textContent.trim(),
    }))
  );

  console.log(`Found ${fastReadSteps.length} fast-read pipeline steps:`);
  fastReadSteps.forEach((s) => console.log(`  Step ${s.num}: ${s.title}`));
  if (fastReadSteps.length !== 5) {
    throw new Error(`Expected exactly 5 fast-read pipeline steps, found ${fastReadSteps.length}`);
  }
  console.log("✔ 60-Second Fast Read pipeline verified.");

  // 2. Module 01: What RR Asked
  await page.click("#tab-01-what-rr-asked");
  await new Promise((r) => setTimeout(r, 200));
  const mod01Text = await page.$eval("#panel-01-what-rr-asked", (el) => el.textContent);
  if (
    !mod01Text.includes("15 November 2026") ||
    !mod01Text.includes("10 batters") ||
    !mod01Text.includes("10 bowlers") ||
    !mod01Text.includes("Freedom to Define Pressure")
  ) {
    throw new Error("Module 01 content verification failed.");
  }
  console.log("✔ Module 01 (What RR Asked) verified.");

  // 3. Module 02: Timeline (10–15 Nov IST)
  await page.click("#tab-02-timeline");
  await new Promise((r) => setTimeout(r, 200));
  const mod02Text = await page.$eval("#panel-02-timeline", (el) => el.textContent);
  if (
    !mod02Text.includes("10–11 Nov 2026") ||
    !mod02Text.includes("15 Nov 2026 (IST)") ||
    !mod02Text.includes("232 automated tests") ||
    !mod02Text.includes("33 contract tests")
  ) {
    throw new Error("Module 02 content verification failed.");
  }
  console.log("✔ Module 02 (Project Timeline 10–15 Nov IST) verified.");

  // 4. Module 03: Data & Transformations
  await page.click("#tab-03-data-transformations");
  await new Promise((r) => setTimeout(r, 200));
  const mod03Text = await page.$eval("#panel-03-data-transformations", (el) => el.textContent);
  if (
    !mod03Text.includes("200,999") ||
    !mod03Text.includes("806") ||
    !mod03Text.includes("168,632") ||
    !mod03Text.includes("6 of 6") ||
    !mod03Text.includes("4,793") ||
    !mod03Text.includes("264 ambiguous no-ball")
  ) {
    throw new Error("Module 03 content verification failed.");
  }
  console.log("✔ Module 03 (Data Funnel, Scorecards & Ingest) verified.");

  // 5. Module 04: Pressure Definition & Worked Chase Example
  await page.click("#tab-04-pressure-definition");
  await new Promise((r) => setTimeout(r, 200));
  const mod04Text = await page.$eval("#panel-04-pressure-definition", (el) => el.textContent);
  if (
    !mod04Text.includes("RCB vs MI") ||
    !mod04Text.includes("154/5") ||
    !mod04Text.includes("42.0%") ||
    !mod04Text.includes("19.0 percentage points") ||
    !mod04Text.includes("8.2 percentage points") ||
    !mod04Text.includes("HIGH PRESSURE")
  ) {
    throw new Error("Module 04 content verification failed.");
  }
  console.log("✔ Module 04 (Pressure Definition & Worked Chase Example) verified.");

  // 6. Module 05: Player Forecasting & Ensembling
  await page.click("#tab-05-player-forecast");
  await new Promise((r) => setTimeout(r, 200));
  const mod05Text = await page.$eval("#panel-05-player-forecast", (el) => el.textContent);
  if (
    !mod05Text.includes("75% Pressure Impact + 25% Ordinary Impact") ||
    !mod05Text.includes("Josh Inglis") ||
    !mod05Text.includes("+13.49 r/12") ||
    !mod05Text.includes("+4.92 r/12") ||
    !mod05Text.includes("+4.70 r/12")
  ) {
    throw new Error("Module 05 content verification failed.");
  }
  console.log("✔ Module 05 (Forecasting, Shrinkage & Inglis Rate Comparison) verified.");

  // 7. Module 06: Model Matrix & Replays
  await page.click("#tab-06-model-matrix");
  await new Promise((r) => setTimeout(r, 200));
  const mod06Text = await page.$eval("#panel-06-model-matrix", (el) => el.textContent);
  if (
    !mod06Text.includes("160 comparison rows") ||
    !mod06Text.includes("Challenger D") ||
    !mod06Text.includes("4.87") ||
    !mod06Text.includes("−0.89 observed composite impact")
  ) {
    throw new Error("Module 06 content verification failed.");
  }
  console.log("✔ Module 06 (160 Model Matrix, Split-Target Rejection & Auction Limitation) verified.");

  // 8. Module 07: Reading Confidence
  await page.click("#tab-07-confidence-stability");
  await new Promise((r) => setTimeout(r, 200));
  const mod07Text = await page.$eval("#panel-07-confidence-stability", (el) => el.textContent);
  if (
    !mod07Text.includes("95.8%") ||
    !mod07Text.includes("89.4%") ||
    !mod07Text.includes("0 of 1,000") ||
    !mod07Text.includes("Trent Boult (#7) vs Mitchell Starc") ||
    !mod07Text.includes("Prabhsimran Singh (#8) vs KL Rahul")
  ) {
    throw new Error("Module 07 content verification failed.");
  }
  console.log("✔ Module 07 (Confidence Layers, Bootstrap & Close Calls) verified.");

  // 9. Module 08: Auction Scenarios & Interactive Switcher
  await page.click("#tab-08-auction-contingencies");
  await new Promise((r) => setTimeout(r, 200));

  // Test Scenario A: Gujarat keeps Siraj & Holder
  const scenarioBtns = await page.$$(".scenario-btn");
  console.log(`Found ${scenarioBtns.length} scenario contingency buttons.`);

  // Click Scenario A (button 1)
  await scenarioBtns[1].click();
  await new Promise((r) => setTimeout(r, 200));
  const scAText = await page.$eval(".scenario-dynamic-display", (el) => el.textContent);
  if (
    !scAText.includes("Deepak Chahar") ||
    !scAText.includes("Mitchell Starc") ||
    !scAText.includes("Mohammed Siraj (#1)")
  ) {
    throw new Error("Scenario A interactive replacement verification failed.");
  }
  console.log("✔ Scenario A (GT keeps Siraj & Holder -> Chahar & Starc enter) verified.");

  // Click Scenario C: No new overseas bowling slot (button 3)
  await scenarioBtns[3].click();
  await new Promise((r) => setTimeout(r, 200));
  const scCText = await page.$eval(".scenario-dynamic-display", (el) => el.textContent);
  if (
    !scCText.includes("Avesh Khan") ||
    !scCText.includes("Deepak Chahar") ||
    !scCText.includes("Jofra Archer")
  ) {
    throw new Error("Scenario C interactive replacement verification failed.");
  }
  console.log("✔ Scenario C (No overseas bowling -> Avesh, Chahar & Archer enter) verified.");

  // Click Scenario D: No new overseas batting slot (button 4)
  await scenarioBtns[4].click();
  await new Promise((r) => setTimeout(r, 200));
  const scDText = await page.$eval(".scenario-dynamic-display", (el) => el.textContent);
  if (
    !scDText.includes("Aniket Verma") ||
    !scDText.includes("KL Rahul")
  ) {
    throw new Error("Scenario D interactive replacement verification failed.");
  }
  console.log("✔ Scenario D (No overseas batting -> Verma & Rahul enter) verified.");

  // 10. Responsive Verification across 5 viewports
  const viewports = [
    { w: 1440, h: 900 },
    { w: 1024, h: 768 },
    { w: 768, h: 1024 },
    { w: 390, h: 844 },
    { w: 320, h: 568 },
  ];

  const outDir = path.resolve("../scratch/screenshots_stage04");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  for (const vp of viewports) {
    await page.setViewport({ width: vp.w, height: vp.h });
    await new Promise((r) => setTimeout(r, 150));
    const check = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      hasOverflow: document.documentElement.scrollWidth > window.innerWidth,
    }));

    console.log(`Viewport ${vp.w}x${vp.h} -> scrollWidth=${check.scrollW}, innerWidth=${check.innerW}, overflow=${check.hasOverflow}`);
    if (check.hasOverflow) {
      throw new Error(`Overflow detected at ${vp.w}px`);
    }

    const shotPath = path.join(outDir, `viewport_${vp.w}x${vp.h}_stage04.png`);
    await page.screenshot({ path: shotPath });
  }

  // Fullpage screenshot at 1440
  await page.setViewport({ width: 1440, height: 900 });
  const fullPath = path.join(outDir, "fullpage_1440_stage04.png");
  await page.screenshot({ path: fullPath, fullPage: true });
  console.log(`Saved fullpage screenshot: ${fullPath}`);

  await browser.close();
  console.log("=== ALL STAGE 04 ACCEPTANCE CHECKS PASSED ===");
}

main().catch((err) => {
  console.error("Verification failed:", err);
  process.exit(1);
});
