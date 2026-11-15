const puppeteer = require('puppeteer');
const assert = require('assert');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  console.log('--- 1. Testing Main Dashboard Screen (http://localhost:5173/) ---');
  await page.goto('http://localhost:5173/#batters', { waitUntil: 'networkidle0' });

  // Verify that .portrait-preview-link-btn does NOT exist in DOM
  const previewBtns = await page.$$('.portrait-preview-link-btn');
  console.log('  Count of .portrait-preview-link-btn on main screen:', previewBtns.length);
  assert.strictEqual(previewBtns.length, 0, 'Must NOT render any explicit preview buttons on main screen!');

  // Verify text "Preview Card" does NOT exist anywhere in player card visuals
  const textMatches = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll('.player-card'));
    let foundUglyButton = false;
    for (const card of cards) {
      if (card.querySelector('.rect-visual-col')?.textContent?.includes('Preview Card')) {
        foundUglyButton = true;
      }
    }
    return foundUglyButton;
  });
  console.log('  Found any preview button text on portraits:', textMatches);
  assert.strictEqual(textMatches, false, 'No preview button text allowed on portraits!');

  // Verify that portrait has .portrait-click-target link to contact_sheet.html
  const clickTargetHref = await page.$eval('.portrait-click-target', el => el.getAttribute('href'));
  console.log('  Portrait click target href:', clickTargetHref);
  assert(clickTargetHref.includes('/portraits/contact_sheet.html#player-'), 'Portrait must link to contact sheet!');

  // Take screenshot of top cards on main screen
  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage05_clean_main_screen_cards.png' });
  console.log('  ✔ [PASS] Main screen is 100% clean and pristine! No ugly preview button!');

  console.log('--- 2. Testing Media Screen (http://localhost:5173/portraits/contact_sheet.html) ---');
  await page.goto('http://localhost:5173/portraits/contact_sheet.html', { waitUntil: 'networkidle0' });

  // Verify that .btn-preview-card DOES exist in media screen
  const mediaPreviewBtns = await page.$$('.btn-preview-card');
  console.log('  Count of .btn-preview-card on media screen:', mediaPreviewBtns.length);
  assert.strictEqual(mediaPreviewBtns.length, 19, 'Must render exactly 19 preview buttons on media screen!');

  // Click first button and verify modal opens
  await mediaPreviewBtns[0].click();
  await new Promise(r => setTimeout(r, 400));
  const isModalOpen = await page.$eval('#player-modal', el => el.classList.contains('is-open'));
  console.log('  Media modal lightbox opened on click:', isModalOpen);
  assert.strictEqual(isModalOpen, true, 'Modal must open on media screen!');

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage05_media_screen_modal_preserved.png' });
  console.log('  ✔ [PASS] Media screen modal lightbox is fully preserved and functional!');

  await browser.close();
  console.log('🎉 ALL ASSERTIONS PASSED 100%!');
})().catch(e => {
  console.error('❌ Verification failed:', e);
  process.exit(1);
});
