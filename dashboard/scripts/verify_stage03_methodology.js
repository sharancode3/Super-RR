import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";

async function verifyStage03() {
  console.log("=== STAGE 03 COMPREHENSIVE METHODOLOGY & EVIDENCE AUDIT ===");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/#methodology", { waitUntil: "networkidle0" });

  const artifactDir = "C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061";

  // 1. STORY POINT 1: THE QUESTION
  await page.click("#tab-01-what-rr-asked");
  await new Promise((r) => setTimeout(r, 300));
  const mod01Text = await page.$eval("#panel-01-what-rr-asked", (el) => el.textContent);
  if (!mod01Text.includes("We compared how players perform in high-pressure situations with their usual performance and shortlisted roles RR could back.")) {
    throw new Error("Story Point 1: Missing core question sentence.");
  }
  if (!mod01Text.includes("10 batters") || !mod01Text.includes("10 bowlers") || !mod01Text.includes("15 November 2026")) {
    throw new Error("Story Point 1: Missing list or cutoff definitions.");
  }
  const unstopLink = await page.$eval("#panel-01-what-rr-asked a.external-audit-link", (el) => el.href);
  if (!unstopLink.includes("unstop.com/hackathons/crp-superr-selector-season-2")) {
    throw new Error("Story Point 1: Missing or invalid Unstop challenge link.");
  }
  console.log("✔ Story Point 1 (The Question) verified.");

  // 2. STORY POINT 2: TIMELINE & EARLIER EXPERIMENTS
  await page.click("#tab-02-timeline");
  await new Promise((r) => setTimeout(r, 300));
  const mod02Text = await page.$eval("#panel-02-timeline", (el) => el.textContent);
  if (
    !mod02Text.includes("10–11 Nov 2026") ||
    !mod02Text.includes("12–13 Nov 2026") ||
    !mod02Text.includes("14 Nov 2026") ||
    !mod02Text.includes("15 Nov 2026 (IST)") ||
    !mod02Text.includes("15 Nov 2026 (Evening)") ||
    !mod02Text.includes("232 unit") ||
    !mod02Text.includes("33 targeted")
  ) {
    throw new Error("Story Point 2: Missing timeline milestones or test counts.");
  }
  console.log("✔ Story Point 2 (Timeline & Milestones) verified.");

  // 3. STORY POINT 3: DATA & PREPARATION
  await page.click("#tab-03-data-transformations");
  await new Promise((r) => setTimeout(r, 300));
  const mod03Text = await page.$eval("#panel-03-data-transformations", (el) => el.textContent);
  if (
    !mod03Text.includes("200,999") ||
    !mod03Text.includes("806") ||
    !mod03Text.includes("168,632") ||
    !mod03Text.includes("708") ||
    !mod03Text.includes("4,793 delivery pressure flags") ||
    !mod03Text.includes("264 ambiguous no-ball events") ||
    !mod03Text.includes("6 of 6 Verified Chase Targets") ||
    !mod03Text.includes("67,577") || // IPL balls
    !mod03Text.includes("94,589")    // T20I balls
  ) {
    throw new Error("Story Point 3: Missing data funnel counts or IPL vs T20I verified aggregates.");
  }
  console.log("✔ Story Point 3 (Data & Preparation with IPL vs T20I) verified.");

  // 4. STORY POINT 4: PRESSURE & IMPACT
  await page.click("#tab-04-pressure-definition");
  await new Promise((r) => setTimeout(r, 300));
  const mod04Text = await page.$eval("#panel-04-pressure-definition", (el) => el.textContent);
  if (
    !mod04Text.includes("Before the ball, we estimate how much realistic next-ball outcomes could move the match.") ||
    !mod04Text.includes("rr_pressure/pressure.py") ||
    !mod04Text.includes("RCB vs MI · Match 54") ||
    !mod04Text.includes("167 runs") ||
    !mod04Text.includes("0.336") ||
    !mod04Text.includes("0.082")
  ) {
    throw new Error("Story Point 4: Missing pressure estimation sentence, pressure.py link, or Match 54 facts.");
  }
  console.log("✔ Story Point 4 (Pressure Leverage, Code Link & Match 54 Worked Example) verified.");

  // 5. STORY POINT 5: TRAINING & EVALUATION
  await page.click("#tab-06-model-matrix");
  await new Promise((r) => setTimeout(r, 300));
  const mod06Text = await page.$eval("#panel-06-model-matrix", (el) => el.textContent);
  if (
    !mod06Text.includes("482 matches") ||
    !mod06Text.includes("191 in 2025") ||
    !mod06Text.includes("133 in 2026") ||
    !mod06Text.includes("160 comparison rows") ||
    !mod06Text.includes("4.87") ||
    !mod06Text.includes("Stage 02 Bowling Experiment: Challenging the Baseline") ||
    !mod06Text.includes("DECISION GATE: RETAIN BASELINE") ||
    !mod06Text.includes("−0.89 observed composite impact")
  ) {
    throw new Error("Story Point 5: Missing chronological cohorts, 160 matrix rows, Stage 02 gate, or auction limitation.");
  }
  console.log("✔ Story Point 5 (Training, 160 Matrix, Stage 02 Gate & Limitation) verified.");

  // 6. STORY POINT 6: FROM MODEL TO RR
  await page.click("#tab-09-raw-model-ranks");
  await new Promise((r) => setTimeout(r, 300));
  const mod09Text = await page.$eval("#panel-09-raw-model-ranks", (el) => el.textContent);
  if (
    !mod09Text.includes("Stepped Selection Pipeline") ||
    !mod09Text.includes("248 Scored Players") ||
    !mod09Text.includes("Jasprit Bumrah") ||
    !mod09Text.includes("Ravindra Jadeja") ||
    !mod09Text.includes("Deepak Chahar") ||
    !mod09Text.includes("2 spinners") ||
    !mod09Text.includes("-0.49 r/12")
  ) {
    throw new Error("Story Point 6: Missing stepped visual, Bumrah exclusion, or Jadeja 2-spinner quota movement.");
  }
  console.log("✔ Story Point 6 (From Model to RR: Stepped Visual, Bumrah & Jadeja Transformations) verified.");

  // 7. STORY POINT 7: HOW SURE ARE WE?
  await page.click("#tab-07-confidence-stability");
  await new Promise((r) => setTimeout(r, 300));
  const mod07Text = await page.$eval("#panel-07-confidence-stability", (el) => el.textContent);
  if (
    !mod07Text.includes("95.8%") ||
    !mod07Text.includes("89.4%") ||
    !mod07Text.includes("0 of 1,000 Repeats") ||
    !mod07Text.includes("0.0%") ||
    !mod07Text.includes("Trent Boult (#7) vs Mitchell Starc") ||
    !mod07Text.includes("Prabhsimran Singh (#8) vs KL Rahul")
  ) {
    throw new Error("Story Point 7: Missing uncertainty layers, counts with percentages, or close calls.");
  }
  console.log("✔ Story Point 7 (Uncertainty Layers, Exact Concordance & Close Calls) verified.");

  // Capture Screenshot of Module 09 Stepped Transformation
  await page.click("#tab-09-raw-model-ranks");
  await new Promise((r) => setTimeout(r, 300));
  const mod09El = await page.$("#panel-09-raw-model-ranks");
  if (mod09El) {
    await mod09El.screenshot({
      path: path.join(artifactDir, "module09_stepped_transformation_audit.png"),
    });
    console.log("✔ Saved screenshot: module09_stepped_transformation_audit.png");
  }

  // Capture Screenshot of Module 03 Data Funnel & Tier Comparison
  await page.click("#tab-03-data-transformations");
  await new Promise((r) => setTimeout(r, 300));
  const mod03El = await page.$("#panel-03-data-transformations");
  if (mod03El) {
    await mod03El.screenshot({
      path: path.join(artifactDir, "module03_data_funnel_and_tier_comparison.png"),
    });
    console.log("✔ Saved screenshot: module03_data_funnel_and_tier_comparison.png");
  }

  await browser.close();
  console.log("=== ALL STAGE 03 ACCEPTANCE CHECKS PASSED SUCCESSFULLY ===");
}

verifyStage03().catch((err) => {
  console.error("Stage 03 verification failed:", err);
  process.exit(1);
});
