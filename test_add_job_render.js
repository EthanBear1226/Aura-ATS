const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));

  await page.goto('http://127.0.0.1:8000/add-job.html', { waitUntil: 'networkidle0' });
  
  const innerHtml = await page.evaluate(() => {
     const s = document.getElementById('jobDepartment');
     if (!s) return 'Element jobDepartment not found in DOM';
     return s.innerHTML;
  });
  console.log('Department Select InnerHTML:', innerHtml);

  await browser.close();
})();
