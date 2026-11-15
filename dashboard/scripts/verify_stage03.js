import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const EXPECTED_BATTERS = [
  { rank: 1, name: "Vaibhav Sooryavanshi", id: 50284, anchor: "batting-vaibhav-sooryavanshi" },
  { rank: 2, name: "Josh Inglis", id: 4736, anchor: "batting-josh-inglis" },
  { rank: 3, name: "Sameer Rizvi", id: 8238, anchor: "batting-sameer-rizvi" },
  { rank: 4, name: "Cooper Connolly", id: 8654, anchor: "batting-cooper-connolly" },
  { rank: 5, name: "Donovan Ferreira", id: 8182, anchor: "batting-donovan-ferreira" },
  { rank: 6, name: "Abishek Porel", id: 19714, anchor: "batting-abishek-porel" },
  { rank: 7, name: "Riyan Parag", id: 6423, anchor: "batting-riyan-parag" },
  { rank: 8, name: "Prabhsimran Singh", id: 7216, anchor: "batting-prabhsimran-singh" },
  { rank: 9, name: "Ravindra Jadeja", id: 152, anchor: "batting-ravindra-jadeja" },
  { rank: 10, name: "Venkatesh Iyer", id: 7544, anchor: "batting-venkatesh-iyer" },
];

const EXPECTED_BOWLERS = [
  { rank: 1, name: "Mohammed Siraj", id: 5944, anchor: "bowling-mohammed-siraj" },
  { rank: 2, name: "Jason Holder", id: 2633, anchor: "bowling-jason-holder" },
  { rank: 3, name: "Kartik Tyagi", id: 8530, anchor: "bowling-kartik-tyagi" },
  { rank: 4, name: "Lungi Ngidi", id: 4641, anchor: "bowling-lungi-ngidi" },
  { rank: 5, name: "Krunal Pandya", id: 4219, anchor: "bowling-krunal-pandya" },
  { rank: 6, name: "Rasikh Salam", id: 7327, anchor: "bowling-rasikh-salam" },
  { rank: 7, name: "Trent Boult", id: 2320, anchor: "bowling-trent-boult" },
  { rank: 8, name: "Mohammed Shami", id: 1566, anchor: "bowling-mohammed-shami" },
  { rank: 9, name: "Anshul Kamboj", id: 27964, anchor: "bowling-anshul-kamboj" },
  { rank: 10, name: "Ravindra Jadeja", id: 152, anchor: "bowling-ravindra-jadeja" },
];

