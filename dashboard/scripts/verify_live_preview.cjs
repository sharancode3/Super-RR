const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  await page.goto('http://localhost:5173/portraits/contact_sheet.html', { waitUntil: 'networkidle0' });

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/live_check_contact_sheet.png' });

  // Click on the first preview button
  const btn = await page.$('.btn-preview-modal');
  if (btn) {
    await btn.click();
    await new Promise(r => setTimeout(r, 400));
    await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/live_check_contact_modal_open.png' });
  }

  await browser.close();
  console.log('Contact sheet verified successfully');
})().catch(e => { console.error(e); process.exit(1); });
