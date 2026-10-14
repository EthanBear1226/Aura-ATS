const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert');
(async()=>{
  const server=http.createServer((req,res)=>{
    const file=path.join(__dirname,req.url.split('?')[0]);
    if(!fs.existsSync(file)){res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
    const context=await browser.newContext({viewport:{width:1366,height:1000}});
    await context.addInitScript(()=>{
      localStorage.setItem('aura_user',JSON.stringify({role:'Interviewer',name:'Owner'}));
      localStorage.setItem('aura_token','test.'+btoa(JSON.stringify({exp:4102444800}))+'.test');
    });
    const page=await context.newPage(); const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.clock.setFixedTime(new Date('2026-10-13T12:00:00+08:00'));
    const item=(id,start,end,extra={})=>({id,candidate_name:`Candidate ${id}`,job_title:'Backend Engineer',location:'Online',candidate_stage:'面试中',status:'已安排',start_time:start,end_time:end,...extra});
    const data=[
      item(1,'2026-10-13T10:00:00','2026-10-13T11:00:00'),
      item(2,'2026-10-13T11:30:00','2026-10-13T12:30:00'),
      item(3,'2026-10-14T10:00:00','2026-10-14T11:00:00'),
      item(4,'2026-10-14T12:00:00','2026-10-14T13:00:00',{status:'已取消'}),
      item(5,'2026-10-12T10:00:00','2026-10-12T11:00:00',{candidate_stage:'已归档'}),
      item(6,'2026-10-30T10:00:00','2026-10-30T11:00:00',{job_title:'Product Manager'}),
      ...Array.from({length:6},(_,i)=>item(7+i,`2026-10-0${i+1}T10:00:00`,`2026-10-0${i+1}T11:00:00`,{status:'已完成',feedback_result:'满意'})),
      item(13,'2026-10-14T15:00:00','2026-10-14T16:00:00',{candidate_name:'<img src=x onerror=alert(1)>',candidate_stage:'已淘汰'}),
      item(14,'2026-10-13T12:30:00','2026-10-13T13:30:00'),
      item(15,'2026-10-12T11:00:00','2026-10-12T12:00:00')
    ];
    let fail=false;
    await page.route('**/api/interviewer/workbench',route=>route.fulfill(fail?{status:500,json:{detail:'error'}}:{json:data}));
    const url=`http://127.0.0.1:${server.address().port}/interviewer-workbench.html`;
    await page.goto(url);
    await page.waitForFunction(()=>document.querySelectorAll('.interview-card').length===15);
    assert.equal(await page.locator('#feedbackCount').innerText(),'2');
    assert.equal(await page.locator('#upcomingCount').innerText(),'2');
    assert.equal(await page.locator('#completedCount').innerText(),'6');
    assert.equal(await page.locator('#todayCount').innerText(),'3');
    assert.equal(await page.locator('#reminderCount').innerText(),'3 项');
    assert.deepEqual(await page.locator('.reminder-label').allInnerTexts(),['反馈逾期','面试已超时','即将开始']);
    assert.equal(await page.locator('.reminder-link').count(),3);
    assert.equal(await page.locator('#interviewList img').count(),0);
    await page.locator('[data-filter="feedback"]').click();
    assert.equal(await page.locator('.interview-card').count(),2);
    assert((await page.locator('.candidate-name').allInnerTexts()).some(name => name === 'Candidate 1'));
    await page.locator('[data-filter="upcoming"]').click();
    assert.equal(await page.locator('.interview-card').count(),2);
    await page.locator('[data-filter="completed"]').click();
    assert.equal(await page.locator('.interview-card').count(),6);
    await page.locator('[data-sort="desc"]').click();
    assert.equal(await page.locator('.candidate-name').first().innerText(),'Candidate 12');
    await page.locator('#interviewSearch').fill('Candidate 8');
    assert.equal(await page.locator('.interview-card').count(),1);
    await page.reload();
    await page.waitForFunction(()=>document.querySelectorAll('.interview-card').length===1);
    assert.equal(await page.locator('#interviewSearch').inputValue(),'Candidate 8');
    assert.equal(await page.locator('[data-sort="desc"]').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('select').count(),0);
    const geometry = await page.locator('.page-content').boundingBox();
    const mainGeometry = await page.locator('.main-content').boundingBox();
    assert(Math.abs(geometry.width-mainGeometry.width)<2, 'Workbench must fill main content width');
    assert.equal(await page.locator('#completedCount').innerText(),'6');
    await page.locator('#clearFilters').click();
    assert.equal(await page.locator('.interview-card').count(),15);
    await page.locator('#interviewSearch').fill('product manager');
    assert.equal(await page.locator('.interview-card').count(),1);
    await page.locator('#clearFilters').click();
    await page.locator('[data-filter="closed"]').click();
    assert.equal(await page.locator('.interview-card').count(),3);
    await page.screenshot({path:path.join(__dirname,'workbench-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(__dirname,'workbench-mobile.png'),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.locator('#interviewSearch').fill('no match');
    assert((await page.locator('#interviewList').innerText()).includes('没有符合'));
    fail=true;
    await page.locator('#refreshInterviews').click();
    await page.waitForFunction(()=>!document.querySelector('#retryLoad').hidden);
    assert.equal(await page.locator('#feedbackCount').innerText(),'--');
    fail=false; await page.locator('#retryLoad').click();
    await page.waitForFunction(()=>document.querySelector('#feedbackCount').textContent==='2');
    assert.equal(await page.locator('#feedbackCount').innerText(),'2');
    data.splice(0);
    await page.setViewportSize({width:1920,height:1080});
    await page.locator('#refreshInterviews').click();
    await page.waitForFunction(()=>document.querySelector('#todayCount').textContent==='0');
    const wide = await page.locator('.page-content').boundingBox();
    assert(wide.width>1800, 'Wide empty workbench should use available width');
    assert.equal(await page.locator('#reminderCount').innerText(),'0 项');
    await page.mouse.move(1800,100);
    await page.waitForTimeout(350);
    await page.screenshot({path:path.join(__dirname,'workbench-wide-empty.png'),fullPage:true});
    assert.equal(errors.length,0,errors.join('\n'));
    console.log('PASS: no duplicate cards; pending after end; cancelled/terminal excluded; six completed; search; sort; URL restoration; clear; empty; error/retry; XSS escaping; mobile overflow');
  }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
