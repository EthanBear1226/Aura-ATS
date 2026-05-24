const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/index.html');
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/candidate-detail.html?id=6', { waitUntil: 'networkidle0' });
  
  await page.screenshot({ path: 'pdf_ss.png' });
  
  const iframeSrc = await page.evaluate(() => document.getElementById('pdf-viewer').src);
  console.log('iframe src:', iframeSrc);

  await browser.close();
})();
