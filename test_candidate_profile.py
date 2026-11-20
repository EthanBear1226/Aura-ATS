from unittest.mock import patch

import models
from resume_profile import extract_resume_profile
from test_security_boundaries import _make_candidate, _valid_pdf_bytes


def test_profile_extraction_is_explicit_and_does_not_guess():
    profile = extract_resume_profile(
        "姓名：张雪 | 学历：本科\n电话 139-0000-1234 邮箱 actual@test.local\n博士项目，硕士优先"
    )
    assert profile == {
        "name": "张雪", "exp": "本科", "phone": "13900001234", "email": "actual@test.local",
    }
    missing = extract_resume_profile("博士项目 硕士优先\nLegacy number: 310104199508122345")
    assert missing == {"name": "", "exp": "", "phone": "", "email": ""}
    header = extract_resume_profile("张雪 Zhang Xue\nheader@test.local\n教育背景\n计算机 硕⼠研究⽣ (在读)\n工作经历\n博士项目")
    assert header["name"] == "张雪"
    assert header["exp"] == "硕士（在读）"


def test_profile_patch_persists_and_preserves_resume(client, db_session, admin_headers):
    candidate = _make_candidate(db_session, pdf_path="/uploads/original.pdf")
    original_raw = candidate.raw_text
    response = client.patch(f"/api/candidates/{candidate.id}", headers=admin_headers, json={
        "name": "  Correct Name  ", "phone": " +86 139-0000-1234 ",
        "email": " new@test.local ", "exp": " 硕士 ",
    })
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Correct Name"
    assert response.json()["phone"] == "+86 139-0000-1234"
    assert response.json()["raw_text"] == original_raw
    assert response.json()["pdf_path"] == "/uploads/original.pdf"
    refreshed = client.get(f"/api/candidates/{candidate.id}", headers=admin_headers).json()
    assert refreshed["email"] == "new@test.local"
    assert refreshed["exp"] == "硕士"
    assert len(refreshed["logs"]) == 1
    assert refreshed["logs"][0]["operator"] == "Admin"
    assert refreshed["updated_at"] != refreshed["created_at"]
    no_op = client.patch(f"/api/candidates/{candidate.id}", headers=admin_headers, json={"name": "Correct Name"})
    assert len(no_op.json()["logs"]) == 1
    cleared = client.patch(f"/api/candidates/{candidate.id}", headers=admin_headers, json={"phone": "", "email": "", "exp": ""})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["phone"] == ""
    assert cleared.json()["email"] == ""


def test_profile_patch_validates_before_mutation(client, db_session, admin_headers):
    candidate = _make_candidate(db_session)
    for payload in [
        {"name": " "}, {"name": "a" * 81}, {"email": "invalid"}, {"phone": "unknown"},
        {"phone": "123"}, {"exp": "a" * 81}, {"name": "bad\nname"},
        {"email": "a@test.local", "phone": "not a phone", "stage": "面试"},
    ]:
        response = client.patch(f"/api/candidates/{candidate.id}", headers=admin_headers, json=payload)
        assert response.status_code == 422, response.text
    db_session.expire_all()
    assert db_session.get(models.Candidate, candidate.id).stage == "初筛"
    assert db_session.query(models.CandidateLog).count() == 0


def test_profile_patch_requires_recruiting_role(client, db_session, make_auth_headers):
    candidate = _make_candidate(db_session)
    headers = make_auth_headers("profile-interviewer@test.local", role="Interviewer", name="Reviewer")
    assert client.patch(f"/api/candidates/{candidate.id}", headers=headers, json={"name": "Other"}).status_code == 403
    import datetime
    db_session.add(models.Interview(
        candidate_id=candidate.id, interviewer_name="Reviewer", job_title=candidate.job,
        start_time=datetime.datetime.utcnow(), end_time=datetime.datetime.utcnow(), location="Online",
    ))
    db_session.commit()
    assert client.patch(f"/api/candidates/{candidate.id}", headers=headers, json={"name": "Other", "stage": "面试"}).status_code == 403
    # A no-op must not leak the unmasked contacts through the PATCH response.
    no_op = client.patch(f"/api/candidates/{candidate.id}", headers=headers, json={})
    assert no_op.status_code == 200, no_op.text
    assert "*" in no_op.json()["phone"]
    for role in ("Recruiter", "Admin"):
        recruiter = make_auth_headers(f"profile-{role}@test.local", role=role)
        response = client.patch(f"/api/candidates/{candidate.id}", headers=recruiter, json={"name": role})
        assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.get(models.Candidate, candidate.id).stage == "初筛"


def test_resume_without_ai_extracts_real_basics(client, db_session, admin_headers):
    import main
    with patch.object(main, "api_key", ""), patch.object(main.genai, "GenerativeModel") as ai:
        response = client.post("/api/parse-resume", headers=admin_headers,
            files={"file": ("untrusted-filename.pdf", _valid_pdf_bytes("Name: Real Person | Phone: 13900001234 Email: real@test.local"), "application/pdf")})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "Real Person"
        assert body["phone"] == "13900001234"
        assert body["email"] == "real@test.local"
        assert body["skills"] == []
        assert body["exp"] == "未知"
        assert body["job"] == "未指定职位"
        ai.assert_not_called()


def test_resume_ai_failure_never_creates_demo_identity(client, db_session, admin_headers):
    import main
    for index, error in enumerate(("429 quota exceeded", "service unavailable")):
        with patch.object(main, "api_key", "synthetic-key"), patch.object(main.genai, "GenerativeModel", side_effect=RuntimeError(error)):
            response = client.post("/api/parse-resume", headers=admin_headers,
                files={"file": (f"wrong-person-{index}.pdf", _valid_pdf_bytes(f"Actual resume {index}"), "application/pdf")})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "姓名待补充"
        assert body["email"] == "暂无"
        assert body["exp"] == "未知"
        assert body["skills"] == []
        assert "demo@example.com" not in response.text
        assert "Actual resume" in body["raw_text"]


def test_resume_extraction_preserves_source_characters(client, db_session, admin_headers):
    import main
    source = "姓名：张雪 | 学历：本科\n聘用专员招聘，足球项目\n\n邮箱 actual@test.local"

    class Page:
        def extract_text(self):
            return source

    class Pdf:
        pages = [Page()]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    with patch.object(main, "api_key", ""), patch.object(main.pdfplumber, "open", return_value=Pdf()):
        response = client.post("/api/parse-resume", headers=admin_headers,
            files={"file": ("resume.pdf", _valid_pdf_bytes(), "application/pdf")})
    assert response.status_code == 200, response.text
    assert response.json()["raw_text"] == source + "\n"
    assert response.json()["name"] == "张雪"
    assert response.json()["exp"] == "本科"
