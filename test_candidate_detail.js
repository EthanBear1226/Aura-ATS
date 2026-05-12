const puppeteer = require('puppeteer');
const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
  let filePath = '.' + req.url.split('?')[0];
  if (filePath === './') filePath = './candidate-detail.html';
  const extname = String(path.extname(filePath)).toLowerCase();
  const mimeTypes = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
  const contentType = mimeTypes[extname] || 'application/octet-stream';
  fs.readFile(filePath, (error, content) => {
    if (error) { res.writeHead(404); res.end('File not found'); }
    else { res.writeHead(200, { 'Content-Type': contentType }); res.end(content, 'utf-8'); }
  });
});

server.listen(8080, async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  
  // Set mock local storage and session storage
  await page.goto('http://localhost:8080/');
  await page.evaluate(() => {
    localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'hr' }));
    const mockData = {"name":"张佳妮","job":"错误","stage":"初筛","exp":"未知","phone":"暂无","email":"未知","skills":["解析失败"],"raw_text":"Hello World\n","ai_summary":"服务响应异常","ai_analysis":"400 User location is not supported for the API use.","match_score":null,"match_reason":null,"pdf_path":"/uploads/dummy.pdf","id":5,"created_at":"2026-05-09T01:37:43.405221","updated_at":"2026-05-09T01:37:43.405281","logs":[]};
    sessionStorage.setItem('last_parsed_candidate', JSON.stringify(mockData));
  });
  
  await page.goto('http://localhost:8080/candidate-detail.html?id=5', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  
  await browser.close();
  server.close();
});
