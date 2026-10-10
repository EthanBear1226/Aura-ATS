import datetime
import json

import models


def _valid_pdf_bytes(text="Aura Candidate Resume"):
    from io import BytesIO

    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 750, text)
    pdf.save()
    return buffer.getvalue()


def _make_candidate(db_session, **overrides):
    data = {
        "name": "Boundary Candidate",
        "email": "candidate.secret@test.local",
        "phone": "13800001234",
        "id_card": "110101199001011234",
        "job": "Backend Engineer",
        "stage": "初筛",
        "exp": "本科",
        "raw_text": "Boundary Candidate resume",
    }
    data.update(overrides)
    candidate = models.Candidate(**data)
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def test_candidate_detail_masks_sensitive_fields_by_default_and_reveals_for_authorized_roles(
    client,
    db_session,
    admin_headers,
):
    candidate = _make_candidate(db_session)

    masked = client.get(f"/api/candidates/{candidate.id}", headers=admin_headers)
    assert masked.status_code == 200, masked.text
    assert masked.json()["phone"] != "13800001234"
    assert "*" in masked.json()["phone"]
    assert masked.json()["email"] != "candidate.secret@test.local"
    assert masked.json()["id_card"] != "110101199001011234"

    revealed = client.get(
        f"/api/candidates/{candidate.id}?reveal_sensitive=true",
        headers=admin_headers,
    )
    assert revealed.status_code == 200, revealed.text
    assert revealed.json()["phone"] == "13800001234"
    assert revealed.json()["email"] == "candidate.secret@test.local"
    assert revealed.json()["id_card"] == "110101199001011234"


def test_interviewer_can_view_only_assigned_candidate_and_cannot_reveal_sensitive_fields(
    client,
    db_session,
    make_auth_headers,
):
    assigned = _make_candidate(db_session, email="assigned@test.local")
    other = _make_candidate(db_session, email="other@test.local")
    db_session.add(
        models.Interview(
            candidate_id=assigned.id,
            interviewer_name="Interviewer User",
            job_title=assigned.job,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            location="Online",
        )
    )
    db_session.commit()

    headers = make_auth_headers(
        "interviewer-boundary@test.local",
        role="Interviewer",
        name="Interviewer User",
    )

    assigned_response = client.get(
        f"/api/candidates/{assigned.id}?reveal_sensitive=true",
        headers=headers,
    )
    assert assigned_response.status_code == 200, assigned_response.text
    assert assigned_response.json()["phone"] != "13800001234"
    assert "*" in assigned_response.json()["phone"]

    other_response = client.get(f"/api/candidates/{other.id}", headers=headers)
    assert other_response.status_code == 403


def test_hiring_manager_without_matching_department_cannot_read_candidate_detail(
    client,
    db_session,
    make_auth_headers,
):
    db_session.add(
        models.Job(
            title="Backend Engineer",
            department="Engineering",
            location="Beijing",
            status="Open",
            hr_name="HR",
        )
    )
    candidate = _make_candidate(db_session)

    no_department_headers = make_auth_headers(
        "manager-without-dept@test.local",
        role="HiringManager",
        name="Manager No Department",
    )
    no_department = client.get(
        f"/api/candidates/{candidate.id}",
        headers=no_department_headers,
    )
    assert no_department.status_code == 403

    db_session.add(
        models.UserInvitation(
            email="manager-other-dept@test.local",
            name="Manager Other Department",
            department="Finance",
            role="HiringManager",
            token="manager-other-dept-token",
            status="accepted",
        )
    )
    db_session.commit()
    other_department_headers = make_auth_headers(
        "manager-other-dept@test.local",
        role="HiringManager",
        name="Manager Other Department",
    )
    other_department = client.get(
        f"/api/candidates/{candidate.id}",
        headers=other_department_headers,
    )
    assert other_department.status_code == 403


