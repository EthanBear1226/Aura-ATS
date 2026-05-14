const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  page.on('requestfailed', request => console.error('FAILED:', request.url(), request.failure().errorText));

  await page.goto('http://127.0.0.1:8000/add-job.html', { waitUntil: 'networkidle0' });
  
  const deptSelect = await page.evaluate(() => {
     const s = document.getElementById('jobDepartment');
     return s ? s.innerHTML : 'null';
  });
  console.log('Department Select InnerHTML:', deptSelect);

  await browser.close();
})();
