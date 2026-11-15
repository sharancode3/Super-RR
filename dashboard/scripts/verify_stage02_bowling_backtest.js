import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";

async function verifyStage02() {
  console.log("=== STAGE 02 AUTOMATED BOWLING BACKTEST VERIFICATION ===");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/#methodology", { waitUntil: "networkidle0" });

  // Navigate to Module 06
  await page.click("#tab-06-model-matrix");
  await new Promise((r) => setTimeout(r, 400));

  const mod06Text = await page.$eval("#panel-06-model-matrix", (el) => el.textContent);

  // 1. Verify Decision Gate & Retain Baseline
  if (!mod06Text.includes("Stage 02 Bowling Experiment: Challenging the Baseline")) {
    throw new Error("Missing Stage 02 Bowling Experiment header in Module 06.");
  }
  if (!mod06Text.includes("DECISION GATE: RETAIN BASELINE")) {
    throw new Error("Missing DECISION GATE: RETAIN BASELINE badge.");
  }
  console.log("✔ Stage 02 Decision Gate Verified: RETAIN BASELINE.");

  // 2. Verify Incumbent Baseline & Challenger metrics
  if (!mod06Text.includes("+1.26 r/12") || !mod06Text.includes("MAE 3.94")) {
    throw new Error("Missing Incumbent Baseline metrics in Module 06.");
  }
  if (!mod06Text.includes("Challenger 1 (Recency IPL)") || !mod06Text.includes("Challenger 2 (Shrunk Uplift)")) {
    throw new Error("Missing Challenger cards in Module 06.");
  }
  console.log("✔ Incumbent Baseline and Challenger metrics verified.");

  // 3. Verify Three Choice Pairs
  if (!mod06Text.includes("Ravindra Jadeja vs Anukul Roy") || !mod06Text.includes("Spin (Slot #10)")) {
    throw new Error("Missing Choice Pair A (Jadeja vs Roy) in Module 06.");
  }
  if (!mod06Text.includes("Trent Boult vs Mitchell Starc") || !mod06Text.includes("Powerplay Pace (Slot #7)")) {
    throw new Error("Missing Choice Pair B (Boult vs Starc) in Module 06.");
  }
  if (!mod06Text.includes("Ravindra Jadeja vs Deepak Chahar") || !mod06Text.includes("Slot #10 Tactical Allocation")) {
    throw new Error("Missing Choice Pair C (Jadeja vs Chahar) in Module 06.");
  }
  console.log("✔ All Three Choice Pairs verified (Jadeja vs Roy, Boult vs Starc, Jadeja vs Chahar).");

  // 4. Verify Disclosed Limitation
  if (!mod06Text.includes("−0.89 observed composite impact per offered slot") || !mod06Text.includes("four of ten")) {
    throw new Error("Missing Bowling Auction Replay limitation disclosure.");
  }
  console.log("✔ Disclosed Bowling Auction Replay limitation (-0.89 r/12, 4 assessed) verified.");

  // Capture screenshot of Module 06 with Bowling Experiment
  const mod06Element = await page.$("#panel-06-model-matrix");
  if (mod06Element) {
    const artifactDir = "C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061";
    await mod06Element.screenshot({
      path: path.join(artifactDir, "module06_bowling_backtest_audit.png"),
    });
    console.log("✔ Saved screenshot: module06_bowling_backtest_audit.png");
  }

  await browser.close();
  console.log("=== ALL STAGE 02 CHECKS PASSED SUCCESSFULLY ===");
}

verifyStage02().catch((err) => {
  console.error("Stage 02 verification failed:", err);
  process.exit(1);
});
