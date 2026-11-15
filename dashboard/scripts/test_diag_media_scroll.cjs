const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  
  console.log('Current URL before click:', page.url());
  const initialMedia = await page.evaluate(() => {
    const el = document.getElementById('media');
    return {
      exists: !!el,
      id: el ? el.id : null,
      offsetTop: el ? el.offsetTop : null,
      tagName: el ? el.tagName : null,
      className: el ? el.className : null
    };
  });
  console.log('Initial media element info:', initialMedia);

  console.log('Clicking header media link...');
  await page.click('a.nav-sheet[href="#media"]');
  await new Promise(r => setTimeout(r, 1200));

  const afterClick = await page.evaluate(() => {
    const el = document.getElementById('media');
    return {
      url: window.location.href,
      scrollY: window.scrollY,
      rect: el ? el.getBoundingClientRect() : null
    };
  });
  console.log('After click:', afterClick);

  await browser.close();
})();
