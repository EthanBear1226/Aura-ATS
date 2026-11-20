function candidateProfileValue(value) {
    const text = String(value ?? '').trim();
    return ['', '--', '暂无', '未知', 'None', 'null'].includes(text) ? '' : text;
}

function extractCandidateMetaFromText(cand) {
    const resume = String(cand.raw_text || '').normalize('NFKC');
    const labelledName = resume.match(/(?:^|[\n|｜【])\s*(?:姓名|Name)\s*[:：]\s*([\u4e00-\u9fff·]{2,20}|[A-Za-z][A-Za-z .'-]{1,79})[ \t]*(?=$|[\n|｜】])/im);
    let name = candidateProfileValue(cand.name);
    if (/\.pdf$/i.test(name) || ['AI 解析异常', '姓名待补充'].includes(name)) name = '';
    if (!name && labelledName) name = labelledName[1].trim();
    const bilingualHeader = resume.trimStart().split('\n')[0].trim().match(/^([\u4e00-\u9fff·]{2,4})[ \t]+[A-Za-z][A-Za-z .'-]+$/);
    if (!name && bilingualHeader && /@|1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}/.test(resume.slice(0, 500))) {
        name = bilingualHeader[1];
    }

    let phone = candidateProfileValue(cand.phone);
    let email = candidateProfileValue(cand.email);
    if (canExtractResumeContacts()) {
        const phoneMatch = resume.match(/(?:^|[^\d])(1[3-9]\d[-\s]?\d{4}[-\s]?\d{4})(?!\d)/);
        const emailMatch = resume.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
        // An explicit empty string is a saved clear; only legacy missing values recover.
        if (!phone && cand.phone !== '' && phoneMatch) phone = phoneMatch[1];
        if (!email && cand.email !== '' && emailMatch) email = emailMatch[0];
    }
    const genderMatch = resume.match(/(?:^|[\n|｜])\s*性别\s*[:：]\s*(男|女)(?=$|[\s|｜])/m);
    const gender = ['男', '女'].includes(cand.gender) ? cand.gender : (genderMatch?.[1] || '');
    const educationMatch = resume.match(/(?:最高学历|学历|学位)\s*[:：]\s*(博士|硕士|本科|学士|大专|专科|高中|中专)(?!优先|项目|导师)/);
    const educationSection = resume.match(/(?:教育经历|教育背景|EDUCATION)([\s\S]*?)(?=实习经历|工作经历|项目经历|INTERNSHIP|WORK EXPERIENCE|$)/i)?.[1] || '';
    let extractedEducation = educationMatch?.[1] || '';
    if (!extractedEducation) {
        for (const degree of ['博士', '硕士', '本科', '学士', '大专', '专科', '高中', '中专']) {
            if (new RegExp(`${degree}(?!优先|项目|导师)`).test(educationSection)) {
                const enrolled = new RegExp(`${degree}(?:研究生)?\\s*[（(]?\\s*在读`).test(educationSection);
                extractedEducation = degree + (enrolled ? '（在读）' : '');
                break;
            }
        }
    }
    const edu = cand.exp === '' ? '' : (candidateProfileValue(cand.exp) || extractedEducation);
    return { name, phone, email, gender, edu };
}

function candidateSkills(cand) {
    const skills = Array.isArray(cand.skills) ? cand.skills : String(cand.skills || '').split(/[,，]/);
    return skills.map(s => String(s).trim()).filter(s =>
        s && !['模拟', '演示模式', '解析失败', '所有模型额度已满'].includes(s));
}

function escapeProfileHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

let profileSaving = false;
let profileBaseline = null;
let profileSaveUncertain = false;

function openEditModal() {
    if (!currentCandidate || profileSaving || !canExtractResumeContacts()) return;
    if (profileSaveUncertain) {
        document.getElementById('profile-edit-dialog').showModal();
        return;
    }
    const meta = extractCandidateMetaFromText(currentCandidate);
    profileBaseline = { id: currentCandidate.id, ...meta };
    for (const [field, value] of Object.entries({ name: meta.name, phone: meta.phone, email: meta.email, exp: meta.edu })) {
        document.getElementById(`edit-profile-${field}`).value = value;
    }
    document.getElementById('profile-save').disabled = false;
    document.getElementById('profile-edit-error').textContent = '';
    document.getElementById('profile-edit-dialog').showModal();
}

function closeProfileEditor() {
    if (!profileSaving) document.getElementById('profile-edit-dialog').close();
}

async function saveCandidateProfile(event) {
    event.preventDefault();
    if (profileSaving || profileSaveUncertain || !profileBaseline || !canExtractResumeContacts()) return;
    const form = document.getElementById('profile-edit-form');
    const error = document.getElementById('profile-edit-error');
    const values = {};
    for (const field of ['name', 'phone', 'email', 'exp']) {
        values[field] = document.getElementById(`edit-profile-${field}`).value.trim();
    }
    error.textContent = '';
    if (!values.name) error.textContent = '请填写候选人姓名';
    else if (values.phone && (!/^\+?[0-9() -]+$/.test(values.phone) ||
        values.phone.replace(/\D/g, '').length < 6 || values.phone.replace(/\D/g, '').length > 20)) {
        error.textContent = '请填写有效联系电话';
    } else if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
        error.textContent = '请填写有效邮箱';
    }
    if (error.textContent || !form.reportValidity()) return;
    const patch = {};
    for (const field of ['name', 'phone', 'email', 'exp']) {
        const baseline = field === 'exp' ? profileBaseline.edu : profileBaseline[field];
        // Opening the form never writes; only an actual form change creates a patch.
        if (values[field] !== baseline) {
            patch[field] = values[field];
        }
    }
    if (!Object.keys(patch).length) { closeProfileEditor(); return; }
    profileSaving = true;
    const submit = document.getElementById('profile-save');
    submit.textContent = '保存中...';
    for (const control of form.elements) control.disabled = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    let confirmed = false;
    try {
        const response = await authFetch(`/api/candidates/${encodeURIComponent(profileBaseline.id)}`, {
            method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch), signal: controller.signal,
        });
        if (!response.ok) {
            confirmed = response.status < 500;
            const data = await response.json().catch(() => ({}));
            throw new Error(typeof data.detail === 'string' ? data.detail : '保存失败，请检查输入或权限');
        }
        const saved = await response.json();
        if (String(saved.id) !== String(profileBaseline.id)) throw new Error('保存结果不匹配');
        confirmed = true;
        renderCandidateData(saved);
        document.getElementById('profile-edit-dialog').close();
        showToast('基本信息已保存', 'success');
    } catch (err) {
        profileSaveUncertain = !confirmed;
        error.textContent = confirmed ? err.message : '保存结果待确认，请关闭窗口并刷新档案核对，输入已保留';
    } finally {
        clearTimeout(timer);
        profileSaving = false;
        for (const control of form.elements) control.disabled = false;
        submit.textContent = '保存';
        submit.disabled = profileSaveUncertain;
    }
}
