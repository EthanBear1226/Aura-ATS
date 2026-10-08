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