def test_offer_approval_detail_and_action_are_bound_to_owner_or_current_approver(
    client,
    db_session,
    make_auth_headers,
):
    candidate = _make_candidate(db_session, stage="Offer")
    instance = models.OfferApprovalInstance(
        candidate_id=candidate.id,
        candidate_name=candidate.name,
        job_title=candidate.job,
        salary="30k*14",
        job_level="P6",
        department="Engineering",
        current_step_index=0,
        status="pending",
        creator_email="creator@test.local",
        steps_data=[
            {
                "label": "HRBP",
                "approver_email": "Approver@Test.Local",
                "status": "pending",
                "comment": "",
                "action_time": "",
            }
        ],
        offer_details={"contract_subject": "Aura Test"},
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)

    stranger_headers = make_auth_headers(
        "stranger@test.local",
        role="Recruiter",
        name="Stranger",
    )
    detail = client.get(f"/api/approvals/{instance.id}", headers=stranger_headers)
    assert detail.status_code == 403

    action = client.post(
        f"/api/approvals/{instance.id}/action",
        headers=stranger_headers,
        json={"action": "approve", "comment": "not mine"},
    )
    assert action.status_code == 403

    approver_headers = make_auth_headers(
        "approver@test.local",
        role="Recruiter",
        name="Approver",
    )
    approve = client.post(
        f"/api/approvals/{instance.id}/action",
        headers=approver_headers,
        json={"action": "approve", "comment": "case-insensitive owner check"},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "approved"


def _feedback_payload(result="满意", text="面试表现符合岗位要求", confirm_rejection=False):
    return {
        "feedback_result": result,
        "feedback_text": text,
        "professional_score": 4,
        "communication_score": 4,
        "business_score": 3,
        "collaboration_score": 4,
        "potential_score": 4,
        "interviewer_notes": "记录候选人项目深度和沟通表现。",
        "confirm_rejection": confirm_rejection,
    }


def test_interview_feedback_requires_assigned_interviewer_and_structured_scores(
    client,
    db_session,
    make_auth_headers,
):
    candidate = _make_candidate(db_session, name="Feedback Candidate")
    db_session.add(
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Assigned Feedback Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            location="Online",
        )
    )
    db_session.commit()
    interview = db_session.query(models.Interview).first()

    stranger_headers = make_auth_headers(
        "feedback-stranger@test.local",
        role="Interviewer",
        name="Other Feedback Interviewer",
    )
    forbidden = client.patch(
        f"/api/interviews/{interview.id}/feedback",
        headers=stranger_headers,
        json=_feedback_payload(),
    )
    assert forbidden.status_code == 403

    assigned_headers = make_auth_headers(
        "assigned-feedback@test.local",
        role="Interviewer",
        name="Assigned Feedback Interviewer",
    )
    invalid_scores = _feedback_payload()
    invalid_scores["professional_score"] = None
    invalid = client.patch(
        f"/api/interviews/{interview.id}/feedback",
        headers=assigned_headers,
        json=invalid_scores,
    )
    assert invalid.status_code == 400

    hr_headers = make_auth_headers(
        "feedback-hr@test.local",
        role="Recruiter",
        name="Feedback HR",
    )
    view = client.get(f"/api/interviews/{interview.id}", headers=hr_headers)
    assert view.status_code == 200, view.text
    hr_cannot_edit = client.patch(
        f"/api/interviews/{interview.id}/feedback",
        headers=hr_headers,
        json=_feedback_payload(),
    )
    assert hr_cannot_edit.status_code == 403


