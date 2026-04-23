const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8000/candidates.html?action=add');
  // wait for a bit
  await page.waitForTimeout(1000);
  
  // check if modal is active
  const isModalActive = await page.$eval('#uploadModal', el => el.classList.contains('active'));
  console.log('Upload modal active:', isModalActive);
  
  await browser.close();
})();
