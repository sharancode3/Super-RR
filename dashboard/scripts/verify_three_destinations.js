import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const outDir = path.resolve(__dirname, "../../scratch/screenshots_destinations");

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

async function main() {
  console.log("=== THREE DESTINATIONS AUDIT & SCREENSHOT CAPTURE ===");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  // 1. Audit Navigation Links
  const navLinks = await page.$$eval(".primary-nav .nav-link", (els) =>
    els.map((el) => ({
      text: el.textContent.trim(),
      href: el.getAttribute("href"),
    }))
  );
  console.log("Primary nav links:", navLinks);

  // Take screenshot of Destination 1: Hero & Shortlist
  await page.screenshot({ path: path.join(outDir, "destination_01_shortlist.png") });
  console.log("✔ Saved destination_01_shortlist.png");

  // 2. Destination 2: Model Rankings
  await page.evaluate(() => {
    const el = document.getElementById("model-rankings");
    if (el) el.scrollIntoView({ behavior: "instant" });
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.screenshot({ path: path.join(outDir, "destination_02_model_rankings_batters.png") });
  console.log("✔ Saved destination_02_model_rankings_batters.png");

  // Switch to Bowlers tab
  const buttons = await page.$$(".raw-subnav-btn");
  if (buttons.length >= 2) {
    await buttons[1].click();
    await new Promise((r) => setTimeout(r, 400));
    await page.screenshot({ path: path.join(outDir, "destination_02_model_rankings_bowlers.png") });
    console.log("✔ Saved destination_02_model_rankings_bowlers.png");
  }

  // Switch to Filters tab
  if (buttons.length >= 3) {
    await buttons[2].click();
    await new Promise((r) => setTimeout(r, 400));
    await page.screenshot({ path: path.join(outDir, "destination_02_model_rankings_pillars.png") });
    console.log("✔ Saved destination_02_model_rankings_pillars.png");
  }

  // 3. Destination 3: Methodology
  await page.evaluate(() => {
    const el = document.getElementById("methodology");
    if (el) el.scrollIntoView({ behavior: "instant" });
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.screenshot({ path: path.join(outDir, "destination_03_methodology.png") });
  console.log("✔ Saved destination_03_methodology.png");

  // Check return bar
  const hasReturnBar = await page.$eval("#methodology-return-bar", (el) => !!el);
  console.log("Methodology return bar exists:", hasReturnBar);

  await browser.close();
  console.log("=== THREE DESTINATIONS AUDIT COMPLETE ===");
}

main().catch((err) => {
  console.error("Audit failed:", err);
  process.exit(1);
});
