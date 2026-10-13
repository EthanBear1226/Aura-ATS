import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import models


def test_interview_detail_and_feedback_history_are_scoped_to_assigned_interviewer(
    client,
    db_session,
    make_auth_headers,
):
    candidate = models.Candidate(
        name="Detail Candidate",
        job="Backend Engineer",
        stage="Interview",
        exp="5 years",
        skills=["Python", "SQL"],
        pdf_path="/uploads/detail-candidate.pdf",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    interview = models.Interview(
        candidate_id=candidate.id,
        interviewer_name="Detail Interviewer",
        job_title="Backend Engineer",
        start_time=datetime.datetime.utcnow(),
        end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        location="Online",
        feedback_result="满意",
        feedback_text="Strong technical depth",
        professional_score=4,
        communication_score=4,
        business_score=3,
        collaboration_score=4,
        potential_score=4,
        feedback_revision_count=0,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    db_session.add(
        models.InterviewFeedbackRevision(
            interview_id=interview.id,
            revision_number=0,
            action="submitted",
            actor_name="Detail Interviewer",
            actor_role="Interviewer",
            feedback_snapshot=json.dumps({
                "feedback_result": "满意",
                "feedback_text": "Strong technical depth",
                "professional_score": 4,
                "communication_score": 4,
                "business_score": 3,
                "collaboration_score": 4,
                "potential_score": 4,
                "interviewer_notes": "Keep in loop",
            }),
        )
    )
    db_session.commit()

    assigned = make_auth_headers(
        "detail-interviewer@test.local",
        role="Interviewer",
        name="Detail Interviewer",
    )
    detail = client.get(f"/api/interviews/{interview.id}", headers=assigned)
    assert detail.status_code == 200, detail.text
    assert detail.json()["candidate"]["name"] == "Detail Candidate"
    assert detail.json()["candidate"]["pdf_path"] == "/uploads/detail-candidate.pdf"
    assert "phone" not in detail.json()["candidate"]
    assert "email" not in detail.json()["candidate"]

    history = client.get(
        f"/api/interviews/{interview.id}/feedback-revisions",
        headers=assigned,
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]["feedback_text"] == "Strong technical depth"
    assert history.json()[0]["actor_name"] == "Detail Interviewer"

    stranger = make_auth_headers(
        "other-detail-interviewer@test.local",
        role="Interviewer",
        name="Other Detail Interviewer",
    )
    forbidden_detail = client.get(
        f"/api/interviews/{interview.id}",
        headers=stranger,
    )
    forbidden_history = client.get(
        f"/api/interviews/{interview.id}/feedback-revisions",
        headers=stranger,
    )
    assert forbidden_detail.status_code == 403
    assert forbidden_history.status_code == 403


def test_interview_detail_page_route_is_available(client):
    response = client.get("/interview-detail.html")
    assert response.status_code == 200
    assert 'id="detailContent"' in response.text


def test_terminal_candidate_and_cancelled_interview_cannot_change_feedback(client, db_session, make_auth_headers):
    candidate = models.Candidate(name="Closed Candidate", job="Engineer", stage="已淘汰", exp="5 years")
    db_session.add(candidate)
    db_session.flush()
    interview = models.Interview(candidate_id=candidate.id, interviewer_name="Owner", job_title="Engineer",
                                 start_time=datetime.datetime.utcnow(), end_time=datetime.datetime.utcnow(),
                                 location="Online", status="已完成", feedback_result="不满意", feedback_text="Original")
    db_session.add(interview)
    db_session.commit()
    headers = make_auth_headers("closed-owner@test.local", role="Interviewer", name="Owner")
    payload = dict(feedback_result="满意", feedback_text="Attempt to reopen", professional_score=4,
                   communication_score=4, business_score=4, collaboration_score=4, potential_score=4)
    for stage, status in [("已淘汰", "已完成"), ("已归档", "已完成"), ("面试中", "已取消")]:
        candidate.stage = stage
        interview.status = status
        db_session.commit()
        response = client.patch(f"/api/interviews/{interview.id}/feedback", headers=headers, json=payload)
        assert response.status_code == 400, response.text
        db_session.refresh(interview)
        assert interview.feedback_text == "Original"
        assert db_session.query(models.InterviewFeedbackRevision).count() == 0


def test_feedback_history_updates_and_hr_is_read_only(client, db_session, make_auth_headers):
    candidate = models.Candidate(name="Active Candidate", job="Engineer", stage="面试中", exp="5 years")
    db_session.add(candidate)
    db_session.flush()
    interview = models.Interview(candidate_id=candidate.id, interviewer_name="Owner", job_title="Engineer",
                                 start_time=datetime.datetime.utcnow(), end_time=datetime.datetime.utcnow(), location="Online")
    db_session.add(interview)
    db_session.commit()
    headers = make_auth_headers("active-owner@test.local", role="Interviewer", name="Owner")
    hr = make_auth_headers("read-only-hr@test.local", role="Recruiter", name="HR")
    payload = dict(feedback_result="满意", feedback_text="Initial", professional_score=4,
                   communication_score=4, business_score=4, collaboration_score=4, potential_score=4,
                   interviewer_notes="Notes")
    for version in range(3):
        payload["feedback_text"] = f"Version {version}"
        response = client.patch(f"/api/interviews/{interview.id}/feedback", headers=headers, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["feedback_revision_count"] == version
    assert client.patch(f"/api/interviews/{interview.id}/feedback", headers=headers, json=payload).status_code == 400
    assert client.patch(f"/api/interviews/{interview.id}/feedback", headers=hr, json=payload).status_code == 403
    history = client.get(f"/api/interviews/{interview.id}/feedback-revisions", headers=hr)
    assert history.status_code == 200
    assert [item["feedback_text"] for item in history.json()] == ["Version 0", "Version 1", "Version 2"]
    assert all(item["interviewer_notes"] == "Notes" for item in history.json())


def _resume_interview(db_session):
    candidate = models.Candidate(name="Resume Candidate", job="Engineer", stage="面试中", exp="5 years", pdf_path="/uploads/resume.pdf")
    db_session.add(candidate)
    db_session.flush()
    interview = models.Interview(candidate_id=candidate.id, interviewer_name="Resume Owner", job_title="Engineer",
                                 start_time=datetime.datetime.utcnow(), end_time=datetime.datetime.utcnow(), location="Online")
    db_session.add(interview)
    db_session.commit()
    return interview, candidate


def test_resume_file_requires_login_and_interview_assignment(client, db_session, make_auth_headers):
    interview, candidate = _resume_interview(db_session)
    owner = make_auth_headers("resume-owner@test.local", role="Interviewer", name="Resume Owner")
    other = make_auth_headers("resume-other@test.local", role="Interviewer", name="Other Owner")
    hr = make_auth_headers("resume-hr@test.local", role="Recruiter", name="HR")
    url = f"/api/interviews/{interview.id}/resume"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=other).status_code == 403
    with TemporaryDirectory() as temp, patch("main.UPLOAD_DIR", temp):
        content = b"%PDF-1.4\nResume fixture"
        Path(temp, "resume.pdf").write_bytes(content)
        for headers in (owner, hr):
            response = client.get(url, headers=headers)
            assert response.status_code == 200, response.text
            assert response.content == content
            assert response.headers["content-type"] == "application/pdf"
            assert response.headers["cache-control"] == "private, no-store"
            assert response.headers["x-content-type-options"] == "nosniff"


def test_resume_file_rejects_missing_and_invalid_pdf(client, db_session, make_auth_headers):
    interview, candidate = _resume_interview(db_session)
    headers = make_auth_headers("missing-resume@test.local", role="Interviewer", name="Resume Owner")
    url = f"/api/interviews/{interview.id}/resume"
    with TemporaryDirectory() as temp, patch("main.UPLOAD_DIR", temp):
        assert client.get(url, headers=headers).status_code == 404
        Path(temp, "resume.pdf").write_bytes(b"not a PDF")
        assert client.get(url, headers=headers).status_code == 415
        candidate.pdf_path = "/uploads/resume.txt"
        db_session.commit()
        Path(temp, "resume.txt").write_bytes(b"%PDF-1.4\n")
        assert client.get(url, headers=headers).status_code == 415
        candidate.pdf_path = None
        db_session.commit()
        assert client.get(url, headers=headers).status_code == 404


def test_resume_file_blocks_paths_outside_upload_directory(client, db_session, make_auth_headers):
    interview, candidate = _resume_interview(db_session)
    headers = make_auth_headers("path-resume@test.local", role="Interviewer", name="Resume Owner")
    with TemporaryDirectory() as temp:
        root = Path(temp, "uploads")
        root.mkdir()
        Path(temp, "outside.pdf").write_bytes(b"%PDF-1.4\nPrivate file")
        with patch("main.UPLOAD_DIR", str(root)):
            for value in ("/uploads/../outside.pdf", "/uploads/..\\outside.pdf", "https://example.com/resume.pdf"):
                candidate.pdf_path = value
                db_session.commit()
                response = client.get(f"/api/interviews/{interview.id}/resume", headers=headers)
                assert response.status_code == 404, response.text