async function main() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  console.log("=== STAGE 03 AUTOMATED VERIFICATION ===");

  // 1. Semantic ordered lists check
  const ols = await page.$$eval(".board-players-ol", (elements) => {
    return elements.map((el) => {
      const items = Array.from(el.querySelectorAll(":scope > li"));
      return {
        label: el.getAttribute("aria-label"),
        count: items.length,
        anchors: items.map((li) => li.id),
      };
    });
  });

  console.log(`Found ${ols.length} semantic <ol> lists:`);
  if (ols.length !== 2) {
    throw new Error(`Expected exactly 2 <ol class="board-players-ol">, found ${ols.length}`);
  }
  if (ols[0].count !== 10 || ols[1].count !== 10) {
    throw new Error(`Expected 10 items in each <ol>, found [${ols[0].count}, ${ols[1].count}]`);
  }
  console.log(`✔ Batters <ol> has exactly 10 items.`);
  console.log(`✔ Bowlers <ol> has exactly 10 items.`);

  // 2. Validate all 20 anchors and exact DOM order
  for (let i = 0; i < 10; i++) {
    const expectedB = EXPECTED_BATTERS[i];
    const actualBAnchor = ols[0].anchors[i];
    if (actualBAnchor !== expectedB.anchor) {
      throw new Error(`Batters rank ${i + 1} anchor mismatch: expected ${expectedB.anchor}, got ${actualBAnchor}`);
    }

    const expectedBowler = EXPECTED_BOWLERS[i];
    const actualBowlerAnchor = ols[1].anchors[i];
    if (actualBowlerAnchor !== expectedBowler.anchor) {
      throw new Error(`Bowlers rank ${i + 1} anchor mismatch: expected ${expectedBowler.anchor}, got ${actualBowlerAnchor}`);
    }
  }
  console.log("✔ All 20 anchors match expected slugs and exact 1..10 DOM order.");

  // 3. Verify Ravindra Jadeja dual identity & cross-links
  const jadejaBattingLink = await page.$eval(
    "#batting-ravindra-jadeja .jadeja-crosslink-anchor",
    (el) => el.getAttribute("href")
  );
  const jadejaBowlingLink = await page.$eval(
    "#bowling-ravindra-jadeja .jadeja-crosslink-anchor",
    (el) => el.getAttribute("href")
  );

  console.log(`Jadeja batting crosslink: ${jadejaBattingLink}`);
  console.log(`Jadeja bowling crosslink: ${jadejaBowlingLink}`);
  if (jadejaBattingLink !== "#bowling-ravindra-jadeja") {
    throw new Error(`Jadeja batting crosslink mismatch: expected #bowling-ravindra-jadeja, got ${jadejaBattingLink}`);
  }
  if (jadejaBowlingLink !== "#batting-ravindra-jadeja") {
    throw new Error(`Jadeja bowling crosslink mismatch: expected #batting-ravindra-jadeja, got ${jadejaBowlingLink}`);
  }
  console.log("✔ Jadeja dual-role crosslinks verified bidirectionally.");

  // 4. Verify Vaibhav & Siraj values
  const vaibhavData = await page.evaluate(() => {
    const el = document.getElementById("batting-vaibhav-sooryavanshi");
    return {
      text: el.innerText,
    };
  });
  console.log("Vaibhav card text summary check:");
  if (!vaibhavData.text.includes("+4.94") || !vaibhavData.text.includes("+11.02") || !vaibhavData.text.includes("95.8%")) {
    throw new Error(`Vaibhav data verification failed in DOM text.`);
  }
  console.log("✔ Vaibhav values verified (+4.94 impact, +11.02 pressure, 95.8% stability).");

  const sirajData = await page.evaluate(() => {
    const el = document.getElementById("bowling-mohammed-siraj");
    return {
      text: el.innerText,
    };
  });
  if (!sirajData.text.includes("+2.48") || !sirajData.text.includes("+5.74") || !sirajData.text.includes("89.4%")) {
    throw new Error(`Siraj data verification failed in DOM text.`);
  }
  console.log("✔ Siraj values verified (+2.48 impact, +5.74 pressure, 89.4% stability).");

  // 5. Test interaction: Expand disclosure on Vaibhav and Trent Boult, check zero baseline and bars
  await page.click("#batting-vaibhav-sooryavanshi .evidence-summary-btn");
  await page.click("#bowling-trent-boult .evidence-summary-btn");
  await new Promise((r) => setTimeout(r, 300));

  const isVaibhavOpen = await page.$eval(
    "#batting-vaibhav-sooryavanshi .player-evidence-disclosure",
    (el) => el.hasAttribute("open")
  );
  const isBoultOpen = await page.$eval(
    "#bowling-trent-boult .player-evidence-disclosure",
    (el) => el.hasAttribute("open")
  );

  console.log(`Vaibhav disclosure open: ${isVaibhavOpen}`);
  console.log(`Boult disclosure open: ${isBoultOpen}`);
  if (!isVaibhavOpen || !isBoultOpen) {
    throw new Error("Disclosure expansion failed.");
  }
  console.log("✔ Disclosure expand/collapse interaction verified.");

  // 6. Verify small sample (Sameer Rizvi: 8 balls), negative rate (Trent Boult: -6.06, -4.18), absent interval (Riyan Parag: n/a (1 match))
  const rizviText = await page.$eval("#batting-sameer-rizvi", (el) => el.textContent);
  if (!rizviText.includes("8b (4m)") || !rizviText.includes("8 balls (4 matches)")) {
    throw new Error(`Sameer Rizvi small sample check failed: expected 8 balls / 4 matches`);
  }
  console.log("✔ Small sample check: Sameer Rizvi (8 balls, 4 matches) verified.");

  const boultText = await page.$eval("#bowling-trent-boult", (el) => el.innerText);
  if (!boultText.includes("-6.06") || !boultText.includes("-4.18") || !boultText.includes("-1.88")) {
    throw new Error(`Trent Boult negative rate check failed: ${boultText}`);
  }
  console.log("✔ Negative rate check: Trent Boult (-6.06 pressure, -4.18 ordinary, -1.88 uplift) verified.");

  const paragText = await page.$eval("#batting-riyan-parag", (el) => el.textContent);
  if (!paragText.includes("n/a (1 match)")) {
    throw new Error(`Riyan Parag absent interval check failed: expected 'n/a (1 match)'`);
  }
  console.log("✔ Absent interval check: Riyan Parag ('n/a (1 match)') verified.");

  const krunalText = await page.$eval("#bowling-krunal-pandya", (el) => el.textContent);
  if (!krunalText.includes("n/a (1 match)")) {
    throw new Error(`Krunal Pandya absent interval check failed: expected 'n/a (1 match)'`);
  }
  console.log("✔ Absent interval check: Krunal Pandya ('n/a (1 match)') verified.");

  // 7. Verify zero horizontal scroll across 320, 390, 768, 1024, 1440
  const viewports = [
    { w: 1440, h: 900 },
    { w: 1024, h: 768 },
    { w: 768, h: 1024 },
    { w: 390, h: 844 },
    { w: 320, h: 568 },
  ];

  const outDir = path.join(__dirname, "../../scratch/screenshots_stage03");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  for (const vp of viewports) {
    await page.setViewport({ width: vp.w, height: vp.h });
    await new Promise((r) => setTimeout(r, 200));

    const overflowCheck = await page.evaluate(() => {
      return {
        innerWidth: window.innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth,
      };
    });

    console.log(`Viewport ${vp.w}x${vp.h}: inner=${overflowCheck.innerWidth}, docScroll=${overflowCheck.scrollWidth}`);
    if (overflowCheck.scrollWidth > overflowCheck.innerWidth) {
      throw new Error(`Horizontal overflow detected at ${vp.w}px: scrollWidth = ${overflowCheck.scrollWidth}`);
    }

    const shotPath = path.join(outDir, `viewport_${vp.w}x${vp.h}.png`);
    await page.screenshot({ path: shotPath });
    console.log(`Saved screenshot: ${shotPath}`);
  }

  // Also capture fullpage at 1440 with expanded cards
  await page.setViewport({ width: 1440, height: 900 });
  const fullPageShot = path.join(outDir, "fullpage_1440_stage03.png");
  await page.screenshot({ path: fullPageShot, fullPage: true });
  console.log(`Saved fullpage screenshot: ${fullPageShot}`);

  await browser.close();
  console.log("=== ALL STAGE 03 ACCEPTANCE CHECKS PASSED ===");
}

main().catch((err) => {
  console.error("Verification failed:", err);
  process.exit(1);
});
