const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1366,height:1000}});
  const html=fs.readFileSync(path.join(__dirname,'candidate-detail.html'),'utf8');
  let status=200, requests=[];
  await page.route('http://preview.test/**',route=>{
   const url=route.request().url();
   if(url.endsWith('/resume')) {
    requests.push(url);
    return route.fulfill(status===200?{contentType:'application/pdf',body:fs.readFileSync(path.join(__dirname,'preview-fixture.pdf'))}:{status,json:{detail:'Denied or missing'}});
   }
   return route.fulfill({contentType:'text/html',body:html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'')});
  });
  await page.goto('http://preview.test/candidate-detail.html');
  const start=html.indexOf('let currentPdfZoom');
  const end=html.indexOf('function formatRawResumeText',start);
  await page.addScriptTag({content:`let currentCandidate={id:1,name:'Preview',pdf_path:'/uploads/secret.pdf'}; const authFetch=(url)=>fetch(url,{headers:{Authorization:'Bearer test'}}); function showToast(){} function prepareStructuredFallbackData(){} function showFallbackResumeView(){}\n${html.slice(start,end)}`});
  await page.evaluate(()=>loadPdfOrFallback(currentCandidate));
  assert((await page.locator('#pdf-viewer').getAttribute('src')).startsWith('blob:'));
  assert.equal(requests.length,1);
  await page.evaluate(()=>zoomPdfIn());
  assert((await page.locator('#pdf-viewer').getAttribute('src')).includes('zoom=115'));
  status=403;
  await page.evaluate(()=>loadPdfOrFallback(currentCandidate));
  assert(await page.locator('#pdf-error-fallback').isVisible());
  assert(!(await page.locator('#pdf-viewer').getAttribute('src')).includes('/uploads/'));
  status=404;
  await page.evaluate(()=>loadPdfOrFallback(currentCandidate));
  assert(await page.locator('#pdf-missing-fallback').isVisible());
  status=200;
  await page.evaluate(()=>loadPdfOrFallback(currentCandidate));
  assert(await page.locator('#pdf-viewer').isVisible());
  await page.evaluate(()=>downloadResumePdf());
  assert(requests.every(url=>url==='http://preview.test/api/candidates/1/resume'));
  console.log('PASS: candidate preview through authorized fetch; blob zoom; 403 and 404 states; retry; download');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
