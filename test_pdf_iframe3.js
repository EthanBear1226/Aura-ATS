const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('http://127.0.0.1:8000/index.html');
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.evaluate(() => { 
      sessionStorage.setItem('last_parsed_candidate', JSON.stringify({
          id: 999, name: "Test PDF", job: "Test Job", stage: "初筛", exp: "本科",
          phone: "123", email: "a@a.com", skills: [], raw_text: "", ai_summary: "", ai_analysis: "",
          pdf_path: "/uploads/dummy.pdf", created_at: new Date()
      }));
  });
  await page.goto('http://127.0.0.1:8000/candidate-detail.html?id=999', { waitUntil: 'networkidle0' });
  
  const iframeSrc = await page.evaluate(() => document.getElementById('pdf-viewer').src);
  console.log('iframe src after fix:', iframeSrc);
  
  const btnStyle = await page.evaluate(() => window.getComputedStyle(document.getElementById('pdf-download-btn')).display);
  console.log('btn display:', btnStyle);

  await browser.close();
})();
