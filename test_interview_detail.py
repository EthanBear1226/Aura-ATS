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
