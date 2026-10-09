from pathlib import Path

import pytest


ROOT = Path(__file__).parent

pytestmark = pytest.mark.no_db


def read_page(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_candidates_page_no_longer_contains_toast_only_fake_controls():
    html = read_page("candidates.html")
    forbidden_snippets = [
        "showToast('折叠职位侧边栏'",
        "showToast('按分组切换模式'",
        "showToast('排序规则更新'",
        "showToast('视图切换已同步'",
        "按分组查看",
        "排序方式：按进入阶段时间倒序",
    ]

    for snippet in forbidden_snippets:
        assert snippet not in html


def test_schedule_drawer_is_not_globally_mounted_on_unrelated_pages():
    for page_name in ["jobs.html", "settings.html"]:
        html = read_page(page_name)
        assert "安排新面试" not in html
        assert "submitDrawerSchedule" not in html


def test_public_portal_upload_limit_matches_backend_copy():
    html = read_page("portal.html")

    assert "10MB" not in html
    assert "最大 5MB" in html
    assert "MAX_RESUME_UPLOAD_BYTES = 5 * 1024 * 1024" in html
