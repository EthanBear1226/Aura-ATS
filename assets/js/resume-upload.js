(() => {
    const entries = [];
    const fileInput = document.getElementById('resume-file');
    const jobSelect = document.getElementById('modal-job-select');
    const area = document.getElementById('uploadArea');
    const retryButton = document.getElementById('retryFailedUploads');
    const maxBytes = 5 * 1024 * 1024;
    window.resumeUploadBusy = false;

    function setBusy(busy) {
        window.resumeUploadBusy = busy;
        fileInput.disabled = busy;
        jobSelect.disabled = busy;
        retryButton.disabled = busy;
        area.setAttribute('aria-disabled', String(busy));
        area.setAttribute('aria-busy', String(busy));
        document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
            wrapper.classList.remove('open');
            wrapper.style.pointerEvents = busy ? 'none' : '';
            wrapper.style.opacity = busy ? '.6' : '';
        });
    }

    function render() {
        const box = document.getElementById('upload-results');
        box.style.display = entries.length ? 'block' : 'none';
        const labels = {pending:'等待处理', processing:'正在解析', failed:'解析失败', invalid:'未上传', unknown:'结果待确认'};
        box.innerHTML = entries.map(entry => {
            const success = entry.status === 'success';
            const label = success ? `解析成功：${entry.candidate.name || entry.file.name}`
                : `${labels[entry.status]}：${entry.detail || ''}`;
            return `<div class="upload-result ${success ? 'success' : 'failed'}"><div class="upload-result-copy"><strong>${escapeHtml(entry.file.name)}</strong><div>${escapeHtml(label)}</div><div class="upload-job">${escapeHtml(entry.jobTitle)}</div></div>${success ? `<a class="btn" href="candidate-detail.html?id=${encodeURIComponent(entry.candidate.id)}">查看候选人</a>` : ''}</div>`;
        }).join('');
        retryButton.hidden = !entries.some(entry => entry.status === 'failed');
        document.getElementById('view-uploaded-candidates').style.display = entries.some(entry => ['success','unknown'].includes(entry.status)) ? 'inline-flex' : 'none';
        const count = status => entries.filter(entry => entry.status === status).length;
        document.getElementById('progress-text').textContent = window.resumeUploadBusy ? '正在检查或解析简历，请稍候...'
            : `处理完成：成功 ${count('success')} 份，失败 ${count('failed')} 份，未上传 ${count('invalid')} 份，待确认 ${count('unknown')} 份`;
    }

    async function send(group) {
        const formData = new FormData();
        group.forEach(entry => { entry.status = 'processing'; formData.append('files', entry.file); });
        formData.append('job_id', group[0].jobId);
        const user = JSON.parse(localStorage.getItem('aura_user') || '{}');
        formData.append('operator', user.name || '系统');
        render();
        try {
            const response = await fetch('/api/parse-resumes', {method:'POST', headers:authHeaders(), body:formData});
            if (!response.ok) throw new Error('请求未完成');
            const batch = await response.json();
            // Associate by request order, not filename: different PDFs can share a name.
            if (!Array.isArray(batch.results) || batch.results.length !== group.length
                || batch.results.some(item => !item || !['success','failed'].includes(item.status)
                    || (item.status === 'success' && !item.candidate?.id))) throw new Error('响应格式异常');
            batch.results.forEach((result, index) => {
                const entry = group[index];
                entry.status = result.status;
                entry.candidate = result.candidate;
                entry.detail = String(result.detail || '服务端处理失败，可重试');
                if (entry.status === 'success') entry.file = {name: entry.file.name};
            });
        } catch (error) {
            group.forEach(entry => {
                entry.status = 'unknown';
                entry.detail = '连接中断或响应异常，请先在候选人列表确认是否已入库，避免重复上传';
            });
        }
    }

    async function process(files, retry = false) {
        if (window.resumeUploadBusy) return;
        const jobId = jobSelect.value;
        if (!retry && !jobId) { showToast('请先选择投递职位', 'error'); return; }
        if (!retry && !files.length) return;
        setBusy(true);
        document.getElementById('upload-progress').style.display = 'block';
        document.getElementById('progress-bar').style.width = '30%';
        try {
            let pending = retry ? entries.filter(entry => entry.status === 'failed') : [];
            if (!retry) {
                const jobTitle = jobSelect.selectedOptions[0]?.textContent || '';
                for (const file of files) {
                    const entry = {file, jobId, jobTitle, status:'invalid', detail:''};
                    entries.push(entry);
                    if (!file.name.toLowerCase().endsWith('.pdf') || (file.type && file.type !== 'application/pdf')) entry.detail = '仅支持 PDF 文件';
                    else if (!file.size) entry.detail = '文件为空';
                    else if (file.size > maxBytes) entry.detail = '文件超过 5MB';
                    else {
                        try {
                            const bytes = await file.arrayBuffer();
                            if (new TextDecoder().decode(bytes.slice(0,5)) !== '%PDF-') entry.detail = '文件内容不是有效 PDF';
                            else {
                                const digest = await crypto.subtle.digest('SHA-256', bytes);
                                entry.hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2,'0')).join('');
                                const duplicate = entries.some(other => other !== entry && other.jobId === jobId
                                    && other.hash === entry.hash && other.status !== 'invalid');
                                if (duplicate) entry.detail = '重复文件：此职位已选择相同内容，请使用失败重试或先核对列表';
                                else { entry.status = 'pending'; pending.push(entry); }
                            }
                        } catch (error) { entry.detail = '文件无法读取，请重新选择'; }
                    }
                }
            }
            // Retrying retains the job captured for each file, even if the picker changed.
            for (const groupJobId of new Set(pending.map(entry => entry.jobId))) {
                await send(pending.filter(entry => entry.jobId === groupJobId));
            }
        } finally {
            setBusy(false);
            fileInput.value = '';
            document.getElementById('progress-bar').style.width = '100%';
            render();
        }
    }

    fileInput.addEventListener('change', () => process(Array.from(fileInput.files || [])));
    retryButton.addEventListener('click', () => process([], true));
    area.addEventListener('keydown', event => {
        if (['Enter',' '].includes(event.key)) { event.preventDefault(); handleUploadAreaClick(); }
    });
    area.addEventListener('dragover', event => { event.preventDefault(); });
    area.addEventListener('drop', event => {
        event.preventDefault();
        if (!window.resumeUploadBusy) process(Array.from(event.dataTransfer?.files || []));
    });
    window.addEventListener('beforeunload', event => {
        if (window.resumeUploadBusy) { event.preventDefault(); event.returnValue = ''; }
    });
})();
