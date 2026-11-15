const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/#media', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 600));

  const btns = await page.$$('.btn-media-preview');
  console.log(`Found ${btns.length} .btn-media-preview buttons.`);

  if (btns.length > 0) {
    console.log('Clicking first preview button...');
    await btns[0].click();
    await new Promise(r => setTimeout(r, 600));

    const modal = await page.$('.react-player-modal-backdrop');
    console.log('Modal backdrop element found:', !!modal);

    if (modal) {
      const name = await page.evaluate(() => document.querySelector('.react-modal-name')?.textContent);
      console.log('Modal player name:', name);
      const stats = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('.react-stat-card')).map(c => c.textContent.trim());
      });
      console.log('Modal stat cards:', stats.slice(0, 4));
    }
  }

  await browser.close();
})();
