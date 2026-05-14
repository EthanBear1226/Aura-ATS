const fs = require('fs');

// 1. Update app.js
let appJs = fs.readFileSync('assets/js/app.js', 'utf8');

appJs = appJs.replace(
  /function openScheduleDrawer\(candidateName = '', candidateEmail = '', candidateJob = ''\) \{/,
  `let currentDrawerCandidateId = null;
let currentDrawerCandidateJob = null;
function openScheduleDrawer(candidateName = '', candidateEmail = '', candidateJob = '', candidateId = null) {
    currentDrawerCandidateId = candidateId;
    currentDrawerCandidateJob = candidateJob;`
);

const realLoadDrawer = `async function loadDrawerAvailability() {
    const date = document.getElementById('drawerInterviewDate').value;
    const interviewer = document.getElementById('drawerInterviewerSelect').value;
    if (!date || !interviewer) return;
    
    // Update status text
    const statusText = document.getElementById('drawerAvailabilityStatus');
    if (statusText) statusText.innerHTML = \`已同步 <b>系统日历</b> 实时数据\`;
    
    try {
        const response = await fetch(\`/api/calendar/freebusy?interviewer=\${interviewer}&date=\${date}\`);
        if (!response.ok) throw new Error("Failed to fetch slots");
        const slots = await response.json();
        
        const container = document.getElementById('drawerAvailabilityBlocks');
        container.innerHTML = slots.map((slot, index) => {
            const isFree = slot.isFree;
            return \`
            <label style="border:1px solid \${isFree ? 'var(--border-color)' : '#eee'}; background:\${isFree ? '#fff' : '#fafafa'}; padding:8px; border-radius:4px; text-align:center; cursor:\${isFree ? 'pointer' : 'not-allowed'}; opacity:\${isFree ? '1' : '0.5'}; display:block; margin-bottom:8px;">
                <input type="radio" name="drawerTimeSlot" value="\${slot.time}" \${!isFree ? 'disabled' : ''} style="display:none;">
                <div style="font-size:14px; font-weight:500;">\${slot.time}</div>
                <div style="font-size:12px; color:var(--text-secondary);">\${isFree ? '空闲' : '忙碌'}</div>
            </label>
            \`;
        }).join('');
        
        // Add event listeners to radio buttons to update UI on select
        container.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                container.querySelectorAll('label').forEach(l => l.style.borderColor = 'var(--border-color)');
                e.target.parentElement.style.borderColor = 'var(--primary-color)';
            });
        });
    } catch(e) { 
        console.error(e); 
        const container = document.getElementById('drawerAvailabilityBlocks');
        if (container) container.innerHTML = \`<div style="text-align:center; color:#FF3B30; font-size:13px; padding:20px;">获取档期失败</div>\`;
    }
}`;

const realSubmitDrawer = `async function submitDrawerSchedule() {
    const date = document.getElementById('drawerInterviewDate').value;
    const interviewer = document.getElementById('drawerInterviewerSelect').value;
    const slotRadio = document.querySelector('input[name="drawerTimeSlot"]:checked');
    
    if (!date || !interviewer || !slotRadio || !currentDrawerCandidateId) {
        if(window.showToast) window.showToast("请完整选择面试日期、面试官和时间段", "error");
        return;
    }
    
    const time = slotRadio.value; // e.g. "10:00 - 11:00"
    const startTimeStr = time.split(' - ')[0]; // extract "10:00" from "10:00 - 11:00" if applicable
    const start_time = \`\${date}T\${startTimeStr || time}:00\`;
    
    // Simple mock for end time (1 hour later)
    const [hour, min] = (startTimeStr || time).split(':');
    const end_time = \`\${date}T\${parseInt(hour)+1}:\${min}:00\`;

    const btn = document.getElementById('drawerSubmitBtn');
    const originalText = btn.innerText;
    btn.innerText = "发送邀约中...";
    btn.disabled = true;
    
    try {
        const payload = {
            candidate_id: currentDrawerCandidateId,
            interviewer_name: interviewer,
            job_title: currentDrawerCandidateJob || '未知',
            start_time: start_time,
            end_time: end_time,
            location: "线上 / 待定"
        };

        const response = await fetch('/api/interviews', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            if(window.showToast) window.showToast("邀约已发送，日程已锁定", "success");
            closeScheduleDrawer();
        } else {
            const data = await response.json();
            if(window.showToast) window.showToast(\`安排失败: \${data.detail || '未知错误'}\`, "error");
        }
    } catch(e) {
        console.error(e);
        if(window.showToast) window.showToast("安排失败，请检查网络", "error");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}`;

appJs = appJs.replace(/function mockLoadDrawerAvailability\(\) \{[\s\S]*?\}\n/, realLoadDrawer + '\n\n');
appJs = appJs.replace(/function submitDrawerSchedule\(\) \{[\s\S]*?\}\n/, realSubmitDrawer + '\n\n');
appJs = appJs.replace(/onchange="mockLoadDrawerAvailability\(\)"/g, 'onchange="loadDrawerAvailability()"');

fs.writeFileSync('assets/js/app.js', appJs);

// 2. Update candidates.html
let candidatesHtml = fs.readFileSync('candidates.html', 'utf8');
candidatesHtml = candidatesHtml.replace(
  /openScheduleDrawer\('\${c\.name}', '\${c\.email \|\| ''}', '\${c\.job}'\)/g,
  `openScheduleDrawer('\${c.name}', '\${c.email || ''}', '\${c.job}', \${c.id})`
);
fs.writeFileSync('candidates.html', candidatesHtml);

// 3. Update candidate-detail.html
let detailHtml = fs.readFileSync('candidate-detail.html', 'utf8');
detailHtml = detailHtml.replace(
  /openScheduleDrawer\(currentCandidate\?\.name \|\| '', currentCandidate\?\.email \|\| '', currentCandidate\?\.job \|\| ''\)/g,
  `openScheduleDrawer(currentCandidate?.name || '', currentCandidate?.email || '', currentCandidate?.job || '', currentCandidate?.id)`
);
detailHtml = detailHtml.replace(
  /openScheduleDrawer\('\${candidate\.name}', '\${candidate\.email \|\| ''}', '\${candidate\.job}'\)/g,
  `openScheduleDrawer('\${candidate.name}', '\${candidate.email || ''}', '\${candidate.job}', \${candidate.id})`
);

// Remove the inline functions. Need robust replace since there could be differences.
detailHtml = detailHtml.replace(/\/\/ Override mock function from app\.js to use real API[\s\S]*?async function loadDrawerAvailability[\s\S]*?\} catch\(e\) \{[\s\S]*?\}[\s\S]*?\}/, '');
detailHtml = detailHtml.replace(/async function submitDrawerSchedule\(\) \{[\s\S]*?\}\n        \}/, '');
fs.writeFileSync('candidate-detail.html', detailHtml);

console.log('Fixed drawer scheduling logic');