const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  
  const offsets = await page.evaluate(() => {
    return {
      methodology: document.getElementById('methodology')?.offsetTop,
      media: document.getElementById('media')?.offsetTop,
      bodyHeight: document.body.scrollHeight
    };
  });
  console.log('Offsets:', offsets);

  await page.evaluate(() => {
    const el = document.getElementById('media');
    if (el) {
      el.scrollIntoView({ behavior: 'instant', block: 'start' });
    }
  });
  await new Promise(r => setTimeout(r, 600));

  const after = await page.evaluate(() => window.scrollY);
  console.log('ScrollY after scrollIntoView:', after);

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage07_verified_media_section_real.png' });
  await browser.close();
})();
