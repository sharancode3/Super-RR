const puppeteer = require('puppeteer');
const assert = require('assert');

(async () => {
  console.log('🚀 Starting Comprehensive End-to-End Browser Verification Test...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`[PAGE ERROR]: ${msg.text()}`);
  });

  try {
    // -------------------------------------------------------------
    // 1. Initial Page Load & Single-Page Integrity
    // -------------------------------------------------------------
    console.log('\n--- 1. Testing Initial Page Load & SPA Integrity ---');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });

    const title = await page.title();
    console.log(`Page title: "${title}"`);
    assert(title.includes('Rajasthan Royals') || title.includes('SupeRR'), 'Title must match RR branding');

    // -------------------------------------------------------------
    // 2. Navigation: Header "Media Section" Link Must Stay In-App
    // -------------------------------------------------------------
    console.log('\n--- 2. Testing Header "Media Section" Click ---');
    const headerMediaLink = await page.$('a.nav-sheet[href="#media"]');
    assert(headerMediaLink, 'Header Media Section anchor link href="#media" must exist');

    await page.click('a.nav-sheet[href="#media"]');
    await new Promise(r => setTimeout(r, 1500));

    const currentUrl = page.url();
    console.log(`Current URL after clicking Media link: ${currentUrl}`);
    assert(currentUrl.includes('#media'), 'URL must end in #media');
    assert(!currentUrl.includes('contact_sheet.html'), 'MUST NOT navigate away to contact_sheet.html!');

    const mediaSectionVisible = await page.evaluate(() => {
      const el = document.getElementById('media');
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      console.log('Media rect top:', rect.top, 'innerHeight:', window.innerHeight);
      return rect.top >= -300 && rect.top <= window.innerHeight + 300;
    });
    console.log(`Media section scrolled into view: ${mediaSectionVisible}`);
    assert(mediaSectionVisible, 'Media section must be scrolled into view');

    // -------------------------------------------------------------
    // 3. Floating Sidebar: Position, Gap, and Navigation
    // -------------------------------------------------------------
    console.log('\n--- 3. Testing Floating Sidebar & Sticky Bar Clearance ---');
    await page.evaluate(() => window.scrollTo(0, 800));
    await new Promise(r => setTimeout(r, 400));

    const sidebarVisible = await page.evaluate(() => {
      const sb = document.getElementById('floating-sidebar');
      return sb && sb.classList.contains('is-visible');
    });
    console.log(`Floating sidebar visible on scroll: ${sidebarVisible}`);
    assert(sidebarVisible, 'Floating sidebar must be visible when scrolled');

    // Check gap between sticky-rank-bar and floating-sidebar
    const clearance = await page.evaluate(() => {
      const stickyBar = document.querySelector('.sticky-rank-bar');
      const floatingSidebar = document.getElementById('floating-sidebar');
      if (!stickyBar || !floatingSidebar) return null;
      const sRect = stickyBar.getBoundingClientRect();
      const fRect = floatingSidebar.getBoundingClientRect();
      return {
        stickyBottom: sRect.bottom,
        floatingTop: fRect.top,
        gap: fRect.top - sRect.bottom
      };
    });
    console.log('Floating sidebar clearance:', clearance);
    if (clearance) {
      assert(clearance.gap >= 0, `Floating sidebar must not overlap sticky bar! Gap: ${clearance.gap}px`);
    }

    // -------------------------------------------------------------
    // 4. Leaderboard Mini Portraits: Batters (15) and Bowlers (15)
    // -------------------------------------------------------------
    console.log('\n--- 4. Testing Leaderboard Player Thumbnails (Top 15 Batters & Bowlers) ---');
    await page.evaluate(() => {
      const el = document.getElementById('model-rankings');
      if (el) el.scrollIntoView();
    });
    await new Promise(r => setTimeout(r, 600));

    // Switch to Batting tab and verify 15 thumbnails
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Batting Model'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const batterThumbnails = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.slice(0, 15).map(r => {
        const name = r.querySelector('.raw-player-name')?.textContent?.trim() || '';
        const img = r.querySelector('.raw-player-thumb-img');
        return {
          name,
          hasImg: !!img,
          src: img ? img.src : null,
          complete: img ? img.complete : false,
          naturalWidth: img ? img.naturalWidth : 0
        };
      });
    });

    console.log(`Loaded ${batterThumbnails.length} Batters in Leaderboard Top 15.`);
    assert.strictEqual(batterThumbnails.length, 15, 'Must have 15 batters in Top 15');
    batterThumbnails.forEach(t => {
      assert(t.hasImg, `Batter ${t.name} must have thumbnail img`);
      assert(t.naturalWidth > 0, `Batter ${t.name} thumbnail image must decode properly (naturalWidth > 0)`);
    });
    console.log('✅ All 15 Batters thumbnails rendered and decoded successfully.');

    // Switch to Bowling tab and verify 15 thumbnails
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && (b.textContent.includes('Bowlers') || b.textContent.includes('Bowling Model')));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const bowlerThumbnails = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.slice(0, 15).map(r => {
        const name = r.querySelector('.raw-player-name')?.textContent?.trim() || '';
        const img = r.querySelector('.raw-player-thumb-img');
        return {
          name,
          hasImg: !!img,
          src: img ? img.src : null,
          complete: img ? img.complete : false,
          naturalWidth: img ? img.naturalWidth : 0
        };
      });
    });

    console.log(`Loaded ${bowlerThumbnails.length} Bowlers in Leaderboard Top 15.`);
    assert.strictEqual(bowlerThumbnails.length, 15, 'Must have 15 bowlers in Top 15');
    bowlerThumbnails.forEach(t => {
      assert(t.hasImg, `Bowler ${t.name} must have thumbnail img`);
      assert(t.naturalWidth > 0, `Bowler ${t.name} thumbnail image must decode properly (naturalWidth > 0)`);
    });
    console.log('✅ All 15 Bowlers thumbnails rendered and decoded successfully.');

    // -------------------------------------------------------------
    // 5. In-App Media Section Functionality
    // -------------------------------------------------------------
    console.log('\n--- 5. Testing In-App Media Section ---');
    await page.evaluate(() => {
      const el = document.getElementById('media');
      if (el) el.scrollIntoView();
    });
    await new Promise(r => setTimeout(r, 400));

    const mediaCardsCount = await page.evaluate(() => {
      return document.querySelectorAll('.media-player-card').length;
    });
    console.log(`Total Media Player Cards rendered: ${mediaCardsCount}`);
    assert.strictEqual(mediaCardsCount, 19, 'Must render exactly 19 player cards in media section');

    // Test filter tabs: "Bowlers (9 + Dual)"
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.media-filter-btn')).find(b => b.textContent && b.textContent.includes('Bowlers'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 300));
    const bowlersCardCount = await page.evaluate(() => document.querySelectorAll('.media-player-card').length);
    console.log(`Filtered Bowlers Cards count: ${bowlersCardCount}`);
    assert.strictEqual(bowlersCardCount, 10, 'Filtered bowlers must be 10 cards (9 bowlers + Jadeja dual)');

    // Reset filter to "All"
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.media-filter-btn')).find(b => b.textContent && b.textContent.includes('All'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 300));

    // Test clicking "Preview Card & Official IPL Stats" in Media Section
    console.log('Testing "Preview Card & Official IPL Stats" modal trigger...');
    const firstPreviewBtn = await page.$('.btn-media-preview');
    assert(firstPreviewBtn, 'Must have preview button in media card');
    await firstPreviewBtn.click();
    await new Promise(r => setTimeout(r, 600));

    const modalData = await page.evaluate(() => {
      const modal = document.querySelector('.react-player-modal-backdrop');
      if (!modal) return null;
      const title = modal.querySelector('.react-modal-name')?.textContent?.trim();
      const metricCards = Array.from(modal.querySelectorAll('.react-metric-card'));
      return {
        open: true,
        title,
        hasStatsGrid: metricCards.length > 0,
        statItemsCount: metricCards.length
      };
    });

    console.log('Modal data opened from Media Section:', modalData);
    assert(modalData && modalData.open, 'Modal must open upon clicking preview button');
    assert(modalData.title && modalData.title.length > 0, 'Modal must display player name');
    assert(modalData.hasStatsGrid, 'Modal must display official IPL stats grid');
    assert(modalData.statItemsCount >= 4, 'Modal must have at least 4 key stats (Matches, Runs/Wkts, SR/Econ, Avg)');

    // Close modal
    await page.click('.react-modal-close-btn');
    await new Promise(r => setTimeout(r, 400));
    const isModalClosed = await page.evaluate(() => !document.querySelector('.react-player-modal-backdrop'));
    assert(isModalClosed, 'Modal must close cleanly when clicking close button');
    console.log('✅ In-app preview modal verified in Media Section.');

    // -------------------------------------------------------------
    // 6. Main Dashboard Player Card Click Preview (No separate site)
    // -------------------------------------------------------------
    console.log('\n--- 6. Testing Main Dashboard Player Card Click ---');
    await page.evaluate(() => window.scrollTo(0, 300));
    await new Promise(r => setTimeout(r, 500));

    const portraitButton = await page.$('.portrait-click-target');
    assert(portraitButton, 'Portrait click target must exist on main card');
    await portraitButton.click();
    await new Promise(r => setTimeout(r, 600));

    const mainCardModal = await page.evaluate(() => {
      const modal = document.querySelector('.react-player-modal-backdrop');
      return modal ? modal.querySelector('.react-modal-name')?.textContent?.trim() : null;
    });
    console.log(`Modal opened from main card click: "${mainCardModal}"`);
    assert(mainCardModal, 'Clicking player portrait in main board must open in-app modal, not external site');

    // Close modal
    await page.keyboard.press('Escape');
    await new Promise(r => setTimeout(r, 400));
    console.log('✅ Main card portrait preview modal verified without leaving page.');

    // -------------------------------------------------------------
    // 7. Strict Zero Emojis Across DOM
    // -------------------------------------------------------------
    console.log('\n--- 7. Verifying Strict Zero-Emoji Rule Across Entire Page ---');
    const emojiCheck = await page.evaluate(() => {
      // Extended_Pictographic matches actual emojis (faces, animals, food, sports equipment, etc.)
      const emojiRegex = /\p{Extended_Pictographic}/gu;
      
      const elements = Array.from(document.body.querySelectorAll('*'));
      const offending = [];

      for (const el of elements) {
        // Skip script and style tags
        if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'NOSCRIPT') continue;
        
        // Check only direct text nodes
        for (const child of el.childNodes) {
          if (child.nodeType === Node.TEXT_NODE) {
            const text = child.nodeValue || '';
            const matches = text.match(emojiRegex);
            if (matches) {
              offending.push({
                tag: el.tagName,
                className: el.className,
                text: text.trim(),
                emojis: matches
              });
            }
          }
        }
      }
      return offending;
    });

    console.log(`Emoji audit offending count: ${emojiCheck.length}`);
    if (emojiCheck.length > 0) {
      console.error('Found offending emojis:', JSON.stringify(emojiCheck, null, 2));
    }
    assert.strictEqual(emojiCheck.length, 0, 'Must have strictly ZERO emojis across entire UI!');
    console.log('✅ 100% Zero-Emoji Guarantee passed.');

    // -------------------------------------------------------------
    // 8. Auto-Stabilization Across Viewports (Mobile, Tablet, Desktop)
    // -------------------------------------------------------------
    console.log('\n--- 8. Testing Auto-Stabilization Across Viewports ---');
    const viewports = [
      { name: 'Mobile (390x844)', width: 390, height: 844 },
      { name: 'Tablet (768x1024)', width: 768, height: 1024 },
      { name: 'Desktop (1440x900)', width: 1440, height: 900 }
    ];

    for (const vp of viewports) {
      await page.setViewport({ width: vp.width, height: vp.height });
      await new Promise(r => setTimeout(r, 400));

      const overflow = await page.evaluate(() => {
        return {
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          hasHorizontalScrollbar: document.documentElement.scrollWidth > document.documentElement.clientWidth
        };
      });

      console.log(`Viewport ${vp.name}: clientWidth=${overflow.clientWidth}, scrollWidth=${overflow.scrollWidth}, horizontalOverflow=${overflow.hasHorizontalScrollbar}`);
      assert(!overflow.hasHorizontalScrollbar, `Viewport ${vp.name} must have ZERO horizontal overflow!`);
    }
    console.log('✅ Auto-stabilization verified across Mobile, Tablet, and Desktop.');

    // Take verified full screenshots
    await page.setViewport({ width: 1440, height: 900 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await new Promise(r => setTimeout(r, 300));

    // Save screenshots to brain directory
    const brainDir = 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061';
    await page.screenshot({ path: `${brainDir}/stage07_verified_e2e_top.png` });

    await page.evaluate(() => {
      const mr = document.getElementById('model-rankings');
      if (mr) mr.scrollIntoView();
    });
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: `${brainDir}/stage07_verified_e2e_model_rankings.png` });

    await page.evaluate(() => {
      const m = document.getElementById('media');
      if (m) m.scrollIntoView();
    });
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: `${brainDir}/stage07_verified_e2e_media_section.png` });

    console.log('\n🎉 ALL END-TO-END BROWSER TESTS PASSED FLAWLESSLY!');
  } finally {
    await browser.close();
  }
})();
