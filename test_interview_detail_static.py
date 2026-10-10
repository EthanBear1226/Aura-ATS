from pathlib import Path

import pytest


ROOT = Path(__file__).parent

pytestmark = pytest.mark.no_db


def read_page(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_interviewer_detail_page_is_a_real_scoped_workflow():
    detail_html = read_page("interview-detail.html")
    workbench_html = read_page("interviewer-workbench.html")
    main_py = read_page("main.py")

    for required in [
        "/api/interviews/${encodeURIComponent(id)}",
        "/api/interviews/${encodeURIComponent(id)}/feedback-revisions",
        "candidate-summary",
        "resumeLink",
        "revisionList",
        "feedbackButton",
        "user.role !== 'Interviewer'",
    ]:
        assert required in detail_html

    assert "interview-detail.html?id=${encodeURIComponent(interview.id)}" in workbench_html
    assert '@app.get("/interview-detail.html")' in main_py
    assert "phone" not in detail_html
    assert "email" not in detail_html
