const puppeteer = require('puppeteer');
const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {
  let filePath = '.' + req.url.split('?')[0];
  if (filePath === './') filePath = './settings.html';
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
  await page.setViewport({ width: 1200, height: 1000 });
  await page.goto('http://localhost:8080/');
  await page.evaluate(() => { localStorage.setItem('aura_user', JSON.stringify({ name: 'Admin', role: 'SuperAdmin' })); });
  await page.goto('http://localhost:8080/settings.html', { waitUntil: 'networkidle0' });
  await page.screenshot({ path: 'settings_screenshot.png', fullPage: true });
  await browser.close();
  server.close();
});
