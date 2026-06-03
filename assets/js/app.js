// --- Global Fetch Interceptor for JWT Authentication ---
const originalFetch = window.fetch;
window.fetch = async function (url, options = {}) {
    options.headers = options.headers || {};
    const token = localStorage.getItem('aura_token');
    
    // 注入 JWT 令牌
    if (token && url.startsWith('/api/') && !url.includes('/api/auth/')) {
        if (options.headers instanceof Headers) {
            options.headers.set('Authorization', `Bearer ${token}`);
        } else {
            options.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    try {
        const response = await originalFetch(url, options);
        // 若后端返回 401 凭证失效，则自动退登
        if (response.status === 401 && url.startsWith('/api/') && !url.includes('/api/auth/')) {
            localStorage.removeItem('aura_token');
            localStorage.removeItem('aura_user');
            const path = window.location.pathname;
            if (!path.includes('login.html') && !path.includes('register.html')) {
                window.location.href = 'login.html';
            }
        }
        return response;
    } catch (error) {
        console.error("Fetch interceptor error:", error);
        throw error;
    }
};

function checkAuth() {
    const token = localStorage.getItem('aura_token');
    const user = localStorage.getItem('aura_user');
    const path = window.location.pathname;
    if ((!token || !user) && !path.includes('login.html') && !path.includes('register.html')) {
        window.location.href = 'login.html';
    }
}

function renderSidebar(activeId) {
    const container = document.getElementById('sidebar-container');
    if (!container) return;

    const navItems = [
        { id: 'index', name: '工作台', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>', link: 'index.html?v=1' },
        { id: 'candidates', name: '候选人管理', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>', link: 'candidates.html?v=1' },
        { id: 'interviews', name: '面试日程', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1 0.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>', link: 'interviews.html?v=1' },
        { id: 'jobs', name: '职位管理', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/></svg>', link: 'jobs.html?v=1' },
        { id: 'talent-pool', name: '人才库', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H8V4h12v12z"/></svg>', link: 'talent-pool.html?v=1' }
    ];

    const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
    const role = user.role || 'HR';
    
    if (role === 'SuperAdmin' || role === 'Admin') {
        navItems.push({ id: 'settings', name: '系统设置', icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.06-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.73,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.06,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.49-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>', link: 'settings.html?v=1' });
    }

    let html = `
        <div class="sidebar-logo">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="var(--primary-color)"><path d="M12 2L2 22h20L12 2zm0 6l5.5 11h-11L12 8z"/></svg>
            <span class="nav-text">Aura</span>
        </div>
        <nav class="nav-menu">
    `;

    navItems.forEach(item => {
        const activeClass = item.id === activeId ? 'active' : '';
        html += `<a href="${item.link}" class="nav-item ${activeClass}">
                    ${item.icon}
                    <span class="nav-text">${item.name}</span>
                 </a>`;
    });

    html += `</nav>`;
    container.innerHTML = html;
}

function renderHeader() {
    const container = document.getElementById('header-container');
    if (!container) return;

    let user = JSON.parse(localStorage.getItem('aura_user') || '{}');
    if (!user.role) {
        user.role = 'SuperAdmin'; // Default role
        user.name = '超级管理员';
        localStorage.setItem('aura_user', JSON.stringify(user));
    }
    
    container.innerHTML = `
        <div class="header-search">
            <input type="text" placeholder="搜索候选人、职位...">
        </div>
        <div class="header-actions">
            <div class="dropdown-container" style="position: relative; display: inline-block;">
                <button class="btn btn-primary" style="padding: 8px 16px;">+ 添加</button>
                <div class="dropdown-menu" style="position: absolute; top: 100%; right: 0; padding-top: 8px; width: 180px; display: none; flex-direction: column; z-index: 1000;">
                    <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); box-shadow: var(--shadow-md); padding: 8px; display: flex; flex-direction: column; gap: 4px;">
                        <a href="add-candidate.html" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; text-decoration: none; color: var(--text-primary); font-size: 14px; font-weight: 500; border-radius: var(--radius-sm); transition: var(--transition);" onmouseover="this.style.background='var(--bg-color)'" onmouseout="this.style.background='transparent'">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--text-secondary);"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                            添加候选人
                        </a>
                        <a href="add-job.html" style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; text-decoration: none; color: var(--text-primary); font-size: 14px; font-weight: 500; border-radius: var(--radius-sm); transition: var(--transition);" onmouseover="this.style.background='var(--bg-color)'" onmouseout="this.style.background='transparent'">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--text-secondary);"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
                            发布新职位
                        </a>
                    </div>
                </div>
            </div>
            <div style="cursor:pointer; display:flex; align-items:center; gap:8px;" onclick="logout()">
                <div style="width:32px; height:32px; border-radius:16px; background:var(--primary-color); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold;">
                    ${user.name ? user.name.charAt(0) : 'U'}
                </div>
                <span style="font-size:14px; font-weight:500;">${user.name || 'User'}</span>
            </div>
        </div>
    `;
}

function switchRole(role) {
    let name = '超级管理员';
    if (role === 'Recruiter') name = '招聘官 HRBP';
    if (role === 'HiringManager') name = '技术总监 (用人经理)';
    if (role === 'Interviewer') name = '前端架构师 (面试官)';
    if (role === 'Assistant') name = '招聘实习生 (助理)';
    
    localStorage.setItem('aura_user', JSON.stringify({ name: name, email: 'user@example.com', role: role }));
    window.location.reload();
}

function logout() {
    showConfirm('确定要退出登录吗？', () => {
        localStorage.removeItem('aura_user');
        window.location.href = 'login.html';
    });
}

// Global Notification (Toast)
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = '';
    if (type === 'success') {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    } else if (type === 'error') {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }
    
    toast.innerHTML = `<span style="display:flex;align-items:center;gap:8px;">${icon} ${message}</span>`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('active'));

    setTimeout(() => {
        toast.classList.remove('active');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Global Custom Confirm Modal
function showConfirm(message, onConfirm, onCancel = null) {
    const overlay = document.createElement('div');
    overlay.className = 'confirm-modal-overlay';
    
    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    
    modal.innerHTML = `
        <h3 style="margin-top:0; font-size:18px; color:var(--text-primary);">确认操作</h3>
        <p style="margin:16px 0 32px; font-size:14px; color:var(--text-secondary); line-height:1.5;">${message}</p>
        <div style="display:flex; justify-content:center; gap:12px;">
            <button class="btn" id="confirmCancelBtn" style="padding:8px 24px; flex:1;">取消</button>
            <button class="btn btn-primary" id="confirmOkBtn" style="padding:8px 24px; flex:1; background:#FF3B30; border-color:#FF3B30;">确认</button>
        </div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    requestAnimationFrame(() => {
        overlay.classList.add('active');
        modal.classList.add('active');
    });
    
    const close = () => {
        modal.classList.remove('active');
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 200);
    };

    document.getElementById('confirmCancelBtn').onclick = () => {
        close();
        if (onCancel) onCancel();
    };
    
    document.getElementById('confirmOkBtn').onclick = () => {
        close();
        if (onConfirm) onConfirm();
    };
}

// Global Drawer Component
function renderScheduleDrawer() {
    if (document.getElementById('globalScheduleDrawerOverlay')) return;

    const drawerHTML = `
    <div class="drawer-overlay" id="globalScheduleDrawerOverlay" onclick="closeScheduleDrawer(event)"></div>
    <div class="drawer" id="globalScheduleDrawer">
        <div class="drawer-header">
            <h2 class="drawer-title">安排新面试</h2>
            <button class="drawer-close" onclick="closeScheduleDrawer()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
        </div>
        <div class="drawer-body">
            <!-- Left Form Area -->
            <div class="drawer-form">
                <div class="form-group" style="margin-bottom: 24px;">
                    <label style="display:block; margin-bottom:8px; font-size:14px; font-weight:500;">候选人</label>
                    <select id="drawerCandidateSelect" class="form-control" style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm);" onchange="updateDrawerCandidateEmail()">
                        <option value="">请选择候选人...</option>
                        <option value="zhangsan@example.com">张三 - 高级前端工程师</option>
                        <option value="lisi@example.com">李四 - 产品经理</option>
                        <option value="wangwu@example.com">王五 - 数据分析师</option>
                    </select>
                </div>

                <div class="form-group" style="margin-bottom: 24px;">
                    <label style="display:block; margin-bottom:8px; font-size:14px; font-weight:500;">
                        面试邀约邮件
                    </label>
                    <input type="email" id="drawerCandidateEmail" placeholder="候选人邮箱自动填入" style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm); margin-bottom: 12px; background:var(--bg-color);">
                    <textarea placeholder="面试邀请文案..." style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm); height: 120px; resize: none; font-family: inherit; font-size: 13px; line-height: 1.5;">您好！

非常荣幸地通知您，您已通过我们的初步筛选。我们希望邀请您参加线上面试，进一步沟通您的过往经历与我们的业务匹配度。

请确认以下面试时间与会议链接，期待与您的交流！</textarea>
                </div>

                <div style="display: flex; gap: 16px; margin-bottom: 24px;">
                    <div class="form-group" style="flex: 1;">
                        <label style="display:block; margin-bottom:8px; font-size:14px; font-weight:500;">面试日期</label>
                        <input type="date" id="drawerInterviewDate" style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm);" onchange="loadDrawerAvailability()">
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label style="display:block; margin-bottom:8px; font-size:14px; font-weight:500;">
                            面试官
                        </label>
                        <select id="drawerInterviewerSelect" class="form-control" style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm);" onchange="loadDrawerAvailability()">
                            <option value="">请选择面试官...</option>
                            <option value="wang">王大锤 (技术总监)</option>
                            <option value="zhao">赵总 (产品VP)</option>
                        </select>
                    </div>
                </div>

                <div class="form-group" style="margin-bottom: 24px;">
                    <label style="display:block; margin-bottom:8px; font-size:14px; font-weight:500;">
                        预订会议室
                    </label>
                    <select class="form-control" style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-sm);">
                        <option value="">无 (线上会议，自动生成腾讯会议链接)</option>
                        <option value="room1">会议室 A (6人) - 剩余可用</option>
                        <option value="room2">会议室 B (10人) - 剩余可用</option>
                    </select>
                </div>
            </div>

            <!-- Right Sidebar Area -->
            <div class="drawer-sidebar">
                <h3 style="margin-top: 0; font-size: 15px; margin-bottom: 8px; color: var(--text-primary);">面试官日程情况</h3>
                <p style="font-size: 12px; color: var(--text-secondary); margin-top: 0; margin-bottom: 24px;">
                    <span id="drawerAvailabilityStatus">请选择日期与面试官，系统将拉取真实飞书日历。</span>
                </p>

                <div id="drawerAvailabilityBlocks" style="display: flex; flex-direction: column; gap: 12px; flex: 1; overflow-y: auto;">
                    <div style="border: 1px dashed var(--border-color); border-radius: var(--radius-sm); height: 80px; display: flex; align-items: center; justify-content: center; color: #C7C7CC; font-size: 13px; text-align: center; padding: 20px;">
                        暂无数据<br>等待条件选择
                    </div>
                </div>
                
                <div style="margin-top: 24px; font-size: 12px; color: var(--text-secondary); display: flex; gap: 16px; justify-content: center;">
                    <span style="display: flex; align-items: center; gap: 6px;"><span style="width:8px; height:8px; border-radius:4px; background:#34C759;"></span> 空闲</span>
                    <span style="display: flex; align-items: center; gap: 6px;"><span style="width:8px; height:8px; border-radius:4px; background:#FF3B30;"></span> 忙碌</span>
                </div>
            </div>
        </div>
        <div class="drawer-footer">
            <button class="btn" style="padding: 10px 24px;" onclick="closeScheduleDrawer()">取消</button>
            <button class="btn btn-primary" id="drawerSubmitBtn" style="padding: 10px 24px;" onclick="submitDrawerSchedule()">确认安排并发送邀约</button>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', drawerHTML);
}

let currentDrawerCandidateId = null;
let currentDrawerCandidateJob = null;
function openScheduleDrawer(candidateName = '', candidateEmail = '', candidateJob = '', candidateId = null) {
    currentDrawerCandidateId = candidateId;
    currentDrawerCandidateJob = candidateJob;
    const overlay = document.getElementById('globalScheduleDrawerOverlay');
    const drawer = document.getElementById('globalScheduleDrawer');
    if (!overlay || !drawer) return;
    
    const select = document.getElementById('drawerCandidateSelect');
    const emailInput = document.getElementById('drawerCandidateEmail');
    
    if (candidateName || candidateEmail) {
        let optionExists = false;
        for(let i=0; i<select.options.length; i++) {
            if(select.options[i].text.includes(candidateName || candidateEmail)) {
                select.selectedIndex = i;
                optionExists = true;
                break;
            }
        }
        if(!optionExists) {
            const label = candidateName ? `${candidateName} - ${candidateJob || '候选人'}` : `${candidateEmail} (候选人)`;
            const val = candidateEmail || candidateName;
            const newOption = new Option(label, val);
            select.add(newOption);
            select.selectedIndex = select.options.length - 1;
        }
        select.disabled = true; // 锁定选择，防止误触
        emailInput.value = candidateEmail || '';
    } else {
        select.disabled = false; // 允许选择
        select.selectedIndex = 0;
        emailInput.value = '';
    }

    overlay.classList.add('active');
    drawer.classList.add('active');
}

function closeScheduleDrawer(e) {
    if (e && e.target.id !== 'globalScheduleDrawerOverlay') return;
    document.getElementById('globalScheduleDrawerOverlay').classList.remove('active');
    document.getElementById('globalScheduleDrawer').classList.remove('active');
}

function updateDrawerCandidateEmail() {
    const selectElement = document.getElementById('drawerCandidateSelect');
    const emailInput = document.getElementById('drawerCandidateEmail');
    emailInput.value = selectElement.value || '';
}

async function loadDrawerAvailability() {
    const date = document.getElementById('drawerInterviewDate').value;
    const interviewer = document.getElementById('drawerInterviewerSelect').value;
    if (!date || !interviewer) return;
    
    // Update status text
    const statusText = document.getElementById('drawerAvailabilityStatus');
    if (statusText) statusText.innerHTML = `已同步 <b>系统日历</b> 实时数据`;
    
    try {
        const response = await fetch(`/api/calendar/freebusy?interviewer=${interviewer}&date=${date}`);
        if (!response.ok) throw new Error("Failed to fetch slots");
        const slots = await response.json();
        
        const container = document.getElementById('drawerAvailabilityBlocks');
        container.innerHTML = slots.map((slot, index) => {
            const isFree = slot.isFree;
            return `
            <label style="border:1px solid ${isFree ? 'var(--border-color)' : '#eee'}; background:${isFree ? '#fff' : '#fafafa'}; padding:8px; border-radius:4px; text-align:center; cursor:${isFree ? 'pointer' : 'not-allowed'}; opacity:${isFree ? '1' : '0.5'}; display:block; margin-bottom:8px;">
                <input type="radio" name="drawerTimeSlot" value="${slot.time}" ${!isFree ? 'disabled' : ''} style="display:none;">
                <div style="font-size:14px; font-weight:500;">${slot.time}</div>
                <div style="font-size:12px; color:var(--text-secondary);">${isFree ? '空闲' : '忙碌'}</div>
            </label>
            `;
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
        if (container) container.innerHTML = `<div style="text-align:center; color:#FF3B30; font-size:13px; padding:20px;">获取档期失败</div>`;
    }
}

async function submitDrawerSchedule() {
    const date = document.getElementById('drawerInterviewDate').value;
    const interviewer = document.getElementById('drawerInterviewerSelect').value;
    const slotRadio = document.querySelector('input[name="drawerTimeSlot"]:checked');
    
    if (!date || !interviewer || !slotRadio || !currentDrawerCandidateId) {
        if(window.showToast) window.showToast("请完整选择面试日期、面试官和时间段", "error");
        return;
    }
    
    const time = slotRadio.value; // e.g. "10:00 - 11:00"
    const startTimeStr = time.split(' - ')[0]; // extract "10:00" from "10:00 - 11:00" if applicable
    const start_time = `${date}T${startTimeStr || time}:00`;
    
    // Simple mock for end time (1 hour later)
    const [hour, min] = (startTimeStr || time).split(':');
    const end_time = `${date}T${parseInt(hour)+1}:${min}:00`;

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
            if(window.showToast) window.showToast(`安排失败: ${data.detail || '未知错误'}`, "error");
        }
    } catch(e) {
        console.error(e);
        if(window.showToast) window.showToast("安排失败，请检查网络", "error");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}


document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    renderScheduleDrawer();
});

// Run auth check automatically on script load
checkAuth();