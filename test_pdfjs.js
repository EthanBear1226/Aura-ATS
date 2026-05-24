const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('https://mozilla.github.io/pdf.js/web/viewer.html?file=https://raw.githubusercontent.com/mozilla/pdf.js/ba2edeae/web/compressed.tracemonkey-pldi-09.pdf', { waitUntil: 'networkidle0' });
  
  await page.screenshot({ path: 'pdfjs_ss.png' });
  console.log('PDF.js loads fine');

  await browser.close();
})();