def test_interview_feedback_allows_two_modifications_and_records_rejection(
    client,
    db_session,
    make_auth_headers,
):
    candidate = _make_candidate(db_session, name="Feedback Revision Candidate", stage="面试中")
    db_session.add_all([
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Revision Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            location="Online",
        ),
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Revision Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow() + datetime.timedelta(days=1),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=1),
            location="Online",
        ),
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Revision Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow() + datetime.timedelta(days=2),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(days=2, hours=1),
            location="Online",
        ),
    ])
    db_session.commit()
    interviews = db_session.query(models.Interview).order_by(models.Interview.id.asc()).all()
    headers = make_auth_headers(
        "revision-interviewer@test.local",
        role="Interviewer",
        name="Revision Interviewer",
    )

    first = client.patch(
        f"/api/interviews/{interviews[0].id}/feedback",
        headers=headers,
        json=_feedback_payload(),
    )
    assert first.status_code == 200, first.text
    assert first.json()["feedback_revision_count"] == 0

    second = client.patch(
        f"/api/interviews/{interviews[0].id}/feedback",
        headers=headers,
        json=_feedback_payload(text="第一次修改反馈"),
    )
    assert second.status_code == 200, second.text
    assert second.json()["feedback_revision_count"] == 1

    third = client.patch(
        f"/api/interviews/{interviews[0].id}/feedback",
        headers=headers,
        json=_feedback_payload(text="第二次修改反馈"),
    )
    assert third.status_code == 200, third.text
    assert third.json()["feedback_revision_count"] == 2

    fourth = client.patch(
        f"/api/interviews/{interviews[0].id}/feedback",
        headers=headers,
        json=_feedback_payload(text="超过修改次数"),
    )
    assert fourth.status_code == 400

    rejection_without_confirmation = client.patch(
        f"/api/interviews/{interviews[1].id}/feedback",
        headers=headers,
        json=_feedback_payload(result="不满意"),
    )
    assert rejection_without_confirmation.status_code == 400

    rejected = client.patch(
        f"/api/interviews/{interviews[1].id}/feedback",
        headers=headers,
        json=_feedback_payload(result="不满意", confirm_rejection=True),
    )
    assert rejected.status_code == 200, rejected.text

    db_session.expire_all()
    refreshed_candidate = db_session.query(models.Candidate).get(candidate.id)
    refreshed_interviews = db_session.query(models.Interview).filter(
        models.Interview.candidate_id == candidate.id
    ).all()
    assert refreshed_candidate.stage == "已淘汰"
    assert refreshed_interviews[0].status == "已完成"
    assert refreshed_interviews[1].status == "已完成"
    assert refreshed_interviews[2].status == "已取消"


def test_public_resume_upload_rejects_non_pdf_and_oversized_pdf(client, db_session):
    job = models.Job(
        title="Upload Validation Job",
        department="Engineering",
        location="Beijing",
        status="热招中",
        hr_name="HR",
        description="<p>Open role</p>",
    )
    db_session.add(job)
    db_session.commit()

    non_pdf = client.post(
        "/api/public/submit-resume",
        files={"file": ("resume.txt", b"plain text", "text/plain")},
        data={"job_title": job.title},
    )
    assert non_pdf.status_code == 400

    oversized = client.post(
        "/api/public/submit-resume",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4\n" + b"x" * (5 * 1024 * 1024 + 1),
                "application/pdf",
            )
        },
        data={"job_title": job.title},
    )
    assert oversized.status_code == 413


def test_public_resume_upload_rejects_unknown_and_closed_jobs(client, db_session):
    unknown_job = client.post(
        "/api/public/submit-resume",
        files={"file": ("resume.pdf", b"not parsed", "application/pdf")},
        data={"job_title": "Missing Public Job"},
    )
    assert unknown_job.status_code == 404

    closed_job = models.Job(
        title="Closed Public Job",
        department="Engineering",
        location="Beijing",
        status="已停招",
        hr_name="HR",
        description="<p>Closed role</p>",
    )
    db_session.add(closed_job)
    db_session.commit()

    closed = client.post(
        "/api/public/submit-resume",
        files={"file": ("resume.pdf", b"not parsed", "application/pdf")},
        data={"job_title": closed_job.title},
    )
    assert closed.status_code == 400


def test_public_resume_upload_rejects_duplicate_active_application(client, db_session):
    import main

    job = models.Job(
        title="Open Public Job",
        department="Engineering",
        location="Beijing",
        status="热招中",
        hr_name="HR",
        description="<p>Open role</p>",
    )
    db_session.add(job)
    db_session.commit()

    parsed_resume = {
        "name": "Duplicate Applicant",
        "job": job.title,
        "exp": "Bachelor",
        "phone": "13900000000",
        "email": "duplicate@test.local",
        "skills": ["Python"],
        "ai_summary": "Qualified",
        "ai_analysis": "Qualified",
    }

    class FakeModel:
        def __init__(self, model_name):
            self.model_name = model_name

        def generate_content(self, prompt, generation_config=None):
            class Response:
                text = json.dumps(parsed_resume)

            return Response()

    original_api_key = main.api_key
    original_model = main.genai.GenerativeModel
    main.api_key = "test-api-key"
    main.genai.GenerativeModel = FakeModel
    try:
        first = client.post(
            "/api/public/submit-resume",
            files={"file": ("resume.pdf", _valid_pdf_bytes(), "application/pdf")},
            data={"job_title": job.title},
        )
        assert first.status_code == 200, first.text

        duplicate = client.post(
            "/api/public/submit-resume",
            files={"file": ("resume.pdf", _valid_pdf_bytes(), "application/pdf")},
            data={"job_title": job.title},
        )
        assert duplicate.status_code == 400, duplicate.text
    finally:
        main.api_key = original_api_key
        main.genai.GenerativeModel = original_model


