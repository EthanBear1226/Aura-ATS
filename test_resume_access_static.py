from pathlib import Path

import pytest


ROOT = Path(__file__).parent
pytestmark = pytest.mark.no_db


def test_resume_files_are_read_through_authorized_api_only():
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    detail_html = (ROOT / "candidate-detail.html").read_text(encoding="utf-8")
    interview_html = (ROOT / "interview-detail.html").read_text(encoding="utf-8")

    assert 'app.mount("/uploads"' not in main_py
    assert '@app.get("/api/candidates/{candidate_id}/resume")' in main_py
    assert 'authFetch(`/api/candidates/${candidate.id}/resume`)' in detail_html
    assert 'fetch(`/api/interviews/${encodeURIComponent(interview.id)}/resume`' in interview_html
    assert "window.open(rawUrl, '_blank')" not in detail_html


def test_candidate_resume_preview_uses_flex_height_and_native_fit_width():
    html = (ROOT / "candidate-detail.html").read_text(encoding="utf-8")

    assert "#tab-pane-0.active {\n            display: flex;" in html
    assert "height: calc(100% - 40px)" not in html
    assert "availableHeight - 40" not in html
    assert "? '#toolbar=0&navpanes=0&view=FitH'" in html
    assert "setTimeout(() => applyPdfZoom(100)" not in html
    assert 'title="候选人原始简历"' in html
    assert 'src="assets/vendor/lucide-0.468.0/lucide.min.js"' in html
    assert "if (window.lucide) lucide.createIcons();" in html
    for name in ("缩小简历", "放大简历", "适应宽度", "切换全屏", "下载简历文件"):
        assert f'aria-label="{name}"' in html


def test_candidate_contacts_are_direct_and_national_id_is_not_collected():
    html = (ROOT / "candidate-detail.html").read_text(encoding="utf-8")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    seeds = (ROOT / "seed_data.py").read_text(encoding="utf-8")

    assert "eye-btn-" not in html
    assert "toggleSensitiveField" not in html
    assert "sensitiveVisible" not in html
    assert "meta-idcard" not in html
    assert "id_card" not in html
    assert "身份证" not in html
    assert "id_card" not in seeds
    assert "身份证" not in seeds
    assert "ADD COLUMN id_card" not in main_py
    assert "不要提取、输出或在摘要、分析中复述身份证号码" in main_py
    assert "meta.phone || '--'" in html
    assert "meta.email || '--'" in html
    assert "?reveal_sensitive=true" in html
    assert "renderCandidateData(currentCandidate || initialFallback)" not in html
    assert "prepareStructuredFallbackData(" not in html


def test_candidate_sidebar_uses_plain_actions_and_separate_confirmation_modals():
    html = (ROOT / "candidate-detail.html").read_text(encoding="utf-8")
    sidebar = html.split('class="right-control-sidebar"', 1)[1].split("<!-- JS 业务逻辑 -->", 1)[0]
    actions = html.split("function renderStageActionControls(candidate)", 1)[1].split("function handleStepNodeClick", 1)[0]
    for symbol in ("💬", "👥", "⚠", "🎉", "↻", "↩", "➔", "✕"):
        assert symbol not in sidebar
        assert symbol not in actions
    assert "candidate-action-shortcuts" in sidebar
    assert "candidate-action-danger" in actions
    assert "驳回淘汰" not in actions
    assert "background: #fff1f0;" in html.split(".candidate-action-secondary .candidate-action-danger {", 1)[1].split("}", 1)[0]
    assert "advanceReasonInput" not in html
    assert "advanceToStage" not in html
    assert "document.getElementById('advanceNoteInput').value" in html
    assert '</div>\n        </div>\n    </div>\n    <!-- 推进流程 Modal 弹窗 -->' in html
