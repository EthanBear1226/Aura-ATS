const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('file://' + process.cwd() + '/add-job.html');
  await new Promise(r => setTimeout(r, 2000));
  
  const hasCustomSelect = await page.evaluate(() => document.querySelectorAll('.custom-select-wrapper').length);
  const isQuillLoaded = await page.evaluate(() => document.querySelector('.ql-editor') !== null);
  const quillText = await page.evaluate(() => typeof Quill !== 'undefined');
  console.log('Custom selects count:', hasCustomSelect);
  console.log('Is Quill loaded?', isQuillLoaded);
  console.log('Is Quill object defined?', quillText);

  await browser.close();
})();
