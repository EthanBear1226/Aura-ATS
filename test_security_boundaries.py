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
