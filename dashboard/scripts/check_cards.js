import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 600));

  await page.screenshot({ path: 'clean_starting_section_desktop.png', fullPage: false });
  console.log('Saved clean_starting_section_desktop.png');

  // Check on mobile 390x844
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 600));

  await page.screenshot({ path: 'clean_starting_section_mobile.png', fullPage: false });
  console.log('Saved clean_starting_section_mobile.png');

  await browser.close();
})();
