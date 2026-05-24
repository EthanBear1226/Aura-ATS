const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  
  await page.goto('http://127.0.0.1:8000/interviews.html', { waitUntil: 'networkidle0' });
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://127.0.0.1:8000/interviews.html', { waitUntil: 'networkidle0' });
  
  // Try to click "填写评价"
  const btns = await page.$$('button');
  let clicked = false;
  for (const btn of btns) {
     const text = await page.evaluate(el => el.innerText, btn);
     if (text.includes('填写评价')) {
         await btn.click();
         clicked = true;
         break;
     }
  }
  
  console.log('Clicked feedback button:', clicked);
  if (clicked) {
      await new Promise(r => setTimeout(r, 500));
      await page.screenshot({ path: 'feedback_modal_ss.png' });
      
      const isVisible = await page.evaluate(() => {
          const m = document.getElementById('feedbackModal');
          return window.getComputedStyle(m).display;
      });
      console.log('Modal display style:', isVisible);
  } else {
      console.log('No 填写评价 button found. Let me check the HTML.');
      const html = await page.content();
      console.log('HTML excerpt:', html.substring(0, 1000));
  }

  await browser.close();
})();
