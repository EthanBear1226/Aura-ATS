import datetime

import models


def test_non_admin_cannot_create_settings_department(client, make_auth_headers):
    recruiter_headers = make_auth_headers(
        "recruiter@test.local",
        role="Recruiter",
        name="Recruiter",
    )

    response = client.post(
        "/api/settings/departments",
        headers=recruiter_headers,
        json={"name": "Unauthorized Department"},
    )

    assert response.status_code == 403


def test_interviewer_workbench_is_scoped_to_interviewer(client, db_session, make_auth_headers):
    candidate = models.Candidate(
        name="Interviewer Workbench Candidate",
        job="Backend Engineer",
        stage="面试中",
        exp="Bachelor",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    db_session.add_all([
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Assigned Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            location="Online",
        ),
        models.Interview(
            candidate_id=candidate.id,
            interviewer_name="Other Interviewer",
            job_title=candidate.job,
            start_time=datetime.datetime.utcnow(),
            end_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            location="Online",
        ),
    ])
    db_session.commit()

    interviewer_headers = make_auth_headers(
        "assigned-interviewer@test.local",
        role="Interviewer",
        name="Assigned Interviewer",
    )
    response = client.get("/api/interviewer/workbench", headers=interviewer_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["candidate_name"] == "Interviewer Workbench Candidate"

    hr_headers = make_auth_headers(
        "hr-workbench@test.local",
        role="Recruiter",
        name="HR Workbench",
    )
    forbidden = client.get("/api/interviewer/workbench", headers=hr_headers)
    assert forbidden.status_code == 403


def test_interviewer_cannot_create_job(client, make_auth_headers):
    interviewer_headers = make_auth_headers(
        "interviewer@test.local",
        role="Interviewer",
        name="Interviewer",
    )

    response = client.post(
        "/api/jobs",
        headers=interviewer_headers,
        json={
            "title": "权限测试岗位",
            "department": "研发部",
            "location": "北京",
            "status": "热招中",
            "hr_name": "HR",
            "interview_process": "标准面试流程",
            "description": "用于验证面试官不能创建职位。",
            "job_type": "全职",
            "category": "技术",
            "experience": "不限",
            "job_level": "P5",
            "headcount": 1,
            "salary_range": "20k-30k",
            "salary_months": 12,
        },
    )

    assert response.status_code == 403
