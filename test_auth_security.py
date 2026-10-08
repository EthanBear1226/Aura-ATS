import models


def test_health_check_reports_database_status(client):
    response = client.get("/healthz")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_internal_business_apis_require_login(client):
    protected_endpoints = [
        "/api/candidates",
        "/api/jobs",
        "/api/workbench/dashboard",
        "/api/approvals/offer-fields-config",
        "/api/approvals/pending",
        "/api/settings/departments",
    ]

    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401, endpoint


def test_public_job_detail_remains_available_without_login(client, db_session):
    job = models.Job(
        title="公开投递测试岗位",
        department="研发部",
        location="北京",
        status="热招中",
        hr_name="HR",
        description="<h3>岗位职责</h3><p>负责 Aura ATS 自动化测试覆盖。</p>",
        salary_range="20k-30k",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/public/jobs/{job.id}")

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "公开投递测试岗位"
