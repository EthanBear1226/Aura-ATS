const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), http = require('http'), assert = require('assert');

(async () => {
    const server = http.createServer((req, res) => {
        const file = path.join(__dirname, req.url.split('?')[0]);
        if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
        res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
        res.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    let browser;
    try {
        browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
        const context = await browser.newContext({viewport:{width:1280,height:900}});
        await context.addInitScript(() => {
            localStorage.setItem('aura_user', JSON.stringify({role:'Admin',name:'Upload Tester'}));
            localStorage.setItem('aura_token', 'test.' + btoa(JSON.stringify({exp:4102444800})) + '.test');
        });
        const page = await context.newPage(), errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.route('**/api/jobs', route => route.fulfill({json:[{id:7,title:'Frontend',status:'热招中'},{id:8,title:'Backend',status:'热招中'}]}));
        await page.goto(`http://127.0.0.1:${server.address().port}/add-candidate.html`);
        await page.waitForFunction(() => document.querySelector('#modal-job-select option[value="7"]'));
        await page.locator('.custom-select-trigger').click();
        await page.locator('.custom-option[data-value="7"]').click();
        const pdf = (name, text) => ({name,mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n' + text)});
        let calls = 0, release;
        await page.route('**/api/parse-resumes', async route => {
            calls++;
            const body = route.request().postDataBuffer().toString();
            assert(body.includes(`name="job_id"\r\n\r\n${calls <= 2 ? 7 : 8}`));
            if (calls === 1) {
                assert.equal((body.match(/name="files"/g)||[]).length,2);
                assert(body.includes('FIRST CONTENT') && body.includes('SECOND CONTENT'));
                await new Promise(resolve => { release = resolve; });
                await route.fulfill({json:{results:[{status:'success',candidate:{id:201,name:'First'}},{status:'failed',detail:'Temporary parser failure'}]}});
            } else {
                assert.equal((body.match(/name="files"/g)||[]).length,1);
                if (calls === 2) assert(!body.includes('FIRST CONTENT') && body.includes('SECOND CONTENT'));
                await route.fulfill({json:{results:[{status:'success',candidate:{id:202,name:'Second'}}]}});
            }
        });
        await page.locator('#resume-file').setInputFiles([
            pdf('same.pdf','FIRST CONTENT'), pdf('same.pdf','SECOND CONTENT'), pdf('duplicate.pdf','FIRST CONTENT'),
            {name:'wrong.txt',mimeType:'text/plain',buffer:Buffer.from('text')},
            pdf('fake.pdf','fake'),
            {name:'empty.pdf',mimeType:'application/pdf',buffer:Buffer.alloc(0)},
            {name:'large.pdf',mimeType:'application/pdf',buffer:Buffer.alloc(5*1024*1024+1)}
        ].map((file,index)=>index===4?{...file,buffer:Buffer.from('not a pdf')}:file));
        await page.waitForFunction(()=>window.resumeUploadBusy && document.querySelector('#resume-file').disabled);
        await page.waitForTimeout(150);
        assert.equal(calls,1);
        assert(await page.locator('#modal-job-select').isDisabled());
        assert(await page.evaluate(()=>{
            const event=new Event('beforeunload',{cancelable:true});
            window.dispatchEvent(event); return event.defaultPrevented;
        }));
        await page.locator('#uploadArea').dispatchEvent('drop'); // No handler data: busy lock must return before reads.
        assert.equal(calls,1);
        release();
        await page.waitForFunction(()=>!window.resumeUploadBusy);
        assert.equal(await page.locator('.upload-result.success').count(),1);
        assert.equal(await page.locator('.upload-result').count(),7);
        assert((await page.locator('#upload-results').innerText()).includes('重复文件'));
        await page.evaluate(()=>document.querySelector('#modal-job-select').value='8');
        await page.locator('#retryFailedUploads').click();
        await page.waitForFunction(()=>!window.resumeUploadBusy && document.querySelectorAll('.upload-result.success').length===2);
        assert.equal(calls,2);
        assert(await page.locator('#retryFailedUploads').isHidden());
        assert.equal(await page.locator('#upload-results a').count(),2);
        assert(!await page.evaluate(()=>{const e=new Event('beforeunload',{cancelable:true});window.dispatchEvent(e);return e.defaultPrevented;}));
        await page.evaluate(()=>document.querySelector('#modal-job-select').value='7');
        await page.locator('#resume-file').setInputFiles(pdf('renamed.pdf','FIRST CONTENT'));
        await page.waitForFunction(()=>!window.resumeUploadBusy);
        assert.equal(calls,2,'A successful file must not be submitted again for the same job');
        await page.evaluate(()=>document.querySelector('#modal-job-select').value='8');
        await page.locator('#resume-file').setInputFiles(pdf('again.pdf','FIRST CONTENT'));
        await page.waitForFunction(()=>!window.resumeUploadBusy);
        assert.equal(calls,3); // A different job may receive the same resume.
        assert.equal(errors.length,0,errors.join('\n'));

        // A disconnected response is not safe to retry automatically.
        await page.unroute('**/api/parse-resumes');
        await page.route('**/api/parse-resumes', route=>route.abort('failed'));
        await page.locator('#resume-file').setInputFiles(pdf('uncertain.pdf','UNCERTAIN CONTENT'));
        await page.waitForFunction(()=>!window.resumeUploadBusy);
        assert((await page.locator('#upload-results').innerText()).includes('结果待确认'));
        assert(await page.locator('#retryFailedUploads').isHidden());
        await page.setViewportSize({width:390,height:844});
        await page.screenshot({path:path.join(__dirname,'upload-mobile.png')});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        assert.equal(errors.length,0,errors.join('\n'));
        console.log('PASS upload: validation, content duplicates, busy lock, leave guard, same-name mapping, retry failed only, original job, preserved successes, uncertain response and mobile');
    } finally {
        if (browser) await browser.close();
        await new Promise(resolve=>server.close(resolve));
    }
})().catch(error=>{console.error(error);process.exitCode=1;});
