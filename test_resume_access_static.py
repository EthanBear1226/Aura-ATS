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
