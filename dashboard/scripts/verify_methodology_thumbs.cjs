const puppeteer = require('../node_modules/puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  await page.goto('http://localhost:5173/#methodology', { waitUntil: 'networkidle0', timeout: 15000 });

  // Click Module 09 tab
  await page.click('#tab-09-raw-model-ranks');
  await new Promise(r => setTimeout(r, 600));

  const thumbs = await page.$$eval('#methodology .raw-player-thumb-img', imgs => {
    return imgs.slice(0, 15).map(img => ({
      src: img.src,
      ok: img.complete && img.naturalWidth > 0,
      w: img.naturalWidth,
      h: img.naturalHeight
    }));
  });

  console.log(`Methodology Chapter 6 Thumbnails loaded: ${thumbs.filter(t => t.ok).length} of ${thumbs.length}`);
  await browser.close();
})();
