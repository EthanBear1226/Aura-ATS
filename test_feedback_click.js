const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/interviews.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/interviews.html', { waitUntil: 'networkidle0' });
  
  // Try to click "填写评价"
  const btns = await page.$$('button');
  for (const btn of btns) {
     const text = await page.evaluate(el => el.innerText, btn);
     if (text.includes('填写评价')) {
         await btn.click();
         break;
     }
  }
  
  await new Promise(r => setTimeout(r, 500));
  
  // Get active item
  let active = await page.evaluate(() => document.querySelector('#feedbackSegmentedControl .active').dataset.value);
  console.log('Active before click:', active);
  
  // Click on "不满意"
  const items = await page.$$('#feedbackSegmentedControl .segmented-item');
  for (const item of items) {
      const val = await page.evaluate(el => el.dataset.value, item);
      if (val === '不满意') {
          await item.click();
          break;
      }
  }
  
  active = await page.evaluate(() => document.querySelector('#feedbackSegmentedControl .active').dataset.value);
  console.log('Active after click:', active);
  
  const hiddenVal = await page.evaluate(() => document.getElementById('feedbackResult').value);
  console.log('Hidden input value:', hiddenVal);

  await browser.close();
})();
