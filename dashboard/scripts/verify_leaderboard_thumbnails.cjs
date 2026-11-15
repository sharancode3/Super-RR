const puppeteer = require('../node_modules/puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = path.resolve('C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061');

(async () => {
  console.log("================================================================================");
  console.log("VERIFICATION: LEADERBOARD 15-PLAYER THUMBNAILS & UI/UX ACCURACY");
  console.log("================================================================================\n");

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 2 });

  await page.goto('http://localhost:5173/#model-rankings', { waitUntil: 'networkidle0', timeout: 15000 });
  
  // Scroll directly to the Model Rankings table
  await page.evaluate(() => {
    const el = document.getElementById('model-rankings') || document.querySelector('.raw-comparison-table');
    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
  });

  // Wait for all 15 batter thumbnail images to load
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('.raw-comparison-table tbody tr .raw-player-thumb-img')).slice(0, 15);
    return imgs.length === 15 && imgs.every(i => i.complete && i.naturalWidth > 0);
  }, { timeout: 10000 });

  // [TEST 1] Batters Leaderboard Top 15 Thumbnails
  console.log("[TEST 1] Verifying Batters Leaderboard (Top 15) thumbnails...");
  const batterRows = await page.$$eval('.raw-comparison-table tbody tr', (rows) => {
    return rows.slice(0, 15).map(row => {
      const rank = row.querySelector('.machine-rank-badge')?.textContent?.trim();
      const name = row.querySelector('.raw-player-name')?.textContent?.trim();
      const img = row.querySelector('.raw-player-thumb-img');
      return {
        rank,
        name,
        hasThumbFrame: !!row.querySelector('.raw-player-thumb-frame'),
        hasImg: !!img,
        src: img?.src,
        naturalWidth: img?.naturalWidth || 0,
        naturalHeight: img?.naturalHeight || 0
      };
    });
  });

  console.log(`Found ${batterRows.length} batter rows in Top 15:`);
  let allBattersPassed = true;
  for (const b of batterRows) {
    const ok = b.hasThumbFrame && b.hasImg && b.naturalWidth > 0;
    if (!ok) allBattersPassed = false;
    console.log(`  ${b.rank} ${b.name}: ${ok ? '✔ [LOADED]' : '❌ [FAILED]'} (${b.naturalWidth}x${b.naturalHeight}px) -> ${b.src}`);
  }

  if (!allBattersPassed || batterRows.length !== 15) {
    throw new Error(`Batters leaderboard thumbnail verification failed! Passed: ${allBattersPassed}, count: ${batterRows.length}`);
  }
  console.log("  ✔ [PASS] All 15 Batters have verified high-res mini portraits loaded!\n");

  // Capture screenshot of Batters Leaderboard
  const batterTableElement = await page.$('.raw-rankings-table-container');
  if (batterTableElement) {
    const screenshotPath = path.join(ARTIFACT_DIR, 'stage06_leaderboard_batters_thumbnails.png');
    await batterTableElement.screenshot({ path: screenshotPath });
    console.log(`Saved screenshot to: ${screenshotPath}`);
  }

  // [TEST 2] Switch to Bowlers Leaderboard
  console.log("[TEST 2] Switching to Bowlers Leaderboard (Top 15)...");
  const bowlerTabBtn = (await page.$$('.raw-subnav-btn'))[1];
  await bowlerTabBtn.click();
  
  // Wait for all 15 bowler thumbnail images to load
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('.raw-comparison-table tbody tr .raw-player-thumb-img')).slice(0, 15);
    return imgs.length === 15 && imgs.every(i => i.complete && i.naturalWidth > 0);
  }, { timeout: 10000 });

  const bowlerRows = await page.$$eval('.raw-comparison-table tbody tr', (rows) => {
    return rows.slice(0, 15).map(row => {
      const rank = row.querySelector('.machine-rank-badge')?.textContent?.trim();
      const name = row.querySelector('.raw-player-name')?.textContent?.trim();
      const img = row.querySelector('.raw-player-thumb-img');
      return {
        rank,
        name,
        hasThumbFrame: !!row.querySelector('.raw-player-thumb-frame'),
        hasImg: !!img,
        src: img?.src,
        naturalWidth: img?.naturalWidth || 0,
        naturalHeight: img?.naturalHeight || 0
      };
    });
  });

  console.log(`Found ${bowlerRows.length} bowler rows in Top 15:`);
  let allBowlersPassed = true;
  for (const b of bowlerRows) {
    const ok = b.hasThumbFrame && b.hasImg && b.naturalWidth > 0;
    if (!ok) allBowlersPassed = false;
    console.log(`  ${b.rank} ${b.name}: ${ok ? '✔ [LOADED]' : '❌ [FAILED]'} (${b.naturalWidth}x${b.naturalHeight}px) -> ${b.src}`);
  }

  if (!allBowlersPassed || bowlerRows.length !== 15) {
    throw new Error(`Bowlers leaderboard thumbnail verification failed! Passed: ${allBowlersPassed}, count: ${bowlerRows.length}`);
  }
  console.log("  ✔ [PASS] All 15 Bowlers have verified high-res mini portraits loaded!\n");

  // Capture screenshot of Bowlers Leaderboard
  const bowlerTableElement = await page.$('.raw-rankings-table-container');
  if (bowlerTableElement) {
    const screenshotPath = path.join(ARTIFACT_DIR, 'stage06_leaderboard_bowlers_thumbnails.png');
    await bowlerTableElement.screenshot({ path: screenshotPath });
    console.log(`Saved screenshot to: ${screenshotPath}`);
  }

  // [TEST 3] Verify no preview click behavior on thumbnails
  console.log("[TEST 3] Verifying thumbnails do NOT trigger preview click or modal popups...");
  const firstThumb = await page.$('.raw-player-thumb-frame');
  await firstThumb.click();
  await new Promise(r => setTimeout(r, 400));
  const modalOpen = await page.$('.react-player-modal-backdrop');
  if (modalOpen) {
    throw new Error("Thumbnail click unexpectedly triggered modal!");
  }
  console.log("  ✔ [PASS] Thumbnails are clean visual additions with zero unwanted click popups.\n");

  await browser.close();

  console.log("================================================================================");
  console.log("🎉 ALL LEADERBOARD THUMBNAIL TESTS PASSED 100%!");
  console.log("================================================================================");
})();
