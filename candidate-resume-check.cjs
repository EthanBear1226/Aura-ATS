const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');

// ReportLab generates a real multipage PDF without storing a candidate's data.
const fixture = spawnSync(path.join(__dirname, 'venv/Scripts/python.exe'), ['-c', [
    'import sys',
    'from io import BytesIO',
    'from reportlab.pdfgen import canvas',
    'buffer = BytesIO()',
    'pdf = canvas.Canvas(buffer, pagesize=(595,842))',
    'for page in (1, 2):',
    '    pdf.drawString(40,790,f"SYNTHETIC RESUME - PAGE {page} / 2")',
    '    pdf.rect(30,30,535,780)',
    '    pdf.drawString(40,45,"END OF PAGE")',
    '    pdf.showPage()',
    'pdf.save()',
    'sys.stdout.buffer.write(buffer.getvalue())',
].join('\n')]);
assert.equal(fixture.status, 0, fixture.stderr.toString());

(async () => {
    const browser = await chromium.launch({
        executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
    });
    try {
        const page = await browser.newPage({ viewport: { width: 1366, height: 1000 } });
        const html = fs.readFileSync(path.join(__dirname, 'candidate-detail.html'), 'utf8');
        let status = 200;
        let validPdf = true;
        let requests = [];
        await page.route('http://preview.test/**', route => {
            const url = new URL(route.request().url());
            if (url.pathname.endsWith('/resume')) {
                assert.equal(route.request().headers().authorization, 'Bearer test');
                requests.push(url.pathname);
                return route.fulfill(status === 200
                    ? { contentType: 'application/pdf', body: validPdf ? fixture.stdout : Buffer.from('invalid') }
                    : { status, json: { detail: 'Denied or missing' } });
            }
            if (url.pathname === '/assets/css/styles.css') {
                return route.fulfill({ contentType: 'text/css', body: fs.readFileSync(path.join(__dirname, url.pathname), 'utf8') });
            }
            return route.fulfill({ contentType: 'text/html', body: html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '') });
        });
        await page.goto('http://preview.test/candidate-detail.html');
        const start = html.indexOf('function alignThreeColumnsHeight');
        const end = html.indexOf('function formatRawResumeText', start);
        const fullStart = html.indexOf('async function togglePdfFullScreen');
        const fullEnd = html.indexOf('async function openOfferDeptTreeModal', fullStart);
        await page.addScriptTag({ content: `
            let currentCandidate={id:1,name:'Preview',pdf_path:'/uploads/secret.pdf'};
            const authFetch=url=>fetch(url,{headers:{Authorization:'Bearer test'}});
            function showToast(){} function prepareStructuredFallbackData(){}
            function showFallbackResumeView(){hideAllResumeViews(); document.getElementById('fallback-resume-card').style.display='block';}
            ${html.slice(start, end)}
            ${html.slice(fullStart, fullEnd)}
            window.addEventListener('resize', alignThreeColumnsHeight);
            alignThreeColumnsHeight();
        ` });
        await page.evaluate(() => loadPdfOrFallback(currentCandidate));
        const src = () => page.locator('#pdf-viewer').getAttribute('src');
        assert((await src()).startsWith('blob:'));
        assert((await src()).endsWith('&view=FitH'));
        assert.equal(requests.length, 1);

        for (const width of [1920, 1440, 1280, 1024, 800, 390, 320]) {
            await page.setViewportSize({ width, height: 900 });
            await page.evaluate(() => alignThreeColumnsHeight());
            const layout = await page.evaluate(() => {
                const rect = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
                const toolbar = rect('.pdf-toolbar-header');
                return {
                    frame: rect('#pdf-viewer'), pane: rect('.left-main-pane'),
                    overflow: document.querySelector('main').scrollWidth - document.querySelector('main').clientWidth,
                    toolbarOverflow: [...document.querySelectorAll('.pdf-toolbar-header button')].some(button => {
                        const r = button.getBoundingClientRect();
                        return r.left < toolbar.left || r.right > toolbar.right || r.bottom > toolbar.bottom;
                    }),
                };
            });
            assert(layout.frame.height > 450, `${width}px: PDF collapsed to ${layout.frame.height}px`);
            assert(layout.frame.bottom <= layout.pane.bottom, `${width}px: PDF outside pane`);
            assert(layout.overflow <= 1, `${width}px: horizontal overflow ${layout.overflow}`);
            assert(!layout.toolbarOverflow, `${width}px: toolbar controls overflow`);
        }

        await page.getByRole('button', { name: '放大简历', exact: true }).click();
        assert((await src()).includes('zoom=115'));
        await page.getByRole('button', { name: '缩小简历', exact: true }).click();
        assert((await src()).includes('zoom=100'));
        await page.getByRole('button', { name: '适应宽度', exact: true }).click();
        assert((await src()).endsWith('&view=FitH'));
        await page.getByRole('button', { name: '结构化档案', exact: true }).click();
        assert(await page.locator('#fallback-resume-card').isVisible());
        await page.getByRole('button', { name: '查看原件', exact: true }).click();
        await page.waitForFunction(() => document.getElementById('pdf-viewer').style.display === 'block');
        await page.setViewportSize({ width: 1280, height: 900 });
        await page.getByRole('button', { name: '切换全屏', exact: true }).click();
        await page.waitForFunction(() => !!document.fullscreenElement);
        assert(await page.getByRole('button', { name: '适应宽度', exact: true }).isVisible());
        await page.getByRole('button', { name: '切换全屏', exact: true }).click();
        await page.waitForFunction(() => !document.fullscreenElement);

        for (const [httpStatus, selector] of [[403, '#pdf-error-fallback'], [404, '#pdf-missing-fallback']]) {
            status = httpStatus;
            await page.evaluate(() => loadPdfOrFallback(currentCandidate));
            assert(await page.locator(selector).isVisible());
            assert(!(await src()).includes('/uploads/'));
        }
        status = 200;
        validPdf = false;
        await page.evaluate(() => loadPdfOrFallback(currentCandidate));
        assert(await page.locator('#pdf-unsupported-fallback').isVisible());
        validPdf = true;
        await page.evaluate(() => loadPdfOrFallback(currentCandidate));
        assert(await page.locator('#pdf-viewer').isVisible());
        await page.evaluate(() => downloadResumePdf());
        assert(requests.every(url => url === '/api/candidates/1/resume'));
        console.log('PASS: real two-page PDF; authorized blob fetch; desktop/mobile flex height; toolbar bounds; fit-width; zoom; mode switch; fullscreen; 403/404/invalid PDF; retry; download');

        // Optional end-to-end check against the isolated local preview server.
        if (process.env.AURA_PREVIEW_URL) {
            const base = process.env.AURA_PREVIEW_URL;
            const actual = await browser.newPage({ viewport: { width: 1280, height: 900 } });
            await actual.goto(`${base}/login.html`);
            await actual.getByRole('button', { name: '登录', exact: true }).click();
            await actual.waitForURL('**/index.html');
            await actual.goto(`${base}/candidate-detail.html?id=1`);
            await actual.waitForFunction(() => document.querySelector('#pdf-viewer').src.startsWith('blob:'));
            assert.equal(await actual.locator('.pdf-toolbar-header svg').count(), 8);
            // The PDF plugin paints asynchronously after the iframe load event.
            await actual.waitForTimeout(2000);
            const assertPdfPainted = async () => {
                const image = await actual.locator('#pdf-viewer').screenshot();
                const check = spawnSync(path.join(__dirname, 'venv/Scripts/python.exe'), ['-c', [
                    'import sys',
                    'from io import BytesIO',
                    'from PIL import Image',
                    'pixels = list(Image.open(BytesIO(sys.stdin.buffer.read())).convert("RGB").getdata())',
                    'white = sum(r>240 and g>240 and b>240 for r,g,b in pixels)',
                    'green = sum(g>60 and g>r*1.5 and g>b*1.1 for r,g,b in pixels)',
                    'assert white > len(pixels)*0.3 and green>100, "PDF plugin has not painted the synthetic page"',
                ].join('\n')], { input: image });
                assert.equal(check.status, 0, check.stderr.toString());
            };
            await assertPdfPainted();
            await actual.screenshot({ path: path.join(__dirname, 'candidate-resume-desktop_screenshot.png') });
            const frameBounds = await actual.locator('#pdf-viewer').boundingBox();
            await actual.mouse.move(frameBounds.x + frameBounds.width / 2, frameBounds.y + 100);
            await actual.mouse.wheel(0, 650);
            await actual.waitForTimeout(500);
            await assertPdfPainted();
            await actual.screenshot({ path: path.join(__dirname, 'candidate-resume-page2_screenshot.png') });
            await actual.getByText('备注', { exact: true }).click();
            assert(await actual.locator('#tab-pane-4').isVisible());
            await actual.getByText('基本信息', { exact: true }).click();
            assert(await actual.locator('#pdf-viewer').isVisible());
            await actual.mouse.move(frameBounds.x + frameBounds.width / 2, frameBounds.y + 100);
            await actual.mouse.wheel(0, -1500);
            await actual.setViewportSize({ width: 390, height: 844 });
            const mobile = await actual.evaluate(() => ({
                height: document.querySelector('#pdf-viewer').getBoundingClientRect().height,
                overflow: document.querySelector('main').scrollWidth - document.querySelector('main').clientWidth,
            }));
            assert(mobile.height > 450);
            assert.equal(mobile.overflow, 0);
            await actual.evaluate(() => { document.querySelector('main').scrollTop = 0; });
            await actual.waitForTimeout(500);
            await assertPdfPainted();
            await actual.screenshot({ path: path.join(__dirname, 'candidate-resume-mobile_screenshot.png') });
            console.log('PASS: local API login and candidate PDF, toolbar icons, PDF painted pixel checks, second-page scroll, tabs, desktop/mobile screenshots');
        }
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