def test_internal_resume_upload_can_bind_by_job_id(client, db_session, admin_headers):
    import main

    job = models.Job(
        title="Job ID Binding",
        department="Engineering",
        location="Beijing",
        status="热招中",
        hr_name="HR",
        description="<p>Open role</p>",
    )
    db_session.add(job)
    db_session.commit()

    parsed_resume = {
        "name": "Job ID Candidate",
        "job": "Wrong AI Job",
        "exp": "Bachelor",
        "phone": "13900000001",
        "email": "job-id@test.local",
        "skills": ["Python"],
        "ai_summary": "Qualified",
        "ai_analysis": "Qualified",
    }

    class FakeModel:
        def __init__(self, model_name):
            self.model_name = model_name

        def generate_content(self, prompt, generation_config=None):
            class Response:
                text = json.dumps(parsed_resume)

            return Response()

    original_api_key = main.api_key
    original_model = main.genai.GenerativeModel
    main.api_key = "test-api-key"
    main.genai.GenerativeModel = FakeModel
    try:
        response = client.post(
            "/api/parse-resume",
            headers=admin_headers,
            files={"file": ("resume.pdf", _valid_pdf_bytes(), "application/pdf")},
            data={"job_id": str(job.id), "operator": "Admin"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["job"] == job.title
    finally:
        main.api_key = original_api_key
        main.genai.GenerativeModel = original_model


def test_internal_batch_resume_upload_returns_per_file_results(client, db_session, admin_headers):
    import main

    job = models.Job(
        title="Batch Upload Job",
        department="Engineering",
        location="Beijing",
        status="热招中",
        hr_name="HR",
        description="<p>Open role</p>",
    )
    db_session.add(job)
    db_session.commit()

    responses = iter([
        {
            "name": "Batch Candidate One",
            "job": job.title,
            "exp": "Bachelor",
            "phone": "13900000002",
            "email": "batch-one@test.local",
            "skills": ["Python"],
            "ai_summary": "Qualified",
            "ai_analysis": "Qualified",
        },
        {
            "name": "Batch Candidate Two",
            "job": job.title,
            "exp": "Master",
            "phone": "13900000003",
            "email": "batch-two@test.local",
            "skills": ["FastAPI"],
            "ai_summary": "Qualified",
            "ai_analysis": "Qualified",
        },
    ])

    class FakeModel:
        def __init__(self, model_name):
            self.model_name = model_name

        def generate_content(self, prompt, generation_config=None):
            class Response:
                text = json.dumps(next(responses))

            return Response()

    original_api_key = main.api_key
    original_model = main.genai.GenerativeModel
    main.api_key = "test-api-key"
    main.genai.GenerativeModel = FakeModel
    try:
        response = client.post(
            "/api/parse-resumes",
            headers=admin_headers,
            files=[
                ("files", ("one.pdf", _valid_pdf_bytes("one"), "application/pdf")),
                ("files", ("two.pdf", _valid_pdf_bytes("two"), "application/pdf")),
            ],
            data={"job_id": str(job.id), "operator": "Admin"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        assert body["succeeded"] == 2
        assert body["failed"] == 0
        assert [item["status"] for item in body["results"]] == ["success", "success"]
        assert all(item["candidate"]["job"] == job.title for item in body["results"])
    finally:
        main.api_key = original_api_key
        main.genai.GenerativeModel = original_model
