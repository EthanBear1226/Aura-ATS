import datetime
import json

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
