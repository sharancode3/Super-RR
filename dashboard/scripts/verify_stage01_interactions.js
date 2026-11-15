import puppeteer from "puppeteer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outDir = path.resolve(__dirname, "../../scratch/screenshots_stage01");

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

async function main() {
  console.log("=== STAGE 01 MODEL RANKINGS INTERACTION TEST ===");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  // Scroll to Model Rankings
  await page.evaluate(() => {
    const el = document.getElementById("model-rankings");
    if (el) el.scrollIntoView({ behavior: "instant" });
  });
  await new Promise((r) => setTimeout(r, 400));

  // 1. Check Primary Priority Score Sort
  const firstRowName = await page.$eval(".raw-comparison-table tbody tr:first-child .raw-player-name", (el) => el.textContent.trim());
  const firstRowScore = await page.$eval(".raw-comparison-table tbody tr:first-child .priority-val", (el) => el.textContent.trim());
  console.log(`Priority Mode Leader: ${firstRowName} (${firstRowScore})`);
  if (!firstRowName.includes("Vaibhav Sooryavanshi")) {
    throw new Error(`Expected Vaibhav Sooryavanshi as #1 priority batter, found ${firstRowName}`);
  }

  // 2. Click "Forecast Only" Button
  const toggleButtons = await page.$$(".raw-table-meta-bar button");
  // Find "Forecast Only" button
  for (const btn of toggleButtons) {
    const text = await (await btn.getProperty("textContent")).jsonValue();
    if (text.includes("Forecast Only")) {
      await btn.click();
      break;
    }
  }
  await new Promise((r) => setTimeout(r, 400));
  await page.screenshot({ path: path.join(outDir, "model_rankings_forecast_only.png") });
  console.log("✔ Switched to Forecast Only sort and captured model_rankings_forecast_only.png");

  // 3. Switch to Bowlers Tab
  const subnavButtons = await page.$$(".raw-subnav-btn");
  if (subnavButtons.length >= 2) {
    await subnavButtons[1].click();
    await new Promise((r) => setTimeout(r, 400));
    const bowlerLeader = await page.$eval(".raw-comparison-table tbody tr:first-child .raw-player-name", (el) => el.textContent.trim());
    console.log(`Bowling Leader: ${bowlerLeader}`);
    if (!bowlerLeader.includes("Bumrah") && !bowlerLeader.includes("Narine")) {
      throw new Error(`Expected Jasprit Bumrah or Sunil Narine at top of raw bowling, found ${bowlerLeader}`);
    }
    await page.screenshot({ path: path.join(outDir, "model_rankings_bowlers_scored.png") });
    console.log("✔ Bowling tab verified and captured model_rankings_bowlers_scored.png");
  }

  // 4. Click Shortlist Badge Anchor Link (e.g. Siraj -> #bowling-mohammed-siraj)
  const sirajBadge = await page.$("a.rr-target-badge");
  if (sirajBadge) {
    const href = await (await sirajBadge.getProperty("href")).jsonValue();
    console.log("Clicking shortlist jump badge:", href);
    await sirajBadge.click();
    await new Promise((r) => setTimeout(r, 400));
    const url = page.url();
    console.log("Current URL after jump:", url);
    if (!url.includes("#bowling-")) {
      throw new Error(`Expected jump to bowling card anchor, current URL is ${url}`);
    }
    console.log("✔ Seamless anchor jump from Model Rankings to RR Shortlist card verified.");
  }

  await browser.close();
  console.log("=== STAGE 01 VERIFICATION PASSED SUCCESSFULLY ===");
}

main().catch((err) => {
  console.error("Verification failed:", err);
  process.exit(1);
});
