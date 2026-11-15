const puppeteer = require('puppeteer');
const assert = require('assert');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061';

async function run() {
  console.log('🚀 Starting Dedicated Archer Bowling Revision Verification Suite...');

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });

    // -------------------------------------------------------------------------
    // TEST 1: Bowlers Shortlist (Cards #7, #8, #9, #10)
    // -------------------------------------------------------------------------
    console.log('\n--- 1. Testing Bowlers Shortlist Cards ---');
    // Switch to Bowlers tab
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Bowlers (10)'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 500));

    // Get the bowler cards from #bowlers section
    const bowlerCards = await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('#bowlers .player-card'));
      return cards.map(c => {
        const rank = c.querySelector('.card-desktop-rank-badge .rank-num')?.textContent?.trim() || '';
        const name = c.querySelector('.rect-player-name')?.textContent?.trim() || '';
        const role = c.querySelector('.phase-pill')?.textContent?.trim() || '';
        const status = c.querySelector('.route-pill')?.textContent?.trim() || '';
        const metricBoxes = Array.from(c.querySelectorAll('.metric-box'));
        const forecast = metricBoxes[0]?.querySelector('.metric-value')?.textContent?.trim() || '';
        const hpRate = metricBoxes[1]?.querySelector('.metric-value')?.textContent?.trim() || '';
        const hpFootnote = metricBoxes[1]?.querySelector('.metric-footnote')?.textContent?.trim() || '';
        const stability = metricBoxes[3]?.querySelector('.metric-value')?.textContent?.trim() || '';
        const img = c.querySelector('.player-portrait-img');
        return {
          rank,
          name,
          role,
          status,
          forecast,
          hpRate: `${hpRate} ${hpFootnote}`,
          stability,
          imgSrc: img ? img.getAttribute('src') : null,
          imgComplete: img ? img.complete : false,
          naturalWidth: img ? img.naturalWidth : 0
        };
      });
    });

    console.log(`Found ${bowlerCards.length} bowler cards in shortlist.`);
    assert.strictEqual(bowlerCards.length, 10, 'Must have exactly 10 bowler cards');

    const expectedBowlers = [
      { rank: '#1', name: 'Mohammed Siraj' },
      { rank: '#2', name: 'Jason Holder' },
      { rank: '#3', name: 'Kartik Tyagi' },
      { rank: '#4', name: 'Lungi Ngidi' },
      { rank: '#5', name: 'Krunal Pandya' },
      { rank: '#6', name: 'Rasikh Salam' },
      { rank: '#7', name: 'Mohammed Shami' },
      { rank: '#8', name: 'Anshul Kamboj' },
      { rank: '#9', name: 'Ravindra Jadeja' },
      { rank: '#10', name: 'Jofra Archer' },
    ];

    expectedBowlers.forEach((exp, i) => {
      assert.strictEqual(bowlerCards[i].name, exp.name, `Bowler #${i+1} must be ${exp.name}`);
      assert.strictEqual(bowlerCards[i].rank, exp.rank, `Bowler #${i+1} rank badge must be ${exp.rank}`);
      assert(bowlerCards[i].naturalWidth > 0, `Bowler ${exp.name} portrait must load successfully`);
    });

    // Specific assertions for Archer (#10)
    const archer = bowlerCards[9];
    console.log('Archer Shortlist Card Details:', archer);
    assert.strictEqual(archer.name, 'Jofra Archer');
    assert.strictEqual(archer.rank, '#10');
    assert(archer.role.toLowerCase().includes('new-ball') || archer.role.toLowerCase().includes('powerplay') || archer.role.toLowerCase().includes('pace'), 'Archer role should be New-ball bowling/Powerplay/Pace');
    assert(archer.status.includes('RR squad decision'), 'Archer route should be RR squad decision');
    assert(archer.hpRate.includes('-1.98'), 'Archer HP rate should be -1.98 r/12');
    assert(archer.hpRate.includes('106b'), 'Archer HP rate should cite 106 balls');
    assert(archer.forecast.includes('+0.64'), 'Archer forecast impact should be +0.64');
    assert(archer.stability.includes('25.8%'), 'Archer stability should be 25.8%');

    // Scroll to Bowler #10 and take screenshot
    await page.evaluate(() => {
      const cards = document.querySelectorAll('#bowlers .player-card');
      if (cards.length >= 10) cards[9].scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage10_archer_shortlist_card.png') });
    console.log('📸 Saved stage10_archer_shortlist_card.png');

    // -------------------------------------------------------------------------
    // TEST 2: Model Rankings Section (Screened Top 15, Archer #13, Boult MI #7)
    // -------------------------------------------------------------------------
    console.log('\n--- 2. Testing Model Rankings Screened Top 15 & Boult/Archer ---');
    await page.evaluate(() => {
      const sec = document.getElementById('model-rankings');
      if (sec) sec.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await new Promise(r => setTimeout(r, 400));

    // Switch Model Rankings to Bowling Tab
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Raw Bowlers Leaderboard'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    // Click "RR-Screened Pool" button
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('RR-Screened Pool'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    // Check rows under Screened Priority Sort (Top 15)
    const screenedBowlingRows = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.map((r, i) => {
        const rank = r.querySelector('.td-machine-rank .machine-rank-badge')?.textContent?.trim() || '';
        const name = r.querySelector('.raw-player-name')?.textContent?.trim() || '';
        const team = r.querySelector('.raw-player-meta span:last-child')?.textContent?.trim() || '';
        const score = r.querySelector('.td-priority .priority-val')?.textContent?.trim() || '';
        const outcome = r.querySelector('.td-outcome')?.textContent?.trim() || '';
        const anchor = r.querySelector('.rr-target-badge')?.getAttribute('href') || null;
        return { idx: i + 1, rank, name, team, score, outcome, anchor };
      });
    });

    console.log(`Screened Bowling rows visible: ${screenedBowlingRows.length}`);
    assert(screenedBowlingRows.length >= 15, 'Must have at least 15 rows in screened bowling table');

    // Find Boult and Archer in Screened Priority
    const screenedBoult = screenedBowlingRows.find(r => r.name === 'Trent Boult');
    const screenedArcher = screenedBowlingRows.find(r => r.name === 'Jofra Archer');

    console.log('Screened Boult row:', screenedBoult);
    console.log('Screened Archer row:', screenedArcher);

    assert(screenedBoult, 'Boult must be in Screened Bowling rankings');
    assert.strictEqual(screenedBoult.rank, '#7', 'Boult should be #7 in screened priority');
    assert.strictEqual(screenedBoult.team, 'Mumbai Indians', 'Boult 2026 affiliation must be Mumbai Indians');

    assert(screenedArcher, 'Archer must be in Screened Bowling rankings');
    assert.strictEqual(screenedArcher.rank, '#13', 'Archer should be #13 in screened priority');
    assert(screenedArcher.outcome.includes('RR #10'), 'Archer outcome badge should say RR #10');
    assert.strictEqual(screenedArcher.anchor, '#bowling-jofra-archer', 'Archer should link to #bowling-jofra-archer');

    // Take screenshot of Screened Top 15
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage10_model_rankings_screened_bowling.png') });
    console.log('📸 Saved stage10_model_rankings_screened_bowling.png');

    // Test Forecast-only sort
    console.log('Switching to Forecast sort in Screened Pool...');
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Forecast Only'));
      if (btn) btn.click();
    });
    // Expand to "All Scored" to find Archer at #19
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('All Scored'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const forecastRows = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.map((r, i) => {
        const rank = r.querySelector('.td-machine-rank .machine-rank-badge')?.textContent?.trim() || '';
        const name = r.querySelector('.raw-player-name')?.textContent?.trim() || '';
        return { idx: i + 1, rank, name };
      });
    });

    const forecastArcher = forecastRows.find(r => r.name === 'Jofra Archer');
    console.log('Archer in Screened Forecast sort:', forecastArcher);
    assert(forecastArcher, 'Archer must be present in screened forecast rankings');
    assert.strictEqual(forecastArcher.rank, '#19', 'Archer must be #19 in screened forecast ranking');

    // Reset back to Priority sort and Top 15
    await page.evaluate(() => {
      const prioBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Priority Score'));
      if (prioBtn) prioBtn.click();
      const topBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Top 15'));
      if (topBtn) topBtn.click();
    });
    await new Promise(r => setTimeout(r, 300));

    // Test Archer anchor link click
    console.log('Testing click on Archer anchor link in outcome column...');
    const clickResult = await page.evaluate(() => {
      const archerRow = Array.from(document.querySelectorAll('.raw-table-row')).find(r => r.textContent.includes('Jofra Archer'));
      if (!archerRow) return { foundRow: false };
      const link = archerRow.querySelector('.rr-target-badge');
      if (!link) return { foundRow: true, foundLink: false };
      const href = link.getAttribute('href');
      link.click();
      return { foundRow: true, foundLink: true, href };
    });
    console.log('Click result:', clickResult);
    await new Promise(r => setTimeout(r, 600));

    const currentHash = await page.evaluate(() => window.location.hash);
    console.log('Current URL hash after clicking Archer anchor:', currentHash);
    assert.strictEqual(currentHash, '#bowling-jofra-archer', 'URL hash should be #bowling-jofra-archer');

    // -------------------------------------------------------------------------
    // TEST 3: Methodology Section Archer–Boult Case Study
    // -------------------------------------------------------------------------
    console.log('\n--- 3. Testing Methodology Section Archer–Boult Comparison ---');
    await page.evaluate(() => {
      const sec = document.getElementById('methodology');
      if (sec) sec.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await new Promise(r => setTimeout(r, 500));

    // Open Module 07 in Methodology
    await page.evaluate(() => {
      const tab7 = document.getElementById('tab-07-confidence-stability');
      if (tab7) tab7.click();
    });
    await new Promise(r => setTimeout(r, 500));

    const methodologyText = await page.evaluate(() => {
      const el = document.getElementById('methodology');
      return el ? el.innerText : '';
    });
    console.log('Methodology text sample (first 400 chars):', methodologyText.slice(0, 400));
    console.log('Includes Jofra Archer?', methodologyText.includes('Jofra Archer'));
    console.log('Includes Archer vs Trent Boult?', methodologyText.includes('Archer vs Trent Boult'));
    console.log('Includes Archer–Boult?', methodologyText.includes('Archer–Boult'));

    assert(methodologyText.includes('Jofra Archer over Trent Boult') || (methodologyText.includes('Jofra Archer') && methodologyText.includes('Trent Boult')), 'Must contain Archer over Boult trade-off case');
    assert(methodologyText.includes('-1.98') && methodologyText.includes('106 balls'), 'Must cite Archer -1.98 across 106 balls');
    assert(methodologyText.includes('-6.06') && methodologyText.includes('20 balls'), 'Must cite Boult -6.06 across 20 balls');
    assert(methodologyText.includes('+0.64') && methodologyText.includes('+1.40'), 'Must cite Archer +0.64 vs Boult +1.40 composite forecast');
    assert(methodologyText.includes('25 wickets in 16 matches'), 'Must cite Archer 25 wickets in 16 matches for RR');
    assert(methodologyText.includes('SRH vs RR on 27 May 2026') || methodologyText.includes('Match 50943'), 'Must cite official Eliminator match context');
    console.log('✅ Methodology Module 07 Archer–Boult 4-dimension trade-off verified.');

    // Scroll to the card and take screenshot
    await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll('*')).find(e => e.textContent && e.textContent.includes('Jofra Archer over Trent Boult') && e.children.length === 0);
      if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage10_methodology_archer_boult_case.png') });
    console.log('📸 Saved stage10_methodology_archer_boult_case.png');

    // -------------------------------------------------------------------------
    // TEST 4: Media Section Bowler Filter and Archer Card
    // -------------------------------------------------------------------------
    console.log('\n--- 4. Testing Media Section Bowlers & Archer Card ---');
    await page.evaluate(() => {
      const sec = document.getElementById('media');
      if (sec) sec.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await new Promise(r => setTimeout(r, 500));

    // Click Bowlers filter in Media Section
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.media-filter-btn')).find(b => b.textContent && b.textContent.includes('Bowlers'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const mediaCards = await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.media-player-card'));
      return items.map(c => {
        const title = c.querySelector('.media-card-name')?.textContent?.trim() || '';
        const badge = c.querySelector('.media-rank-badge')?.textContent?.trim() || c.querySelector('.media-leader-badge')?.textContent?.trim() || '';
        const meta = c.querySelector('.media-card-meta')?.textContent?.trim() || '';
        return { title, badge, meta };
      });
    });

    console.log(`Media bowlers count: ${mediaCards.length}`);
    assert.strictEqual(mediaCards.length, 10, 'Media section bowlers filter must show exactly 10 cards');

    const archerMedia = mediaCards.find(c => c.title.includes('Jofra Archer'));
    console.log('Archer Media Card:', archerMedia);
    assert(archerMedia, 'Archer card must be present in Media Section bowlers');
    assert(archerMedia.badge.includes('#10'), 'Archer card badge must be #10');

    // Test clicking Archer's Preview button
    await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.media-player-card'));
      const archerItem = items.find(c => c.textContent.includes('Jofra Archer'));
      if (archerItem) {
        const btn = archerItem.querySelector('.btn-media-preview');
        if (btn) btn.click();
      }
    });
    await new Promise(r => setTimeout(r, 500));

    const modalData = await page.evaluate(() => {
      const modal = document.querySelector('.react-player-modal-backdrop');
      if (!modal) return null;
      const title = modal.querySelector('.react-modal-name')?.textContent?.trim() || '';
      const stats = Array.from(modal.querySelectorAll('.react-metric-card')).map(s => s.textContent.trim());
      return { open: true, title, statsCount: stats.length, sampleStats: stats.slice(0, 5) };
    });

    console.log('Archer Lightbox Modal:', modalData);
    assert(modalData && modalData.open, 'Lightbox modal must open for Archer');
    assert.strictEqual(modalData.title, 'Jofra Archer');
    assert(modalData.statsCount > 0, 'Modal must display verified ball-by-ball IPL stats');

    // Take screenshot of modal
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage10_archer_media_modal.png') });
    console.log('📸 Saved stage10_archer_media_modal.png');

    // Close modal
    await page.click('.react-modal-close-btn');
    await new Promise(r => setTimeout(r, 400));

    console.log('\n🎉 ALL ARCHER REVISION & BOWLING SHORTLIST TESTS PASSED PERFECTLY!');
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error('❌ Test failed with error:', err);
  process.exit(1);
});
