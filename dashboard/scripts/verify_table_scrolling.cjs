const puppeteer = require('puppeteer');
const assert = require('assert');
const path = require('path');

const ARTIFACT_DIR = 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061';

async function run() {
  console.log('🚀 Starting Table Scrolling & 10 RR Bowlers Coverage Verification...');

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  try {
    await page.goto('http://localhost:5173/#model-rankings', { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 600));

    // Switch to Bowlers tab
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Raw Bowlers Leaderboard'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    // Check row count on default load (should be 25 rows in broad pool)
    const initialRows = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.map((r, i) => {
        const rank = r.querySelector('.machine-rank-badge')?.textContent?.trim() || '';
        const name = r.querySelector('.raw-player-name')?.textContent?.trim() || '';
        const outcome = r.querySelector('.td-outcome')?.textContent?.trim() || '';
        return { idx: i + 1, rank, name, outcome };
      });
    });

    console.log(`Initial Broad Bowlers row count: ${initialRows.length}`);
    assert.strictEqual(initialRows.length, 25, 'Broad bowlers must default to Top 25 (covering all 10 RR picks)');

    // Verify ALL 10 RR bowlers are present in these 25 rows!
    const expectedRRBowlers = [
      { name: 'Mohammed Siraj', rrRank: 'RR #1' },
      { name: 'Jason Holder', rrRank: 'RR #2' },
      { name: 'Kartik Tyagi', rrRank: 'RR #3' },
      { name: 'Lungi Ngidi', rrRank: 'RR #4' },
      { name: 'Krunal Pandya', rrRank: 'RR #5' },
      { name: 'Rasikh Salam', rrRank: 'RR #6' },
      { name: 'Mohammed Shami', rrRank: 'RR #7' },
      { name: 'Anshul Kamboj', rrRank: 'RR #8' },
      { name: 'Ravindra Jadeja', rrRank: 'RR #9' },
      { name: 'Jofra Archer', rrRank: 'RR #10' },
    ];

    expectedRRBowlers.forEach(b => {
      const found = initialRows.find(r => r.name === b.name);
      assert(found, `RR Bowler ${b.name} (${b.rrRank}) must be present in table rows`);
      assert(found.outcome.includes(b.rrRank), `RR Bowler ${b.name} outcome badge must display ${b.rrRank}`);
      console.log(`  ✔ Found ${b.rrRank}: ${b.name} at Model Row #${found.idx} (${found.rank})`);
    });

    console.log('✅ ALL 10 RR shortlisted bowlers verified in table view (not stopping at 6)!');

    // Take screenshot of table top
    await page.evaluate(() => {
      const el = document.getElementById('model-rankings');
      if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage11_table_top_toolbar.png') });
    console.log('📸 Saved stage11_table_top_toolbar.png');

    // Test clicking "↓ Scroll to RR #10 (Archer)" button
    console.log('Testing "↓ Scroll to RR #10 (Archer)" button click...');
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Scroll to RR #10'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 800));

    // Check scroll position of .raw-table-scroll-wrapper
    const scrollPos = await page.evaluate(() => {
      const el = document.querySelector('.raw-table-scroll-wrapper');
      return el ? { scrollTop: el.scrollTop, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight } : null;
    });
    console.log('Table scroll container position:', scrollPos);
    assert(scrollPos && scrollPos.scrollTop > 200, 'Table must scroll vertically when clicking Scroll to RR #10');

    // Take screenshot showing Archer at rank 25 inside the scroll container
    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'stage11_table_scrolled_archer.png') });
    console.log('📸 Saved stage11_table_scrolled_archer.png');

    // Test clicking "RR 10 Only" button
    console.log('Testing "RR 10 Only" filter...');
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.trim() === 'RR 10 Only');
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const rr10Rows = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.raw-table-row'));
      return rows.map(r => r.querySelector('.raw-player-name')?.textContent?.trim() || '');
    });

    console.log('RR 10 Only rows:', rr10Rows);
    assert.strictEqual(rr10Rows.length, 10, 'RR 10 Only must show exactly 10 players');
    expectedRRBowlers.forEach(b => {
      assert(rr10Rows.includes(b.name), `RR 10 Only must include ${b.name}`);
    });
    console.log('✅ "RR 10 Only" filter verified.');

    // Test clicking "All Scored" button
    console.log('Testing "All Scored" button...');
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('All Scored'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 400));

    const allScoredCount = await page.evaluate(() => document.querySelectorAll('.raw-table-row').length);
    console.log(`All Scored bowlers count: ${allScoredCount}`);
    assert.strictEqual(allScoredCount, 130, 'All Scored bowlers must be 130 players');
    console.log('✅ "All Scored" candidate universe verified.');

    // Reset back to "All 10 RR Targets (Top 25)"
    await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('All 10 RR Targets'));
      if (btn) btn.click();
    });
    await new Promise(r => setTimeout(r, 300));

    console.log('\n🎉 ALL TABLE SCROLLING & 10 RR BOWLERS VERIFICATIONS PASSED PERFECTLY!');
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error('❌ Test failed with error:', err);
  process.exit(1);
});
