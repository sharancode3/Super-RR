const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1366, height: 768 });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  
  await page.evaluate(() => {
    const el = document.getElementById('model-rankings');
    if (el) el.scrollIntoView({ behavior: 'instant', block: 'start' });
  });
  await new Promise(r => setTimeout(r, 600));

  const tableInfo = await page.evaluate(() => {
    const wrapper = document.querySelector('.raw-table-scroll-wrapper');
    const table = document.querySelector('.raw-comparison-table');
    const ths = Array.from(document.querySelectorAll('.raw-comparison-table th')).map(th => ({
      text: th.textContent.trim(),
      width: th.offsetWidth
    }));
    return {
      wrapperClientWidth: wrapper?.clientWidth,
      wrapperScrollWidth: wrapper?.scrollWidth,
      hasOverflow: wrapper ? wrapper.scrollWidth > wrapper.clientWidth : false,
      ths
    };
  });
  console.log('Table info at 1366x768:', JSON.stringify(tableInfo, null, 2));

  await page.screenshot({ path: 'C:/Users/tms10/.gemini/antigravity/brain/58919bc3-f90c-4e68-8103-3c4969f79061/stage08_table_overflow_diag.png' });
  await browser.close();
})();
