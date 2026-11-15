const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  for (const width of [1440, 1200, 1024, 768]) {
    await page.setViewport({ width, height: 800 });
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
    await page.evaluate(() => {
      const el = document.getElementById('model-rankings');
      if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await new Promise(r => setTimeout(r, 400));
    
    const info = await page.evaluate(() => {
      const wrapper = document.querySelector('.raw-table-scroll-wrapper');
      return {
        clientWidth: wrapper?.clientWidth,
        scrollWidth: wrapper?.scrollWidth,
        overflow: wrapper ? wrapper.scrollWidth > wrapper.clientWidth : false
      };
    });
    console.log(`Width ${width}:`, info);
  }

  await browser.close();
})();
