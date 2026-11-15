const puppeteer = require('puppeteer');
const assert = require('assert');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();

  console.log('================================================================================');
  console.log('VERIFICATION: IN-APP PREVIEW MODAL, ZERO EMOJIS & DEVICE SCREEN STABILIZATION');
  console.log('================================================================================\n');

  // ---------------------------------------------------------------------------
  // 1. SCAN FOR EMOJIS ACROSS SRC AND PUBLIC
  // ---------------------------------------------------------------------------
  console.log('[TEST 1] Scanning for ANY emojis in src/ and public/...');
  const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F1E6}-\u{1F1FF}]|✓|✕/gu;
  let emojiCount = 0;

  function scanDir(dir) {
    const files = fs.readdirSync(dir, { withFileTypes: true });
    for (const f of files) {
      const full = path.join(dir, f.name);
      if (f.isDirectory()) {
        if (f.name !== 'node_modules' && f.name !== 'dist' && f.name !== '.git') {
          scanDir(full);
        }
      } else if (/\.(tsx|ts|jsx|js|html|css|json)$/.test(f.name)) {
        const content = fs.readFileSync(full, 'utf8');
        const matches = content.match(emojiRegex);
        if (matches) {
          console.error(`  Found emojis in ${full}:`, Array.from(new Set(matches)));
          emojiCount += matches.length;
        }
      }
    }
  }

  scanDir('dashboard/src');
  scanDir('dashboard/public');
  assert.strictEqual(emojiCount, 0, 'Must have strictly ZERO emojis across all source and public assets!');
  console.log('  ✔ [PASS] Zero emojis found! All iconography uses proper SVGs.\n');

  // ---------------------------------------------------------------------------
  // 2. IN-APP MODAL ON MAIN DASHBOARD (NO REDIRECT TO SEPARATE HTML)
  // ---------------------------------------------------------------------------
  console.log('[TEST 2] Verifying In-App Player Modal on Desktop (1440x900)...');
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/#batters', { waitUntil: 'networkidle0' });

  // Click on Vaibhav Sooryavanshi portrait
  console.log('  Clicking on Vaibhav Sooryavanshi portrait...');
  const firstPortrait = await page.$('#card-batting-50284 .portrait-click-target');
  assert(firstPortrait, 'Portrait button must exist on player card');
  await firstPortrait.click();
  await new Promise(r => setTimeout(r, 400));

  // Verify URL did NOT change to a separate html page
  const currentUrl = page.url();
  console.log('  Current URL after click:', currentUrl);
  assert(!currentUrl.includes('contact_sheet.html'), 'Must NOT navigate to contact_sheet.html! Must stay in-app!');

  // Verify modal is open
  const modalVisible = await page.$eval('.react-player-modal-dialog', el => !!el);
  assert(modalVisible, 'In-app modal dialog must be visible');

  // Verify modal content is specifically for Vaibhav Sooryavanshi
  const modalName = await page.$eval('#player-preview-title', el => el.textContent.trim());
  console.log('  Modal Player Title:', modalName);
  assert.strictEqual(modalName, 'Vaibhav Sooryavanshi', 'Modal must show ONLY that player\'s preview!');

  const runsVal = await page.$eval('.react-metric-card.highlight-pink .react-metric-num', el => el.textContent.trim());
  console.log('  Total Runs displayed:', runsVal);
  assert.strictEqual(runsVal, '1028', 'Must display verified 1028 runs');

  // Test theme switching in-app
  console.log('  Testing theme switcher (Pink, Blue, Dark, Paper)...');
  await page.click('.react-theme-btn:nth-child(2)'); // Pink
  await new Promise(r => setTimeout(r, 100));
  let wellClass = await page.$eval('.react-modal-portrait-well', el => el.className);
  assert(wellClass.includes('tile-pink'), 'Must switch to pink theme');

  await page.click('.react-theme-btn:nth-child(3)'); // Blue
  await new Promise(r => setTimeout(r, 100));
  wellClass = await page.$eval('.react-modal-portrait-well', el => el.className);
  assert(wellClass.includes('tile-blue'), 'Must switch to blue theme');

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage05_in_app_modal_desktop.png' });

  // Close modal via close button
  await page.click('.react-modal-close-btn');
  await new Promise(r => setTimeout(r, 300));
  const isClosed = await page.evaluate(() => !document.querySelector('.react-player-modal-dialog'));
  assert(isClosed, 'Modal must close on close-button click');
  console.log('  ✔ [PASS] Vaibhav Sooryavanshi in-app preview verified!\n');

  // ---------------------------------------------------------------------------
  // 3. VERIFY SPECIFIC PLAYER CLICK: JOSH INGLIS (#4736)
  // ---------------------------------------------------------------------------
  console.log('[TEST 3] Verifying specific player click for Josh Inglis (#4736)...');
  const inglisPortrait = await page.$('#card-batting-4736 .portrait-click-target');
  assert(inglisPortrait, 'Josh Inglis portrait button must exist');
  await inglisPortrait.click();
  await new Promise(r => setTimeout(r, 400));

  const inglisName = await page.$eval('#player-preview-title', el => el.textContent.trim());
  console.log('  Modal Player Title for Inglis:', inglisName);
  assert.strictEqual(inglisName, 'Josh Inglis', 'Modal must show Josh Inglis only!');

  const inglisRuns = await page.$eval('.react-metric-card.highlight-pink .react-metric-num', el => el.textContent.trim());
  console.log('  Josh Inglis runs:', inglisRuns);
  assert.strictEqual(inglisRuns, '544', 'Must display Josh Inglis 544 verified runs');

  // Test close via Escape key
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 300));
  const isInglisClosed = await page.evaluate(() => !document.querySelector('.react-player-modal-dialog'));
  assert(isInglisClosed, 'Modal must close on Escape key');
  console.log('  ✔ [PASS] Specific player preview verified for Josh Inglis!\n');

  // ---------------------------------------------------------------------------
  // 4. VERIFY DUAL-ROLE PLAYER: RAVINDRA JADEJA (#152)
  // ---------------------------------------------------------------------------
  console.log('[TEST 4] Verifying Dual-Role player Ravindra Jadeja (#152)...');
  const jadejaPortrait = await page.$('#card-batting-152 .portrait-click-target');
  assert(jadejaPortrait, 'Jadeja portrait button must exist');
  await jadejaPortrait.click();
  await new Promise(r => setTimeout(r, 400));

  const jadejaName = await page.$eval('#player-preview-title', el => el.textContent.trim());
  assert.strictEqual(jadejaName, 'Ravindra Jadeja');

  // Check dual-role tabs exist
  const dualTabs = await page.$$('.react-modal-dual-tab');
  assert.strictEqual(dualTabs.length, 2, 'Dual-role player must have Batting and Bowling tabs');
  console.log('  Toggling between Batting and Bowling tabs...');
  await dualTabs[1].click(); // Bowling tab
  await new Promise(r => setTimeout(r, 200));

  const oversVal = await page.$eval('.react-metric-card.highlight-navy .react-metric-num', el => el.textContent.trim());
  console.log('  Jadeja Bowling Overs:', oversVal);
  assert.strictEqual(oversVal, '207.8', 'Jadeja bowling overs must be 207.8');

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage05_in_app_modal_jadeja_dual.png' });
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 300));
  console.log('  ✔ [PASS] Dual-role in-app preview verified!\n');

  // ---------------------------------------------------------------------------
  // 5. AUTO-STABILIZATION ACROSS DEVICES (MOBILE, TABLET, DESKTOP)
  // ---------------------------------------------------------------------------
  console.log('[TEST 5] Testing Auto-Stabilization across screen sizes...');
  const viewports = [
    { name: 'Mobile (390x844)', width: 390, height: 844 },
    { name: 'Tablet (768x1024)', width: 768, height: 1024 },
    { name: 'Desktop Compact (1100x800)', width: 1100, height: 800 }
  ];

  for (const vp of viewports) {
    await page.setViewport({ width: vp.width, height: vp.height });
    await page.goto('http://localhost:5173/#batters', { waitUntil: 'networkidle0' });

    const portrait = await page.$('#card-batting-50284 .portrait-click-target');
    assert(portrait, 'Portrait button must exist');
    await portrait.click();
    await new Promise(r => setTimeout(r, 400));

    // Verify modal boundaries do NOT overflow viewport
    const overflowCheck = await page.evaluate((vpWidth, vpHeight) => {
      const dialog = document.querySelector('.react-player-modal-dialog');
      if (!dialog) return { found: false };
      const r = dialog.getBoundingClientRect();
      return {
        found: true,
        width: r.width,
        height: r.height,
        left: r.left,
        right: r.right,
        top: r.top,
        bottom: r.bottom,
        overflowsWidth: r.width > vpWidth,
        fitsVertically: r.height <= vpHeight
      };
    }, vp.width, vp.height);

    console.log(`  ${vp.name} Bounds:`, overflowCheck);
    assert(!overflowCheck.overflowsWidth, `Modal must not exceed viewport width on ${vp.name}`);
    assert(overflowCheck.fitsVertically, `Modal must fit within viewport height on ${vp.name}`);

    const safeName = vp.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
    await page.screenshot({ path: `C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage05_modal_${safeName}.png` });

    await page.keyboard.press('Escape');
    await new Promise(r => setTimeout(r, 300));
  }
  console.log('  ✔ [PASS] Auto-stabilization verified across all devices!\n');

  await browser.close();
  console.log('================================================================================');
  console.log('🎉 ALL 5 TEST GATES PASSED 100%! ZERO DISCREPANCIES FOUND.');
  console.log('================================================================================');
})().catch(e => {
  console.error('❌ Verification failed:', e);
  process.exit(1);
});
