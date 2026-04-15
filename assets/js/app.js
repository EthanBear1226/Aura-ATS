function checkAuth() {
    const user = localStorage.getItem('aura_user');
    const path = window.location.pathname;
    if (!user && !path.includes('login.html') && !path.includes('register.html')) {
        window.location.href = 'login.html';
    }
}

function renderSidebar(activeId) {
    const container = document.getElementById('sidebar-container');
    if (!container) return;

    const navItems = [
        { id: 'index', name: '工作台', icon: '<svg viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>', link: 'index.html' },
        { id: 'candidates', name: '候选人管理', icon: '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>', link: 'candidates.html' },
        { id: 'jobs', name: '职位管理', icon: '<svg viewBox="0 0 24 24"><path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/></svg>', link: 'jobs.html' },
        { id: 'interviews', name: '面试日程', icon: '<svg viewBox="0 0 24 24"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1 0.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/></svg>', link: 'interviews.html' }
    ];

    let html = `
        <div class="sidebar-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="var(--primary-color)"><path d="M12 2L2 22h20L12 2zm0 6l5.5 11h-11L12 8z"/></svg>
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
            <select id="roleSwitcher" onchange="switchRole(this.value)" style="padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border-color); background: #f9f9f9; outline: none; cursor: pointer; font-size: 13px;">
                <option value="SuperAdmin" ${user.role === 'SuperAdmin' ? 'selected' : ''}>👁️ 超级管理员 (全量)</option>
                <option value="Recruiter" ${user.role === 'Recruiter' ? 'selected' : ''}>👁️ 招聘官 (业务链)</option>
                <option value="HiringManager" ${user.role === 'HiringManager' ? 'selected' : ''}>👁️ 用人经理 (部门)</option>
                <option value="Interviewer" ${user.role === 'Interviewer' ? 'selected' : ''}>👁️ 面试官 (任务)</option>
                <option value="Assistant" ${user.role === 'Assistant' ? 'selected' : ''}>👁️ 协同助理 (基础)</option>
            </select>
            <button class="btn btn-primary" onclick="alert('快捷添加功能演示')">+ 快捷添加</button>
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
    if(confirm('确定要退出登录吗？')) {
        localStorage.removeItem('aura_user');
        window.location.href = 'login.html';
    }
}

// Run auth check automatically on script load
checkAuth();