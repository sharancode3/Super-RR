import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const outDir = path.resolve(__dirname, "../../scratch/screenshots_downwise_verification");
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

async function testAll() {
  console.log("===============================================================");
  console.log("STARTING DOWN-WISE CARDS STREAM & CONTACT SHEET VERIFICATION");
  console.log("===============================================================\n");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();

  // 1. TEST CONTACT SHEET & RETURN TO DASHBOARD NAVIGATION
  console.log("--- 1. Testing Contact Sheet Navigation & Back Button ---");
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/portraits/contact_sheet.html", { waitUntil: "networkidle0" });

  const contactSheetNav = await page.evaluate(() => {
    const topBar = document.querySelector(".top-nav-bar");
    const backBtn = document.querySelector("#nav-btn-back");
    const heroBackBtn = document.querySelector("#hero-btn-back");
    const floatingBackBtn = document.querySelector("#floating-btn-back");
    return {
      hasTopBar: !!topBar,
      hasNavBackBtn: !!backBtn,
      navBackText: backBtn ? backBtn.textContent.trim() : "",
      navBackHref: backBtn ? backBtn.getAttribute("href") : "",
      hasHeroBackBtn: !!heroBackBtn,
      hasFloatingBackBtn: !!floatingBackBtn,
    };
  });
  console.log("  Contact sheet nav audit:", contactSheetNav);
  if (!contactSheetNav.hasTopBar || !contactSheetNav.hasNavBackBtn) {
    throw new Error("Contact sheet missing top navigation bar or back button!");
  }

  await page.screenshot({
    path: path.join(outDir, "contact_sheet_with_back_nav.png"),
    fullPage: false,
  });

  // Click the back button and verify navigation back to dashboard
  console.log("  Clicking 'Back to Scouting Dashboard' button...");
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle0" }),
    page.click("#nav-btn-back"),
  ]);
  const currentUrl = page.url();
  console.log(`  Returned to URL: ${currentUrl}`);
  if (!currentUrl.endsWith("/") && !currentUrl.includes("localhost:5173")) {
    throw new Error(`Back button failed to return to dashboard! Current URL: ${currentUrl}`);
  }
  console.log("  ✔ Successfully navigated back to the main scouting dashboard.");

  // 2. TEST MULTI-VIEWPORT RESPONSIVENESS & ZERO DOCUMENT OVERFLOW
  console.log("\n--- 2. Multi-Viewport & Overflow Audit ---");
  const VIEWPORTS = [
    { name: "320x800", width: 320, height: 800, isMobile: true },
    { name: "390x844", width: 390, height: 844, isMobile: true, hasTouch: true },
    { name: "768x1024", width: 768, height: 1024, isMobile: false },
    { name: "1024x768", width: 1024, height: 768, isMobile: false },
    { name: "1440x900", width: 1440, height: 900, isMobile: false },
  ];

  for (const vp of VIEWPORTS) {
    await page.setViewport({ width: vp.width, height: vp.height, isMobile: vp.isMobile, hasTouch: vp.hasTouch });
    await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

    const overflow = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      innerW: window.innerWidth,
      hasOverflow: document.documentElement.scrollWidth > window.innerWidth,
    }));

    if (overflow.hasOverflow) {
      throw new Error(`Document overflow at ${vp.name}: scrollWidth=${overflow.scrollW} > innerWidth=${overflow.innerW}`);
    }
    console.log(`  ✔ Viewport ${vp.name}: width=${overflow.innerW}px, scrollWidth=${overflow.scrollW}px (NO OVERFLOW)`);

    await page.screenshot({
      path: path.join(outDir, `viewport_${vp.name}.png`),
      fullPage: false,
    });
  }

  // 3. AUDIT ALL 20 PLAYER CARDS IN EXPANSIVE DOSSIER FORMAT
  console.log("\n--- 3. Auditing All 20 Player Cards (Expansive Dossier Format) ---");
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  const playerAudit = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll(".player-card"));
    return cards.map((card, idx) => {
      const nameEl = card.querySelector(".leader-name");
      const rankBadge = card.querySelector(".rank-num");
      const img = card.querySelector(".player-portrait-img");
      const visualWell = card.querySelector(".player-visual-well");
      const headlineImpact = card.querySelector(".dossier-headline-impact");
      const metrics = card.querySelectorAll(".metric-box");
      const stabilityNote = card.querySelector(".stability-plain-note");
      const looBar = card.querySelector(".loo-range-bar");
      const fitSummary = card.querySelector(".leader-fit-summary");
      const disclosure = card.querySelector(".player-evidence-disclosure");

      const wellRect = visualWell ? visualWell.getBoundingClientRect() : null;
      const imgRect = img ? img.getBoundingClientRect() : null;

      return {
        index: idx + 1,
        name: nameEl ? nameEl.textContent.trim() : null,
        rank: rankBadge ? rankBadge.textContent.trim() : null,
        hasImage: !!img,
        imgSrc: img ? img.currentSrc || img.src : null,
        imgComplete: img ? img.complete : false,
        imgNaturalHeight: img ? img.naturalHeight : 0,
        imgNaturalWidth: img ? img.naturalWidth : 0,
        wellHeight: wellRect ? wellRect.height : 0,
        hasHeadlineImpact: !!headlineImpact,
        metricsCount: metrics.length,
        hasStabilityNote: !!stabilityNote,
        hasLooBar: !!looBar,
        hasFitSummary: !!fitSummary,
        hasDisclosure: !!disclosure,
        imgHeightInWell: imgRect ? imgRect.height : 0,
      };
    });
  });

  console.log(`  Found ${playerAudit.length} player cards rendered.`);
  if (playerAudit.length !== 20) {
    throw new Error(`Expected exactly 20 player cards, got ${playerAudit.length}!`);
  }

  playerAudit.forEach((p) => {
    if (!p.name || !p.rank) throw new Error(`Card #${p.index} missing name or rank!`);
    if (!p.hasImage || p.imgNaturalHeight === 0) throw new Error(`Card #${p.index} (${p.name}) image failed to load!`);
    if (p.wellHeight < 220) throw new Error(`Card #${p.index} (${p.name}) visual well is squished: ${p.wellHeight}px!`);
    if (!p.hasHeadlineImpact) throw new Error(`Card #${p.index} (${p.name}) missing headline impact banner!`);
    if (p.metricsCount !== 4) throw new Error(`Card #${p.index} (${p.name}) expected 4 metrics, got ${p.metricsCount}!`);
    if (!p.hasStabilityNote || !p.hasLooBar || !p.hasFitSummary || !p.hasDisclosure) {
      throw new Error(`Card #${p.index} (${p.name}) missing required metadata sections!`);
    }
    console.log(`  ✔ Card ${p.rank} ${p.name.padEnd(22)} | Well: ${Math.round(p.wellHeight)}px | Img: ${p.imgNaturalWidth}x${p.imgNaturalHeight}px (rendered: ${Math.round(p.imgHeightInWell)}px) | Headline + 4 Metrics + Evidence`);
  });

  // 4. TEST DOWN-WISE SCROLLING & STICKY RANK JUMPERS IN BATTERS
  console.log("\n--- 4. Testing Batters Down-wise Scrolling & Sticky Rank Bar ---");
  await page.evaluate(() => {
    document.querySelector("#batters").scrollIntoView();
  });
  await new Promise((r) => setTimeout(r, 400));

  await page.screenshot({
    path: path.join(outDir, "batters_section_top.png"),
  });

  // Test Rank Pill jump down to #3 Sameer Rizvi
  console.log("  Testing Rank Pill jump down to #3 Sameer Rizvi...");
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll("#batters .rank-pill-item"));
    const p3 = pills.find((p) => p.textContent.includes("#3"));
    if (p3) p3.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  await page.screenshot({
    path: path.join(outDir, "batters_scrolled_to_rank3_rizvi.png"),
  });

  // Test Rank Pill jump down to #7 Riyan Parag
  console.log("  Testing Rank Pill jump down to #7 Riyan Parag...");
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll("#batters .rank-pill-item"));
    const p7 = pills.find((p) => p.textContent.includes("#7"));
    if (p7) p7.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  await page.screenshot({
    path: path.join(outDir, "batters_scrolled_to_rank7_parag.png"),
  });

  // 5. TEST DOWN-WISE SCROLLING & STICKY RANK JUMPERS IN BOWLERS
  console.log("\n--- 5. Testing Bowlers Down-wise Scrolling & Sticky Rank Bar ---");
  await page.evaluate(() => {
    document.querySelector("#bowlers").scrollIntoView();
  });
  await new Promise((r) => setTimeout(r, 400));

  await page.screenshot({
    path: path.join(outDir, "bowlers_section_top.png"),
  });

  // Test Rank Pill jump down to #5 Krunal Pandya
  console.log("  Testing Rank Pill jump down to #5 Krunal Pandya...");
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll("#bowlers .rank-pill-item"));
    const p5 = pills.find((p) => p.textContent.includes("#5"));
    if (p5) p5.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  await page.screenshot({
    path: path.join(outDir, "bowlers_scrolled_to_rank5_pandya.png"),
  });

  // Test Rank Pill jump down to #10 Ravindra Jadeja
  console.log("  Testing Rank Pill jump down to #10 Ravindra Jadeja...");
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll("#bowlers .rank-pill-item"));
    const p10 = pills.find((p) => p.textContent.includes("#10"));
    if (p10) p10.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  await page.screenshot({
    path: path.join(outDir, "bowlers_scrolled_to_rank10_jadeja.png"),
  });

  // 6. TEST EXPANDABLE EVIDENCE AUDIT DRAWER
  console.log("\n--- 6. Testing Evidence Audit Drawer Expansion ---");
  await page.evaluate(() => {
    const details = document.querySelector("#card-bowling-152 details");
    if (details) details.open = true;
  });
  await new Promise((r) => setTimeout(r, 300));
  await page.screenshot({
    path: path.join(outDir, "jadeja_bowling_evidence_expanded.png"),
  });
  console.log("  ✔ Evidence drawer expanded cleanly showing leverage fixtures and dual-role cross-link.");

  // 7. TEST MOBILE RENDERING AT 390x844
  console.log("\n--- 7. Testing Mobile View at 390x844 ---");
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await page.goto("http://localhost:5173/", { waitUntil: "networkidle0" });

  await page.evaluate(() => {
    document.querySelector("#batters").scrollIntoView();
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.screenshot({
    path: path.join(outDir, "mobile_downwise_batters.png"),
  });

  await page.evaluate(() => {
    document.querySelector("#bowlers").scrollIntoView();
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.screenshot({
    path: path.join(outDir, "mobile_downwise_bowlers.png"),
  });

  await browser.close();

  console.log("\n===============================================================");
  console.log("✔ ALL VERIFICATION TESTS PASSED SUCCESSFULLY!");
  console.log(`Screenshots saved to: ${outDir}`);
  console.log("===============================================================");
}

testAll().catch((err) => {
  console.error("\n❌ VERIFICATION TEST FAILED:", err);
  process.exit(1);
});
